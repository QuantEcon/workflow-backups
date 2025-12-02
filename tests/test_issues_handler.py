"""Tests for the issues handler module."""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest

from src.backup.issues_handler import IssuesHandler


@pytest.fixture
def mock_github():
    """Create a mock GitHub client."""
    return Mock()


@pytest.fixture
def mock_repo():
    """Create a mock GitHub repository."""
    repo = Mock()
    repo.name = "test-repo"
    repo.full_name = "QuantEcon/test-repo"
    return repo


@pytest.fixture
def mock_issue():
    """Create a mock GitHub issue."""
    issue = Mock()
    issue.number = 42
    issue.title = "Test issue title"
    issue.html_url = "https://github.com/QuantEcon/test-repo/issues/42"
    issue.state = "open"
    issue.user = Mock()
    issue.user.login = "testuser"
    issue.created_at = datetime(2024, 6, 15, 10, 30, 0)
    issue.updated_at = datetime(2024, 11, 20, 14, 22, 0)
    issue.closed_at = None
    issue.closed_by = None
    issue.labels = []
    issue.milestone = None
    issue.assignees = []
    issue.body = "This is the issue body with **markdown**."
    issue.pull_request = None  # Not a PR

    # Mock comments
    comment = Mock()
    comment.id = 123
    comment.user = Mock()
    comment.user.login = "commenter"
    comment.created_at = datetime(2024, 6, 16, 9, 0, 0)
    comment.body = "This is a comment."
    issue.get_comments.return_value = [comment]

    return issue


@pytest.fixture
def mock_pull_request():
    """Create a mock pull request (should be filtered out)."""
    pr = Mock()
    pr.number = 99
    pr.title = "Fix something"
    pr.pull_request = Mock()  # Has pull_request attribute = is a PR
    return pr


class TestIssuesHandler:
    """Tests for the IssuesHandler class."""

    def test_init(self, mock_github):
        """Test handler initialization."""
        handler = IssuesHandler(mock_github)
        assert handler.github == mock_github

    def test_export_issues_empty_repo(self, mock_github, mock_repo):
        """Test exporting issues from a repo with no issues."""
        mock_repo.get_issues.return_value = []

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        assert export["metadata"]["repo"] == "QuantEcon/test-repo"
        assert export["metadata"]["total_issues"] == 0
        assert export["metadata"]["open_issues"] == 0
        assert export["metadata"]["closed_issues"] == 0
        assert export["issues"] == []

    def test_export_issues_filters_pull_requests(
        self, mock_github, mock_repo, mock_issue, mock_pull_request
    ):
        """Test that pull requests are filtered out."""
        mock_repo.get_issues.return_value = [mock_issue, mock_pull_request]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        # Should only have 1 issue (PR filtered out)
        assert export["metadata"]["total_issues"] == 1
        assert len(export["issues"]) == 1
        assert export["issues"][0]["number"] == 42

    def test_serialize_issue_basic(self, mock_github, mock_repo, mock_issue):
        """Test serializing a basic issue."""
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        issue_data = export["issues"][0]
        assert issue_data["number"] == 42
        assert issue_data["title"] == "Test issue title"
        assert issue_data["url"] == "https://github.com/QuantEcon/test-repo/issues/42"
        assert issue_data["state"] == "open"
        assert issue_data["author"] == "testuser"
        assert issue_data["body"] == "This is the issue body with **markdown**."
        assert issue_data["closed_at"] is None
        assert issue_data["closed_by"] is None

    def test_serialize_issue_with_labels(self, mock_github, mock_repo, mock_issue):
        """Test serializing an issue with labels."""
        label1 = Mock()
        label1.name = "bug"
        label2 = Mock()
        label2.name = "help wanted"
        mock_issue.labels = [label1, label2]
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        issue_data = export["issues"][0]
        assert issue_data["labels"] == ["bug", "help wanted"]

    def test_serialize_issue_with_milestone(self, mock_github, mock_repo, mock_issue):
        """Test serializing an issue with a milestone."""
        mock_issue.milestone = Mock()
        mock_issue.milestone.title = "v1.0.0"
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        issue_data = export["issues"][0]
        assert issue_data["milestone"] == "v1.0.0"

    def test_serialize_issue_with_assignees(self, mock_github, mock_repo, mock_issue):
        """Test serializing an issue with assignees."""
        assignee1 = Mock()
        assignee1.login = "user1"
        assignee2 = Mock()
        assignee2.login = "user2"
        mock_issue.assignees = [assignee1, assignee2]
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        issue_data = export["issues"][0]
        assert issue_data["assignees"] == ["user1", "user2"]

    def test_serialize_issue_with_comments(self, mock_github, mock_repo, mock_issue):
        """Test serializing an issue with comments."""
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        issue_data = export["issues"][0]
        assert issue_data["comment_count"] == 1
        assert len(issue_data["comments"]) == 1
        assert issue_data["comments"][0]["author"] == "commenter"
        assert issue_data["comments"][0]["body"] == "This is a comment."

    def test_serialize_closed_issue(self, mock_github, mock_repo, mock_issue):
        """Test serializing a closed issue."""
        mock_issue.state = "closed"
        mock_issue.closed_at = datetime(2024, 12, 1, 12, 0, 0)
        mock_issue.closed_by = Mock()
        mock_issue.closed_by.login = "closer"
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        assert export["metadata"]["closed_issues"] == 1
        assert export["metadata"]["open_issues"] == 0
        issue_data = export["issues"][0]
        assert issue_data["state"] == "closed"
        assert issue_data["closed_by"] == "closer"
        assert issue_data["closed_at"] is not None

    def test_issues_sorted_by_number(self, mock_github, mock_repo):
        """Test that issues are sorted by number."""
        issue1 = Mock()
        issue1.number = 10
        issue1.title = "Issue 10"
        issue1.html_url = "https://github.com/QuantEcon/test-repo/issues/10"
        issue1.state = "open"
        issue1.user = Mock()
        issue1.user.login = "user"
        issue1.created_at = datetime(2024, 1, 1)
        issue1.updated_at = datetime(2024, 1, 1)
        issue1.closed_at = None
        issue1.closed_by = None
        issue1.labels = []
        issue1.milestone = None
        issue1.assignees = []
        issue1.body = "Body"
        issue1.pull_request = None
        issue1.get_comments.return_value = []

        issue2 = Mock()
        issue2.number = 5
        issue2.title = "Issue 5"
        issue2.html_url = "https://github.com/QuantEcon/test-repo/issues/5"
        issue2.state = "open"
        issue2.user = Mock()
        issue2.user.login = "user"
        issue2.created_at = datetime(2024, 1, 1)
        issue2.updated_at = datetime(2024, 1, 1)
        issue2.closed_at = None
        issue2.closed_by = None
        issue2.labels = []
        issue2.milestone = None
        issue2.assignees = []
        issue2.body = "Body"
        issue2.pull_request = None
        issue2.get_comments.return_value = []

        mock_repo.get_issues.return_value = [issue1, issue2]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        # Should be sorted by number (5 before 10)
        assert export["issues"][0]["number"] == 5
        assert export["issues"][1]["number"] == 10

    def test_save_to_file(self, mock_github, tmp_path):
        """Test saving export data to a JSON file."""
        handler = IssuesHandler(mock_github)

        export_data = {"metadata": {"repo": "test", "total_issues": 0}, "issues": []}

        output_path = tmp_path / "subdir" / "issues.json"
        handler.save_to_file(export_data, output_path)

        assert output_path.exists()
        with open(output_path) as f:
            saved_data = json.load(f)
        assert saved_data == export_data

    def test_export_to_file(self, mock_github, mock_repo, mock_issue, tmp_path):
        """Test the combined export and save method."""
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        output_path = tmp_path / "issues.json"

        export_data = handler.export_to_file(mock_repo, output_path)

        assert output_path.exists()
        assert export_data["metadata"]["total_issues"] == 1

        with open(output_path) as f:
            saved_data = json.load(f)
        assert saved_data["issues"][0]["number"] == 42

    def test_handles_null_user(self, mock_github, mock_repo, mock_issue):
        """Test handling of issues with null user (deleted accounts)."""
        mock_issue.user = None
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        issue_data = export["issues"][0]
        assert issue_data["author"] is None

    def test_handles_null_comment_user(self, mock_github, mock_repo, mock_issue):
        """Test handling of comments with null user (deleted accounts)."""
        comment = Mock()
        comment.id = 456
        comment.user = None
        comment.created_at = datetime(2024, 6, 16, 9, 0, 0)
        comment.body = "Comment from deleted user."
        mock_issue.get_comments.return_value = [comment]
        mock_repo.get_issues.return_value = [mock_issue]

        handler = IssuesHandler(mock_github)
        export = handler.export_issues(mock_repo)

        comment_data = export["issues"][0]["comments"][0]
        assert comment_data["author"] is None
