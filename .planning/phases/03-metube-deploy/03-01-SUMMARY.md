---
requirements-completed: [METB-01, METB-02, METB-03]
phase: 03-metube-deploy
plan: 01
subsystem: deploy
tags: [metube, docker, yt-dlp-plugin, deploy-script, readme]
status: complete
requires:
  - phase: 02
    provides: final yt_dlp_plugins/extractor/audiocom.py (sha256 179cf7f49548...)
provides:
  - AudioComIE loaded in the running MeTube container next to the Rumble plugins
  - scripts/deploy-metube.sh (install check, restart guard, restart, load checks, --check, --force, --smoke video|audio)
  - README ## MeTube section (Install, Update, Remove)
affects: [MeTube container metube, /tank/docker/metube/downloads]
tech-stack:
  added: []
  patterns: [capture-then-grep under pipefail, one ok/FAIL line per step, unique custom_name_prefix per smoke run]
key-files:
  created:
    - scripts/deploy-metube.sh
  modified:
    - README.md
decisions:
  - "Task 1 sudo install was run by the orchestrator with the user's authorization (CONTEXT updated 2026-10-28); the script itself still never runs sudo"
  - "Restart guard counts only queue items in preparing/downloading/postprocessing; pending/queued/scheduled persist across restart"
  - "Install-command line printed with printf %q so paths with spaces stay copy-pasteable (identical output for plain paths)"
metrics:
  duration: ~25 min
  completed: 2026-10-28
actuals:
  tokens: 4800
  tasks: 3
  commits: 2
plan_head_before: f59d49cdc8e815c43fb582e0bcd78bb02aec0695
plan_head_after: a5ef9139cdfdd2b71137dc821a37fb76c72d3417
---

# Phase 3 Plan 01: MeTube Deploy Summary

AudioComIE now loads in the running MeTube (no image rebuild, same container), and MeTube turns the reference audio.com URL into correctly tagged m4a (video mode) and mp3 (audio mode) files. A repeatable `scripts/deploy-metube.sh` handles the guarded restart and checks, and the README covers install, update and removal.

## Tasks

| Task | Name | Commit | Result |
|------|------|--------|--------|
| 1 | Install plugin into /opt/metube/plugins (sudo) | completed by orchestrator | `INSTALLED`: cmp-identical, 644 root, dir holds only audiocom.py + rumble_fix.py, no __init__.py, rumble_fix sha256 unchanged |
| 2 | Tracer: deploy script, restart, load check, video smoke | 7cae0a7 | `TRACER OK`, `SC1 OK`, `FRESH FILE OK`, `STALE INSTALL REFUSED`, `BOUNDARIES OK` |
| 3 | Guard, --check, --force, audio smoke, README | a5ef913 | `REDEPLOY OK`, `CHECK MODE OK`, `GUARD HOLDS`, `AUDIO MODE OK`, `REMOVAL CHECK SOUND`, `README OK`, `SCRIPT BOUNDARIES OK` |

In-container `-v` line after deploy: `Extractor Plugins: AudioComIE, grid (RumbleChannelIE), impersonate (RumbleEmbedIE), impersonate (RumbleIE)`; `Plugin directories: /plugins/yt_dlp_plugins, /usr/local/lib/python3.13/site-packages/yt_dlp_plugins`. Container id unchanged (60865e0463a9...) across both restarts. Compose file, metube.service and rumble_fix.py keep their planning sha256; the pre-existing `Rusted Pitchfork ... .m4a` is unchanged (7169460 bytes, sha256 0e3d145a...).

## Test downloads (left for the Plex check; delete afterwards)

- `/tank/docker/metube/downloads/audiocom-smoke-video-1793216760.Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best.m4a` (aac, no video, title/artist tags correct, ~186 s)
- `/tank/docker/metube/downloads/audiocom-smoke-audio-1793216858.Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best.mp3` (mp3, same checks)

## Pending human check

Play both files in Plex: title "Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best", artist David Oliveira. Then delete the `audiocom-smoke-*` files.

## Deviations from Plan

**1. [Checkpoint resolution] Task 1 sudo install run by the orchestrator, not the user.** The plan's prohibition said the agent never runs sudo; the user authorized it and CONTEXT records that. This executor ran no sudo; it only confirmed Task 1's acceptance checks.

**2. [Rule 3 - Blocking] GUARD verify used system `python3 -I` for the fake /history server.** The worktree has no gitignored `.venv`, so the plan's `.venv/bin/python` command could not start the server. That first attempt still exercised the script's other guard branch correctly (`FAIL: MeTube not answering at .../history; pass --force to restart anyway`, DEPLOY FAILED, no restart). The re-run with python3 printed `FAIL: 1 downloads still active after 10s; ...` and `GUARD HOLDS`. No script change.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: scripts/deploy-metube.sh (mode 100755), README.md `## MeTube`
- FOUND: commits 7cae0a7, a5ef913 on HEAD
- FOUND: both test downloads listed above
