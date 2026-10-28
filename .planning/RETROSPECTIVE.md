# Retrospective

## Milestone: v1.0 — audio.com plugin MVP

**Shipped:** 2026-10-28
**Phases:** 3 | **Plans:** 6

### What Was Built
- `AudioComIE` yt-dlp plugin: oEmbed → api.audio.com, highest-bitrate mp3/m4a, metadata with fallbacks
- Opt-in `-f original`, newest-upload-only formats, one-line errors, `scripts/test-live.sh` on two yt-dlp versions
- MeTube deploy via `scripts/deploy-metube.sh` (systemd restart through the ZFS guard)

### What Worked
- Early research found the unchallenged API path, so no Cloudflare impersonation was ever needed
- Code review after each phase caught real issues (case-folding URL bypass, signed URLs in logs, restart skipping the ZFS guard)

### What Was Inefficient
- Several locked decisions were corrected by phase research (bitrate sort, `is_public` meaning, field names) — earlier sampling of more tracks would have avoided the churn
- Later-phase edits made earlier verifications stale, forcing a re-verify pass at milestone close

### Patterns Established
- Worktree-isolated executors, TDD commit pairs, redacted fixtures with a hygiene test
- Never AI-author upstream yt-dlp contributions (CONTRIBUTING no-AI policy); plugin-only

### Key Lessons
- Check contribution policies before planning an upstream PR
- Treat restarts of host services through their real unit, not raw `docker restart`

## Cross-Milestone Trends

| Milestone | Phases | Plans | Review blockers | Notes |
|-----------|--------|-------|-----------------|-------|
| v1.0 | 3 | 6 | 1 (phase 3 restart guard) | shipped same day |
