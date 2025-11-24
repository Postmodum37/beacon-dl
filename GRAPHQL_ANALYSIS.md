# BeaconTV GraphQL API Reference

## Endpoint
`https://beacon.tv/api/graphql` (POST)

## Authentication
Cookie: `beacon-session` (obtained after SSO login)

```bash
curl 'https://beacon.tv/api/graphql' \
  -X POST -H 'content-type: application/json' \
  -b beacon_cookies.txt \
  -d '{"query": "..."}'
```

## Key Queries

### Get Latest Episodes
```graphql
query { Contents(limit: 10, sort: "-releaseDate") {
  docs { id title slug seasonNumber episodeNumber releaseDate duration
    primaryCollection { name slug } }
}}
```

### Search by Collection
```graphql
query { search(collection: "68caf69e7a76bce4b7aa689a", contentTypes: ["videoPodcast"], sort: "-releaseDate", limit: 5) {
  docs { id title slug seasonNumber episodeNumber releaseDate duration }
  totalDocs totalPages
}}
```
**Note**: Use collection ID, not slug.

### List All Series
```graphql
query { Collections(where: { isSeries: { equals: true } }, sort: "name") {
  docs { id name slug isSeries itemCount }
}}
```

## Known Series IDs
| Series | ID |
|--------|-----|
| Campaign 4 | `68caf69e7a76bce4b7aa689a` |
| Campaign 3: Bells Hells | `65b2548e78f89be87b4dbe9a` |
| Campaign 2: The Mighty Nein | `660676d5c1ffa829c389a4c7` |
| Candela Obscura | `66067a09c1ffa829c389a65e` |
| Exandria Unlimited | `662c3b58fd8fbf1731b32f48` |

Full cache (23 series) in `src/beacon_dl/graphql.py:COLLECTION_CACHE`

## Limitations
- `contentVideo.video.playlistUrl` returns `null` - video URLs not exposed (use yt-dlp)
- `ViewHistories` returns 403 Forbidden
- `meMember.user` returns `null`
- GraphQL variables in `where` clauses not supported (use literal values)

## Schema Types
**Content**: id, title, slug, description, seasonNumber, episodeNumber, duration (ms), releaseDate, contentType, primaryCollection

**Collection**: id, name, slug, isSeries, itemCount, isPodcast

## Architecture
- **GraphQL**: Content discovery, metadata, episode listings (~100ms)
- **yt-dlp**: Video downloads with cookies (required - video URLs not in API)
