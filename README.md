# QuantEcon Repository Backup Workflow

[![GitHub](https://img.shields.io/badge/github-QuantEcon%2Fworkflow--backups-blue?logo=github)](https://github.com/QuantEcon/workflow-backups)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A centralized workflow for backing up QuantEcon repositories to AWS S3.

## Overview

This workflow automatically backs up GitHub repositories to AWS S3 for disaster recovery and compliance. It runs from this single repository and backs up all matching repositories across the organization. It supports pattern-based repository selection, allowing you to backup specific repositories from an organization.

## Features

- **Pattern-based selection**: Use regex patterns to select which repositories to backup
- **Mirror backups**: Complete repository backups including all branches, tags, and history
- **S3 storage**: Secure storage in AWS S3 with upload verification
- **Skip existing**: Avoid redundant backups with automatic duplicate detection
- **Backup reporting**: Generate reports on backup status and storage usage

## Quick Start

### 1. Configure AWS IAM for OIDC Authentication (Recommended)

OIDC authentication is more secure than static credentials—no long-lived secrets to manage.

#### Create IAM Identity Provider

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```

#### Create IAM Role with Trust Policy

Create a file `trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/workflow-backups:*"
        }
      }
    }
  ]
}
```

Create the role:

```bash
aws iam create-role \
  --role-name GitHubActionsBackupRole \
  --assume-role-policy-document file://trust-policy.json
```

#### Attach S3 Permissions

Create `s3-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:HeadObject"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR_BUCKET_NAME",
        "arn:aws:s3:::YOUR_BUCKET_NAME/*"
      ]
    }
  ]
}
```

```bash
aws iam put-role-policy \
  --role-name GitHubActionsBackupRole \
  --policy-name S3BackupAccess \
  --policy-document file://s3-policy.json
```

### 2. Configure GitHub Repository

Add the following secret to your repository:

- `AWS_ROLE_ARN`: The ARN of the IAM role (e.g., `arn:aws:iam::123456789012:role/GitHubActionsBackupRole`)

Optionally add a variable:

- `AWS_REGION`: AWS region (default: `us-east-1`)

### 3. Create Configuration File

Create `config.yml` in your repository:

```yaml
backup:
  enabled: true
  organization: "your-org"
  patterns:
    - "lecture-.*"      # Backup repos starting with "lecture-"
    - "quantecon-.*"    # Backup repos starting with "quantecon-"
  s3:
    bucket: "your-backup-bucket"
    region: "us-east-1"
    prefix: "backups/"
```

### 4. Use the Workflow

The included workflow (`.github/workflows/backup.yml`) runs weekly and can be triggered manually:

```yaml
name: Repository Backup
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM UTC
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      - run: python -m src.main --config config.yml --task backup
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Local Development

```bash
# Clone repository
git clone https://github.com/quantecon/workflow-backups.git
cd workflow-backups

# Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure AWS credentials locally
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export GITHUB_TOKEN="your_token"

# Run backup
python -m src.main --config config.yml --task backup

# Run tests
pytest tests/
```

## CLI Options

```bash
python -m src.main --help

Options:
  --config PATH       Path to configuration file (default: config.yml)
  --task {backup,report}  Task to run (default: backup)
  --organization ORG  Override organization from config
  --force            Force backup even if today's backup exists
  --verbose          Enable debug logging
```

## Backup Storage Structure

Backups are stored in S3 with the following structure:

```
s3://bucket-name/
├── repo-name/
│   ├── repo-name-20251127.tar.gz
│   ├── repo-name-20251120.tar.gz
│   └── repo-name-20251113.tar.gz
└── another-repo/
    └── another-repo-20251127.tar.gz
```

Each backup includes metadata:
- Repository full name
- Backup timestamp
- Default branch
- Archive size

## Restoring a Backup

To restore a repository from a backup:

```bash
# 1. Download the backup from S3
aws s3 cp s3://bucket-name/repo-name/repo-name-20251127.tar.gz .

# 2. Extract the archive (contains a bare git mirror)
tar -xzf repo-name-20251127.tar.gz

# 3. Clone from the bare repo to create a working repository
git clone repo-name restored-repo

# 4. You now have a full working repository
cd restored-repo
git branch -a   # View all branches
git tag         # View all tags
```

The backup is a complete git mirror including all branches, tags, and full commit history.

## Technology Stack

- **Language**: Python 3.9+
- **Cloud Storage**: AWS S3
- **GitHub API**: PyGithub
- **AWS SDK**: boto3
- **Testing**: pytest

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Open an issue in this repository
- Contact the QuantEcon development team
