# Architecture Documentation

## Overview

The `workflow-backups` project is a centralized Python application that backs up QuantEcon repositories to AWS S3. It runs as a scheduled GitHub Actions workflow from this single repository, backing up all matching repositories across the organization.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   GitHub Actions Runtime                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              GitHub Actions Workflow                    │ │
│  │          (.github/workflows/backup.yml)                 │ │
│  └──────────────────────┬─────────────────────────────────┘ │
│                         │                                    │
│  ┌──────────────────────▼─────────────────────────────────┐ │
│  │                  Main Entry Point                       │ │
│  │                   (src/main.py)                         │ │
│  └──────────────────────┬─────────────────────────────────┘ │
│                         │                                    │
│  ┌──────────────────────▼─────────────────────────────────┐ │
│  │               Configuration Loader                      │ │
│  │               (config.yml parsing)                      │ │
│  └──────────────────────┬─────────────────────────────────┘ │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ BackupManager │
                  └───────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐   ┌──────────┐   ┌──────────────┐
│ RepoMatcher  │   │S3Handler │   │  GitHub API  │
│              │   │          │   │  (PyGithub)  │
└──────────────┘   └──────────┘   └──────────────┘
        │                │                │
        ▼                ▼                ▼
┌──────────────┐   ┌──────────┐   ┌──────────────┐
│GitHub Repos  │   │  AWS S3  │   │  Git Clone   │
└──────────────┘   └──────────┘   └──────────────┘
```

## Components

### Main Entry Point (`src/main.py`)

Handles CLI argument parsing, configuration loading, and task dispatch.

**Functions:**
- `main()`: Entry point, parses arguments
- `load_config()`: Load YAML configuration
- `run_backup()`: Execute backup task
- `run_report()`: Generate backup report

### BackupManager (`src/backup/backup_manager.py`)

Coordinates the backup process for all matched repositories.

**Methods:**
- `backup_repositories()`: Main orchestration - iterates repos, handles results
- `_backup_single_repo()`: Clone repo, create archive, upload to S3
- `get_backup_report()`: Generate statistics on backups

**Backup Process:**
1. Filter repositories by pattern
2. For each matched repository:
   - Check if today's backup exists (skip if so)
   - Clone as mirror (`git clone --mirror`)
   - Create tarball (`tar -czf`)
   - Upload to S3 with metadata
   - Verify upload
3. Return results summary

### RepoMatcher (`src/backup/repo_matcher.py`)

Filters repositories using regex patterns and exact names, with exclusion support.

**Methods:**
- `matches(repo_name)`: Check if name matches any pattern or exact name
- `is_excluded(repo_name)`: Check if name matches any exclude rule
- `filter_repositories(github_client, org)`: Get all matching repos (after exclusions)
- `_log_repo_list(repo_names)`: Format and log a list of repos in columns

**Configuration Options:**
- `patterns`: Regex patterns to include
- `repositories`: Exact names to include
- `exclude_archived`: Skip archived repositories
- `exclude_patterns`: Regex patterns to exclude
- `exclude_repositories`: Exact names to exclude

**Exclusion Order:**
1. Archived repos filtered first (if `exclude_archived: true`)
2. Include patterns/repositories applied
3. Exclusions applied last (takes priority over includes)

**Example Output:**
```
INFO - Excluded 6 repositories by exclude rules:
INFO -   econark                   old-project               quantecon.py
INFO -   repo-deprecated           test-repo                 unused-fork
INFO - 42 repositories remaining after exclusions
```

**Pattern Examples:**
- `lecture-.*` → matches `lecture-python`, `lecture-julia`
- `^specific-repo$` → exact match only

### S3Handler (`src/backup/s3_handler.py`)

Manages S3 uploads with verification.

**Methods:**
- `upload_file()`: Upload with MD5 verification
- `backup_exists()`: Check if backup already exists
- `list_backups()`: List backups for a repository

**Upload Process:**
1. Calculate MD5 hash
2. Upload to S3 with metadata
3. Verify by comparing file sizes
4. Return success/failure

## Configuration

**File:** `config.yml`

```yaml
backup:
  enabled: true
  organization: "quantecon"
  exclude_archived: true
  repositories:
    - "specific-repo"
  patterns:
    - "lecture-.*"
  exclude_repositories:
    - "old-repo"
  exclude_patterns:
    - ".*-test$"
  s3:
    bucket: "bucket-name"
    region: "us-east-1"
    prefix: "backups/"
```

Environment variables:
- `GITHUB_TOKEN`: GitHub API access
- AWS credentials via OIDC (recommended) or environment variables

## S3 Storage Structure

```
s3://bucket-name/backups/
├── repo-name/
│   ├── repo-name-20251127.tar.gz
│   └── repo-name-20251120.tar.gz
└── another-repo/
    └── another-repo-20251127.tar.gz
```

**Metadata per backup:**
- `repository`: Full name (org/repo)
- `backup_date`: ISO 8601 timestamp
- `default_branch`: Default branch name
- `size_bytes`: Archive size

## Authentication

### Recommended: OIDC (OpenID Connect)

No long-lived credentials. GitHub Actions gets temporary credentials via AWS IAM role.

```yaml
permissions:
  id-token: write
  contents: read

- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: us-east-1
```

### Alternative: Static Credentials

Store `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in GitHub secrets.

## Error Handling

- **Component level**: Each component logs errors and returns success/failure
- **Task level**: Failed repos are logged but don't stop other backups
- **Main level**: Returns exit code 1 if any failures occurred

## Testing

```
tests/
├── conftest.py              # Pytest fixtures
├── test_backup_manager.py   # BackupManager tests
├── test_main.py             # CLI tests
├── test_repo_matcher.py     # RepoMatcher tests
└── test_s3_handler.py       # S3Handler tests
```

Run tests:
```bash
nox -s tests          # Full suite with coverage (Python 3.9-3.12)
nox -s tests_quick    # Quick run without coverage
```

**Coverage**: 88% (55 tests)

## Security

### Read-Only GitHub Operations

This workflow performs **read-only operations** on GitHub repositories:

- Only `get_organization()`, `get_repos()`, and property access are used
- `git clone --mirror` only downloads (never pushes)
- No repository modifications, commits, or pull requests

### Best Practices

- Use OIDC authentication (no stored credentials)
- Use fine-grained PATs with minimal scopes
- S3 bucket should have restricted access
- Backups encrypted in transit (TLS)

---

**Last Updated**: 2025-12-02
