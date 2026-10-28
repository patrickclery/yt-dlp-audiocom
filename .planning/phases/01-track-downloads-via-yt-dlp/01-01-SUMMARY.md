---
requirements-completed: [EXTR-01, EXTR-02, EXTR-03, PLUG-01]
phase: 01-track-downloads-via-yt-dlp
plan: 01
subsystem: extractor
status: complete
tags: [yt-dlp, plugin, audio.com, oembed, hatchling, walking-skeleton]
requires: []
provides:
  - "AudioComIE plugin (yt_dlp_plugins/extractor/audiocom.py): URL -> oEmbed -> /audio/<id> -> mp3/m4a formats"
  - "hatchling pyproject with editable plugin discovery"
  - "Pinned Python 3.11 venvs: .venv (yt-dlp 2026.10.26), .venv-metube (yt-dlp 2026.8.19)"
  - "tests/test_plugin_loading.py, tests/test_url_matching.py"
affects: [01-02]
tech-stack:
  added: ["yt-dlp==2026.10.26 (.venv)", "yt-dlp==2026.8.19 (.venv-metube)", "pytest==9.1.1", "hatchling==1.32.4 (build backend)"]
  patterns: ["namespace plugin package, no __init__.py", "absolute yt_dlp imports", "monkeypatched _download_json for offline tests"]
key-files:
  created:
    - pyproject.toml
    - .gitignore
    - yt_dlp_plugins/extractor/audiocom.py
    - tests/test_plugin_loading.py
    - tests/test_url_matching.py
  modified:
    - .planning/phases/01-track-downloads-via-yt-dlp/SKELETON.md
decisions:
  - "display_id is the lowercased slug; user and slug are lowercased via _canonical_url before oEmbed"
  - "Task 3 committed as separate RED (test) and GREEN (feat) commits per the canonical TDD reference"
metrics:
  duration: "~2 min"
  completed: 2026-10-28
actuals:
  tokens: 1755
  tasks: 3
  commits: 3
plan_head_before: a27ea92eb94b57910e3dbc84c15509c8ee69e48e
plan_head_after: 3a358eaca16ce1c6607482796a3c27b7bcd333c1
---

# Phase 1 Plan 01: Walking Skeleton Summary

A hatchling-packaged `AudioComIE` yt-dlp namespace plugin resolves audio.com track URLs through `api.audio.com/oembed` and `/audio/<id>` and downloads the m4a via stock yt-dlp, with no impersonation. It loads on yt-dlp 2026.10.26 and 2026.8.19.

## Tasks

| Task | Name | Commit | Result |
|------|------|--------|--------|
| 1 | Package legitimacy gate | n/a | **Approved by human** (relayed by orchestrator) for exactly yt-dlp==2026.10.26, yt-dlp==2026.8.19, pytest==9.1.1, hatchling==1.32.4. Only those pins plus pytest transitives (iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, pygments 2.21.0) were installed |
| 2 | Tracer: reference URL -> m4a | 9563179 | `TRACER OK`. `[AudioCom]` log, no `[generic]`/403, 7.2 MB `1877766681285368.m4a` written to the scratchpad (outside the repo). `test_plugin_loading.py` 2 passed in both venvs |
| 3 (RED) | Failing URL-variant tests | 8e7e4ee | 9 failed / 10 passed against the tracer regex |
| 3 (GREEN) | Variant matching + canonicalization | 3a358ea | 21 passed in both venvs. All 4 live variants print `AudioCom 1877766681285368` |

## Verification

- `.venv/bin/yt-dlp --version` = 2026.10.26, `.venv-metube/bin/yt-dlp --version` = 2026.08.19
- `-v` prints `Extractor Plugins: AudioComIE` with no `Error while importing` in both venvs
- `-F` lists `mp3 192k` and `m4a 306k` audio-only rows
- All Task 2 and Task 3 acceptance greps pass (no `__init__.py`, no `impersonate`/`curl_cffi`/`_download_webpage`/`sources`, no relative imports, no `yt_dlp/` tree, venvs and media gitignored)
- SKELETON.md: ticked scaffold, routing, interface and local run command. Data read (metadata) and data write (embedded metadata) stay open for Plan 01-02

## TDD Gate Compliance

- RED: 8e7e4ee `test(01-01)` failed for the expected reasons (regex rejected variants, accepted embed/ and audio/audio/)
- GREEN: 3a358ea `feat(01-01)`, all 21 tests pass
- REFACTOR: not needed

## Deviations from Plan

**1. [Rule 3 - Blocking] Task 3 split into RED and GREEN commits**
- **Issue:** The plan said to commit the test and extractor change together. The canonical TDD reference and execute-phase's RED-commit gate expect a separate failing-test commit.
- **Fix:** Committed the RED test (8e7e4ee), then the GREEN implementation (3a358ea).

**2. [Rule 3 - Blocking] Plan commit ledger not written to disk**
- **Issue:** The worktree sandbox refuses writes into the shared `.git/worktrees/...` directory, so the protocol 0c ledger file could not be created.
- **Fix:** Used the known spawn base `a27ea92` directly for `plan_head_before` and `git rev-list --count`.

## Known Stubs

None. Metadata fields beyond `title` are out of scope here and owned by Plan 01-02.

## Self-Check: PASSED

- FOUND: pyproject.toml, .gitignore, yt_dlp_plugins/extractor/audiocom.py, tests/test_plugin_loading.py, tests/test_url_matching.py
- FOUND: 9563179, 8e7e4ee, 3a358ea (ancestors of HEAD)
