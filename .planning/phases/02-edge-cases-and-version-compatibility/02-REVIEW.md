---
phase: 02-edge-cases-and-version-compatibility
reviewed: 2026-10-28T13:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - yt_dlp_plugins/extractor/audiocom.py
  - scripts/test-live.sh
  - scripts/run_live_tests.py
  - scripts/record_fixture.py
  - README.md
  - .gitignore
  - tests/conftest.py
  - tests/test_extract_offline.py
  - tests/test_fixture_hygiene.py
  - tests/test_metadata_offline.py
  - tests/test_sources_offline.py
findings:
  critical: 0
  warning: 6
  info: 4
  total: 10
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-10-28T13:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

I reviewed the changes since `133bd56`: one-line 404/410/401/403 errors, newest-upload transcoding selection, opt-in `-f original` with the 1-byte probe and the wv skip, the live-test script, and the extensions to the fixture recorder and hygiene checks. The offline suite passes on both venvs (274 passed, 43 skipped). Several requirements hold up. `is_public` is never read, so an unlisted track cannot raise. A track that is not downloadable never touches its source URL. The default sort, `-f ba` and `-S` never pick `original`, which I checked against the fixtures.

I found no blockers. The weak spots:
- The "opt-in only" promise for `original` is broken by worst-quality selectors.
- The probe's skip line can print a signed URL when yt-dlp uses the requests handler, which MeTube has installed.
- `test-live.sh` prints unredacted output right after the redacted copy.
- The harness "clean checkout" check ignores gitignored files such as `test/local_parameters.json`.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Worst-quality selectors pick the uploader's original, so it is not opt-in only

**File:** `yt_dlp_plugins/extractor/audiocom.py:177-179`, `README.md:95-96`
**Issue:** `preference: -10` puts `original` at the bottom of the sort. That is exactly where `-f worst`, `-f wa` and `-f worstaudio` look. I checked this against the fixtures: on every downloadable fixture (1880272416485027, 1880272945380630, 1880272428195927), `{'format': 'worst'}` and `{'format': 'worstaudio'}` both select `original`. Format filters such as `ba[ext=wav]` also select it on andrea-mathiopoulos. The result is usually the largest file (for example, a PCM wav), and it is chosen by a selector that means "smallest". This contradicts the README ("It is opt-in only") and the comment on line 177. The only part tested is the `best` side (`test_original_never_selected_by_default_or_ranking`).
**Fix:** List the original only on explicit request, for example behind an extractor-arg:
```python
if (data.get('is_downloadable') is True
        and self._configuration_arg('original', ['no'])[0] == 'yes'
        and url_or_none(traverse_obj(current, 'url'))):
```
Usage would be `--extractor-args "audiocom:original=yes" -f original`. Alternatively, keep the current design but document that worst selectors pick it. In either case, add `worst` and `wa` to the parametrize list in `tests/test_sources_offline.py:111`.

### WR-02: The probe's skip line can print the signed source URL

**File:** `yt_dlp_plugins/extractor/audiocom.py:167`
**Issue:** `_is_valid_url` catches the probe's `ExtractorError` and prints `f'{video_id}: {item} URL is invalid, skipping: {e.cause!s}'`. For an `HTTPError`, that text is only `HTTP Error 404: Not Found`, which is the only case `test_mutation_probe_failure_drops_original` covers. A connection failure is different.
- Under the `requests` handler (installed in MeTube through `yt-dlp[default]`), `TransportError(cause=e)` takes `str(cause)` as its message (`networking/exceptions.py:20-21`).
- urllib3's `MaxRetryError` text is `HTTPSConnectionPool(host='s3.ustatik.com', ...): Max retries exceeded with url: /audio.com.audio/source/...?X-Amz-...&X-Amz-Signature=...`.

So a DNS failure, connection reset or Cloudflare TCP drop writes the presigned URL into MeTube's logs at normal verbosity. That breaks T-02-11 ("only the HTTP status, never the URL"). The dev venvs have no `requests`, so this path is never exercised.
**Fix:** Do the probe inline and print only the status or the exception type:
```python
try:
    urlh = self._request_webpage(current['url'], track_id, 'Checking original upload URL',
                                 headers={'Range': 'bytes=0-0'})
    urlh.close()
except ExtractorError as e:
    reason = e.cause.status if isinstance(e.cause, HTTPError) else type(e.cause).__name__
    self.to_screen(f'{track_id}: original upload unavailable, skipping ({reason})')
else:
    formats.append({...})
```
Also add a conftest probe mode that raises `TransportError('... with url: /x?X-Amz-Signature=abc')`, and assert that the printed line contains neither `X-Amz` nor `/x`.

### WR-03: test-live.sh step 9 prints unredacted output right after the redacted copy

**File:** `scripts/test-live.sh:170-171`
**Issue:** Line 170 prints `$out` through `redact`. Line 171 then interpolates the same `$out` raw into the FAIL message (`format ids: $out`), which cancels the redaction on every failure of this step. `$out` holds combined stdout and stderr, including any yt-dlp error or warning text. The header (line 22-23) promises the output never contains media URLs. Separately, `redact()` (line 48-50) only matches URLs that start with `https?://`. urllib3 errors print the scheme-less form `with url: /path?X-Amz-...`, which passes through unredacted in steps 4, 6, 7 and 8.
**Fix:**
```bash
echo "FAIL: non-downloadable track (yt-dlp exit $rc; need mp3 and no original)"; fail=1
```
Also widen `redact` to strip any query string, not only those on absolute URLs:
```bash
redact() { sed -E 's#(/[^[:space:]?]*)\?[^[:space:]]*#\1?<redacted>#g'; }
```

### WR-04: The harness "clean checkout" check ignores gitignored files, including test/local_parameters.json

**File:** `scripts/test-live.sh:72-74`
**Issue:** `git status --porcelain` leaves out ignored files. yt-dlp's `.gitignore`, which is in the sparse cone because root files are always included, ignores `*.pyc` and `test/local_parameters.json`. `test/helper.py:25` loads `test/local_parameters.json` and merges it into the harness parameters. A stray or planted file there can change what `_TESTS` checks, for example with `skip_download` or a different `format`, and still pass the "exactly the pinned tag commit, no modified or extra files" gate described in README line 50-52. Step 6 already writes `test/__pycache__/` into the cached harness, and `git status --porcelain --ignored` on the 2026.10.26 cache shows `!! test/__pycache__/`. Stale bytecode is therefore reused across runs without any check.
**Fix:** Include ignored files in the check, and stop writing bytecode into the harness:
```bash
status=$(git -C "$dir" status --porcelain --ignored 2>/dev/null || echo 'status failed')
...
out=$(cd "$work" && PYTHONDONTWRITEBYTECODE=1 "$py" "$ROOT/scripts/run_live_tests.py" "$dir" AudioCom 2>&1) ...
```
Delete the existing `test/__pycache__` in each cached harness once.

### WR-05: Every 401/403 is reported as "private or restricted" with expected=True

**File:** `yt_dlp_plugins/extractor/audiocom.py:100-102`
**Issue:** The comment admits a 401/403 has never been seen anonymously. The project's own STACK research documents Cloudflare 403s on audio.com for non-browser clients. A WAF challenge, bot block or regional block from `api.audio.com` would be shown as "This audio.com track is private or restricted". Because the error is `expected=True`, the "report this issue" hint is suppressed and the `(caused by HTTPError)` text is dropped. A site-wide breakage would then look like a user-side problem on every URL, and nothing would be reported.
**Fix:** Map a 403 only when it is not an anti-bot response, and otherwise re-raise yt-dlp's own error:
```python
if e.cause.status in (401, 403):
    resp = e.cause.response
    if resp.headers.get('cf-mitigated') or 'cloudflare' in (resp.headers.get('server') or '').lower():
        raise
    raise ExtractorError('This audio.com track is private or restricted', video_id=video_id, expected=True)
```

### WR-06: The original-upload probe runs on every extraction, including default downloads

**File:** `yt_dlp_plugins/extractor/audiocom.py:160-167`
**Issue:** For every track flagged downloadable, each extraction makes an extra S3 GET. This includes the default download in MeTube, `-F`, `--simulate`, and the fixture recorder. Users who never asked for `original` see a `Checking original upload URL` line. When the S3 object is missing, they also see `original upload URL is invalid, skipping: HTTP Error 404` on every normal download of that track (arthur-hpcp, per the ORIGINAL table). If the probe fails for a transient reason, `original` is silently dropped, and an explicit `-f original` then fails with the misleading `Requested format is not available`.
**Fix:** Run the probe only when the original was requested (see WR-01's extractor-arg). Alternatively, skip the probe and let a missing object fail at download time with a real HTTP error, which is more accurate for the one user who asked for it.

## Info

### IN-01: The live script writes plugin bytecode into the repo

**File:** `scripts/test-live.sh:105-106, 116-166`; `README.md:42-43`
**Issue:** Only step 4 sets `PYTHONDONTWRITEBYTECODE=1`. Steps 5-9 import the plugin through the editable install, which writes `yt_dlp_plugins/extractor/__pycache__/` into the repo (present now). That contradicts "writes nothing inside the repo". It is gitignored, so it does no harm.
**Fix:** Add `export PYTHONDONTWRITEBYTECODE=1` after `set -euo pipefail`.

### IN-02: .gitignore misses other extensions that -f original can write

**File:** `.gitignore:10-14`
**Issue:** `_known_ext` accepts any extension in `KNOWN_EXTENSIONS` reached through `mimetype2ext`, so `audio/opus`, `audio/webm`, `audio/aac` and `audio/aiff` give `opus`, `webm`, `aac` and `aiff`. Only `wav`, `flac`, `aiff` and `ogg` are ignored. Downloading such an original in the repo leaves an untracked media file that is easy to commit.
**Fix:** Add `*.opus`, `*.webm`, `*.aac`, `*.aif`, `*.alac`, `*.ytdl` and `*.temp`.

### IN-03: The fallback path mixes upload versions

**File:** `yt_dlp_plugins/extractor/audiocom.py:129-131, 160, 206-208`
**Issue:** When no transcoding's `source_id` matches the newest source, every version's transcodings are kept. `duration` then comes from `transcodings[0]`, which may be the old version's, while `original` still comes from the newest source. Two transcodings with the same extension also produce `mp3-0`/`mp3-1` ids. The behavior is intended, but nothing logs it.
**Fix:** In the fallback branch, call `self.write_debug('No transcoding matches the newest upload; listing all versions')`.

### IN-04: Misleading failure message when the yt-dlp binary is missing

**File:** `scripts/test-live.sh:90-91`
**Issue:** The check covers both `$py` and `$ytdlp`, but the message always says "has no python".
**Fix:** `echo "FAIL: $venv has no python or yt-dlp executable"`.

---

_Reviewed: 2026-10-28T13:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
