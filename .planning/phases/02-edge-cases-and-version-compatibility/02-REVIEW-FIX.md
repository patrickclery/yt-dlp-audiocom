---
phase: 02-edge-cases-and-version-compatibility
fixed_at: 2026-10-28T19:40:00Z
review_path: .planning/phases/02-edge-cases-and-version-compatibility/02-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-10-28T19:40:00Z
**Source review:** .planning/phases/02-edge-cases-and-version-compatibility/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (Critical + Warning; IN-01..IN-04 out of scope)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### WR-01: Worst-quality selectors pick the uploader's original, so it is not opt-in only

**Files modified:** `yt_dlp_plugins/extractor/audiocom.py`, `tests/test_sources_offline.py`, `README.md`, `scripts/test-live.sh`
**Commit:** 130d312
**Status:** fixed: requires human verification (logic change)
**Applied fix:** I added `_original_requested()`. The original is now listed only when the `-f` spec names `original` as a whole token (`original`, `original/ba`, `ba/original`, `[format_id=original]`), for `-F` (`listformats`), or for interactive `-f -`. Upstream pluralsight narrows its formats on `-f`/`-F` the same way. Plain `-f original` still works, and no extractor-arg is needed. I rejected two alternatives: the extractor-arg breaks plain `-f original`, and `acodec: 'none'` misstates the codec while `-f all` still picks the format. `preference: -10` stays for the cases where the original is listed. Tests now cover worst, w, wa, worstaudio, w*, `ba[ext=wav]` and wav. They also cover ranking once the original is listed, `-F` listing, and the token matcher, including callable selectors. Live step 9 now passes `-f original/ba`, so the is_downloadable gate is actually exercised. Checked live on both versions with alec-murray: `-f original` gives original, and worst/wa give mp3.

### WR-02: The probe's skip line can print the signed source URL

**Files modified:** `yt_dlp_plugins/extractor/audiocom.py`, `tests/conftest.py`, `tests/test_sources_offline.py`
**Commit:** dcecbd5
**Applied fix:** The probe now runs inline in `_probe_original()` instead of `_is_valid_url`. It sends the same Range 0-0 GET and closes the response. On failure it prints `str(HTTPError)` (status and reason only) or the cause's type name. The skip line keeps its wording, so the README text still holds. I added a conftest `probe.transport_error` mode and a test that a urllib3-style `with url: /x?X-Amz-Signature=abc` message leaks nothing.

### WR-03: test-live.sh step 9 prints unredacted output right after the redacted copy

**Files modified:** `scripts/test-live.sh`
**Commit:** 070cedd
**Applied fix:** I removed `$out` from the step 9 FAIL line. `redact()` now also strips the query string after any bare `/path?`. I checked it on a scheme-less urllib3 line and on an absolute URL.

### WR-04: The harness "clean checkout" check ignores gitignored files

**Files modified:** `scripts/test-live.sh`, `README.md`
**Commit:** bc9866e
**Applied fix:** The check now runs `git status --porcelain --ignored`, and step 6 runs with `PYTHONDONTWRITEBYTECODE=1`. I deleted the stale `test/__pycache__/` once from both cached harnesses (`~/.cache/yt-dlp-audiocom/harness/{2026.08.19,2026.10.26}`). Both are clean after the live run.

### WR-05: Every 401/403 is reported as "private or restricted" with expected=True

**Files modified:** `yt_dlp_plugins/extractor/audiocom.py`, `tests/test_extract_offline.py`, `README.md`
**Commit:** 2ed61d9
**Status:** fixed: requires human verification (logic change)
**Applied fix:** 401/403 maps to the expected "private or restricted" error only when the response is an API JSON answer: `Content-Type` contains `json` and there is no `cf-mitigated` header. The check is `_is_api_answer`. HTML block pages, challenges and responses with no content type re-raise yt-dlp's own HTTP error. I did not use `Server: cloudflare` as a signal, because api.audio.com is likely fronted by Cloudflare, which would make the mapping dead code. New parametrized tests cover html, challenge, json+cf-mitigated and no-type, on both endpoints, for both statuses.

### WR-06: The original-upload probe runs on every extraction, including default downloads

**Files modified:** `tests/test_sources_offline.py`, `README.md`
**Commit:** 71abe7c (the behavior change landed in 130d312, WR-01)
**Applied fix:** WR-01's gate means the S3 probe now runs only when the original is requested. This commit adds a regression test: with an unreachable probe, a default extraction of every fixture makes no probe request and prints no "original upload" line. It also documents in the README that a plain download makes no extra request. If `-f original` hits a transient probe failure, the user now sees the skip line just before "Requested format is not available", and only because they asked for the original.

## Verification

All gates ran in the **main checkout** (`/home/patrick/github.com/patrickclery/audio-com-downloader`) after the fast-forward to 71abe7c, so they can be reproduced from that tree. During fixing, I ran the per-fix suites in the isolated worktree with the main venvs; pytest's `pythonpath=["."]` loaded the worktree copy, which I confirmed by module path.

- Offline suite, `.venv` (yt-dlp 2026.10.26): 384 passed, 120 skipped
- Offline suite, `.venv-metube` (yt-dlp 2026.08.19): 384 passed, 120 skipped
- `scripts/test-live.sh`: ALL TARGETS PASSED (both targets: harness clean, _TESTS 3 passed, real download, one-line missing error, non-downloadable lists no original)
- I installed nothing. The existing venvs already had the approved pins.

---

_Fixed: 2026-10-28T19:40:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
