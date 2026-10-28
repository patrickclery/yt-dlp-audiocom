# Feature Research

**Domain:** yt-dlp single-track extractor for an audio-hosting site (audio.com)
**Researched:** 2026-10-28
**Confidence:** HIGH (prior art, live-site observation, yt-dlp source read directly); MEDIUM on upstream-acceptance predictions

---

## Prior Art (searched first, per request)

**Verdict: there is no prior art.** Nobody has published an audio.com downloader, extractor, plugin, userscript or site-support request anywhere on GitHub. The extractor is greenfield, and nothing is competing for the upstream slot.

### yt-dlp upstream

| Check | Result | Evidence |
|-------|--------|----------|
| audio.com extractor in yt-dlp master | **No.** Latest release `2026.10.26` (published 2026-10-26); master `f264a6c` (2026-10-26). No `audio*` file other than `audioboom`, `audiodraft`, `audiomack`, `audius`; `_extractors.py` has no audio.com import. | GitHub contents/tree API, 2026-10-28 |
| Open or closed site-support issue | **None.** `repo:yt-dlp/yt-dlp` searched for `audio.com`, `"audio.com"`, `audiocom`, `"https://audio.com"`, `api.audio.com`, `ustatik` and `audio.com in:title/body/comments`: 0 hits. Search itself verified working (`soundcloud` returns 148, `audiomack` 7). | GitHub search API |
| Open, merged, rejected or stale PR | **None** (same queries with `type:pr`: 0). | GitHub search API |
| Discussions | 0 (GraphQL DISCUSSION search). | GitHub GraphQL |
| Maintainer comments declining the site | **None exist.** No request means no decline. | n/a |

Closest relevant precedent, with a useful signal about maintainer attitude. [yt-dlp/yt-dlp#6913](https://github.com/yt-dlp/yt-dlp/issues/6913) was a site request for **whyp.it**, a small free audio host. `bashonly` added it within a day of the request (commit `2c566ed`, 2023-04-25). The extractor is now `yt_dlp/extractor/whyp.py` (83 lines). **Small, legitimate audio hosts get accepted quickly when the extractor is clean.** CONTRIBUTING's only site-level rejection grounds are primarily-piracy sites, DRM-only services and fake-porn sites. audio.com (operated by the Audacity/Muse Group ecosystem) is none of these.

Unrelated but adjacent open work: [PR #17258 "[ie/audiomack] Rework extractor"](https://github.com/yt-dlp/yt-dlp/pull/17258), [PR #12269 soundcloud.com/you](https://github.com/yt-dlp/yt-dlp/pull/12269), [PR #15913 descript](https://github.com/yt-dlp/yt-dlp/pull/15913). They show the review queue is slow (all open and touched 2026-10-21), which supports shipping the plugin first.

### Standalone tools, userscripts, plugins, forks

| Search | Result |
|--------|--------|
| Repos: `audio.com downloader`, `audio.com yt-dlp`, `audio.com userscript`, `audiocom`, `audio-com-downloader`, `audio.com` (name/description/readme) | 0 relevant repos. Hits were unrelated (generic yt-dlp wrappers, audio-compression projects). |
| Code: `AudioComIE`, `class AudioCom`, `"audio.com" InfoExtractor`, `"audio.com" _VALID_URL`, `"audio.com/embed"`, `"audio.com.audio"`, `yt_dlp_plugins` + `audio.com` | 0 extractors or plugins. |
| Issues in `gallery-dl`, `cobalt`, `youtube-dl`, `metube` mentioning audio.com | 0 hits each. |
| Greasy Fork / Reddit / web | Nothing. Web search found only "share from Audacity to audio.com" docs; no downloader. |

### Adjacent finds that ARE reusable (not downloaders, but they reveal the site's surface)

| Find | URL | Status / last activity | Reusable? |
|------|-----|------------------------|-----------|
| **audio.com oEmbed endpoint** | `https://api.audio.com/oembed` (docs: `https://audio.com/oembed-docs/`); registered in [iamcal/oembed `providers/audiocom.yml`](https://github.com/iamcal/oembed/blob/master/providers/audiocom.yml), [mpratt/Embera `Audiocom.php`](https://github.com/mpratt/Embera/blob/master/src/Embera/Provider/Audiocom.php), [Discourse onebox for audio.com](https://github.com/makehackvoid/community.canberramaker.space/blob/master/lib/onebox/engine/audio_com_onebox.rb) | **Works today, unauthenticated, not behind the Cloudflare challenge** (verified: HTTP 200 JSON for the reference URL). Returns `title`, `author_name`, `author_url`, `iframe_url`/embed id, `thumbnail_url` (empty for the reference track). **Returns no audio URL.** Type is always `rich`. | Yes, as a **metadata fallback / URL-to-id resolver only**. Cannot produce formats. |
| **Public API v1** | `https://api.audio.com/v1/docs`, `/v1/openapi.json` | Live. All 19 operations are OAuth2 (PKCE, scope `public`) and act only on **the authenticated user's own audio** (`/v1/audio/view` "View one of your audio"). Anonymous `GET /v1/audio/<id>` returns 404. | **No.** Cannot read arbitrary public tracks, and OAuth is unacceptable for an upstream extractor. Do not build on it. |
| **Soundscaper** (`mindscaper-org/Soundscaper`) audio.com provider and research notes | [`functions/api/audiocom/README.md`](https://github.com/mindscaper-org/Soundscaper/blob/main/functions/api/audiocom/README.md), [`docs/research/audio-com-project-sync.md`](https://github.com/mindscaper-org/Soundscaper/blob/main/docs/research/audio-com-project-sync.md) | Active (validated 2026-10-15). A web audio editor that uses the OAuth v1 API for search, ranged playback and upload. | Confirms the API is owner-scoped and that media is served from `s3.ustatik.com` with signed URLs. No scraping code to reuse. |
| **Audacity cloud client** | [`audacity/audacity` `au3/libraries/au3-cloud-audiocom`](https://github.com/audacity/audacity/tree/master/au3/libraries/au3-cloud-audiocom) | Active. Upload and project-sync protocol only. | No (upload path, not download). Do not copy its embedded OAuth client secret. |

### Reusable first-hand discovery (this research, 2026-10-28)

Even with no prior art, the page is rich and scrapable. With a Chrome-impersonated client (`curl_cffi`), the reference track page returned HTTP 200 (plain `curl` and a browser UA get **403**, matching PROJECT.md). The page exposes two usable sources:

1. **Standard `<meta>`/JSON-LD:** `og:title`, `og:description`, `og:type=music.song`, `og:audio` (signed mp3 URL), and a schema.org `AudioObject` (`name`, `author`, `uploadDate`, `fileFormat`, `contentUrl`, `url`). `og:image`/`image` is absent for tracks with no artwork.
2. **A `<div class="js-store" data-content="...">` JSON blob** (HTML-escaped) at `screen.data.audio` with the full record. Field names are listed in the table below.

| `screen.data.audio` field | Observed (reference track) | Maps to yt-dlp |
|---|---|---|
| `id` | `1877766681285368` (matches oEmbed iframe id) | `id` |
| `title` | "Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best" | `title` |
| `slug` | `rusted-pitchfork-...-best` | `display_id` |
| `author` / `username` / `user` | "David Oliveira" / `david-oliveira-1877766671108274` / `1877766671097193` | `uploader` / `uploader_id` (username) / `uploader_url` = `https://audio.com/<username>` |
| `created` / `updated` | `1790777856` (unix seconds, = 2026-09-30) | `timestamp` (and `modified_timestamp`) |
| `play.duration` | `186331` (**milliseconds**) | `duration` = 186.331 (scale 1000) |
| `play.url` | signed mp3 (`audio/mpeg`, ~4.5 MB) | format `mp3` |
| `playhq.url` | signed m4a (`audio/mp4`, ~7.2 MB) | format `m4a` (higher quality) |
| `source.download` / `source.codec` | signed **WavPack `.wv`** original (`audio/x-wavpack`, 33 MB, 44.1 kHz stereo, md5 present) | optional lossless format (see Anti-Features: blocked by core ext allowlist) |
| `downloadable` | `false` for this track (the signed source URL still returned HTTP 206) | policy flag |
| `stats.plays_count` / `likes_count` / `comments_count` / `shares_count` / `downloads_count` | 5555 / 25 / 0 / 49 / 0 | `view_count` / `like_count` / `comment_count` / `repost_count` / (none) |
| `tags` | `["music", "effects unit"]` | `tags` |
| `category_name` | "Music" | `categories` |
| `genres` | `[]` (empty here) | `genres` |
| `license`, `description`, `image`, `avatar` | `none`, empty, empty, empty | `license` (skip "none"), `description`, `thumbnail`, none |
| signed-URL expiry | `X-Amz-Expires=518400` (6 days) | no refresh logic needed |

The CDN host `s3.ustatik.com` served the media with **plain `curl`** (HTTP 206, no impersonation needed). Cloudflare gates only the HTML pages. So impersonation applies to one request (the page fetch); the actual download is an ordinary HTTP download.

---

## Feature Landscape

### What comparable yt-dlp audio extractors provide (reference baseline, read from master)

| Field / behavior | SoundCloud | Bandcamp | Mixcloud | Audiomack | hearthis.at | Whyp (modern, 83 lines) |
|---|---|---|---|---|---|---|
| `id`, `title`, `formats` | yes | yes | yes | yes (minimal) | yes | yes |
| `ext` (+ `vcodec: none`/`acodec`) | yes | yes | yes | mp3 only | yes | `vcodec: none` |
| `abr`, `acodec`, `format_note`, `quality` ranking | yes (`abr`, `quality`, "Original"/"Premium") | yes (`abr`) | no | no | `quality: 2` for original | `quality: 10` for lossless |
| `duration` | yes | yes | yes | no | yes | yes (float) |
| `uploader` + `uploader_id` | yes + `uploader_url` | yes + `uploader_url` | yes + `uploader_url` | `uploader` only | no (artist baked into title) | yes (no `uploader_url`) |
| `thumbnail(s)` | yes (`thumbnails`, original-size preferred) | yes | yes | no | yes | yes |
| `description` | yes | no (on album) | yes | yes (wrapped case) | yes | yes |
| `timestamp` / `upload_date` | yes (+ `release_*`, `modified_*`) | yes (+ `release_timestamp`) | yes | `upload_date` | yes | yes |
| `view_count` | (via API) | no | yes | no | yes | no |
| `like_count` / `repost_count` / `comment_count` | yes / yes / yes | no | yes / yes / yes | no | no | no |
| `tags` / `genres` | yes / yes | `tags` | `tags` | no | `genre(s)` | no |
| `license` | yes | no | no | no | no | no |
| music fields (`track`, `album`, `artists`, `track_number`) | `album*` on sets | yes, all | `artist` | no | no | no |
| Original-quality download gated on a flag | yes (`downloadable` + auth, "Original") | no | no | no | yes (`download_url`) | yes (`lossless_url`) |
| DRM/preview handling | yes (skips `ctr-`/`cbc-`, previews deprioritized) | yes (free vs purchased) | no | no | no | no |
| Cloudflare/impersonation | `impersonate` used for some requests | no | no | no | no | no |
| `_TESTS` | many | 4+ with `md5`, `skip` | 2 | 2 (one `skip`) | 4 with `md5` | 2 + `only_matching` |

Pattern: the **newest, cleanest extractor (Whyp)** is the model to copy. It uses `traverse_obj` with type-casting transformers, `require()` for mandatory data, `display_id` + `id` split, `vcodec: none`, and `quality` ranking. `CONTRIBUTING.md` makes only `id`, `title` and a usable `formats`/`url` mandatory. **Everything else must be non-fatal.**

### Table Stakes (must have or the extractor is not PR-ready / users leave)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Match `https://audio.com/<user>/audio/<slug>` (with/without `www`, trailing slash, query string) | Core promise: pasting a link works | LOW | `_VALID_URL` with named groups `user`, `id` (= slug). Fuzzy regex per CONTRIBUTING. Must NOT swallow `/collections/` (out of scope) or `/embed/`. |
| Pass Cloudflare anti-bot on the page fetch | Generic extractor currently 403s; without this nothing works | MEDIUM | Page request needs browser TLS impersonation (`impersonate=True` via optional `curl_cffi`). Verified working with `chrome`. No new hard dependency. Emit a clear `raise_no_formats`/hint when no impersonation target is installed (as the generic error already suggests). Highest-risk table-stakes item. |
| `id` (numeric audio id, e.g. `1877766681285368`) | Mandatory field | LOW | `screen.data.audio.id` |
| `title` | Mandatory field | LOW | JSON, falling back to `og:title` stripped of the " \| Music by ... \| Listen on audio.com" suffix. |
| Direct-audio `formats` (mp3 from `play.url`, m4a from `playhq.url`) | Mandatory; gets the file | LOW | Distinct `format_id` (`mp3`, `m4a`), `vcodec: none`, `acodec`, `ext`, `filesize`/`abr` when known, `quality` ordering (m4a above mp3 if higher bitrate). No Referer/cookie needed for the CDN. |
| Correct file extension and container (`ext` from format) | MeTube/`-x` rely on it | LOW | Use `ext` from MIME type (`audio/mpeg` to `mp3`, `audio/mp4` to `m4a`), not guessed from the signed URL query string. |
| `uploader`, `uploader_id`, `uploader_url` | Matches every reference extractor; PROJECT.md "uploader" | LOW | `author` / `username` / `https://audio.com/<username>`. |
| `duration` (seconds, scaled from ms) | PROJECT.md requirement | LOW | `play.duration` ms, so `scale=1000`. |
| `thumbnail` (non-fatal; absent for many tracks) | PROJECT.md requirement | LOW | `image` or `og:image`. **Empty on the reference track** (and oEmbed `thumbnail_url` empty), so must be optional and the test must not assert it unless the test URL has artwork. |
| `description` (non-fatal; often empty) | PROJECT.md requirement | LOW | Empty string on reference track. Return `None`, not `""`. |
| `timestamp` (+ derived `upload_date`) | Every reference extractor | LOW | `created` (unix seconds). |
| `webpage_url`, `display_id` (slug) | Standard info-dict hygiene | LOW | `display_id` = `slug`. |
| `_TESTS` with at least one working download test; fields typed (`int`, `re:`) for volatile values | CONTRIBUTING: "at least one test"; PR rejected otherwise | LOW | Use `'view_count': int`, not literals (counts change; reference shows 5555 plays). Add `skip` only with a stated reason. Add `only_matching` for alternate URL forms. Prefer a track with artwork + description + tags so more fields are asserted; keep the reference track as a second test. Note the test track must be long-lived. |
| Code-style conformance (`hatch fmt`/ruff, `traverse_obj`, no bare `.get` chains, `fatal=False` on optional data, Python >=3.11) | PR-ready gate | LOW | Copy the Whyp idiom. |
| Clean errors for unavailable tracks (404, deleted, private/unlisted) | Users otherwise see a stack trace | LOW-MEDIUM | Detect missing `screen.data.audio` and raise `ExtractorError(expected=True)`. `listed`/`browsable` flags exist in the JSON. |
| Packaged as a plugin (`yt_dlp_plugins/extractor/audiocom.py`) usable in the MeTube container | PROJECT.md core value | LOW-MEDIUM | Same file; plugin namespace imports differ (`yt_dlp.extractor.common`). Must load on yt-dlp 2026.08.19. See PITFALLS. |

### Differentiators (valued, not expected; pick few)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `view_count`, `like_count`, `comment_count`, `repost_count` | Parity with Mixcloud/SoundCloud; free to extract from `stats` | LOW | `stats.plays_count`/`likes_count`/`comments_count`/`shares_count`. All optional via `int_or_none`. **Best value-for-effort differentiator.** |
| `tags`, `categories`, `genres` | Parity with SoundCloud/Bandcamp; useful for `--embed-metadata` | LOW | `tags[]`, `category_name`, `genres[]`. Drop the synthetic `cross_link_tags`. |
| `modified_timestamp` | SoundCloud parity | LOW | `updated`. |
| `license` | SoundCloud parity | LOW | Skip when `none`. |
| Embed URL support (`https://audio.com/embed/audio/<id>`) as a second `_VALID_URL`/alt route | Third-party sites embed audio.com; MeTube users may paste an embed link | MEDIUM | The embed page is a SPA shell with no `og:audio` and no `js-store` (verified), so it needs a redirect/oEmbed to the canonical page, or `only_matching` plus a webpage-embed extractor. Defer. |
| oEmbed (`api.audio.com/oembed`) used as an **unblocked metadata fallback** when the page is challenge-blocked | Gives title/uploader even when no impersonation target exists, and a useful error message | LOW-MEDIUM | Cannot yield formats, so it is value-limited. Useful mainly for a better failure message ("track exists but audio requires impersonation"). Optional. |
| Highest-quality lossless "source" format (WavPack) | Archivists want the original | **HIGH (blocked)** | See Anti-Features. `wv` is **not** in yt-dlp's `_UnsafeExtensionError.ALLOWED_EXTENSIONS`/`MEDIA_EXTENSIONS`, so a `.wv` format would be rejected at filename sanitization unless core `utils` is modified in the same PR. Also not in `FFmpegExtractAudio` codecs. |
| Waveform / chapters / transcript | None of the reference extractors surface them | MEDIUM | `play.waveform` JSON exists, but no yt-dlp field consumes it. Skip. |
| `abr`/`asr`/`audio_channels`/`filesize` on each format | Better `-F` output; enables `-S` sorting | LOW | `source` gives `sample_rate`, `channels`, `size`, `bit_rate` for the original only. For mp3/m4a, take `filesize` from the `Content-Range` header (needs an extra request, so skip unless free). |

### Anti-Features (deliberately NOT building)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Collections / playlists / profile pages (`/collections/...`, `/<user>`) | "Download everything from this artist" | Explicitly out of scope in PROJECT.md. It needs paging, a second `_VALID_URL`, and a playlist test. It also tends to be the part reviewers push back on. | Single-track only for v1. Ensure `_VALID_URL` does not accidentally match them, and note them as v2. |
| Using the official Public API v1 / OAuth | "Cleaner than scraping" | Owner-scoped (cannot read other people's tracks); requires OAuth app registration, which is incompatible with an upstream extractor and with MeTube. Audacity's embedded client secret must not be reused. | Scrape the page's `js-store` JSON. |
| Lossless WavPack original as a format (v1) | Best quality | `.wv` is not an allowed yt-dlp extension, so it needs a core `utils` change (scope creep that threatens the PR). Also `downloadable:false` on tracks whose owners chose to disable downloads. | Ship mp3 + m4a. Revisit as a separate follow-up PR that adds `wv` to the allowlist. |
| Bypassing the owner's `downloadable:false` choice for the original file | "Get the source file anyway" | Respect for uploader intent, and the reviewer/legal optics that decide the PR. SoundCloud's extractor sets the precedent: the original is offered only when `downloadable` is true. The stream (`play`/`playhq`) is what the site's own player serves. | Offer the original only when `downloadable` is true (and only once `wv` is supportable). Streams are always offered. |
| Login / cookies / account support | "Private tracks" | Needs a session-handling flow, and tests become non-reproducible. Unlisted tracks work via the plain URL anyway. | Out of scope. `--cookies` already works generically if ever needed. |
| Hard dependency on `curl_cffi` or a bundled headless browser | "Make Cloudflare go away" | Violates the upstream policy (no new hard deps). | Use yt-dlp's optional impersonation (`impersonate=True`) and fail with an actionable message when missing. |
| Scraping/rotating third-party proxies or CAPTCHA solving | Robustness | Fragile, ethically gray, instant PR rejection. | Rely on impersonation only. |
| Standalone CLI/GUI/batch archiver | "Easier to use" | yt-dlp + MeTube already are the interface (PROJECT.md out of scope). | None. |
| Search, recommendations (`suggestions`), related tracks | Present in page JSON | No yt-dlp extractor for single tracks surfaces them. | Ignore. |
| Hard-coding `User-Agent: Audacity/x` or the page's analytics endpoints | Seems to help | Not needed (media works with plain HTTP) and brittle. | Plain fetch with impersonation. |
| Asserting volatile fields literally in `_TESTS` (plays, likes, signed URLs, `md5` of the file at a signed URL) | "Strong test" | Counts change; signed URLs expire in 6 days; breaks CI. | Use `int`/`re:` matchers. Use the `md5` of the first 10241 bytes only if the stream is stable (otherwise omit). |

---

## Feature Dependencies

```
[Cloudflare impersonated page fetch]
    └──requires──> [optional curl_cffi present + clear missing-impersonation error]
    └──enables───> [js-store JSON parse]  (nothing downstream works without this)
                       ├──> [id, title, display_id]            (mandatory)
                       ├──> [formats: mp3 (play) + m4a (playhq)]  (mandatory)
                       │        └──requires──> [ext/acodec from MIME, vcodec none, quality ranking]
                       ├──> [uploader / uploader_id / uploader_url]
                       ├──> [duration (ms -> s), timestamp, thumbnail, description]  (non-fatal)
                       └──> [stats -> view/like/comment/repost counts; tags; categories; genres]  (differentiators)

[_VALID_URL for /<user>/audio/<slug>] ──requires──> [display_id/id handling]
[_TESTS (typed matchers)] ──requires──> [stable public test track + at least one fully-populated track]
[Plugin packaging] ──requires──> [working extractor] + [compat with yt-dlp 2026.08.19 in MeTube]
[Upstream PR] ──requires──> [ruff/hatch clean + _TESTS + registered in _extractors.py]

[Lossless wv format] ──requires──> [core utils change: allow 'wv' ext]  (CONFLICTS with a small, extractor-only PR)
[Embed-URL support] ──requires──> [canonical-URL resolution via oEmbed or redirect]  (enhances base extractor)
[oEmbed fallback] ──enhances──> [error messaging when impersonation unavailable]
[Collections/playlists] ──conflicts──> [single-track-only scope]
```

### Dependency Notes

- **Everything depends on the impersonated page fetch.** The CDN and oEmbed are unblocked, but the page is the only source of the signed media URLs, so this is the first thing to prove and the biggest risk. De-risk it in phase 1.
- **Formats depend on MIME-derived `ext`.** The signed URLs end in a query string; letting yt-dlp guess the extension from the URL path works for `.mp3`/`.m4a`, but an explicit `ext` is safer.
- **The `wv` format conflicts with the PR strategy.** A small extractor-only PR is a better bet. Because `wv` is unsupported in core, treat lossless as a separate, later PR.
- **Plugin and upstream share one file.** The only differences are import paths and the plugin directory layout. Keep the extractor free of plugin-only constructs.
- **Differentiator fields are all non-fatal and cheap.** They come from the same JSON as the mandatory fields, so adding them costs no extra requests.

---

## MVP Definition

### Launch With (v1)

- [ ] `_VALID_URL` matching `audio.com/<user>/audio/<slug>`; excludes collections/embed. Essential: defines scope.
- [ ] Impersonated page fetch with an actionable missing-`curl_cffi` error. Essential: unblocks everything.
- [ ] Parse `js-store` JSON (with `og:`/JSON-LD fallback for title and `og:audio` mp3 URL). Essential: single source of truth, with a resilience fallback.
- [ ] Mandatory fields: `id`, `title`, `formats` (mp3 + m4a, `vcodec: none`, correct `ext`). Essential: Core Value.
- [ ] Metadata: `uploader`, `uploader_id`, `uploader_url`, `duration`, `timestamp`, `thumbnail`, `description`, `display_id` (all non-fatal). Essential: PROJECT.md requirement.
- [ ] Cheap extras: `view_count`, `like_count`, `comment_count`, `repost_count`, `tags`, `categories`. Included because they cost nothing and match SoundCloud/Mixcloud parity.
- [ ] `_TESTS`: at least one live download test with typed matchers, plus `only_matching` for URL variants.
- [ ] Clean `ExtractorError(expected=True)` for missing/removed/private tracks.
- [ ] ruff/`hatch fmt` clean; Python >=3.11; registered in `_extractors.py`.
- [ ] Plugin build of the same code, loaded in MeTube on yt-dlp 2026.08.19.

### Add After Validation (v1.x)

- [ ] `modified_timestamp`, `license`, `genres` (when non-empty). Trigger: a test track that actually has them.
- [ ] oEmbed-based diagnostic fallback. Trigger: users report confusing 403s without impersonation.
- [ ] Embed URL support (`/embed/audio/<id>`). Trigger: someone requests it or third-party embeds appear.
- [ ] Upstream PR follow-ups requested by maintainers (naming, test URL swap).

### Future Consideration (v2+)

- [ ] Collections/playlists (`/collections/<slug>`), profile pages. Deferred per PROJECT.md.
- [ ] Lossless WavPack original. Defer until `wv` is added to core's extension allowlist, and honor `downloadable`.
- [ ] Per-format `filesize`/`abr` via HEAD/Range probes. Defer; low value for extra requests.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| URL match + `id`/`title` | HIGH | LOW | P1 |
| Cloudflare impersonation (page fetch) | HIGH | MEDIUM | P1 |
| mp3 + m4a formats, correct `ext` | HIGH | LOW | P1 |
| uploader / duration / timestamp / thumbnail / description | HIGH | LOW | P1 |
| `_TESTS` + code-style conformance | HIGH (gates PR) | LOW | P1 |
| Clean error handling (private/removed/no-impersonation) | MEDIUM | LOW | P1 |
| Plugin packaging for MeTube | HIGH | LOW-MEDIUM | P1 |
| view/like/comment/repost counts, tags, categories | MEDIUM | LOW | P2 |
| modified_timestamp, license, genres | LOW | LOW | P2 |
| oEmbed diagnostic fallback | LOW | LOW-MEDIUM | P3 |
| Embed URL support | LOW | MEDIUM | P3 |
| Lossless WavPack format | MEDIUM | HIGH (core change) | P3 |
| Collections / profile | LOW (per PROJECT.md) | HIGH | P3 (out of scope) |

**Priority key:** P1 = must have for launch; P2 = add when possible; P3 = future / out of scope.

---

## Competitor Feature Analysis

"Competitors" here are the existing yt-dlp extractors the new one will be reviewed against.

| Feature | SoundCloud | Bandcamp | Mixcloud | Whyp (cleanest model) | Our Approach |
|---------|-----------|----------|----------|-----------------------|--------------|
| Metadata source | Authenticated v2 JSON API (needs scraped `client_id`) | HTML + embedded JSON | GraphQL API | Nuxt payload in HTML | Embedded `js-store` JSON in HTML (+ `og:`/JSON-LD fallback) |
| Formats | Many (progressive/HLS, "Original" if downloadable) | mp3 + original | Stream via obfuscated URL decryption | `audio`/`lossy`/`lossless` direct URLs | `mp3` + `m4a` direct, signed, 6-day URLs |
| Anti-bot | Occasional impersonation | None | None | None | Impersonation required for page fetch only |
| Stats/social fields | likes, reposts, comments | none | likes, reposts, comments, views | none | views, likes, comments, shares via `stats` |
| Original-file gate | `downloadable` flag | n/a | n/a | tier URL present | Honor `downloadable` (when `wv` ever supported) |
| Lines of code | ~1360 | ~570 | ~370 | 83 | Target roughly 80-120 (Whyp-sized) |

## Sources

- yt-dlp `master` (`f264a6c`, 2026-10-26), read via GitHub API: `yt_dlp/extractor/{soundcloud,bandcamp,mixcloud,audiomack,hearthisat,whyp,audius}.py`, `extractor/common.py` (info-dict field docs), `utils/_utils.py` (`MEDIA_EXTENSIONS`, `_UnsafeExtensionError.ALLOWED_EXTENSIONS`: no `wv`), `postprocessor/ffmpeg.py` (`ACODECS`: no wavpack), `CONTRIBUTING.md` (mandatory vs optional metafields, `_TESTS`, ruff, policy). HIGH.
- GitHub search (issues, PRs, discussions, code, repos) for audio.com across yt-dlp, gallery-dl, cobalt, youtube-dl, metube and all of GitHub: 0 downloader/extractor results. [yt-dlp#6913 whyp.it](https://github.com/yt-dlp/yt-dlp/issues/6913) precedent. HIGH.
- Live probes of audio.com (2026-10-28): `https://api.audio.com/oembed`, `/v1/docs`, `/v1/openapi.json`, `/.well-known/oauth-authorization-server`, the reference track page and embed page (via `curl_cffi` chrome impersonation), signed CDN URLs. HIGH (direct observation, one track only).
- [iamcal/oembed audiocom.yml](https://github.com/iamcal/oembed/blob/master/providers/audiocom.yml), [mindscaper-org/Soundscaper audio.com notes](https://github.com/mindscaper-org/Soundscaper/blob/main/docs/research/audio-com-project-sync.md), [audacity/audacity au3-cloud-audiocom](https://github.com/audacity/audacity/tree/master/au3/libraries/au3-cloud-audiocom). MEDIUM (third-party, corroborated by live probes).
- Web searches for "audio.com downloader / yt-dlp / userscript": nothing found. MEDIUM (absence of evidence).

## Gaps / confidence caveats

- Only **one** audio.com track was inspected. Field presence on other tracks (artwork, description, genres, `downloadable:true`, tracks with only a WavPack source) is unverified. Phase 1 should sample 5 or more diverse tracks, including one that is `downloadable:true` and one with artwork.
- The "`.wv` rejected by `_UnsafeExtensionError`" conclusion is from reading source, not running yt-dlp. Confirm empirically in the formats phase.
- Whether the `js-store` JSON shape is stable across site releases (`audio-web_app_1.00.35` seen) is unknown, so keep the JSON-LD/`og:` fallback for title and mp3 URL.
- The `downloadable:false` policy question (whether to ever expose the source file) is a decision for the user, not a research finding.

---
*Feature research for: yt-dlp single-track audio-host extractor (audio.com)*
*Researched: 2026-10-28*
