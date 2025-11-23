# BeaconTV GraphQL API

BeaconTV has a GraphQL API at `https://beacon.tv/api/graphql` that could be useful for future enhancements.

## Authentication

Requires:
- `Cookie: beacon-session=<session-token>` - Obtained after SSO login
- `authorization: Bearer <token>` - API token (appears in network requests)

## Example Queries

### Get User Profile

```graphql
query GetUserProfile {
  meMember {
    user {
      id
      username
      externalId
      activatedAt
      activeSubscription
      completedOnboarding
      planId
      dailyStreak
      tier {
        id
        name
        planLevel
      }
      profileImage {
        id
        name
        image {
          sizes {
            square {
              url
            }
          }
        }
      }
    }
  }
}
```

### Example cURL

```bash
curl 'https://beacon.tv/api/graphql' \
  -X POST \
  -H 'content-type: application/json' \
  -H 'Cookie: beacon-session=<your-session-cookie>' \
  -H 'authorization: Bearer <token>' \
  --data-raw '{
    "operationName":"GetUserProfile",
    "variables":{},
    "query":"query GetUserProfile { meMember { user { id username activeSubscription } } }"
  }'
```

## Potential Use Cases

### 1. Verify Authentication
- Check if user is logged in before attempting download
- Validate subscription status

### 2. Fetch Metadata
- Get series information
- Get episode lists
- Get video metadata (title, description, etc.)

### 3. Content Access Check
- Verify user has access to specific content
- Check tier/plan requirements

### 4. User Information
- Get user profile
- Check subscription status
- Get watch history

## Integration Ideas

### Replace Web Scraping
Currently we use Playwright to scrape:
- Latest episode URLs (`get_latest_episode_url()`)
- Episode metadata

Could be replaced with GraphQL queries for:
- Faster execution
- More reliable (no DOM changes)
- Less resource intensive (no browser)

### Enhanced Authentication
Instead of relying on cookie validation, could:
- Query user profile to verify login
- Check subscription tier before download
- Provide better error messages

### Future Features
- List all episodes in a series
- Download entire series
- Check for new episodes
- Download history tracking

## Implementation Notes

**Current approach (yt-dlp with cookies):**
- Works well for downloading
- No need to parse GraphQL responses
- yt-dlp handles all video logic

**GraphQL could enhance:**
- Metadata fetching (before yt-dlp)
- Authentication verification
- Series/episode discovery
- User preferences

## Next Steps

1. Reverse engineer more GraphQL queries from network tab
2. Document query schemas
3. Create optional GraphQL client wrapper
4. Use for metadata where beneficial
5. Keep yt-dlp for actual downloading

## Example Integration

```python
# Future enhancement
from .graphql import BeaconGraphQL

def get_series_episodes(series_url: str) -> list[str]:
    """Get all episode URLs from a series using GraphQL."""
    client = BeaconGraphQL(cookie_file="beacon_cookies.txt")

    # Query series ID from URL
    series_id = extract_series_id(series_url)

    # GraphQL query
    episodes = client.query("""
        query GetSeriesEpisodes($id: ID!) {
          series(id: $id) {
            episodes {
              id
              url
              title
            }
          }
        }
    """, variables={"id": series_id})

    return [ep["url"] for ep in episodes["series"]["episodes"]]
```

## References

- API Endpoint: `https://beacon.tv/api/graphql`
- GraphQL Browser: Check Network tab in browser DevTools
- Requires valid `beacon-session` cookie from SSO login

---

*Note: This API is not officially documented. Use responsibly and respect rate limits.*
