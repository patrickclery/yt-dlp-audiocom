---
phase: 03-metube-deploy
verified: 2026-10-28T20:06:32Z
status: passed
score: 12/12 must-haves verified
covered_files:
  - ".planning/phases/03-metube-deploy/03-01-PLAN.md"
  - ".planning/phases/03-metube-deploy/03-01-SUMMARY.md"
  - "README.md"
  - "scripts/deploy-metube.sh"
  - "yt_dlp_plugins/extractor/audiocom.py"
covered_digest: "v3:sha256:2c1a70d2d7506ae7c55284091b49258fed03ed793b9d1f556677c7c4da4870d7"
behavior_unverified: 0
overrides_applied: 3
overrides:
  - must_have: "MUST NOT run sudo from the agent or from scripts/deploy-metube.sh"
    reason: "CR-01: restart must go through metube.service (tank-service-guard, 60 s stop); sudo systemctl restart metube.service is the only sudo the script runs"
    accepted_by: "patrick"
    accepted_at: "2026-10-28T20:01:58Z"
  - must_have: "MUST NOT recreate the metube container or change its mounts or env. Use docker restart only"
    reason: "CR-01 replaced docker restart with metube.service; a compose recreate is reported as ok. Container id observed unchanged (60865e0463a9)"
    accepted_by: "patrick"
    accepted_at: "2026-10-28T20:01:58Z"
  - must_have: "Backstop: parallel or interrupted MeTube downloads of the same track stay independent and an interrupted item is re-extracted on retry"
    reason: "Accepted as untested in 03-UAT.md test 3 (testing needs a MeTube restart). Wiring present: unique custom_name_prefix, msg check, ytdl.py download([self.info.url])"
    accepted_by: "patrick"
    accepted_at: "2026-10-28T20:01:58Z"
re_verification:
  previous_status: human_needed
  previous_score: 11/12
  gaps_closed:
    - "Human items (Plex playback, review-driven prohibition deviations, backstop truth) signed off in 03-UAT.md (status complete, 3/3 pass)"
  gaps_remaining: []
  regressions: []
---

# Phase 3: MeTube Deploy Verification Report

**Phase Goal:** Pasting an audio.com track URL into MeTube produces a playable audio file in the download folder.
**Verified:** 2026-10-28T20:06:32Z
**Status:** passed
**Re-verification:** Yes. The prior report was stale only because 03-01-SUMMARY.md gained `requirements-completed` frontmatter. Its human items are now closed by 03-UAT.md.

## Goal Achievement

Re-checked live and read-only. Container 60865e0463a9 is unchanged (StartedAt 19:57:25Z, the post-fix restart) and metube.service is active. `--check` ends DEPLOY OK. In-container `yt-dlp -v --simulate` on the reference URL lists AudioComIE with the Rumble plugins and extracts the track. All three smoke files plus the reference m4a probe as audio-only with correct tags and a duration of 186.33 s.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: plugin installed 644 next to rumble_fix.py, no rebuild; `yt-dlp -v` lists AudioComIE with the Rumble plugins | ✓ VERIFIED | `cmp` OK, `644 root`, dir = audiocom.py rumble_fix.py. Live `-v --simulate`: rc 0, `Extractor Plugins: AudioComIE, grid (RumbleChannelIE), impersonate (RumbleEmbedIE), impersonate (RumbleIE)`, no `[generic]`, no import error, `AudioCom\|Rusted Pitchfork…\|186.358` |
| 2 | SC2: reference URL in MeTube produces a playable, correctly titled file | ✓ VERIFIED | ffprobe on the 3 smoke files: aac/mp3 audio only, title "Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best", artist "David Oliveira", 186.33 s. Plex playback signed off (03-UAT.md test 1) |
| 3 | SC3: README covers install, update, removal (with `--list-extractors` check) | ✓ VERIFIED | `## MeTube` has `### Install` (l.18), `### Update` (l.62), `### Remove` (l.85), grep check at l.91. Uses `sudo systemctl restart metube.service` (CR-01, accepted) |
| 4 | Installed file byte-identical, 644 root, only audiocom.py and rumble_fix.py | ✓ VERIFIED | As in truth 1; `--check` reports sha256 179cf7f49548 on both sides |
| 5 | Audio mode saves an mp3 | ✓ VERIFIED | `audiocom-smoke-audio-1793216858…mp3`: mp3 stream, tags correct, 186.33 s |
| 6 | MeTube re-extracts at download time from the page URL | ✓ VERIFIED | Prior evidence `/app/app/ytdl.py:937` `download([self.info.url])`; container unchanged since |
| 7 | Script refuses to restart on a missing or differing install | ✓ VERIFIED | Exercised in the prior run (rc 1, StartedAt unchanged); script unchanged in coverage (`bash -n` OK) |
| 8 | Idempotent re-deploy keeps the same container | ✓ VERIFIED | Container Id 60865e0463a9 unchanged; AudioComIE listed once |
| 9 | Guard refuses to restart while an item is downloading | ✓ VERIFIED | Exercised in the prior run (fake /history, sudo shim) |
| 10 | `--check` verifies without restarting and ends DEPLOY OK | ✓ VERIFIED | Live: 9 ok lines, `DEPLOY OK`, rc 0, StartedAt unchanged |
| 11 | `--list-extractors \| grep -ic audiocom` prints 0 with the plugin loaded | ✓ VERIFIED | Live: `0` |
| 12 | Backstop: parallel or interrupted downloads are independent and re-extracted on retry | PASSED (override) | Accepted as untested by patrick, 03-UAT.md test 3 |

**Score:** 12/12 truths verified (1 via override; 0 present, behavior-unverified)

### Prohibitions

| Prohibition | Tier | Result |
|-------------|------|--------|
| No sudo from agent or script | judgment | PASSED (override): `sudo systemctl restart` accepted in 03-UAT.md test 2 |
| Compose, unit and rumble_fix.py unchanged; no `__init__.py` | test | Held: `--check` reports `no __init__.py`, rumble_fix.py present |
| No container recreate; docker restart only | test | PASSED (override): Id unchanged; systemctl path accepted in 03-UAT.md test 2 |
| Pre-existing reference m4a untouched | test | Held: 7169460 bytes, mtime Oct 28 11:34 |
| No upstream PR text or code | judgment | Held (LLM check): grep for PR text in README.md and scripts/ finds none |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `scripts/deploy-metube.sh` | ✓ VERIFIED | `bash -n` OK, runs live, DEPLOY OK |
| `README.md` | ✓ VERIFIED | Install/Update/Remove present |
| `/opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py` | ✓ VERIFIED | Identical to repo, 644 root, loaded |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| deploy-metube.sh | installed audiocom.py | `cmp`/sha256 before restart | WIRED (live --check) |
| deploy-metube.sh | metube container | `docker exec` yt-dlp -v --simulate, sha256sum | WIRED (live --check) |
| deploy-metube.sh | MeTube /add, /history | `custom_name_prefix` POST plus done polling | WIRED (smoke files exist) |
| README.md | deploy-metube.sh | Install and Update steps, `--check` | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Check mode | `scripts/deploy-metube.sh --check` | DEPLOY OK, rc 0 | ✓ PASS |
| Plugin loads in MeTube | `docker exec metube yt-dlp -v --simulate <ref>` | AudioComIE listed, AudioCom extractor, 186.358 s | ✓ PASS |
| Smoke files playable | ffprobe | 4/4 audio-only, correct tags | ✓ PASS |
| Removal check | `--list-extractors \| grep -ic audiocom` | 0 | ✓ PASS |

### Probe Execution

None declared. No `scripts/*/tests/probe-*.sh` files exist.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| METB-01 | 03-01 | Installed next to rumble_fix.py without breaking other plugins | ✓ SATISFIED | Truths 1, 4; both plugin dirs still searched |
| METB-02 | 03-01 | Reference URL in MeTube gives a playable audio file | ✓ SATISFIED | Truths 2, 5; Plex playback in 03-UAT.md |
| METB-03 | 03-01 | README install, update, removal | ✓ SATISFIED | Truth 3 |

No orphaned requirements. REQUIREMENTS.md now marks METB-01..03 Complete, and 03-01-SUMMARY.md declares `requirements-completed: [METB-01, METB-02, METB-03]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | No TBD/FIXME/XXX/TODO/HACK in scripts/deploy-metube.sh or README.md | - | - |

### Human Verification Required

None open. All three items were signed off in `.planning/phases/03-metube-deploy/03-UAT.md` (status complete, 3/3 pass).

### Gaps Summary

No gaps. The phase goal holds on the live system. Housekeeping only: the `audiocom-smoke-*` files are still in /tank/docker/metube/downloads (deletion was part of UAT test 1, not done; not a goal issue).

---

_Verified: 2026-10-28T20:06:32Z_
_Verifier: Claude (gsd-verifier)_
