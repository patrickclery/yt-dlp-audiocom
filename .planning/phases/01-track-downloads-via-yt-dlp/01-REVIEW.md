---
phase: 01-track-downloads-via-yt-dlp
reviewed: 2026-10-28T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - yt_dlp_plugins/extractor/audiocom.py
  - scripts/record_fixture.py
  - pyproject.toml
  - .gitignore
  - tests/conftest.py
  - tests/test_extract_offline.py
  - tests/test_fixture_hygiene.py
  - tests/test_metadata_offline.py
  - tests/test_plugin_loading.py
  - tests/test_url_matching.py
findings:
  critical: 0
  warning: 7
  info: 6
  total: 13
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-10-28
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

I reviewed the audio.com extractor plugin, the fixture recorder, and the offline test suite. I checked behaviour against yt-dlp 2026.10.26 in a scratch venv. In that venv 114 tests pass and `test_plugin_listed` fails because the plugin is not installed there (see WR-06). The 8 committed fixtures are clean: no query strings, no signed-URL markers, and only allowlisted keys.

I found no blockers. The main risks are:
- The URL guard can be bypassed by changing letter case.
- Errors that users can expect (a deleted or private track) are reported as yt-dlp bugs.
- The `format` value from the API goes straight into `ext` without validation.
- The recorder's allowlist projection lets data through unfiltered when the API changes shape. A narrow marker scan is then the only remaining check.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: The `embed/` / `audio/` negative lookahead can be bypassed with different letter case

**File:** `yt_dlp_plugins/extractor/audiocom.py:16`
**Issue:** The plugin deliberately accepts uppercase user segments (`David-Oliveira-...`), and `_canonical_url` lowercases them. The lookahead `(?!embed/|audio/)`, however, is case-sensitive. I confirmed that `AudioComIE.suitable('https://audio.com/Embed/audio/123')` and `.suitable('https://audio.com/AUDIO/audio/123')` both return `True`. The extractor then sends `https://audio.com/embed/audio/123` to oEmbed. The invariant stated in the comment on line 15 therefore does not hold. The NEGATIVE list in `tests/test_url_matching.py:21-32` only covers lowercase.
**Fix:**
```python
_VALID_URL = r'https?://(?:www\.)?audio\.com/(?!(?i:embed|audio)/)(?P<user>[^/?#]+)/audio/(?P<slug>[^/?#]+)/?(?:[?#]|$)'
```
Also add `https://audio.com/Embed/audio/1877766681285368` and `https://audio.com/AUDIO/audio/1877766681285368` to NEGATIVE.

### WR-02: A deleted, private, or mistyped track produces "please report this issue on yt-dlp/yt-dlp"

**File:** `yt_dlp_plugins/extractor/audiocom.py:51-55`
**Issue:** If oEmbed returns 404, `_download_json` raises a non-`expected` `ExtractorError`. yt-dlp then adds its bug-report message pointing at the upstream yt-dlp tracker. Two other paths produce the same message: a missing `iframe_url` (`RegexNotFoundError`) and a 404 on `/audio/<id>`. I reproduced the upstream-tracker text through the id-mismatch path. These are ordinary user situations, and since this is an out-of-tree plugin, the message sends reports to the wrong project.
**Fix:**
```python
from yt_dlp.networking.exceptions import HTTPError
try:
    oembed = self._download_json(f'{self._API_BASE}/oembed', slug, 'Downloading oEmbed JSON',
                                 query={'url': canonical})
except ExtractorError as e:
    if isinstance(e.cause, HTTPError) and e.cause.status == 404:
        raise ExtractorError('Track not found, private, or removed', expected=True)
    raise
track_id = self._search_regex(r'/embed/audio/(\d+)(?:[/?#]|$)',
    traverse_obj(oembed, ('iframe_url', {str})) or '', 'track id', fatal=False)
if not track_id:
    raise ExtractorError('oEmbed returned no embed URL for this track', expected=True)
```

### WR-03: The API `format` string is used as `ext` without validation

**File:** `yt_dlp_plugins/extractor/audiocom.py:62-67`
**Issue:** `ext` comes from the API's `format` field and is also used as `format_id`. `mimetype2ext` is only consulted when `format` is missing. I probed this: a transcoding with `format: 'm4a_hq'` makes it through `process_ie_result` as `ext='m4a_hq'`. The failure only appears at download time, when yt-dlp's `_UnsafeExtensionError` rejects the filename. Any new or unusual label from audio.com (`aac`, `mp4a`, `hls`, ...) would therefore break the download late with an unclear error, and `-f m4a` would not match it either. When both `format` and `type` are missing, `ext` and `format_id` become `None`, which leaves URL sniffing to yt-dlp.
**Fix:** Prefer the MIME type and accept `format` only if it is a known audio extension:
```python
from yt_dlp.utils import KNOWN_EXTENSIONS
fmt = traverse_obj(t, ('format', {str}, {str.lower}))
ext = mimetype2ext(traverse_obj(t, ('type', {str}))) or (fmt if fmt in KNOWN_EXTENSIONS else None)
```
Then set `format_id` to `join_nonempty(ext, int_or_none(abr))` so that two transcodings with the same extension get stable IDs instead of yt-dlp's `mp3-0`/`mp3-1`.

### WR-04: The track-id regex accepts partial digit runs, and the mismatch guard is skipped for non-string ids

**File:** `yt_dlp_plugins/extractor/audiocom.py:53-58`
**Issue:** `r'/embed/audio/(\d+)'` captures `123` from `/embed/audio/123abc`, so a different track id gets requested. Line 56 is the guard that catches this, but `('id', {str})` returns `None` for an integer `id`, which disables the check. I confirmed that `audio['id'] = 999` against an expected `1877766681285368` is accepted without error, and the extractor returns metadata for the wrong track.
**Fix:** Anchor the regex (`r'/embed/audio/(\d+)(?:[/?#]|$)'`) and compare normalised values:
```python
returned_id = traverse_obj(data, ('id', {str_or_none}))
if returned_id is None or returned_id != track_id:
    raise ExtractorError(f'API returned track {returned_id}, expected {track_id}')
```
Use `str_or_none` from `yt_dlp.utils`. Add a test where the API returns an integer id that does not match.

### WR-05: The recorder's allowlist projection passes data through when the API changes shape, which can leak signed URLs

**File:** `scripts/record_fixture.py:44-53`
**Issue:** Each field is filtered only if it has the expected type:
- If `stats` is not a dict, it is written verbatim.
- If `transcodings` is not a list (for example a dict keyed by format), it is written verbatim, signed `url`s included.
- If `image` or `avatar` is a dict or list (for example `{"url": ..., "sizes": ...}`), `strip_url` returns it unchanged.

The only remaining check is then the substring scan on line 82. That scan misses common presign schemes such as Azure SAS (`sig=`, `se=`, `sp=`) and generic `?key=`/`?expires=` parameters. On top of that, free-text fields (`description`, `title`, `tags`) are never URL-stripped, and the recorder does not run the query-string check that `tests/test_fixture_hygiene.py:45-48` does. The recorder can therefore write a fixture that the hygiene test later rejects, or one that leaks a query the markers do not cover.
**Fix:** Fail closed on unexpected types, and apply the hygiene rules before writing:
```python
def _require(value, typ, name):
    if value is not None and not isinstance(value, typ):
        raise RefusedError(f'unexpected type for {name}')
    return value
...
for s in _strings(rec):            # same walker as the hygiene test
    if '://' in s and ('?' in s or '#' in s):
        raise RefusedError('URL with query or fragment')
```

### WR-06: `test_plugin_listed` depends on an undocumented install step and fails with a misleading message

**File:** `tests/test_plugin_loading.py:20-31`
**Issue:** The test assumes three things:
1. A `yt-dlp` console script sits next to `sys.executable`. Otherwise it raises `FileNotFoundError`, for example under pipx, system Python, or Windows where the file is `yt-dlp.exe`.
2. The project is installed into that environment, since `PYTHONPATH` is removed and `cwd='/'`.
3. `AudioComIE` is the first or only entry on the `Extractor Plugins:` line. yt-dlp sorts and joins the names, so a plugin that sorts earlier (`Abc...IE`) or an override display entry breaks the substring match.

In a fresh venv with `pip install yt-dlp pytest` this test fails with an AssertionError (reproduced), which looks like a plugin defect.
**Fix:** `pytest.skip` when the binary is missing or `importlib.metadata.distribution('yt-dlp-audiocom')` raises `PackageNotFoundError`. Match with `re.search(r'Extractor Plugins: .*\bAudioComIE\b', proc.stdout)`. Also document `pip install -e .[dev]` as the setup step.

### WR-07: The redaction rules are duplicated between the recorder and the hygiene test

**File:** `scripts/record_fixture.py:22-28`, `tests/test_fixture_hygiene.py:10-15`
**Issue:** `FORBIDDEN_MARKERS`, `AUDIO_KEYS`, `STATS_KEYS` and `TRANSCODING_KEYS` are copied by hand into both files. If a new key is allowlisted in only one of them, or a marker is added in only one, the recorder and the test drift apart without any error. That is the drift WR-05 already exploits. For a redaction boundary, this is a correctness risk and not only a style issue.
**Fix:** Keep the constants and the URL/marker checks in one module, either `scripts/record_fixture.py` or a small `tests/fixture_rules.py`, and import them in both places. Make the hygiene test call the recorder's own validation function.

## Info

### IN-01: Duration is taken from `transcodings[0]` even when that transcoding is unplayable

**File:** `yt_dlp_plugins/extractor/audiocom.py:102`
**Issue:** The format loop skips transcodings without a URL, but duration still reads index 0. If the first entry has `url: null` or no `duration`, the value comes from an unplayable entry or is missing, even though later entries have one (probed: 999.999 s was taken from a URL-less entry).
**Fix:** `'duration': ('transcodings', lambda _, v: url_or_none(v['url']), 'duration', {lambda x: float_or_none(x, 1000)}, any)`.

### IN-02: The host match is case-sensitive

**File:** `yt_dlp_plugins/extractor/audiocom.py:16`
**Issue:** `https://AUDIO.com/u/audio/s` is not matched, even though paths are treated case-insensitively. This is unusual input, but it is inconsistent with the stated intent to accept uppercase.
**Fix:** `https?://(?:www\.)?(?i:audio\.com)/...`, or leave it as is and document it.

### IN-03: The recorder names fixture files from the API's `id` instead of the extractor's validated id

**File:** `scripts/record_fixture.py:77,86-88`
**Issue:** The return value of `ie.extract(url)` is discarded, and the filename is built from `rec["audio"]["id"]`, which is raw API data. Combined with WR-04 (non-string ids skip validation), a non-string or unexpected id becomes part of a filesystem path.
**Fix:** `info = ie.extract(url)`, then `path = FIXTURE_DIR / f'{info["id"]}.json'` after asserting `info['id'].isdigit()`.

### IN-04: The forbidden-marker scan also refuses legitimate content

**File:** `scripts/record_fixture.py:28,80-84`
**Issue:** The scan is a substring match over the whole serialized record, titles and descriptions included. A track titled "Token", "Signature Sound" or "Stripes" is refused. This errs on the safe side, but the message only lists the matched markers and not which field matched, so the operator cannot tell a real leak from a false positive.
**Fix:** Run the marker scan only over URL-bearing strings, or include the JSON path of the hit in the `REFUSED` message (without the value).

### IN-05: yt-dlp is unpinned and has no declared minimum version

**File:** `pyproject.toml:10,13`
**Issue:** The extractor relies on fairly recent `traverse_obj` path features (`filter` and `all` as path elements, set-wrapped callables) and on the `yt_dlp.utils.traversal` module. `dev = ["yt-dlp"]` has no lower bound, while pytest is pinned exactly. On an older bundled yt-dlp (MeTube images can lag behind), the plugin would fail in confusing ways.
**Fix:** Declare the minimum version the plugin is tested against, for example `"yt-dlp>=2025.1.1"` (use the actual tested floor), and note it in the plugin header comment.

### IN-06: `.gitignore` covers only two audio extensions

**File:** `.gitignore:7-10`
**Issue:** Only `*.m4a`, `*.mp3` and `*.part` are ignored. Manual testing with other yt-dlp outputs can leave large binaries ready to commit: `-x --audio-format opus/flac`, `*.ytdl` resume files, `*.part-Frag*`, `*.webm`/`*.ogg`/`*.opus`/`*.flac`, and thumbnails from `--write-thumbnail` (`*.jpg`/`*.webp`).
**Fix:** Add `*.ytdl`, `*.part-Frag*`, `*.opus`, `*.ogg`, `*.flac`, `*.wav`, `*.webm`, `*.webp`, `*.jpg`. Avoid broad image globs if fixtures will ever include images.

---

_Reviewed: 2026-10-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
