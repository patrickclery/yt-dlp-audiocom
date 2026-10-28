---
status: testing
phase: 03-metube-deploy
source: [03-VERIFICATION.md]
started: 2026-10-28T20:01:58Z
updated: 2026-10-28T20:01:58Z
---

## Current Test

number: 1
name: Plex playback of the audiocom-smoke-* files
expected: |
  All three smoke files play in Plex with correct title/artist (~3:06); then delete them
awaiting: user response

## Tests

### 1. Plex playback of smoke files
expected: Plays, correct tags
result: [pending]

### 2. Accept review-driven deviations (sudo systemctl restart via unit/guard; compose-recreated container reported OK)
expected: Accepted
result: [pending]

### 3. Interrupted/parallel downloads of same track (untested — needs restart)
expected: Accept as untested
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
