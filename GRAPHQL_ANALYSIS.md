# BeaconTV GraphQL API Analysis

## Summary

Successfully discovered and tested the BeaconTV GraphQL API at `https://beacon.tv/api/graphql`. The API provides rich content metadata and can significantly improve the downloader by replacing web scraping with direct API calls.

## Authentication

**Works with**: beacon-session cookie only (no additional Bearer token required)

```bash
curl 'https://beacon.tv/api/graphql' \
  -X POST \
  -H 'content-type: application/json' \
  -b beacon_cookies.txt \
  -d '{"query": "..."}'
```

## Key Queries Discovered

### 1. List Latest Content (`Contents`)

**Use case**: Replace Playwright scraping for "latest episode" feature

```graphql
query GetLatestEpisodes {
  Contents(
    limit: 10
    sort: "-releaseDate"
  ) {
    docs {
      id
      title
      slug
      seasonNumber
      episodeNumber
      releaseDate
      duration
      primaryCollection {
        name
        slug
      }
    }
  }
}
```

**Response example**:
```json
{
  "data": {
    "Contents": {
      "docs": [
        {
          "id": "691f59778e6c004863e24ba1",
          "title": "C4 E007 | On the Scent",
          "slug": "c4-e007-on-the-scent",
          "seasonNumber": 4,
          "episodeNumber": 7,
          "releaseDate": "2025-11-21T03:00:00.000Z",
          "duration": 13949000,
          "primaryCollection": {
            "name": "Campaign 4",
            "slug": "campaign-4"
          }
        }
      ]
    }
  }
}
```

### 2. Get Series Episodes (`Contents` with filter)

**Use case**: List all episodes in a series for batch downloads

```graphql
query GetSeriesEpisodes($collectionId: String!) {
  Contents(
    where: { primaryCollection: { equals: $collectionId } }
    sort: "seasonNumber,episodeNumber"
    limit: 100
  ) {
    docs {
      id
      title
      slug
      seasonNumber
      episodeNumber
      releaseDate
      duration
      description
    }
  }
}
```

**Variables**:
```json
{
  "collectionId": "68caf69e7a76bce4b7aa689a"
}
```

### 3. Get Content by Slug (`Contents` with slug filter)

**Use case**: Convert URL slug to content ID and metadata

```graphql
query GetContentBySlug($slug: String!) {
  Contents(
    where: { slug: { equals: $slug } }
    limit: 1
  ) {
    docs {
      id
      title
      slug
      seasonNumber
      episodeNumber
      releaseDate
      duration
      description
      primaryCollection {
        name
        slug
      }
    }
  }
}
```

**Variables**:
```json
{
  "slug": "c4-e006-knives-and-thorns"
}
```

### 4. Get Specific Content (`Content`)

**Use case**: Get full metadata for a specific episode

```graphql
query GetContent($id: String!) {
  Content(id: $id) {
    id
    title
    slug
    description
    seasonNumber
    episodeNumber
    aggregateEpisodeNumber
    duration
    releaseDate
    contentType
    primaryCollection {
      id
      name
      slug
      isSeries
    }
  }
}
```

**Variables**:
```json
{
  "id": "691f59778e6c004863e24ba1"
}
```

### 5. Get Collection Info (`Collection`)

**Use case**: Get series metadata and episode count

```graphql
query GetCollection($id: String!) {
  Collection(id: $id) {
    id
    name
    slug
    isSeries
    itemCount
    category {
      name
    }
  }
}
```

**Response example**:
```json
{
  "data": {
    "Collection": {
      "id": "68caf69e7a76bce4b7aa689a",
      "name": "Campaign 4",
      "slug": "campaign-4",
      "isSeries": true,
      "itemCount": 12
    }
  }
}
```

### 6. List All Collections (`Collections`)

**Use case**: Browse all available series

```graphql
query GetCollections {
  Collections(
    where: { isSeries: { equals: true } }
    sort: "name"
  ) {
    docs {
      id
      name
      slug
      isSeries
      itemCount
    }
  }
}
```

## Key Schema Types

### Content Type
```
id: String!
title: String
slug: String
description: String
seasonNumber: Int
episodeNumber: Int
aggregateEpisodeNumber: Int
duration: Int (milliseconds)
releaseDate: DateTime
contentType: String ("videoPodcast", etc.)
primaryCollection: Collection
collections: [Collection]
contentVideo: Content_ContentVideo
```

### Collection Type
```
id: String!
name: String
slug: String
isSeries: Boolean
itemCount: Int
category: Category
```

## Proposed Integration Plan

### 1. Replace Web Scraping (HIGH PRIORITY)

**Current**: Playwright scrapes series page to find latest episode URL
**Proposed**: Use GraphQL `Contents` query with collection filter

**Benefits**:
- **Faster**: ~100ms vs ~3-5 seconds (Playwright)
- **More reliable**: No DOM breakage risk
- **Less resource intensive**: No browser overhead
- **Better metadata**: Get episode number, duration, release date directly

**Implementation**:
```python
# src/beacon_dl/graphql.py (NEW)
from typing import Optional, Dict, Any, List
import requests

class BeaconGraphQL:
    """GraphQL client for beacon.tv API"""

    def __init__(self, cookie_file: Path):
        self.endpoint = "https://beacon.tv/api/graphql"
        self.cookies = self._load_cookies(cookie_file)

    def get_latest_episode(self, collection_slug: str = "campaign-4") -> Optional[Dict[str, Any]]:
        """Get latest episode from a series"""
        collection_id = self._get_collection_id(collection_slug)

        query = """
        query GetLatestEpisode($collectionId: String!) {
          Contents(
            where: {
              primaryCollection: { equals: $collectionId }
              seasonNumber: { not_equals: null }
              episodeNumber: { not_equals: null }
            }
            sort: "-releaseDate"
            limit: 1
          ) {
            docs {
              id
              title
              slug
              seasonNumber
              episodeNumber
              releaseDate
              duration
            }
          }
        }
        """

        response = self._query(query, {"collectionId": collection_id})
        docs = response.get("data", {}).get("Contents", {}).get("docs", [])
        return docs[0] if docs else None

    def get_content_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get content metadata by URL slug"""
        query = """
        query GetContentBySlug($slug: String!) {
          Contents(where: { slug: { equals: $slug } }, limit: 1) {
            docs {
              id
              title
              slug
              seasonNumber
              episodeNumber
              releaseDate
              duration
              description
              primaryCollection {
                name
                slug
              }
            }
          }
        }
        """

        response = self._query(query, {"slug": slug})
        docs = response.get("data", {}).get("Contents", {}).get("docs", [])
        return docs[0] if docs else None

    def get_series_episodes(self, collection_slug: str) -> List[Dict[str, Any]]:
        """Get all episodes in a series"""
        collection_id = self._get_collection_id(collection_slug)

        query = """
        query GetSeriesEpisodes($collectionId: String!) {
          Contents(
            where: { primaryCollection: { equals: $collectionId } }
            sort: "seasonNumber,episodeNumber"
            limit: 200
          ) {
            docs {
              id
              title
              slug
              seasonNumber
              episodeNumber
              releaseDate
              duration
            }
          }
        }
        """

        response = self._query(query, {"collectionId": collection_id})
        return response.get("data", {}).get("Contents", {}).get("docs", [])
```

### 2. Enhanced Metadata Extraction

**Current**: yt-dlp metadata extraction
**Proposed**: Use GraphQL for initial metadata, fallback to yt-dlp

**Benefits**:
- Episode numbers more reliable (direct from API)
- Series name always correct
- Release dates available
- Duration information

### 3. New Features Enabled

#### 3.1. Batch Download Series
```bash
# Download entire Campaign 4
beacon-dl --series campaign-4 --batch-download

# Download specific episode range
beacon-dl --series campaign-4 --episodes 1-10
```

#### 3.2. List Available Series
```bash
# List all available series
beacon-dl --list-series

# Output:
# - Campaign 4 (12 episodes)
# - Campaign 3 (115 episodes)
# - Exandria Unlimited: Calamity (4 episodes)
# ...
```

#### 3.3. List Episodes in Series
```bash
# List all episodes in Campaign 4
beacon-dl --series campaign-4 --list-episodes

# Output:
# C4 E001 | The Fall of Thjazi Fang (2025-10-03)
# C4 E002 | Broken Wing (2025-10-10)
# ...
```

#### 3.4. Check for New Episodes
```bash
# Check if new episodes are available
beacon-dl --check-new

# Output:
# ✓ New episode available: C4 E007 | On the Scent (2025-11-21)
```

### 4. Improved Latest Episode Logic

**Current approach** (Playwright):
```python
# src/beacon_dl/utils.py:get_latest_episode_url()
# 1. Launch Playwright browser (3-5 seconds)
# 2. Navigate to series page
# 3. Wait for page load
# 4. Parse DOM to find episode links
# 5. Extract first link
# 6. Close browser
```

**Proposed approach** (GraphQL):
```python
# src/beacon_dl/graphql.py:get_latest_episode()
# 1. Make GraphQL query (~100ms)
# 2. Parse JSON response
# 3. Return episode metadata
```

**Performance improvement**: ~30-50x faster

## Implementation Roadmap

### Phase 1: Core GraphQL Client (Week 1)
- [ ] Create `src/beacon_dl/graphql.py` module
- [ ] Implement `BeaconGraphQL` class with cookie auth
- [ ] Add methods: `get_latest_episode()`, `get_content_by_slug()`
- [ ] Add error handling and retries
- [ ] Write unit tests

### Phase 2: Replace Playwright Scraping (Week 1)
- [ ] Update `utils.py:get_latest_episode_url()` to use GraphQL
- [ ] Keep Playwright as fallback if GraphQL fails
- [ ] Test with multiple series (Campaign 4, EXU Calamity, etc.)
- [ ] Update tests

### Phase 3: Enhanced Features (Week 2)
- [ ] Implement `--list-series` command
- [ ] Implement `--list-episodes` command
- [ ] Implement `--batch-download` for entire series
- [ ] Implement `--check-new` for new episode detection
- [ ] Add episode range support (e.g., `--episodes 1-10`)

### Phase 4: Metadata Enhancement (Week 2)
- [ ] Use GraphQL metadata as primary source
- [ ] Fallback to yt-dlp if GraphQL fails
- [ ] Improve filename generation with GraphQL data
- [ ] Add series name normalization

## Testing Notes

### Collection IDs (discovered):
- Campaign 4: `68caf69e7a76bce4b7aa689a`

### Episode Slugs (tested):
- C4 E006: `c4-e006-knives-and-thorns` → ID: `6914e32be6f4eb512d3a61f4`
- C4 E007: `c4-e007-on-the-scent` → ID: `691f59778e6c004863e24ba1`

### URL to Slug Conversion:
```
https://beacon.tv/content/c4-e006-knives-and-thorns
                         ^^^^^^^^^^^^^^^^^^^^^^^^
                         slug
```

### Authentication Notes:
- `meUser` query returns null for all fields (expected - session-only auth)
- Content queries work fine with beacon-session cookie
- No Bearer token required for content queries

## Limitations Discovered

1. **No video URLs**: GraphQL doesn't expose video playback URLs (still need yt-dlp)
2. **No user info**: `meUser` returns null (session-based, no user profile access)
3. **contentVideo is null**: Video metadata not available via GraphQL (use yt-dlp)

## Conclusion

The GraphQL API provides excellent metadata for content discovery but doesn't replace yt-dlp for actual video downloads. The ideal architecture is:

**GraphQL**: Content discovery, metadata, episode listings
**yt-dlp**: Video downloads with cookies

This hybrid approach gives us the best of both worlds:
- Fast, reliable content discovery (GraphQL)
- Robust video downloading (yt-dlp)
