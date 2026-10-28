---
phase: 02-edge-cases-and-version-compatibility
plan: 02
subsystem: extractor
tags: [yt-dlp, plugin, fixtures, multi-version, redaction]
status: complete

requires:
  - phase: 02-edge-cases-and-version-compatibility
    plan: 01
    provides: scripts/test-live.sh, _TESTS reference + jasa, HTTP error mapping
provides:
  - Recorder allowlist with is_downloadable, is_public, sources[] (SOURCE_KEYS) and transcodings[].source_id
  - 12 commit-safe fixtures (8 re-recorded, 4 new)
  - tests/conftest.py current_transcodings(audio) oracle
  - Newest-source selection in AudioComIE._real_extract (local `current`, used by 02-03 as the original)
affects: [02-03]

actuals:
  tokens: 10544
  tasks: 2
  commits: 3
plan_head_before: d5f2e555786bd09d03884869e71a3632578607e7
plan_head_after: 6c478b9a93f98238cd5d53dd8ae403669c9f52ef

tech-stack:
  added: []
  patterns:
    - "Per-entry allowlist projection for nested API lists (sources[]) with strip_url on every url"
    - "Test oracle (current_transcodings) written independently of the extractor's traverse_obj code"

key-files:
  created:
    - tests/fixtures/1880272945380630.json
    - tests/fixtures/1880272416485027.json
    - tests/fixtures/1772828397072996.json
    - tests/fixtures/1858402410391836.json
  modified:
    - scripts/record_fixture.py
    - tests/test_fixture_hygiene.py
    - tests/conftest.py
    - tests/test_extract_offline.py
    - tests/test_metadata_offline.py
    - yt_dlp_plugins/extractor/audiocom.py
    - tests/fixtures/ (8 Phase 1 fixtures re-recorded)

key-decisions:
  - "Newest upload = max int_or_none(date_created) or 0 over reversed(sources), so ties go to the later entry; fallback to every URL-bearing transcoding when sources/source_id are absent or unmatched"
  - "Duration comes from the first transcoding of the current upload, not transcodings[0]"
  - "check_record treats sources: null as absent and refuses any non-list sources"

requirements-completed: [PLUG-02]

coverage:
  - id: D1
    description: "Fixtures carry download flag and source metadata with no signed URLs or uploader filenames"
    requirement: EXTR-04
    verification:
      - kind: unit
        ref: "tests/test_fixture_hygiene.py"
        status: pass
  - id: D2
    description: "Re-uploaded track lists only the current upload's formats and duration on both versions"
    requirement: PLUG-02
    verification:
      - kind: unit
        ref: "tests/test_extract_offline.py::test_multi_version_*"
        status: pass
      - kind: e2e
        ref: "yt-dlp --simulate louder-jazz-bababa on .venv and .venv-metube → 314.088|[\"mp3\"]"
        status: pass
      - kind: e2e
        ref: "scripts/test-live.sh → ALL TARGETS PASSED"
        status: pass

duration: ~20min
completed: 2026-10-28
---

# Phase 2 Plan 02: Source Metadata Fixtures and Newest-Upload Selection Summary

**The recorder now captures is_downloadable, is_public, sources[] and source_id without signed URLs or uploader filenames. Re-uploaded tracks now list only the newest upload's formats and its duration: louder-jazz gives 314.088 s with one mp3 instead of 240.024 s with mp3-0/mp3-1.**

## Performance

- Duration: about 20 min
- Tasks: 2/2
- Files: 18 changed (+701 / -19)

## Accomplishments

- `SOURCE_KEYS` allowlist with a per-entry `_check_keys` in `check_record()`. The `download`, `name`, `md5`, `from`, `waveform`, `date_updated` and `date_uploaded` fields are dropped, and the comment in the code says why.
- Recorded 12 fixtures: the 8 Phase 1 tracks plus alec-murray, andrea-mathiopoulos, louder-jazz-bababa and beso. **No substitutions were needed.** Together they cover dl=true (5) and dl=false (7), source formats wv/wav/mp3/m4a, wav served from a wavpack upload (andrea), 2+ sources (louder-jazz, beso) and is_public false (louder-jazz).
- Hygiene tests now cover sources-download/name/md5/dict mutations, the dict and bare-URL-list shapes, a projection test that drops the extra source fields, and a per-fixture flag/source invariant. `test_shape_coverage` checks the new shapes.
- `current_transcodings(audio)` is the oracle that both offline test modules use for expected formats and duration.
- The extractor now selects the newest source, with the tie, bad-date, no-sources, no-source_id and no-match edges pinned by mutation tests.

## Task Commits

1. **Task 1: Recorder and 10 fixtures:** `11e16a5` (feat)
2. **Task 2 RED: Multi-version fixtures and failing tests:** `4cdea85` (test)
3. **Task 2 GREEN: Newest-source selection:** `6c478b9` (feat)

## Table Changes

- New BEST/EXPECTED rows for these tracks:
  - alec-murray: m4a; 'alec Murray', 38.792, 20261028
  - andrea: m4a; 'Andrea Mathiopoulos', 10.789, 20261028
  - louder-jazz: mp3; 'Trebor', 314.088, 20230730, thumb+desc
  - beso: m4a (311.263 > 192); 'Maya', 173.035, 20260228, thumb+desc
- No Phase 1 row changed. Re-recording changed only stats counts and added the new keys.

## Verification

- `pytest -q` passes on both venvs: 195 passed, 10 skipped.
- FIXTURES CLEAN gate passed after Task 1. The x-amz guard passes. Re-recording arthur-hpcp prints exactly one line, `1861573231849291 tests/fixtures/...`.
- Live: `314.088|["mp3"]` on yt-dlp 2026.10.26 and 2026.08.19. `scripts/test-live.sh` ends ALL TARGETS PASSED with 0 FAIL lines.

## TDD Gate Compliance

RED `4cdea85`: 9 failures on both venvs, including duration `240.024 != 314.088` and `['mp3','mp3'] != ['mp3']`. GREEN `6c478b9` makes them pass. No refactor commit was needed.

## Deviations from Plan

None. The plan was executed as written.

## Known Stubs

None.

## Notes

- Assumption A4 still applies: "newest date_created wins" is deterministic but was confirmed against the site player on only two tracks.
- Six fixture tracks were uploaded on 2026-10-28 and may disappear. Only the reference and jasa tracks are in live `_TESTS`.

## Self-Check: PASSED

- All 4 new fixture files and all 6 modified source and test files exist.
- Commits 11e16a5, 4cdea85 and 6c478b9 are ancestors of HEAD.
