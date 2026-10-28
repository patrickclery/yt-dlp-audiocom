---
phase: 03-metube-deploy
reviewed: 2026-10-28T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - scripts/deploy-metube.sh
  - README.md
findings:
  critical: 1
  warning: 4
  info: 6
  total: 11
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-28
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

I reviewed the changes since f59d49c statically and did not run the script. Its shell hygiene is solid: `set -euo pipefail`, output is captured before grepping, sudo is printed with `printf %q` and never run, and the only `rm` targets the mktemp marker. The restart path is the main problem. `docker restart metube` skips the host's `tank-service-guard`, which is the safety gate that `/opt/metube/docker-compose.yml` and `metube.service` say owns every container start. It also stops the container with Docker's 10 s default timeout, while systemd uses 60 s. Several checks can pass when they should fail: a missing plugin dir, a decoupled `AUDIOCOM_INSTALL_PATH`, or a title that yt-dlp sanitizes. A few README and usability gaps round out the list.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `docker restart` bypasses metube.service's tank-service-guard

**File:** `scripts/deploy-metube.sh:179`, `README.md:24`, `README.md:93`
**Issue:** `/opt/metube/docker-compose.yml` says: "restart: "no" is deliberate ... startup is owned by metube.service, which runs tank-service-guard first so the container can never bind an empty (unmounted) /tank dir". `metube.service` enforces this with `ExecStartPre=/usr/local/bin/tank-service-guard --mount /tank/docker --sentinel /tank/docker/metube/downloads --sentinel /var/lib/docker-data/metube/state`. On a restart, `docker restart` re-resolves the bind sources without running that guard. Compose short-syntax binds are created with create-host-path. So if the pool is not mounted, the container comes back on an empty root-fs `/tank/docker/metube/downloads`. New downloads then go there and are hidden when the pool mounts back over the directory. That is the exact data-loss case the guard was added to prevent. The README Install and Remove blocks tell the user to run the same unguarded `docker restart metube`.
**Fix:** Before the restart, check the same conditions the guard checks, and fail closed:
```bash
pre_restart_guard() {
  if ! findmnt -n -T /tank/docker >/dev/null || [[ "$(findmnt -n -o TARGET -T /tank/docker)" == / ]]; then
    echo "FAIL: /tank/docker is not mounted; not restarting"; die
  fi
  for s in "$METUBE_DOWNLOADS" /var/lib/docker-data/metube/state; do
    if [[ ! -d "$s" || -z "$(ls -A "$s" 2>/dev/null)" ]]; then
      echo "FAIL: sentinel $s missing or empty; not restarting"; die
    fi
  done
}
```
A simpler option is to call `/usr/local/bin/tank-service-guard --name metube --mount /tank/docker --sentinel ... --sentinel ...` directly, if it works without root. Make the README restart commands match this, or point them at the script only.

## Warnings

### WR-01: Restart uses Docker's 10 s stop timeout, not the service's 60 s

**File:** `scripts/deploy-metube.sh:179`, `README.md:24,93`
**Issue:** `docker inspect -f '{{.Config.StopTimeout}}' metube` returns `<nil>`, so `docker restart` sends SIGKILL 10 s after SIGTERM. `metube.service` stops the container with `docker compose stop -t 60`. MeTube writes its queue to `/state` on shutdown, and under `--force` there can be live ffmpeg postprocessing in `/downloads` (TEMP_DIR=/downloads). A kill at 10 s can drop or corrupt the saved queue and leave partial files in the library folder.
**Fix:** `out=$(docker restart -t 60 "$CONTAINER" 2>&1)`, and use `docker restart -t 60 metube` in the README.

### WR-02: Install check follows `AUDIOCOM_INSTALL_PATH`, everything else stays hardcoded to /opt/metube

**File:** `scripts/deploy-metube.sh:43-45`
**Issue:** `DEST` can be overridden, but `PLUGINS_DIR` and `RUMBLE` are fixed. Nothing checks that the file yt-dlp loads inside the container is the repo file. With the override set, step 1 can report "installed plugin matches repo" for a file the container never mounts. Steps 6-8 then pass on whatever stale `audiocom.py` is in `/opt/metube/plugins`, and the run ends `DEPLOY OK` for the wrong code.
**Fix:** Either remove the override, or derive `PLUGINS_DIR="${DEST%/yt_dlp_plugins/extractor/*}"`. In both cases, add an in-container identity check after the restart:
```bash
in_sha=$(docker exec "$CONTAINER" sha256sum /plugins/yt_dlp_plugins/extractor/audiocom.py 2>/dev/null | cut -d' ' -f1 || true)
[[ "$in_sha" == "${sha%% *}" ]] || { echo "FAIL: container sees a different audiocom.py"; fail=1; }
```

### WR-03: The `__init__.py` check passes when the plugin dir is missing or unreadable

**File:** `scripts/deploy-metube.sh:129-134`
**Issue:** `find "$PLUGINS_DIR" ... 2>/dev/null || true` throws away both the error and the exit status. I confirmed it: `find /nonexistent-dir -name __init__.py 2>/dev/null || true` returns empty, and the script prints `ok: no __init__.py`. A permission-denied subdirectory is skipped the same way, so an `__init__.py` inside it goes unreported, and that file would break bgutil (PITFALLS 7).
**Fix:**
```bash
[[ -d "$PLUGINS_DIR" ]] || { echo "FAIL: $PLUGINS_DIR not found"; die; }
if ! inits=$(find "$PLUGINS_DIR" -name __init__.py 2>&1); then
  echo "FAIL: cannot scan $PLUGINS_DIR: ${inits//$'\n'/; }"; die
fi
```

### WR-04: The smoke step compares raw titles with sanitized filenames, so the no-overwrite check can turn off without notice

**File:** `scripts/deploy-metube.sh:275-276,315-316`
**Issue:** `TITLE` is the raw `%(title)s` from `--print`. yt-dlp sanitizes `%(title)s` in the output template: `/ \ : | ? * " < >` become full-width lookalikes. If the reference track's title ever contains one of those characters, the check at line 316 fails even though MeTube saved the file correctly. Worse, `existing` on line 275 then points at a path that does not exist, so `pre` stays empty and the check for "the pre-existing copy did not change" is skipped with no message. That check is the evidence behind the header's claim that the script never overwrites a file.
**Fix:** Take the real filename from MeTube's done entry, or match on the prefix alone. Fail loudly if the pre-existing copy was expected and not found:
```bash
f=${files[0]}   # after asserting exactly one "$prefix.*.$ext" match
[[ -f "$existing" ]] || echo "note: no unprefixed copy at $existing; overwrite check not applicable"
```
Better still, use `docker exec metube yt-dlp --print filename -o '%(title)s.%(ext)s' "$REF"` to get the sanitized name.

## Info

### IN-01: Field parse can still shift when the uploader contains `|`

**File:** `scripts/deploy-metube.sh:218-219,246-254`
**Issue:** The comment says a `|` cannot shift fields because the title is in the middle. But `UPLOADER=${rest##*|}` takes the text after the last `|`. If the uploader name contains a `|`, part of the uploader becomes the duration and the duration ends up in the title. The smoke step then reports false artist and duration failures.
**Fix:** Use one `--print` per field with distinct line prefixes, for example `--print 'AC_TITLE=%(title)s' --print 'AC_UPLOADER=%(uploader)s'`, and grep each line.

### IN-02: ffprobe is required even when `--smoke` is not used

**File:** `scripts/deploy-metube.sh:93`
**Issue:** On a host without ffmpeg, a plain deploy or `--check` fails before any work with `missing tool ffprobe`, though only `smoke_run` uses it.
**Fix:** Check `ffprobe` only when `[[ -n $smoke ]]`.

### IN-03: A download can start between the drain check and the restart

**File:** `scripts/deploy-metube.sh:196-198`
**Issue:** `drain` returns on one zero sample, and the restart follows. An item in `queued` or `scheduled`, or a new web-UI add, can start in that gap and be killed. The window is small, but the guard is not atomic.
**Fix:** Require two zero samples a few seconds apart, or re-check just before `docker restart`.

### IN-04: A smoke timeout leaves the item running with no hint

**File:** `scripts/deploy-metube.sh:292-307`
**Issue:** With `MAX_CONCURRENT_DOWNLOADS=5`, the smoke item can wait for a free slot past 300 s. The script prints FAIL, but MeTube still finishes the download into the Plex-indexed folder. A re-run then gets `Already in queue` because MeTube keys the queue by URL.
**Fix:** On timeout, say that `$prefix` may still finish and must be removed from the queue before a re-run.

### IN-05: README is missing the script's prerequisites and side effects

**File:** `README.md:32-41`
**Issue:** The README does not say that the script needs `docker` access without sudo (docker group), plus `curl`, `jq`, `ffprobe`, `cmp` and `sha256sum` on the host. It does not list the env overrides (`METUBE_URL`, `METUBE_DOWNLOADS`, `AUDIOCOM_DRAIN_TIMEOUT`). It also does not warn that smoke files land in `/tank/docker/metube/downloads`, which Plex section 16 "Music (yt)" indexes, so they show up as duplicate tracks until deleted. Finally, `<title>` in the documented filename is the sanitized title, not the raw one.
**Fix:** Add a short "Requirements / environment" note and a line about the Plex side effect.

### IN-06: Option and exit-code edge cases don't match the header

**File:** `scripts/deploy-metube.sh:36-37,77-86,190-199`
**Issue:** `--check --force` silently ignores `--force`. Usage errors and a bad `AUDIOCOM_DRAIN_TIMEOUT` exit 2 without the `DEPLOY FAILED` line that the header says always comes last. A missing `rumble_fix.py` (step 3) sets `fail=1` but still restarts MeTube, even though the run is already sure to fail at step 6.
**Fix:** Reject or warn on `--check --force`, note the exit-2 case in the header, and run `die` before the restart when step 3 fails in deploy mode.

---

_Reviewed: 2026-10-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
