#!/usr/bin/env bash
# Deploy the AudioComIE plugin into the running MeTube container and prove it.
#
# Checks that the plugin file the user installed in MeTube's host plugin
# directory is identical to this repo's yt_dlp_plugins/extractor/audiocom.py,
# waits until MeTube has no active download, restarts MeTube through its
# systemd unit metube.service, and checks inside it that yt-dlp loads
# AudioComIE next to the existing Rumble plugins and extracts the reference
# track. With --smoke it also submits the reference track to MeTube the way the
# web UI does and checks the saved file.
#
# The restart is `sudo systemctl restart metube.service`, never `docker
# restart`: the unit runs tank-service-guard before every start (so MeTube never
# binds an empty, unmounted /tank dir) and stops the container with a 60 s
# timeout. The script runs the same guard first, unprivileged, so a refusal
# stops the run while MeTube is still up. That systemctl call is the only sudo
# it runs. When the installed file is missing or out of date it only prints the
# one sudo install command for the user to run, and stops before any restart.
# Its only state changes are that restart (plus the guard's journal line) and,
# with --smoke, one new download named audiocom-smoke-<mode>-<epoch>.<title> in
# the download folder. It never deletes, moves or overwrites any file.
#
# Usage: scripts/deploy-metube.sh [--check] [--force] [--smoke video|audio]
#   (no option)    install check, wait for active downloads, restart, load checks
#   --check        the same checks without the restart; run it after a MeTube
#                  image update
#   --force        restart even while downloads are active (skips the wait)
#   --smoke MODE   also download the reference track through MeTube: video is
#                  the web UI's default form (m4a), audio is Audio/MP3 (mp3)
#   Options combine, e.g. --force --smoke audio or --check --smoke video.
#
# Env:
#   AUDIOCOM_INSTALL_PATH  installed plugin file, <plugin dir>/yt_dlp_plugins/extractor/audiocom.py
#                          (default /opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py).
#                          The __init__.py and rumble_fix.py checks follow its
#                          plugin dir, and the file the container sees under
#                          /plugins must still match the repo.
#   METUBE_URL             MeTube's HTTP address (default http://127.0.0.1:8085)
#   METUBE_DOWNLOADS       host path of MeTube's download folder
#                          (default /tank/docker/metube/downloads)
#   AUDIOCOM_DRAIN_TIMEOUT seconds to wait for active downloads before the
#                          restart (default 300)
#
# Each step prints one `ok: ...` or `FAIL: ...` line. The last line is
# DEPLOY OK (exit 0) or DEPLOY FAILED (exit 1). Raw yt-dlp output and MeTube's
# history JSON are never printed, because both can carry signed media URLs.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
SRC="$ROOT/yt_dlp_plugins/extractor/audiocom.py"
DEST=${AUDIOCOM_INSTALL_PATH:-/opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py}
PLUGINS_DIR=${DEST%/yt_dlp_plugins/extractor/audiocom.py}
# The same file as seen inside the container (/opt/metube/plugins:/plugins:ro).
IN_CONTAINER=/plugins/yt_dlp_plugins/extractor/audiocom.py
RUMBLE="$PLUGINS_DIR/yt_dlp_plugins/extractor/rumble_fix.py"
METUBE_URL=${METUBE_URL:-http://127.0.0.1:8085}
METUBE_URL=${METUBE_URL%/}
METUBE_DOWNLOADS=${METUBE_DOWNLOADS:-/tank/docker/metube/downloads}
CONTAINER=metube
SERVICE=metube.service
# The guard and arguments of metube.service's ExecStartPre (systemctl cat metube).
GUARD=/usr/local/bin/tank-service-guard
GUARD_ARGS=(--mount /tank/docker --sentinel /tank/docker/metube/downloads
  --sentinel /var/lib/docker-data/metube/state)
REF='https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best'
REF_SLUG=${REF##*/}
# Whole word, so a lookalike such as AudioComFooIE does not count.
PLUGIN_WORD='\bAudioComIE\b'

# Rule for every check below: capture a command's output into a variable first,
# then grep the variable. Piping a command straight into a quiet grep is wrong
# under pipefail, because grep exits at the first match, the writer then dies of
# SIGPIPE and the pipeline reports a failure even though the text was there.

usage() {
  echo 'Usage: scripts/deploy-metube.sh [--check] [--force] [--smoke video|audio]'
}

redact() {  # strip query strings (presign parameters) from any URL or bare path
  sed -E 's#(/[^[:space:]?]*)\?[^[:space:]]*#\1?<redacted>#g'
}

die() {  # the last FAIL line is already printed; nothing after this point runs
  echo "DEPLOY FAILED"
  exit 1
}

smoke='' check=0 force=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --smoke)
      if [[ $# -lt 2 || ( $2 != video && $2 != audio ) ]]; then usage >&2; exit 2; fi
      smoke=$2; shift 2 ;;
    --check) check=1; shift ;;
    --force) force=1; shift ;;
    *) usage >&2; exit 2 ;;
  esac
done
DRAIN_TIMEOUT=${AUDIOCOM_DRAIN_TIMEOUT:-300}
if [[ ! "$DRAIN_TIMEOUT" =~ ^[0-9]+$ ]]; then
  echo "AUDIOCOM_DRAIN_TIMEOUT must be a whole number of seconds" >&2; exit 2
fi

if [[ "$PLUGINS_DIR" == "$DEST" || -z "$PLUGINS_DIR" ]]; then
  echo "AUDIOCOM_INSTALL_PATH must end in /yt_dlp_plugins/extractor/audiocom.py" >&2; exit 2
fi

marker=''
cleanup() { [[ -z "$marker" ]] || rm -f "$marker"; }
trap cleanup EXIT

for tool in docker curl jq ffprobe cmp sha256sum; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "FAIL: missing tool $tool"
    die
  fi
done

fail=0

# 1) The installed file is this repo's file, mode 644. Anything else stops the
# run here, so a stale or half-written install never triggers a restart.
problem=''
if [[ ! -f "$SRC" ]]; then
  echo "FAIL: repo plugin $SRC not found"
  die
elif [[ ! -f "$DEST" ]]; then
  problem="FAIL: plugin not installed at $DEST"
elif ! cmp -s "$SRC" "$DEST"; then
  problem="FAIL: installed plugin $DEST differs from $SRC"
else
  mode=$(stat -c %a "$DEST" 2>/dev/null || echo '?')
  if [[ "$mode" != 644 ]]; then
    problem="FAIL: installed plugin $DEST has mode $mode, expected 644"
  fi
fi
if [[ -n "$problem" ]]; then
  echo "$problem"
  echo "Run this, then re-run scripts/deploy-metube.sh:"
  printf '  sudo install -m 644 %q %q\n' "$SRC" "$DEST"
  die
fi
sha=$(sha256sum <"$SRC")
echo "ok: installed plugin matches repo (sha256 ${sha:0:12})"

# 2) An __init__.py anywhere under the plugin dir turns yt_dlp_plugins into a
# regular package and hides MeTube's bundled bgutil plugins (PITFALLS 7).
# A missing or partly unreadable dir fails here instead of passing as "none found".
if [[ ! -d "$PLUGINS_DIR" ]]; then
  echo "FAIL: plugin dir $PLUGINS_DIR not found"
  die
fi
if ! inits=$(find "$PLUGINS_DIR" -name __init__.py 2>&1); then
  echo "FAIL: cannot scan $PLUGINS_DIR: ${inits//$'\n'/; }"
  die
fi
if [[ -n "$inits" ]]; then
  echo "FAIL: ${inits//$'\n'/, } shadows MeTube's bundled plugins; remove it before deploying"
  die
fi
echo "ok: no __init__.py under $PLUGINS_DIR"

# 3) The existing Rumble plugin is still in place (not fatal).
if [[ -f "$RUMBLE" ]]; then
  echo "ok: rumble_fix.py present"
else
  echo "FAIL: $RUMBLE is missing"; fail=1
fi

# Restart guard: never restart while MeTube is working on an item. Pending,
# queued and scheduled items persist across a restart, so they do not count.
# A failed request is retried until the timeout.
drain() {
  local deadline=$((SECONDS + DRAIN_TIMEOUT)) h n active='' answered=0
  while :; do
    h=$(curl -sf --max-time 5 "$METUBE_URL/history" 2>/dev/null || true)
    n=$(jq -r 'if type == "object" then [(.queue // [])[]
          | select(.status == "preparing" or .status == "downloading" or .status == "postprocessing")]
          | length else empty end' <<<"$h" 2>/dev/null || true)
    if [[ "$n" =~ ^[0-9]+$ ]]; then
      answered=1; active=$n
      if [[ "$n" -eq 0 ]]; then
        echo "ok: no active downloads"
        return 0
      fi
    fi
    if [[ "$SECONDS" -ge "$deadline" ]]; then break; fi
    sleep 5
  done
  if [[ "$answered" -eq 1 ]]; then
    echo "FAIL: $active downloads still active after ${DRAIN_TIMEOUT}s; re-run later or pass --force"
  else
    echo "FAIL: MeTube not answering at $METUBE_URL/history; pass --force to restart anyway"
  fi
  return 1
}

restart() {  # 4) Restart through metube.service, which owns every MeTube start.
  local before after id0 start0 id1 start1 running out rc gout note=''
  before=$(docker inspect -f '{{.Id}} {{.State.StartedAt}}' "$CONTAINER" 2>/dev/null || true)
  if [[ -z "$before" ]]; then
    echo "FAIL: container $CONTAINER not found"
    die
  fi
  read -r id0 start0 <<<"$before"
  # The unit stops the container before its guard runs, so a refusal there
  # would leave MeTube down. Run the guard first and stop here instead.
  if [[ ! -x "$GUARD" ]]; then
    echo "FAIL: $GUARD not found; not restarting"
    die
  fi
  if ! gout=$("$GUARD" --name metube-deploy-precheck "${GUARD_ARGS[@]}" 2>&1); then
    echo "FAIL: tank-service-guard refused, MeTube left running: ${gout//$'\n'/ }"
    die
  fi
  echo "ok: tank-service-guard passed"
  out=$(sudo systemctl restart "$SERVICE" 2>&1) && rc=0 || rc=$?
  after=$(docker inspect -f '{{.Id}} {{.State.StartedAt}} {{.State.Running}}' "$CONTAINER" 2>/dev/null || true)
  read -r id1 start1 running <<<"$after"
  if [[ "$rc" -eq 0 && "$running" == true && -n "$start1" && "$start1" != "$start0" ]]; then
    # compose recreates the container only when its config or image changed.
    if [[ "$id1" != "$id0" ]]; then note=", container recreated by compose"; fi
    echo "ok: restarted MeTube through $SERVICE$note"
  else
    echo "FAIL: sudo systemctl restart $SERVICE (exit $rc: ${out//$'\n'/ }; id ${id0:0:12} -> ${id1:0:12}, started $start0 -> ${start1:-?}, running ${running:-?}); see systemctl status $SERVICE"
    die
  fi
}

if [[ "$check" -eq 1 ]]; then
  echo "ok: restart skipped (--check)"
else
  if [[ "$force" -eq 1 ]]; then
    echo "ok: active-download check skipped (--force)"
  else
    drain || die
  fi
  restart
fi

# 5) MeTube answers again. The later steps need the container.
ver=''
deadline=$((SECONDS + 120))
while :; do
  body=$(curl -sf --max-time 2 "$METUBE_URL/version" 2>/dev/null || true)
  ver=$(jq -r '."yt-dlp" // empty' <<<"$body" 2>/dev/null || true)
  if [[ -n "$ver" || "$SECONDS" -ge "$deadline" ]]; then break; fi
  sleep 1
done
if [[ -z "$ver" ]]; then
  echo "FAIL: MeTube not answering at $METUBE_URL/version after 120s"
  die
fi
echo "ok: MeTube answering (yt-dlp $ver)"

# The file yt-dlp loads inside the container is this repo's file. Step 1 checked
# the host path; this catches an install path the container does not mount.
in_sha=$(docker exec "$CONTAINER" sha256sum "$IN_CONTAINER" 2>/dev/null || true)
if [[ -n "$in_sha" && "${in_sha%% *}" == "${sha%% *}" ]]; then
  echo "ok: container sees the repo plugin at $IN_CONTAINER"
else
  echo "FAIL: $IN_CONTAINER inside $CONTAINER is missing or differs from $SRC"; fail=1
fi

# 6) yt-dlp inside MeTube lists AudioComIE once, next to the Rumble plugins,
# and no plugin failed to import.
# The second --print is the title as yt-dlp writes it into a filename
# (sanitized: / : | ? and so on become lookalikes), which the raw title is not.
out=$(docker exec "$CONTAINER" yt-dlp -v --simulate -o 'AC_FILE=%(title)s' \
  --print '%(extractor_key)s|%(title)s|%(duration)s|%(uploader)s' --print filename "$REF" 2>&1) && yrc=0 || yrc=$?
plugins_line=$(grep -m 1 '^\[debug\] Extractor Plugins:' <<<"$out" || true)
dirs_line=$(grep -m 1 '^\[debug\] Plugin directories:' <<<"$out" || true)
import_errors=$(grep 'Error while importing' <<<"$out" || true)
hits=$(grep -oE "$PLUGIN_WORD" <<<"$plugins_line" || true)
count=0
if [[ -n "$hits" ]]; then count=$(wc -l <<<"$hits"); fi
show_debug() {  # only the plugin lines, never the rest of the -v output
  printf '%s\n' "${plugins_line:-<no Extractor Plugins line>}" "${dirs_line:-<no Plugin directories line>}"
  if [[ -n "$import_errors" ]]; then printf '%s\n' "$import_errors" | redact; fi
}
if [[ "$count" -eq 1 ]] && grep -qE '\bRumbleIE\b' <<<"$plugins_line" && [[ -z "$import_errors" ]]; then
  echo "ok: plugin listed with Rumble plugins"
else
  show_debug
  echo "FAIL: AudioComIE listed $count times (need 1), RumbleIE missing, or a plugin failed to import"; fail=1
fi

# 7) Both plugin trees are searched: MeTube's /plugins mount and the image's
# site-packages tree that holds the bgutil PO-token plugins.
if [[ "$dirs_line" == *'/plugins/yt_dlp_plugins'* && "$dirs_line" == *'site-packages/yt_dlp_plugins'* ]]; then
  echo "ok: plugin directories intact"
else
  printf '%s\n' "${dirs_line:-<no Plugin directories line>}"
  echo "FAIL: plugin directories must include /plugins/yt_dlp_plugins and site-packages/yt_dlp_plugins"; fail=1
fi

# 8) AudioCom extracted the reference track. The title is the middle field, so
# a '|' inside it cannot shift the duration or uploader.
TITLE='' DURATION='' UPLOADER='' FILE_TITLE=''
line=$(grep -m 1 '^AC_FILE=' <<<"$out" || true)
FILE_TITLE=${line#AC_FILE=}
line=$(grep -m 1 '^AudioCom|' <<<"$out" || true)
if [[ -n "$line" ]]; then
  rest=${line#AudioCom|}
  UPLOADER=${rest##*|}; rest=${rest%|*}
  DURATION=${rest##*|}; TITLE=${rest%|*}
fi
extracted=0
if [[ "$yrc" -eq 0 && -n "$TITLE" && "$TITLE" != NA && "$TITLE" != "$REF_SLUG" ]]; then
  extracted=1
  echo "ok: reference URL extracted by AudioCom"
else
  errs=$(grep '^ERROR:' <<<"$out" || true)
  if [[ -n "$errs" ]]; then printf '%s\n' "$errs" | redact; fi
  echo "FAIL: reference URL not extracted by AudioCom (yt-dlp exit $yrc)"; fail=1
fi

# 9) --smoke: submit the reference URL like the web UI and check the saved file.
smoke_run() {  # $1 = video | audio
  local mode=$1 dtype fmt ext want_codec prefix existing pre='' body resp st msg
  local h entry state='' emsg fname files f problems=() acodec vstreams ftitle fartist fdur now
  case $mode in
    video) dtype=video; fmt=any; ext=m4a; want_codec=aac ;;
    # MeTube's audio mode re-encodes with FFmpegExtractAudio (PITFALLS 6).
    audio) dtype=audio; fmt=mp3; ext=mp3; want_codec=mp3 ;;
  esac
  prefix="audiocom-smoke-$mode-$(date +%s)"
  if [[ -z "$FILE_TITLE" || "$FILE_TITLE" == */* ]]; then
    echo "FAIL: yt-dlp gave no usable filename title for the reference track"
    return 1
  fi
  # The unprefixed copy a plain web-UI download would have saved. When it is
  # there, the smoke run must leave it untouched.
  existing="$METUBE_DOWNLOADS/$FILE_TITLE.m4a"
  if [[ -f "$existing" ]]; then
    pre=$(stat -c '%s %Y' "$existing")
  else
    echo "note: no unprefixed copy at $existing; overwrite check not applicable"
  fi
  marker=$(mktemp)

  # The web UI's own field names and default form values.
  body=$(jq -nc --arg url "$REF" --arg dt "$dtype" --arg fmt "$fmt" --arg p "$prefix" \
    '{url: $url, download_type: $dt, codec: "auto", format: $fmt, quality: "best", custom_name_prefix: $p}')
  resp=$(curl -sS --max-time 120 -H 'Content-Type: application/json' -d "$body" "$METUBE_URL/add" 2>&1 || true)
  st=$(jq -r '.status // empty' <<<"$resp" 2>/dev/null || true)
  msg=$(jq -r '.msg // empty' <<<"$resp" 2>/dev/null || true)
  if [[ "$st" != ok || -n "$msg" ]]; then
    if [[ -z "$st" ]]; then msg=$(head -c 300 <<<"$resp" | tr '\n' ' '); fi
    echo "FAIL: MeTube add ($mode) answered ${st:-no JSON}: $(redact <<<"${msg:-<no msg>}")"
    return 1
  fi

  # MeTube moves the item to "done" as finished or error; its title is <prefix>.<title>.
  local wait_deadline=$((SECONDS + 300))
  while :; do
    h=$(curl -sf --max-time 10 "$METUBE_URL/history" 2>/dev/null || true)
    entry=$(jq -c --arg p "$prefix." \
      '[.done[]? | select((.title // "") | startswith($p))] | first // empty' <<<"$h" 2>/dev/null || true)
    if [[ -n "$entry" ]]; then
      state=$(jq -r '.status // empty' <<<"$entry" 2>/dev/null || true)
      break
    fi
    if [[ "$SECONDS" -ge "$wait_deadline" ]]; then break; fi
    sleep 5
  done
  if [[ -z "$entry" ]]; then
    echo "FAIL: MeTube did not finish $prefix within 300s"
    return 1
  fi
  if [[ "$state" != finished ]]; then
    emsg=$(jq -r '.msg // .error // empty' <<<"$entry" 2>/dev/null || true)
    echo "FAIL: MeTube download $prefix ended '$state': $(redact <<<"${emsg:-<no msg>}")"
    return 1
  fi

  # The saved name comes from MeTube's done entry, not from the raw title.
  fname=$(jq -r '.filename // empty' <<<"$entry" 2>/dev/null || true)
  if [[ -z "$fname" || "$fname" == */* || "$fname" != "$prefix".*."$ext" ]]; then
    echo "FAIL: MeTube done entry for $prefix names file '${fname:-<none>}', expected $prefix.<title>.$ext"
    return 1
  fi
  f="$METUBE_DOWNLOADS/$fname"
  mapfile -t files < <(find "$METUBE_DOWNLOADS" -maxdepth 1 -type f -name "$prefix.*.$ext" -newer "$marker" 2>/dev/null)
  if [[ "${#files[@]}" -ne 1 || "${files[0]}" != "$f" || ! -s "$f" ]]; then
    echo "FAIL: expected exactly one new non-empty $f, found ${#files[@]}: ${files[*]:-none}"
    return 1
  fi

  acodec=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nw=1:nk=1 "$f" 2>/dev/null || true)
  vstreams=$(ffprobe -v error -select_streams V -show_entries stream=index -of csv=p=0 "$f" 2>/dev/null || true)
  ftitle=$(ffprobe -v error -show_entries format_tags=title -of default=nw=1:nk=1 "$f" 2>/dev/null || true)
  fartist=$(ffprobe -v error -show_entries format_tags=artist -of default=nw=1:nk=1 "$f" 2>/dev/null || true)
  fdur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$f" 2>/dev/null || true)
  [[ "$acodec" == "$want_codec" ]] || problems+=("audio codec '${acodec:-none}', expected $want_codec")
  [[ -z "$vstreams" ]] || problems+=("has a video stream")
  [[ "$ftitle" == "$TITLE" ]] || problems+=("title tag '$ftitle', expected '$TITLE'")
  [[ "$fartist" == "$UPLOADER" ]] || problems+=("artist tag '$fartist', expected '$UPLOADER'")
  awk -v d="$fdur" -v e="$DURATION" 'BEGIN { exit !(d != "" && e != "" && d - e <= 2 && e - d <= 2) }' \
    || problems+=("duration ${fdur:-?}s, expected ${DURATION:-?}s within 2s")
  if [[ -n "$pre" ]]; then
    now=$(stat -c '%s %Y' "$existing" 2>/dev/null || echo missing)
    [[ "$now" == "$pre" ]] || problems+=("pre-existing $existing changed ($pre -> $now)")
  fi
  if [[ "${#problems[@]}" -gt 0 ]]; then
    msg=$(printf '%s; ' "${problems[@]}")
    echo "FAIL: $f: ${msg%; }"
    return 1
  fi
  echo "ok: MeTube saved $f"
  echo "note: this is a test download; delete it when you no longer need it"
  rm -f "$marker"; marker=''
}

if [[ -n "$smoke" ]]; then
  if [[ "$extracted" -eq 1 ]]; then
    smoke_run "$smoke" || fail=1
  else
    echo "FAIL: --smoke $smoke skipped (reference URL not extracted)"; fail=1
  fi
fi

if [[ "$fail" -ne 0 ]]; then
  echo "DEPLOY FAILED"
  exit 1
fi
echo "DEPLOY OK"
