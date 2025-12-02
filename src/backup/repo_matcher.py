"""Repository pattern matcher for selecting repositories to backup."""

from __future__ import annotations

import logging
import re
from re import Pattern

from github import Github
from github.Repository import Repository

logger = logging.getLogger(__name__)


class RepoMatcher:
    """Matches repositories based on regex patterns and exact names."""

    def __init__(
        self,
        patterns: list[str] | None = None,
        repositories: list[str] | None = None,
        exclude_archived: bool = False,
        exclude_patterns: list[str] | None = None,
        exclude_repositories: list[str] | None = None,
    ) -> None:
        """
        Initialize the repository matcher.

        Args:
            patterns: List of regex patterns to match repository names
            repositories: List of exact repository names to match
            exclude_archived: If True, skip archived repositories
            exclude_patterns: List of regex patterns to exclude repository names
            exclude_repositories: List of exact repository names to exclude
        """
        self.patterns: list[Pattern[str]] = [re.compile(pattern) for pattern in (patterns or [])]
        self.repositories: set[str] = set(repositories or [])
        self.exclude_archived = exclude_archived
        self.exclude_patterns: list[Pattern[str]] = [
            re.compile(pattern) for pattern in (exclude_patterns or [])
        ]
        self.exclude_repositories: set[str] = set(exclude_repositories or [])
        logger.info(
            f"Initialized RepoMatcher with {len(self.patterns)} patterns, "
            f"{len(self.repositories)} exact repositories, "
            f"exclude_archived={exclude_archived}, "
            f"{len(self.exclude_patterns)} exclude patterns, "
            f"{len(self.exclude_repositories)} exclude repositories"
        )

    def matches(self, repo_name: str) -> bool:
        """
        Check if a repository name matches any pattern or exact name.

        Args:
            repo_name: The repository name to check

        Returns:
            True if the repository matches any pattern or exact name, False otherwise
        """
        # Check exact repository names first (fast set lookup)
        if repo_name in self.repositories:
            logger.debug(f"Repository '{repo_name}' matched exact name")
            return True

        # Check regex patterns
        for pattern in self.patterns:
            if pattern.match(repo_name):
                logger.debug(f"Repository '{repo_name}' matched pattern: {pattern.pattern}")
                return True
        return False

    def is_excluded(self, repo_name: str) -> bool:
        """
        Check if a repository name should be excluded.

        Args:
            repo_name: The repository name to check

        Returns:
            True if the repository should be excluded, False otherwise
        """
        # Check exact exclude names first (fast set lookup)
        if repo_name in self.exclude_repositories:
            logger.debug(f"Repository '{repo_name}' excluded by exact name")
            return True

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if pattern.match(repo_name):
                logger.debug(f"Repository '{repo_name}' excluded by pattern: {pattern.pattern}")
                return True
        return False

    def _log_repo_list(self, repo_names: list[str], num_columns: int = 3) -> None:
        """
        Log a list of repository names in a formatted multi-column layout.

        Args:
            repo_names: Sorted list of repository names to log
            num_columns: Number of columns to display (default: 3)
        """
        if not repo_names:
            return

        # Calculate column width based on longest name
        max_width = max(len(name) for name in repo_names) + 2

        # Build rows
        for i in range(0, len(repo_names), num_columns):
            row_items = repo_names[i : i + num_columns]
            row = "  " + "".join(name.ljust(max_width) for name in row_items)
            logger.info(row)

    def filter_repositories(self, github_client: Github, organization: str) -> list[Repository]:
        """
        Filter repositories from an organization based on configured patterns.

        Args:
            github_client: Authenticated GitHub client
            organization: Organization name to fetch repositories from

        Returns:
            List of repositories that match the configured patterns
        """
        logger.info(f"Fetching repositories for organization: {organization}")
        org = github_client.get_organization(organization)
        # Use type="all" to include private repositories
        all_repos = list(org.get_repos(type="all"))
        logger.info(f"Found {len(all_repos)} total repositories")

        # Filter out archived repos if requested
        if self.exclude_archived:
            archived_count = sum(1 for repo in all_repos if repo.archived)
            all_repos = [repo for repo in all_repos if not repo.archived]
            logger.info(
                f"Excluding {archived_count} archived repositories, " f"{len(all_repos)} remaining"
            )

        matched_repos = [repo for repo in all_repos if self.matches(repo.name)]
        logger.info(f"Matched {len(matched_repos)} repositories out of {len(all_repos)} total")

        # Apply exclusions
        if self.exclude_patterns or self.exclude_repositories:
            excluded_repos = [repo for repo in matched_repos if self.is_excluded(repo.name)]
            if excluded_repos:
                excluded_names = sorted(repo.name for repo in excluded_repos)
                logger.info(f"Excluded {len(excluded_repos)} repositories by exclude rules:")
                # Format in columns for readability
                self._log_repo_list(excluded_names)
            matched_repos = [repo for repo in matched_repos if not self.is_excluded(repo.name)]
            logger.info(f"{len(matched_repos)} repositories remaining after exclusions")

        for repo in matched_repos:
            logger.debug(f"Matched repository: {repo.full_name}")

        # Warn about exact repository names that weren't found
        # (could be private repos not visible to the token)
        if self.repositories:
            found_names = {repo.name for repo in all_repos}
            not_found = self.repositories - found_names
            if not_found:
                logger.warning(
                    f"Configured repositories not found (may be private or misspelled): "
                    f"{sorted(not_found)}"
                )

        return matched_repos
