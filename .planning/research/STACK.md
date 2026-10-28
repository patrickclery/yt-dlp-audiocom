# Stack Research

**Domain:** yt-dlp site extractor (audio.com single tracks), upstream PR + external plugin for MeTube
**Researched:** 2026-10-28
**Confidence:** HIGH (everything below was verified against upstream `master` files and the live `metube` container, not training data)

## READ FIRST: upstream has a hard NO AI / NO LLM policy

`CONTRIBUTING.md` (master) forbids LLMs/agents for "patches or pull requests (including PR descriptions)", issues, and review comments. The PR template makes the submitter attest to it ("If any of your answers are dishonest, you will be permanently blocked"). Violators "may be blocked without warning".

Roadmap consequence: the code and PR text that go **upstream must be written by Patrick personally**, not generated or rewritten by Claude. AI assistance is safe only for the *plugin-only* track and for non-upstream research/notes. Decide this before the extractor phase, because the upstream file and the plugin file are meant to be the same file (see Pattern below). Options: (a) Patrick hand-writes the extractor and Claude only reviews or tests the plugin copy, or (b) ship plugin-only and skip the upstream PR. Confidence: HIGH (read from master CONTRIBUTING.md and PULL_REQUEST_TEMPLATE.md).

Also required by upstream: new-site rules (not a piracy site; audio.com is a legit hosting platform), code under Unlicense/public domain, open an issue first only for *features*, not new extractors.

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

1. File `yt_dlp/extractor/audiocom.py`, class `AudioComIE` (name must end `IE`), relative imports (`from .common import InfoExtractor`, `from ..utils import ...`).
2. Register in `yt_dlp/extractor/_extractors.py` (alphabetical; trailing comma in parenthesized import groups).
3. `_TESTS`: at least one test. Use a `skip` key with a reason if the URL can't be automated. Info dict needs `id`, `ext`; add `title`, `uploader`, `duration`, `thumbnail` (regex `r're:https?://...'`), `description` (`md5:` prefix) as available. `only_matching` for extra URL shapes. Tests raise on any warning (`report_warning` is overridden to raise in `test_download.py`).
4. Single quotes, 120-col soft limit, trailing commas, ruff `select`/`ignore` from `pyproject.toml` (quotes `Q`, commas `COM`, pyupgrade `UP`, bugbear `B`, simplify `SIM`, `T20` no `print`, etc.). No `# noqa` unless a maintainer asks.
5. Mandatory fields: `id`, `title`, and formats (or `url`). Everything else optional and non-fatal. Audio-only formats should set `'vcodec': 'none'`.
6. Impersonation idiom: `self._download_webpage(url, display_id, impersonate=True)` (optionally `require_impersonation=True` for a clear error when `curl_cffi` is missing). Extractor-level `impersonate` is the contract; do not add global flags.
7. `_WORKING = False` is only for an extractor known broken at merge time; otherwise leave the default.
8. PR: open from a branch of your fork, enable "edits by maintainers", fill the full PR template (do not force-push after opening).

## Plugin Strategy (single source of truth)

Write the extractor once, upstream-style, in the plugin repo as `yt_dlp_plugins/extractor/audiocom.py`, importing from the **absolute** `yt_dlp.*` paths. A plugin cannot use relative imports to reach yt-dlp internals. For the upstream PR, convert the three import lines to relative (`from .common import InfoExtractor`, `from ..utils import ...`). Keep a tiny script or Makefile target that does that substitution so the two files cannot drift.

Plugin loading rules (from `yt_dlp/plugins.py`, verified in the container):
- Every public class ending in `IE` defined **in the plugin module** is registered; imported classes are ignored (`obj.__module__` filter). Underscore-prefixed classes/modules are skipped.
- Plugin extractors are *prepended* to the extractor map, so they take priority over built-ins. Keep the class name `AudioComIE` identical to the future upstream name so that after the upstream merge the plugin shadows rather than duplicates; delete the plugin once MeTube ships a yt-dlp containing it.
- Import errors in a plugin are printed to stderr and skipped. If the plugin fails to load, symptoms are a `[generic]` 403 in MeTube, not a crash. Check `yt-dlp -v` for the "Extractor Plugins:" line.
- `Note that all plugins are imported even if not invoked`: keep import-time work at zero.
- Override-style plugins (`class X(BuiltinIE, plugin_name='...')`) are not needed here because no built-in `audio.com` extractor exists. (The existing `rumble_fix.py` uses that mode; do not copy it.)

MeTube deployment steps (compose already correct, no changes needed):
1. Put the file at `/opt/metube/plugins/yt_dlp_plugins/extractor/audiocom.py` (source of truth is `homelab/docker/metube/plugins/` per the compose comment; commit it there).
2. Restart the container (restart policy is `"no"`; startup is owned by `metube.service`, so use `systemctl restart metube`, or `docker restart metube` if you accept bypassing the guard). Plugins are read at process start; MeTube also runs yt-dlp per request in-process, so a restart is required after edits.
3. Verify: `docker exec metube yt-dlp -v --simulate <audio.com url>` shows `Extractor Plugins: ... AudioComIE` and `[AudioCom]` lines.
- MeTube cannot set `impersonate` through `YTDL_OPTIONS` (JSON, yt-dlp wants an object), which is why the extractor must pass `impersonate=True` itself. This is exactly the design chosen here.

## Installation

```bash
# Upstream dev environment (Patrick's host; yt-dlp is not installed there)
pipx install hatch                      # >= 1.10, currently 1.18.2
git clone git@github.com:<you>/yt-dlp.git && cd yt-dlp
git checkout -b audiocom
hatch run setup                         # installs pre-commit hook
hatch test AudioCom                     # after adding the extractor + _extractors.py import
hatch fmt --check                       # ruff ~=0.17.0 + autopep8 ~=2.0, upstream config

# Without hatch
python -m pip install -e ".[default,curl-cffi,dev]"
python -m devscripts.run_tests AudioCom
ruff check . && autopep8 --diff .

# Plugin compatibility check against the version MeTube actually runs
uv venv /tmp/ytdlp-2026.8.19 && uv pip install -p /tmp/ytdlp-2026.8.19 "yt-dlp[default,curl-cffi]==2026.8.19"
/tmp/ytdlp-2026.8.19/bin/yt-dlp -v --plugin-dirs ./ <url> --simulate
```

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

**If the PR is human-authored and the plugin shares code:**
- Keep one source file, converted to relative imports for the PR.
- Because both targets exercise the same tests, run `hatch test AudioCom` in the fork and the `docker exec ... --simulate` smoke check against the plugin.

**If the upstream PR is dropped (AI-assisted authoring):**
- Ship plugin-only; the plugin has no AI-policy exposure. Still follow upstream style, so a human can submit it later.

**If `curl_cffi` is ever missing (non-MeTube installs):**
- `impersonate=True` emits a warning and the plain request 403s. Add `require_impersonation=True` so the user gets a clear "install curl_cffi / yt-dlp[curl-cffi]" error rather than an opaque 403.

**If Cloudflare tightens (JS challenge/Turnstile):**
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

---
*Stack research for: yt-dlp extractor + MeTube plugin (audio.com)*
*Researched: 2026-10-28*
