"""Unit tests for RepoMatcher."""

import pytest
from src.backup.repo_matcher import RepoMatcher


class TestRepoMatcher:
    """Test the RepoMatcher class."""

    def test_single_pattern_match(self):
        """Test matching with a single pattern."""
        matcher = RepoMatcher(patterns=["lecture-.*"])
        
        assert matcher.matches("lecture-python.myst") is True
        assert matcher.matches("lecture-julia") is True
        assert matcher.matches("other-repo") is False

    def test_multiple_patterns(self):
        """Test matching with multiple patterns."""
        matcher = RepoMatcher(patterns=["lecture-.*", "quantecon-.*"])
        
        assert matcher.matches("lecture-python.myst") is True
        assert matcher.matches("quantecon-notebooks") is True
        assert matcher.matches("other-repo") is False

    def test_exact_match_with_pattern(self):
        """Test exact repository name matching with regex pattern."""
        matcher = RepoMatcher(patterns=["^specific-repo$"])
        
        assert matcher.matches("specific-repo") is True
        assert matcher.matches("specific-repo-extra") is False
        assert matcher.matches("prefix-specific-repo") is False

    def test_exact_repositories(self):
        """Test exact repository name matching without regex."""
        matcher = RepoMatcher(repositories=["my-repo", "QuantEcon.manual"])
        
        assert matcher.matches("my-repo") is True
        assert matcher.matches("QuantEcon.manual") is True
        assert matcher.matches("other-repo") is False

    def test_combined_patterns_and_repositories(self):
        """Test combining patterns and exact repository names."""
        matcher = RepoMatcher(
            patterns=["lecture-.*"],
            repositories=["specific-repo", "another-repo"]
        )
        
        # Matches via pattern
        assert matcher.matches("lecture-python.myst") is True
        # Matches via exact name
        assert matcher.matches("specific-repo") is True
        assert matcher.matches("another-repo") is True
        # No match
        assert matcher.matches("other-repo") is False

    def test_filter_repositories(self, mock_github_client):
        """Test filtering repositories from an organization."""
        matcher = RepoMatcher(patterns=["lecture-.*"])
        
        repos = matcher.filter_repositories(mock_github_client, "quantecon")
        
        assert len(repos) == 2
        repo_names = [r.name for r in repos]
        assert "lecture-python.myst" in repo_names
        assert "lecture-julia" in repo_names

    def test_filter_multiple_patterns(self, mock_github_client):
        """Test filtering with multiple patterns."""
        matcher = RepoMatcher(patterns=["lecture-.*", "quantecon-.*"])
        
        repos = matcher.filter_repositories(mock_github_client, "quantecon")
        
        assert len(repos) == 3
        repo_names = [r.name for r in repos]
        assert "lecture-python.myst" in repo_names
        assert "lecture-julia" in repo_names
        assert "quantecon-notebooks-python" in repo_names

    def test_filter_with_exact_repositories(self, mock_github_client):
        """Test filtering with exact repository names."""
        matcher = RepoMatcher(repositories=["other-repo"])
        
        repos = matcher.filter_repositories(mock_github_client, "quantecon")
        
        assert len(repos) == 1
        assert repos[0].name == "other-repo"

    def test_no_matches(self, mock_github_client):
        """Test when no repositories match the patterns."""
        matcher = RepoMatcher(patterns=["nonexistent-.*"])
        
        repos = matcher.filter_repositories(mock_github_client, "quantecon")
        
        assert len(repos) == 0

    def test_warns_on_not_found_repositories(self, mock_github_client, caplog):
        """Test that a warning is logged for configured repos not found."""
        import logging
        
        matcher = RepoMatcher(repositories=["other-repo", "missing-repo"])
        
        with caplog.at_level(logging.WARNING):
            repos = matcher.filter_repositories(mock_github_client, "quantecon")
        
        # Should still return the repo that was found
        assert len(repos) == 1
        assert repos[0].name == "other-repo"
        
        # Should warn about the missing repo
        assert "missing-repo" in caplog.text
        assert "not found" in caplog.text.lower()

    def test_empty_patterns_and_repositories(self):
        """Test with empty pattern and repository lists."""
        matcher = RepoMatcher()
        
        assert matcher.matches("any-repo") is False
