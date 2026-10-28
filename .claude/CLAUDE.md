<!-- GSD:project-start source:PROJECT.md -->

## Project

**audio.com yt-dlp Extractor**

A yt-dlp extractor for audio.com single-track pages (e.g. `https://audio.com/<user>/audio/<slug>`), so they can be downloaded programmatically. It ships as a yt-dlp plugin that Patrick's MeTube container loads, so pasting an audio.com link into MeTube just works.

**Core Value:** Pasting an audio.com track URL into MeTube (or `yt-dlp`) downloads the audio file with correct metadata.

### Constraints

- **Tech stack**: Python, yt-dlp extractor API (`InfoExtractor`) — required for upstream acceptance
- **Compatibility**: Must load in MeTube's bundled yt-dlp version without rebuilding the image (volume-mounted plugin)
- **Upstream policy**: Must satisfy yt-dlp maintainers' rules (no new hard dependencies; impersonation via existing optional curl_cffi support)

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## READ FIRST: upstream has a hard NO AI / NO LLM policy

## Verified Environment Facts (live `metube` container, read-only inspection)

| Fact | Value | Confidence |
|------|-------|------------|
| Bundled yt-dlp | 2026.08.19 (latest upstream release is 2026.10.26) | HIGH |
| Python in image | 3.13.15 | HIGH |
| `curl_cffi` in image | **Yes, 0.16.3** (MeTube's own `pyproject.toml` lists `yt-dlp[default,curl-cffi,deno]` AND `curl-cffi` explicitly, so it is durable across image updates) | HIGH |
| Request handlers | `urllib, requests, websockets, curl_cffi` | HIGH |
| `--list-impersonate-targets` | Chrome-133/136, Firefox 133-147, Safari 15-26, Edge, Tor, etc. via curl_cffi | HIGH |
| ffmpeg | 7.1.5 | HIGH |
| Plugin mount already in place | `/opt/metube/plugins:/plugins:ro` + `PYTHONPATH=/plugins` in `/opt/metube/docker-compose.yml`; a working plugin already loads (`yt_dlp_plugins/extractor/rumble_fix.py`, shown in `-v` as "Extractor Plugins: grid (RumbleChannelIE), impersonate (...)") | HIGH |
| yt-dlp plugin dirs searched | `/plugins/yt_dlp_plugins` and site-packages `yt_dlp_plugins` | HIGH |
| Cloudflare behaviour | Plain urllib page fetch: 403. `curl_cffi` `impersonate='chrome'`: 200 with `og:audio:secure_url` (a presigned `s3.ustatik.com` mp3) in HTML. `yt-dlp --extractor-args generic:impersonate` already reaches the mp3 through the generic extractor. | HIGH |
| Media CDN | Presigned URL (`X-Amz-Expires=518400`, 6 days) served via Cloudflare; Range GET returned 206 with a browser User-Agent. Python's default `urllib` UA got 403. yt-dlp sends a browser UA by default, so format-level impersonation is probably unnecessary. Verify in the build phase; fallback is a format-level `'impersonate': True`. | MEDIUM |
| Page has no `__NEXT_DATA__`; JSON-LD on the page is only the site Organization, not the track | Metadata comes from `og:`/`twitter:` meta tags (title format `"<track> \| Music by <user> \| Listen on audio.com"`), so parse carefully | HIGH |

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `yt_dlp.extractor.common.InfoExtractor` | yt-dlp master (2026.10.26); must also run on 2026.08.19 | Extractor base class | Mandatory for upstream. Subclass it, define `_VALID_URL`, `_TESTS`, `_real_extract`. No new dependencies allowed. |
| Python | Write for **3.11** (upstream floor, CPython and PyPy >=3.11); runs on MeTube's 3.13.15 | Language | Upstream rejects syntax newer than 3.11. Watch for 3.12+ only features (same-quote nested f-strings, PEP 695 generics). |
| `curl_cffi` via yt-dlp's own impersonation | 0.16.3 in image; 0.17.0 latest; yt-dlp allows `>=0.5.10,!=0.6-0.9,<0.18` | TLS/HTTP2 fingerprint impersonation to pass Cloudflare | Upstream-blessed path: it is an *optional* dependency, and the extractor only passes `impersonate=True`. Never import `curl_cffi` in the extractor. |
| `hatch` | 1.18.2 (needs >=1.10) | Project/test/lint runner | What CONTRIBUTING.md tells contributors to use (`hatch run setup`, `hatch test`, `hatch fmt`). Default env uses the `uv` installer. |
| `ruff` | `~=0.17.0` (0.17.3 current) | Linter | Pinned by yt-dlp's `static-analysis` group; run through `hatch fmt` so the version and config match upstream exactly. |
| `autopep8` | `~=2.0` | Formatter | yt-dlp formats with autopep8 (a selected E/W rule list), not black/ruff-format. Running `ruff format` or `black` will produce a diff that CI/maintainers reject. |
| `pytest` | `~=9.0` (+ `pytest-rerunfailures ~=16.0`; hatch-test adds `pytest-randomly ~=3.15`, `pytest-xdist[psutil] ~=3.5`) | Test runner | Invoked by `devscripts/run_tests.py` via `hatch test`. |

### Plugin Packaging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `yt_dlp_plugins` namespace package | Needs yt-dlp >=2023.01.02 | Plugin discovery | Layout `yt_dlp_plugins/extractor/audiocom.py`, **no `__init__.py`** in `yt_dlp_plugins/` or `extractor/` (namespace package). |
| Volume mount to `/plugins` + `PYTHONPATH=/plugins` | n/a | Load plugin in MeTube | Documented on MeTube's wiki ("yt-dlp plugins") and **already configured** in the existing compose. Deliverable is one file dropped at `/opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py` plus a container restart. |
| setuptools `find_namespace:` or hatchling `packages=["yt_dlp_plugins"]` | any | Optional pip-installable wheel | Only if you want `pip install` distribution (mirrors `yt-dlp/yt-dlp-sample-plugins`). Not needed for MeTube; skip for v1. |

### Supporting Libraries (all already inside yt-dlp; add nothing)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `yt_dlp.utils.traverse_obj`, `int_or_none`, `float_or_none`, `url_or_none`, `clean_html`, `unified_timestamp`, `parse_duration`, `ExtractorError` | bundled | Defensive field extraction | Always. Upstream convention: lenient `traverse_obj`, optional fields `fatal=False`. |
| `InfoExtractor._og_search_title/_og_search_thumbnail/_og_search_description/_html_search_meta/_search_regex/_search_json` | bundled | Pull metadata from the SSR HTML | The track metadata lives in `og:`/meta tags in the Cloudflare-served HTML. |
| `yt_dlp.networking.impersonate.ImpersonateTarget` | bundled | Pin a specific browser (e.g. `ImpersonateTarget('chrome', '116', 'windows', '10')`) | Only if bare `impersonate=True` ("any available target") proves flaky. Default to `True`: it resolves to whatever the installed backend supports, which is the pattern in bandcamp/mixcloud/samplefocus/kick. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `git clone` of a fork of yt-dlp/yt-dlp + `hatch run setup` | Installs pre-commit hook (`hatch fmt` on commit) | Venv at `.venv`; `hatch shell` to enter. |
| `python -m devscripts.install_deps --include-group dev` or `pip install -e ".[default,curl-cffi,dev]"` | Non-hatch fallback | Use `curl-cffi` extra, or the impersonation path silently degrades and tests fail (see Pitfalls). |
| `hatch test AudioCom` / `AudioCom_1` / `AudioCom_all` | Run extractor tests from `_TESTS` | Maps to `test/test_download.py::TestDownload::test_AudioCom*` (the `IE` suffix is stripped). Marked `download`, so network tests do not run in the core CI job. |
| `python -m devscripts.run_tests AudioCom` | Same without hatch | Respects `HATCH_TEST_ARGS`. |
| `hatch fmt --check` / `hatch fmt` | ruff check + autopep8 | Run before every commit. |
| `python -m yt_dlp -v --plugin-dirs <dir> <url>` | Test the plugin in a host venv | `--plugin-dirs` takes a directory containing `yt_dlp_plugins/`. Confirm "Extractor Plugins:" appears in `-v`. |
| `docker exec metube yt-dlp -v --simulate <url>` | Final acceptance against the real bundled version (2026.08.19) | Read-only; shows "Extractor Plugins:" line. |
| `python devscripts/make_supportedsites.py` | Regenerate `supportedsites.md` | Check whether maintainers want it in the PR; not listed in CONTRIBUTING steps. |

## Upstream Extractor Conventions (what review checks)

## Plugin Strategy (single source of truth)

- Every public class ending in `IE` defined **in the plugin module** is registered; imported classes are ignored (`obj.__module__` filter). Underscore-prefixed classes/modules are skipped.
- Plugin extractors are *prepended* to the extractor map, so they take priority over built-ins. Keep the class name `AudioComIE` identical to the future upstream name so that after the upstream merge the plugin shadows rather than duplicates; delete the plugin once MeTube ships a yt-dlp containing it.
- Import errors in a plugin are printed to stderr and skipped. If the plugin fails to load, symptoms are a `[generic]` 403 in MeTube, not a crash. Check `yt-dlp -v` for the "Extractor Plugins:" line.
- `Note that all plugins are imported even if not invoked`: keep import-time work at zero.
- Override-style plugins (`class X(BuiltinIE, plugin_name='...')`) are not needed here because no built-in `audio.com` extractor exists. (The existing `rumble_fix.py` uses that mode; do not copy it.)
- MeTube cannot set `impersonate` through `YTDL_OPTIONS` (JSON, yt-dlp wants an object), which is why the extractor must pass `impersonate=True` itself. This is exactly the design chosen here.

## Installation

# Upstream dev environment (Patrick's host; yt-dlp is not installed there)

# Without hatch

# Plugin compatibility check against the version MeTube actually runs

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `impersonate=True` in the extractor | Pin `ImpersonateTarget('chrome', ...)` | If "any target" selects a fingerprint Cloudflare later blocks; pin the oldest stable Chrome that works. |
| `impersonate=True` in the extractor | `--extractor-args generic:impersonate` (works today for the generic path) | Stopgap for MeTube without a plugin, but not settable per-site in MeTube's JSON options and gives poor metadata (generic `title` = slug, no uploader). |
| Directory mount + `PYTHONPATH` | `--plugin-dirs`, `~/.config/yt-dlp/plugins/...`, `.zip` on `PYTHONPATH`, `pip install` of a wheel | `PYTHONPATH` mount is already wired and survives image updates; the others require changing MeTube's command line/image or writing inside the container. |
| hatch (upstream standard) | plain venv + `devscripts.run_tests` | When hatch/uv is unavailable; same commands, less ergonomic. |
| Parse `og:` meta tags | Hit an audio.com JSON API | Only if the discovery phase finds a stable, unauthenticated API. Prefer SSR meta because it is the cheapest, least likely to need auth. (Not investigated here; flag for the extractor phase.) |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Importing `curl_cffi`/`requests` directly in the extractor | Upstream rejects new hard deps; bypasses yt-dlp's cookie jar, proxy, UA and `--impersonate` handling | `_download_webpage(..., impersonate=True)` |
| `ruff format` / `black` / `flake8` | Upstream formats with `autopep8` and lints with `ruff` using a custom rule set; other formatters create diffs | `hatch fmt` |
| `print()` in the extractor | ruff `T20` is enforced for `yt_dlp/extractor/**` (the per-file ignore exempts every *other* path) | `self.to_screen`, `self.report_warning`, `self.write_debug` |
| Relative imports in the *plugin* file | Plugins live in the `yt_dlp_plugins` namespace, not `yt_dlp.extractor` | Absolute `from yt_dlp.extractor.common import InfoExtractor` |
| `__init__.py` in `yt_dlp_plugins/` or `yt_dlp_plugins/extractor/` | Breaks the namespace-package merge with other plugin packages (MeTube already has Rumble plugin files in the same tree) | No `__init__.py` |
| Plugin filename colliding with another plugin package's file | pip-installed plugin files must have unique filenames across packages | `audiocom.py` (unique) |
| Python 3.12+ only syntax | Upstream CI runs 3.11 | Write for 3.11 |
| Hard-coded signed media URLs/IDs from the reference track in `_TESTS` | Presigned URLs expire in 6 days; the track may be deleted | Test on `id`/`title`/regex fields; use `skip` if the track is not stable |
| LLM-written upstream code or PR text | Violates the project's NO AI policy; account can be banned | Patrick writes the upstream copy himself |
| Relying on `generic` + `generic:impersonate` as the "solution" | Works only by accident (JSON-LD/direct-link path), loses uploader/duration/description | Dedicated extractor |

## Stack Patterns by Variant

- Keep one source file, converted to relative imports for the PR.
- Because both targets exercise the same tests, run `hatch test AudioCom` in the fork and the `docker exec ... --simulate` smoke check against the plugin.
- Ship plugin-only; the plugin has no AI-policy exposure. Still follow upstream style, so a human can submit it later.
- `impersonate=True` emits a warning and the plain request 403s. Add `require_impersonation=True` so the user gets a clear "install curl_cffi / yt-dlp[curl-cffi]" error rather than an opaque 403.
- `curl_cffi` cannot solve JS challenges. Fallbacks are cookies (`--cookies`, MeTube `/cookies` mount) or a different target version. This is out of scope for v1; flag it.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| yt-dlp 2026.08.19 (MeTube) | `curl_cffi` 0.16.3 (installed) | Within yt-dlp's `<0.18` bound. |
| yt-dlp master/2026.10.26 | `curl_cffi` 0.17.0 (pinned in `pin-curl-cffi`) | Dev venv will pick 0.17.x. Targets can differ slightly between 0.16 and 0.17, so always smoke-test on the container too. |
| `impersonate=` kwarg on `_download_webpage` | present in 2026.08.19 | Verified by reading the installed `common.py`. `require_impersonation` also present. |
| `yt_dlp_plugins` namespace plugins | yt-dlp >=2023.01.02 | Plugin API explicitly carries "no backwards compatibility guaranteed" in `globals.py`. Re-verify after each MeTube yt-dlp bump. |
| Python 3.13.15 (image) | upstream floor 3.11 | Code must satisfy the lower bound. |
| ruff `~=0.17.0`, autopep8 `~=2.0`, pytest `~=9.0` | per upstream `pyproject.toml` `[dependency-groups]` | Don't pin differently; let `hatch fmt` pull the right ones. |

## Sources

- https://github.com/yt-dlp/yt-dlp (master `pyproject.toml`, `CONTRIBUTING.md`, `README.md` Plugins section, `yt_dlp/networking/impersonate.py`, `yt_dlp/extractor/common.py`, `test/test_download.py`, `devscripts/run_tests.py`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/workflows/core.yml`): HIGH
- https://github.com/alexta69/metube/wiki/yt-dlp-plugins ("`PYTHONPATH=/plugins`, mount `./plugins:/plugins:ro`, `yt_dlp_plugins/extractor/`"): HIGH
- https://github.com/yt-dlp/yt-dlp/wiki/Plugin-Development and https://github.com/yt-dlp/yt-dlp-sample-plugins: HIGH
- Live `docker exec metube` inspection (env, `pip list`, `yt-dlp -v`, `--list-impersonate-targets`, installed `yt_dlp/plugins.py`, `extractor/common.py`, `/app/pyproject.toml`, `/app/docker-entrypoint.sh`) and `/opt/metube/docker-compose.yml`: HIGH
- Live probes against the reference audio.com URL via `curl_cffi` and `urllib` in the container: HIGH (page), MEDIUM (media CDN behavior across UAs)
- PyPI JSON (yt-dlp 2026.10.26, curl-cffi 0.17.0, hatch 1.18.2, ruff 0.17.3): HIGH
- Not run through the `research-plan`/`classify-confidence` seam; primary sources were read directly, so confidence tags above reflect direct verification.

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
