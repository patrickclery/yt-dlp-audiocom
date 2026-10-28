---
status: testing
phase: 01-track-downloads-via-yt-dlp
source: [01-VERIFICATION.md]
started: 2026-10-28T17:36:49Z
updated: 2026-10-28T17:36:49Z
---

## Current Test

number: 1
name: Playback of downloaded reference track
expected: |
  /tmp/claude-1000/-home-patrick-github-com-patrickclery-audio-com-downloader/b3b4fecb-6dde-482c-aee9-1603f83e8e2d/scratchpad/verify-dl/new/1877766681285368.m4a plays ~3:06 with correct title/artist
awaiting: user response

## Tests

### 1. Playback of downloaded reference track
expected: File plays ~3:06, player shows title "Rusted Pitchfork..." and artist David Oliveira
result: [pending]

### 2. Backstop truth: extractor has no mutable state / file I/O
expected: Accept code-read evidence (no enforcing test)
result: [pending]

### 3. Prohibitions without enforcing tests (no upstream code, no committed audio, no ~/.config writes)
expected: Accept verifier's clean inspection
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
