# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repository backup functionality to AWS S3
- Pattern-based repository selection using regex
- S3Handler for uploads with MD5 verification
- RepoMatcher for filtering repositories by pattern
- BackupManager for coordinating backup operations
- GitHub Actions workflow with OIDC authentication
- Configuration system using YAML
- Backup reporting functionality
- Comprehensive documentation

### Changed
- Renamed project from `action-repo-maintenance` to `workflow-backups`
- Adopted `workflow-` prefix convention for org-level automation
- Switched to OIDC authentication (recommended over static credentials)
- Simplified configuration by removing unused feature placeholders

### Removed
- Placeholder configuration for unimplemented features (health_checks, automation, retention)
- Unused `requests` dependency

---

Release notes for each version are in `docs/releases/`.
