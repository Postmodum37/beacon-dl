# Tests

This directory contains tests for the beacon-tv-downloader Python package.

## Running Tests

### Install test dependencies

```bash
# With uv
uv pip install -e ".[dev]"

# With pip
pip install -e ".[dev]"
```

### Run all tests

```bash
pytest
```

### Run with coverage report

```bash
pytest --cov=src/beacon_dl --cov-report=html
```

### Run specific test file

```bash
pytest tests/test_auth.py
pytest tests/test_utils.py
```

### Run specific test

```bash
pytest tests/test_auth.py::TestCookieValidation::test_validate_cookies_valid_beacon_tv_cookies
```

## Test Structure

- `test_auth.py` - Tests for authentication module
  - Cookie validation tests
  - Authentication priority tests
  - Settings configuration tests

- `test_utils.py` - Tests for utility functions
  - Filename sanitization tests
  - Language mapping tests
  - Browser detection tests

## Writing New Tests

- Follow pytest conventions
- Use descriptive test names
- Add docstrings to test functions
- Group related tests in classes
- Mock external dependencies (filesystem, network, etc.)

## Coverage

Tests aim for high coverage of critical functionality:
- Authentication logic
- Cookie validation
- Configuration management
- Filename sanitization
- Language mapping

Integration tests for Playwright and yt-dlp are minimal to avoid dependencies on external services.
