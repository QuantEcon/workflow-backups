# Improvement Plan for workflow-backups

## Problem Statement

The current backup strategy creates a **full `git clone --mirror` → `tar.gz` → S3 upload** every week for every matched repository. This causes S3 storage to grow rapidly — a ~100MB repo generates ~5GB/year of backups with zero deduplication. Across 180+ repos in the full org config, this is unsustainable.

Meanwhile, git repositories are inherently distributed (every clone is a full backup), making weekly full snapshots largely redundant. The real recovery risk is **built HTML** — ephemeral build artifacts that are hard to reproduce.

---

## Strategy Overview

### Two Pillars

1. **HTML Recovery Tool** (new, in QuantEcon/actions) — Restore lecture websites from GitHub Release assets. This is the highest-priority recovery concern. **Tracked in [QuantEcon/actions#27](https://github.com/QuantEcon/actions/issues/27).**

2. **Improved S3 Backups** (this repo) — Keep the existing git mirror → S3 approach but add retention management, storage class optimization, and skip-unchanged logic to eliminate waste.

---

## Phase 0: S3 Lifecycle Rules (No Code Changes)

**Goal:** Immediately reduce storage costs by 40-60% with zero code changes.

### Actions

- [ ] Add S3 Lifecycle rule: transition objects older than 90 days to **S3 Standard-IA** (~40% cheaper)
- [ ] Add S3 Lifecycle rule: transition objects older than 365 days to **Glacier Instant Retrieval** (~68% cheaper)
- [ ] Consider enabling **S3 Intelligent-Tiering** for automatic cost optimization

### S3 Lifecycle Configuration

```json
{
  "Rules": [
    {
      "ID": "backup-tiering",
      "Filter": { "Prefix": "backups/" },
      "Status": "Enabled",
      "Transitions": [
        { "Days": 90, "StorageClass": "STANDARD_IA" },
        { "Days": 365, "StorageClass": "GLACIER_INSTANT_RETRIEVAL" }
      ]
    }
  ]
}
```

### Implementation

Apply via AWS CLI:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket backup-quantecon-github \
  --lifecycle-configuration file://aws/lifecycle-policy.json
```

---

## Phase 1: GFS Retention Policy

**Goal:** Cap the number of backups per repo using a Grandfather-Father-Son rotation. Eliminate unbounded growth.

### Retention Rules

| Tier | What to Keep | Duration | ~Count per Repo |
|------|-------------|----------|-----------------|
| Weekly | All backups | Last 2 months | ~8 |
| Monthly | Last backup of each month | Next 10 months | ~10 |
| Yearly | Last backup of each year | Indefinite | Accumulates |

**Steady-state: ~18-20 backups per repo** instead of unbounded weekly accumulation.

### Changes Required

#### 1. New module: `src/backup/retention.py`

Implement retention logic that runs after each backup cycle:

```python
def apply_retention_policy(s3_handler, repo_name, policy):
    """Delete backups that fall outside the retention policy."""
    backups = s3_handler.list_backups(repo_name)  # already exists
    keep = compute_keepers(backups, policy)
    to_delete = set(backups) - keep
    for backup in to_delete:
        s3_handler.delete(backup["key"])
```

Key logic:
- Parse date from backup key format: `{repo}-{YYYYMMDD}.tar.gz`
- Keep all within 60 days (weekly tier)
- Keep last-of-month within 365 days (monthly tier)  
- Keep last-of-year forever (yearly tier)

#### 2. New method: `S3Handler.delete_object()`

Add a delete method to `s3_handler.py`:

```python
def delete_object(self, object_key: str) -> bool:
    """Delete a single object from S3."""
```

#### 3. New CLI task: `--task cleanup`

Add a cleanup task to `main.py` that applies retention to all repos:

```bash
python -m src.main --config config.yml --task cleanup          # Apply retention
python -m src.main --config config.yml --task cleanup --dry-run # Preview deletions
```

#### 4. Config extension

```yaml
retention:
  weekly_days: 60      # Keep all backups within this many days
  monthly_days: 365    # Keep last-of-month within this many days
  yearly: true         # Keep last-of-year indefinitely
```

#### 5. Integration

- Run retention **after** each backup cycle in the GitHub Actions workflow
- Add retention summary to the backup report
- Log all deletions for auditability

### Tests

- `tests/test_retention.py` — Unit tests for date parsing, keeper computation, edge cases (month boundaries, year boundaries, empty backup list, single backup)

---

## Phase 2: Skip Unchanged Repositories

**Goal:** Avoid backing up repos that haven't changed since the last backup.

### Approach

Before cloning a repo, check if it has new commits since the last backup:

1. Fetch the latest commit SHA from GitHub API (`repo.get_branch(default_branch).commit.sha`)
2. Compare against the SHA stored as S3 metadata on the most recent backup
3. Skip if unchanged (log as "no changes")

### Changes Required

#### 1. Store commit SHA in backup metadata

In `BackupManager._backup_single_repo()`, add `latest_commit_sha` to the metadata dict passed to `s3_handler.upload_file()`.

#### 2. New method: `S3Handler.get_latest_backup_metadata()`

Retrieve metadata from the most recent backup for a repo:

```python
def get_latest_backup_metadata(self, repo_name: str) -> dict | None:
    """Get metadata from the most recent backup of a repo."""
```

#### 3. Change detection in backup loop

In `BackupManager.backup_repositories()`, before cloning:

```python
if skip_unchanged:
    latest_meta = self.s3_handler.get_latest_backup_metadata(repo.name)
    current_sha = repo.get_branch(repo.default_branch).commit.sha
    if latest_meta and latest_meta.get("latest_commit_sha") == current_sha:
        logger.info(f"No changes since last backup, skipping: {repo.full_name}")
        results["skipped"].append({"repo": repo.full_name, "reason": "no_changes"})
        continue
```

#### 4. Config option

```yaml
backup:
  skip_unchanged: true  # Skip repos with no new commits since last backup
```

### Impact

For a typical week, most lecture repos don't change. This could skip 80-90% of repos in a weekly run, dramatically reducing clone time and upload volume.

---

## Phase 3: Git Bundles (Optional, Future)

**Goal:** Replace full tarballs with git bundles for ~90% size reduction on incremental backups.

### Why

Git bundles are native git transport files. An incremental bundle contains only new objects since a reference point:

```bash
# Full bundle (~100MB)
git bundle create repo-full.bundle --all

# Incremental (~10KB-5MB typically)
git bundle create repo-incr.bundle --all ^<last-refs>
```

### Trade-offs

| Pro | Con |
|-----|-----|
| ~90% size reduction | More complex backup/restore logic |
| Git-native verification (`git bundle verify`) | Need to track refs per repo |
| Incremental by design | Restore requires chaining bundles |

### Decision

**Defer until Phase 1+2 are complete.** The GFS retention policy and skip-unchanged together should reduce storage by 70-80%. Git bundles add complexity and are only worth implementing if further reduction is needed.

---

## Phase 4: GitLab Mirror (Optional, Future)

**Goal:** Secondary live mirror for instant recovery.

### Approach

- Sign up for free GitLab.com account
- Create `quantecon-backup` group
- Push mirrors via `git push --mirror` from the existing GitHub Actions workflow
- GitLab free tier: unlimited private repos, supports push mirroring

### Trade-offs

| Pro | Con |
|-----|-----|
| Instant `git clone` recovery | Same-vendor risk if using another SaaS |
| Browsable web UI | Additional secrets to manage |
| Zero storage cost | Free-tier limitations on CI minutes |

### Decision

**Evaluate after Phase 0-2.** If S3 costs become negligible with retention + lifecycle rules, the motivation for a secondary mirror is reduced. Consider if the primary goal is faster recovery speed rather than cost.

---

## Implementation Priority

| Phase | What | Effort | Storage Impact | Status |
|-------|------|--------|---------------|--------|
| **0** | S3 Lifecycle rules | ~30 min (AWS console/CLI) | ~40-60% cost reduction | Not started |
| **1** | GFS Retention policy | Medium (new module + tests) | Caps growth, deletes old backups | Not started |
| **2** | Skip unchanged repos | Small (metadata + SHA check) | ~80-90% fewer uploads per run | Not started |
| **3** | Git bundles | Large (rewrite backup logic) | ~90% per-backup size reduction | Deferred |
| **4** | GitLab mirror | Small (workflow step) | N/A (separate system) | Deferred |

### Recommended Order

**Phase 0 → Phase 1 → Phase 2**

Phase 0 is immediate and requires no code changes. Phase 1 is the highest-impact code change — it directly caps storage growth. Phase 2 is a quick win that reduces backup run time and upload volume.

Together, Phases 0-2 should reduce S3 costs by **~80-90%** compared to the current unbounded weekly full-backup approach.

---

## Related

- [QuantEcon/actions#27](https://github.com/QuantEcon/actions/issues/27) — HTML Recovery Tool for lecture sites
- `publish-gh-pages` action `create-release-assets` feature — Already creates HTML archives on release
- Current lecture-python.myst `publish.yml` — Uses `softprops/action-gh-release@v2` for release assets
