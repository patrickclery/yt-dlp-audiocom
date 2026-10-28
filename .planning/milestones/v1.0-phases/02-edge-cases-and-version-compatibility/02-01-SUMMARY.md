---
phase: 02-edge-cases-and-version-compatibility
plan: 01
subsystem: testing
tags: [yt-dlp, plugin, live-tests, error-handling, bash]
status: complete

requires:
  - phase: 01-track-downloads-via-yt-dlp
    provides: AudioComIE plugin, offline fixtures, conftest helpers, pinned venvs recipe
provides:
  - scripts/test-live.sh version matrix (pin, pinned clean harness, offline suite, plugin listed, _TESTS, real download, missing-track error)
  - scripts/run_live_tests.py (load_all_plugins + version-matched test_download.py)
  - AudioComIE._TESTS[1] jasa-sisemore, replayed offline
  - HTTP 401/403/404/410 mapping to one-line expected errors with video_id
  - README.md (setup, offline tests, live tests, errors)
affects: [02-02, 02-03, 03-deploy]

actuals:
  tokens: 6665
  tasks: 2
  commits: 3
plan_head_before: 133bd56b1cd63b4e4bf5086fec48f230c2277828
plan_head_after: da578f899df9c03f2e3311f35f123fd43f309053

tech-stack:
  added: []
  patterns:
    - "Capture-then-grep in bash under pipefail; never pipe into a quiet grep"
    - "Harness trust: sparse test/-only clone at zero-padded tag, SHA + clean-status + no yt_dlp/ checks"
    - "Error tests assert ExtractorError.orig_msg plus the full str(err) one-line form"

key-files:
  created:
    - scripts/test-live.sh
    - scripts/run_live_tests.py
    - README.md
  modified:
    - yt_dlp_plugins/extractor/audiocom.py
    - tests/test_metadata_offline.py
    - tests/test_extract_offline.py

key-decisions:
  - "Harness check also requires empty `git status --porcelain`, so untracked files (e.g. a planted conftest) are refused, not only modified tracked files"
  - "Error tests compare ExtractorError.orig_msg, because .msg carries the '[AudioCom] <id>: ' prefix"
  - "test-live.sh redacts URL query strings from any echoed tool output"

requirements-completed: [PLUG-02, PLUG-03, EXTR-06]

coverage:
  - id: D1
    description: "One command proves the plugin on yt-dlp 2026.10.26 and 2026.08.19"
    requirement: PLUG-02
    verification:
      - kind: e2e
        ref: "scripts/test-live.sh"
        status: pass
  - id: D2
    description: "_TESTS = reference + jasa-sisemore + only_matching, each replayed offline and through yt-dlp's harness"
    requirement: PLUG-03
    verification:
      - kind: unit
        ref: "tests/test_metadata_offline.py#test_tests_info_dict_matches_offline_fixture"
        status: pass
      - kind: integration
        ref: "scripts/run_live_tests.py (3 passed on both versions)"
        status: pass
  - id: D3
    description: "Missing/removed/private track fails with one clean ERROR line naming the slug or id"
    requirement: EXTR-06
    verification:
      - kind: unit
        ref: "tests/test_extract_offline.py#test_edge_unavailable_is_one_line_expected_error"
        status: pass
      - kind: e2e
        ref: "yt-dlp --simulate .../this-slug-does-not-exist-zz9 on both venvs"
        status: pass

duration: ~25min
completed: 2026-10-28
---

# Phase 2 Plan 01: Live test matrix and one-line errors Summary

`scripts/test-live.sh` proves AudioComIE on yt-dlp 2026.10.26 and 2026.08.19 through yt-dlp's own pinned test harness and a real download, and missing tracks now fail with `ERROR: [AudioCom] <slug>: This audio.com track is unavailable (removed, private, or wrong URL)`.

## What was built

- **test-live.sh**: per venv, in fixed order: interpreter present, exact version pin, sparse harness at the pinned tag commit (clean, no `yt_dlp/`), offline suite, `AudioComIE` whole-word in `Extractor Plugins:`, `_TESTS` (3 passed required), real m4a download (7,169,078 bytes), and the missing-track one-line error. It runs every step even after a failure and ends with `ALL TARGETS PASSED` or `SOME TARGETS FAILED`. File mode is 100755.
- **run_live_tests.py**: refuses a harness with `yt_dlp/`, calls `load_all_plugins()` and then runs pytest on the harness's `test_download.py` (exit 5 when nothing is collected).
- **Extractor**: `_TESTS[1]` jasa-sisemore. `_call_api` maps 404/410 to "unavailable" and 401/403 to "private or restricted", both expected, with `video_id` and no cause attached. Other statuses are re-raised. The no-embed-URL, no-transcodings and id-mismatch errors now carry `video_id`. `is_public` is never read.
- **Tests**: 126 to 140 passed on both venvs. `_TESTS` replay is parametrized per entry, D-08 set/order test, 401/403/404/410/500 on both endpoints, unlisted-track test.

## Verification

| Check | Result |
|-------|--------|
| `pytest -q` on both venvs | 140 passed, 6 skipped |
| `scripts/test-live.sh` | rc 0, ALL TARGETS PASSED, 6 ok lines per venv |
| Tampered tracked file in 2026.10.26 harness | FAIL harness line, SOME TARGETS FAILED, rc 1 |
| Untracked file planted in harness | refused the same way |
| `.venv` moved away | `FAIL: .venv has no python`, `.venv-metube` still ran, rc 1 |
| Plugin regex | matches with neighbours, rejects `AudioComFooIE` and `AudioComIE_x` |
| `-k NoSuchExtractorZZ` | pytest exit 5 |
| CLI missing-slug check | ONE-LINE ERRORS OK on both venvs |

The live runs used `AUDIOCOM_HARNESS_DIR` and `TMPDIR` in the session scratchpad (RESEARCH Pitfall 7). No signed URLs appear in the run logs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Harness also refused when it has untracked files**
- **Found during:** Task 1
- **Issue:** `git diff --quiet HEAD` ignores untracked files, so a planted `test/conftest.py` would run unnoticed (T-02-01).
- **Fix:** also require an empty `git status --porcelain`. Clean cached harnesses still pass on rerun.
- **Files modified:** scripts/test-live.sh
- **Commit:** 1387317

**2. [Rule 2 - Security] Echoed tool output is redacted**
- **Found during:** Task 1
- **Issue:** harness or yt-dlp failure output could include presigned media URLs (T-02-04).
- **Fix:** a `redact` sed filter strips URL query strings from everything the script echoes.
- **Files modified:** scripts/test-live.sh
- **Commit:** 1387317

**3. [Rule 1 - Bug] RED tests compared the prefixed message**
- **Found during:** Task 2 GREEN
- **Issue:** `ExtractorError.msg` is `[AudioCom] <id>: <text>` once `video_id` is set, so `msg == locked text` could never pass.
- **Fix:** assert `orig_msg` equals the locked text and `str(err)` equals the full one-line form, which is stricter.
- **Files modified:** tests/test_extract_offline.py
- **Commit:** da578f8

Additional steps not in the plan's list: `ok: yt-dlp <version>` and `ok: harness <tag> at <sha>` lines, so every check prints one line. If there is no clean harness, `_TESTS` prints `FAIL: _TESTS not run`.

## TDD Gate Compliance

Task 2: RED commit 4fb25c6 (12 tests failing on both venvs for the intended reasons: not expected, no video_id, no 401/403/410 mapping), then GREEN commit da578f8.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: scripts/test-live.sh, scripts/run_live_tests.py, README.md
- FOUND commits: 1387317, 4fb25c6, da578f8
