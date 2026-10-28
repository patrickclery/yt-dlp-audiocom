# Phase 2: Edge Cases and Version Compatibility - Research

**Researched:** 2026-10-28
**Domain:** yt-dlp plugin extractor hardening (audio.com `sources[]`, error mapping), live `_TESTS` harness on two pinned yt-dlp versions
**Confidence:** HIGH. Every behavioral claim below was exercised live this session on yt-dlp 2026.8.19 (`.venv-metube`) and 2026.10.26 (`.venv`), except where it is tagged `[ASSUMED]`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Original upload, errors & test command
- `sources[]` emitted only when `is_downloadable is True`; never otherwise (EXTR-04)
- Original is opt-in, NOT the default: give it `format_id` starting `original` (e.g. `original` / `original-wav`) and a `quality`/preference lower than the transcodings so default selection still picks the highest-bitrate transcoding (Phase 1 decision stands). User requests it with `-f original`
- WavPack (`wv`) sources are skipped (not in yt-dlp's allowed extensions); wav/mp3/m4a originals are offered. Emit a `to_screen`/debug note when a `wv` original is skipped
- Errors: oEmbed 404 or API 404 → `ExtractorError('This audio.com track is unavailable (removed, private, or wrong URL)', expected=True)`; where the API distinguishes private (e.g. `is_public: false`, 403) use a more specific expected message. No traceback, no "please report this issue"
- Live test command: `scripts/test-live.sh` runs the extractor's `_TESTS` against each venv (`.venv` = 2026.10.26, `.venv-metube` = 2026.8.19) using the approach from Phase 1 RESEARCH (`load_all_plugins()` + the matching version's `test/test_download.py -k AudioCom` from a writable temp dir; git tags are zero-padded). Documented in README

#### Version compatibility
- Exact pins only: yt-dlp==2026.8.19 and yt-dlp==2026.10.26; no nightly
- Private/unlisted behavior probed anonymously only; no account login, no creating test tracks. Record observed responses in RESEARCH
- Live `_TESTS` use only the reference track and the 2023 `jasa-sisemore/...` track; other sampled tracks stay offline-fixture-only

### Claude's Discretion
- Exact `format_id` naming for originals, README layout, script internals

### Deferred Ideas (OUT OF SCOPE)
- WavPack originals (needs core yt-dlp change)
- Collections, profiles, embed URLs — v2
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXTR-04 | Original upload (`sources`) offered only when the track is flagged downloadable; never otherwise | `sources[]` shape on 22 tracks (Finding 2). Signed source URLs download **without auth even when `is_downloadable` is false**, so the gate is the only control. Prototype gate, `format_id: 'original'` and `preference: -10` verified on both versions, including real `-f original` downloads (Code Examples) |
| EXTR-06 | Unavailable/private/removed tracks fail with a clear `ExtractorError` | Every anonymous failure observed is HTTP 404 with a JSON body (Finding 1). `is_public: false` is **unlisted and fully playable**, not private. The official API states "There are no private audio." Mapping verified on both versions as a one-line `ERROR: [AudioCom] <id>: …` |
| PLUG-02 | `yt-dlp -v` lists the plugin; works on 2026.08.19 and current stable | `[debug] Extractor Plugins: AudioComIE` observed on both venvs. `test-live.sh` checks it (Finding 5) |
| PLUG-03 | `_TESTS` cover the reference URL plus ≥1 other track; a local command runs them | The jasa-sisemore `info_dict` values were captured live. 3 harness tests (`test_AudioCom`, `_1`, `_all`) passed on both versions. A full `scripts/test-live.sh` recipe ran end-to-end with exit 0 on both (Finding 5) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python plus the yt-dlp `InfoExtractor` API. Write for Python 3.11 syntax; the image runs 3.13.15.
- The plugin must load in MeTube's bundled yt-dlp **2026.08.19** via a volume mount, with no image rebuild.
- No new hard dependencies. Never import `curl_cffi`/`requests` in the extractor. No impersonation on this data path.
- Plugin imports must be absolute (`from yt_dlp...`). No `__init__.py` in `yt_dlp_plugins/` or `yt_dlp_plugins/extractor/`.
- Zero import-time work, because every plugin is imported on every yt-dlp run.
- No `print()` in the extractor. Use `self.to_screen` / `self.write_debug` / `self.report_warning`.
- Class name stays `AudioComIE`. Keep the "DELETE THIS FILE once built-in exists" header.
- **No agent-authored upstream yt-dlp code, PR text or issues.** Plugin-only scope.
- `_TESTS` must not hard-code signed URLs or `md5`.
- GSD workflow: edits go through `/gsd-execute-phase`.
- User global: dotfiles under `~/.config` are managed by chezmoi. Not relevant here, because the cache dir in `~/.cache` is not chezmoi-managed.

## Summary

The audio.com API has three variants that Phase 1 did not cover, and they change the plan. (1) `is_public: false` means **unlisted**. Such tracks are fully playable anonymously: 9 of 11 tracks harvested from the Audacity forum had `is_public: false` and all returned 200 with transcodings. The public API spec says "There are no private audio." So the extractor must **not** raise on `is_public: false`. The CONTEXT example ("e.g. `is_public: false`") rests on a false premise and has to be dropped. (2) **Multi-version tracks**: a track can carry several `sources[]` (re-uploads), each with its own transcodings. The site plays the newest source. The current extractor lists stale-version formats and takes `duration` from the old version: on `anonymous-audio/.../louder-jazz-bababa` it reports 240.024 s for a 314 s track. (3) The `sources[]` metadata cannot always be trusted. On one downloadable track, a `format: "wav"` source with `codec: "wavpack"` is served as a 24-bit PCM WAV of 2,843,736 bytes, while the API says 1,037,708. On another (arthur-hpcp), the source object returns S3 `NoSuchKey` 404 although `is_downloadable` is true.

Every anonymous failure observed is a JSON **404**. That covers an unknown slug, an unknown user, an unknown numeric id, a malformed id and an uppercase URL. 403 and 410 were never observed. WavPack really does fail: `ERROR: The extracted extension ('wv') is unusual and will be skipped for safety reasons` on both versions. `wav`, `mp3` and `m4a` are allowed and downloaded fine. The selection policy "original is opt-in" works with `preference: -10`: default `best`, `ba`, `-S abr` and `-S size` all still pick a transcoding, and only `-f original` selects it, on both versions.

The live-test recipe runs end-to-end on both versions (exit 0). It does three things: a sparse `git clone` of only `test/` at the zero-padded tag, pinned to the tag's commit SHA; a `run_live_tests.py` wrapper that calls `load_all_plugins()` before pytest imports `test_download.py`; and a real full download of the reference track. Two traps came up while building it. First, `yt-dlp … | grep -q` under `set -o pipefail` reports failure through SIGPIPE. Second, a full (non-sparse) clone would put the clone's own `yt_dlp/` ahead of the installed one on `sys.path`.

**Primary recommendation:** Pick the newest source and keep only its transcodings. Emit one `format_id: 'original'` with `preference: -10`, only when `is_downloadable is True`, the ext is in `KNOWN_EXTENSIONS`, and a `Range: bytes=0-0` probe succeeds. Map 404/410 to the locked message and 401/403 to a defensive "private or restricted" message. Never error on `is_public`. Extend the recorder allowlist to `sources[]`, `source_id`, `is_downloadable` and `is_public`, and re-record all fixtures plus 4 new ones. Ship `scripts/test-live.sh` and `scripts/run_live_tests.py` as verified below.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Current-version selection (`sources[]` / `transcodings[].source_id`) | Extractor (`_real_extract`) | — | Pure JSON shaping; the site's player logic has to be mirrored |
| Original-upload gating (EXTR-04) | Extractor | yt-dlp format selector (`-f original`) | The policy lives in the extractor; selection is yt-dlp core |
| Unusual-extension safety (`wv`) | Extractor (skip) | yt-dlp core `_UnsafeExtensionError` | Skip it before core rejects it at download time |
| Error mapping (EXTR-06) | Extractor `_call_api` | yt-dlp `InfoExtractor.extract()` wrapper | Expected errors print one line with no traceback |
| Live `_TESTS` comparison | yt-dlp `test/test_download.py` + `test/helper.py` (version-matched) | `scripts/run_live_tests.py` wrapper | Same semantics maintainers use |
| Harness acquisition and version matrix | `scripts/test-live.sh` (bash, git) | user cache dir | Outside the repo; pinned by tag and SHA |
| Offline regression | pytest `tests/` + recorded fixtures | `scripts/record_fixture.py` | No network in the default suite |

## Standard Stack

### Core (no change from Phase 1)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| yt-dlp | ==2026.10.26 (`.venv`), ==2026.8.19 (`.venv-metube`) | Target runtime, plus the test harness at matching tags `2026.10.26` / `2026.08.19` | Locked pins [VERIFIED: `yt_dlp.version.__version__` printed `2026.10.26` / `2026.08.19` in each venv] |
| pytest | ==9.1.1 | Offline suite and the harness runner | Approved pin; it honors the harness's native `[tool.pytest]` table [VERIFIED: harness run printed `configfile: pyproject.toml`] |
| hatchling | ==1.32.4 | Editable install | Approved pin |
| git, bash | system | Fetch harness `test/` and run the script | Present (`/usr/bin/git`) |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `ffprobe` (optional) | Inspect downloaded originals in manual checks | Not required by `test-live.sh` |
| `yt_dlp.utils.KNOWN_EXTENSIONS` | Accept-list for the original's ext | Already imported in the extractor |
| `InfoExtractor._is_valid_url(url, id, item, headers=)` | One-byte probe of the original | Downloadable tracks only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sparse git clone of `test/` | PyPI sdist `yt_dlp-<ver>.tar.gz` (contains `test/`, verified in Phase 1) | Needs a pip/uv download or a PyPI URL lookup. Version strings are not zero-padded (`2026.8.19`). Fallback only |
| `preference: -10` | `quality: -1` | With `quality: -1`, `-S abr` / `-S size` pick the original (verified). That conflicts with "opt-in" |
| Range probe of the original | No probe | Saves one request on downloadable tracks, but `-f original` then fails at download time on broken sources (1 of 6 downloadable sampled) |

**Installation:** none. No new packages.

## Package Legitimacy Audit

This phase installs no new packages. The venvs already contain only the approved pins (yt-dlp 2026.10.26 / 2026.8.19, pytest 9.1.1, hatchling 1.32.4), audited in Phase 1. The harness is test source code fetched by git at a pinned tag and commit SHA. It is not installed.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none new) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none new. Phase 1 flagged yt-dlp as seam-SUS (it is the target program itself, pinned exactly).

## Live Findings

### Finding 1: Error responses (anonymous, this session)

[VERIFIED: live probes through yt-dlp's own `urlopen`, 2026-10-28; bodies quoted verbatim]

| Request | Status | Body |
|---------|--------|------|
| oEmbed, existing user, nonexistent slug | 404 | `{"name": "Not Found", "message": "Resource not found!", "code": 0, "status": 404}` |
| oEmbed, nonexistent user | 404 | same `"Resource not found!"` |
| oEmbed, uppercase slug (not canonicalized) | 404 | `{"name": "Not Found", "message": "Unknown url type", "code": 0, "status": 404}` |
| oEmbed, non-audio.com URL | 404 | `"Unknown url type"` |
| oEmbed, no `url` param | 400 | `{"name": "Bad Request", "message": "Missing required parameters: url", "code": 0, "status": 400}` |
| `/audio/1`, `/audio/0`, `/audio/9999999999999999`, `/audio/<ref id + 1>` | 404 | `{"name": "Not Found", "message": "Audio not found!", "code": 0, "status": 404}` |
| `/audio/abc` | 404 | `{"name": "Not Found", "message": "Page not found.", "code": 0, "status": 404, "previous": {…"Invalid Route"…}}` |
| oEmbed of `https://audio.com/embed/audio/<id>` | 200 | full oEmbed (v2 note only) |

**Private / unlisted:**
- The official public API spec (`https://api.audio.com/v1/openapi.json`, re-fetched this session, HTTP 200) states verbatim: "Unlisted audio are not published anywhere — anyone with the direct URL can still listen, and only the owner sees them in their library. There are no private audio." [CITED: api.audio.com/v1/openapi.json]
- 9 of 11 forum-linked tracks have `is_public: false`. All 9 return oEmbed 200 and `/audio/<id>` 200 with playable transcodings. The current extractor already extracts one of them (`anonymous-audio/audio/louder-jazz-bababa`). [VERIFIED: live]
- So `is_public` is the internal name of v1's `is_listed`. **Do not raise on `is_public: false`.** [VERIFIED for behavior; the field-name mapping is ASSUMED]
- 403 and 410 were never observed. A deleted track could not be found anonymously (all ~20 harvested links are alive). Removed tracks are expected to 404 like unknown ones. [ASSUMED]

**Current CLI output** (both versions, Phase 1 code): `ERROR: [AudioCom] Track not found, private, or removed`, exit 1. There is no traceback, but the `<id>:` prefix is missing because `_VALID_URL` has no `id` group, so `get_temp_id()` returns None [VERIFIED: venv `yt_dlp/extractor/common.py:638-642,780-783`]. Pass `video_id=` explicitly. The prototype then prints `ERROR: [AudioCom] this-slug-does-not-exist-zz9: This audio.com track is unavailable (removed, private, or wrong URL)` on both versions. [VERIFIED: live]

### Finding 2: `sources[]` shapes (22 tracks)

[VERIFIED: live `/audio/<id>`. URLs reduced to basename; no query strings recorded]

Entry keys: `bit_rate, channels, codec, date_created, date_updated, date_uploaded, download, duration, format, from, id, md5, name, sample_rate, size, type, url` (+ `waveform`).
- `url` and `download` point at the **same S3 object**. `download` only adds `response-content-disposition=attachment; filename="<name>"`. Use `url`. Never record `download` or `name`, because `name` is the uploader's original filename.
- Both are SigV4-presigned (`X-Amz-Expires=518400`). **A GET with `Range` works without auth, even for `is_downloadable: false` tracks** (206 for the non-downloadable `wv` and `wav` originals). The gate is policy, not access control. A `HEAD` returns **403**, because the signature binds the method. Probe with `GET` + `Range: bytes=0-0`.

| format / codec / type | `from` | Seen on | Served bytes |
|---|---|---|---|
| `wv` / `wavpack` / `audio/x-wavpack` | `audacity` | reference, beards-and-banter, davidmoreno, james-gant, plimbus (all `is_downloadable: false`) | WavPack (`wvpk` magic) |
| `wav` / `pcm_s16le` (or `pcm_f32le`) / `audio/wav` | `audiocom` | jasa-sisemore, 7 anonymous-audio tracks (all dl=false) | RIFF/WAVE PCM; size matches API |
| `wav` / **`wavpack`** / `audio/wav` | `audiocom` | andrea-mathiopoulos (dl=**true**) | **24-bit PCM WAV, 2,843,736 bytes vs API `size` 1,037,708**. The path is under `/transcoding/`, so audio.com converted the file server-side |
| `mp3` / `mp3` / `audio/mpeg` | `audiocom` | roshimakr21, shivgas, jetlocksmithsau (dl=true); helena, stefaniecg, sterling (dl=false) | MP3, size matches |
| `m4a` / `aac` / `audio/m4a` | `audiocom` | arthur-hpcp, alec-murray (dl=true) | alec: AAC, 331,730 bytes = API size. **arthur: S3 `NoSuchKey` 404** |

The v1 spec lists the upload formats as "wav, mp3, flac, wavpack, aiff, ogg, m4a" [CITED: api.audio.com/v1/openapi.json]. flac, aiff and ogg were not observed, but they are in `KNOWN_EXTENSIONS`.

**Multi-version tracks** [VERIFIED: live]:
- `stefaniecg/audio/beso` (1858402410391836): 2 sources (`…459955` created 1772310648, `…105810` created 1772449738). Transcodings: mp3 → old source; mp3 and m4a → new source.
- `anonymous-audio/audio/louder-jazz-bababa` (1772828397072996): 2 sources (240 s, created 1690700910; 314 s, created 1690909118). One mp3 transcoding per source.
- The web page's `og:audio:url` (fetched once with chrome impersonation, research-only) points at the **newest source's** transcoding on both tracks. On beso, only the new source's transcodings appear in the HTML.
- Current Phase 1 output for louder-jazz: `duration= 240.024`, formats `mp3-0` (old) and `mp3-1` (new). yt-dlp auto-renames duplicate ids [VERIFIED: venv-metube `YoutubeDL.py:3001-3016`].
- Prototype output: `dur=314.088`, a single `mp3` format. beso: `dur=173.035`, `mp3` + `m4a`.
- In all 20 single-source tracks, every transcoding's `source_id` equals the only source's `id`.

### Finding 3: Unsafe extensions (real runs, both versions)

[VERIFIED: venv `yt_dlp/utils/_utils.py:5123-5204` read this session; scratch run through `YoutubeDL.process_ie_result(download=True)` against a local HTTP server]

- `MEDIA_EXTENSIONS.audio` (both versions) is `('aac', 'ape', 'asf', 'f4a', 'f4b', 'm4b', 'm4r', 'oga', 'ogx', 'spx', 'vorbis', 'wma', 'weba', 'aiff', 'alac', 'flac', 'm4a', 'mka', 'mp3', 'ogg', 'opus', 'wav')`. `wv` is in neither `KNOWN_EXTENSIONS` nor `ALLOWED_EXTENSIONS`.
- `ext: 'wv'` fails on both versions: `ERROR: The extracted extension ('wv') is unusual and will be skipped for safety reasons. If you believe this is an error, please report this issue on  https://github.com/yt-dlp/yt-dlp/issues?q= …` (`DownloadError`). That is the "report this issue" text the phase forbids, so skip `wv` in the extractor.
- `ext: 'wav'` downloads normally on both versions.
- The existing ext rule (`format` label, else `mimetype2ext(type)`, keep only if in `KNOWN_EXTENSIONS`) already rejects `wv` without a special case.

### Finding 4: Format ranking of the original (both versions)

[VERIFIED: venv `yt_dlp/utils/_utils.py:5363-5365` default sort `('hidden', 'aud_or_vid', 'hasvid', 'ie_pref', 'lang', 'quality', …)`, `:5392` `'ie_pref': {'priority': True, 'type': 'extractor'}`, `:5396` `'quality': {'convert': 'float', 'default': -1}`; scratch run]

| Original carries | default | `-f original` | `-S abr` | `-S size` | `-f ba` |
|---|---|---|---|---|---|
| `quality: -1` | mp3 | original | **original** | **original** | mp3 |
| `preference: -10` | mp3 | original | mp3 | mp3 | mp3 |

Use `preference: -10`. `ie_pref` has priority, so user `-S` cannot promote the original, which keeps it opt-in. Use the exact `format_id: 'original'`, because `-f original` does not match `original-wav`. With one current source there is exactly one original, so no suffix is needed.

### Finding 5: Live `_TESTS` harness (verified recipe)

[VERIFIED: `git ls-remote` + sparse clones; runs on both venvs this session]

- Tags (zero-padded) and their commits: `2026.08.19` → `3a08beaf031ab68f966401ead017ac81fe8486cf`, `2026.10.26` → `f264a6cbd1f630894da0f368df00f8aae50140e0`. `refs/tags/2026.8.19` does not exist.
- `yt_dlp.version.__version__` prints the zero-padded form (`2026.08.19`), so it can be used directly as the tag.
- `git clone --depth 1 --branch <tag> --filter=blob:none --sparse … && git sparse-checkout set test` gives root files + `test/` (1.1 MB) and **no `yt_dlp/`**. This is required: `test/test_download.py:8` does `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`, so a full clone would shadow the installed yt-dlp.
- The harness `pyproject.toml` has `[tool.pytest]` with `strict_config = true`, `strict_markers = true`, `markers = ["download"]`. pytest 9.1.1 picks it up as rootdir/configfile. No extra plugins are needed.
- `test_download.py` builds its methods at import time via `gen_extractors()`, so `load_all_plugins()` must run first (Phase 1 finding; re-verified).
- `test_download.py` and `helper.py` differ between the two tags (e.g. `assertGreaterEqual` helpers removed in 10.26). Always pair a venv with its own tag.
- With the jasa entry injected into `_TESTS`, both versions printed `test_AudioCom PASSED`, `test_AudioCom_1 PASSED`, `test_AudioCom_all PASSED`, "3 passed" in about 3.5 s. The cwd was left empty afterwards because the harness cleans up its files.
- The full `test-live.sh` (below) printed `ok: plugin listed`, `2 passed`, and `ok: downloaded 7169078 bytes` (= API m4a size) on both venvs, exit 0.
- Values for `_TESTS[1]`, captured live with `yt-dlp -j` through the plugin: `id '1782423994666898'`, `ext 'mp3'`, `display_id 'jasasisemore-audacitypractice-autoduck-assignment-4aup'`, `title 'JasaSisemore_AudacityPractice_AUTODUCK_assignment 4.aup'`, `uploader 'Jasa Sisemore'`, `uploader_id 'jasa-sisemore'`, `uploader_url 'https://audio.com/jasa-sisemore'`, `duration 44.722`, `timestamp 1699851984`, `upload_date '20231113'`, `tags` (5 items), counts all `0` (use `int`), no thumbnail, no description.

## Architecture Patterns

### System Architecture Diagram

```
URL ──► _VALID_URL (user, slug) ──► canonical lowercase URL
          │
          ▼
  GET api.audio.com/oembed?url=…  ──404/410──►  ExtractorError(expected, "unavailable …", video_id=slug)
          │ 200                     ──401/403──►  ExtractorError(expected, "private or restricted")
          ▼
  iframe_url → track_id ──(none)──► ExtractorError(expected)
          ▼
  GET api.audio.com/audio/<id>  ──404/410/401/403──► same mapping (video_id=track_id)
          │ 200 (is_public true OR false: both proceed)
          ▼
  current = newest sources[] by date_created (tie → last)
          ▼
  transcodings where source_id == current.id   (fallback: all transcodings)
          │──► formats[] mp3/m4a (quality = abr)          ──none──► "No playable transcodings"
          ▼
  is_downloadable is True?  ──no──► (no original)
          │ yes
  ext(current) in KNOWN_EXTENSIONS? ──no (wv)──► write_debug("Skipping original upload …")
          │ yes
  GET current.url Range: bytes=0-0 ──fail──► to_screen("… original upload URL is invalid, skipping")
          │ 2xx
  formats += {format_id: 'original', preference: -10, …}
          ▼
  info dict (duration from first current transcoding) ──► yt-dlp sort/select ──► download
```

### Recommended Project Structure (additions)
```
scripts/
├── record_fixture.py      # extend allowlist: sources[], source_id, is_downloadable, is_public
├── run_live_tests.py      # NEW: load_all_plugins() + harness pytest (verified)
└── test-live.sh           # NEW: version matrix, harness fetch, -v check, _TESTS, real download
tests/
├── fixtures/              # re-record all 8 and add 4 (see Fixtures)
├── test_sources_offline.py   # NEW: EXTR-04 + version selection
└── test_errors_offline.py    # NEW (or extend test_extract_offline.py): EXTR-06 mapping
README.md                  # NEW: install, offline tests, live tests (Phase 3 extends it)
```

### Pattern 1: Newest-source selection
**What:** Pick the source with the max `date_created`, breaking ties with the last list entry. Keep only its transcodings. Take duration from the first kept transcoding.
**When:** Always. For single-source tracks it is a no-op. With missing `sources` or `source_id` it falls back to all transcodings, so old fixtures keep working.

### Pattern 2: Opt-in original
**What:** One `format_id: 'original'` with `preference: -10` and `format_note: 'original upload'`. It is added only when `is_downloadable is True`, the ext is known, and the Range probe passes.
**Metadata rule:** if `codec == 'wavpack'`, the served file is a server-side conversion, so omit `acodec`, `abr` and `filesize` (the API values describe the wavpack file). Keep `asr` and `audio_channels`, which matched.

### Pattern 3: Offline tests must block the probe request
`_is_valid_url` → `_request_webpage` is a **second network path** that `patch_api` (which only patches `_download_json`) does not intercept. conftest must also patch `AudioComIE._request_webpage`, or `_is_valid_url`, to fail by default, plus a helper to make the original reachable or broken. Otherwise the offline suite hits S3 with stripped, unsigned URLs, gets 403, and silently drops the original.

### Anti-Patterns to Avoid
- **Raising on `is_public: false`:** this breaks every unlisted track, which is most of the forum sample.
- **Using `download` instead of `url`**, or recording `name`: it leaks the uploader filename into fixtures and adds a content-disposition query.
- **`HEAD` to check the original:** it gets 403 on SigV4 GET-signed URLs.
- **`format_id: 'original-wav'`:** `-f original` stops working.
- **`quality: -1` for the original:** `-S abr` / `-S size` then auto-pick it.
- **Full clone of yt-dlp for the harness:** its `yt_dlp/` shadows the installed version.
- **`cmd | grep -q` under `set -o pipefail`:** grep's early exit gives the writer SIGPIPE, and the pipeline reports failure (observed: `FAIL: AudioComIE not in 'Extractor Plugins'` while the line was present). Capture to a variable first.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| `_TESTS` comparison | Custom comparator | Version-matched `test/test_download.py` via `run_live_tests.py` | Same semantics as upstream; verified for plugins |
| Duplicate format ids | Manual suffixing | yt-dlp core (`mp3-0`, `mp3-1`) | Already in core on both versions; irrelevant once versions are filtered |
| URL liveness probe | Raw `urlopen` | `self._is_valid_url(url, id, 'original upload', headers={'Range': 'bytes=0-0'})` | Honors proxy/cookies/UA; prints a clean skip line |
| Ext safety list | Hard-coded `('mp3','m4a','wav')` | `KNOWN_EXTENSIONS` membership | Already used for transcodings; covers flac/aiff/ogg |
| Harness version pin | Downloading tarballs by hand | `git clone --sparse` at tag + `rev-parse HEAD` SHA check | Reproducible and tamper-evident |

## Common Pitfalls

### Pitfall 1: Stale versions and wrong duration
**What goes wrong:** Multi-version tracks list old-version formats, and `duration` comes from the old upload (240 s vs 314 s).
**How to avoid:** Pattern 1, plus fixtures 1772828397072996 and 1858402410391836.
**Warning sign:** Duplicate `mp3-0` / `mp3-1` ids in `-F`.

### Pitfall 2: Treating `is_public` as access control
**What goes wrong:** Unlisted tracks error out. **Avoid:** never read `is_public` for control flow. Record it in fixtures only to prove that.

### Pitfall 3: Trusting `sources[]` metadata
**What goes wrong:** `filesize`/`acodec` are wrong for wavpack→wav conversions, and some originals are missing on S3. **Avoid:** the Pattern 2 metadata rule plus the Range probe.

### Pitfall 4: Existing tests that will break (update them on purpose; do not delete coverage)
- `tests/test_extract_offline.py:39-56` `test_formats_mirror_transcodings` asserts `len(info['formats']) == len(playable)` and `f['format_id'] == f['ext']` for every format. With originals and version filtering, compare against current-source transcodings only, excluding `format_id == 'original'`. [VERIFIED: Read this session]
- `tests/test_metadata_offline.py:26-40` asserts `info['duration'] == audio['transcodings'][0]['duration'] / 1000 == duration`. That changes to "first transcoding of the current source". [VERIFIED: Read this session]
- `tests/test_extract_offline.py:153-157` `test_edge_404_is_expected_error` still passes. Extend it to assert the exact locked message and the `video_id`.
- Phase 1's message `'Track not found, private, or removed'` (`yt_dlp_plugins/extractor/audiocom.py:64`) is replaced by the locked text. [VERIFIED: Read this session]

### Pitfall 5: Offline suite leaking to the network
See Pattern 3. Add a test that fails if `_request_webpage` is called for a non-downloadable fixture.

### Pitfall 6: Harness or venv mismatch
**What goes wrong:** Running 10.26's `test_download.py` on 8.19 can break on helper changes. **Avoid:** the script asserts `__version__ == tag` per venv and pins the SHA.

### Pitfall 7: Sandbox paths during execution
`mktemp -d` honors `TMPDIR`, and the harness cache honors `AUDIOCOM_HARNESS_DIR`. The executor must set both to the session scratchpad (verified that way here).

## Code Examples

### Extractor changes (prototype run live on both versions; scratch copy, not committed)
```python
# _call_api: map HTTP errors (verified output: "ERROR: [AudioCom] <id>: This audio.com track is unavailable …")
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in (404, 410):
                raise ExtractorError(
                    'This audio.com track is unavailable (removed, private, or wrong URL)',
                    video_id=video_id, expected=True)
            if isinstance(e.cause, HTTPError) and e.cause.status in (401, 403):  # never observed; defensive
                raise ExtractorError(
                    'This audio.com track is private or restricted', video_id=video_id, expected=True)
            raise

# _real_extract, after the id check: newest source wins (site plays it)
        sources = traverse_obj(data, ('sources', lambda _, v: v['id']))
        current = max(reversed(sources), key=lambda s: int_or_none(s.get('date_created')) or 0, default=None)
        current_id = traverse_obj(current, ('id', {str_or_none}))
        transcodings = traverse_obj(data, ('transcodings', lambda _, v: url_or_none(v['url'])))
        if current_id:
            transcodings = [t for t in transcodings
                            if str_or_none(t.get('source_id')) == current_id] or transcodings
        # ... existing per-transcoding format loop over `transcodings` ...

        # EXTR-04: original only when the uploader allows downloads
        if data.get('is_downloadable') is True and url_or_none(traverse_obj(current, 'url')):
            ext = next((e for e in (
                traverse_obj(current, ('format', {str}, {str.lower})),
                mimetype2ext(traverse_obj(current, ('type', {str}))),
            ) if e in KNOWN_EXTENSIONS), None)
            if not ext:
                self.write_debug(f'Skipping original upload: unsupported format {current.get("format")!r}')
            elif self._is_valid_url(current['url'], track_id, 'original upload', headers={'Range': 'bytes=0-0'}):
                converted = traverse_obj(current, ('codec', {str})) == 'wavpack'  # served as PCM wav
                formats.append({
                    'url': current['url'],
                    'format_id': 'original',
                    'format_note': 'original upload',
                    'ext': ext,
                    'vcodec': 'none',
                    'preference': -10,
                    **({} if converted else traverse_obj(current, {
                        'acodec': ('codec', {str}),
                        'abr': ('bit_rate', {lambda x: float_or_none(x, 1000)}),
                        'filesize': ('size', {int_or_none}),
                    })),
                    **traverse_obj(current, {
                        'asr': ('sample_rate', {int_or_none}),
                        'audio_channels': ('channels', {int_or_none}),
                    }),
                })
        # duration: traverse_obj(transcodings, (0, 'duration', {lambda x: float_or_none(x, 1000)}))
```
The prototype was verified on both versions. Reference and jasa have no original. arthur-hpcp prints `original upload URL is invalid, skipping: HTTP Error 404: Not Found`. andrea `-f original` gives a `.wav` of 2,843,736 bytes, `pcm_s24le,44100,2`. alec-murray `-f original` gives an `.m4a` of 331,730 bytes, `aac,44100,1`. `-f original` on arthur gives `ERROR: [AudioCom] 1861573231849291: Requested format is not available.` (The prototype used `max(sources…)`. `reversed()` is the tie-break refinement and is untested live, though neither sampled track has a tie.) `write_debug` was used for the `wv` note; it fires only on downloadable `wv` tracks, which were not observed live, so it is offline-only.

### `_TESTS[1]` (values captured live)
```python
    }, {
        'url': 'https://audio.com/jasa-sisemore/audio/jasasisemore-audacitypractice-autoduck-assignment-4aup',
        'info_dict': {
            'id': '1782423994666898',
            'ext': 'mp3',
            'display_id': 'jasasisemore-audacitypractice-autoduck-assignment-4aup',
            'title': 'JasaSisemore_AudacityPractice_AUTODUCK_assignment 4.aup',
            'uploader': 'Jasa Sisemore',
            'uploader_id': 'jasa-sisemore',
            'uploader_url': 'https://audio.com/jasa-sisemore',
            'duration': 44.722,
            'timestamp': 1699851984,
            'upload_date': '20231113',
            'tags': 'count:5',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {   # existing only_matching entry stays last
```

### `scripts/run_live_tests.py` (verified on both versions)
```python
"""Run AudioComIE._TESTS through yt-dlp's own test/test_download.py harness.

Usage: python scripts/run_live_tests.py <harness-root> [pytest -k expr] [extra pytest args]
<harness-root> must hold test/test_download.py from the SAME yt-dlp version and no yt_dlp/.
"""
import os
import sys

import pytest
from yt_dlp.plugins import load_all_plugins

load_all_plugins()  # test_download.py builds methods from gen_extractors() at import

harness = sys.argv[1]
if os.path.isdir(os.path.join(harness, 'yt_dlp')):
    sys.exit(f'{harness} contains yt_dlp/; use a test-only (sparse) checkout')
sys.exit(pytest.main([
    os.path.join(harness, 'test', 'test_download.py'), '-p', 'no:cacheprovider',
    '-k', sys.argv[2] if len(sys.argv) > 2 else 'AudioCom', *sys.argv[3:]]))
```

### `scripts/test-live.sh` (verified: exit 0 on both venvs)
```bash
#!/usr/bin/env bash
# Live check: run AudioComIE._TESTS and one real download on every target yt-dlp.
# Usage: scripts/test-live.sh   (network; ~10 s per venv)
# Env: AUDIOCOM_HARNESS_DIR (default ~/.cache/yt-dlp-audiocom/harness), TMPDIR (work dirs)
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CACHE=${AUDIOCOM_HARNESS_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/yt-dlp-audiocom/harness}
REF_URL='https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best'
REF_ID=1877766681285368
TARGETS=(  # venv  yt-dlp version (= zero-padded git tag)  tag commit
  ".venv        2026.10.26 f264a6cbd1f630894da0f368df00f8aae50140e0"
  ".venv-metube 2026.08.19 3a08beaf031ab68f966401ead017ac81fe8486cf"
)

harness() {  # $1=tag $2=sha -> prints harness root
  local dir="$CACHE/$1"
  if [[ ! -f "$dir/test/test_download.py" ]]; then
    rm -rf "$dir"
    git -c advice.detachedHead=false clone -q --depth 1 --branch "$1" --filter=blob:none --sparse \
      https://github.com/yt-dlp/yt-dlp "$dir" >&2
    git -C "$dir" sparse-checkout set test >&2
  fi
  [[ "$(git -C "$dir" rev-parse HEAD)" == "$2" ]] || { echo "harness $1 is not commit $2" >&2; return 1; }
  printf '%s\n' "$dir"
}

fail=0
for t in "${TARGETS[@]}"; do
  read -r venv want sha <<<"$t"
  py="$ROOT/$venv/bin/python"
  echo "=== $venv (yt-dlp $want)"
  have=$("$py" -c 'import yt_dlp.version as v; print(v.__version__)')
  [[ "$have" == "$want" ]] || { echo "FAIL: $venv has yt-dlp $have, expected $want"; fail=1; continue; }
  dir=$(harness "$want" "$sha") || { fail=1; continue; }
  work=$(mktemp -d)
  # 1) PLUG-02: plugin listed. Capture first: `| grep -q` + pipefail fails via SIGPIPE
  dbg=$("$ROOT/$venv/bin/yt-dlp" -v --ignore-config --simulate "$REF_URL" 2>&1 || true)
  if grep -Eq 'Extractor Plugins: .*\bAudioComIE\b' <<<"$dbg"; then
    echo "ok: plugin listed"; else echo "FAIL: AudioComIE not in 'Extractor Plugins'"; fail=1; fi
  # 2) PLUG-03: _TESTS via yt-dlp's harness, from a writable throwaway cwd
  (cd "$work" && "$py" "$ROOT/scripts/run_live_tests.py" "$dir" AudioCom) || fail=1
  # 3) one real full download of the default format
  if (cd "$work" && "$ROOT/$venv/bin/yt-dlp" --ignore-config -q --no-progress -o '%(id)s.%(ext)s' "$REF_URL") \
     && [[ -s "$work/$REF_ID.m4a" ]]; then
    echo "ok: downloaded $(stat -c %s "$work/$REF_ID.m4a") bytes"; else echo "FAIL: real download"; fail=1; fi
  rm -rf "$work"
done
exit "$fail"
```
Possible additions at the planner's discretion: an `--offline` step that runs `pytest -q` per venv, and a check that the harness collected ≥3 tests.

## Fixtures and Recorder Changes

**Recorder allowlist** (`scripts/record_fixture.py:24-30`, currently `AUDIO_KEYS = ('id', 'username', 'author_name', 'title', 'description', 'image', 'avatar', 'date_created', 'tags', 'stats', 'transcodings')`, `TRANSCODING_KEYS = ('format', 'type', 'url', 'size', 'codec', 'sample_rate', 'channels', 'duration', 'bit_rate')`) [VERIFIED: Read this session]:
- Add to `AUDIO_KEYS`: `'is_downloadable'`, `'is_public'`, `'sources'`.
- Add to `TRANSCODING_KEYS`: `'source_id'`.
- New `SOURCE_KEYS = ('id', 'format', 'type', 'url', 'size', 'codec', 'sample_rate', 'channels', 'duration', 'bit_rate', 'date_created')`. **Exclude** `download`, `name`, `md5`, `from`, `date_updated`, `date_uploaded`, `waveform`.
- `project()`: `_require(sources, list)`, each entry `_require(dict)`, `url` through `strip_url`. `check_record()`: `_check_keys` for every `sources[]` entry. The existing `://`+`?` and forbidden-marker scans then cover it.
- Hygiene `test_recorder_check_rejects`: add `sources-key` (e.g. `download`) and `sources-name` mutations. `test_shape_coverage`: add `is_downloadable` true and false, `len(sources) > 1`, a `wv` source, a `wav` source, and `is_public is False`.

**Fixture set** (re-record all 8 so they gain the new keys, then add 4):

| Id | Track | Covers |
|----|-------|--------|
| 1877766681285368 | reference | dl=false, `wv` source → no original |
| 1782423994666898 | jasa-sisemore | dl=false, `wav` pcm source → no original |
| 1861573231849291 | arthur-hpcp | dl=true, m4a source (live object 404; offline: probe-fails path) |
| 1880272428195927 | roshimakr21 | dl=true, mp3 original |
| 1880272651234303 | shivgas | dl=true, mp3 original; transcoding also mp3 (id non-collision) |
| others (3) | beards, davidmoreno, james-gant | dl=false wv |
| **1880272945380630** (new) | alec-murray/audio/podcast-intro | dl=true, m4a original, size matches |
| **1880272416485027** (new) | andrea-mathiopoulos/audio/song-9-… | dl=true, `wav`+`wavpack` conversion (no acodec/filesize) |
| **1772828397072996** (new) | anonymous-audio/audio/louder-jazz-bababa | `is_public: false`, 2 versions, duration 314.088 |
| **1858402410391836** (new) | stefaniecg/audio/beso | `is_public: true`, 2 sources / 3 transcodings, newest = mp3+m4a |

The new fixtures stay offline-only (per CONTEXT). Re-recording updates `stats` counts. The EXPECTED/BEST tables use none of them, but re-check them after recording. Error cases need no recorded bodies: build `HTTPError(Response(io.BytesIO(body), url, {}, status=N))` as `tests/test_extract_offline.py:137-150` already does, parametrized over 404, 410, 403 and 401, and optionally use the verbatim 404 JSON bodies from Finding 1.

## State of the Art

| Old Approach (Phase 1) | Current Approach (Phase 2) | Impact |
|--------------|------------------|--------|
| All `transcodings[]` emitted | Current-source transcodings only | Correct duration and formats on multi-version tracks |
| `sources` ignored | Gated `original` format | EXTR-04 |
| 404 → "Track not found, private, or removed" without id | Locked message + `video_id`; 401/403/410 mapped | EXTR-06 |
| `_TESTS` = reference only | + jasa-sisemore | PLUG-03 |
| Manual harness run | `scripts/test-live.sh` | PLUG-02/03, SC4 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Removed/deleted tracks return 404 like unknown ones (none found anonymously) | Finding 1 | A different status (e.g. 410/403) is already mapped to an expected error; only the wording would differ |
| A2 | 401/403 never happen anonymously; the mapping is defensive only | Code Examples | None functionally; the message is untested live |
| A3 | Internal `is_public` = v1 `is_listed` (unlisted ≠ private) | Finding 1 | Behavior (200 + playable) is verified either way |
| A4 | "Newest `date_created` wins" holds generally (verified on 2 multi-version tracks against `og:audio:url`) | Pattern 1 | A track whose list order and dates disagree could pick the wrong version |
| A5 | flac/aiff/ogg originals behave like wav/mp3/m4a (not observed) | Finding 2 | Low; they are in `KNOWN_EXTENSIONS`/`ALLOWED_EXTENSIONS` |

## Open Questions (RESOLVED — see 02-CONTEXT.md "Revised after research")

1. **CONTEXT says "where the API distinguishes private (e.g. `is_public: false`, 403) use a more specific message".**
   - What we know: `is_public: false` tracks are public-by-link and play anonymously. The official spec says there are no private audio.
   - Recommendation: never error on `is_public`; keep a defensive 401/403 message. The planner should state this deviation in the plan, because it corrects the example and keeps the decision's intent.
2. **Range probe of the original (one extra request on downloadable tracks).**
   - Recommendation: keep it (1 of 6 downloadable originals was missing on S3). Its message is a clean skip line.
3. **Multi-version handling is not in the CONTEXT decisions** but falls under "works on every track variant".
   - Recommendation: include it. It is small and fixes a wrong `duration` (EXTR-05 regression) on real tracks.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `.venv` yt-dlp | live + offline | ✓ | 2026.10.26 | — |
| `.venv-metube` yt-dlp | live + offline | ✓ | 2026.08.19 | — |
| pytest (both venvs) | tests | ✓ | 9.1.1 | — |
| git + github.com reachability | harness fetch | ✓ | system | PyPI sdist `test/` (Phase 1 verified) |
| api.audio.com / s3.ustatik.com | live tests | ✓ | — | none (live by definition) |
| ffprobe | manual checks only | ✓ | system | not needed by script |
| `yt-dlp` console script in each venv | PLUG-02 check | ✓ | — | `python -m yt_dlp` |

**Missing dependencies with no fallback:** none.

## Validation Architecture

(`workflow.nyquist_validation` is `false` in config. This section is included because the orchestrator requested it.)

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (offline); yt-dlp `test/test_download.py` at matching tag (live) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| Quick run command | `.venv/bin/python -m pytest -q -p no:cacheprovider` (baseline 126 passed, 6 skipped, ~2 s, both venvs) |
| Full suite command | the above for `.venv` and `.venv-metube`, then `scripts/test-live.sh` |

### Phase Requirements → Test Map
| Criterion / Req | Behavior | Type | Automated Command | File Exists? |
|--------|----------|------|-------------------|-------------|
| SC1 / EXTR-04 | dl=true fixtures have exactly one `format_id == 'original'` with `preference == -10`; dl=false fixtures never do; default selection is never `original`; `-f original` selects it | unit (offline) | `pytest tests/test_sources_offline.py -q` | ❌ Wave 0 |
| SC1 / EXTR-04 | `wv` on a dl=true mutation → no original, debug note; probe failure → no original; wavpack→wav has no `filesize`/`acodec` | unit | same file | ❌ Wave 0 |
| SC1 (variant) | multi-version fixtures: formats only from the newest source; duration 314.088 / 173.035 | unit | same file | ❌ Wave 0 |
| SC1 (variant) | `is_public: false` fixture extracts normally | unit | same file | ❌ Wave 0 |
| SC2 / EXTR-06 | 404/410 on each endpoint → `expected`, exact locked message, `video_id` set, no "report this issue"; 401/403 → specific message | unit | `pytest tests/test_extract_offline.py -k "404 or error" -q` | partial (extend) |
| SC2 / EXTR-06 | CLI prints one `ERROR:` line, no `Traceback`, exit 1 | smoke (live) | `.venv/bin/yt-dlp --ignore-config --simulate https://audio.com/david-oliveira-1877766671108274/audio/this-slug-does-not-exist-zz9 2>&1 \| grep -c '^ERROR:'` = 1, no `Traceback` (optionally a `test-live.sh` step) | ❌ |
| SC3 / PLUG-03 | `_TESTS` has the reference + jasa; offline replay of `_TESTS[1]` against fixture 1782423994666898 | unit | `pytest tests/test_metadata_offline.py -q` (generalize `test_tests_info_dict_matches_offline_reference` over non-`only_matching` entries) | partial |
| SC3/SC4 / PLUG-02/03 | harness passes `test_AudioCom`, `_1`, `_all`; plugin listed; real download on both versions | live | `scripts/test-live.sh` | ❌ Wave 0 |
| Hygiene | fixtures with `sources` contain no `download`/`name`/query strings | unit | `pytest tests/test_fixture_hygiene.py -q` | extend |
| No network offline | `_request_webpage` never called for dl=false fixtures; calls are intercepted for dl=true | unit | in `test_sources_offline.py` | ❌ |

### Sampling Rate
- **Per task commit:** the offline suite on both venvs (~2 s each).
- **Per wave merge:** plus `scripts/test-live.sh`.
- **Phase gate:** both green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/conftest.py`: block or stub `_request_webpage`/`_is_valid_url`; helper for original-probe outcome
- [ ] Recorder allowlist extension + re-record 8 + record 4 new fixtures
- [ ] `tests/test_sources_offline.py`
- [ ] `scripts/run_live_tests.py`, `scripts/test-live.sh`, README section

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | anonymous API only; no login (locked) |
| V3 Session Management | no | — |
| V4 Access Control | yes (policy) | `is_downloadable is True` gate. Source URLs are reachable regardless, so the extractor is the only enforcement point (EXTR-04; out of scope to bypass) |
| V5 Input Validation | yes | anchored `_VALID_URL`; `traverse_obj` type filters; ext accept-list `KNOWN_EXTENSIONS` (blocks `wv`/arbitrary ext from API labels) |
| V6 Cryptography | no | — |
| V7 Errors & Logging | yes | `expected=True` errors; skip messages print the HTTP status only (`HTTP Error 404: Not Found`), never signed URLs; recorder prints ids only |
| V10 Malicious Code / supply chain | yes | harness pinned by tag **and** commit SHA; sparse checkout so no foreign `yt_dlp/` is imported; no new packages |
| V14 Configuration | yes | zero import-time work (unchanged) |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Signed S3 URL leaking into git (fixtures, `_TESTS`, logs) | Information disclosure | `strip_url` on `sources[].url`; drop `download`/`name`; `check_record` scans; no URLs in `_TESTS` |
| Hostile API `format` label reaching the filename | Tampering | `KNOWN_EXTENSIONS` accept-list (already), same for originals |
| Tampered harness checkout executing in the venv | Tampering / EoP | `rev-parse HEAD` == pinned SHA, re-clone otherwise |
| Exposing non-downloadable originals | Policy / repudiation | strict `is True` gate + offline tests over dl=false fixtures |

## Sources

### Primary (HIGH confidence)
- Live probes this session: `api.audio.com/oembed`, `api.audio.com/audio/<id>` (22 tracks + 8 error cases), S3 Range GETs, two research-only page fetches (`og:audio:url`)
- `https://api.audio.com/v1/openapi.json` (re-fetched, HTTP 200): "There are no private audio.", `is_listed`, supported upload formats
- Installed yt-dlp sources read this session: `yt_dlp/utils/_utils.py:5123-5204, 5363-5365, 5386-5408`; `yt_dlp/YoutubeDL.py:2995-3030` (2026.8.19); `yt_dlp/extractor/common.py:638-642, 780-783, 1957-2001`; `yt_dlp/extractor/soundcloud.py:260-292` (original-download precedent)
- yt-dlp harness at tags `2026.08.19` / `2026.10.26` (sparse clones; `test/test_download.py`, `test/helper.py`, `pyproject.toml`), `git ls-remote` tag SHAs
- Repo files read this session: `yt_dlp_plugins/extractor/audiocom.py`, `scripts/record_fixture.py`, `tests/conftest.py`, `tests/test_extract_offline.py`, `tests/test_metadata_offline.py`, `tests/test_fixture_hygiene.py`, `tests/test_plugin_loading.py`

### Secondary (MEDIUM confidence)
- Audacity forum search JSON (`forum.audacityteam.org/search.json`) as a source of older/unlisted track links
- [Can no longer upload audio to audio.com (Audacity forum)](https://forum.audacityteam.org/t/can-no-longer-upload-audio-to-audio-com/135900) (WebSearch hit; no track data used)

### Tertiary (LOW confidence)
- none relied on

Not run through the `research-plan`/`classify-confidence` seam: all search providers are disabled in config, and primary sources were probed directly.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Unchanged pins, verified in both venvs.
- Architecture (version selection, original gating, ranking): HIGH. The prototype ran live on 10 tracks on both versions.
- Error mapping: HIGH for 404 (observed); LOW for removed/403/410 (not observable anonymously).
- Harness recipe: HIGH. Full script exit 0 on both versions.

**Research date:** 2026-10-28
**Valid until:** about 2026-11-27 for the API shapes. Re-check the harness SHAs only if the pins change. The new spam-like fixtures may disappear live, but they are offline-only.
