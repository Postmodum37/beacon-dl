"""Custom exceptions for beacon-dl.

This module provides a hierarchy of exceptions for better error handling
and clearer error messages throughout the application.
"""


class BeaconError(Exception):
    """Base exception for all beacon-dl errors.

    All custom exceptions in beacon-dl inherit from this class,
    making it easy to catch all beacon-dl specific errors.
    """

    pass


class AuthenticationError(BeaconError):
    """Raised when authentication fails.

    Examples:
        - Invalid username/password
        - Expired session
        - Missing cookies
        - Login page not accessible
    """

    pass


class ContentNotFoundError(BeaconError):
    """Raised when requested content cannot be found.

    Examples:
        - Invalid slug
        - Episode doesn't exist
        - Series not found
    """

    pass


class DownloadError(BeaconError):
    """Raised when a download operation fails.

    Examples:
        - Network error during download
        - File write failure
        - Incomplete download
    """

    pass


class MergeError(BeaconError):
    """Raised when ffmpeg merge operation fails.

    Examples:
        - ffmpeg not installed
        - Invalid input files
        - Codec incompatibility
    """

    pass


class ConfigurationError(BeaconError):
    """Raised when configuration is invalid.

    Examples:
        - Invalid resolution format
        - Unknown container format
        - Invalid path
    """

    pass


class GraphQLError(BeaconError):
    """Raised when a GraphQL query fails.

    Examples:
        - API returned errors
        - Invalid query
        - Rate limited
    """

    pass


class ValidationError(BeaconError):
    """Raised when input validation fails.

    Examples:
        - Invalid slug format
        - Invalid URL
        - Invalid filename characters
    """

    pass
