---
phase: 02-edge-cases-and-version-compatibility
verified: 2026-10-28T20:07:08Z
status: passed
score: 15/15 must-haves verified
covered_files:
  - ".gitignore"
  - ".planning/phases/02-edge-cases-and-version-compatibility/02-01-PLAN.md"
  - ".planning/phases/02-edge-cases-and-version-compatibility/02-01-SUMMARY.md"
  - ".planning/phases/02-edge-cases-and-version-compatibility/02-02-PLAN.md"
  - ".planning/phases/02-edge-cases-and-version-compatibility/02-02-SUMMARY.md"
  - ".planning/phases/02-edge-cases-and-version-compatibility/02-03-PLAN.md"
  - ".planning/phases/02-edge-cases-and-version-compatibility/02-03-SUMMARY.md"
  - "README.md"
  - "scripts/record_fixture.py"
  - "scripts/run_live_tests.py"
  - "scripts/test-live.sh"
  - "tests/conftest.py"
  - "tests/fixtures/1772828397072996.json"
  - "tests/fixtures/1782423994666898.json"
  - "tests/fixtures/1795055938670272.json"
  - "tests/fixtures/1858402410391836.json"
  - "tests/fixtures/1861573231849291.json"
  - "tests/fixtures/1877766681285368.json"
  - "tests/fixtures/1880272004207526.json"
  - "tests/fixtures/1880272416485027.json"
  - "tests/fixtures/1880272428195927.json"
  - "tests/fixtures/1880272651234303.json"
  - "tests/fixtures/1880272945380630.json"
  - "tests/fixtures/1880273150344633.json"
  - "tests/test_extract_offline.py"
  - "tests/test_fixture_hygiene.py"
  - "tests/test_metadata_offline.py"
  - "tests/test_sources_offline.py"
  - "yt_dlp_plugins/extractor/audiocom.py"
covered_digest: "v3:sha256:099dae009f2739ab848e125a1b6f68fb9dc3c85ee0d74189d3d507f3eaf27203"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 14/15
  gaps_closed: []
  gaps_remaining: []
  regressions: []
  reason: "Fingerprint stale after Phase 3 edited README.md (additive ## MeTube section only). Backstop truth and three judgment prohibitions signed off in 02-UAT.md (status complete, 4/4 pass)."
---

# Phase 2: Edge Cases and Version Compatibility Verification Report

**Phase Goal:** The plugin works on every track variant and on both target yt-dlp versions, and has a test command that proves it.
**Verified:** 2026-10-28T20:07:08Z
**Status:** passed
**Re-verification:** Yes (refresh after Phase 3 changed README.md; HEAD 01132d9)

## What changed since the last report

`git diff 68d007c HEAD` outside `.planning/` touches only `README.md` (+97 lines, one new `## MeTube` section inserted before `## Development setup`, nothing removed or edited) and the new Phase 3 file `scripts/deploy-metube.sh`. No Phase 2 code, test, fixture or script changed. The README `## Live tests`, `## Original uploads` and `## Errors` sections are byte-identical to the previously verified text and were re-checked against current code and live behavior below.

## User Flow Coverage

| Step | Expected | Evidence (this run) | Status |
| ---- | -------- | -------- | ------ |
| One local command proves it on both versions | ALL TARGETS PASSED | `scripts/test-live.sh` (TMPDIR in scratchpad): rc 0, 8 ok lines per venv, no FAIL | ✓ |
| Reference track | Default transcoding downloads | `ok: downloaded 7169078 bytes` on 2026.10.26 and 2026.08.19 | ✓ |
| Downloadable track, ask for the original | `-F` lists `original` | alec-murray/podcast-intro `-F`: `original m4a ... 65k original upload` on both venvs | ✓ |
| Downloadable track, do not ask | A transcoding | default picks `m4a`, `-f wa` picks `mp3` on both venvs | ✓ |
| Non-downloadable track | No original | test-live step 9 ok on both venvs | ✓ |
| Gone track | One-line reason | test-live step 8 ok on both venvs (exact `ERROR: [AudioCom] this-slug-does-not-exist-zz9: ...` line) | ✓ |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | SC1: downloadable track offers its original as an extra format; non-downloadable never lists one | ✓ VERIFIED | Gate `data.get('is_downloadable') is True and self._original_requested()` (audiocom.py:195); live alec-murray `-F` lists original, test-live step 9 negative ok, both venvs |
| 2 | SC2: removed/private/nonexistent URL gives one-line ERROR with cause, no traceback | ✓ VERIFIED | audiocom.py:130,135-137; test-live step 8 ok on both venvs |
| 3 | SC3: one documented command runs `_TESTS` (reference + ≥1 other) and passes | ✓ VERIFIED | README `## Live tests` documents `scripts/test-live.sh`; `ok: _TESTS 3 passed` on both venvs |
| 4 | SC4: test command and real download pass on 2026.08.19 and 2026.10.26 | ✓ VERIFIED | `ALL TARGETS PASSED`, rc 0; versions pinned (`ok: yt-dlp 2026.10.26`, `ok: yt-dlp 2026.08.19`) |
| 5 | test-live.sh refuses wrong pin and a non-pristine harness | ✓ VERIFIED | Script unchanged since tamper run in prior report; `status --porcelain --ignored` check at test-live.sh:75; harness SHAs f264a6c… / 3a08bea… confirmed this run |
| 6 | Fixed target order; keeps going after failure; non-zero on any failure | ✓ VERIFIED | Order .venv then .venv-metube in this run; script unchanged since prior tamper run (rc 1, continued) |
| 7 | Plugin check matches AudioComIE in `Extractor Plugins:` | ✓ VERIFIED | `ok: plugin listed` both venvs |
| 8 | 401/403 JSON → "private or restricted"; non-API 403/500 re-raised | ✓ VERIFIED | `_is_api_answer` (audiocom.py:113,135); offline suite 384 passed on both venvs |
| 9 | Unlisted (`is_public: false`) extracts normally | ✓ VERIFIED | Offline suite passes; flag never read (code unchanged) |
| 10 | Multi-version tracks keep only newest source | ✓ VERIFIED | Offline suite passes on both venvs; code unchanged since live check in prior report |
| 11 | 12 sanitized fixtures | ✓ VERIFIED | 12 fixtures in covered set; hygiene tests in the 384 passed |
| 12 | Original is opt-in only | ✓ VERIFIED | Live: default `m4a`, `wa` `mp3` on alec-murray both venvs; offline selector tests pass |
| 13 | WavPack skipped; failed probe drops original; Range 0-0 probe | ✓ VERIFIED | audiocom.py:105 `Range: bytes=0-0`, :108 skip message, :199 wv note; offline tests pass |
| 14 | Phase 1 not regressed | ✓ VERIFIED | Reference real download 7,169,078 bytes both venvs; `_TESTS` reference passes |
| 15 | No mutable shared state; parallel/interrupted extractions independent (backstop) | ✓ VERIFIED (human) | Signed off in 02-UAT.md test 1 (result: pass); code unchanged |

**Score:** 15/15 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `scripts/test-live.sh` | ✓ VERIFIED | Ran green this session |
| `scripts/run_live_tests.py` | ✓ VERIFIED | Drives step 6, 3 passed per venv |
| `yt_dlp_plugins/extractor/audiocom.py` | ✓ VERIFIED | Unchanged since prior verification |
| Offline tests + `conftest.py` | ✓ VERIFIED | 384 passed / 120 skipped per venv |
| `README.md` | ✓ VERIFIED | Phase 2 sections (Development setup, Offline tests, Live tests, Original uploads, Errors) intact and match code and live output; Phase 3 addition is a separate section |
| `.gitignore` | ✓ VERIFIED | Unchanged |

### Key Link Verification

All declared links WIRED (unchanged code). The 02-03 `_is_valid_url` link remains an intentional alternative (`_probe_original`, same Range 0-0 GET, WR-02), as documented in the prior report.

### Behavioral Spot-Checks

| Behavior | Result | Status |
| -------- | ------ | ------ |
| `scripts/test-live.sh` both venvs | ALL TARGETS PASSED, rc 0 | ✓ PASS |
| alec-murray `-F` / default / `-f wa` both venvs | original listed; m4a; mp3 | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` declared or present. Not applicable.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| ----------- | ---------- | ------ | -------- |
| EXTR-04 | 02-02, 02-03 | ✓ SATISFIED | Truths 1, 12, 13 |
| EXTR-06 | 02-01 | ✓ SATISFIED | Truths 2, 8 |
| PLUG-02 | 02-01, 02-02, 02-03 | ✓ SATISFIED | Truths 4, 7 |
| PLUG-03 | 02-01 | ✓ SATISFIED | Truth 3 |

No orphaned requirements; REQUIREMENTS.md maps exactly these four to Phase 2 (now marked Complete).

### Prohibitions

| Prohibition | Tier | Disposition |
| ----------- | ---- | ----------- |
| No raise/warn on is_public false | test | ✓ enforced |
| No vendored harness or yt_dlp/ | test | ✓ enforced |
| No signed URLs / audio committed | test | ✓ hygiene tests |
| Original only when is_downloadable True | test | ✓ offline + live |
| Original never default / ba / -S | test | ✓ offline + live |
| No login/credentials (D-07) | judgment | ✓ human-resolved, 02-UAT.md test 2 pass |
| MeTube untouched in Phase 2 | judgment | ✓ human-resolved, 02-UAT.md test 3 pass |
| No bypass option | judgment | ✓ human-resolved, 02-UAT.md test 4 pass |

### Anti-Patterns Found

None in Phase 2 files (unchanged). IN-01..IN-04 from 02-REVIEW remain info-only.

### Human Verification Required

None outstanding. All four items were signed off in `02-UAT.md` (status: complete, 4/4 pass).

### Gaps Summary

No gaps. Phase 3's README change is additive and leaves the Live tests, Original uploads and Errors sections accurate; the live test command passes on both pinned yt-dlp versions against the current code.

---

_Verified: 2026-10-28T20:07:08Z_
_Verifier: Claude (gsd-verifier)_
