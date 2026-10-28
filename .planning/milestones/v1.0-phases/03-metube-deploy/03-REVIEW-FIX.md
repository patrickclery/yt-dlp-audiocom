---
phase: 03-metube-deploy
fixed_at: 2026-10-28T20:00:00Z
review_path: .planning/phases/03-metube-deploy/03-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 3: Code Review Fix Report

**Fixed at:** 2026-10-28T20:00:00Z
**Source review:** .planning/phases/03-metube-deploy/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (1 critical, 4 warning; Info findings not in scope)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: `docker restart` bypasses metube.service's tank-service-guard

**Files modified:** `scripts/deploy-metube.sh`, `README.md`
**Commit:** 1a78b36
**Applied fix:** `restart()` now runs `sudo systemctl restart metube.service`. The unit is Type=oneshot with RemainAfterExit=yes, so a restart runs ExecStop (`docker compose stop -t 60`), then ExecStartPre (`tank-service-guard`), then ExecStart (`docker compose up -d`). The unit stops MeTube before its guard runs, so the script first runs `/usr/local/bin/tank-service-guard` itself with the unit's exact arguments. The guard works without root. If it refuses, the run stops and MeTube stays up. The success check now requires systemctl exit 0, a running container, and a new StartedAt. A container id change is reported as a compose recreate rather than treated as a failure. The header is updated: that systemctl call is the only sudo the script runs. The README Install and Remove blocks and the Update prose now say `sudo systemctl restart metube.service`, and there is a new note saying never to use `docker restart`.

### WR-01: Restart uses Docker's 10 s stop timeout, not the service's 60 s

**Files modified:** `scripts/deploy-metube.sh`, `README.md`
**Commit:** 1a78b36 (same commit as CR-01)
**Applied fix:** Fixed by the CR-01 change. The stop now goes through the unit's `ExecStop=/usr/bin/docker compose stop -t 60`, both in the script and in the README commands. There is no separate `docker restart -t 60` anywhere.

### WR-02: Install check follows `AUDIOCOM_INSTALL_PATH`, everything else stays hardcoded to /opt/metube

**Files modified:** `scripts/deploy-metube.sh`
**Commit:** a8674ec
**Applied fix:** `PLUGINS_DIR` (and so `RUMBLE`) is now derived from `DEST`. An install path that does not end in `/yt_dlp_plugins/extractor/audiocom.py` exits 2. A new step after "MeTube answering" runs `docker exec metube sha256sum /plugins/yt_dlp_plugins/extractor/audiocom.py` and fails the run unless the hash matches the repo file. The env docs in the header are updated.

### WR-03: The `__init__.py` check passes when the plugin dir is missing or unreadable

**Files modified:** `scripts/deploy-metube.sh`
**Commit:** c6e31ea
**Applied fix:** The check now fails with `die` when `$PLUGINS_DIR` is not a directory, and also when `find` exits non-zero (for example a permission-denied subdirectory), with find's stderr shown in the FAIL line.

### WR-04: The smoke step compares raw titles with sanitized filenames, so the no-overwrite check can turn off without notice

**Files modified:** `scripts/deploy-metube.sh`
**Commit:** 4cff3b8
**Status:** fixed: requires human verification (logic change)
**Applied fix:** Step 6's yt-dlp call now also passes `-o 'AC_FILE=%(title)s' --print filename`, which gives the title as it appears in filenames (sanitized). That value is now used for the pre-existing unprefixed copy path. If that copy is missing, the run prints `note: no unprefixed copy at ...; overwrite check not applicable`. The saved file now comes from the `filename` field of MeTube's done entry. That field must have the form `<prefix>.*.<ext>`, contain no `/`, and be the single new file `find` reports. The ffprobe title-tag check still compares against the raw title, which is correct because tags hold the raw title.

## Verification

All verification ran in the isolated worktree (`.claude/worktrees/rf-03-2054294-1793217304`), against the live host MeTube. The repo's `audiocom.py` was not changed, so the results also hold for the main checkout after the fast-forward.

- `bash -n` passed after each fix. shellcheck is not installed.
- `scripts/deploy-metube.sh --smoke video` printed `DEPLOY OK` (exit 0). The drain found no active downloads, the guard pre-check passed, `metube.service` restarted the same container (id 60865e0463a9, StartedAt 19:47:36Z changed to 19:57:25Z), and the container-side hash matched. The pre-existing unprefixed copy was found, so the overwrite check ran, and it found the copy unchanged.
- New smoke file created (delete when no longer needed): `/tank/docker/metube/downloads/audiocom-smoke-video-1793217447.Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best.m4a`
- `scripts/deploy-metube.sh --check` printed `DEPLOY OK` (exit 0), and `metube.service` is active.

---

_Fixed: 2026-10-28T20:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
