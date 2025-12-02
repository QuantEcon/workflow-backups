"""Unit tests for main module."""

import argparse
from unittest.mock import Mock, patch

import pytest

from src.main import load_config, main, run_backup, run_report


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_config_success(self, tmp_path):
        """Test loading valid config file."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
backup:
  enabled: true
  organization: quantecon
  patterns:
    - "lecture-.*"
  s3:
    bucket: test-bucket
    region: us-east-1
"""
        )

        config = load_config(config_file)

        assert config["backup"]["enabled"] is True
        assert config["backup"]["organization"] == "quantecon"
        assert "lecture-.*" in config["backup"]["patterns"]

    def test_load_config_file_not_found(self, tmp_path):
        """Test loading nonexistent config file."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yml")


class TestRunBackup:
    """Test run_backup function."""

    @patch.dict("os.environ", {"GITHUB_TOKEN": ""}, clear=True)
    def test_backup_no_token(self, sample_config):
        """Test backup fails without GitHub token."""
        args = argparse.Namespace(
            organization=None,
            force=False,
            dry_run=False,
        )

        result = run_backup(sample_config, args)

        assert result == 1

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"})
    def test_backup_disabled(self):
        """Test backup exits when disabled in config."""
        config = {"backup": {"enabled": False}}
        args = argparse.Namespace(organization=None, force=False, dry_run=False)

        result = run_backup(config, args)

        assert result == 0

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"})
    @patch("src.main.BackupManager")
    @patch("src.main.S3Handler")
    @patch("src.main.RepoMatcher")
    def test_backup_success(self, mock_matcher, mock_s3, mock_manager, sample_config):
        """Test successful backup run."""
        mock_manager_instance = Mock()
        mock_manager_instance.backup_repositories.return_value = {
            "total_repos": 2,
            "successful": ["repo1", "repo2"],
            "failed": [],
            "skipped": [],
        }
        mock_manager.return_value = mock_manager_instance

        args = argparse.Namespace(organization=None, force=False, dry_run=False)

        result = run_backup(sample_config, args)

        assert result == 0
        mock_manager_instance.backup_repositories.assert_called_once()

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"})
    @patch("src.main.BackupManager")
    @patch("src.main.S3Handler")
    @patch("src.main.RepoMatcher")
    def test_backup_dry_run(self, mock_matcher, mock_s3, mock_manager, sample_config):
        """Test dry-run mode returns success without actual backups."""
        mock_manager_instance = Mock()
        mock_manager_instance.backup_repositories.return_value = {
            "total_repos": 2,
            "successful": [],
            "failed": [],
            "skipped": [],
            "would_backup": [
                {"repo": "org/repo1", "backup_key": "repo1/repo1-20251127.tar.gz"},
                {"repo": "org/repo2", "backup_key": "repo2/repo2-20251127.tar.gz"},
            ],
            "dry_run": True,
        }
        mock_manager.return_value = mock_manager_instance

        args = argparse.Namespace(organization=None, force=False, dry_run=True)

        result = run_backup(sample_config, args)

        assert result == 0
        mock_manager_instance.backup_repositories.assert_called_once_with(
            organization="quantecon",
            skip_existing=True,
            dry_run=True,
        )

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"})
    @patch("src.main.BackupManager")
    @patch("src.main.S3Handler")
    @patch("src.main.RepoMatcher")
    def test_backup_with_failures(self, mock_matcher, mock_s3, mock_manager, sample_config):
        """Test backup returns error when repos fail."""
        mock_manager_instance = Mock()
        mock_manager_instance.backup_repositories.return_value = {
            "total_repos": 2,
            "successful": ["repo1"],
            "failed": [{"repo": "repo2", "reason": "upload_failed"}],
            "skipped": [],
        }
        mock_manager.return_value = mock_manager_instance

        args = argparse.Namespace(organization=None, force=False, dry_run=False)

        result = run_backup(sample_config, args)

        assert result == 1

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"})
    @patch("src.main.BackupManager")
    @patch("src.main.S3Handler")
    @patch("src.main.RepoMatcher")
    def test_backup_org_override(self, mock_matcher, mock_s3, mock_manager, sample_config):
        """Test organization override from command line."""
        mock_manager_instance = Mock()
        mock_manager_instance.backup_repositories.return_value = {
            "total_repos": 1,
            "successful": ["repo1"],
            "failed": [],
            "skipped": [],
        }
        mock_manager.return_value = mock_manager_instance

        args = argparse.Namespace(organization="other-org", force=False, dry_run=False)

        run_backup(sample_config, args)  # Result intentionally unused

        mock_manager_instance.backup_repositories.assert_called_once_with(
            organization="other-org",
            skip_existing=True,
            dry_run=False,
        )


class TestRunReport:
    """Test run_report function."""

    @patch.dict("os.environ", {"GITHUB_TOKEN": ""}, clear=True)
    def test_report_no_token(self, sample_config):
        """Test report fails without GitHub token."""
        args = argparse.Namespace(organization=None)

        result = run_report(sample_config, args)

        assert result == 1

    @patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"})
    @patch("src.main.BackupManager")
    @patch("src.main.S3Handler")
    @patch("src.main.RepoMatcher")
    def test_report_success(self, mock_matcher, mock_s3, mock_manager, sample_config):
        """Test successful report generation."""
        mock_manager_instance = Mock()
        mock_manager_instance.get_backup_report.return_value = {
            "organization": "quantecon",
            "total_repos": 5,
            "repos_with_backups": 3,
            "total_backup_size": 1024 * 1024 * 100,  # 100 MB
            "repositories": {},
        }
        mock_manager.return_value = mock_manager_instance

        args = argparse.Namespace(organization=None)

        result = run_report(sample_config, args)

        assert result == 0


class TestMain:
    """Test main entry point."""

    @patch("src.main.run_backup")
    @patch("src.main.load_config")
    def test_main_backup_task(self, mock_load_config, mock_run_backup, tmp_path):
        """Test main runs backup task."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("backup:\n  enabled: true")

        mock_load_config.return_value = {"backup": {"enabled": True}}
        mock_run_backup.return_value = 0

        with patch("sys.argv", ["prog", "--config", str(config_file), "--task", "backup"]):
            result = main()

        assert result == 0
        mock_run_backup.assert_called_once()

    @patch("src.main.run_report")
    @patch("src.main.load_config")
    def test_main_report_task(self, mock_load_config, mock_run_report, tmp_path):
        """Test main runs report task."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("backup:\n  enabled: true")

        mock_load_config.return_value = {"backup": {"enabled": True}}
        mock_run_report.return_value = 0

        with patch("sys.argv", ["prog", "--config", str(config_file), "--task", "report"]):
            result = main()

        assert result == 0
        mock_run_report.assert_called_once()

    def test_main_config_not_found(self, tmp_path):
        """Test main fails when config not found."""
        with patch("sys.argv", ["prog", "--config", str(tmp_path / "nonexistent.yml")]):
            result = main()

        assert result == 1
