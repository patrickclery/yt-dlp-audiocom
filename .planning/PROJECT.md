# audio.com yt-dlp Extractor

## What This Is

A yt-dlp extractor for audio.com single-track pages (e.g. `https://audio.com/<user>/audio/<slug>`), so they can be downloaded programmatically. It is built to be contributed upstream to yt-dlp via PR, and in the meantime shipped as a yt-dlp plugin that Patrick's MeTube container loads, so pasting an audio.com link into MeTube just works.

## Core Value

Pasting an audio.com track URL into MeTube (or `yt-dlp`) downloads the audio file with correct metadata.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Research prior art on GitHub (existing audio.com downloaders/extractors, open yt-dlp issues/PRs) before building
- [ ] yt-dlp extractor recognizes audio.com single-track URLs and extracts the audio stream
- [ ] Extracts metadata: title, uploader, duration, thumbnail, description where available
- [ ] Gets past audio.com's Cloudflare anti-bot challenge (generic extractor currently gets HTTP 403)
- [ ] Extractor follows yt-dlp contribution conventions (code style, `_TESTS`, flake8/ruff, CONTRIBUTING.md) so it is PR-ready
- [ ] Same code packaged as a yt-dlp plugin mounted into the existing MeTube Docker container
- [ ] Upstream PR opened against yt-dlp/yt-dlp

### Out of Scope

- Collections/playlists — not needed for occasional personal saves; can follow later
- Whole-profile downloads — same reason
- Standalone CLI/GUI — yt-dlp + MeTube already cover the interface
- Batch/automated archiving hardening — use case is occasional personal saves

## Context

- MeTube (`ghcr.io/alexta69/metube:latest`) is already running locally as container `metube`; it's a web UI over yt-dlp (bundled yt-dlp 2026.08.19).
- That yt-dlp has **no audio.com extractor**; it falls to `[generic]` and fails with `HTTP Error 403 caused by Cloudflare anti-bot challenge; try again with --extractor-args "generic:impersonate"`. Impersonation (curl_cffi) is likely needed.
- yt-dlp is not installed on the host.
- Reference URL: https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best
- yt-dlp supports external plugins via `yt_dlp_plugins/extractor/` packages on the plugin search path.

## Constraints

- **Tech stack**: Python, yt-dlp extractor API (`InfoExtractor`) — required for upstream acceptance
- **Compatibility**: Must load in MeTube's bundled yt-dlp version without rebuilding the image (volume-mounted plugin)
- **Upstream policy**: Must satisfy yt-dlp maintainers' rules (no new hard dependencies; impersonation via existing optional curl_cffi support)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build a yt-dlp extractor, not a standalone tool | MeTube is just a yt-dlp front end; an extractor makes both work | — Pending |
| Target upstream PR to yt-dlp | Benefits everyone, maintained long-term by upstream | — Pending |
| Also ship as plugin for MeTube | Upstream review can take weeks; want it usable now | — Pending |
| Single tracks only for v1 | Use case is occasional personal saves | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-28 after initialization*
