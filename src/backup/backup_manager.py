"""Main backup manager coordinating repository backups to S3."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from github import Github
from github.Repository import Repository

from .issues_handler import IssuesHandler
from .repo_matcher import RepoMatcher
from .s3_handler import S3Handler

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages the backup process for repositories."""

    def __init__(
        self,
        github_token: str,
        s3_handler: S3Handler,
        repo_matcher: RepoMatcher,
        backup_metadata: dict[str, bool] | None = None,
    ) -> None:
        """
        Initialize the backup manager.

        Args:
            github_token: GitHub authentication token
            s3_handler: Configured S3 handler for uploads
            repo_matcher: Repository pattern matcher
            backup_metadata: Dict of metadata types to backup (e.g., {"issues": True})
        """
        self.github_token = github_token
        self.github = Github(github_token)
        self.s3_handler = s3_handler
        self.repo_matcher = repo_matcher
        self.backup_metadata = backup_metadata or {}
        self.issues_handler = (
            IssuesHandler(self.github) if self.backup_metadata.get("issues") else None
        )
        logger.info("Initialized BackupManager")

    def backup_repositories(
        self, organization: str, skip_existing: bool = True, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Backup all matching repositories for an organization.

        Args:
            organization: GitHub organization name
            skip_existing: Skip repositories that already have today's backup
            dry_run: If True, show what would be done without actually backing up

        Returns:
            Dictionary with backup results and statistics
        """
        if dry_run:
            logger.info("DRY RUN MODE - No actual backups will be performed")
        logger.info(f"Starting backup process for organization: {organization}")

        # Get matching repositories
        repos = self.repo_matcher.filter_repositories(self.github, organization)

        results = {
            "total_repos": len(repos),
            "successful": [],
            "failed": [],
            "skipped": [],
            "would_backup": [],  # For dry-run mode
            "issues_backup": {
                "successful": [],
                "failed": [],
                "skipped": [],
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
        }

        for repo in repos:
            try:
                logger.info(f"Processing repository: {repo.full_name}")

                # Generate backup filename
                date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
                backup_key = f"{repo.name}/{repo.name}-{date_str}.tar.gz"

                # Skip if backup exists and skip_existing is True
                if skip_existing and self.s3_handler.backup_exists(backup_key):
                    logger.info(f"Backup already exists, skipping: {backup_key}")
                    results["skipped"].append({"repo": repo.full_name, "reason": "already_exists"})
                    # Still backup issues if enabled (issues may have changed)
                    if self.issues_handler and not dry_run:
                        self._backup_issues(repo, date_str, results, skip_existing)
                    continue

                # In dry-run mode, just log what would happen
                if dry_run:
                    logger.info(f"[DRY RUN] Would backup: {repo.full_name} -> {backup_key}")
                    results["would_backup"].append(
                        {"repo": repo.full_name, "backup_key": backup_key}
                    )
                    continue

                # Perform git backup
                success = self._backup_single_repo(repo, backup_key)

                if success:
                    results["successful"].append(repo.full_name)
                    # Backup issues if enabled
                    if self.issues_handler:
                        self._backup_issues(repo, date_str, results, skip_existing)
                else:
                    results["failed"].append({"repo": repo.full_name, "reason": "upload_failed"})

            except Exception as e:
                logger.error(f"Failed to backup {repo.full_name}: {e}")
                results["failed"].append({"repo": repo.full_name, "reason": str(e)})

        if dry_run:
            logger.info(
                f"DRY RUN complete: {len(results['would_backup'])} would be backed up, "
                f"{len(results['skipped'])} already exist"
            )
        else:
            logger.info(
                f"Backup complete: {len(results['successful'])} successful, "
                f"{len(results['failed'])} failed, {len(results['skipped'])} skipped"
            )

        return results

    def _backup_single_repo(self, repo: Repository, backup_key: str) -> bool:
        """
        Backup a single repository to S3.

        Args:
            repo: GitHub repository object
            backup_key: S3 object key for the backup

        Returns:
            True if backup was successful, False otherwise
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_path = temp_path / repo.name
            archive_path = temp_path / f"{repo.name}.tar.gz"

            try:
                # Clone repository (mirror for complete backup)
                # Use authenticated URL for private repos
                clone_url = repo.clone_url
                if self.github_token and clone_url.startswith("https://"):
                    # Insert token into URL: https://github.com/... -> https://token@github.com/...
                    clone_url = clone_url.replace(
                        "https://", f"https://x-access-token:{self.github_token}@"
                    )

                logger.info(f"Cloning repository: {repo.clone_url}")  # Log without token
                subprocess.run(
                    ["git", "clone", "--mirror", clone_url, str(repo_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Create tarball
                logger.info(f"Creating archive: {archive_path}")
                subprocess.run(
                    ["tar", "-czf", str(archive_path), "-C", str(temp_path), repo.name],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Prepare metadata
                metadata = {
                    "repository": repo.full_name,
                    "backup_date": datetime.now(timezone.utc).isoformat(),
                    "default_branch": repo.default_branch,
                    "size_bytes": str(archive_path.stat().st_size),
                }

                # Upload to S3
                success = self.s3_handler.upload_file(archive_path, backup_key, metadata)

                return success

            except subprocess.CalledProcessError as e:
                logger.error(f"Git/tar command failed: {e.stderr}")
                return False
            except Exception as e:
                logger.error(f"Backup failed for {repo.full_name}: {e}")
                return False

    def _backup_issues(
        self, repo: Repository, date_str: str, results: dict[str, Any], skip_existing: bool
    ) -> bool:
        """
        Backup issues for a single repository to S3.

        Args:
            repo: GitHub repository object
            date_str: Date string for backup filename (YYYYMMDD)
            results: Results dictionary to update
            skip_existing: Skip if backup already exists

        Returns:
            True if backup was successful, False otherwise
        """
        issues_key = f"{repo.name}/{repo.name}-issues-{date_str}.json"

        try:
            # Skip if issues backup already exists
            if skip_existing and self.s3_handler.backup_exists(issues_key):
                logger.info(f"Issues backup already exists, skipping: {issues_key}")
                results["issues_backup"]["skipped"].append(repo.full_name)
                return True

            # Export issues
            logger.info(f"Exporting issues for: {repo.full_name}")
            export_data = self.issues_handler.export_issues(repo)

            # Upload to S3 as JSON
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                temp_file = Path(f.name)

            try:
                metadata = {
                    "repository": repo.full_name,
                    "backup_date": datetime.now(timezone.utc).isoformat(),
                    "content_type": "application/json",
                    "total_issues": str(export_data["metadata"]["total_issues"]),
                }

                success = self.s3_handler.upload_file(temp_file, issues_key, metadata)

                if success:
                    logger.info(
                        f"Issues backup successful: {issues_key} "
                        f"({export_data['metadata']['total_issues']} issues)"
                    )
                    results["issues_backup"]["successful"].append(repo.full_name)
                else:
                    results["issues_backup"]["failed"].append(
                        {"repo": repo.full_name, "reason": "upload_failed"}
                    )

                return success

            finally:
                temp_file.unlink()  # Clean up temp file

        except Exception as e:
            logger.error(f"Failed to backup issues for {repo.full_name}: {e}")
            results["issues_backup"]["failed"].append({"repo": repo.full_name, "reason": str(e)})
            return False

    def get_backup_report(self, organization: str) -> dict[str, Any]:
        """
        Generate a report of all backups for an organization.

        Args:
            organization: GitHub organization name

        Returns:
            Dictionary containing backup statistics and details
        """
        repos = self.repo_matcher.filter_repositories(self.github, organization)

        report = {
            "organization": organization,
            "total_repos": len(repos),
            "repos_with_backups": 0,
            "total_backup_size": 0,
            "repositories": {},
        }

        for repo in repos:
            backups = self.s3_handler.list_backups(repo.name)
            if backups:
                report["repos_with_backups"] += 1
                total_size = sum(b["size"] for b in backups)
                report["total_backup_size"] += total_size

                report["repositories"][repo.name] = {
                    "backup_count": len(backups),
                    "total_size": total_size,
                    "latest_backup": max(b["last_modified"] for b in backups),
                    "backups": backups,
                }

        return report
