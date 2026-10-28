---
phase: 02-edge-cases-and-version-compatibility
verified: 2026-10-28T20:05:00Z
status: passed
score: 14/15 must-haves verified
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
covered_digest: "v3:sha256:c4692970fa5724a80699beaf94eb308e0eba4f183be47cab98b4a122979e7de7"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Concurrency backstop (02-03 truth, verification: backstop): run two extractions of a downloadable track in parallel (e.g. two MeTube queue items, or two `yt-dlp -f original` processes on alec-murray) and interrupt one `-f original` download, then re-run it"
    expected: "Both extractions succeed independently; the interrupted download resumes from its .part file"
    why_human: "Non-inferable truth. Code inspection shows no mutable module/class state in AudioComIE and the probe is a read-only one-byte GET, but no held-out or property test exercises parallel/interrupted runs, so presence+wiring cannot certify it"
  - test: "Judgment prohibition (02-01 / 02-02): confirm no login, cookies, credentials or created audio.com tracks/accounts were used to probe or record fixtures (D-07)"
    expected: "Anonymous probing only"
    why_human: "Judgment-tier prohibition. LLM-judge verdict (non-authoritative): no cookie/login/password/extractor-arg use in audiocom.py or scripts/; fixtures are public-by-link tracks. Flag: unverified-prohibition, human review recommended"
  - test: "Judgment prohibition (02-01): confirm the MeTube container and /opt/metube were not touched in this phase"
    expected: "No change to MeTube"
    why_human: "Judgment-tier prohibition. LLM-judge verdict (non-authoritative): /opt/metube/plugins/yt_dlp_plugins/extractor/ holds only rumble_fix.py, mtime 2026-10-19, no audiocom.py. Container state not inspected. Flag: unverified-prohibition, human review recommended"
  - test: "Judgment prohibition (02-03): confirm there is no option, extractor-arg or fallback that exposes the original of a track not flagged downloadable"
    expected: "Only `is_downloadable is True` opens the gate"
    why_human: "Judgment-tier prohibition. LLM-judge verdict (non-authoritative): audiocom.py:195 requires `data.get('is_downloadable') is True`; no _configuration_arg/extractor_args anywhere; live `-f original` on jasa-sisemore fails 'Requested format is not available' on both venvs. Flag: unverified-prohibition, human review recommended"
---

# Phase 2: Edge Cases and Version Compatibility Verification Report

**Phase Goal:** The plugin works on every track variant and on both target yt-dlp versions, and has a test command that proves it.
**Verified:** 2026-10-28T20:05:00Z
**Status:** human_needed
**Re-verification:** No (initial verification; current code after 02-REVIEW-FIX, HEAD 6ec2d73)

**MVP mode note (warning):** ROADMAP marks Phase 2 `mode: mvp`, but its goal line is not in user-story form (`user-story.validate` = false). Verified against the user story restated in 02-01-PLAN.md (validates true), as Phase 1 did. Run `/gsd-mvp-phase 2` to canonicalize ROADMAP if wanted.

## User Flow Coverage

| Step | Expected | Evidence | Status |
| ---- | -------- | -------- | ------ |
| Give yt-dlp a normal track URL (reference) | Highest-bitrate transcoding with metadata | Both venvs: selects `m4a` (306 kbps over mp3 192), title/uploader/duration 186.358/upload_date 20260930 correct; real download 7,169,078 bytes | ✓ |
| Give an unlisted track (louder-jazz-bababa, is_public false) | Extracts normally | Both venvs: `314.088|["mp3"]` | ✓ |
| Give a re-uploaded track | Only current upload's formats/duration | louder-jazz `314.088|["mp3"]`, beso `173.035|["mp3","m4a"]` on both venvs | ✓ |
| Downloadable track, ask for the original | `-F` lists `original`; `-f original` downloads it | alec-murray: `-F` lists `original m4a aac 65k original upload`; `-f original` wrote 331,730-byte AAC m4a on both venvs | ✓ |
| Downloadable track, do not ask | A transcoding, never the original | alec-murray default/ba/-S abr/-S size give `m4a`; worst/wa give `mp3` (WR-01 fix holds) | ✓ |
| Non-downloadable track | Never lists an original | jasa-sisemore `-F` shows only mp3; `-f original` gives "Requested format is not available" on both venvs | ✓ |
| Gone track | One-line reason | `ERROR: [AudioCom] this-slug-does-not-exist-zz9: This audio.com track is unavailable (removed, private, or wrong URL)` on both venvs, no traceback | ✓ |
| One local command proves it on both versions | ALL TARGETS PASSED | `scripts/test-live.sh` run by verifier: rc 0, 8 ok lines per venv, no FAIL | ✓ |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | SC1: downloadable track offers its original as an extra format; non-downloadable never lists one | ✓ VERIFIED | WR-01 narrows listing to `-f` naming `original`, `-F`, or `-f -`. That still satisfies SC1: the original is discoverable in `-F` and selectable with `-f original` (live, both venvs). Gate `is_downloadable is True` (audiocom.py:195). Offline: `test_original_only_when_downloadable`, `test_list_formats_lists_original`, `test_no_source_url_leaks_when_not_downloadable` over all 12 fixtures |
| 2 | SC2: removed/private/nonexistent URL gives one-line ERROR with cause, no traceback, no bare 404 | ✓ VERIFIED | Live on both venvs (test-live step 8 + spot check). 404/410 mapping has no header condition, so WR-05 does not affect it. Removed/private could not be produced anonymously; RESEARCH shows every anonymous failure is JSON 404 and the API says "There are no private audio" |
| 3 | SC3: one documented command runs `_TESTS` (reference + ≥1 other) and passes | ✓ VERIFIED | README `## Live tests` documents `scripts/test-live.sh`; run gave `_TESTS 3 passed` (test_AudioCom, _1, _all) on both venvs; `_TESTS` = reference + jasa-sisemore + only_matching |
| 4 | SC4: test command and real download pass on 2026.08.19 and 2026.10.26 | ✓ VERIFIED | Verifier run of test-live.sh: `ALL TARGETS PASSED`, rc 0; `ok: downloaded 7169078 bytes` on both; versions pinned (`ok: yt-dlp 2026.10.26` / `2026.08.19`) |
| 5 | test-live.sh refuses wrong version pin and a harness not exactly the pinned SHA / dirty | ✓ VERIFIED | Tamper run (helper.py appended in a copied harness): `FAIL: harness 2026.10.26 is not a clean checkout of f264a6c…`, `SOME TARGETS FAILED`, rc 1. Check now includes `--ignored` (WR-04) |
| 6 | Fixed target order; keeps going after a failure; non-zero if any step failed | ✓ VERIFIED | Same tamper run: .venv ran remaining steps, then .venv-metube ran all 8 ok steps; final rc 1 |
| 7 | Plugin check matches AudioComIE as a whole word in `Extractor Plugins:` | ✓ VERIFIED | `PLUGIN_RE='Extractor Plugins: .*\bAudioComIE\b'`, capture-then-grep; `ok: plugin listed` on both; no piped quiet grep in script |
| 8 | 401/403 JSON API answer gives expected "private or restricted"; HTML/cf-mitigated/no-type re-raise yt-dlp's error; 500 re-raised (WR-05) | ✓ VERIFIED | `_is_api_answer` (audiocom.py:113-116,135). 27 error-mapping tests pass on each venv, incl. `test_edge_restricted_is_one_line_expected_error` and `test_edge_non_api_403_is_reraised_unchanged` (expected False) |
| 9 | `is_public: false` (unlisted) extracts normally; flag never read | ✓ VERIFIED | `grep is_public audiocom.py` empty; unlisted test passes; louder-jazz (is_public false) extracts live |
| 10 | Multi-version tracks keep only newest source's transcodings and duration | ✓ VERIFIED | Live both venvs: louder-jazz `314.088|["mp3"]`, beso `173.035|["mp3","m4a"]` |
| 11 | 12 fixtures with is_downloadable/is_public/sources/source_id, free of signed URLs and filenames | ✓ VERIFIED | 12 files present; hygiene suite in the 384-passed run; `git grep X-Amz` hits only test inputs, a doc comment and .claude/CLAUDE.md prose |
| 12 | Original is opt-in: default, ba, -S abr, -S size, worst, wa never pick it; `-f original` does | ✓ VERIFIED | Live alec-murray both venvs (see flow table); offline `test_generic_selectors_never_reach_original` (11 selectors) and `test_listed_original_never_selected_by_default_or_ranking` |
| 13 | WavPack/unknown-ext original skipped; failed Range probe drops original and extraction still succeeds; no offline network | ✓ VERIFIED | Reference (wv source) lists no original; arthur-hpcp `-F` live prints `original upload URL is invalid, skipping: HTTP Error 404: Not Found` and still lists transcodings; `test_probe_only_for_downloadable` asserts headers == `{'Range': 'bytes=0-0'}`; conftest autouse stub |
| 14 | Phase 1 not regressed: reference downloads highest-bitrate transcoding with metadata | ✓ VERIFIED | Both venvs: `m4a|306.343`, title, uploader, duration 186.358, upload_date 20260930; real 7,169,078-byte m4a |
| 15 | AudioComIE keeps no mutable shared state; parallel/interrupted extractions independent (backstop) | ? insufficient_spec | Inspection: no module/class mutable state, probe is read-only. No test exercises it. Routed to human verification |

**Score:** 14/15 truths verified (0 present-but-behavior-unverified; 1 insufficient_spec)

### Required Artifacts

`verify.artifacts`: 02-01 6/6, 02-02 6/6, 02-03 6/6 passed.

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `scripts/test-live.sh` | ✓ VERIFIED | mode 100755, both SHAs, 9 steps, ran green |
| `scripts/run_live_tests.py` | ✓ VERIFIED | `load_all_plugins()` before pytest; refuses `yt_dlp/` |
| `yt_dlp_plugins/extractor/audiocom.py` | ✓ VERIFIED | locked messages, `video_id=`, source_id selection, gated `original` |
| `tests/test_sources_offline.py`, `test_extract_offline.py`, `test_metadata_offline.py`, `test_fixture_hygiene.py`, `conftest.py` | ✓ VERIFIED | 384 passed / 120 skipped (parametrized per-fixture skips) on both venvs |
| `README.md` | ✓ VERIFIED | Development setup (pins incl. `yt-dlp==2026.8.19`), Offline tests, Live tests, Original uploads (`-f original`), Errors |
| `.gitignore` | ✓ VERIFIED | `*.wav *.flac *.aiff *.ogg *.m4a *.mp3` |

### Key Link Verification

`verify.key-links`: 02-01 5/5, 02-02 3/3, 02-03 3/4.

| From | To | Status | Details |
| ---- | --- | ------ | ------- |
| audiocom.py | `InfoExtractor._is_valid_url` | WIRED (alternative) | Pattern absent by design: WR-02 replaced `_is_valid_url` with `_probe_original()` (same one-byte Range GET via `_request_webpage`, prints status only). Still runs only after the is_downloadable and ext checks. Proven live (arthur-hpcp) and offline (Range header test) |
| All other declared links | | WIRED | tool-verified |

**This looks intentional.** To clear the tool mismatch, add to this file's frontmatter:

```yaml
overrides:
  - must_have: "audiocom.py to InfoExtractor._is_valid_url via one-byte GET probe"
    reason: "WR-02 replaced _is_valid_url with inline _probe_original (same Range 0-0 GET) so a transport error cannot print the signed URL"
    accepted_by: "{name}"
    accepted_at: "{ISO timestamp}"
```

### Behavioral Spot-Checks

| Behavior | Result | Status |
| -------- | ------ | ------ |
| `scripts/test-live.sh` (both venvs) | ALL TARGETS PASSED, rc 0 | ✓ PASS |
| Tampered harness copy | harness FAIL line, SOME TARGETS FAILED, rc 1 | ✓ PASS |
| alec-murray `-f original` download (both venvs) | 331,730-byte AAC m4a in scratchpad | ✓ PASS |
| jasa-sisemore `-f original` | Requested format is not available | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` declared or present. Not applicable.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| ----------- | ---------- | ------ | -------- |
| EXTR-04 | 02-02, 02-03 | ✓ SATISFIED | Truths 1, 12, 13 |
| EXTR-06 | 02-01 | ✓ SATISFIED | Truths 2, 8 |
| PLUG-02 | 02-01, 02-02, 02-03 | ✓ SATISFIED | Truths 4, 7; plugin listed on both versions |
| PLUG-03 | 02-01 | ✓ SATISFIED | Truth 3 |

No orphaned requirements: REQUIREMENTS.md maps exactly these four IDs to Phase 2. REQUIREMENTS.md checkboxes are still `[ ]` / Pending (bookkeeping for the orchestrator).

### Prohibitions

| Prohibition | Tier | Disposition |
| ----------- | ---- | ----------- |
| No raise/warn on is_public false | test | ✓ enforced (unlisted test; flag never read) |
| No vendored harness or yt_dlp/ | test | ✓ `git ls-files 'test/*' 'yt_dlp/*'` empty; script and runner refuse `yt_dlp/` |
| No signed URLs / downloaded audio committed | test | ✓ hygiene tests; no tracked audio files |
| Original only when is_downloadable True | test | ✓ offline tests + live negative |
| Original never default / ba / -S | test | ✓ offline + live |
| No login/credentials (D-07) | judgment | flagged, human review recommended |
| MeTube untouched | judgment | flagged, human review recommended |
| No bypass option | judgment | flagged, human review recommended |

### Anti-Patterns Found

None. No TBD/FIXME/XXX/TODO/HACK markers in phase files. IN-01..IN-04 from 02-REVIEW remain open (info only: bytecode in repo, .gitignore misses opus/webm/aac, fallback not logged, missing-binary message wording).

### Human Verification Required

1. **Concurrency backstop.** Run two extractions of a downloadable track in parallel and interrupt one `-f original` download, then re-run. Expected: both independent; resume from `.part`. Why human: non-inferable truth, no test.
2. **No login/credentials used (D-07).** Confirm anonymous-only probing. Why human: judgment-tier prohibition.
3. **MeTube untouched.** Confirm the container and `/opt/metube` were not changed. Why human: judgment-tier; container not inspected.
4. **No bypass option.** Confirm nothing exposes an original when downloads are disallowed. Why human: judgment-tier.

### Gaps Summary

No gaps. All four ROADMAP success criteria and all four requirement IDs hold in the current code on both pinned yt-dlp versions, including after WR-01 (original listed only when requested, still offered via `-F` / `-f original`) and WR-05 (401/403 JSON-only mapping, which does not touch the 404/410 path SC2 relies on). Phase 1 behavior is intact. Status is `human_needed` only because of the backstop truth and three judgment-tier prohibitions.

---

_Verified: 2026-10-28T20:05:00Z_
_Verifier: Claude (gsd-verifier)_
