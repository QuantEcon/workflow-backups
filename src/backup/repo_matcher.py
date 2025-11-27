"""Repository pattern matcher for selecting repositories to backup."""

import re
import logging
from typing import List, Optional, Pattern, Set
from github import Github
from github.Repository import Repository

logger = logging.getLogger(__name__)


class RepoMatcher:
    """Matches repositories based on regex patterns and exact names."""

    def __init__(
        self,
        patterns: Optional[List[str]] = None,
        repositories: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the repository matcher.

        Args:
            patterns: List of regex patterns to match repository names
            repositories: List of exact repository names to match
        """
        self.patterns: List[Pattern[str]] = [
            re.compile(pattern) for pattern in (patterns or [])
        ]
        self.repositories: Set[str] = set(repositories or [])
        logger.info(
            f"Initialized RepoMatcher with {len(self.patterns)} patterns "
            f"and {len(self.repositories)} exact repositories"
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

    def filter_repositories(
        self, github_client: Github, organization: str
    ) -> List[Repository]:
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

        matched_repos = [repo for repo in all_repos if self.matches(repo.name)]
        logger.info(
            f"Matched {len(matched_repos)} repositories out of {len(all_repos)} total"
        )

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
