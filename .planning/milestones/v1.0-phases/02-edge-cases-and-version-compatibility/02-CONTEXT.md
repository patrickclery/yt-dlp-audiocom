# Phase 2: Edge Cases and Version Compatibility - Context

**Gathered:** 2026-10-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden the Phase 1 `AudioComIE` plugin: offer the original upload only for downloadable tracks, map unavailable/private/missing tracks to clean one-line errors, and add one documented live-test command that runs `_TESTS` on both yt-dlp 2026.8.19 and 2026.10.26. MeTube deploy is Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Original upload, errors & test command
- `sources[]` emitted only when `is_downloadable is True`; never otherwise (EXTR-04)
- Original is opt-in, NOT the default: give it `format_id` starting `original` (e.g. `original` / `original-wav`) and a `quality`/preference lower than the transcodings so default selection still picks the highest-bitrate transcoding (Phase 1 decision stands). User requests it with `-f original`
- WavPack (`wv`) sources are skipped (not in yt-dlp's allowed extensions); wav/mp3/m4a originals are offered. Emit a `to_screen`/debug note when a `wv` original is skipped
- Errors: oEmbed 404 or API 404 → `ExtractorError('This audio.com track is unavailable (removed, private, or wrong URL)', expected=True)`; where the API distinguishes private (e.g. `is_public: false`, 403) use a more specific expected message. No traceback, no "please report this issue"
- Live test command: `scripts/test-live.sh` runs the extractor's `_TESTS` against each venv (`.venv` = 2026.10.26, `.venv-metube` = 2026.8.19) using the approach from Phase 1 RESEARCH (`load_all_plugins()` + the matching version's `test/test_download.py -k AudioCom` from a writable temp dir; git tags are zero-padded). Documented in README

### Version compatibility
- Exact pins only: yt-dlp==2026.8.19 and yt-dlp==2026.10.26; no nightly
- Private/unlisted behavior probed anonymously only; no account login, no creating test tracks. Record observed responses in RESEARCH
- Live `_TESTS` use only the reference track and the 2023 `jasa-sisemore/...` track; other sampled tracks stay offline-fixture-only

### Revised after research (2026-10-28)
- `is_public: false` means UNLISTED and plays anonymously — never raise on it. Keep 401/403 → expected 'private/restricted' message only as a guard (never observed)
- All observed failures are 404 JSON; pass `video_id=` so the error is one line `ERROR: [AudioCom] <id>: ...`
- Multi-version tracks: keep only the newest upload's transcodings, and take duration from it (bug: louder-jazz-bababa reported 240 s vs 314 s)
- Originals: `format_id` `original*` with `preference: -10` (NOT `quality: -1`) keeps it opt-in under default, `ba`, `-S abr`, `-S size`; skip `wv` in the extractor; do a 1-byte Range GET to drop originals that 404 (HEAD returns 403)
- Live runner recipe per 02-RESEARCH.md (sparse-clone `test/` at zero-padded tag, verify SHA, `load_all_plugins()`; avoid full clone shadowing installed `yt_dlp`; no `grep -q` under pipefail)

### Claude's Discretion
- Exact `format_id` naming for originals, README layout, script internals

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `yt_dlp_plugins/extractor/audiocom.py` — `AudioComIE` with oEmbed → API path, bitrate `quality` ranking, metadata fallbacks, WR-01..07 fixes
- `scripts/record_fixture.py` + shared redaction rules; fixtures under `tests/fixtures/` (8 tracks)
- `tests/` offline suite (126 passing on both venvs); `_TESTS` already present in the extractor

### Established Patterns
- TDD commits (failing test, then fix); `traverse_obj`, `ExtractorError(expected=True)`
- Venvs `.venv` / `.venv-metube` built with uv from approved pins only (pytest==9.1.1, hatchling==1.32.4)

### Integration Points
- Phase 3 copies the plugin into `/opt/metube/plugins/yt_dlp_plugins/extractor/`

</code_context>

<specifics>
## Specific Ideas

- Recorder currently drops `sources`; fixtures will need `sources[].{format, codec, size, ...}` (URLs stripped of query strings) and `is_downloadable`/`is_public` to test EXTR-04 offline
- Code review WR-03 deferred `format_id = ext-abr` change — revisit only if originals collide with transcoding format_ids

</specifics>

<deferred>
## Deferred Ideas

- WavPack originals (needs core yt-dlp change)
- Collections, profiles, embed URLs — v2

</deferred>
