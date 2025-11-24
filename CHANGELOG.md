# Changelog

## [2025-11-24] GraphQL Integration & Security Hardening

### Added
- **GraphQL API client** (`src/beacon_dl/graphql.py`) - 30-50x faster than Playwright scraping
- **New CLI commands**: `list-series`, `list-episodes`, `check-new`, `batch-download`
- **23 series IDs cached** for instant lookups
- **Constants module** (`constants.py`) - Centralized configuration values
- **Domain models** (`models.py`) - Type-safe data objects

### Fixed
- **GraphQL injection vulnerability** - Input validation on all slugs
- **Insecure file permissions** - Cookie files now 600 (owner-only)
- **Password screenshot exposure** - Removed debug screenshots after credential entry
- **Environment variable injection** - Pydantic validators on all user inputs

### Improved
- Test suite: 12 → 82 tests
- Coverage: 25% → 46%

## [2025-11-23] SSO Authentication Fix

### Fixed
- **SSO authentication** - Must click Login button on beacon.tv after members.beacon.tv login
- BeaconTV uses two separate domains with independent authentication
- `beacon-session` cookie only created after SSO trigger

### Added
- Debug mode (`--debug`) - Shows browser window, verbose output
- Cookie validation with detailed reporting
- Comprehensive test suite (34 tests)

## [Initial] Python CLI Implementation

- Python package with Playwright authentication
- Automatic latest episode fetching
- Multi-format episode detection (C4 E006, S04E06, 4x06)
- All subtitle tracks with ISO 639-2 language mapping
- Same output format as bash script
