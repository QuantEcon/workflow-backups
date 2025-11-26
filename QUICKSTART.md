# Quick Start Guide

Get started with the QuantEcon centralized backup workflow for AWS S3.

## Prerequisites

- Python 3.9 or higher
- GitHub personal access token with `repo` scope
- AWS account with S3 bucket
- AWS IAM role configured for GitHub Actions OIDC (recommended)

## Option 1: GitHub Actions (Recommended)

### Step 1: Set Up AWS OIDC Authentication

Create an IAM Identity Provider for GitHub:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```

Create an IAM role with this trust policy (replace `ACCOUNT_ID` and `YOUR_ORG/YOUR_REPO`):

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
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
```

Attach S3 permissions to the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket", "s3:HeadObject"],
      "Resource": ["arn:aws:s3:::YOUR_BUCKET", "arn:aws:s3:::YOUR_BUCKET/*"]
    }
  ]
}
```

### Step 2: Configure GitHub Secrets

Add to your repository secrets:

| Secret | Value |
|--------|-------|
| `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/GitHubActionsBackupRole` |

### Step 3: Create Configuration

Create `config.yml`:

```yaml
backup:
  enabled: true
  organization: "your-org"
  patterns:
    - "lecture-.*"
    - "quantecon-.*"
  s3:
    bucket: "your-bucket-name"
    region: "us-east-1"
    prefix: "backups/"
```

### Step 4: Run the Workflow

1. Go to Actions tab in GitHub
2. Select "Repository Backup"
3. Click "Run workflow"

## Option 2: Local Development

### Step 1: Clone and Install

```bash
git clone https://github.com/quantecon/workflow-backups.git
cd workflow-backups

python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### Step 2: Configure

```bash
cp config.example.yml config.yml
# Edit config.yml with your settings
```

### Step 3: Set Environment Variables

```bash
export GITHUB_TOKEN="ghp_your_token"
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
```

### Step 4: Run Backup

```bash
# Run backup
python -m src.main --config config.yml --task backup

# Generate report
python -m src.main --config config.yml --task report

# Force re-backup
python -m src.main --config config.yml --task backup --force

# Debug mode
python -m src.main --config config.yml --task backup --verbose
```

## Backup Structure

Backups are stored as:

```
s3://bucket/backups/{repo-name}/{repo-name}-{YYYYMMDD}.tar.gz
```

Example:
```
s3://quantecon-backups/backups/lecture-python/lecture-python-20251127.tar.gz
```

## Pattern Matching Examples

| Pattern | Matches |
|---------|---------|
| `lecture-.*` | `lecture-python`, `lecture-julia`, `lecture-stats` |
| `quantecon-.*` | `quantecon-notebooks`, `quantecon-py` |
| `^exact-name$` | Only `exact-name` |
| `.*-notes` | `lecture-notes`, `class-notes` |

## Troubleshooting

### "GITHUB_TOKEN not set"

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

### "Access Denied" on S3

1. Check IAM role has correct permissions
2. Verify OIDC trust policy references correct repository
3. Ensure S3 bucket exists and is in correct region

### "No repositories matched"

1. Verify patterns are valid Python regex
2. Check organization name is correct
3. Ensure GitHub token has access to the organization

## Next Steps

- Review [README.md](README.md) for full documentation
- Check [docs/architecture.md](docs/architecture.md) for technical details
