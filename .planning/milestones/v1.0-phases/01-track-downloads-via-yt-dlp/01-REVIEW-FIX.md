---
phase: 01-track-downloads-via-yt-dlp
fixed_at: 2026-10-28T00:00:00Z
review_path: .planning/phases/01-track-downloads-via-yt-dlp/01-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-10-28
**Source review:** .planning/phases/01-track-downloads-via-yt-dlp/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (fix_scope: critical_warning; 0 critical, 7 warning)
- Fixed: 7
- Skipped: 0

## Verification

The full suite was run after every fix in the isolated worktree, using both venvs built with only the approved pins: `.venv` (yt-dlp 2026.10.26, pytest 9.1.1, editable install) and `.venv-metube` (yt-dlp 2026.8.19, pytest 9.1.1, editable install). After the fast-forward to `master`, the suite was run again from the main checkout, with the main checkout's sources first on `sys.path`. Result in both venvs: 126 passed, 6 skipped. The baseline before any fix was 115 passed, 6 skipped. The count is 126 rather than higher because WR-07 merged three per-fixture hygiene tests into one recorder-check test. For WR-03, WR-04 and WR-06, the new tests were also run with the fix temporarily removed to confirm they fail against the old code. The venvs lived inside the worktree and were removed with it.

## Fixed Issues

### WR-01: The `embed/` / `audio/` negative lookahead can be bypassed with different letter case

**Files modified:** `yt_dlp_plugins/extractor/audiocom.py`, `tests/test_url_matching.py`
**Commit:** 0ddfd36
**Applied fix:** Changed the lookahead to `(?!(?i:embed|audio)/)` and added `Embed/audio/...` and `AUDIO/audio/...` to NEGATIVE.

### WR-02: A deleted, private, or mistyped track produces "please report this issue on yt-dlp/yt-dlp"

**Files modified:** `yt_dlp_plugins/extractor/audiocom.py`, `tests/test_extract_offline.py`
**Commit:** 3daa261
**Applied fix:** Added a `_call_api` helper that turns an HTTP 404 into `ExtractorError('Track not found, private, or removed', expected=True)`. Both the oEmbed and `/audio/<id>` requests now go through it. A missing or digit-less `iframe_url` now raises an expected error. New tests cover a 404 on each endpoint, and the existing empty-oEmbed and no-digits tests now assert `expected is True`.

### WR-03: The API `format` string is used as `ext` without validation

**Files modified:** `yt_dlp_plugins/extractor/audiocom.py`, `tests/test_extract_offline.py`
**Commit:** 813fe1b
**Applied fix:** `ext` is now the first value in `KNOWN_EXTENSIONS` out of the lowercased `format` label and then `mimetype2ext(type)`. Unknown labels such as `m4a_hq` therefore fall back to the MIME type and never reach the filename. Two parts of the reviewer's suggestion were left out on purpose. The plan's precedence (format label first, MIME as fallback) is kept, so `format` still wins when it is valid. `format_id` stays equal to `ext`, because 01-01-PLAN and 01-02-PLAN fix `format_id == ext` and the 01-02 verification greps for `AudioCom mp3`. Renaming it to `ext-abr` would contradict that decision and needs a human call.

### WR-04: The track-id regex accepts partial digit runs, and the mismatch guard is skipped for non-string ids

**Files modified:** `yt_dlp_plugins/extractor/audiocom.py`, `tests/test_extract_offline.py`
**Commit:** f098113
**Status:** fixed: requires human verification (logic change in the id guard)
**Applied fix:** The regex is anchored as `/embed/audio/(\d+)(?:[/?#]|$)`. The returned id is normalised with `str_or_none`, and any mismatch now raises, including a missing id. New tests cover an integer mismatching id, a missing id, an integer matching id (accepted), and `/embed/audio/<id>abc`.

### WR-05: The recorder's allowlist projection passes data through when the API changes shape

**Files modified:** `scripts/record_fixture.py`, `tests/test_fixture_hygiene.py`
**Commit:** 932581d
**Applied fix:** Added `_require()`. `project()` now refuses unexpected types for audio, oembed, image, avatar, stats, transcodings, transcoding entries and their URLs, instead of passing them through verbatim. Added `check_record()`, which runs the forbidden-marker scan and refuses any string anywhere in the record (free text included) that contains `://` together with `?` or `#`. `record()` calls it before writing. New tests cover the refused shapes and SAS-style or fragment URLs in the description.

### WR-06: `test_plugin_listed` depends on an undocumented install step and fails with a misleading message

**Files modified:** `tests/test_plugin_loading.py`
**Commit:** 28d4f1e
**Applied fix:** The test now skips when there is no `yt-dlp` or `yt-dlp.exe` next to `sys.executable`, or when the `yt-dlp-audiocom` distribution is not installed. It matches with `re.search(r'Extractor Plugins: .*\bAudioComIE\b', ...)`. The install step is documented in the module docstring. No README was created, because the project has none.

### WR-07: The redaction rules are duplicated between the recorder and the hygiene test

**Files modified:** `scripts/record_fixture.py`, `tests/test_fixture_hygiene.py`
**Commit:** de08d45
**Applied fix:** `scripts/record_fixture.py` is now the single source for the rules. `check_record()` also enforces the key allowlists: exact top-level keys, exact oEmbed keys, and the audio, stats and transcoding subsets. The hygiene test no longer copies the constants or the walker. It calls `check_record()` on every fixture and has mutation tests showing that each rule rejects bad input.

---

_Fixed: 2026-10-28_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
