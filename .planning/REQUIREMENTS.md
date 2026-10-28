# Requirements: audio.com yt-dlp Extractor

**Defined:** 2026-10-28
**Core Value:** Pasting an audio.com track URL into MeTube (or `yt-dlp`) downloads the audio file with correct metadata.

## v1 Requirements

### Extraction

- [ ] **EXTR-01**: User can pass an audio.com single-track URL (`audio.com/<user>/audio/<slug>`, with or without `www.`, trailing slash, or query string) to yt-dlp and it is matched by the `AudioCom` extractor
- [ ] **EXTR-02**: Extractor resolves the track ID from the slug URL (oEmbed on the canonicalized URL) without needing browser impersonation
- [ ] **EXTR-03**: User gets mp3 and m4a formats from the track's transcodings, with correct ext/abr/acodec
- [ ] **EXTR-04**: Original upload (`sources`) is offered only when the track is flagged downloadable; never exposed otherwise
- [ ] **EXTR-05**: Downloaded file carries title, uploader, uploader_id/url, duration (seconds), and upload date; thumbnail, description, tags, and counts are included only when present
- [ ] **EXTR-06**: Unavailable, private, or removed tracks fail with a clear `ExtractorError`, not a stack trace or bare 404

### Plugin Packaging

- [ ] **PLUG-01**: Repo ships an installable yt-dlp plugin (`yt_dlp_plugins/extractor/audiocom.py`, namespace package, no `__init__.py` in `yt_dlp_plugins`) that loads with absolute imports
- [ ] **PLUG-02**: `yt-dlp -v` lists the plugin extractor, and it works on both yt-dlp 2026.08.19 (MeTube's bundled) and current stable
- [ ] **PLUG-03**: Extractor has `_TESTS` covering the reference URL plus at least one other track, and a local test command runs them

### MeTube Deploy

- [ ] **METB-01**: Plugin is installed into `/opt/metube/plugins/yt_dlp_plugins/extractor/` alongside the existing `rumble_fix.py` without breaking it or MeTube's other plugins
- [ ] **METB-02**: User pastes the reference audio.com URL into MeTube's web UI and gets a playable audio file in the download folder
- [ ] **METB-03**: README documents install, update, and the step to remove the plugin once a built-in audio.com extractor exists

## v2 Requirements

- **EXTR-07**: Collections/playlists
- **EXTR-08**: Whole user-profile downloads
- **EXTR-09**: Embed URLs (`audio.com/embed/...`)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Agent-authored upstream yt-dlp PR (code or PR text) | yt-dlp CONTRIBUTING policy forbids LLM/agent-written contributions; the user may hand-write one separately |
| Bypassing `is_downloadable=false` to fetch originals | Respect uploader's choice; not needed for listening copies |
| WavPack `.wv` as default format | Not in yt-dlp's allowed extension list without a core change |
| OAuth API (`api.audio.com/v1`) / login | Only exposes the logged-in user's own tracks |
| Hard curl_cffi dependency | Chosen data path doesn't need impersonation |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 0
- Unmapped: 12 ⚠️

---
*Requirements defined: 2026-10-28*
*Last updated: 2026-10-28 after initial definition*
