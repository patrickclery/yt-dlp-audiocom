---
phase: 01-track-downloads-via-yt-dlp
verified: 2026-10-28T20:07:36Z
status: passed
score: 16/16 must-haves verified
covered_files:
  - ".gitignore"
  - ".planning/phases/01-track-downloads-via-yt-dlp/01-01-PLAN.md"
  - ".planning/phases/01-track-downloads-via-yt-dlp/01-01-SUMMARY.md"
  - ".planning/phases/01-track-downloads-via-yt-dlp/01-02-PLAN.md"
  - ".planning/phases/01-track-downloads-via-yt-dlp/01-02-SUMMARY.md"
  - "pyproject.toml"
  - "scripts/record_fixture.py"
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
  - "tests/test_plugin_loading.py"
  - "tests/test_sources_offline.py"
  - "tests/test_url_matching.py"
  - "yt_dlp_plugins/extractor/audiocom.py"
covered_digest: "v3:sha256:380af7805dec2a60940b174bd327fac59374ffe8ec54767770b0a19f7fa62335"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 15/16
  reason: "Covered files changed in Phases 2 and 3; fingerprint stale"
  gaps_closed:
    - "Backstop truth 16 (no mutable state / file I/O) and the three flagged prohibitions were signed off in 01-UAT.md (status complete, 3/3 pass)"
  gaps_remaining: []
  regressions: []
---

# Phase 1: Track Downloads via yt-dlp Verification Report

**Phase Goal:** User can run yt-dlp with the repo's plugin on an audio.com track URL and get an mp3 or m4a file with correct metadata, without impersonation.
**Verified:** 2026-10-28T20:07:36Z
**Status:** passed
**Re-verification:** Yes. The previous report was stale because Phases 2 and 3 changed covered files. This run checks the current code.

Phase 2 changed some behavior on purpose: only the newest upload's transcodings are kept, errors are one line, and `-f original` is opt-in behind `is_downloadable`. None of these is counted as a Phase 1 regression. The Phase 1 prohibition "no original-upload formats" is superseded by EXTR-04. Even so, with the current code a plain download and `-F` on the reference track still list only the mp3 and m4a transcodings.

## User Flow Coverage

| Step | Expected | Evidence (this run) | Status |
| ---- | -------- | ------------------- | ------ |
| Install the plugin | `yt-dlp -v` lists AudioComIE | Both venvs, run from cwd=/, print `Extractor Plugins: AudioComIE`. No import error | VERIFIED |
| Pass a track URL | `[AudioCom]` is used, no 403 | Live `-v` logs on both venvs show `[AudioCom]` oEmbed and track JSON, with 0 lines matching `[generic]`, `403` or `impersonat` | VERIFIED |
| Get mp3 or m4a | Non-empty audio file | 7,169,460-byte m4a on 2026.10.26 and on 2026.08.19. `-f mp3` gives codec mp3 | VERIFIED |
| Correct metadata | Title, artist and date embedded | ffprobe on both m4a files shows title, artist=David Oliveira, date=20260930, 186.33 s. The mp3 has the same title and artist | VERIFIED |
| Without impersonation | No impersonation used | `curl_cffi` is not importable in either venv. There is no `impersonat` in audiocom.py. `test_requests_are_canonical_without_impersonation` passes | VERIFIED |

## Observable Truths

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | SC1: `yt-dlp -v` lists AudioCom, no "Error while importing" | VERIFIED | Both venvs. `test_plugin_listed` PASSED (not skipped) |
| 2 | SC2: reference URL and its www., trailing-slash, query and uppercase variants use `[AudioCom]` and download without 403 or impersonation. Collection, profile and embed URLs are rejected | VERIFIED | 4 live variants print `AudioCom 1877766681285368`. `suitable()` is False for profile, collections, embed, Embed, audio/audio, a lookalike host, the api host, a deeper path, an empty slug and an empty user |
| 3 | SC3: `-F` lists mp3 and m4a with correct ext, abr and acodec, no vcodec | VERIFIED | `mp3 mp3 audio only ... mp3 192k` and `m4a m4a audio only ... aac 306k`. No original row |
| 4 | SC4: core metadata is present; optional fields appear only when present; at least 5 redacted fixtures | VERIFIED | Live `--print` gives all core fields, and thumbnail is NA as expected. There are 12 fixtures. `test_metadata_fields`, `test_no_empty_string_values` and the mutation tests pass |
| 5 | No `__init__.py`; only absolute yt_dlp imports | VERIFIED | `find` is empty, there are no relative imports, and `test_layout` passes |
| 6 | Lowercased canonical URL is sent only through `query={'url': ...}` | VERIFIED | audiocom.py:74-76 and :144. `test_canonical_url_sent_to_oembed` passes |
| 7 | Fixtures cover mp3-only, mp3 > m4a, empty author_name, an image and a description | VERIFIED | `test_shape_coverage` and `test_fixture_count` pass |
| 8 | Fixtures have no query strings or secrets and are allowlisted | VERIFIED | `test_passes_recorder_check` runs on every fixture. `git grep` finds only test literals and the forbidden-marker list |
| 9 | One oEmbed and one /audio/<id> request, with no impersonation kwarg | VERIFIED | `test_requests_are_canonical_without_impersonation` |
| 10 | Format fields: ext in {mp3, m4a}, vcodec none, abr = bit_rate/1000, quality = abr, and one format for mp3-only | VERIFIED | audiocom.py:168-187. `test_formats_mirror_transcodings` and `test_mp3_only_yields_one_format` pass. The filter to the newest upload (Phase 2) is intended |
| 11 | Default selection takes the highest abr | VERIFIED | `test_highest_bitrate_selected`. Live arthur-hpcp gives `AudioCom mp3 160.0` |
| 12 | `-F` shows an mp3/mp3 row and an m4a/aac row | VERIFIED | Same as truth 3 |
| 13 | A real `--embed-metadata` download has the expected title and artist | VERIFIED | ffprobe on files from both venvs and on the mp3 |
| 14 | A malformed oEmbed response or missing transcodings raise ExtractorError, never KeyError or TypeError | VERIFIED | `test_edge_*` pass. Errors are now one line (Phase 2) |
| 15 | The id is compared as a string; a mismatch names both ids | VERIFIED | audiocom.py:151-154. `test_edge_api_id_*` pass |
| 16 | No mutable state and no file I/O (backstop) | VERIFIED (human sign-off) | Code reading still holds: there are only constant class attributes, no `open()`, and all state is local. Accepted in 01-UAT.md test 2 |

**Score:** 16/16 (0 present but behavior-unverified)

## Prohibitions

| Prohibition | Disposition | Evidence |
| ----------- | ----------- | -------- |
| No browser impersonation | VERIFIED | Offline test, no matches in the code, curl_cffi absent, and the live download works |
| No upstream yt-dlp source or PR text | VERIFIED (human sign-off) | No `yt_dlp/` tree. Accepted in 01-UAT.md test 3 |
| No yt-dlp config under ~/.config | VERIFIED (human sign-off) | `~/.config/yt-dlp` does not exist. Accepted in 01-UAT.md test 3 |
| No original-upload formats in Phase 1 | SUPERSEDED by Phase 2 (EXTR-04) | The original is now gated on `is_downloadable is True` plus an explicit `-f original` request. The reference `-F` lists no original |
| No signed URLs committed | VERIFIED | Hygiene tests pass and `git grep` is clean |
| No downloaded audio committed | VERIFIED (human sign-off) | `git ls-files '*.m4a' '*.mp3' '*.part'` and the git history are empty. .gitignore covers the media extensions. Accepted in 01-UAT.md test 3 |

## Artifacts and Key Links

`verify.artifacts`: 01-01 is 4/5 and 01-02 is 7/7. `verify.key-links`: 01-01 is 3/4 and 01-02 is 3/4. All three misses are pattern drift from later refactors, not missing behavior:

- `tests/test_plugin_loading.py`: the literal `Extractor Plugins: AudioComIE` became the regex `Extractor Plugins: .*\bAudioComIE\b`, and `with_name('yt-dlp')` became a loop over `yt-dlp` and `yt-dlp.exe`. `test_plugin_listed` passes.
- `tests/test_metadata_offline.py`: `_TESTS[0]` became `DOWNLOADABLE_TESTS`, a parametrized list of all non-only_matching entries, after Phase 2 added a second live test. `test_tests_info_dict_matches_offline_fixture` passes for both entries.

## Behavioral Spot-Checks

| Behavior | Result | Status |
| -------- | ------ | ------ |
| `.venv/bin/python -m pytest -q` (2026.10.26) | 384 passed, 120 skipped (fixture-conditional parametrizations) | PASS |
| `.venv-metube/bin/python -m pytest -q` (2026.08.19) | 384 passed, 120 skipped | PASS |
| Live `-v --embed-metadata` on the reference, both venvs | exit 0, m4a written, tags correct | PASS |
| Live `-f mp3 --embed-metadata` | mp3 codec, tags correct | PASS |
| Live arthur-hpcp default selection | `mp3 160.0` | PASS |

Downloads were written to `/tmp/claude-1000/-home-patrick-github-com-patrickclery-audio-com-downloader/b3b4fecb-6dde-482c-aee9-1603f83e8e2d/scratchpad/reverify1/`.

Probe execution: no `scripts/*/tests/probe-*.sh` files exist, and none are declared.

## Requirements Coverage

| Requirement | Status | Evidence |
| ----------- | ------ | -------- |
| EXTR-01 | SATISFIED | Truth 2 |
| EXTR-02 | SATISFIED | Truths 6, 9 and 15 |
| EXTR-03 | SATISFIED | Truths 3, 10 and 11 |
| EXTR-05 | SATISFIED | Truths 4 and 13 |
| PLUG-01 | SATISFIED | Truths 1 and 5 |

No orphaned requirements.

## Anti-Patterns

There are no TBD, FIXME, XXX, TODO or HACK markers in audiocom.py. Info only: `pyproject.toml` leaves `yt-dlp` unpinned in the dev extra, while the venvs are pinned.

## Human Verification

None outstanding. All three earlier items (playback, the backstop truth, and the flagged prohibitions) were signed off in `01-UAT.md` (status complete, 3/3 pass).

## Gaps Summary

There are no gaps. The current code still meets the Phase 1 goal on both target yt-dlp versions.

---

_Verified: 2026-10-28T20:07:36Z_
_Verifier: Claude (gsd-verifier)_
