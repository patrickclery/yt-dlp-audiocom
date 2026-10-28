---
phase: 01-track-downloads-via-yt-dlp
verified: 2026-10-28T11:40:00Z
status: human_needed
score: 15/16 must-haves verified
covered_files:
  - ".gitignore"
  - ".planning/phases/01-track-downloads-via-yt-dlp/01-01-PLAN.md"
  - ".planning/phases/01-track-downloads-via-yt-dlp/01-01-SUMMARY.md"
  - ".planning/phases/01-track-downloads-via-yt-dlp/01-02-PLAN.md"
  - ".planning/phases/01-track-downloads-via-yt-dlp/01-02-SUMMARY.md"
  - "pyproject.toml"
  - "scripts/record_fixture.py"
  - "tests/conftest.py"
  - "tests/fixtures/1782423994666898.json"
  - "tests/fixtures/1795055938670272.json"
  - "tests/fixtures/1861573231849291.json"
  - "tests/fixtures/1877766681285368.json"
  - "tests/fixtures/1880272004207526.json"
  - "tests/fixtures/1880272428195927.json"
  - "tests/fixtures/1880272651234303.json"
  - "tests/fixtures/1880273150344633.json"
  - "tests/test_extract_offline.py"
  - "tests/test_fixture_hygiene.py"
  - "tests/test_metadata_offline.py"
  - "tests/test_plugin_loading.py"
  - "tests/test_url_matching.py"
  - "yt_dlp_plugins/extractor/audiocom.py"
covered_digest: "v3:sha256:58a4501fbea57f120d537d1853f74def2da48c3d7951f908801c2f1986be79a5"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Play /tmp/claude-1000/-home-patrick-github-com-patrickclery-audio-com-downloader/b3b4fecb-6dde-482c-aee9-1603f83e8e2d/scratchpad/verify-dl/new/1877766681285368.m4a (or the mp3 at .../verify-dl/mp3/1877766681285368.mp3) in a media player"
    expected: "Audio plays for about 3:06. Player shows title 'Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best' and artist 'David Oliveira'"
    why_human: "Plan 01-02 queued this check. ffprobe confirms tags and a 186.33 s duration, but whether the audio actually plays and sounds right needs a listener"
  - test: "Confirm the backstop truth: AudioComIE keeps no mutable module- or class-level state and does no file I/O, so parallel or interrupted extractions are independent"
    expected: "Accept based on code reading (audiocom.py has only constant class attributes, no open()/file writes, all state is local to _real_extract), or require a concurrency test"
    why_human: "Tagged verification: backstop. Non-inferable truths need a held-out test or observed behavior, and none exists"
  - test: "Resolve three flagged prohibitions with no wired enforcement test: (a) no upstream yt-dlp source or PR text, (b) no downloaded audio committed, (c) no yt-dlp config written under ~/.config"
    expected: "Verifier observed: no yt_dlp/ tree in the repo; `git ls-files '*.m4a' '*.mp3' '*.part'` and `git log --all -- '*.m4a' '*.mp3'` are empty and .gitignore covers them; ~/.config/yt-dlp does not exist. A human should confirm these, or add tests for (a) and (b)"
    why_human: "(a) and (b) are verification: test but no test enforces them (fail-closed: flagged). (c) is judgment-tier; the verifier's verdict is not authoritative"
---

# Phase 1: Track Downloads via yt-dlp Verification Report

**Phase Goal:** User can run yt-dlp with the repo's plugin on an audio.com track URL and get an mp3 or m4a file with correct metadata, without impersonation.
**Verified:** 2026-10-28T11:40:00Z
**Status:** human_needed
**Re-verification:** No, initial verification

MVP mode note: the ROADMAP goal line is not in user-story form (`user-story.validate` returns false). 01-01-PLAN restates it as "As a yt-dlp user, I want to run yt-dlp with this repo's plugin on an audio.com track URL, so that I get an mp3 or m4a file with correct metadata, without impersonation." That version validates, so verification used it. Run `/gsd-mvp-phase 1` to canonicalize ROADMAP.

## User Flow Coverage

| Step | Expected | Evidence | Status |
| ---- | -------- | -------- | ------ |
| Install the plugin | `yt-dlp -v` lists AudioComIE with no import error | Fresh venvs built with only the approved pins plus `uv pip install -e .`. Both print `Extractor Plugins: AudioComIE` | VERIFIED |
| Pass a track URL | `[AudioCom]` picks it up with no 403 | Live runs on both venvs log `[AudioCom]` oEmbed and track JSON. No `[generic]`, 403 or impersonation lines | VERIFIED |
| Get an mp3 or m4a | Non-empty audio file | 7,169,460-byte m4a from both venvs; `-f mp3` gives an mp3 with codec mp3 | VERIFIED |
| Correct metadata (outcome) | Title, artist and date embedded | ffprobe on both m4a files: title, artist=David Oliveira, date=20260930, duration 186.33 s | VERIFIED |
| Without impersonation | No impersonation used | curl_cffi is not installed in either venv. No `impersonat` in audiocom.py. An offline test asserts no impersonation kwarg on any request | VERIFIED |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | SC1: `yt-dlp -v` lists AudioCom under extractor plugins, no "Error while importing" | VERIFIED | Both venvs, run from cwd=/; `test_plugin_listed` ran (not skipped) and passed |
| 2 | SC2: reference URL plus www., trailing-slash, query and uppercase variants pick `[AudioCom]` and download with no 403 or impersonation. Collection, profile and /embed/ URLs don't match | VERIFIED | All 5 live variants print `AudioCom 1877766681285368`. `suitable()` is False for profile, collections, embed, `Embed/`, audio/audio, lookalike host, api host, deeper path, empty slug and empty user |
| 3 | SC3: `-F` lists mp3 and m4a with correct ext, abr and acodec, no video codec | VERIFIED | Both venvs: `mp3 mp3 audio only ... mp3 192k` and `m4a m4a audio only ... aac 306k` |
| 4 | SC4: title, uploader, uploader_id/url, duration (s), upload date; optional fields only when present; checked against at least 5 redacted fixtures | VERIFIED | Live `--print`: all core fields present, thumbnail NA (the reference has no image or avatar, which is correct). 8 fixtures; `test_metadata_fields`, `test_no_empty_string_values` and 5 mutation tests pass |
| 5 | No `__init__.py` in yt_dlp_plugins/ or extractor/; only absolute yt_dlp imports | VERIFIED | `find` is empty; `test_layout` passes |
| 6 | Uppercase is lowercased before oEmbed; the canonical URL goes only through `query={'url': ...}` | VERIFIED | audiocom.py:55 and :71; `test_requests_are_canonical_without_impersonation` |
| 7 | Fixtures cover mp3-only, mp3 > m4a, empty author_name, an image and a description | VERIFIED | 1782423994666898 is mp3-only; 1861573231849291 has 160k mp3 vs 8.9k m4a; 1880272004207526 has author_name ''; three have images; 1880272651234303 has a description |
| 8 | Fixtures have no query strings or secrets and are allowlisted | VERIFIED | Hygiene tests call `check_record()` on every fixture. A git grep finds no real presign values |
| 9 | One oEmbed and one /audio/<id> request, no impersonation keyword | VERIFIED | `test_requests_are_canonical_without_impersonation` over 8 fixtures |
| 10 | Format fields: ext in {mp3, m4a}, vcodec none, acodec, abr = bit_rate/1000, quality = abr, one format for mp3-only | VERIFIED | `test_formats_mirror_transcodings` and `test_mp3_only_yields_one_format`. WR-03 now limits ext to KNOWN_EXTENSIONS with a MIME fallback; real fixtures are unaffected |
| 11 | The default selection picks the highest abr | VERIFIED | `test_highest_bitrate_selected`; live arthur-hpcp gives `AudioCom mp3 160.0`, and the reference gives m4a 306k |
| 12 | `-F` shows an mp3/mp3 row and an m4a/aac row | VERIFIED | Same as truth 3 |
| 13 | A real download with `--embed-metadata` has the expected title and artist | VERIFIED | ffprobe on m4a files from both venvs and on the mp3 |
| 14 | A malformed oEmbed response or missing transcodings raise ExtractorError, never KeyError or TypeError | VERIFIED | `test_edge_empty_oembed`, `_iframe_url_without_digits`, `_no_transcodings`, `_all_transcoding_urls_null` and `_404_is_expected_error` pass |
| 15 | The track id is a digit string compared as a string; a mismatch raises naming both ids | VERIFIED | audiocom.py:72-81; `test_edge_api_id_mismatch`, `_non_string_mismatch`, `_integer_match_accepted` and `_partial_digit_run` pass. **WR-04 impact:** a missing API id now raises. The live API returns the id as a string that matches, and the live download works on both venvs, so the goal is not broken |
| 16 | No mutable state and no file I/O, so extractions are independent (backstop) | insufficient_spec | Code reading supports it, but a backstop truth cannot be verified from code alone. Routed to human |

**Score:** 15/16 truths verified (0 present but behavior-unverified; 1 insufficient_spec routed to human)

### Prohibitions

| Prohibition | Tier | Disposition | Evidence |
| ----------- | ---- | ----------- | -------- |
| No browser impersonation | test | VERIFIED | Offline test asserts no impersonation kwarg; nothing in the code; curl_cffi absent and the download still works |
| No upstream yt-dlp source or PR text | test | FLAGGED (unverified) | No yt_dlp/ tree found, but no test enforces it |
| No yt-dlp config under ~/.config | judgment | FLAGGED (non-authoritative pass) | ~/.config/yt-dlp does not exist |
| No original-upload formats | test | VERIFIED | `test_formats_mirror_transcodings` asserts format count equals playable transcodings; no `sources` in the code |
| No signed URLs committed | test | VERIFIED | Hygiene tests on fixtures; git grep found no real signatures |
| No downloaded audio committed | test | FLAGGED (unverified) | `git ls-files` and history are empty and .gitignore covers the extensions, but no test enforces it |

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `pyproject.toml` | VERIFIED | hatchling==1.32.4, `packages = ["yt_dlp_plugins"]` |
| `.gitignore` | VERIFIED | venvs, caches, *.m4a, *.mp3, *.part |
| `yt_dlp_plugins/extractor/audiocom.py` | VERIFIED | 139 lines, real oEmbed and API path, used by both venvs |
| `tests/test_plugin_loading.py` | VERIFIED (pattern drift) | `verify.artifacts` reports "Missing pattern: Extractor Plugins: AudioComIE" because WR-06 replaced the literal with the regex `Extractor Plugins: .*\bAudioComIE\b`. The behavior is equivalent and the test passes |
| `tests/test_url_matching.py` | VERIFIED | |
| `scripts/record_fixture.py`, `tests/test_fixture_hygiene.py`, `tests/conftest.py`, `tests/test_extract_offline.py`, `tests/test_metadata_offline.py`, 8 fixtures | VERIFIED | `verify.artifacts` 01-02: 7/7 |

### Key Link Verification

| From | To | Status | Details |
| ---- | -- | ------ | ------- |
| pyproject.toml | audiocom.py | WIRED | The editable install makes yt-dlp report `Plugin directories: .../yt_dlp_plugins` |
| audiocom.py | api.audio.com/oembed | WIRED | `query={'url': canonical}`; live |
| audiocom.py | api.audio.com/audio/<id> | WIRED | Id parsed from `/embed/audio/(\d+)`; live |
| test_plugin_loading.py | venv yt-dlp | WIRED (pattern drift) | The literal `with_name('yt-dlp')` became `with_name(n) for n in ('yt-dlp', 'yt-dlp.exe')` in WR-06 |
| conftest.py, record_fixture.py, FormatSorter, `_TESTS[0]` | | WIRED | `verify.key-links` 01-02: 4/4 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Test suite, new yt-dlp | `.venv/bin/python -m pytest -q` | 126 passed, 6 skipped (mp3-only test on two-format fixtures) | PASS |
| Test suite, MeTube yt-dlp | `.venv-metube/bin/python -m pytest -q` | 126 passed, 6 skipped | PASS |
| Live download plus metadata, both venvs | `yt-dlp -v --embed-metadata <ref>` | exit 0, m4a written, ffprobe tags correct | PASS |
| Second track picks highest bitrate | `yt-dlp --print ... arthur-hpcp/audio/original` | `AudioCom mp3 160.0`, uploader Arthur Hpcp | PASS |

### Probe Execution

Step 7c: no `scripts/*/tests/probe-*.sh` exist and the plans declare none.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| ----------- | ----------- | ------ | -------- |
| EXTR-01 | 01-01 | SATISFIED | Truth 2 |
| EXTR-02 | 01-01, 01-02 | SATISFIED | Truths 6, 9 and 15; plain urllib, no impersonation |
| EXTR-03 | 01-01, 01-02 | SATISFIED | Truths 3, 10 and 11 |
| EXTR-05 | 01-02 | SATISFIED | Truths 4 and 13 |
| PLUG-01 | 01-01 | SATISFIED | Truths 1 and 5 |

No orphaned requirements. REQUIREMENTS.md maps exactly these five IDs to Phase 1.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (all modified files) | | No TBD, FIXME, XXX, TODO, HACK or placeholder markers | | |
| `yt_dlp_plugins/extractor/audiocom.py` | 88-96 | ext and format_id can be None if both the label and the MIME type are unknown (tested as intended in WR-03) | Info | Not reachable with current API data |
| `pyproject.toml` | dev extra | `yt-dlp` has no version pin (review IN-05) | Info | The venvs are pinned explicitly |

### Human Verification Required

1. **Playback (queued by plan 01-02).** Play `/tmp/claude-1000/-home-patrick-github-com-patrickclery-audio-com-downloader/b3b4fecb-6dde-482c-aee9-1603f83e8e2d/scratchpad/verify-dl/new/1877766681285368.m4a`. Expected: about 3:06 of audio, title "Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best", artist "David Oliveira". Why human: ffprobe can show the tags but cannot tell whether it plays correctly.
2. **Backstop truth 16.** Accept "no mutable state, no file I/O" from code reading, or ask for a test.
3. **Flagged prohibitions.** Confirm (a) no upstream yt-dlp source or PR text, (b) no committed audio, (c) no ~/.config writes. The verifier observed all three as clean, but (a) and (b) have no enforcing test and (c) is judgment-tier.

### Gaps Summary

No blocking gaps. The current post-review code achieves the goal on both target yt-dlp versions. A live download through plain HTTP with only the approved pins produces correctly tagged m4a and mp3 files. The WR-04 id-guard change does not affect the real API path. The remaining items need human sign-off (playback, one backstop truth, three flagged prohibitions). The two artifact-tool mismatches come from literal patterns in the plan that WR-06 reworded; they are not real gaps.

---

_Verified: 2026-10-28T11:40:00Z_
_Verifier: Claude (gsd-verifier)_
