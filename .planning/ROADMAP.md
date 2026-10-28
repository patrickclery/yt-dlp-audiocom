# Roadmap: audio.com yt-dlp Extractor

## Overview

Three phases take this from nothing to a working MeTube download. Phase 1 sets up the plugin repo, records API fixtures from at least five real tracks, and builds an `AudioComIE` plugin that downloads a track with yt-dlp through the oEmbed and `api.audio.com/audio/<id>` path, with correct metadata. Phase 2 handles the edge cases: originals offered only when the track is downloadable, clean errors, `_TESTS`, and checks on both yt-dlp 2026.08.19 and current stable. Phase 3 installs the plugin into the running MeTube container next to the existing plugins and documents install, update, and removal. The scope is the plugin only. No phase covers upstream yt-dlp PR work, because yt-dlp policy forbids agent-written contributions.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Track Downloads via yt-dlp** - Plugin repo, recorded fixtures from 5+ tracks, and an `AudioComIE` that downloads mp3/m4a with correct metadata
- [ ] **Phase 2: Edge Cases and Version Compatibility** - Originals gated on `is_downloadable`, clean errors, `_TESTS`, and checks on yt-dlp 2026.08.19 and current stable
- [ ] **Phase 3: MeTube Deploy** - Plugin installed into the MeTube container next to existing plugins, plus README for install, update, and removal

## Phase Details

### Phase 1: Track Downloads via yt-dlp

**Goal**: User can run yt-dlp with the repo's plugin on an audio.com track URL and get an mp3 or m4a file with correct metadata, without impersonation.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: EXTR-01, EXTR-02, EXTR-03, EXTR-05, PLUG-01
**Success Criteria** (what must be TRUE):
  1. With the repo's plugin directory on the plugin search path, `yt-dlp -v` lists the AudioCom extractor under extractor plugins and shows no "Error while importing" line.
  2. Running `yt-dlp` on the reference URL, and on its `www.`, trailing-slash, and query-string variants, picks `[AudioCom]` (not `[generic]`) and downloads the track with no Cloudflare 403 and no impersonation. Collection, profile, and `/embed/` URLs are not matched.
  3. `yt-dlp -F` on the reference URL lists mp3 and m4a formats with correct ext, abr, and acodec, and no video codec.
  4. The downloaded file has title, uploader, uploader_id/url, duration in seconds, and upload date. Thumbnail, description, tags, and counts appear only for tracks that have them, checked against redacted fixtures recorded from at least 5 sampled tracks.

**Plans:** 2 plans

Plans:
**Wave 1**
- [ ] 01-01-PLAN.md — Walking skeleton: package-legitimacy gate, hatchling plugin scaffold plus two pinned venvs, tracer (reference URL → oEmbed → API → m4a), URL variants and negatives

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 01-02-PLAN.md — Fixture recorder plus ≥5 redacted fixtures, highest-bitrate format selection, full metadata with uploader/thumbnail fallbacks

**Research flag**: Sample at least 5 audio.com tracks for fixtures before finalizing the field mapping: `is_downloadable` true and false, with and without artwork, with and without description. Strip signatures and `app.*` config values.

### Phase 2: Edge Cases and Version Compatibility

**Goal**: The plugin works on every track variant and on both target yt-dlp versions, and has a test command that proves it.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: EXTR-04, EXTR-06, PLUG-02, PLUG-03
**Success Criteria** (what must be TRUE):
  1. A track flagged downloadable offers its original upload as an extra format. A track that is not flagged downloadable never lists one.
  2. A removed, private, or nonexistent track URL fails with a one-line yt-dlp `ERROR:` that states the cause, with no traceback and no bare HTTP 404.
  3. One documented local command runs the extractor's `_TESTS` (the reference URL plus at least one other track), and it passes.
  4. That test command and a real download both pass on yt-dlp 2026.08.19 and on current stable.

**Plans**: TBD
**Research flag**: How private and unlisted tracks behave is unknown. Probe these cases and map each one to `ExtractorError(expected=True)`.

### Phase 3: MeTube Deploy

**Goal**: Pasting an audio.com track URL into MeTube produces a playable audio file in the download folder.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: METB-01, METB-02, METB-03
**Success Criteria** (what must be TRUE):
  1. After the plugin is placed at `/opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py` (mode 644, no image rebuild), `docker exec metube yt-dlp -v` lists AudioCom alongside `rumble_fix` and the other existing plugins, with no import errors.
  2. Pasting the reference audio.com URL into MeTube produces a playable audio file with the correct title in the download folder.
  3. The README covers install, update, and the step to delete the plugin once bundled yt-dlp includes `[audiocom]`. Following its install steps reproduces the working deploy.

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Track Downloads via yt-dlp | 0/TBD | Not started | - |
| 2. Edge Cases and Version Compatibility | 0/TBD | Not started | - |
| 3. MeTube Deploy | 0/TBD | Not started | - |
