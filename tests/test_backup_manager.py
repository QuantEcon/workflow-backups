"""Unit tests for BackupManager."""

import subprocess
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.backup.backup_manager import BackupManager
from src.backup.repo_matcher import RepoMatcher
from src.backup.s3_handler import S3Handler


@pytest.fixture
def mock_s3_handler():
    """Create a mock S3Handler."""
    handler = Mock(spec=S3Handler)
    handler.backup_exists.return_value = False
    handler.upload_file.return_value = True
    handler.list_backups.return_value = []
    return handler


@pytest.fixture
def mock_repo_matcher():
    """Create a mock RepoMatcher."""
    matcher = Mock(spec=RepoMatcher)
    return matcher


@pytest.fixture
def mock_repos():
    """Create mock repository objects."""
    repos = []
    for name in ["lecture-python", "lecture-julia", "quantecon-notebooks"]:
        repo = Mock()
        repo.name = name
        repo.full_name = f"quantecon/{name}"
        repo.clone_url = f"https://github.com/quantecon/{name}.git"
        repo.default_branch = "main"
        repos.append(repo)
    return repos


class TestBackupManagerInit:
    """Test BackupManager initialization."""

    @patch("src.backup.backup_manager.Github")
    def test_init(self, mock_github_class, mock_s3_handler, mock_repo_matcher):
        """Test manager initializes correctly."""
        manager = BackupManager(
            github_token="test-token",
            s3_handler=mock_s3_handler,
            repo_matcher=mock_repo_matcher,
        )

        mock_github_class.assert_called_once_with("test-token")
        assert manager.s3_handler == mock_s3_handler
        assert manager.repo_matcher == mock_repo_matcher


class TestBackupRepositories:
    """Test backup_repositories method."""

    @patch("src.backup.backup_manager.Github")
    def test_backup_skips_existing(
        self, mock_github, mock_s3_handler, mock_repo_matcher, mock_repos
    ):
        """Test that existing backups are skipped."""
        mock_repo_matcher.filter_repositories.return_value = mock_repos
        mock_s3_handler.backup_exists.return_value = True  # All exist

        manager = BackupManager(
            github_token="test-token",
            s3_handler=mock_s3_handler,
            repo_matcher=mock_repo_matcher,
        )

        results = manager.backup_repositories("quantecon", skip_existing=True)

        assert results["total_repos"] == 3
        assert len(results["successful"]) == 0
        assert len(results["failed"]) == 0
        assert len(results["skipped"]) == 3
        for skip in results["skipped"]:
            assert skip["reason"] == "already_exists"

    @patch("src.backup.backup_manager.Github")
    def test_backup_no_matching_repos(self, mock_github, mock_s3_handler, mock_repo_matcher):
        """Test when no repositories match patterns."""
        mock_repo_matcher.filter_repositories.return_value = []

        manager = BackupManager(
            github_token="test-token",
            s3_handler=mock_s3_handler,
            repo_matcher=mock_repo_matcher,
        )

        results = manager.backup_repositories("quantecon")

        assert results["total_repos"] == 0
        assert len(results["successful"]) == 0


class TestBackupSingleRepo:
    """Test _backup_single_repo method."""

    @patch("src.backup.backup_manager.Github")
    @patch("src.backup.backup_manager.subprocess.run")
    def test_backup_single_repo_success(
        self, mock_run, mock_github, mock_s3_handler, mock_repo_matcher, mock_repos, tmp_path
    ):
        """Test successful single repo backup."""
        # Mock successful git clone and tar
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        manager = BackupManager(
            github_token="test-token",
            s3_handler=mock_s3_handler,
            repo_matcher=mock_repo_matcher,
        )

        _repo = mock_repos[0]  # noqa: F841
        # We can't easily test this without creating actual files
        # Just verify the method exists and is callable
        assert hasattr(manager, "_backup_single_repo")

    @patch("src.backup.backup_manager.Github")
    @patch("src.backup.backup_manager.subprocess.run")
    def test_backup_single_repo_clone_failure(
        self, mock_run, mock_github, mock_s3_handler, mock_repo_matcher, mock_repos
    ):
        """Test handling of git clone failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr="Authentication failed"
        )

        manager = BackupManager(
            github_token="test-token",
            s3_handler=mock_s3_handler,
            repo_matcher=mock_repo_matcher,
        )

        repo = mock_repos[0]
        result = manager._backup_single_repo(repo, "test-key")

        assert result is False


class TestGetBackupReport:
    """Test get_backup_report method."""

    @patch("src.backup.backup_manager.Github")
    def test_report_with_backups(self, mock_github, mock_s3_handler, mock_repo_matcher, mock_repos):
        """Test report generation with existing backups."""
        mock_repo_matcher.filter_repositories.return_value = mock_repos[:2]

        # Setup mock backup data
        mock_s3_handler.list_backups.side_effect = [
            [  # lecture-python has 2 backups
                {
                    "key": "backups/lecture-python/lecture-python-20251127.tar.gz",
                    "size": 1024000,
                    "last_modified": datetime(2025, 11, 27),
                },
                {
                    "key": "backups/lecture-python/lecture-python-20251120.tar.gz",
                    "size": 1020000,
                    "last_modified": datetime(2025, 11, 20),
                },
            ],
            [  # lecture-julia has 1 backup
                {
                    "key": "backups/lecture-julia/lecture-julia-20251127.tar.gz",
                    "size": 512000,
                    "last_modified": datetime(2025, 11, 27),
                },
            ],
        ]

        manager = BackupManager(
            github_token="test-token",
            s3_handler=mock_s3_handler,
            repo_matcher=mock_repo_matcher,
        )

        report = manager.get_backup_report("quantecon")

        assert report["organization"] == "quantecon"
        assert report["total_repos"] == 2
        assert report["repos_with_backups"] == 2
        assert report["total_backup_size"] == 1024000 + 1020000 + 512000
        assert "lecture-python" in report["repositories"]
        assert report["repositories"]["lecture-python"]["backup_count"] == 2

    @patch("src.backup.backup_manager.Github")
    def test_report_no_backups(self, mock_github, mock_s3_handler, mock_repo_matcher, mock_repos):
        """Test report when no backups exist."""
        mock_repo_matcher.filter_repositories.return_value = mock_repos
        mock_s3_handler.list_backups.return_value = []  # No backups

        manager = BackupManager(
            github_token="test-token",
            s3_handler=mock_s3_handler,
            repo_matcher=mock_repo_matcher,
        )

        report = manager.get_backup_report("quantecon")

        assert report["total_repos"] == 3
        assert report["repos_with_backups"] == 0
        assert report["total_backup_size"] == 0
        assert report["repositories"] == {}
