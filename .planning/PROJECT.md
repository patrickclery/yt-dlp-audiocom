# audio.com yt-dlp Extractor

## What This Is

A yt-dlp extractor for audio.com single-track pages (e.g. `https://audio.com/<user>/audio/<slug>`), so they can be downloaded programmatically. It ships as a yt-dlp plugin that Patrick's MeTube container loads, so pasting an audio.com link into MeTube just works.

## Core Value

Pasting an audio.com track URL into MeTube (or `yt-dlp`) downloads the audio file with correct metadata.

## Requirements

### Validated

- ✓ yt-dlp plugin downloads audio.com single tracks (mp3/m4a, highest bitrate) with metadata, no impersonation — Phase 1
- ✓ Works on yt-dlp 2026.8.19 (MeTube) and 2026.10.26 — Phase 1
- ✓ Opt-in `-f original` for downloadable tracks; one-line errors; newest-upload only; `scripts/test-live.sh` passes on both versions — Phase 2

### Active

- [ ] Same code packaged as a yt-dlp plugin mounted into the existing MeTube Docker container

### Out of Scope

- Agent-authored upstream yt-dlp PR — yt-dlp CONTRIBUTING forbids LLM/agent-written patches and PR text; Patrick may hand-write one himself
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
| Plugin only; no agent-built upstream PR | yt-dlp bans AI-authored contributions (research 2026-10-28) | ✓ Good |
| oEmbed → api.audio.com/audio/<id> data path | API host isn't behind Cloudflare; prototype downloaded reference track | ✓ Good |
| Highest bitrate wins (quality = abr) | Codec-order default picked a 9 kbps m4a over 160 kbps mp3 | ✓ Good |
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
*Last updated: 2026-10-28 after Phase 2*
