#!/usr/bin/env bash
# Live check of the AudioComIE plugin on every pinned yt-dlp version.
#
# For each target venv, in a fixed order (.venv = yt-dlp 2026.10.26, then
# .venv-metube = yt-dlp 2026.08.19, MeTube's bundled version), it checks the
# yt-dlp version pin, fetches and verifies that version's own test harness,
# runs the offline suite, checks that `yt-dlp -v` lists AudioComIE, runs
# AudioComIE._TESTS through the harness's test/test_download.py, does one real
# download of the reference track, checks that a nonexistent track fails
# with a single clean ERROR line and that a track not flagged downloadable
# lists no original-upload format. A failed step never stops the run; the
# last line is ALL TARGETS PASSED (exit 0) or SOME TARGETS FAILED (exit 1).
#
# Usage: scripts/test-live.sh   (needs network: github.com and audio.com)
#
# Env:
#   AUDIOCOM_HARNESS_DIR  harness cache, one sparse test/-only checkout per tag
#                         (default ${XDG_CACHE_HOME:-$HOME/.cache}/yt-dlp-audiocom/harness).
#                         Delete <dir>/<tag> to re-fetch a harness.
#   TMPDIR                where the per-target work dirs are created (mktemp -d).
#
# Nothing is written inside the repo. Output carries only versions, step results,
# test counts and byte sizes, never media URLs.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CACHE=${AUDIOCOM_HARNESS_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/yt-dlp-audiocom/harness}
REF_URL='https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best'
REF_ID=1877766681285368
MISSING_URL='https://audio.com/david-oliveira-1877766671108274/audio/this-slug-does-not-exist-zz9'
MISSING_ERROR='ERROR: [AudioCom] this-slug-does-not-exist-zz9: This audio.com track is unavailable (removed, private, or wrong URL)'
# _TESTS[1]; is_downloadable false (EXTR-04 negative)
NODL_URL='https://audio.com/jasa-sisemore/audio/jasasisemore-audacitypractice-autoduck-assignment-4aup'
# Whole word, so other plugins may sit next to it but a lookalike such as
# AudioComFooIE does not count.
PLUGIN_RE='Extractor Plugins: .*\bAudioComIE\b'
MIN_TESTS=3  # test_AudioCom, test_AudioCom_1, test_AudioCom_all
TARGETS=(  # venv  yt-dlp version (= zero-padded git tag)  tag commit
  ".venv        2026.10.26 f264a6cbd1f630894da0f368df00f8aae50140e0"
  ".venv-metube 2026.08.19 3a08beaf031ab68f966401ead017ac81fe8486cf"
)

# Rule for every check below: capture a command's output into a variable first,
# then grep the variable. Piping a command straight into a quiet grep is wrong
# under pipefail, because grep exits at the first match, the writer then dies of
# SIGPIPE and the pipeline reports a failure even though the text was there.

redact() {  # strip query strings (presign parameters) from any URL or bare path
  # Bare paths too: urllib3 errors quote the scheme-less form "with url: /path?X-Amz-...".
  sed -E 's#(/[^[:space:]?]*)\?[^[:space:]]*#\1?<redacted>#g'
}

work=''
cleanup() { [[ -z "$work" ]] || rm -rf "$work"; }
trap cleanup EXIT

harness() {  # $1=tag $2=sha; the harness root is $CACHE/$1
  local dir="$CACHE/$1" head status
  if [[ ! -f "$dir/test/test_download.py" ]]; then
    rm -rf "$dir"
    mkdir -p "$CACHE"
    # Sparse checkout of test/ only: test_download.py puts the checkout root first
    # on sys.path, so a full clone's yt_dlp/ would shadow the installed yt-dlp.
    if ! git -c advice.detachedHead=false clone -q --depth 1 --branch "$1" --filter=blob:none --sparse \
        https://github.com/yt-dlp/yt-dlp "$dir" >&2 \
        || ! git -C "$dir" sparse-checkout set test >&2; then
      echo "FAIL: harness $1 could not be fetched (delete $dir to re-fetch)"
      return 1
    fi
  fi
  # Never re-use or patch a checkout that is not exactly the pinned tag commit.
  # --ignored: yt-dlp's .gitignore hides test/local_parameters.json (merged into
  # the harness params by test/helper.py) and stale bytecode; neither may exist.
  head=$(git -C "$dir" rev-parse HEAD 2>/dev/null || true)
  status=$(git -C "$dir" status --porcelain --ignored 2>/dev/null || echo 'status failed')
  if [[ "$head" != "$2" ]] || ! git -C "$dir" diff --quiet HEAD 2>/dev/null \
      || [[ -n "$status" ]] || [[ -e "$dir/yt_dlp" ]]; then
    echo "FAIL: harness $1 is not a clean checkout of $2 (delete $dir to re-fetch)"
    return 1
  fi
  echo "ok: harness $1 at $2"
}

fail=0
for t in "${TARGETS[@]}"; do
  read -r venv want sha <<<"$t"
  py="$ROOT/$venv/bin/python"
  ytdlp="$ROOT/$venv/bin/yt-dlp"
  dir="$CACHE/$want"
  echo "=== $venv (yt-dlp $want)"

  # 1) The venv exists.
  if [[ ! -x "$py" || ! -x "$ytdlp" ]]; then
    echo "FAIL: $venv has no python"; fail=1; continue
  fi

  # 2) Exact version pin (no nightly, no drift).
  have=$("$py" -c 'import yt_dlp.version as v; print(v.__version__)' 2>/dev/null || true)
  if [[ "$have" != "$want" ]]; then
    echo "FAIL: $venv has yt-dlp ${have:-<none>}, expected $want"; fail=1; continue
  fi
  echo "ok: yt-dlp $have"

  # 3) That version's own harness, pinned by tag commit and unmodified.
  harness_ok=1
  harness "$want" "$sha" || { harness_ok=0; fail=1; }

  # 4) Offline suite on this version (no bytecode written into the repo).
  out=$(cd "$ROOT" && PYTHONDONTWRITEBYTECODE=1 "$py" -m pytest -q -p no:cacheprovider 2>&1) && rc=0 || rc=$?
  summary=${out##*$'\n'}
  if [[ "$rc" -eq 0 ]]; then
    echo "ok: offline suite ($summary)"
  else
    printf '%s\n' "$out" | redact
    echo "FAIL: offline suite (pytest exit $rc)"; fail=1
  fi

  # 5) PLUG-02: the plugin is discovered and imports cleanly.
  dbg=$("$ytdlp" -v --ignore-config --simulate "$REF_URL" 2>&1) || true
  if grep -Eq "$PLUGIN_RE" <<<"$dbg" && ! grep -q 'Error while importing' <<<"$dbg"; then
    echo "ok: plugin listed"
  else
    echo "FAIL: AudioComIE not listed in 'Extractor Plugins', or a plugin failed to import"; fail=1
  fi

  work=$(mktemp -d)

  # 6) PLUG-03: _TESTS through yt-dlp's own harness, from a fresh writable cwd.
  # No bytecode, so the cached harness stays a clean checkout for the next run.
  if [[ "$harness_ok" -eq 1 ]]; then
    out=$(cd "$work" && PYTHONDONTWRITEBYTECODE=1 "$py" "$ROOT/scripts/run_live_tests.py" "$dir" AudioCom 2>&1) \
      && rc=0 || rc=$?
    printf '%s\n' "$out" | redact
    passed=0
    if [[ "$out" =~ ([0-9]+)\ passed ]]; then passed=${BASH_REMATCH[1]}; fi
    if [[ "$rc" -eq 0 && "$passed" -ge "$MIN_TESTS" ]]; then
      echo "ok: _TESTS $passed passed"
    else
      echo "FAIL: _TESTS (pytest exit $rc, $passed passed, need at least $MIN_TESTS)"; fail=1
    fi
  else
    echo "FAIL: _TESTS not run (no clean harness)"
  fi

  # 7) One real download of the default format.
  out=$(cd "$work" && "$ytdlp" --ignore-config -q --no-progress -o '%(id)s.%(ext)s' "$REF_URL" 2>&1) && rc=0 || rc=$?
  if [[ "$rc" -eq 0 && -s "$work/$REF_ID.m4a" ]]; then
    echo "ok: downloaded $(stat -c %s "$work/$REF_ID.m4a") bytes"
  else
    printf '%s\n' "$out" | redact
    echo "FAIL: real download (yt-dlp exit $rc, no non-empty $REF_ID.m4a)"; fail=1
  fi

  # 8) EXTR-06: a nonexistent track fails with exactly one clean ERROR line.
  out=$("$ytdlp" --ignore-config --simulate "$MISSING_URL" 2>&1) && rc=0 || rc=$?
  errors=$(grep -c '^ERROR:' <<<"$out" || true)
  first=$(grep -m 1 '^ERROR:' <<<"$out" || true)
  if [[ "$rc" -ne 0 && "$errors" -eq 1 && "$first" == "$MISSING_ERROR" ]] \
      && ! grep -qE 'Traceback|report this issue|HTTP Error' <<<"$out"; then
    echo "ok: missing track gives one-line error"
  else
    printf '%s\n' "$out" | redact
    echo "FAIL: missing-track error (yt-dlp exit $rc, $errors ERROR lines, expected exactly: $MISSING_ERROR)"; fail=1
  fi

  # 9) EXTR-04: a track not flagged downloadable lists no original upload.
  # jasa-sisemore is the meaningful negative: its source is a plain wav, which
  # would pass the extension accept-list and the probe, so only the
  # is_downloadable gate keeps it out. The reference's WavPack source would be
  # rejected by the extension check anyway. -f names the original so that it is
  # requested (it is never listed otherwise); ba is the fallback. Prints format
  # ids only, never URLs.
  out=$("$ytdlp" --ignore-config --simulate -f 'original/ba' --print '%(formats.:.format_id)j' "$NODL_URL" 2>&1) && rc=0 || rc=$?
  if [[ "$rc" -eq 0 && "$out" == *'"mp3"'* && "$out" != *original* ]]; then
    echo "ok: non-downloadable track lists no original"
  else
    printf '%s\n' "$out" | redact
    echo "FAIL: non-downloadable track (yt-dlp exit $rc; need mp3 and no original)"; fail=1
  fi

  rm -rf "$work"
  work=''
done

if [[ "$fail" -ne 0 ]]; then
  echo "SOME TARGETS FAILED"
  exit 1
fi
echo "ALL TARGETS PASSED"
