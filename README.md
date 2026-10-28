# yt-dlp-audiocom

A [yt-dlp](https://github.com/yt-dlp/yt-dlp) plugin extractor for audio.com
single-track URLs (`https://audio.com/<user>/audio/<slug>`). It ships as a plugin
only: one file, `yt_dlp_plugins/extractor/audiocom.py`, that yt-dlp (or MeTube's
bundled yt-dlp) discovers through the `yt_dlp_plugins` namespace package. It
targets yt-dlp 2026.10.26 (current stable) and 2026.08.19 (the version MeTube
bundles).

## Development setup

Two Python 3.11 venvs, one per supported yt-dlp version, built with
[uv](https://docs.astral.sh/uv/) from exact pins. Both are gitignored.

```sh
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python 'yt-dlp==2026.10.26' 'pytest==9.1.1' -e .
uv venv .venv-metube --python 3.11
uv pip install --python .venv-metube/bin/python 'yt-dlp==2026.8.19' 'pytest==9.1.1' -e .
```

The editable install (`-e .`, built with hatchling 1.32.4) puts the plugin on the
venv's path, so `.venv/bin/yt-dlp -v <url>` lists `AudioComIE` under
`Extractor Plugins:`. Use exact pins only, never a nightly.

## Offline tests

The offline suite replays recorded API fixtures (`tests/fixtures/`) and makes no
network requests. Run it on both versions:

```sh
.venv/bin/python -m pytest -q
.venv-metube/bin/python -m pytest -q
```

## Live tests

```sh
scripts/test-live.sh
```

This is the one command that proves the plugin on both pinned versions. It needs
network access (github.com and audio.com) and writes nothing inside the repo. For
each target, always in this order (`.venv` = 2026.10.26, then `.venv-metube` =
2026.08.19), it prints one `ok: ...` or `FAIL: ...` line per step:

1. The venv's interpreter exists (`FAIL: <venv> has no python` otherwise).
2. `yt_dlp.version.__version__` equals the pinned version (`ok: yt-dlp <version>`).
3. That version's own test harness: a sparse checkout of only `test/` from
   yt-dlp at the matching zero-padded tag. It must be exactly the pinned tag
   commit, with no modified or extra files (gitignored ones such as
   `test/local_parameters.json` or `__pycache__/` included) and no `yt_dlp/`
   directory, or the script refuses it (`ok: harness <tag> at <sha>`).
4. The offline suite passes on this version (`ok: offline suite`).
5. `yt-dlp -v` lists `AudioComIE` under `Extractor Plugins:` with no import error
   (`ok: plugin listed`).
6. `AudioComIE._TESTS` (the reference track and the 2023 jasa-sisemore track)
   run through that version's `test/test_download.py` via
   `scripts/run_live_tests.py`, from a fresh temp directory. At least 3 tests
   must pass: `test_AudioCom`, `test_AudioCom_1` and `test_AudioCom_all`
   (`ok: _TESTS <N> passed`).
7. A real download of the reference track's default format, a non-empty m4a
   (`ok: downloaded <bytes> bytes`).
8. A nonexistent track URL fails (non-zero exit) with exactly one `ERROR:` line,
   `ERROR: [AudioCom] this-slug-does-not-exist-zz9: This audio.com track is unavailable (removed, private, or wrong URL)`,
   and no traceback, "report this issue" or "HTTP Error" text
   (`ok: missing track gives one-line error`).
9. A track not flagged downloadable (jasa-sisemore, whose original is a plain
   wav) lists `mp3` and no `original` format
   (`ok: non-downloadable track lists no original`).

A failed step never stops the run. The last line is `ALL TARGETS PASSED` (exit 0)
only when every step passed on both venvs, and `SOME TARGETS FAILED` (exit 1)
otherwise.

Environment variables:

- `AUDIOCOM_HARNESS_DIR`: the harness cache, one checkout per tag. Default
  `${XDG_CACHE_HOME:-$HOME/.cache}/yt-dlp-audiocom/harness`. To re-fetch a
  harness, delete `<dir>/<tag>` (for example `<dir>/2026.10.26`) and rerun.
- `TMPDIR`: where the per-target work directories are created (`mktemp -d`).
  They are removed afterwards.

To run the harness by hand:
`python scripts/run_live_tests.py <harness-root> [pytest -k expr] [extra pytest args]`.

## Original uploads

When the uploader allows downloads, the track also offers the file they uploaded
(wav, mp3, m4a, flac and so on) as an extra format named `original`:

```sh
yt-dlp -f original 'https://audio.com/<user>/audio/<slug>'
```

- It is opt-in only. It is listed only when the `-f` spec names `original`
  (`-f original`, `-f original/ba`), and for `-F`. Every other selector
  (the default, `-f ba`, `-f worst`, `-f wa`, `-f 'ba[ext=wav]'`, any `-S` sort)
  never sees it and keeps choosing a transcoding (mp3 or m4a). For the same
  reason `-j` does not include it unless `-f` names it.
- WavPack originals are not offered, because yt-dlp rejects the `wv` extension.
- An original that audio.com no longer serves is skipped with a one-line note
  (`<id>: original upload URL is invalid, skipping: HTTP Error 404: Not Found`).
- Tracks not flagged downloadable never list an original. On those, and on the
  cases above, `-f original` fails with `Requested format is not available`.

## Errors

A track that cannot be fetched fails with one line naming the track (its URL slug,
or its numeric id once known) and the cause, with no traceback:

- `ERROR: [AudioCom] <slug or id>: This audio.com track is unavailable (removed, private, or wrong URL)`:
  audio.com answered 404 or 410. The track was removed, the URL is mistyped, or
  the track is private to its owner.
- `ERROR: [AudioCom] <slug or id>: This audio.com track is private or restricted`:
  audio.com's API answered 401 or 403 with JSON, so the track exists but is not
  available anonymously. A 401 or 403 that is a Cloudflare challenge or block
  page (HTML, or a `cf-mitigated` header) is not a track problem and keeps
  yt-dlp's own `HTTP Error 403` message.

Unlisted tracks (not shown on the uploader's profile, but playable by anyone with
the link) download normally. Any other failure keeps yt-dlp's own error message.
Add `-v` to see the requests and the debug trace behind an error.
