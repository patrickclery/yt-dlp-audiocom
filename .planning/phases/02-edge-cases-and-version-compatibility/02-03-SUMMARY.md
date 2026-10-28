---
phase: 02-edge-cases-and-version-compatibility
plan: 03
subsystem: extractor
tags: [yt-dlp, plugin, original-upload, is_downloadable, format-selection]
status: complete

requires:
  - phase: 02-edge-cases-and-version-compatibility
    plan: 01
    provides: scripts/test-live.sh, _TESTS reference + jasa, HTTP error mapping
  - phase: 02-edge-cases-and-version-compatibility
    plan: 02
    provides: sources[] fixtures with is_downloadable, newest-source `current` in _real_extract
provides:
  - Opt-in `original` format (preference -10) on tracks whose is_downloadable is literally True
  - Autouse `probe` fixture stubbing AudioComIE._request_webpage; run_extract(url, params)
  - tests/test_sources_offline.py (ORIGINAL table, gate, probe, selection, metadata, mutations)
  - test-live.sh step 9 (non-downloadable jasa lists no original) and README "Original uploads"
affects: [03]

actuals:
  tokens: 5672
  tasks: 2
  commits: 3
plan_head_before: 27ce2d4e52e276618220a00ad8cac6661e331ab4
plan_head_after: 19d2868a84f4e506497d2aa08175233ebf849d75

tech-stack:
  added: []
  patterns:
    - "Policy gate before any network touch: `is True` check, then ext accept-list, then one-byte Range GET via _is_valid_url"
    - "preference (ie_pref, priority) instead of quality to keep a format strictly opt-in under any -S"
    - "Autouse network stub for the second request path (_request_webpage) so offline tests cannot reach S3"

key-files:
  created:
    - tests/test_sources_offline.py
  modified:
    - yt_dlp_plugins/extractor/audiocom.py
    - tests/conftest.py
    - tests/test_extract_offline.py
    - .gitignore
    - scripts/test-live.sh
    - README.md

key-decisions:
  - "Ext rule factored into AudioComIE._known_ext, shared by transcodings and the original (no behavior change for transcodings)"
  - "run_extract adds YoutubeDL.add_default_extra_info to the processed copy, so yt-dlp's 'Requested format is not available' path can run offline"
  - "Original carries no quality; preference -10 alone keeps default, -f ba, -S abr and -S size on transcodings"

requirements-completed: [EXTR-04, PLUG-02]

duration: ~25min
completed: 2026-10-28
---

# Phase 2 Plan 03: Opt-in original upload Summary

**Downloadable audio.com tracks now offer the uploader's file as `-f original` (newest source URL, ext accept-listed, one-byte Range probe, wavpack metadata rule); non-downloadable tracks never list it or touch the source URL, proven offline on 12 fixtures and live on yt-dlp 2026.10.26 and 2026.08.19.**

## Tasks

| Task | Commit | What |
|------|--------|------|
| 1 RED | c0e27c6 | probe stub, run_extract params, test_sources_offline.py: 24 failures on both venvs, all "no original" |
| 1 GREEN | 2da0340 | gated original in `_real_extract`, `_known_ext` helper, .gitignore wav/flac/aiff/ogg |
| 2 | 19d2868 | test-live.sh step 9 (jasa negative), README `## Original uploads` and step list |

## Verification

| Check | Result |
|-------|--------|
| `pytest -q` on .venv and .venv-metube | 274 passed, 43 skipped (both) |
| OPT-IN OK (alec-murray lists original; default, -f ba, -S abr, -S size all pick m4a) | pass, both venvs |
| ORIGINAL DOWNLOAD OK (`-f original` alec) | 331,730-byte aac .m4a, both venvs |
| GATE OK | arthur-hpcp printed the skip line and listed no original; reference `["mp3","m4a"]`, jasa `["mp3"]`, both venvs |
| `scripts/test-live.sh` | ALL TARGETS PASSED, `ok: non-downloadable track lists no original` on both venvs |
| Acceptance greps, `git ls-files` audio check | all pass, 0 audio files tracked |

alec-murray was still available; no roshimakr21 substitution was needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] run_extract could not reach "Requested format is not available"**
- **Found during:** Task 1 RED
- **Issue:** `process_ie_result` on the raw `extract()` result has no `extractor` key, so the no-formats path raised `KeyError: 'extractor'` instead of yt-dlp's real error.
- **Fix:** run_extract calls `ydl.add_default_extra_info(processed, ie, url)` on the processed copy, which is what `extract_info` does. The raw `info` is unchanged.
- **Files modified:** tests/conftest.py
- **Commit:** c0e27c6

**2. [Refactor within GREEN] Shared `_known_ext` static method**
- The plan computes the original's ext with the transcodings' rule. Rather than duplicate it, the rule moved into `AudioComIE._known_ext`. Transcoding behavior is unchanged; the existing ext mutation tests still pass.

### Environment notes
- Venvs were built with `python3 -m venv` + pip on the host Python 3.14.8 using only the approved pins (yt-dlp 2026.10.26 / 2026.8.19, pytest 9.1.1, editable install via hatchling 1.32.4), not uv + Python 3.11 as README describes. Code still uses no syntax newer than 3.11.
- The plan-ledger and spawn-sentinel files could not be written into the worktree's git dir (sandbox refusal); `plan_head_before` is the dispatched base 27ce2d4 and `commits` was measured with `git rev-list --count 27ce2d4..HEAD`.

## Extra tests beyond the behavior list
- No source URL appears anywhere in `info` or `processed` for non-downloadable fixtures (prohibition 1).
- Probe-failure skip line contains no URL, only the HTTP status (T-02-11).
- The original has no `quality` key.

## Threat model
T-02-09, T-02-10, T-02-11 and T-02-13 mitigations are implemented and tested as planned. No new surface beyond the planned probe GET (T-02-12, accepted).

## Known Stubs
None.

## Self-Check: PASSED
- FOUND: tests/test_sources_offline.py, yt_dlp_plugins/extractor/audiocom.py, scripts/test-live.sh, README.md
- FOUND commits: c0e27c6, 2da0340, 19d2868 (ancestors of HEAD)
