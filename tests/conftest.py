"""Test fixtures for backup tests."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_github_repo():
    """Create a mock GitHub repository."""
    repo = Mock()
    repo.name = "test-repo"
    repo.full_name = "quantecon/test-repo"
    repo.clone_url = "https://github.com/quantecon/test-repo.git"
    repo.default_branch = "main"
    return repo


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    client = Mock()
    org = Mock()

    # Create mock repos with proper string name attributes
    repo1 = Mock()
    repo1.name = "lecture-python.myst"  # This is a real string, not a Mock
    repo1.full_name = "quantecon/lecture-python.myst"
    repo1.archived = False

    repo2 = Mock()
    repo2.name = "lecture-julia"
    repo2.full_name = "quantecon/lecture-julia"
    repo2.archived = False

    repo3 = Mock()
    repo3.name = "quantecon-notebooks-python"
    repo3.full_name = "quantecon/quantecon-notebooks-python"
    repo3.archived = False

    repo4 = Mock()
    repo4.name = "other-repo"
    repo4.full_name = "quantecon/other-repo"
    repo4.archived = False

    repos = [repo1, repo2, repo3, repo4]

    # Accept type parameter for get_repos (e.g., type="all")
    org.get_repos.return_value = repos
    org.get_repos.side_effect = lambda **kwargs: repos
    client.get_organization.return_value = org

    return client


@pytest.fixture
def mock_github_client_with_archived():
    """Create a mock GitHub client with some archived repos."""
    client = Mock()
    org = Mock()

    repo1 = Mock()
    repo1.name = "lecture-python.myst"
    repo1.full_name = "quantecon/lecture-python.myst"
    repo1.archived = False

    repo2 = Mock()
    repo2.name = "lecture-julia"
    repo2.full_name = "quantecon/lecture-julia"
    repo2.archived = True  # Archived!

    repo3 = Mock()
    repo3.name = "quantecon-notebooks-python"
    repo3.full_name = "quantecon/quantecon-notebooks-python"
    repo3.archived = False

    repo4 = Mock()
    repo4.name = "old-archived-repo"
    repo4.full_name = "quantecon/old-archived-repo"
    repo4.archived = True  # Archived!

    repos = [repo1, repo2, repo3, repo4]

    org.get_repos.return_value = repos
    org.get_repos.side_effect = lambda **kwargs: repos
    client.get_organization.return_value = org

    return client


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = Mock()

    # Mock successful upload
    client.upload_file.return_value = None

    # Mock head_object for verification
    client.head_object.return_value = {
        "ContentLength": 1024,
        "LastModified": datetime.now(timezone.utc),
    }

    return client


@pytest.fixture
def sample_config():
    """Provide a sample configuration."""
    return {
        "backup": {
            "enabled": True,
            "organization": "quantecon",
            "patterns": ["lecture-.*", "quantecon-.*"],
            "s3": {
                "bucket": "test-bucket",
                "region": "us-east-1",
                "prefix": "backups/",
            },
        }
    }
