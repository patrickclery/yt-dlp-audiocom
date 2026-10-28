# Milestones

## v1.0 audio.com plugin MVP (Shipped: 2026-10-28)

**Phases completed:** 3 phases, 6 plans, 0 tasks

**Key accomplishments:**
- The recorder now captures is_downloadable, is_public, sources[] and source_id without signed URLs or uploader filenames. Re-uploaded tracks now list only the newest upload's formats and its duration: louder-jazz gives 314.088 s with one mp3 instead of 240.024 s with mp3-0/mp3-1.
- Downloadable audio.com tracks now offer the uploader's file as `-f original` (newest source URL, ext accept-listed, one-byte Range probe, wavpack metadata rule); non-downloadable tracks never list it or touch the source URL, proven offline on 12 fixtures and live on yt-dlp 2026.10.26 and 2026.08.19.

---
