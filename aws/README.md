# AWS IAM Setup for GitHub Actions OIDC

These policy templates are used to configure AWS IAM for the backup workflow.

## Setup Instructions

Replace placeholders before using:
- `ACCOUNT_ID` → Your AWS account ID
- `BUCKET_NAME` → Your S3 bucket name

### 1. Create OIDC Identity Provider

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. Create IAM Role

```bash
# Update trust-policy.json with your ACCOUNT_ID first
aws iam create-role \
  --role-name GitHubActionsBackupRole \
  --assume-role-policy-document file://aws/trust-policy.json
```

### 3. Attach S3 Permissions

```bash
# Update s3-policy.json with your BUCKET_NAME first
aws iam put-role-policy \
  --role-name GitHubActionsBackupRole \
  --policy-name S3BackupAccess \
  --policy-document file://aws/s3-policy.json
```

### 4. Get Role ARN

```bash
aws iam get-role --role-name GitHubActionsBackupRole --query 'Role.Arn' --output text
```

### 5. Add to GitHub Secrets

Add the role ARN as `AWS_ROLE_ARN` secret in your repository settings.
