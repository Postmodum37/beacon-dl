# Changelog

All notable changes to the beacon-tv-downloader Python implementation.

## [Unreleased] - 2025-11-23

### Fixed - SSO Authentication (CRITICAL FIX)

**The Missing Piece:** After logging into `members.beacon.tv`, we must trigger SSO on `beacon.tv` by clicking the Login button.

#### Final Root Cause
- BeaconTV uses **two separate domains** with independent authentication:
  - `members.beacon.tv` - Account management
  - `beacon.tv` - Content streaming
- Logging into one does NOT automatically create a session on the other
- The `beacon-session` cookie (required for downloads) is only set after SSO is triggered

#### Final Solution
Added SSO trigger in `src/beacon_dl/auth.py:250-286`:
1. Login to `members.beacon.tv` ✅
2. Navigate to `beacon.tv` homepage
3. **Click "Login" button** - triggers SSO flow
4. SSO recognizes existing members.beacon.tv session
5. Creates `beacon-session` cookie on beacon.tv ✅

**Additional improvements:**
- Clears persistent browser profile before login (fresh session every time)
- Validates beacon-session cookie exists after login
- Better debug logging with screenshots at each step

#### Result
```bash
beacon-dl --username user@example.com --password yourpassword
# ✅ Now works perfectly!
```

---

## [Previous] - 2025-01-23

### Fixed - Cookie Authentication (Partial)

#### Root Cause
The Python implementation was failing to authenticate with BeaconTV because:
- Playwright logged into `members.beacon.tv` successfully
- BUT those cookies didn't work for `beacon.tv` (where content is hosted)
- Cookie duplication logic was broken
- Authentication priority was backwards (browser cookies first, Playwright last)

#### Solution
**1. Fixed Playwright Cookie Capture** (`src/beacon_dl/auth.py:80-100`)
- After login to members.beacon.tv, now navigates to:
  - `https://beacon.tv` (homepage) - triggers cross-domain cookies
  - `https://beacon.tv/content` - ensures content-specific cookies
  - Target URL (if provided) - captures page-specific cookies
- Proper wait times between navigations (3-5 seconds)
- Captures cookies from ALL beacon.tv domains (not just members.beacon.tv)
- Shows debug info about which domains cookies were captured from

**2. Fixed Cookie Writing** (`src/beacon_dl/auth.py:266-328`)
- Removed broken cookie duplication logic
- Now writes actual captured cookies from both domains
- Filters only beacon.tv related cookies
- Shows summary of cookies written (members.beacon.tv vs beacon.tv)

**3. Fixed Authentication Priority** (`src/beacon_dl/auth.py:330-420`)
- **NEW PRIORITY** (correct):
  1. Playwright login (username/password) - PRIMARY method
  2. Configured browser profile - fallback
  3. Auto-detected browser profile - last resort
- **OLD PRIORITY** (broken):
  1. Browser cookies first
  2. Playwright login last

### Added - Cookie Validation

**Cookie Validation Function** (`src/beacon_dl/auth.py:11-96`)
- Validates cookie file exists and is readable
- Checks for non-expired cookies
- **CRITICAL**: Verifies beacon.tv domain cookies exist (required for downloads)
- Shows detailed validation report:
  - Total cookies count
  - beacon.tv cookies count
  - members.beacon.tv cookies count
  - Expired cookies warning
- Integrated into login flow - validates after capturing cookies

### Added - Debug Mode

**Configuration** (`src/beacon_dl/config.py:25`)
- Added `DEBUG` environment variable
- Default: false (headless mode)

**CLI Flag** (`src/beacon_dl/main.py:18`)
- Added `--debug` flag to CLI
- Shows verbose output
- Makes Playwright browser visible (not headless)
- Shows exception stack traces on errors

**Debug Features** (`src/beacon_dl/auth.py:106-109`)
- Browser runs headless by default
- In debug mode: shows browser window
- Prints debug information about domains captured

### Added - Error Handling

**Main CLI** (`src/beacon_dl/main.py:26-61`)
- Try-catch block wraps entire download flow
- Graceful KeyboardInterrupt handling (exit code 130)
- Exception handling with error messages
- Stack trace in debug mode (`console.print_exception()`)

### Added - Test Suite

**Test Infrastructure** (`pyproject.toml:16-30`)
- Added pytest as dev dependency
- Added pytest-cov for coverage reports
- Configured pytest with sensible defaults

**Test Files**:
- `tests/test_auth.py` - Authentication and cookie validation tests
- `tests/test_utils.py` - Filename sanitization and language mapping tests
- `tests/README.md` - Test documentation and instructions

**Test Coverage**:
- Cookie validation (empty file, expired cookies, valid cookies, etc.)
- Authentication priority (Playwright first, browser fallback)
- Configuration settings
- Filename sanitization
- Language to ISO code mapping

### Improved - Documentation

**CLAUDE.md Updates**:
- Fixed description: "Playwright authentication (primary)" instead of "fallback"
- Updated auth.py module description with new line numbers and features
- Corrected authentication flow documentation
- Added detailed authentication priority explanation
- Added "Why Playwright is Primary" section
- Updated configuration section with DEBUG option
- Updated main.py description with debug flag
- Updated usage examples to show Playwright as primary method

**Usage Examples**:
- Emphasize username/password method (recommended)
- Show debug mode usage
- Show environment variable usage for Docker

### Improved - Code Quality

**Type Hints** (`src/beacon_dl/auth.py:2`)
- Added `Any` type import for better type hints
- Improved `_write_netscape_cookies` signature: `list[dict[str, Any]]`
- Added return type `-> None` to internal functions
- Better type safety throughout

**Docstrings** (`src/beacon_dl/auth.py`):
- Comprehensive docstrings for all functions
- Added detailed descriptions of functionality
- Added Args, Returns, Raises, Example, and Note sections
- Explained BeaconTV's cross-domain authentication
- Documented Netscape cookie format
- Added authentication priority details in docstring
- Examples showing actual usage

**Code Organization**:
- Removed obsolete TODO comments
- Consistent formatting
- Clear separation of concerns
- Better variable names

## Summary

### What was broken:
❌ Playwright authentication didn't work (cookie cross-domain issue)
❌ Authentication priority was backwards
❌ No cookie validation
❌ No debug mode
❌ No error handling
❌ No tests
❌ Documentation was incorrect

### What's fixed:
✅ Playwright authentication works properly (PRIMARY method)
✅ Correct authentication priority (Playwright → browser cookies)
✅ Cookie validation with detailed reporting
✅ Debug mode with visible browser and verbose output
✅ Proper error handling and graceful exits
✅ Comprehensive test suite
✅ Accurate documentation
✅ Improved type hints and docstrings

### How to use the fixed implementation:

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"

# Download with Playwright authentication (recommended)
beacon-dl --username user@example.com --password yourpassword

# Debug mode (shows browser window)
beacon-dl --username user@example.com --password yourpassword --debug

# Run tests
pytest

# Run with coverage
pytest --cov=src/beacon_dl --cov-report=html
```

### Architecture improvements:
- Modern Python package structure
- Type-safe configuration with Pydantic
- Rich console for beautiful terminal output
- Proper error handling and user feedback
- Test coverage for critical functionality
- Comprehensive documentation
- Debug mode for troubleshooting

The Python implementation is now production-ready and more reliable than the bash script for automated/Docker environments!
