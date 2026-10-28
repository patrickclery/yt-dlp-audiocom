# Phase 1: Track Downloads via yt-dlp - Research

**Researched:** 2026-10-28
**Domain:** yt-dlp extractor plugin (Python, `InfoExtractor`), audio.com public API, pytest offline/live testing
**Confidence:** HIGH (every claim about the API, plugin loading, packaging and test harness was exercised live this session on both yt-dlp 2026.8.19 and 2026.10.26)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Repo layout & tooling
- Plugin file lives at repo root: `yt_dlp_plugins/extractor/audiocom.py` (namespace package — NO `__init__.py` in `yt_dlp_plugins/` or `yt_dlp_plugins/extractor/`), so the same tree can be bind-mounted into MeTube or pip-installed
- `pyproject.toml` so `pip install -e .` registers the plugin locally (yt-dlp as dev dependency, not a hard runtime pin)
- Plugin-only code with absolute `yt_dlp.*` imports. No upstream-style `yt_dlp/extractor/audiocom.py`, no generator script, no `_extractors.py` edits — yt-dlp CONTRIBUTING forbids LLM/agent-authored contributions
- Tests: pytest offline tests against redacted recorded fixtures (≥5 tracks) + `_TESTS` in the extractor for live checks

#### Extraction behavior
- Data path: canonicalize URL from regex groups → `GET https://api.audio.com/oembed?url=<canonical>` → parse id from `iframe_url` (`/embed/audio/(\d+)`) → `GET https://api.audio.com/audio/<id>`. No HTML page fetch, no impersonation
- Formats from `transcodings[]` (mp3 ~192k, m4a ~306k) with `abr`, `acodec`, `ext`, `vcodec: 'none'`; let yt-dlp's default sort choose (m4a wins on bitrate). Derive ext from format/MIME, never from signed URL path
- Include `view_count`, `like_count`, `comment_count`, `repost_count`, `tags` in Phase 1 when present (same JSON)
- Fixtures: strip URL signatures (`X-Amz-*` query params) and any tokens/keys; keep only fields the extractor reads
- `duration` from API is milliseconds → divide by 1000; `timestamp` from `created`
- Do NOT emit `sources[]` in Phase 1 (gating on `is_downloadable` is Phase 2, EXTR-04)

### Claude's Discretion
- Exact `_VALID_URL` regex shape (must reject `/collections/`, profile pages, `/embed/`), helper structure, test file organization

### Deferred Ideas (OUT OF SCOPE)
- Original-file `sources[]` gated on `is_downloadable` — Phase 2
- Error mapping for private/removed tracks — Phase 2
- Collections, profiles, embed URLs — v2
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXTR-01 | audio.com single-track URL (with/without `www.`, trailing slash, query) matched by `AudioCom` | Regex in Code Examples verified against 6 positive and 6 negative URL forms; default `IE_NAME` gives `[AudioCom]` |
| EXTR-02 | Track ID resolved from slug via oEmbed on canonicalized URL, no impersonation | oEmbed returned 200 for 11/11 sampled tracks with a Firefox UA and yt-dlp's default UA; lowercasing fixes uppercase input (raw uppercase is 404) |
| EXTR-03 | mp3 and m4a formats from transcodings with ext/abr/acodec | `transcodings[]` shape table below; `-F` output captured; older tracks have **mp3 only** (see Pitfall 1) |
| EXTR-05 | title, uploader, uploader_id/url, duration (s), upload date; optional thumbnail/description/tags/counts | Field map below; `author_name` is empty on 3/11 tracks (Pitfall 3); top-level `duration` does not exist (Pitfall 2) |
| PLUG-01 | Installable plugin, namespace package, absolute imports | Discovery tested across 5 install modes; **setuptools default editable install is NOT discovered** (Pitfall 4); hatchling editable is |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- `./.claude/CLAUDE.md` is GSD-generated project context (PROJECT/STACK). Actionable directives: Python + `InfoExtractor` API; must load in MeTube's bundled yt-dlp (2026.08.19) via volume mount without image rebuild; no new hard dependencies; never import `curl_cffi`; write for Python 3.11 syntax; plugin imports must be absolute; keep import-time work at zero; class name `AudioComIE`.
- **Superseded by STATE/CONTEXT:** CLAUDE.md's stack section still talks about upstream hatch/ruff/autopep8 and PR workflow. Those are out of scope: plugin only, no upstream code or PR text.
- Global user CLAUDE.md: files under `~/.config/` are chezmoi-managed. Do not write a yt-dlp config into `~/.config/yt-dlp/`. Use repo-local venvs and `PYTHONPATH`/editable installs instead.

## Summary

The oEmbed → `api.audio.com/audio/<id>` path works, with no impersonation, on both target yt-dlp versions. A refined plugin skeleton (Code Examples) was run this session as a plugin under 2026.8.19 and 2026.10.26. It showed up in `-v` as `Extractor Plugins: AudioComIE`, listed mp3+m4a in `-F` with `vcodec` "audio only", passed 11 offline fixture tests on both versions, and passed its own `_TESTS` through yt-dlp's real `test/test_download.py` harness on both versions. A full download of a sampled m4a matched the API `size` byte for byte, and ffprobe confirmed AAC. [VERIFIED: live runs in scratch venvs, 2026-10-28]

The 11-track sample turned up five facts that contradict or refine the CONTEXT/ARCHITECTURE assumptions. The planner must account for them:
1. Tracks from 2023-2024 have **only an mp3 transcoding (320k)**. No m4a.
2. The default sort picks m4a because of **acodec rank, not bitrate**. On one track it picks a **9 kbps** m4a over a 160 kbps mp3.
3. There is **no top-level `duration`**. It only exists per transcoding/source.
4. The timestamp field in `/audio/<id>` is **`date_created`**, not `created`. `created` is the search-API model's field.
5. `author_name` is often an empty string.

On packaging, setuptools' default `pip install -e .` installs an import-hook finder that yt-dlp's plugin scanner cannot see. Use **hatchling**: its editable install writes a plain path `.pth` and was discovered on both versions.

**Primary recommendation:** Build the single file `yt_dlp_plugins/extractor/audiocom.py` from the verified skeleton below, with a hatchling `pyproject.toml`. Add offline pytest that monkeypatches `AudioComIE._download_json` with ≥8 redacted fixtures. Run live `_TESTS` through a 5-line wrapper that calls `yt_dlp.plugins.load_all_plugins()` before invoking the version-matched yt-dlp `test/test_download.py`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| URL matching + canonicalization | Plugin (`_VALID_URL`, `_real_extract`) | — | Pure string work; oEmbed is strict, so normalize before any request |
| Slug → numeric id | External API (`api.audio.com/oembed`) | Plugin (regex on `iframe_url`) | Only unchallenged slug resolver |
| Track metadata + signed media URLs | External API (`api.audio.com/audio/<id>`) | — | Single JSON source of truth |
| Format/metadata mapping | Plugin | yt-dlp core (sorting, `upload_date` from `timestamp`) | yt-dlp derives `upload_date` and picks the best format |
| Media download | yt-dlp HTTP downloader → `s3.ustatik.com` | — | Pre-signed HTTPS, Range OK, no headers needed |
| Plugin discovery | yt-dlp `plugins.py` (sys.path scan) | Packaging (`.pth`/PYTHONPATH) | Only directory paths on sys.path are scanned |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| yt-dlp | `2026.8.19` (MeTube) and `2026.10.26` (stable) — dev/test only, not a runtime dep | `InfoExtractor`, `traverse_obj`, utils, test harness | Target runtime itself [VERIFIED: PyPI JSON; container `yt-dlp --version` = 2026.08.19] |
| Python | 3.11 (dev venvs) | Interpreter | 2026.10.26 `Requires-Python: >=3.11`; 2026.8.19 `>=3.10` [VERIFIED: installed dist-info METADATA]. MeTube runs 3.13.15 [VERIFIED: docker exec] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | `9.1.1` (pin; 9.2.0 is <24h old) | Offline + live tests | Always |
| hatchling | `1.32.4` (pin in `build-system.requires`; 1.33.0 is <24h old) | Build backend | `pip/uv install -e .` that yt-dlp can discover |
| uv | 0.11.14 (host) | venv + installs | Dev environment |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hatchling | setuptools `find_namespace:` (what yt-dlp-sample-plugins uses) | Works for **non-editable** installs, but `pip install -e .` needs `--config-settings editable_mode=compat`. Without it the plugin is silently not discovered (verified). It also litters `build/` and `*.egg-info` in the repo root |
| editable install | `PYTHONPATH=<repo>` | Works (verified); this is exactly how MeTube loads it. Fine as the CLI smoke-test path |
| sdist test harness | `git clone --depth 1 --branch 2026.10.26 https://github.com/yt-dlp/yt-dlp` | Same files. Git tags are zero-padded (`2026.08.19`) while PyPI versions are not (`2026.8.19`) [VERIFIED: git ls-remote, PyPI] |

**Installation (two pinned venvs, Python 3.11):**
```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python 'yt-dlp==2026.10.26' 'pytest==9.1.1' -e .
uv venv .venv-metube --python 3.11
uv pip install --python .venv-metube/bin/python 'yt-dlp==2026.8.19' 'pytest==9.1.1' -e .
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| yt-dlp | PyPI | since 2021; latest release 2026-10-26 | seam: unknown | seam: none (actually github.com/yt-dlp/yt-dlp; tag SHAs verified via git ls-remote) | [SUS] (too-new, unknown-downloads, no-repository) | Flagged. This is the target program itself, already running in MeTube. Pin exact versions |
| pytest | PyPI | since 2010, 193 releases; 9.2.0 published 2026-10-27 | seam: unknown | github.com/pytest-dev/pytest | [SUS] (too-new) | Flagged. Pin `9.1.1` (2026-06-19) |
| hatchling | PyPI | since 2022, 86 releases; 1.33.0 published 2026-10-28 | seam: unknown | github.com/pypa/hatch | [SUS] (too-new) | Flagged. Pin `1.32.4` (2026-09-20) |
| setuptools | PyPI | — | — | github.com/pypa/setuptools | [SUS] (too-new) | Not recommended (see Alternatives) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** yt-dlp, pytest, hatchling. All `SUS` verdicts come from the *latest* release being days old. Each is a long-established project. Planner: add one `checkpoint:human-verify` before the first install that confirms the exact pins. Pinning to non-latest versions removes the recency signal for pytest and hatchling. No postinstall concept applies on PyPI.

## Architecture Patterns

### System Architecture Diagram

```
user URL ──► yt-dlp core ──► plugin finder (sys.path dirs containing yt_dlp_plugins/)
                                   │ registers AudioComIE (prepended, wins over Generic)
                                   v
               AudioComIE._VALID_URL match? ──no──► other extractors / [generic]
                                   │yes  groups: user, slug
                                   v
               canonical = https://audio.com/{user.lower()}/audio/{slug.lower()}
                                   v
               GET api.audio.com/oembed?url=canonical ──404──► ExtractorError (Phase 2 polishes msg)
                                   │ iframe_url → /embed/audio/(\d+)
                                   v
               GET api.audio.com/audio/{id}  ──► assert data.id == id
                                   │
               ┌───────────────────┴──────────────────────┐
               v                                          v
   transcodings[] → formats                        metadata → info dict
   (1-2 entries; mp3 always, m4a usually)          (title, uploader*, timestamp, duration, tags, counts, thumbnail?)
               └───────────────────┬──────────────────────┘
                                   v
               yt-dlp sorts formats (acodec rank: aac > mp3) ──► HTTPS GET s3.ustatik.com (pre-signed, 6 days)
```

### Recommended Project Structure
```
audio-com-downloader/
├── yt_dlp_plugins/              # NO __init__.py
│   └── extractor/               # NO __init__.py
│       └── audiocom.py          # AudioComIE (the only shipped file)
├── tests/
│   ├── conftest.py              # fixture loader + _download_json monkeypatch
│   ├── fixtures/<track_id>.json # {"url", "oembed": {"iframe_url"}, "audio": {...redacted subset}}
│   ├── test_url_matching.py     # suitable() positives/negatives
│   ├── test_extract_offline.py  # per-fixture info-dict assertions
│   ├── test_fixture_hygiene.py  # no X-Amz-/Signature/token strings in fixtures
│   └── test_plugin_loading.py   # subprocess `yt-dlp -v` → "Extractor Plugins: AudioComIE"
├── scripts/
│   ├── record_fixture.py        # live probe → redacted fixture (never writes signed URLs)
│   └── run_live_tests.py        # load_all_plugins() + yt-dlp test/test_download.py -k AudioCom
├── pyproject.toml               # hatchling, packages=["yt_dlp_plugins"]
└── .gitignore                   # .venv*/, __pycache__/, .pytest_cache/, build/, dist/, *.egg-info, test_AudioCom*
```

### Pattern 1: Offline extraction with monkeypatched `_download_json`
**What:** Patch the class method so `extract()` never touches the network. Then run `YoutubeDL.process_ie_result(..., download=False)` so yt-dlp itself computes `upload_date` and the selected format.
**Why it works:** `_download_json` is an ordinary method on `InfoExtractor`, built by `__create_download_methods` and looked up by name [VERIFIED: venv yt_dlp/extractor/common.py:1165-1166]. The verified test passed on both versions.

### Pattern 2: Live `_TESTS` via yt-dlp's own harness
**What:** `test/helper.py:gettestcases()` iterates `yt_dlp.extractor.gen_extractors()` at import time. Plugins are only registered when `load_all_plugins()` runs (normally inside `YoutubeDL.__init__`). Verified: without it, `any(ie.IE_NAME=='AudioCom' ...)` is `False`. So call `load_all_plugins()` first, then `pytest.main([.../test/test_download.py, '-k', 'AudioCom'])`. This generated and passed `test_AudioCom` + `test_AudioCom_all` on 2026.8.19 and 2026.10.26 (≈2 s).
**Requirements:** the harness version must match the installed yt-dlp (sdist `yt_dlp-<ver>/test/` or git tag). Run from a **writable, disposable cwd**: the harness writes `test_AudioCom_<id>.info.json` and the 10 KiB test download into cwd. A read-only cwd raised `PermissionError` (observed).

### Anti-Patterns to Avoid
- **setuptools default editable install:** silently not discovered (`Plugin directories: none`). Use hatchling.
- **Asserting both mp3 and m4a for every fixture:** false for pre-2025 tracks.
- **Reading `data['duration']` or `data['created']`:** neither key exists in `/audio/<id>`.
- **Passing the user's URL to oEmbed:** `www.`, trailing slash, query string and uppercase all 404.
- **Using `_TESTS` md5 from the API `md5` field:** the harness downloads only the first 10 KiB, so the file md5 never matches the API's whole-file md5. Omit `md5`.
- **Copying the `X-Amz-*` URL into fixtures, logs or tests.**
- **Using brand-new or spam-like tracks as live `_TESTS`:** 8/11 sampled tracks were uploaded on 2026-10-28, and several look like SEO spam (locksmith, LPG). They are likely to be deleted. Use them only as offline fixtures.

## Verified API Field Shapes (11 tracks, 2026-10-28)

[VERIFIED: live probes of api.audio.com/oembed and /audio/<id>, scratch summary script]

**oEmbed keys (identical on all 11):** `author_name, author_url, cache_age (432000), height, html, iframe_url, provider_name, provider_url, thumbnail_height, thumbnail_url, thumbnail_width (300), title, type ("rich"), version, width`. `iframe_url` = `https://audio.com/embed/audio/<id>?theme=image`. `thumbnail_url` is `''` unless the track has a real cover.

**`/audio/<id>` top-level keys (identical on all 11):** `author_name, avatar, caption, category_id, cross_link_tags, date_created, date_updated, description, id, image, is_downloadable, is_public, license, options, price, slug, sources, stats, tags, title, transcodings, transcribed, username`. There is **no** top-level `duration`, `created`, `user`, or `category_name`.

**`transcodings[]` entry keys:** `id, source_id, format, type, url, size, codec, sample_rate, channels, duration, bit_rate, date_created, date_updated, date_uploaded, date_waveform_generated, md5` (+ `waveform`, ignored).

| Field | Observed values | Unit / note |
|-------|-----------------|-------------|
| `format` | `mp3`, `m4a` | use as `ext`/`format_id` |
| `type` | `audio/mpeg`, `audio/m4a` | `mimetype2ext('audio/m4a')` → `m4a` (verified) |
| `codec` | `mp3`, `aac` | → `acodec` |
| `bit_rate` | mp3: 160000/192000/320000; m4a: 8946…324965 | bits/s → `abr = /1000` |
| `sample_rate` | 16000, 22050, 44100, 48000 | Hz → `asr` |
| `channels` | 2 (all transcodings) | → `audio_channels` |
| `duration` | e.g. 186358 (mp3) vs 186331 (m4a) | **ms**, differs ~25-70 ms between formats |
| `size` | exact bytes (downloaded m4a = 1066348 = API size) | → `filesize` |
| `url` | `https://s3.ustatik.com/audio.com.audio/transcoding/...?X-Amz-...` | pre-signed; strip query in fixtures |

**Other fields:**
| Field | Observed | Map |
|-------|----------|-----|
| `id` | 16-digit **string** | `id` (keep string; compare to requested id) |
| `username` | lowercase, hyphens/digits | `uploader_id`; `uploader_url = https://audio.com/<username>` (= oEmbed `author_url`) |
| `author_name` | display name **or `''`** (3/11) | `uploader`, fallback needed |
| `title` | unicode OK (Arabic sample) | `title` |
| `description`, `caption` | usually `''`; 2/11 had text | `description` only if non-empty |
| `image` | `''` (5/11), real cover `.../audio.com.static/audio/image/...` (1/11), or **uploader avatar** `.../user/avatar/...` (5/11, where `image == avatar`) | `thumbnail` via `url_or_none`. Thumbnails fetch with plain GET 200 `image/jpeg`; `--write-thumbnail` worked |
| `date_created` / `date_updated` | Unix **seconds** (e.g. 1790777856 = 2026-09-30 14:17:36 UTC) | `timestamp` |
| `tags` | list of 4-5 str, apparently auto-generated ("rustling leaves", "speech synthesizer") | `tags` |
| `stats` | `plays_count, likes_count, comments_count, shares_count, downloads_count, followers_count, collections_count` (ints, often 0) | `view_count, like_count, comment_count, repost_count` |
| `is_downloadable` | true 7/11, false 4/11 | not used in Phase 1 |
| `sources[]` | `wv`/wavpack, `wav`/wavpack or pcm_s16le, `mp3`, `m4a` | **do not emit** (Phase 2) |
| `license` | `"none"` on all | skip |

### Sampled tracks (fixture candidates)

| Track (public URL path) | Created | dl | Artwork | Desc | Transcodings | Notes |
|---|---|---|---|---|---|---|
| `david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best` | 2026-09-30 | F | none | no | mp3 192k, m4a 306k | reference; 5.5k plays; **live `_TESTS` #1** |
| `jasa-sisemore/audio/jasasisemore-audacitypractice-autoduck-assignment-4aup` | 2023-11-13 | F | none | no | **mp3 320k only** | oldest; stable; good **live `_TESTS` #2** |
| `beards-and-banter-podcast/audio/episode5-reuploaded-audio` | 2024-03-31 | F | none | no | **mp3 320k only** | 70 min podcast |
| `arthur-hpcp/audio/original` | 2026-04 | T | none | no | mp3 160k, **m4a 9k** @16 kHz | sort anomaly (Pitfall 1) |
| `roshimakr21/audio/5-song-track-chidanandaroopam-f` | 2026-10-28 | T | **real cover** | no | mp3 192k, m4a 323k | empty `author_name`; 48 kHz |
| `davidmoreno-musician/audio/like-a-rolling-stone-original` | 2026-10-28 | F | avatar | no | mp3 192k, m4a 325k | empty `author_name` |
| `alec-murray/audio/podcast-intro` | 2026-10-28 | T | none | no | mp3 192k, m4a 218k | full download verified |
| `james-gant/audio/zyd-arshadat` | 2026-10-28 | F | none | no | mp3 192k, m4a 222k | Arabic title, empty `author_name` |
| `shivgas/audio/festivals-and-pujas-bring-people-together-through-prayers` | 2026-10-28 | T | avatar | **yes** | mp3 160k, m4a 112k @22 kHz | title ≠ slug; spam-like |
| `jetlocksmithsau/audio/emergency-automotive-locksmith-services-what-drivers-need-to-know` | 2026-10-28 | T | avatar | **yes** | mp3 160k, m4a 126k | spam-like |
| `andrea-mathiopoulos/audio/song-9-the-devil-went-down-to-georgia` | 2026-10-28 | T | none | no | mp3 192k, m4a 241k | 10.8 s |

Coverage: downloadable true/false ✓, cover/avatar/none ✓, description yes/no ✓, mp3-only ✓, unicode ✓. Gap: no track with both a real cover and a description that is not spam-like. Acceptable for Phase 1.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Comparing live results to `_TESTS` (`'count:5'`, `int`, `'re:'`, `'md5:'`) | Custom comparator | yt-dlp `test/test_download.py` + `test/helper.py` (version-matched) via wrapper | Same semantics maintainers use; verified working for plugins |
| `upload_date` from `timestamp` | Manual date formatting | Return `timestamp`; yt-dlp core fills `upload_date` | Verified in `process_ie_result` |
| Choosing best format | Custom `preference` logic | yt-dlp default sort (locked), unless user changes decision (Open Q1) | |
| Nested-field extraction | `try/except KeyError` chains | `traverse_obj` with `{str}`, `{int_or_none}`, `filter`, `all` | Works on both versions (tests passed on 2026.8.19) |
| Query-string encoding of canonical URL | f-string concatenation | `_download_json(..., query={'url': canonical})` | Proper encoding |
| ext from MIME | dict of MIME types | `format` field, fallback `mimetype2ext(type)` | |

## Common Pitfalls

### Pitfall 1: "m4a wins on bitrate" is false. Default sort picks m4a by codec rank
**What goes wrong:** On `arthur-hpcp/audio/original`, yt-dlp selects m4a at **8.9 kbps / 16 kHz** over mp3 at 160 kbps. On `jetlocksmithsau/...` it selects m4a 126k over mp3 160k.
**Why:** Default sort order is `('hidden','aud_or_vid','hasvid','ie_pref','lang','quality','res','fps','hdr:12','vcodec','channels','acodec','size','br',...)`, and acodec order ranks `'aac'` above `'mp3'` [VERIFIED: venv yt_dlp/utils/_utils.py:5363-5377]. `acodec` comes before `br`.
**How to avoid:** CONTEXT locks "default sort". Keep it, but **do not assert in tests that the chosen format has the highest bitrate.** Raise Open Question 1 with the user.
**Warning signs:** Tiny output files on long tracks.

### Pitfall 2: Fields that don't exist
`data['duration']`, `data['created']`, `data['user']` do not exist in `/audio/<id>`. Use `transcodings[0].duration` (ms → s) and `date_created` (s). The CONTEXT line "`timestamp` from `created`" refers to the search-API model. The extractor must read `date_created`.

### Pitfall 3: Empty `author_name`
3/11 tracks have `author_name == ''` (oEmbed `author_name` is also `''`). EXTR-05 treats `uploader` as mandatory. The skeleton falls back to `username` [ASSUMED: user preference; see A1].

### Pitfall 4: Plugin installed but not discovered
setuptools ≥64 `pip install -e .` installs `__editable___*_finder.py` (a meta-path hook). yt-dlp's `default_plugin_paths()` only scans `sys.path` *directories* for a `yt_dlp_plugins` folder. Result: `[debug] Plugin directories: none` and no error at all. Verified on both versions. hatchling editable writes the project root into a `.pth` and is discovered. Also verified: `--plugin-dirs DIR` treats `DIR`'s **children** as package roots (`candidate_plugin_paths` iterates `DIR`). Passing the repo root itself finds nothing. Pass its parent, or use `PYTHONPATH=<repo>`. (STACK.md's claim that `--plugin-dirs` takes the directory containing `yt_dlp_plugins/` is wrong.)
**Warning signs:** `-v` lacks `Extractor Plugins: AudioComIE`; URL goes to `[generic]` and 403s.

### Pitfall 5: Import errors are swallowed
`load_plugins` catches any exception on import and prints `Error while importing module 'yt_dlp_plugins.extractor.audiocom'` to stderr, then continues [VERIFIED: venv yt_dlp/plugins.py:200-212]. The smoke test must assert both that the plugin line is present and that this string is absent.

### Pitfall 6: Embed and odd paths match a naive regex
`audio.com/embed/audio/<id>` would match `(?P<user>[^/]+)/audio/(?P<slug>...)` with user=`embed`. `audio.com/audio/audio/<id>` (a site redirect form) would match with user=`audio`. Exclude both with `(?!embed/|audio/)`.

### Pitfall 7: Python 3.12+ syntax
Dev venvs are 3.11 on purpose. Running the tests there is the syntax gate. Host default `python3` is 3.14, so don't run tests with it.

## Code Examples

### Plugin skeleton (verified: offline tests + `-F` + live `_TESTS` on 2026.8.19 and 2026.10.26)
```python
# yt-dlp plugin: audio.com single tracks.
# DELETE THIS FILE once the bundled yt-dlp ships a built-in audio.com extractor
# (check `yt-dlp --list-extractors | grep -i audiocom` after each yt-dlp upgrade).
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, float_or_none, int_or_none, mimetype2ext, url_or_none
from yt_dlp.utils.traversal import traverse_obj


class AudioComIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?audio\.com/(?!embed/|audio/)(?P<user>[^/?#]+)/audio/(?P<slug>[^/?#]+)/?(?:[?#]|$)'
    _API_BASE = 'https://api.audio.com'
    _TESTS = [{
        'url': 'https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best',
        'info_dict': {
            'id': '1877766681285368',
            'ext': 'm4a',
            'display_id': 'rusted-pitchfork-dana-liske-uncut-version-astrayal-best',
            'title': 'Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best',
            'uploader': 'David Oliveira',
            'uploader_id': 'david-oliveira-1877766671108274',
            'uploader_url': 'https://audio.com/david-oliveira-1877766671108274',
            'duration': 186.358,
            'timestamp': 1790777856,
            'upload_date': '20260930',
            'tags': 'count:5',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {
        'url': 'https://www.audio.com/David-Oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best/?utm_source=share',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user, slug = self._match_valid_url(url).group('user', 'slug')
        canonical_url = f'https://audio.com/{user.lower()}/audio/{slug.lower()}'
        oembed = self._download_json(
            f'{self._API_BASE}/oembed', slug, 'Downloading oEmbed JSON', query={'url': canonical_url})
        track_id = self._search_regex(
            r'/embed/audio/(\d+)', traverse_obj(oembed, ('iframe_url', {str})) or '', 'track id')
        data = self._download_json(f'{self._API_BASE}/audio/{track_id}', track_id, 'Downloading track JSON')
        if str_id := traverse_obj(data, ('id', {str})):
            if str_id != track_id:
                raise ExtractorError(f'API returned track {str_id}, expected {track_id}')

        formats = []
        for t in traverse_obj(data, ('transcodings', lambda _, v: url_or_none(v['url']))):
            ext = traverse_obj(t, ('format', {str})) or mimetype2ext(t.get('type'))
            formats.append({
                'url': t['url'],
                'format_id': ext,
                'ext': ext,
                'vcodec': 'none',
                **traverse_obj(t, {
                    'acodec': ('codec', {str}),
                    'abr': ('bit_rate', {lambda x: float_or_none(x, 1000)}),
                    'asr': ('sample_rate', {int_or_none}),
                    'audio_channels': ('channels', {int_or_none}),
                    'filesize': ('size', {int_or_none}),
                }),
            })
        if not formats:
            raise ExtractorError('No playable transcodings found', expected=True)

        username = traverse_obj(data, ('username', {str})) or user.lower()
        return {
            'id': track_id,
            'display_id': slug,
            'formats': formats,
            'uploader_id': username,
            'uploader_url': f'https://audio.com/{username}',
            'uploader': traverse_obj(data, ('author_name', {str}, filter)) or username,  # A1
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str}, filter),
                'thumbnail': ('image', {url_or_none}),
                'timestamp': ('date_created', {int_or_none}),
                'duration': ('transcodings', 0, 'duration', {lambda x: float_or_none(x, 1000)}),
                'tags': ('tags', ..., {str}, filter, all, filter),
                'view_count': ('stats', 'plays_count', {int_or_none}),
                'like_count': ('stats', 'likes_count', {int_or_none}),
                'comment_count': ('stats', 'comments_count', {int_or_none}),
                'repost_count': ('stats', 'shares_count', {int_or_none}),
            }),
        }
```
Notes: omit `IE_NAME`, so the default `cls.__name__[:-2]` gives `[AudioCom]` and `ie_key()` `AudioCom` [VERIFIED: venv yt_dlp/extractor/common.py:834-840]. Error-message polish for 404s is Phase 2 (EXTR-06). Add a second live `_TESTS` entry for `jasa-sisemore/...` (mp3-only, `'ext': 'mp3'`) if the planner wants PLUG-03 groundwork early.

### Offline test (verified, 11/11 passed on both versions)
```python
import json, pathlib
import pytest
from yt_dlp import YoutubeDL
from yt_dlp_plugins.extractor.audiocom import AudioComIE

FIXTURES = sorted((pathlib.Path(__file__).parent / 'fixtures').glob('*.json'))

@pytest.fixture(params=FIXTURES, ids=lambda p: p.stem)
def fx(request, monkeypatch):
    data = json.loads(request.param.read_text())
    calls = []
    def fake(self, url_or_request, video_id, *args, query=None, **kwargs):
        calls.append((url_or_request, query))
        if url_or_request == 'https://api.audio.com/oembed':
            return data['oembed']
        if url_or_request == f'https://api.audio.com/audio/{data["audio"]["id"]}':
            return data['audio']
        raise AssertionError(f'unexpected request {url_or_request}')
    monkeypatch.setattr(AudioComIE, '_download_json', fake)
    return data, calls

def test_extract(fx):
    data, calls = fx
    with YoutubeDL({'quiet': True}) as ydl:
        info = AudioComIE(ydl).extract(data['url'])
        processed = ydl.process_ie_result(dict(info), download=False)
    assert calls[0][1] == {'url': data['url']}           # canonical URL sent to oEmbed
    assert {f['ext'] for f in info['formats']} <= {'mp3', 'm4a'}
    assert all(f['vcodec'] == 'none' for f in info['formats'])
    assert processed['upload_date']
```
`pyproject.toml` needs `[tool.pytest.ini_options] pythonpath = ["."]` (or the editable install) so `yt_dlp_plugins` is importable. Per-fixture expected values (title, uploader, duration, has-thumbnail, has-description, format set) belong in the fixture file or a parametrized table.

### Fixture recording (redaction rule)
Keep only: `audio.{id, username, author_name, slug, title, description, image, date_created, tags, stats, transcodings[].{id, format, type, url, size, codec, sample_rate, channels, duration, bit_rate}}` and `oembed.iframe_url`. Write `url.split('?', 1)[0]` for every transcoding URL. Drop `waveform`, `md5`, `sources`, `download`, `avatar`, `cross_link_tags`. A hygiene test fails if any fixture contains `X-Amz-`, `Signature`, `token`, `client_secret`, `stripe`.

### Live `_TESTS` runner (verified on both versions)
```python
# scripts/run_live_tests.py  usage: python scripts/run_live_tests.py <yt-dlp-src-root> [AudioCom]
import sys
import pytest
from yt_dlp.plugins import load_all_plugins

load_all_plugins()  # must run before test_download builds its test methods
sys.exit(pytest.main([sys.argv[1] + '/test/test_download.py', '-p', 'no:cacheprovider',
                      '-k', sys.argv[2] if len(sys.argv) > 2 else 'AudioCom', '-v']))
```
Get the harness: `git clone --depth 1 --branch 2026.10.26 https://github.com/yt-dlp/yt-dlp /tmp/.../yt-dlp-2026.10.26` (or `--branch 2026.08.19`). Run with cwd set to a temp dir.

### pyproject.toml (hatchling; verified editable discovery on 2026.8.19)
```toml
[build-system]
requires = ["hatchling==1.32.4"]
build-backend = "hatchling.build"

[project]
name = "yt-dlp-audiocom"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["yt-dlp", "pytest==9.1.1"]

[tool.hatch.build.targets.wheel]
packages = ["yt_dlp_plugins"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = ["live: hits api.audio.com"]
```
The built wheel installs `yt_dlp_plugins/extractor/audiocom.py` with no `__init__.py` files (verified).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ytdlp_plugins/<type>/__init__.py` | `yt_dlp_plugins` namespace package, no `__init__.py` | yt-dlp 2023.01.02 | Compat path still exists but only under the executable dir |
| `-v` only listed plugins | `-v` prints `Extractor Plugins: AudioComIE` **and** `Plugin directories: <path>/yt_dlp_plugins` | present in 2026.8.19 and 2026.10.26 | Assert both lines in smoke test [VERIFIED: YoutubeDL.py:4181-4200 + live output] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `uploader` falls back to `username` when `author_name` is empty | Pitfall 3, skeleton | Cosmetic. Alternative is `uploader=None` for ~27% of tracks, which fails EXTR-05's "uploader" check for them |
| A2 | Lowercasing both `user` and `slug` is safe (no observed slug or username contains uppercase in ~40 seen) | Skeleton | A mixed-case slug would 404 at oEmbed. Mitigation: retry with original case (Phase 2) |
| A3 | Using `image` as thumbnail even when it equals the uploader avatar (5/11 tracks) is acceptable | Field map | Embedded cover art is the uploader's avatar, not track art. Alternative: drop it when `image == avatar` |
| A4 | `transcodings` order (mp3 first) is stable; `duration` taken from index 0 | Skeleton | ±70 ms duration change; tests pinned to fixture values |

## Open Questions

1. **Format preference when m4a is lower quality than mp3 (Pitfall 1)**
   - What we know: the default sort always prefers aac. On 1/11 tracks that means 9 kbps instead of 160 kbps, and on 2/11 m4a has a lower bitrate than mp3.
   - What's unclear: whether the user wants to keep the locked "default sort" decision.
   - Recommendation: Phase 1 keeps the default sort (locked). Planner asks the user at the end-of-phase checkpoint whether to add a per-format `quality` derived from `abr` (making the higher bitrate win) in Phase 2.
2. **Thumbnail = avatar (A3).** Keep it for Phase 1 and confirm with the user.
3. **Live `_TESTS` #2 choice.** `jasa-sisemore/...` (2023, mp3-only) is the most stable sampled track. It has 0 plays, so deletion risk is unknown.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | venvs/installs | ✓ | 0.11.14 | `python3.11 -m venv` + pip |
| CPython 3.11 | dev venvs | ✓ (uv-managed) | 3.11.15 | `uv python install 3.11` |
| System python3 | — | ✓ | 3.14.8 | don't use for tests |
| yt-dlp (host) | — | ✗ (by design) | — | venvs above |
| Network → api.audio.com, s3.ustatik.com | live tests, fixture recording | ✓ | — | offline tests need none |
| ffprobe | optional file check | ✓ | system | skip |
| git | harness clone | ✓ | — | PyPI sdist tarball |
| docker / `metube` container | Phase 3 only | ✓ (yt-dlp 2026.08.19, Py 3.13.15) | — | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

(`workflow.nyquist_validation` is `false` in config. Included because the orchestrator requested it explicitly.)

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 on Python 3.11, two venvs (yt-dlp 2026.10.26 / 2026.8.19) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (Wave 0) |
| Quick run command | `.venv/bin/python -m pytest -q -m "not live"` (<1 s observed) |
| Full suite command | `for v in .venv .venv-metube; do $v/bin/python -m pytest -q -m "not live"; done` then the live runner on each |

### Success Criteria → Automated Checks
| Criterion / Req | Behavior | Type | Automated Command | File Exists? |
|-----------------|----------|------|-------------------|-------------|
| SC1 / PLUG-01 | `yt-dlp -v` shows `Extractor Plugins: AudioComIE`, no `Error while importing` | smoke (subprocess, both venvs) | `pytest tests/test_plugin_loading.py` (runs `<venv>/bin/yt-dlp -v` with cwd=/ and asserts both strings) | ❌ Wave 0 |
| SC1 / PLUG-01 | No `__init__.py` under `yt_dlp_plugins/`; only absolute `yt_dlp.` imports | unit | `pytest tests/test_plugin_loading.py::test_layout` (glob + regex `^from \.`) | ❌ Wave 0 |
| SC2 / EXTR-01 | Reference + `www.`/trailing slash/query/uppercase variants → `suitable()` True | unit | `pytest tests/test_url_matching.py` | ❌ Wave 0 |
| SC3 / EXTR-01 | `/collections/`, profile, `/embed/audio/`, `/audio/audio/`, foreign host → False | unit | same file | ❌ Wave 0 |
| SC2 / EXTR-02 | oEmbed called with canonical lowercase URL; no `impersonate` kwarg in any request | unit (monkeypatch records kwargs) | `pytest tests/test_extract_offline.py -k canonical` | ❌ Wave 0 |
| SC2 / EXTR-02 | Live download without 403 | live | `python scripts/run_live_tests.py <harness>` (both versions) | ❌ Wave 0 |
| SC4 / EXTR-03 | formats ⊆ {mp3, m4a}; each has `ext`, `abr`, `acodec`, `vcodec=='none'`; reference fixture has both | unit | `pytest tests/test_extract_offline.py -k formats` | ❌ Wave 0 |
| SC4 / EXTR-03 | `-F` on reference lists mp3+m4a | live/manual | `.venv/bin/yt-dlp -F <ref>` (asserted in live runner or end-of-phase checkpoint) | — |
| SC5 / EXTR-05 | Per-fixture title, uploader, uploader_id/url, duration (float s, <10000), timestamp → upload_date; thumbnail/description absent (not `''`) when empty | unit, ≥5 fixtures (8-11 recommended) | `pytest tests/test_extract_offline.py` | ❌ Wave 0 |
| Fixture hygiene | No signatures/tokens/keys in `tests/fixtures/` | unit | `pytest tests/test_fixture_hygiene.py` | ❌ Wave 0 |
| Py 3.11 syntax | Module compiles on 3.11 | implicit | any test run in the 3.11 venv | — |

### Sampling Rate
- **Per task commit:** quick command in `.venv`
- **Per wave merge:** offline suite in both venvs
- **Phase gate:** offline suite (both venvs) + live runner (both versions) green + end-of-phase human check of a real download

### Wave 0 Gaps
- [ ] `pyproject.toml` (hatchling, pytest config, `live` marker), `.gitignore`
- [ ] `.venv` and `.venv-metube` created with pins
- [ ] `tests/conftest.py` (fixture loader / monkeypatch)
- [ ] `scripts/record_fixture.py` + ≥5 fixtures (recommend the 11 above, or at least reference, jasa-sisemore, arthur-hpcp, roshimakr21, james-gant, shivgas)
- [ ] `scripts/run_live_tests.py` + harness checkout location under the scratch dir (not in repo)

## Security Domain

### Applicable ASVS Categories (L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | anonymous API only; never read the site's embedded OAuth/Stripe config |
| V3 Session Management | no | no cookies |
| V4 Access Control | no (Phase 2 handles `is_downloadable`) | do not emit `sources[]` |
| V5 Input Validation | yes | anchored `_VALID_URL`; user input only reaches `query={'url': ...}` (encoded by yt-dlp); `track_id` constrained to `\d+`; returned `id` checked |
| V6 Cryptography | no | — |
| V8 Data Protection | yes | fixture redaction + hygiene test; never log or commit signed URLs |
| V14 Configuration | yes | zero import-time side effects (all plugins are imported on every yt-dlp run) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Signed S3 URLs leaked into git via fixtures | Information disclosure | strip query strings at record time; hygiene test |
| Lookalike host (`audio.com.evil.com`) routed to plugin | Spoofing | host anchored `audio\.com/` (verified False) |
| Request to unexpected host via crafted URL | Tampering/SSRF | API base is a constant; only path digit id and encoded query param vary |
| API returns a different track than requested | Tampering | `id` equality check |
| Plugin code executed on every yt-dlp invocation | Elevation | no network/file I/O at import; single reviewed file |

## Sources

### Primary (HIGH confidence)
- Live probes this session: `api.audio.com/oembed`, `api.audio.com/audio/<id>` (11 tracks), `s3.ustatik.com` download, thumbnail GETs; summaries in scratch (raw responses not committed)
- Installed yt-dlp 2026.10.26 and 2026.8.19 source: `plugins.py` (load/scan), `YoutubeDL.py:4181-4200` (debug lines), `extractor/common.py` (IE_NAME, `_download_json`, `get_testcases`), `extractor/__init__.py` (plugin spec), `utils/_utils.py:5363-5377` (format sort)
- yt-dlp sdist `test/helper.py`, `test/test_download.py` (2026.10.26 and 2026.8.19)
- yt-dlp README "PLUGINS" section (local copy); https://github.com/yt-dlp/yt-dlp-sample-plugins (`setup.cfg`: `packages = find_namespace:`; `pyproject.toml`: setuptools); https://github.com/yt-dlp/yt-dlp/wiki/Plugin-Development
- PyPI JSON API for versions/dates; `git ls-remote` for tags; `docker exec metube` for bundled version

### Secondary (MEDIUM)
- WebSearch for older public tracks: https://audio.com/beards-and-banter-podcast/audio/episode5-reuploaded-audio, https://audio.com/jasa-sisemore/audio/jasasisemore-audacitypractice-autoduck-assignment-4aup, https://audio.com/arthur-hpcp/audio/original (each then confirmed via API)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (installed and run on both versions)
- Architecture/API shapes: HIGH for 11 sampled tracks; MEDIUM on generalization (sample skews to tracks uploaded on 2026-10-28)
- Pitfalls: HIGH (each reproduced)

**Research date:** 2026-10-28
**Valid until:** 2026-11-27 (API is undocumented; re-probe if fixtures drift)
