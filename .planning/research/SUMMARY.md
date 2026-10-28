# Project Research Summary

**Project:** audio-com-downloader
**Domain:** yt-dlp extractor plugin for single audio.com tracks, delivered to MeTube
**Researched:** 2026-10-28
**Confidence:** HIGH overall for the plugin path; MEDIUM on breadth (one reference track inspected)

## Scope Decision (binding)

Agent-built scope is the **yt-dlp plugin only**: a standalone repo plus the MeTube deploy. yt-dlp's CONTRIBUTING forbids LLM/agent-authored patches and PR text. No agent produces upstream `yt_dlp/extractor/audiocom.py`, `_extractors.py` edits, PR descriptions, issues, or review replies. If Patrick upstreams it later, he hand-writes that himself. The STACK and PITFALLS files recommend the same split; ARCHITECTURE's "canonical upstream file + generated plugin" design is rejected, because it makes the agent write upstream-style code. The plugin is written directly with absolute `yt_dlp.*` imports.

## Executive Summary

audio.com is a small, legitimate audio host. Its track data is reachable without authentication, and the one hard obstacle, a Cloudflare challenge, applies only to the HTML pages. The recommended approach is a single yt-dlp `InfoExtractor` plugin that uses only the unchallenged API host: `api.audio.com/oembed` resolves the slug URL to a numeric track id, and `api.audio.com/audio/<id>` returns the metadata and signed `transcodings[]` URLs (mp3 and m4a). Impersonation (`curl_cffi`) is not needed on this path and stays out of the default design.

The plugin loads through the MeTube container's existing `PYTHONPATH=/plugins` mount, with no image rebuild. The main risks are plugin-loading failures that are silent by design, undocumented endpoint drift, and the naming collision that would happen if the plugin shadowed a future upstream extractor. All three are manageable with a version-matrix smoke test, a removal header, and a plugin-only scope. Upstream policy risk is removed by keeping agents out of upstream work entirely.

## Key Findings

### Recommended Stack

The runtime is the container's bundled yt-dlp (2026.08.19) on Python 3.13, with the same code tested against yt-dlp 2026.10.26. Nothing new needs to be installed.

- `yt_dlp.extractor.common.InfoExtractor` (absolute import in the plugin): base class; `_VALID_URL`, `_real_extract`, `_download_json`.
- `yt_dlp.utils` helpers (`traverse_obj`, `int_or_none`, `url_or_none`, `ExtractorError`): lenient field extraction and clean expected errors.
- Plugin namespace layout `yt_dlp_plugins/extractor/audiocom.py` with no `__init__.py`: the only layout that coexists with MeTube's existing plugins.
- `curl_cffi` (already in the image, 0.16.3): **not used** on the primary path. Optional fallback only.
- Write for Python 3.11 syntax so the plugin stays portable; it runs on 3.13 in the container.

Notes: the plugin API has no compatibility guarantee, so re-test after each yt-dlp bump. Use `ext` from MIME/`format` (`mp3`, `m4a`), never from signed URL paths.

### Expected Features

Prior art: none. No audio.com extractor, issue, or plugin exists in yt-dlp or elsewhere, so the plugin is greenfield.

**Must have (table stakes):**
- `_VALID_URL` for `audio.com/<user>/audio/<slug>` (with or without `www`, trailing slash, query string). Must not match `/collections/`, profiles, or `/embed/`.
- Track id, title, display_id (slug), uploader, uploader_id (username), uploader_url.
- Two formats, `mp3` (`play`) and `m4a` (`playhq`), each with `vcodec: 'none'`, correct `ext`, and `acodec`.
- Duration in seconds (source is milliseconds); timestamp from `created`.
- Non-fatal thumbnail and description, mapped to `None` when empty.
- Clean `ExtractorError(expected=True)` for missing, deleted, or private tracks.

**Should have (cheap differentiators, same JSON):** `view_count`, `like_count`, `comment_count`, `repost_count` from `stats`; `tags`; `modified_timestamp`; `license` when set.

**Defer (v2+):** collections and profile pages; lossless WavPack source (core yt-dlp does not allow `.wv`, and the source is only emitted when `is_downloadable` is true); embed-URL support beyond the oEmbed resolver; page-based fallback using impersonation; per-format `filesize` probes.

### Architecture Approach

A three-step flow with two unchallenged API calls per track and no HTML scraping.

1. Match the URL and rebuild the canonical form `https://audio.com/<user>/audio/<slug>` from regex groups. oEmbed rejects `www.`, trailing slashes, query strings, and uppercased usernames (measured 404).
2. `GET https://api.audio.com/oembed?url=<canonical>`; regex `/embed/audio/(\d+)` on `iframe_url` gives the numeric id.
3. `GET https://api.audio.com/audio/<id>`; map `transcodings[]` to formats; emit `sources[]` only when `is_downloadable` is true; map the rest to the info dict.

Media is served from `s3.ustatik.com` as pre-signed SigV4 URLs (6-day expiry), downloaded with yt-dlp's normal HTTP downloader. No Referer, cookies, or impersonation needed.

Components: (1) `AudioComIE._VALID_URL` and URL normalizer; (2) oEmbed ID resolver; (3) track fetcher; (4) format and metadata mapper; (5) error mapper (404 to `ExtractorError(expected=True)`).

### Critical Pitfalls

1. **Agent-authored upstream work violates yt-dlp's NO AI policy.** Violators can be blocked without warning, and the PR template requires an honest attestation. Avoid: keep all upstream code, PR text, and issue text out of agent scope.
2. **Plugin silently shadows a future upstream extractor.** Plugin classes take priority by name. Avoid: keep the class name `AudioComIE`, add a header stating the removal condition ("delete when bundled yt-dlp includes `[audiocom]`"), and check `-v` after every yt-dlp upgrade.
3. **Plugin fails to load and the user sees a generic 403.** Import errors go to stderr and are skipped. Avoid: deploy exactly `yt_dlp_plugins/extractor/audiocom.py`, mode 644, no `__init__.py`. Smoke-test `-v` for "Extractor Plugins" and the absence of "Error while importing"; confirm the bgutil and rumble plugins still load.
4. **Wrong JSON or wrong units.** The page's first JSON-LD block is the site Organization, and `duration` is milliseconds. Avoid: use the API, not the page; divide duration by 1000; anchor every field on an explicit path; check the returned `id` matches the requested track.
5. **Signed URLs expire (6 days) and cached info dicts go stale.** Avoid: do not cache info dicts; re-extract on each download run.
6. **Honoring `is_downloadable`.** The API returns WavPack source URLs even when `is_downloadable` is false. Avoid: emit `sources[]` only when `is_downloadable is True`.

## Implications for Roadmap

Suggested phase structure (plugin-only scope):

### Phase 1: Policy Gate and Scope Lock
- **Rationale:** The upstream policy decides what agents may touch. Record it before any code.
- **Delivers:** Key Decision recorded; repo layout `plugin/yt_dlp_plugins/extractor/audiocom.py`, tests, deploy note. No `_extractors.py` edits and no upstream-style `audiocom.py`.
- **Avoids:** Pitfall 1.

### Phase 2: API Contract Fixtures
- **Rationale:** Every later phase depends on the exact JSON shape. Only one track has been inspected.
- **Delivers:** Redacted recorded fixtures for `oembed` and `audio/<id>` covering at least five tracks: `is_downloadable` true and false, with and without artwork, with and without description. Signatures and any `app.*` config values stripped.
- **Avoids:** Pitfalls 4 and 5.

### Phase 3: Plugin Extractor
- **Rationale:** The core deliverable. With fixtures, parsing is deterministic and testable offline.
- **Delivers:** `audiocom.py` with `AudioComIE`, absolute imports, tight `_VALID_URL`, URL canonicalization, oEmbed ID resolution, track fetch, `mp3`/`m4a` formats with `vcodec: 'none'`, sources gated on `is_downloadable`, metadata, `expected=True` errors. Offline tests against fixtures; live checks by hand.
- **Avoids:** Pitfalls 2, 4, 5, 6.

### Phase 4: MeTube Deploy and Acceptance
- **Rationale:** The plugin is useless until it runs in the container.
- **Delivers:** File at `/opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py` (mode 644). Verified with `docker exec metube yt-dlp -v --simulate <url>`: AudioComIE listed, no import errors, rumble and bgutil still load. Download verified, including the no-thumbnail case.
- **Avoids:** Pitfall 3.

### Phase 5: Version Matrix and Maintenance
- **Rationale:** The plugin must not silently break after an image update or yt-dlp upgrade.
- **Delivers:** Smoke test against bundled 2026.08.19 and latest stable 2026.10.26; removal checklist; documented fallback plan if oEmbed or `api.audio.com/audio/<id>` changes.

### Phase Ordering Rationale
- Policy first, because it constrains everything else.
- Fixtures before the extractor, because the JSON contract is the largest unknown.
- Extractor before deploy, because deploy needs a working file.
- Version matrix last, because it needs a deployed baseline.

### Research Flags
- **Phase 2 needs research:** field presence varies across tracks; private and unlisted behavior unknown.
- **Phase 5 needs research only if the API path breaks.**
- **Phases 3–4 are standard.**

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against yt-dlp master and the live MeTube container. |
| Features | MEDIUM-HIGH | Prior art search conclusive (none); field set from one reference track. |
| Architecture | HIGH | Endpoints probed live; prototype downloaded the reference track end to end. |
| Pitfalls | HIGH | Plugin loading and policy verified in source; review-latency figures a biased sample. |

**Overall:** HIGH for the plugin path, conditional on sampling more tracks.

### Gaps to Address
- **Breadth of track data:** sample at least five tracks before the mapping is final.
- **Private and unlisted tracks:** behavior unknown; map to `ExtractorError(expected=True)`.
- **`.wv` source ext:** rejection inferred from source reading; default is no source emission.
- **oEmbed stability:** undocumented for this use; note fallback plan in plugin header.
- **Signed URL lifetime:** 6-day expiry observed; confirm MeTube queue behavior.

## Sources

**Primary (HIGH):** yt-dlp master (CONTRIBUTING.md, PULL_REQUEST_TEMPLATE.md, plugins.py, extractor/common.py, extractor/whyp.py, extractor/_extractors.py); live MeTube container inspection; live probes of `api.audio.com/oembed`, `api.audio.com/audio/<id>`, and `s3.ustatik.com` (2026-10-28).

**Secondary (MEDIUM):** yt-dlp GitHub PR history for review latency and AI-policy enforcement; iamcal/oembed `providers/audiocom.yml`.

**Tertiary (LOW):** private/unlisted track behavior; `.wv` rejection by core utils.

---
*Research completed: 2026-10-28*
*Ready for roadmap: yes (plugin-only scope)*
