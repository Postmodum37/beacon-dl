"""Security tests for GraphQL client.

Tests GraphQL injection prevention and input validation.
"""

import pytest
from src.beacon_dl.graphql import validate_slug, BeaconGraphQL
from pathlib import Path


class TestGraphQLInjectionPrevention:
    """Test suite for GraphQL injection attack prevention."""

    def test_validate_slug_accepts_valid_slugs(self):
        """Test that valid slugs are accepted."""
        valid_slugs = [
            "campaign-4",
            "exu-calamity",
            "critical-role",
            "c4-e006-knives-and-thorns",
            "test_slug",
            "Test-Slug_123",
        ]

        for slug in valid_slugs:
            result = validate_slug(slug)
            assert result == slug

    def test_validate_slug_rejects_graphql_injection(self):
        """Test that GraphQL injection attempts are rejected."""
        malicious_slugs = [
            'test"}}}}queryMalicious{Collections{docs{id}}}',
            'test"; query Malicious',
            'test\\"}}',
            "test' OR '1'='1",
            'test"; DROP TABLE users; --',
        ]

        for slug in malicious_slugs:
            with pytest.raises(ValueError, match="Invalid.*slug"):
                validate_slug(slug)

    def test_validate_slug_rejects_shell_metacharacters(self):
        """Test that shell metacharacters are rejected."""
        malicious_slugs = [
            "test; rm -rf /",
            "test | cat /etc/passwd",
            "test && wget malware.sh",
            "test`whoami`",
            "test$(whoami)",
            "test&background",
            "test>output.txt",
            "test<input.txt",
        ]

        for slug in malicious_slugs:
            with pytest.raises(ValueError, match="Invalid"):
                validate_slug(slug)

    def test_validate_slug_rejects_path_traversal(self):
        """Test that path traversal attempts are rejected."""
        malicious_slugs = [
            "../etc/passwd",
            "../../secret",
            "..\\windows\\system32",
            "./../test",
        ]

        for slug in malicious_slugs:
            with pytest.raises(ValueError, match="Invalid"):
                validate_slug(slug)

    def test_validate_slug_rejects_special_chars(self):
        """Test that special characters are rejected."""
        malicious_slugs = [
            "test@domain.com",
            "test#hashtag",
            "test$variable",
            "test%percent",
            "test^caret",
            "test*wildcard",
            "test(parenthesis)",
            "test[bracket]",
            "test{brace}",
            "test+plus",
            "test=equals",
            "test?question",
            "test!exclaim",
            "test~tilde",
            "test'quote",
            'test"doublequote',
            "test\\backslash",
            "test/slash",
            "test:colon",
            "test;semicolon",
            "test,comma",
        ]

        for slug in malicious_slugs:
            with pytest.raises(ValueError, match="Invalid"):
                validate_slug(slug, "test_field")

    def test_validate_slug_enforces_max_length(self):
        """Test that excessively long slugs are rejected (DoS protection)."""
        long_slug = "a" * 201  # Max is 200

        with pytest.raises(ValueError, match="too long"):
            validate_slug(long_slug)

    def test_validate_slug_rejects_empty_string(self):
        """Test that empty slugs are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_slug("")

    def test_validate_slug_custom_field_name_in_error(self):
        """Test that custom field names appear in error messages."""
        with pytest.raises(ValueError, match="custom_field"):
            validate_slug("invalid@slug", "custom_field")


class TestGraphQLClientSecurity:
    """Test GraphQL client security features."""

    def test_get_collection_id_validates_slug(self, tmp_path):
        """Test that _get_collection_id validates slugs."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n")

        client = BeaconGraphQL(cookie_file)

        # Should raise ValueError for invalid slug
        with pytest.raises(ValueError, match="Invalid"):
            client._get_collection_id('test"; query Malicious')

    def test_get_content_by_slug_validates_slug(self, tmp_path):
        """Test that get_content_by_slug validates slugs."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n")

        client = BeaconGraphQL(cookie_file)

        # Should raise ValueError for invalid slug
        with pytest.raises(ValueError, match="Invalid"):
            client.get_content_by_slug('test"; DROP TABLE')

    def test_get_latest_episode_validates_slug(self, tmp_path):
        """Test that get_latest_episode handles invalid slugs gracefully."""
        cookie_file = tmp_path / "cookies.txt"
        cookie_file.write_text("# Netscape HTTP Cookie File\n")

        client = BeaconGraphQL(cookie_file)

        # get_latest_episode catches ValueError and returns None
        # The validation happens in _get_collection_id, which is called internally
        result = client.get_latest_episode('test"; query Evil')
        assert result is None  # Invalid slug causes None return, not exception


@pytest.mark.security
class TestConfigValidationSecurity:
    """Test configuration validation prevents injection."""

    def test_release_group_rejects_shell_metacharacters(self):
        """Test that release_group validates input."""
        from src.beacon_dl.config import Settings

        with pytest.raises(ValueError, match="Invalid value"):
            Settings(release_group="; rm -rf /")

    def test_container_format_only_allows_whitelisted_formats(self):
        """Test that container_format uses whitelist."""
        from src.beacon_dl.config import Settings

        with pytest.raises(ValueError, match="Unsupported format"):
            Settings(container_format="exe")

    def test_resolution_validates_format(self):
        """Test that preferred_resolution validates format."""
        from src.beacon_dl.config import Settings

        with pytest.raises(ValueError, match="Invalid resolution"):
            Settings(preferred_resolution="malicious")

    def test_audio_channels_validates_format(self):
        """Test that default_audio_channels validates format."""
        from src.beacon_dl.config import Settings

        with pytest.raises(ValueError, match="Invalid audio channels"):
            Settings(default_audio_channels="evil")
