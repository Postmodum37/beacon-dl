"""Tests for custom exception hierarchy."""

import pytest

from src.beacon_dl.exceptions import (
    AuthenticationError,
    BeaconError,
    ConfigurationError,
    ContentNotFoundError,
    DownloadError,
    GraphQLError,
    MergeError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test that exceptions follow proper inheritance."""

    def test_beacon_error_is_base(self):
        """Test BeaconError is the base exception."""
        error = BeaconError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_authentication_error_inherits_from_beacon_error(self):
        """Test AuthenticationError inherits from BeaconError."""
        error = AuthenticationError("auth failed")
        assert isinstance(error, BeaconError)
        assert isinstance(error, Exception)

    def test_content_not_found_error_inherits_from_beacon_error(self):
        """Test ContentNotFoundError inherits from BeaconError."""
        error = ContentNotFoundError("content not found")
        assert isinstance(error, BeaconError)

    def test_download_error_inherits_from_beacon_error(self):
        """Test DownloadError inherits from BeaconError."""
        error = DownloadError("download failed")
        assert isinstance(error, BeaconError)

    def test_merge_error_inherits_from_beacon_error(self):
        """Test MergeError inherits from BeaconError."""
        error = MergeError("ffmpeg failed")
        assert isinstance(error, BeaconError)

    def test_configuration_error_inherits_from_beacon_error(self):
        """Test ConfigurationError inherits from BeaconError."""
        error = ConfigurationError("invalid config")
        assert isinstance(error, BeaconError)

    def test_graphql_error_inherits_from_beacon_error(self):
        """Test GraphQLError inherits from BeaconError."""
        error = GraphQLError("query failed")
        assert isinstance(error, BeaconError)

    def test_validation_error_inherits_from_beacon_error(self):
        """Test ValidationError inherits from BeaconError."""
        error = ValidationError("invalid input")
        assert isinstance(error, BeaconError)


class TestExceptionCatching:
    """Test that exceptions can be caught properly."""

    def test_catch_all_beacon_errors(self):
        """Test catching all beacon-dl errors with BeaconError."""
        errors = [
            AuthenticationError("auth"),
            ContentNotFoundError("content"),
            DownloadError("download"),
            MergeError("merge"),
            ConfigurationError("config"),
            GraphQLError("graphql"),
            ValidationError("validation"),
        ]

        for error in errors:
            with pytest.raises(BeaconError):
                raise error

    def test_catch_specific_error(self):
        """Test catching specific error types."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("login failed")

        with pytest.raises(ContentNotFoundError):
            raise ContentNotFoundError("episode not found")

    def test_error_message_preserved(self):
        """Test that error messages are preserved."""
        message = "Detailed error message with context"
        error = DownloadError(message)
        assert str(error) == message
        assert message in repr(error)
