# Phase 1: Track Downloads via yt-dlp - Context

**Gathered:** 2026-10-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a yt-dlp extractor plugin (`AudioComIE`) in this repo that, when on the plugin search path, matches audio.com single-track URLs and downloads mp3/m4a with correct metadata, without browser impersonation. Includes repo scaffolding, recorded fixtures from ≥5 tracks, and offline tests. Edge cases (is_downloadable sources, error mapping), version matrix, and MeTube deploy are later phases.

</domain>

<decisions>
## Implementation Decisions

### Repo layout & tooling
- Plugin file lives at repo root: `yt_dlp_plugins/extractor/audiocom.py` (namespace package — NO `__init__.py` in `yt_dlp_plugins/` or `yt_dlp_plugins/extractor/`), so the same tree can be bind-mounted into MeTube or pip-installed
- `pyproject.toml` so `pip install -e .` registers the plugin locally (yt-dlp as dev dependency, not a hard runtime pin)
- Plugin-only code with absolute `yt_dlp.*` imports. No upstream-style `yt_dlp/extractor/audiocom.py`, no generator script, no `_extractors.py` edits — yt-dlp CONTRIBUTING forbids LLM/agent-authored contributions
- Tests: pytest offline tests against redacted recorded fixtures (≥5 tracks) + `_TESTS` in the extractor for live checks

### Extraction behavior
- Data path: canonicalize URL from regex groups → `GET https://api.audio.com/oembed?url=<canonical>` → parse id from `iframe_url` (`/embed/audio/(\d+)`) → `GET https://api.audio.com/audio/<id>`. No HTML page fetch, no impersonation
- Formats from `transcodings[]` (mp3 ~192k, m4a ~306k) with `abr`, `acodec`, `ext`, `vcodec: 'none'`; let yt-dlp's default sort choose (m4a wins on bitrate). Derive ext from format/MIME, never from signed URL path
- Include `view_count`, `like_count`, `comment_count`, `repost_count`, `tags` in Phase 1 when present (same JSON)
- Fixtures: strip URL signatures (`X-Amz-*` query params) and any tokens/keys; keep only fields the extractor reads
- `duration` from API is milliseconds → divide by 1000; `timestamp` from `created`
- Do NOT emit `sources[]` in Phase 1 (gating on `is_downloadable` is Phase 2, EXTR-04)

### Claude's Discretion
- Exact `_VALID_URL` regex shape (must reject `/collections/`, profile pages, `/embed/`), helper structure, test file organization

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Greenfield repo — no code yet. Research prototype (in scratch) proved the oEmbed → API path downloads the reference track end to end
- yt-dlp in-tree `whyp.py` (~83 lines) is the closest model extractor

### Established Patterns
- yt-dlp idioms: `traverse_obj`, `int_or_none`, `url_or_none`, `float_or_none(..., scale=1000)`, `ExtractorError(expected=True)`

### Integration Points
- MeTube container mounts `/opt/metube/plugins` read-only with `PYTHONPATH=/plugins` (Phase 3)
- Host has no yt-dlp; use a venv for dev/test

</code_context>

<specifics>
## Specific Ideas

- Reference URL: https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best (no thumbnail, no description — tests must not assert those for it)
- oEmbed is strict: `www.`, trailing slash, query string, uppercase username → 404, so canonicalize before calling
- Add a header comment in the plugin: delete once bundled yt-dlp ships a built-in `[audiocom]` extractor

</specifics>

<deferred>
## Deferred Ideas

- Original-file `sources[]` gated on `is_downloadable` — Phase 2
- Error mapping for private/removed tracks — Phase 2
- Collections, profiles, embed URLs — v2

</deferred>
