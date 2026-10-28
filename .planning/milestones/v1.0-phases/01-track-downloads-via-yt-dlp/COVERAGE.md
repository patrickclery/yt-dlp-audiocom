# API Coverage — audio.com (api.audio.com)

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

Phase 1 integrates two undocumented, unauthenticated endpoints: `GET /oembed?url=` and `GET /audio/<id>`. The documented OAuth `v1` API is listed so that its exclusion is a decision on record and not an omission.

| capability | decision | reason |
|---|---|---|
| oembed-resolve-slug-to-id | INTEGRATE | |
| audio-get-track-json | INTEGRATE | |
| audio-transcodings-to-formats | INTEGRATE | |
| audio-title-description | INTEGRATE | |
| audio-uploader-username-author | INTEGRATE | |
| audio-date-created-timestamp | INTEGRATE | |
| audio-tags | INTEGRATE | |
| audio-stats-counts | INTEGRATE | |
| audio-image-avatar-thumbnail | INTEGRATE | |
| audio-original-upload-files | OPT-OUT | not needed yet: offered only when is_downloadable, in Phase 2 (EXTR-04) |
| audio-is-downloadable-flag | OPT-OUT | not needed yet: consumed by Phase 2 (EXTR-04) |
| audio-error-responses-private-removed | OPT-OUT | not needed yet: error mapping is Phase 2 (EXTR-06) |
| audio-waveform | OPT-OUT | not needed: no yt-dlp info-dict field consumes it |
| audio-license-price-category-caption | OPT-OUT | not needed: no requirement maps these fields |
| audio-comments | OPT-OUT | not needed: no requirement for comment extraction |
| html-track-page-scrape | OPT-OUT | explicitly out of scope: Cloudflare-challenged. The oEmbed-to-API path replaces it |
| embed-player-urls | OPT-OUT | explicitly out of scope: deferred to v2 (EXTR-09) |
| collections-playlists | OPT-OUT | explicitly out of scope: deferred to v2 (EXTR-07) |
| user-profile-track-listing | OPT-OUT | explicitly out of scope: deferred to v2 (EXTR-08) |
| site-search | OPT-OUT | not needed: the extractor is URL-driven |
| v1-audio-create-update-delete-image-create | OPT-OUT | explicitly out of scope: OAuth API write operations on the logged-in user's own tracks |
| v1-audio-list-view-stats | OPT-OUT | explicitly out of scope: OAuth API exposes only the logged-in user's own tracks |
| v1-collection-crud-and-items | OPT-OUT | explicitly out of scope: OAuth API, and collections are v2 |
| v1-embed-create | OPT-OUT | explicitly out of scope: OAuth API write operation |
| v1-search | OPT-OUT | explicitly out of scope: OAuth API, and the extractor is URL-driven |
