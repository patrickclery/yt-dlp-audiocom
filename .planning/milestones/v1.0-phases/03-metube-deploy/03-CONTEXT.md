# Phase 3: MeTube Deploy - Context

**Gathered:** 2026-10-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Install the Phase 1–2 `AudioComIE` plugin into the running MeTube container (no image rebuild), prove that a reference audio.com URL submitted to MeTube lands as a playable, correctly titled file in the download folder, and document install / update / removal in the README.

</domain>

<decisions>
## Implementation Decisions

### Deploy mechanism (user-decided)
- Copy, not symlink: `sudo install -m 644 yt_dlp_plugins/extractor/audiocom.py /opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py`. `/opt/metube/plugins` is root-owned → the user authorized the agent (2026-10-28) to run this `sudo install` directly (passwordless sudo available); NOT a human checkpoint
- Updating = re-run the same `sudo install` command, then restart
- Do NOT add any `__init__.py` under `/opt/metube/plugins/yt_dlp_plugins/` (would shadow MeTube's bgutil plugin); do NOT modify or remove `rumble_fix.py`
- Do NOT edit `/opt/metube/docker-compose.yml` or the `metube.service` unit — the existing `/opt/metube/plugins:/plugins:ro` mount and `PYTHONPATH=/plugins` already cover it

### Restart (user-approved)
- The agent may restart MeTube after the file is installed: `docker restart metube` (docker group access, no sudo; mounts/env unchanged). Brief downtime is accepted

### Verification
- `docker exec metube yt-dlp -v --simulate <reference URL>` must list AudioComIE together with the existing extractor plugins (rumble_fix) and show no "Error while importing"
- Submit the reference URL to MeTube the way the web UI does (MeTube HTTP API `POST /add` on the container's published port, or the user pasting it in the UI) and confirm a file with the correct title appears in `/tank/docker/metube/downloads`. A pre-existing copy of the same track already sits there from Phase 1 UAT — the plan must handle that (e.g. check a fresh file/mtime, or move the old copy aside with the user's knowledge)
- Final playback check in Plex is a human verification item

### README (METB-03)
- Sections: MeTube install (sudo install + docker restart + -v check), update (same command), removal (`sudo rm` the file + restart once bundled yt-dlp ships a built-in `[audiocom]` extractor — check with `docker exec metube yt-dlp --list-extractors | grep -i audiocom`)

### Claude's Discretion
- Exact README wording, whether to add a small `scripts/deploy-metube.sh` that prints the sudo command and performs the non-sudo steps

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `yt_dlp_plugins/extractor/audiocom.py` (final Phase 2 version), `scripts/test-live.sh`, README with dev/test/originals/errors sections
- MeTube: container `metube`, image `ghcr.io/alexta69/metube:latest`, bundled yt-dlp 2026.8.19 (Phase 2 verified compatibility), compose at `/opt/metube/docker-compose.yml`, systemd `metube.service` (oneshot, ZFS-guarded)

### Integration Points
- Host `/opt/metube/plugins` → container `/plugins` (ro), `PYTHONPATH=/plugins`; downloads `/tank/docker/metube/downloads` → `/downloads` (Plex section indexes it)

</code_context>

<specifics>
## Specific Ideas

- Reference URL: https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best
- Note MeTube auto-updates (`:latest`) can bump yt-dlp; README should tell the user to re-run `scripts/test-live.sh` after a MeTube image update

</specifics>

<deferred>
## Deferred Ideas

- Automating deploy via chezmoi/compose — user chose plain sudo install
- Collections/profiles — v2

</deferred>
