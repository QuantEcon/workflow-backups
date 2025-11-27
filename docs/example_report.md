# Example Report Output

This document shows example output from the backup workflow.

## Backup Task Output

When running `python -m src.main --config config.yml --task backup`:

```
2025-11-27 02:00:01,123 - src.main - INFO - Loading configuration from: config.yml
2025-11-27 02:00:01,125 - src.backup.s3_handler - INFO - Initialized S3Handler for bucket 'quantecon-backups' in region 'us-east-1'
2025-11-27 02:00:01,126 - src.backup.backup_manager - INFO - Initialized BackupManager
2025-11-27 02:00:01,127 - src.main - INFO - Starting backup for organization: quantecon
2025-11-27 02:00:01,128 - src.backup.backup_manager - INFO - Starting backup process for organization: quantecon
2025-11-27 02:00:02,500 - src.backup.repo_matcher - INFO - Fetching repositories for organization: quantecon
2025-11-27 02:00:03,200 - src.backup.repo_matcher - INFO - Found 45 total repositories
2025-11-27 02:00:03,201 - src.backup.repo_matcher - INFO - Matched 8 repositories out of 45 total
2025-11-27 02:00:03,202 - src.backup.backup_manager - INFO - Processing repository: quantecon/lecture-python.myst
2025-11-27 02:00:03,300 - src.backup.backup_manager - INFO - Backup already exists, skipping: lecture-python.myst/lecture-python.myst-20251127.tar.gz
2025-11-27 02:00:03,301 - src.backup.backup_manager - INFO - Processing repository: quantecon/lecture-julia
2025-11-27 02:00:03,400 - src.backup.backup_manager - INFO - Cloning repository: https://github.com/quantecon/lecture-julia.git
2025-11-27 02:00:15,500 - src.backup.backup_manager - INFO - Creating archive: /tmp/tmpxyz123/lecture-julia.tar.gz
2025-11-27 02:00:18,200 - src.backup.s3_handler - INFO - Uploading /tmp/tmpxyz123/lecture-julia.tar.gz to s3://quantecon-backups/backups/lecture-julia/lecture-julia-20251127.tar.gz
2025-11-27 02:00:45,300 - src.backup.s3_handler - INFO - Successfully uploaded and verified: backups/lecture-julia/lecture-julia-20251127.tar.gz
2025-11-27 02:00:45,301 - src.backup.backup_manager - INFO - Processing repository: quantecon/quantecon-notebooks-python
...
2025-11-27 02:05:30,000 - src.backup.backup_manager - INFO - Backup complete: 7 successful, 0 failed, 1 skipped
2025-11-27 02:05:30,001 - src.main - INFO - ============================================================
2025-11-27 02:05:30,001 - src.main - INFO - Backup Results:
2025-11-27 02:05:30,001 - src.main - INFO - Total repositories: 8
2025-11-27 02:05:30,001 - src.main - INFO - Successful: 7
2025-11-27 02:05:30,001 - src.main - INFO - Failed: 0
2025-11-27 02:05:30,001 - src.main - INFO - Skipped: 1
2025-11-27 02:05:30,001 - src.main - INFO - ============================================================
```

## Report Task Output

When running `python -m src.main --config config.yml --task report`:

```
2025-11-27 10:00:01,123 - src.main - INFO - Loading configuration from: config.yml
2025-11-27 10:00:01,200 - src.backup.s3_handler - INFO - Initialized S3Handler for bucket 'quantecon-backups' in region 'us-east-1'
2025-11-27 10:00:01,201 - src.backup.backup_manager - INFO - Initialized BackupManager
2025-11-27 10:00:02,500 - src.backup.repo_matcher - INFO - Fetching repositories for organization: quantecon
2025-11-27 10:00:03,200 - src.backup.repo_matcher - INFO - Matched 8 repositories out of 45 total
2025-11-27 10:00:03,300 - src.backup.s3_handler - INFO - Found 4 backups for repository: lecture-python.myst
2025-11-27 10:00:03,400 - src.backup.s3_handler - INFO - Found 4 backups for repository: lecture-julia
2025-11-27 10:00:03,500 - src.backup.s3_handler - INFO - Found 3 backups for repository: quantecon-notebooks-python
2025-11-27 10:00:03,600 - src.backup.s3_handler - INFO - Found 4 backups for repository: lecture-python-intro
2025-11-27 10:00:03,700 - src.backup.s3_handler - INFO - Found 2 backups for repository: lecture-stats
2025-11-27 10:00:03,800 - src.backup.s3_handler - INFO - Found 4 backups for repository: quantecon-py
2025-11-27 10:00:03,900 - src.backup.s3_handler - INFO - Found 0 backups for repository: lecture-new-project
2025-11-27 10:00:04,000 - src.backup.s3_handler - INFO - Found 3 backups for repository: quantecon.py
2025-11-27 10:00:04,100 - src.main - INFO - ============================================================
2025-11-27 10:00:04,100 - src.main - INFO - Backup Report for quantecon
2025-11-27 10:00:04,100 - src.main - INFO - ============================================================
2025-11-27 10:00:04,100 - src.main - INFO - Total repositories monitored: 8
2025-11-27 10:00:04,100 - src.main - INFO - Repositories with backups: 7
2025-11-27 10:00:04,100 - src.main - INFO - Total backup size: 2.45 GB
2025-11-27 10:00:04,100 - src.main - INFO - ============================================================
```

## S3 Bucket Structure

After several weeks of backups, the S3 bucket will look like:

```
s3://quantecon-backups/backups/
├── lecture-python.myst/
│   ├── lecture-python.myst-20251127.tar.gz    (156 MB)
│   ├── lecture-python.myst-20251120.tar.gz    (155 MB)
│   ├── lecture-python.myst-20251113.tar.gz    (154 MB)
│   └── lecture-python.myst-20251106.tar.gz    (153 MB)
│
├── lecture-julia/
│   ├── lecture-julia-20251127.tar.gz          (89 MB)
│   ├── lecture-julia-20251120.tar.gz          (88 MB)
│   ├── lecture-julia-20251113.tar.gz          (87 MB)
│   └── lecture-julia-20251106.tar.gz          (86 MB)
│
├── quantecon-notebooks-python/
│   ├── quantecon-notebooks-python-20251127.tar.gz  (45 MB)
│   ├── quantecon-notebooks-python-20251120.tar.gz  (44 MB)
│   └── quantecon-notebooks-python-20251113.tar.gz  (44 MB)
│
├── lecture-python-intro/
│   └── ...
│
└── quantecon-py/
    └── ...
```

## Backup Metadata

Each backup archive includes S3 metadata:

```json
{
  "repository": "quantecon/lecture-python.myst",
  "backup_date": "2025-11-27T02:00:15.123456",
  "default_branch": "main",
  "size_bytes": "163577856"
}
```

## GitHub Actions Summary

After the workflow completes, you'll see in the Actions run:

**Backup Summary:**
- ✅ 7 repositories backed up successfully
- ⏭️ 1 repository skipped (already backed up today)
- ❌ 0 repositories failed

**Artifacts:**
- `backup-logs-42` - Full backup logs (retained 30 days)

## Error Scenarios

### Authentication Failure
```
2025-11-27 02:00:03,400 - src.backup.backup_manager - ERROR - Failed to backup quantecon/private-repo: 
    401 {"message": "Bad credentials"}
```

### S3 Upload Failure
```
2025-11-27 02:00:45,300 - src.backup.s3_handler - ERROR - Failed to upload /tmp/tmpxyz123/repo.tar.gz to S3: 
    An error occurred (AccessDenied) when calling the PutObject operation: Access Denied
```

### Rate Limiting
```
2025-11-27 02:00:03,200 - src.backup.repo_matcher - WARNING - GitHub API rate limit approaching: 
    100 requests remaining (resets at 03:00 UTC)
```
