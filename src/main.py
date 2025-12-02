"""Main entry point for the workflow-backups tool."""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

from src.backup import BackupManager, RepoMatcher, S3Handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    logger.info(f"Loading configuration from: {config_path}")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config


def run_backup(config: dict, args: argparse.Namespace) -> int:
    """
    Run the backup task.

    Args:
        config: Configuration dictionary
        args: Command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Get GitHub token
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.error("GITHUB_TOKEN environment variable not set")
            return 1

        # Get backup configuration
        backup_config = config.get("backup", {})
        if not backup_config.get("enabled", False):
            logger.warning("Backup is not enabled in configuration")
            return 0

        # Initialize components
        s3_config = backup_config.get("s3", {})
        s3_handler = S3Handler(
            bucket_name=s3_config.get("bucket"),
            region=s3_config.get("region", "us-east-1"),
            prefix=s3_config.get("prefix", "backups/"),
        )

        patterns = backup_config.get("patterns", [])
        repositories = backup_config.get("repositories", [])
        exclude_archived = backup_config.get("exclude_archived", False)
        exclude_patterns = backup_config.get("exclude_patterns", [])
        exclude_repositories = backup_config.get("exclude_repositories", [])
        repo_matcher = RepoMatcher(
            patterns=patterns,
            repositories=repositories,
            exclude_archived=exclude_archived,
            exclude_patterns=exclude_patterns,
            exclude_repositories=exclude_repositories,
        )

        backup_manager = BackupManager(
            github_token=github_token,
            s3_handler=s3_handler,
            repo_matcher=repo_matcher,
        )

        # Get organization from config or command line
        organization = args.organization or backup_config.get("organization")
        if not organization:
            logger.error("Organization not specified in config or command line")
            return 1

        # Run backup
        logger.info(f"Starting backup for organization: {organization}")
        results = backup_manager.backup_repositories(
            organization=organization,
            skip_existing=not args.force,
            dry_run=args.dry_run,
        )

        # Log results
        logger.info("=" * 60)
        if results.get("dry_run"):
            logger.info("DRY RUN Results:")
            logger.info(f"Total repositories matched: {results['total_repos']}")
            logger.info(f"Would backup: {len(results['would_backup'])}")
            logger.info(f"Already exist (would skip): {len(results['skipped'])}")
            logger.info("=" * 60)
            if results["would_backup"]:
                logger.info("Repositories that would be backed up:")
                for item in results["would_backup"]:
                    logger.info(f"  - {item['repo']} -> {item['backup_key']}")
        else:
            logger.info("Backup Results:")
            logger.info(f"Total repositories: {results['total_repos']}")
            logger.info(f"Successful: {len(results['successful'])}")
            logger.info(f"Failed: {len(results['failed'])}")
            logger.info(f"Skipped: {len(results['skipped'])}")
            logger.info("=" * 60)

            if results["failed"]:
                logger.error("Failed repositories:")
                for failure in results["failed"]:
                    logger.error(f"  - {failure}")
                return 1

        return 0

    except Exception as e:
        logger.error(f"Backup task failed: {e}", exc_info=True)
        return 1


def run_report(config: dict, args: argparse.Namespace) -> int:
    """
    Generate a backup report.

    Args:
        config: Configuration dictionary
        args: Command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.error("GITHUB_TOKEN environment variable not set")
            return 1

        backup_config = config.get("backup", {})
        s3_config = backup_config.get("s3", {})

        s3_handler = S3Handler(
            bucket_name=s3_config.get("bucket"),
            region=s3_config.get("region", "us-east-1"),
            prefix=s3_config.get("prefix", "backups/"),
        )

        patterns = backup_config.get("patterns", [])
        repositories = backup_config.get("repositories", [])
        exclude_archived = backup_config.get("exclude_archived", False)
        exclude_patterns = backup_config.get("exclude_patterns", [])
        exclude_repositories = backup_config.get("exclude_repositories", [])
        repo_matcher = RepoMatcher(
            patterns=patterns,
            repositories=repositories,
            exclude_archived=exclude_archived,
            exclude_patterns=exclude_patterns,
            exclude_repositories=exclude_repositories,
        )

        backup_manager = BackupManager(
            github_token=github_token,
            s3_handler=s3_handler,
            repo_matcher=repo_matcher,
        )

        organization = args.organization or backup_config.get("organization")
        if not organization:
            logger.error("Organization not specified")
            return 1

        report = backup_manager.get_backup_report(organization)

        # Display report
        logger.info("=" * 60)
        logger.info(f"Backup Report for {organization}")
        logger.info("=" * 60)
        logger.info(f"Total repositories monitored: {report['total_repos']}")
        logger.info(f"Repositories with backups: {report['repos_with_backups']}")
        logger.info(f"Total backup size: {report['total_backup_size'] / (1024**3):.2f} GB")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="QuantEcon Repository Backup Workflow")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yml"),
        help="Path to configuration file",
    )
    parser.add_argument(
        "--task",
        choices=["backup", "report"],
        default="backup",
        help="Task to run",
    )
    parser.add_argument(
        "--organization",
        type=str,
        help="GitHub organization name (overrides config)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force backup even if it already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be backed up without actually doing it",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    if not args.config.exists():
        logger.error(f"Configuration file not found: {args.config}")
        return 1

    config = load_config(args.config)

    # Run task
    if args.task == "backup":
        return run_backup(config, args)
    elif args.task == "report":
        return run_report(config, args)
    else:
        logger.error(f"Unknown task: {args.task}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
