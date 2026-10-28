# Architecture Research

**Domain:** yt-dlp extractor (+ plugin packaging) for audio.com single-track pages
**Researched:** 2026-10-28
**Confidence:** HIGH (every endpoint below was exercised live on 2026-10-28; an end-to-end prototype downloaded the reference track)

## Headline Findings

1. **You do not need impersonation.** The Cloudflare challenge only guards the `audio.com` HTML host (and `/embed/...`). `api.audio.com` is **not** challenged: plain `curl`, a `python-requests` UA and a Firefox UA all got HTTP 200. The media host (`s3.ustatik.com`, Wasabi S3 behind Cloudflare) also serves plain requests (HTTP 206 on Range).
2. **audio.com is not Next.js.** No `__NEXT_DATA__`. It is a server-rendered shell with a React SPA; page state is an HTML-escaped JSON blob in `<div class="js-store" data-content="...">`. Irrelevant for the primary path, but it is the fallback.
3. **The stream is a direct, pre-signed HTTPS file (MP3 and M4A/AAC).** No HLS/DASH. S3 SigV4 query-string signature, `X-Amz-Expires=518400` (6 days).
4. **Slug URL to numeric ID is the one tricky step.** The slug URL does not contain the track ID, and the API has no slug lookup. `GET https://api.audio.com/oembed?url=<canonical page URL>` returns the ID inside `iframe_url`, unchallenged. This replaces the need to scrape the protected page.
5. **Plugin and upstream cannot share a file verbatim.** Upstream style uses relative imports (`from .common import ...`); I verified these raise `ModuleNotFoundError: No module named 'yt_dlp_plugins.extractor.common'` in a plugin. Absolute imports (`from yt_dlp.extractor.common import ...`) work in the plugin. Solution: one canonical upstream-style file, plugin generated from it by a deterministic import rewrite.

## Standard Architecture

### System Overview

```
 user / MeTube
      |  URL: https://audio.com/<user>/audio/<slug>   (or /embed/audio/<id>)
      v
┌──────────────────────────────────────────────────────────────┐
│  yt-dlp core  (URL -> extractor dispatch, format selection,  │
│                download, postprocess)                        │
└───────────────────────────┬──────────────────────────────────┘
                            v
┌──────────────────────────────────────────────────────────────┐
│  AudioComIE  (_VALID_URL, _real_extract)                     │
│   1 normalize URL ──► 2 resolve track id ──► 3 fetch track   │
│   4 map JSON -> info dict (formats, metadata, thumbnails)    │
└───────┬───────────────────────────┬──────────────────────────┘
        │ (2) oEmbed                │ (3) track JSON
        v                           v
 api.audio.com/oembed         api.audio.com/audio/<id>
 (no Cloudflare challenge)    (no Cloudflare challenge)
                                    │ transcodings[].url / sources[].url
                                    v
                      s3.ustatik.com/audio.com.audio/...  (pre-signed S3, direct HTTPS)
                      downloaded by yt-dlp's normal HTTP downloader

 Fallback only (not default): audio.com page HTML (Cloudflare challenge;
 needs impersonate=True / curl_cffi) -> js-store JSON -> screen.data.audio
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `AudioComIE._VALID_URL` | Match `audio.com/<user>/audio/<slug>` and `audio.com/embed/audio/<id>`; capture `user`, `slug` or `embed_id` | one regex with named groups; `www.` optional |
| URL normalizer | Rebuild the exact canonical form `https://audio.com/<user>/audio/<slug>` before oEmbed (oEmbed is strict, see below) | f-string from regex groups, no lowercasing |
| ID resolver | slug URL -> numeric track ID | `_download_json(.../oembed, query={'url': canonical})`, regex `/embed/audio/(\d+)` on `iframe_url` |
| Track fetcher | numeric ID -> full track JSON incl. signed media URLs | `_download_json('https://api.audio.com/audio/<id>')` |
| Format mapper | `transcodings[]` (+ `sources[]` when allowed) -> yt-dlp formats | list comprehension with `traverse_obj`, `int_or_none` |
| Metadata mapper | title, uploader, timestamp, tags, thumbnail, description, duration | plain dict return, empty strings -> `None` |
| Page fallback (optional) | Only if oEmbed stops working: scrape js-store JSON from the page | `_download_webpage(..., impersonate=True)` + `_search_json` / `unescapeHTML` |
| Plugin build script | Emit `yt_dlp_plugins/extractor/audiocom.py` from the canonical file | ~20-line Python rewriting two import forms |
| Drift check (test/CI) | Fail if the committed plugin file differs from a fresh build | `build_plugin.py --check` |

## Discovered Endpoints (with evidence)

All unauthenticated. Tested 2026-10-28 from a residential IP. Signatures and auth-looking values are deliberately not reproduced here.

### E1. `GET https://audio.com/<user>/audio/<slug>`  (page)

| Probe | Result |
|-------|--------|
| plain `curl` | **403**, header `cf-mitigated: challenge`, `server: cloudflare` |
| yt-dlp generic extractor | 403 "Cloudflare anti-bot challenge; try again with --extractor-args generic:impersonate" |
| `curl_cffi` `impersonate='chrome'` | **200**, ~300 KB HTML |
| `https://audio.com/embed/audio/<id>` plain | 403 (also challenged); impersonated: 200 |
| `https://audio.com/audio/<id>` impersonated | 307 to `/audio/audio/<id>` (a redirect bug/loop, not useful as an ID-to-slug resolver) |

Page structure (reference track):
- `<meta property="og:audio:url">` / `og:audio:secure_url`: pre-signed **MP3** URL; `og:audio:type` = `application/mp3`; `og:type` = `music.song`; `og:title` is suffixed with " | Music by <author> | Listen on audio.com" (do not use for the title).
- `<script type="application/ld+json">` with `@type: AudioObject`: `contentUrl` (signed mp3), `name`, `author`, `uploadDate`, `fileFormat`, `bitrate`. The `bitrate` there says "320 kbps" while the real MP3 transcoding is 192 kbps. **Do not trust the JSON-LD bitrate.** `image` is an empty string when there is no cover.
- `<div class="js-store" data-content="...">`: HTML-escaped JSON. Track data at `screen.data.audio` (same shape as search results: `id`, `username`, `slug`, `title`, `author`, `downloadable`, `created`, `updated`, `play{url,duration,waveform}`, `playhq{url,duration,waveform}`, `source{...}`, `stats{plays_count,likes_count,...}`, `tags`). The same blob also embeds client credentials and keys for the site's own OAuth/Stripe; **never read, log, or use them**. `app.domains.api` confirms `https://api.audio.com` is the API host.
- No `__NEXT_DATA__`; `renderType: react`; JS bundles under `/static/public/build/audio_es6/<build>/` (build id changes, never hard-code).

### E2. `GET https://api.audio.com/oembed?url=<canonical page URL>`  (slug -> id)

- HTTP 200, `application/json`, **no Cloudflare challenge** (works with plain curl, python-requests UA, browser UA).
- Response keys: `type`, `version`, `title`, `author_name`, `author_url`, `provider_name`, `provider_url`, `cache_age`, `html`, `width`, `height`, `thumbnail_url`, `thumbnail_width`, `thumbnail_height`, `iframe_url`.
- **ID extraction:** `iframe_url` = `https://audio.com/embed/audio/<id>?theme=image`; regex `/embed/audio/(\d+)`.
- `thumbnail_url` is an empty string for tracks without a cover (same as `image` in E3).
- **Strict about the input URL** (measured): `https://audio.com/...` and `http://audio.com/...` OK; `www.audio.com` 404; trailing slash 404; any `?query` 404; uppercased username 404. Therefore always rebuild `https://audio.com/{user}/audio/{slug}` from the regex groups rather than passing the user's URL through.
- Unknown track: 404 `{"name":"Not Found","message":"Resource not found!"}`.

### E3. `GET https://api.audio.com/audio/<id>`  (track JSON, the workhorse)

- HTTP 200, `application/json`, no auth, no Cloudflare challenge, `x-rate-limit-limit: 100000`, `cf-cache-status: DYNAMIC`.
- Unknown numeric id: 404 `Audio not found!`. Non-numeric: 404 "Invalid Route".
- Top-level keys: `id`, `category_id`, `username`, `author_name`, `slug`, `license`, `title`, `caption`, `description`, `tags[]`, `cross_link_tags[]`, `avatar`, `image`, `is_public`, `is_downloadable`, `transcribed`, `date_created`, `date_updated`, `sources[]`, `transcodings[]`, `waveform`, `stats{}`, `options{}`, `price`.
- Units: `date_created` / `date_updated` are Unix **seconds**; `duration` is **milliseconds**; `bit_rate` is **bits/s** (192000 = 192 kbps); `size` is bytes. `id` is a string of ~16 digits (a Snowflake-like ID; keep as string).
- **`transcodings[]`** (what the web player streams to anonymous users). Reference track:

  | `format` | `type` | `codec` | `bit_rate` | `size` | note |
  |----------|--------|---------|-----------|--------|------|
  | mp3 | audio/mpeg | mp3 | 192000 | 4.47 MB | = page `play` and `og:audio:url` |
  | m4a | audio/m4a | aac | ~306000-333000 | 7.17 MB | = page `playhq`; served to anonymous clients |

  Each has `id`, `source_id`, `url` (pre-signed), `sample_rate`, `channels`, `duration`, `md5`, `waveform[]` (inline amplitude array, ignore). Range requests on both URLs returned HTTP 206 with correct `content-type` (`audio/mpeg`, `audio/mp4`) with no impersonation.
- **`sources[]`** = the original upload. Reference track: WavPack (`format: wv`, `codec: wavpack`, 44.1 kHz, 1.43 Mbps, 33 MB, `from: audacity`). Has `url` and `download` (the latter adds a `response-content-disposition` attachment filename). Both worked with Range requests **even though `is_downloadable` is false**; the flag is only enforced by E4. Another track's source was M4A (`is_downloadable: true`).
- Thumbnail: `image` is a full URL (e.g. `https://audio.com/s3w/audio.com.static/audio/image/..jpeg`, plain GET 200 `image/jpeg`) or empty string. In search results `image` falls back to the uploader `avatar` when no cover exists; for the reference track both are empty (so thumbnails must be optional).
- `description`, `caption` are empty strings when unset; map to `None`.
- `stats`: `plays_count`, `likes_count`, `comments_count`, `shares_count`, `downloads_count` map to `view_count`, `like_count`, `comment_count`, ... (optional).

### E4. `GET https://api.audio.com/download?id=<id>`  (explicit download endpoint)

- Exists, no auth. For a track with `is_downloadable: true` it returns 200 with a JSON **array** of `{source: bool, format, size, url, progress}` (source file plus transcodings, `url` carrying `response-content-disposition`). For `is_downloadable: false` it returns 403 `"You cannot download this audio!"`.
- It adds nothing over E3 (E3 already contains the same files). It is useful only as a reference for "what the uploader permits". **Not needed in the extractor.**

### E5. `GET https://api.audio.com/search?q=<term>&page=<n>`  (discovery, not for v1)

- 200 JSON `{items:[{id,type,model{...}}], pagination{total,pages,page,size}}`. `model` has the same fields as the page's `screen.data.audio` including `play`, `playhq`, `source`. Useful for finding test tracks, and as a future search/playlist hook. Out of scope for v1.

### Media host `s3.ustatik.com`

- Wasabi S3 behind Cloudflare (`x-wasabi-cm-reference-id` header, `cf-cache-status: HIT`). No challenge, no cookies, no special headers, no Referer needed. Pre-signed (SigV4 query string, `UNSIGNED-PAYLOAD`, `X-Amz-Expires=518400`). Supports Range (resumable downloads). `cache-control: no-store`.
- Treat URLs as short-lived: extract and download in the same run; never cache info dicts for days (MeTube queued items older than 6 days will 403, which is acceptable).

## Data Flow

```
URL ──► _match_valid_url ──► groups {user, slug} | {embed_id}
                │
       slug form│                         embed form
                v                              │
   canonical = https://audio.com/{user}/audio/{slug}
                │                              │
                v                              │
   GET api.audio.com/oembed?url=canonical      │
        └─► iframe_url ─► regex id ────────────┤
                                               v
                          GET api.audio.com/audio/{id}
                                               │
          ┌────────────────────────────────────┴────────────────────┐
          v                                                         v
  transcodings[] -> formats (mp3 192k, m4a ~306k+)        metadata -> info dict
  sources[]      -> format only if is_downloadable        id, title, uploader(_id/_url),
                                                          timestamp, duration, tags,
                                                          thumbnails, description,
                                                          view/like counts
          └────────────────────────────────────┬────────────────────┘
                                               v
                       info dict ─► yt-dlp selects best format ─► HTTPS download from S3
```

### Field mapping (info dict)

| info-dict key | Source JSON path | Transform |
|---------------|------------------|-----------|
| `id` | `id` (E3) | string as-is |
| `display_id` | URL `slug` / `slug` | optional |
| `title` | `title` | as-is (not `og:title`, which has a site suffix) |
| `description` | `description` | `or None` |
| `uploader` | `author_name` | |
| `uploader_id` | `username` | e.g. `david-oliveira-1877766671108274` |
| `uploader_url` | `https://audio.com/{username}` | built (matches oEmbed `author_url`) |
| `timestamp` | `date_created` | seconds, as-is |
| `duration` | `sources[0].duration` else `transcodings[0].duration` | `int_or_none(scale=1000)`; reference = 186.331 s |
| `tags` | `tags` | list of str |
| `categories` | `category_name` is only in page/search; E3 has `category_id` only | skip, or map 4 -> Music later |
| `thumbnail` | `url_or_none(image)` | empty string -> `None` |
| `view_count` / `like_count` / `comment_count` | `stats.plays_count` / `likes_count` / `comments_count` | `int_or_none` |
| `license` | `license` | `none` means unset; skip |
| formats `url` | `transcodings[].url` | |
| formats `format_id` | `<format>` (e.g. `mp3`, `m4a`) or `<format>-<id>` | stable short IDs preferred for `-f` use |
| formats `ext` | `format` | |
| formats `acodec` / `vcodec` | `codec` / `'none'` | `vcodec: none` marks audio-only |
| formats `abr` | `bit_rate` / 1000 | `int_or_none(scale=1000)` |
| formats `asr`, `audio_channels`, `filesize` | `sample_rate`, `channels`, `size` | exact `size` allows `filesize` not `filesize_approx` |
| formats `quality` / `source_preference` | | prefer m4a (higher bitrate) over mp3; `source` last unless allowed |

**Format policy (opinionated):** always emit `transcodings` (this is exactly what the public player serves). Emit `sources[]` only when `is_downloadable` is true. This respects the uploader's flag, avoids exposing exotic `.wv` blobs by default, and keeps the PR defensible with maintainers. Default best-audio then resolves to the M4A transcoding (higher bitrate), MP3 available via `-f mp3`.

## Recommended Project Structure

Single source of truth in an upstream-shaped tree; plugin output is a generated artifact.

```
audio-com-downloader/
├── yt_dlp/extractor/audiocom.py          # CANONICAL. Upstream style: relative imports, _TESTS,
│                                         #   AudioComIE, no repo-only code
├── scripts/
│   └── build_plugin.py                   # canonical -> plugin (import rewrite + header); --check mode
├── plugin/
│   └── yt_dlp_plugins/extractor/
│       └── audiocom.py                   # GENERATED, committed, header says "do not edit"
├── tests/
│   ├── test_build_plugin.py              # drift check + "no relative imports left" check
│   └── test_audiocom_offline.py          # optional: recorded JSON fixtures, no network
├── fixtures/                             # recorded oembed.json / audio.json (signatures redacted)
├── upstream/
│   └── README.md                         # how to apply to a yt-dlp fork: copy file + 1-line _extractors.py edit
└── Makefile                              # `make plugin`, `make check`, `make deploy-metube`
```

### Structure Rationale

- **`yt_dlp/extractor/audiocom.py` is canonical** because the PR is the harder constraint (style, relative imports, lazy-extractor generation, `_TESTS`); a plugin has no such constraints and can be derived mechanically.
- **Do not vendor `_extractors.py`.** It is an alphabetical import list inside yt-dlp (`from .audioboom import AudioBoomIE`, then `from .audiodraft import (...)`). Upstream entry goes between them: `from .audiocom import AudioComIE`. Do that on a yt-dlp fork branch (a one-line change); keep only the extractor file here. `lazy_extractors.py` is generated by yt-dlp's build, never edited.
- **Generated plugin is committed** so the deploy step is a plain file copy to the host bind mount without needing Python tooling at deploy time, and so `git diff` shows exactly what ships.

## Single Source of Truth: how it works

yt-dlp plugin loading (verified): modules under `yt_dlp_plugins/extractor/` are imported as `yt_dlp_plugins.extractor.<name>`, so relative imports resolve against the plugin package and break. Loader picks up any class named `*IE` that is defined in that module (it checks `obj.__module__` starts with the plugin module name), so a shim that re-exports a class from `yt_dlp.extractor.audiocom` would be ignored (and does not exist on the unpatched yt-dlp anyway).

**Chosen approach: generate.** Rules for the canonical file so the transform stays trivial and safe:
- Only two import shapes allowed: `from .common import InfoExtractor` and `from ..utils import (...)` (single or parenthesised multi-line).
- Rewrite: `from .common import` -> `from yt_dlp.extractor.common import`; `from ..utils import` -> `from yt_dlp.utils import`. Add a 2-line header comment (generated from, do not edit).
- `build_plugin.py --check` exits non-zero on drift, and a test asserts no line in the output matches `^from \.`.
- If a later version needs more helpers (e.g. `from ..networking.exceptions import HTTPError`), extend the rewrite rule for `..` -> `yt_dlp.` generically: `from ..X` -> `from yt_dlp.X`, `from .X` -> `from yt_dlp.extractor.X`.

Rejected alternatives:

| Alternative | Why not |
|-------------|---------|
| Write absolute imports in the canonical file | Works at runtime, but upstream reviewers expect relative imports in `yt_dlp/extractor/`; PR friction for no gain |
| `try: from .common ... except ImportError: from yt_dlp...` in one file | Ugly, conditional imports are not accepted upstream |
| Plugin shim that `importlib`-loads the canonical file under the name `yt_dlp.extractor.audiocom` | Loader rejects classes whose `__module__` is not under the plugin name; also requires shipping 2 files into the ro mount |
| Plugin as thin subclass of an upstream class | Upstream class does not exist yet; after merge the plugin would be redundant |

**Retirement path:** once upstream merges and MeTube's bundled yt-dlp includes `AudioComIE`, delete the plugin file from `/opt/metube/plugins/yt_dlp_plugins/extractor/`. If both exist, the plugin class of the same name overrides the built-in (yt-dlp's plugin override semantics), so a stale plugin would silently pin old behavior; note this in `upstream/README.md`.

## MeTube deployment facts (read-only inspection of the running container)

- Container `metube`, bundled yt-dlp **2026.8.19**, **curl_cffi 0.16.3 present**, targets include Chrome-133/136, Safari variants. Python 3.13. (Impersonation is therefore available as a fallback; the primary path does not need it.)
- Env `PYTHONPATH=/plugins`; bind mount `/opt/metube/plugins` (host) -> `/plugins` (**read-only**). Existing layout: `/opt/metube/plugins/yt_dlp_plugins/extractor/rumble_fix.py` (an override plugin using absolute `from yt_dlp.extractor.rumble import ...`). `site-packages/yt_dlp_plugins/extractor/` additionally holds the bgutil plugins; both coexist because plugin-package search locations are merged across `sys.path`.
- Deploy = copy `plugin/yt_dlp_plugins/extractor/audiocom.py` to `/opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py` on the host (needs root or sudo; directory is root-owned) and restart/recreate nothing: yt-dlp loads plugins per process, so each new MeTube download picks it up (confirm; a MeTube restart is the safe fallback).
- MeTube `YTDL_OPTIONS` includes `writethumbnail` + `FFmpegThumbnailsConvertor` (jpg) and `FFmpegMetadata`: with no cover (`image` empty) this must not crash, so omit `thumbnail` rather than passing `''`. Also `merge_output_format: mp4` is irrelevant for audio-only formats; verify audio-only downloads still land with `.m4a`/`.mp3` extensions.

## Architectural Patterns

### Pattern 1: oEmbed-then-API (avoid the protected host)

**What:** Use the unprotected `api.audio.com` host for everything; use oEmbed purely as slug -> id resolver.
**When to use:** Always (default path).
**Trade-offs:** (+) no curl_cffi dependency, works on stock yt-dlp, fast (2 small JSON calls), clean for upstream (no new deps). (-) two undocumented-but-public endpoints could change; oEmbed is the more stable of the two (it is a published standard and `<link>`-style integration for embeds).

```python
class AudioComIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?audio\.com/(?:embed/audio/(?P<embed_id>\d+)|(?P<user>[^/?#]+)/audio/(?P<slug>[^/?#]+))'

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        track_id = m.group('embed_id')
        if not track_id:
            oembed = self._download_json(
                'https://api.audio.com/oembed', m.group('slug'), 'Downloading oEmbed JSON',
                query={'url': f'https://audio.com/{m.group("user")}/audio/{m.group("slug")}'})
            track_id = self._search_regex(r'/embed/audio/(\d+)', oembed['iframe_url'], 'track id')
        data = self._download_json(f'https://api.audio.com/audio/{track_id}', track_id)
        ...
```

(A prototype of exactly this flow ran end-to-end under yt-dlp 2026.10.26 as a plugin via `PYTHONPATH` and downloaded the reference track: 4,473,207 bytes, valid MP3 192 kbps/44.1 kHz, title/uploader/duration/upload_date populated.)

### Pattern 2: Page-JSON fallback behind a flag of failure

**What:** If oEmbed returns non-200/unexpected shape, fetch the page with `impersonate=True`, parse `div.js-store[data-content]` (unescape HTML, `json.loads`), read `screen.data.audio.id`, then continue at the track fetch.
**When to use:** Only if oEmbed disappears. Defer to a later phase unless review feedback asks for it; it adds code and a test fixture.
**Trade-offs:** (+) resilience. (-) page is Cloudflare-challenged, needs optional curl_cffi, more surface for upstream review. If `impersonate=True` is requested and no target exists, yt-dlp warns once and continues (it then 403s), which is a clear failure mode.

### Pattern 3: Normalize before external calls

**What:** Rebuild canonical URLs from regex groups before oEmbed.
**Why:** oEmbed 404s on `www.`, trailing slash, query strings, uppercased usernames (measured). Users routinely paste URLs with `?utm_...` or trailing `/`.
**Note:** `_VALID_URL` already excludes `?#` from captures; ensure the regex tolerates optional trailing `/` and query strings so `_match_valid_url` still matches before normalization.

## Anti-Patterns

### Anti-Pattern 1: Scraping the HTML page as the default path

**What people do:** Generic-extractor style: request the page, hunt `og:audio:url`.
**Why it's wrong:** Hits the Cloudflare challenge, forces curl_cffi (an optional dependency upstream cannot assume), and the page URL is signed with a *different* timestamp than the API. `og:` and JSON-LD give MP3 only, with misleading bitrate.
**Do this instead:** Pattern 1.

### Anti-Pattern 2: Using the site's embedded OAuth/Stripe config or session tokens

**What people do:** Lift `app.oauth.*` / API keys from the js-store blob to call "authenticated" endpoints.
**Why it's wrong:** Not needed (everything required is anonymous), ToS risk, and a PR containing credentials will be rejected.
**Do this instead:** Anonymous calls only; add a source-review note that nothing from `app.*` is read.

### Anti-Pattern 3: Hard-coding build hashes or CDN/S3 paths

**What people do:** Construct `s3.ustatik.com/...` URLs from ids or reuse the `/static/public/build/...<hash>.js` names.
**Why it's wrong:** URLs are SigV4-signed (cannot be constructed) and build hashes rotate.
**Do this instead:** Always take URLs verbatim from `transcodings[].url`.

### Anti-Pattern 4: Treating `is_downloadable` as DRM

**What people do:** Ignore it because the API leaks source URLs regardless.
**Why it's wrong:** Raises PR/ethics friction for no user benefit (transcodings are already high quality).
**Do this instead:** Emit sources only when true (see Format policy).

### Anti-Pattern 5: Editing the generated plugin by hand

**What people do:** Hotfix `/opt/metube/plugins/...audiocom.py` directly.
**Why it's wrong:** Immediately drifts from the PR code.
**Do this instead:** Edit canonical, run `make plugin`, redeploy.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Occasional personal saves (target) | Two API calls per track, nothing to tune |
| Batch of a few hundred tracks | API headers show 100,000 rate limit; no action needed. If Cloudflare starts challenging the API, add `impersonate=True` to the two `_download_json` calls |
| Playlists/collections (out of scope) | `/collection?username=&slug=` and `/collection/items` routes exist in the site bundle; revisit as a second extractor class later |

### Scaling Priorities

1. **First bottleneck / risk:** Cloudflare policy change on `api.audio.com` or `oembed`; mitigation is `impersonate=True` (curl_cffi already in MeTube).
2. **Second:** signed-URL expiry (6 days) for queued downloads; re-extract at download time.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| `api.audio.com/oembed` | `_download_json` with `query={'url': canonical}` | strict on URL form; 404 JSON on miss |
| `api.audio.com/audio/<id>` | `_download_json` | anonymous; JSON error bodies `{"name","message","status"}` on 404 (wrap as `ExtractorError(expected=True)` for "Audio not found") |
| `s3.ustatik.com` | yt-dlp HTTP downloader | direct, Range OK, signed 6-day URLs |
| `audio.com` (page/embed) | fallback only | Cloudflare challenge; impersonation required |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| canonical extractor -> plugin | build-time source transform | one-way; plugin never edited |
| canonical extractor -> yt-dlp fork | file copy + 1-line `_extractors.py` insert | only in the PR branch |
| plugin -> MeTube | file in `/opt/metube/plugins/yt_dlp_plugins/extractor/` (ro bind to `/plugins`, on `PYTHONPATH`) | no image rebuild; coexists with `rumble_fix.py` |

## Suggested Build Order

1. **API contract + fixtures** (no code dependencies): save redacted JSON fixtures for oEmbed and `/audio/<id>` for two tracks (the reference non-downloadable one and one `is_downloadable: true`), plus an extra with a cover image if found. Everything else depends on knowing the exact shapes.
2. **Canonical extractor `audiocom.py`** (depends on 1): `_VALID_URL`, normalize, oEmbed id resolve, track fetch, formats, metadata, error handling. Verify locally with `python -m yt_dlp` against a yt-dlp checkout or via `PYTHONPATH` plugin.
3. **Plugin generation + drift check** (depends on 2): `build_plugin.py`, test, `make plugin`. Verify by loading in a scratch venv via `PYTHONPATH` (shows `Extractor Plugins: AudioComIE` in `-v`).
4. **MeTube deployment + acceptance** (depends on 3): copy to `/opt/metube/plugins/...`, paste the reference URL into MeTube, confirm file lands with title/metadata and thumbnail handling OK.
5. **Upstream-readiness** (depends on 2; can run parallel to 3-4): `_TESTS` (one real test + `only_matching` for embed URL form), `hatch test AudioCom`, `ruff` per repo config, `_extractors.py` entry between `audioboom` and `audiodraft`, fork branch, PR text (explain no new deps, no impersonation).
6. **Optional hardening** (later): page-JSON fallback (Pattern 2), `is_downloadable` handling edge cases, private/unlisted tracks, collection support.

## Open Gaps

- **Private/unlisted tracks** (`is_public: false`): not testable anonymously; behavior of `/audio/<id>` (404 vs 403 vs data) unknown. Handle 403/404 as expected ExtractorErrors.
- **Whether `/download` becomes the preferred source for downloadable tracks** (could carry different/newer signed URLs): E3 suffices; no evidence otherwise.
- **Stability of reference track** as an upstream `_TESTS` fixture: choose a track unlikely to be deleted; yt-dlp maintainers may want an md5 or `info_dict` only (signed URLs do not affect md5 of content). Re-verify at PR time; MP3/M4A transcoding content `md5` fields in the API (e.g. `baed0261...` for the reference mp3) could serve as the test `md5` of the downloaded file.
- **Category name** only appears in page/search `category_name`, not in `/audio/<id>` (`category_id` only). Optional.
- **Exact yt-dlp plugin-vs-builtin precedence after upstream merge**: reasoned from the override-plugin pattern in `rumble_fix.py`; confirm when the time comes.
- **Prior-art search** (existing audio.com downloaders / yt-dlp issues): a quick `gh search` for issues/PRs mentioning audio.com in yt-dlp returned no results, and a web search found nothing audio.com-specific; the formal prior-art task is separate.

## Sources

- Live probes of `audio.com`, `api.audio.com`, `s3.ustatik.com` on 2026-10-28 via `curl` and `curl_cffi` (chrome impersonation) in a scratch venv; yt-dlp 2026.10.26 prototype in scratch (HIGH, first-hand).
- MeTube container inspection (read-only `docker exec` / `docker inspect`): yt-dlp 2026.8.19, curl_cffi 0.16.3, `PYTHONPATH=/plugins`, `/opt/metube/plugins` mount; yt-dlp `plugins.py` source (`default_plugin_paths`, `PluginFinder`) (HIGH).
- Installed yt-dlp source: `extractor/audioboom.py` (style reference), `extractor/_extractors.py` (alphabetical import list, ordering of `audioboom`/`audiodraft`) (HIGH).
- yt-dlp CONTRIBUTING.md (`hatch test YourExtractor`, test naming, `only_matching`): https://github.com/yt-dlp/yt-dlp/blob/master/CONTRIBUTING.md (HIGH).
- Local `/opt/metube/plugins/yt_dlp_plugins/extractor/rumble_fix.py` as in-house precedent for override plugins and impersonation via `_request_webpage` (HIGH).

---
*Architecture research for: yt-dlp extractor for audio.com*
*Researched: 2026-10-28*
