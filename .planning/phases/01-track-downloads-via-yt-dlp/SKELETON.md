# Walking Skeleton — audio.com yt-dlp Extractor

**Phase:** 1
**Generated:** 2026-10-28

## Capability Proven End-to-End

Running `yt-dlp` (repo editable-installed in a pinned venv) on the canonical reference URL `https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best` goes URL → oEmbed → track API → info dict → `1877766681285368.m4a` on disk, logged as `[AudioCom]`, with no HTML scraping and no browser impersonation.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | yt-dlp `InfoExtractor` subclass `AudioComIE` (no `IE_NAME`, so `[AudioCom]` / ie_key `AudioCom`), loaded as a yt-dlp plugin | Runs inside stock yt-dlp and MeTube without rebuilding either. The class name matches the future upstream name, so the plugin shadows a built-in instead of duplicating it |
| Data layer | Read-only and stateless. `GET https://api.audio.com/oembed?url=<canonical>` → id from `iframe_url` (`/embed/audio/<digits>`) → `GET https://api.audio.com/audio/<id>`. Media comes from pre-signed `s3.ustatik.com` URLs through yt-dlp's HTTP downloader | Only unchallenged slug resolver. A single JSON source of truth. No persistence, so no concurrency hazards |
| Auth | None. Anonymous public JSON with yt-dlp default headers. No cookies, no OAuth `v1` API, no TLS fingerprinting | Cloudflare does not challenge `api.audio.com`. The OAuth API only exposes the logged-in user's own tracks |
| Packaging | Namespace package `yt_dlp_plugins/extractor/audiocom.py` with no `__init__.py`. hatchling (`==1.32.4`) build backend. Absolute `yt_dlp.*` imports | hatchling's editable `.pth` is discovered by yt-dlp's plugin scanner. setuptools' editable finder is not |
| Deployment target | Phase 1 uses two local uv venvs on Python 3.11: `.venv` (yt-dlp 2026.10.26) and `.venv-metube` (yt-dlp 2026.8.19). Phase 3 uses a read-only bind mount into MeTube via `PYTHONPATH=/plugins` | Covers current stable and MeTube's bundled version. 3.11 is the syntax floor |
| Directory layout | `yt_dlp_plugins/extractor/` (the only shipped file), `tests/` (offline pytest, `tests/fixtures/<track_id>.json`), `scripts/` (fixture recorder) | The same tree can be bind-mounted or pip-installed |
| Format selection | Per-format `quality` = `abr`, so yt-dlp's default sort picks the highest bitrate | User decision 2026-10-28. Codec rank alone picks a 9 kbps m4a over a 160 kbps mp3 |
| Test strategy | Offline pytest with `AudioComIE._download_json` monkeypatched over redacted recorded fixtures (≥5 tracks). Live checks go through the yt-dlp CLI | Fast and deterministic, with no signed URLs in git |

## Stack Touched in Phase 1

- [x] Project scaffold: `pyproject.toml` (hatchling, pytest config), `.gitignore`, pinned venvs, pytest runner
- [x] Routing: `_VALID_URL` matches single-track URLs (incl. `www.`, trailing slash, query, uppercase) and rejects collections, profiles, `/embed/`, `/audio/audio/`
- [ ] Data read: oEmbed and track-API JSON → info dict (formats and metadata)
- [ ] Data write: yt-dlp writes the audio file, with embedded metadata, to disk
- [x] Interface: yt-dlp CLI. `-v` lists `AudioComIE`, `-F` lists mp3/m4a audio-only rows, a download logs `[AudioCom]`
- [x] Local full-stack run command: `.venv/bin/yt-dlp --ignore-config "<audio.com track URL>"`

## Out of Scope (Deferred to Later Slices)

- Original-upload formats gated on `is_downloadable` (Phase 2, EXTR-04)
- One-line errors for private, removed, or nonexistent tracks (Phase 2, EXTR-06)
- The documented `_TESTS` runner command and a second live `_TESTS` track (Phase 2, PLUG-03). The real-download check on both versions (Phase 2, PLUG-02)
- Installing into the MeTube container and the README (Phase 3, METB-01..03)
- Collections, profiles, embed URLs (v2: EXTR-07..09)
- Any upstream yt-dlp code, `_extractors.py` edit, or PR text (yt-dlp forbids AI-authored contributions)
- HTML page scraping, browser/TLS impersonation, OAuth `v1` API, cookies or login

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton and keeps its architectural decisions:

- Phase 2: originals offered only for downloadable tracks, clean `ExtractorError`s, a documented `_TESTS` command, and checks on 2026.08.19 and current stable
- Phase 3: plugin bind-mounted into MeTube next to `rumble_fix.py`. Pasting the reference URL in the web UI yields a playable file. README covers install, update, and removal
