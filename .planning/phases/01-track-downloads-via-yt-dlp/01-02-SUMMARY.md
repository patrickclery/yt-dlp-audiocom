---
requirements-completed: [EXTR-02, EXTR-03, EXTR-05]
phase: 01-track-downloads-via-yt-dlp
plan: 02
subsystem: extractor
status: complete
tags: [yt-dlp, plugin, audio.com, fixtures, format-sort, metadata]
requires: ["01-01"]
provides:
  - "scripts/record_fixture.py: one-command redacted fixture recorder through the plugin's own _download_json"
  - "8 allowlisted fixtures in tests/fixtures/ with mp3-only, mp3>m4a, empty author_name, cover, description coverage"
  - "Bitrate-ranked formats (quality = abr) with asr/audio_channels/filesize and MIME ext fallback"
  - "Full EXTR-05 metadata mapping with D-11 uploader and thumbnail fallbacks"
affects: []
tech-stack:
  added: []
  patterns: ["monkeypatched _download_json over recorded fixtures", "deep-copied info before process_ie_result", "traverse_obj dict mapping with filter for absent-when-empty fields"]
key-files:
  created:
    - scripts/record_fixture.py
    - tests/test_fixture_hygiene.py
    - tests/conftest.py
    - tests/test_extract_offline.py
    - tests/test_metadata_offline.py
    - tests/fixtures/1877766681285368.json
    - tests/fixtures/1782423994666898.json
    - tests/fixtures/1795055938670272.json
    - tests/fixtures/1861573231849291.json
    - tests/fixtures/1880272428195927.json
    - tests/fixtures/1880272004207526.json
    - tests/fixtures/1880273150344633.json
    - tests/fixtures/1880272651234303.json
  modified:
    - yt_dlp_plugins/extractor/audiocom.py
    - .planning/phases/01-track-downloads-via-yt-dlp/SKELETON.md
decisions:
  - "quality = abr on every format so yt-dlp's default sort picks the highest bitrate (mp3 160k beats m4a 8.9k on arthur-hpcp)"
  - "run_extract deep-copies info before process_ie_result so yt-dlp's in-place format fill-in cannot mask extractor output"
  - "Edge tests reject ExtractorError whose cause is KeyError/TypeError/StopIteration/IndexError (extract() wraps KeyError)"
metrics:
  duration: "~15 min"
  completed: 2026-10-28
actuals:
  tokens: 8600
  tasks: 3
  commits: 5
plan_head_before: 60b18ccd9600a4b4a49f6d7f81423f06c11073ce
plan_head_after: c6a0e90
---

# Phase 1 Plan 02: Fixtures, Bitrate Ranking and Metadata Summary

Eight redacted, allowlisted audio.com fixtures recorded through the plugin's own request path drive an offline suite that proves highest-bitrate selection (`quality = abr`) and the full EXTR-05 metadata mapping with username/avatar fallbacks. Green on yt-dlp 2026.10.26 and 2026.8.19 (115 passed, 6 skipped each).

## Tasks

| Task | Name | Commit | Result |
|------|------|--------|--------|
| 1 | Fixture recorder + 8 fixtures + hygiene test | 7915077 | All 8 context-table tracks recorded, no substitutes. 34 hygiene tests pass. `FIXTURES CLEAN`, allowlist and presign greps pass. arthur-hpcp re-record prints `1861573231849291 ...` once |
| 2 (RED) | Offline format/selection/edge tests | bc44e94 | 11 failed (missing quality/asr/channels/filesize, MIME fallback; arthur-hpcp and shivgas picked m4a) |
| 2 (GREEN) | Bitrate ranking, format fields | e27a7fe | `FORMATS OK` (mp3/mp3 and m4a/aac audio-only rows). arthur-hpcp selects `AudioCom mp3` |
| 3 (RED) | Offline metadata tests | 86dcd34 | 10 failed (metadata fields, fallbacks, `_TESTS`) |
| 3 (GREEN) | Metadata mapping + `_TESTS[0]` | c6a0e90 | `--print` gives `David Oliveira\|david-oliveira-1877766671108274\|186.358\|20260930`. Embedded download: ffprobe `title=Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best`, `artist=David Oliveira` |

Fixture substitutions: none. EXPECTED/BEST table changes: none; every recorded value matched the context table.

## Verification

- `.venv/bin/python -m pytest -q` and `.venv-metube/bin/python -m pytest -q`: 115 passed, 6 skipped (skips are `test_mp3_only_yields_one_format` on the 6 two-format fixtures)
- `git ls-files '*.m4a' '*.mp3' '*.part'` is empty. No `'md5'`, `impersonate` or `sources` in the extractor
- SKELETON.md: Data read and Data write ticked; all Phase 1 stack boxes now checked
- Human-check (queued for end-of-phase UAT): play `/tmp/claude-1000/-home-patrick-github-com-patrickclery-audio-com-downloader/b3b4fecb-6dde-482c-aee9-1603f83e8e2d/scratchpad/embed/1877766681285368.m4a` (about 3:06, title and artist shown)

## TDD Gate Compliance

- Task 2: RED bc44e94 `test(01-02)`, GREEN e27a7fe `feat(01-02)`
- Task 3: RED 86dcd34 `test(01-02)`, GREEN c6a0e90 `feat(01-02)`
- REFACTOR: not needed

## Deviations from Plan

**1. [Rule 3 - Blocking] RED and GREEN committed separately (Tasks 2 and 3)**
- The plan said to commit tests and extractor together; the canonical TDD reference expects a failing-test commit. Same handling as 01-01.

**2. [Rule 1 - Bug] run_extract deep-copies info before processing**
- **Found during:** Task 2 RED. With `dict(info)`, `process_ie_result` filled the missing m4a `ext` from the URL path in the shared format dicts, so the MIME-fallback mutation test passed against code without the fallback.
- **Fix:** `copy.deepcopy(info)` in `tests/conftest.py`. The test then failed RED as intended.

**3. [Rule 2 - Correctness] Edge tests also reject wrapped KeyError/TypeError**
- `InfoExtractor.extract()` re-raises KeyError/StopIteration as ExtractorError, so `pytest.raises(ExtractorError)` alone could not prove "never KeyError". Edge tests assert `exc.cause` is not one of those types.

**4. [Rule 2 - Correctness] `username` uses `filter`**
- Plan specified `('username', {str})`. Added `filter` so an empty username also falls back to the URL user group, keeping `uploader_id`/`uploader_url` non-empty.

**5. [Rule 3 - Blocking] Embedded-metadata download went to the scratchpad, not `mktemp -d`**
- Hard constraint: downloaded audio goes under the session scratchpad. Same command otherwise.

**6. [Rule 3 - Blocking] Plan commit ledger not written to disk**
- Same sandbox restriction as 01-01; used the known spawn base `60b18cc` for `plan_head_before`.

## Known Stubs

None.

## Threat Flags

None. The recorder adds no network surface beyond the plugin's own two API requests and prints only `<id> <path>` (failures print only the exception type, or the matched marker names on refusal).

## Self-Check: PASSED

- FOUND: scripts/record_fixture.py, tests/conftest.py, tests/test_fixture_hygiene.py, tests/test_extract_offline.py, tests/test_metadata_offline.py, 8 fixtures
- FOUND: 7915077, bc44e94, e27a7fe, 86dcd34, c6a0e90 (ancestors of HEAD)
