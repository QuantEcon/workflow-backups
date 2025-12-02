"""Handler for backing up GitHub issues to JSON format."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from github import Github
from github.Issue import Issue
from github.Repository import Repository

logger = logging.getLogger(__name__)


class IssuesHandler:
    """Handles exporting GitHub issues to JSON format for backup."""

    def __init__(self, github: Github) -> None:
        """
        Initialize the issues handler.

        Args:
            github: Authenticated PyGithub instance
        """
        self.github = github
        logger.info("Initialized IssuesHandler")

    def export_issues(self, repo: Repository) -> dict[str, Any]:
        """
        Export all issues from a repository to a dictionary.

        Args:
            repo: GitHub repository object

        Returns:
            Dictionary containing all issues with metadata
        """
        logger.info(f"Exporting issues for: {repo.full_name}")

        issues_data: list[dict[str, Any]] = []
        open_count = 0
        closed_count = 0

        # Get all issues (open and closed)
        # Note: This also returns pull requests, we filter them out
        for issue in repo.get_issues(state="all"):
            # Skip pull requests (they have a pull_request attribute)
            if issue.pull_request is not None:
                continue

            issue_dict = self._serialize_issue(issue)
            issues_data.append(issue_dict)

            if issue.state == "open":
                open_count += 1
            else:
                closed_count += 1

        # Sort by issue number for consistent output
        issues_data.sort(key=lambda x: x["number"])

        export = {
            "metadata": {
                "repo": repo.full_name,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_issues": len(issues_data),
                "open_issues": open_count,
                "closed_issues": closed_count,
            },
            "issues": issues_data,
        }

        logger.info(
            f"Exported {len(issues_data)} issues "
            f"({open_count} open, {closed_count} closed) for {repo.full_name}"
        )

        return export

    def _serialize_issue(self, issue: Issue) -> dict[str, Any]:
        """
        Serialize a single issue to a dictionary.

        Args:
            issue: GitHub issue object

        Returns:
            Dictionary representation of the issue
        """
        # Get comments
        comments = []
        for comment in issue.get_comments():
            comments.append(
                {
                    "id": comment.id,
                    "author": comment.user.login if comment.user else None,
                    "created_at": comment.created_at.isoformat() if comment.created_at else None,
                    "body": comment.body,
                }
            )

        return {
            "number": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "state": issue.state,
            "author": issue.user.login if issue.user else None,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
            "closed_by": issue.closed_by.login if issue.closed_by else None,
            "labels": [label.name for label in issue.labels],
            "milestone": issue.milestone.title if issue.milestone else None,
            "assignees": [assignee.login for assignee in issue.assignees],
            "body": issue.body,
            "comment_count": len(comments),
            "comments": comments,
        }

    def save_to_file(self, export_data: dict[str, Any], output_path: Path) -> None:
        """
        Save exported issues to a JSON file.

        Args:
            export_data: Dictionary containing exported issues
            output_path: Path to save the JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved issues export to: {output_path}")

    def export_to_file(self, repo: Repository, output_path: Path) -> dict[str, Any]:
        """
        Export issues from a repository and save to a JSON file.

        Args:
            repo: GitHub repository object
            output_path: Path to save the JSON file

        Returns:
            Dictionary containing exported issues
        """
        export_data = self.export_issues(repo)
        self.save_to_file(export_data, output_path)
        return export_data
