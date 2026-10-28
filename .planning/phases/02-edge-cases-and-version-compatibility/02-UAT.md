---
status: testing
phase: 02-edge-cases-and-version-compatibility
source: [02-VERIFICATION.md]
started: 2026-10-28T19:21:25Z
updated: 2026-10-28T19:21:25Z
---

## Current Test

number: 1
name: Accept backstop truth (no shared state across parallel/resumed extractions)
expected: |
  Accept code-read evidence; optionally run parallel extractions / interrupt a -f original download
awaiting: user response

## Tests

### 1. Backstop truth: parallel extractions and interrupted -f original download behave
expected: No cross-talk; resumed download completes
result: [pending]

### 2. No login or credentials used (D-07)
expected: Confirmed
result: [pending]

### 3. MeTube untouched in Phase 2
expected: /opt/metube/plugins unchanged (only rumble_fix.py)
result: [pending]

### 4. No way to bypass is_downloadable
expected: Original never offered for non-downloadable tracks
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
