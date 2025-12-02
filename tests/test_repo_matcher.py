"""Unit tests for RepoMatcher."""

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
            patterns=["lecture-.*"], repositories=["specific-repo", "another-repo"]
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

    def test_exclude_archived_default_false(self):
        """Test that exclude_archived defaults to False."""
        matcher = RepoMatcher(patterns=["lecture-.*"])

        assert matcher.exclude_archived is False

    def test_exclude_archived_set_true(self):
        """Test setting exclude_archived to True."""
        matcher = RepoMatcher(patterns=["lecture-.*"], exclude_archived=True)

        assert matcher.exclude_archived is True

    def test_filter_excludes_archived_repos(self, mock_github_client_with_archived):
        """Test that archived repos are excluded when exclude_archived=True."""
        matcher = RepoMatcher(patterns=["lecture-.*"], exclude_archived=True)

        repos = matcher.filter_repositories(mock_github_client_with_archived, "quantecon")

        # lecture-julia is archived and should be excluded
        # Only lecture-python.myst should match
        assert len(repos) == 1
        repo_names = [r.name for r in repos]
        assert "lecture-python.myst" in repo_names
        assert "lecture-julia" not in repo_names

    def test_filter_includes_archived_repos_by_default(self, mock_github_client_with_archived):
        """Test that archived repos are included when exclude_archived=False (default)."""
        matcher = RepoMatcher(patterns=["lecture-.*"], exclude_archived=False)

        repos = matcher.filter_repositories(mock_github_client_with_archived, "quantecon")

        # Both lecture repos should match (including archived lecture-julia)
        assert len(repos) == 2
        repo_names = [r.name for r in repos]
        assert "lecture-python.myst" in repo_names
        assert "lecture-julia" in repo_names

    def test_exclude_archived_logs_count(self, mock_github_client_with_archived, caplog):
        """Test that excluding archived repos logs the count."""
        import logging

        matcher = RepoMatcher(patterns=[".*"], exclude_archived=True)

        with caplog.at_level(logging.INFO):
            repos = matcher.filter_repositories(mock_github_client_with_archived, "quantecon")

        # Should log excluding 2 archived repos
        assert "Excluding 2 archived repositories" in caplog.text
        # Should have 2 repos remaining (4 total - 2 archived)
        assert len(repos) == 2

    def test_is_excluded_by_exact_name(self):
        """Test excluding repositories by exact name."""
        matcher = RepoMatcher(patterns=["lecture-.*"], exclude_repositories=["lecture-julia"])

        assert matcher.is_excluded("lecture-julia") is True
        assert matcher.is_excluded("lecture-python.myst") is False
        assert matcher.is_excluded("other-repo") is False

    def test_is_excluded_by_pattern(self):
        """Test excluding repositories by pattern."""
        matcher = RepoMatcher(patterns=[".*"], exclude_patterns=[".*-test$", "test-.*"])

        assert matcher.is_excluded("my-repo-test") is True
        assert matcher.is_excluded("test-repo") is True
        assert matcher.is_excluded("my-repo") is False

    def test_filter_with_exclude_repositories(self, mock_github_client):
        """Test filtering with exclude_repositories."""
        matcher = RepoMatcher(patterns=["lecture-.*"], exclude_repositories=["lecture-julia"])

        repos = matcher.filter_repositories(mock_github_client, "quantecon")

        # lecture-julia should be excluded
        assert len(repos) == 1
        repo_names = [r.name for r in repos]
        assert "lecture-python.myst" in repo_names
        assert "lecture-julia" not in repo_names

    def test_filter_with_exclude_patterns(self, mock_github_client):
        """Test filtering with exclude_patterns."""
        matcher = RepoMatcher(
            patterns=[".*"],  # Match all
            exclude_patterns=["lecture-.*"],  # But exclude lecture repos
        )

        repos = matcher.filter_repositories(mock_github_client, "quantecon")

        # lecture repos should be excluded
        repo_names = [r.name for r in repos]
        assert "lecture-python.myst" not in repo_names
        assert "lecture-julia" not in repo_names
        assert "quantecon-notebooks-python" in repo_names
        assert "other-repo" in repo_names

    def test_filter_with_combined_excludes(self, mock_github_client):
        """Test filtering with both exclude_patterns and exclude_repositories."""
        matcher = RepoMatcher(
            patterns=[".*"],  # Match all
            exclude_patterns=["lecture-.*"],
            exclude_repositories=["other-repo"],
        )

        repos = matcher.filter_repositories(mock_github_client, "quantecon")

        # Only quantecon-notebooks-python should remain
        assert len(repos) == 1
        assert repos[0].name == "quantecon-notebooks-python"

    def test_exclude_logs_count(self, mock_github_client, caplog):
        """Test that excluding repos logs the count."""
        import logging

        matcher = RepoMatcher(patterns=[".*"], exclude_patterns=["lecture-.*"])

        with caplog.at_level(logging.INFO):
            matcher.filter_repositories(
                mock_github_client, "quantecon"
            )  # Result intentionally unused

        # Should log excluding 2 repos (lecture-python.myst and lecture-julia)
        assert "Excluded 2 repositories by exclude rules" in caplog.text
