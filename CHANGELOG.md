# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `exclude_archived` config option to skip archived repositories during backup
- `exclude_repositories` config option to exclude specific repos by exact name
- `exclude_patterns` config option to exclude repos matching regex patterns
- Improved logging: excluded repos now shown in formatted multi-column list

### Changed
- Type hints updated to Python 3.9+ style (lowercase `list`, `dict`, `set`)
- Ruff configuration updated to use `[tool.ruff.lint]` section

## [0.1.0] - 2025-12-02

### Added
- Individual repository backup with `repositories:` config (exact names, no regex needed)
- Pattern-based repository selection with `patterns:` config (Python regex)
- Skip existing same-day backups (use `--force` to override)
- PAT authentication support for private repos via `REPO_BACKUP_TOKEN`
- S3 upload with SHA256 checksums for integrity verification
- Backup reporting with `--task report`
- Issue reporting for weekly runs (creates/updates GitHub issue, tags @mmcky on failure)
- Dry-run mode with `--dry-run` to preview backups
- GitHub Actions workflow with OIDC authentication for AWS
- Configuration system using YAML

### Changed
- Renamed project from `action-repo-maintenance` to `workflow-backups`
- Adopted `workflow-` prefix convention for org-level automation
- Switched to OIDC authentication (recommended over static credentials)

---

Release notes for each version are in `docs/releases/`.
