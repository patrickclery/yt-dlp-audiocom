---
phase: 03-metube-deploy
verified: 2026-10-28T20:15:00Z
status: human_needed
score: 11/12 must-haves verified
covered_files:
  - ".planning/phases/03-metube-deploy/03-01-PLAN.md"
  - ".planning/phases/03-metube-deploy/03-01-SUMMARY.md"
  - ".planning/phases/03-metube-deploy/03-CONTEXT.md"
  - ".planning/phases/03-metube-deploy/03-REVIEW-FIX.md"
  - ".planning/phases/03-metube-deploy/03-REVIEW.md"
  - "README.md"
  - "scripts/deploy-metube.sh"
  - "yt_dlp_plugins/extractor/audiocom.py"
covered_digest: "v3:sha256:215e65876616349c882b369971c2c1b02593f16a0c54b573eba3d6039e123af2"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Play the three smoke files in Plex: audiocom-smoke-video-1793216760.*.m4a, audiocom-smoke-video-1793217447.*.m4a and audiocom-smoke-audio-1793216858.*.mp3 in /tank/docker/metube/downloads. Optionally paste the reference URL into the MeTube web UI once with a custom name prefix. Delete the audiocom-smoke-* files afterwards."
    expected: "Each file plays the full ~3:06 track. Title is 'Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best', artist is 'David Oliveira'."
    why_human: "ffprobe and a full ffmpeg decode pass, but Plex playback and indexing cannot be checked from the shell. The smoke runs used MeTube's /add API with the web UI's form fields, not a real paste in the browser."
  - test: "Decide on the prohibitions that the code-review fixes changed. (a) 'MUST NOT run sudo from scripts/deploy-metube.sh': after CR-01, line 217 runs `sudo systemctl restart metube.service`. (b) 'Use docker restart only, container id the same': the restart now goes through compose via metube.service, and line 222 reports a recreated container as ok instead of failing. (c) 'No agent-authored upstream yt-dlp code or PR text' (judgment): non-authoritative check found none."
    expected: "Accept (a) and (b) as superseded by CR-01, or ask for the script to be reverted. Confirm (c)."
    why_human: "These are judgment-tier prohibitions, or test-tier ones whose wording the review fix changed on purpose. Only the user can accept the change."
  - test: "Backstop truth (verification: backstop): parallel or interrupted MeTube downloads of the same track stay independent, and an interrupted item is re-extracted when MeTube retries it from its persisted queue."
    expected: "A second add of a queued URL gets 'Already in queue' (the script fails on any msg, line 348). An item interrupted by a restart resumes and finishes with fresh media URLs."
    why_human: "insufficient_spec: this is a non-inferable backstop truth. Wiring evidence exists (unique prefixes, msg check, download([self.info.url]) at ytdl.py:937), but no test triggers an interrupt or retry, and doing so needs a MeTube restart, which is not allowed here."
---

# Phase 3: MeTube Deploy Verification Report

**Phase Goal:** Pasting an audio.com track URL into MeTube produces a playable audio file in the download folder.
**Verified:** 2026-10-28T20:15:00Z
**Status:** human_needed
**Re-verification:** No (initial verification; post-review-fix code)

## Goal Achievement

The live checks support the goal. MeTube (container 60865e0463a9, unchanged since planning) loads AudioComIE. Its done history has a `finished` entry for the reference URL. The download folder holds three smoke files with aac/mp3 audio, no video, the correct title and artist tags and a duration of 186.33 s, and all three decode cleanly with ffmpeg.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: plugin at /opt/metube/.../audiocom.py, 644, no rebuild; `yt-dlp -v` lists AudioComIE with the Rumble plugins, no import errors | ✓ VERIFIED | Live `docker exec metube yt-dlp -v --simulate <ref>`: rc 0, `Extractor Plugins: AudioComIE, grid (RumbleChannelIE), impersonate (RumbleEmbedIE), impersonate (RumbleIE)`, both plugin dirs listed, `[AudioCom]` lines, no `[generic]` line, no `Error while importing` |
| 2 | SC2: reference URL in MeTube produces a playable, correctly titled file | ✓ VERIFIED | `/history` done entry `audiocom-smoke-video-1793217447…` status finished, download_type video/any/best. ffprobe on all 3 smoke files: one audio stream, title/artist tags correct, 186.33 s. Full ffmpeg decode, no errors. Plex check is listed under human verification |
| 3 | SC3: README covers install, update, removal (with the `--list-extractors` check) | ✓ VERIFIED (deviation) | `## MeTube` has `### Install`, `### Update` (incl. `--check` and `test-live.sh`), `### Remove` (`sudo rm` plus the grep check). Uses `sudo systemctl restart metube.service` instead of the planned `docker restart metube` (CR-01) |
| 4 | Installed file byte-identical, 644 root, only audiocom.py and rumble_fix.py | ✓ VERIFIED | cmp OK; `644 root`; `ls -A` = audiocom.py rumble_fix.py; sha256 179cf7f4… both sides; in-container sha matches |
| 5 | Audio mode saves an mp3 with the same checks | ✓ VERIFIED | `audiocom-smoke-audio-1793216858…mp3`: mp3 stream, tags correct, 186.33 s. Created before WR-04 and not re-run on the new code (the MeTube behavior does not depend on the script) |
| 6 | MeTube re-extracts at download time from the page URL | ✓ VERIFIED | `/app/app/ytdl.py:937` `self._make_youtube_dl(ytdl_params).download([self.info.url])` |
| 7 | Script refuses to restart on a missing or differing install and prints the sudo command | ✓ VERIFIED (deviation) | Ran with a missing path and with a half-written scratch copy (correctly suffixed): each printed `sudo install -m 644 …`, then `DEPLOY FAILED`, rc 1, StartedAt unchanged. The plan's literal `/nonexistent/audiocom.py` now exits 2 with a usage error (WR-02), and still does not restart |
| 8 | Idempotent re-deploy keeps the same container and lists AudioComIE once | ✓ VERIFIED | Container Id equals the planning-time Id after the plan's and the fix's restarts (StartedAt 19:57:25Z matches REVIEW-FIX). AudioComIE listed once. No restart re-run here (not allowed) |
| 9 | Guard refuses to restart while an item is downloading | ✓ VERIFIED | Fake `/history` with 1 downloading item, `AUDIOCOM_DRAIN_TIMEOUT=6`, sudo shimmed to fail: `FAIL: 1 downloads still active after 6s; re-run later or pass --force`, `DEPLOY FAILED`, real StartedAt unchanged |
| 10 | `--check` verifies without restarting and ends DEPLOY OK | ✓ VERIFIED | Live run: 9 ok lines, `DEPLOY OK`, rc 0, StartedAt unchanged |
| 11 | `--list-extractors \| grep -ic audiocom` prints 0 with the plugin loaded | ✓ VERIFIED | Live: `0` |
| 12 | Backstop: parallel or interrupted downloads are independent and re-extracted on retry | ⚠️ insufficient_spec | Wiring is present (unique prefix, msg check line 348, truth 6), but this backstop truth has no explicit test. Routed to human |

**Score:** 11/12 truths verified (0 present, behavior-unverified; 1 insufficient_spec)

### Prohibitions

| Prohibition | Tier | Result |
|-------------|------|--------|
| No sudo from agent or script | judgment | Flagged. The script now runs `sudo systemctl restart` (CR-01). Task 1's sudo was run by the orchestrator, with the user's authorization recorded in CONTEXT. Human decision needed |
| Compose, unit and rumble_fix.py unchanged; no `__init__.py` | test | Held (observed): sha256 95d7398e…, b74f7c20…, cbae6425… match the planning values; `find` finds no `__init__.py` |
| No container recreate; docker restart only | test | Id unchanged (held). "docker restart only" was superseded by CR-01, and the script now accepts a recreate. Flagged for human |
| Pre-existing reference m4a untouched | test | Held: 7169460 bytes, sha256 0e3d145a…d5b6, mtime 11:34:22 -0600 |
| No upstream PR text or code | judgment | Non-authoritative: none found in README.md or scripts/. Flagged for confirmation |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `scripts/deploy-metube.sh` | install check, guarded restart, load checks, smoke, --check | ✓ VERIFIED | 427 lines, `bash -n` OK, contains `DEPLOY OK`, runs live |
| `README.md` | `## MeTube` install/update/remove | ✓ VERIFIED | Present and matches the script's current behavior |
| `/opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py` | installed plugin | ✓ VERIFIED | Identical to the repo, 644 root, loaded in the container |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| deploy-metube.sh | installed audiocom.py | `cmp -s` (line 129) plus mode check before restart | WIRED (exercised) |
| deploy-metube.sh | metube container | `docker exec` yt-dlp -v --simulate, sha256sum (lines 258, 269) | WIRED (exercised by --check) |
| deploy-metube.sh | MeTube /add, /history | `custom_name_prefix` POST plus done polling (lines 343-366) | WIRED (finished done entry for the post-fix smoke) |
| README.md | deploy-metube.sh | Install and Update steps, `--check` | WIRED |

### Data-Flow Trace (Level 4)

Not applicable (no rendered UI). The data path is reference URL → MeTube /add → yt-dlp AudioComIE → file in /tank/docker/metube/downloads, and it was traced through the history entry and ffprobe tags.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Plugin loads in MeTube | `docker exec metube yt-dlp -v --simulate <ref>` | AudioComIE listed, `AudioCom\|Rusted Pitchfork…\|186.358\|David Oliveira` | ✓ PASS |
| Check mode | `scripts/deploy-metube.sh --check` | DEPLOY OK, rc 0 | ✓ PASS |
| Restart guard | fake /history, sudo shim | DEPLOY FAILED, StartedAt unchanged | ✓ PASS |
| Stale install refusal | scratch AUDIOCOM_INSTALL_PATH | prints sudo install, rc 1 | ✓ PASS |
| Smoke files playable | ffprobe plus `ffmpeg -v error -f null` | 3/3 clean | ✓ PASS |

### Probe Execution

None declared. No `scripts/*/tests/probe-*.sh` files exist.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| METB-01 | 03-01 | Installed next to rumble_fix.py without breaking it or other plugins | ✓ SATISFIED | Truths 1 and 4; bgutil site-packages dir still searched; rumble sha unchanged |
| METB-02 | 03-01 | Reference URL in MeTube gives a playable audio file | ✓ SATISFIED (Plex pending) | Truths 2 and 5; the paste through the UI itself and Plex playback are human items |
| METB-03 | 03-01 | README install, update, removal | ✓ SATISFIED | Truth 3 |

No orphaned requirements. REQUIREMENTS.md still shows METB-01..03 as Pending, so the traceability table needs updating.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | No TBD/FIXME/XXX/TODO/HACK in scripts/deploy-metube.sh or README.md | - | - |
| scripts/deploy-metube.sh | 222 | A container recreate is reported as ok | ℹ️ Info | Removes the plan's no-recreate enforcement; part of the prohibition decision |

### Human Verification Required

1. **Plex playback.** Play the 3 `audiocom-smoke-*` files in Plex (optionally also paste the URL in the MeTube web UI). Expected: full track, title "Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best", artist "David Oliveira". Then delete the smoke files.
2. **Prohibition changes from the review fixes.** Accept or reject: the script now runs `sudo systemctl restart metube.service`, and the restart goes through compose instead of `docker restart`. Confirm that no upstream PR text was added.
3. **Backstop truth 12.** Interrupted or parallel downloads of the same track. Needs a restart to test.

If you accept item 2, these overrides record the deviations (add to frontmatter):

```yaml
overrides:
  - must_have: "MUST NOT run sudo from the agent or from scripts/deploy-metube.sh"
    reason: "CR-01: restart must go through metube.service (tank-service-guard, 60 s stop); systemctl restart is the only sudo"
    accepted_by: "patrick"
    accepted_at: "<ISO timestamp>"
  - must_have: "MUST NOT recreate the metube container or change its mounts or env. Use docker restart only"
    reason: "CR-01 replaced docker restart with metube.service; container id observed unchanged"
    accepted_by: "patrick"
    accepted_at: "<ISO timestamp>"
```

### Gaps Summary

No blocking gaps. The phase goal holds in the live system. The open items are the Plex check, the user's decision on the review-driven deviations from the plan's prohibitions (sudo systemctl in the script, compose restart instead of docker restart), and one backstop truth that cannot be tested without a restart.

---

_Verified: 2026-10-28T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
