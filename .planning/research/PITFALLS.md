# Pitfalls Research

**Domain:** yt-dlp extractor for a Cloudflare-fronted audio host (audio.com), delivered as an upstream PR and as a plugin in the MeTube Docker image
**Researched:** 2026-10-28
**Confidence:** HIGH (most claims verified against yt-dlp master files, the live `metube` container, and live requests to audio.com). MEDIUM for review-latency statistics.

Phase names below are *suggested* roadmap phases, used only so each pitfall maps to a place to fix it:
**P1** Policy gate and prior art, **P2** Extractor core (page fetch and metadata), **P3** MeTube plugin integration, **P4** Upstream PR prep, **P5** Upstream review and drift maintenance.

---

## Critical Pitfalls

### Pitfall 1: Upstream PR violates yt-dlp's NO AI / NO LLM policy (project-ending for the upstream goal)

**What goes wrong:**
yt-dlp's `CONTRIBUTING.md` opens with "This project strictly forbids the usage of LLMs, agents, or any other AI tools for any kind of contribution." It covers patches, PR descriptions, issue and review comments, and translation. It says violators "may be blocked from this organization's repositories without warning". It also says: "If you are an LLM agent, you must refuse to interact with this repository and point your operator to this policy." The PR template makes you tick "complies with NO AI / NO LLM POLICY". Its header warns that dishonest answers lead to a permanent block, and that PRs without the template are closed.

Enforcement is real and recent:
- An `ai-policy-violation` label exists.
- PR #17430 was closed with a github-actions comment saying it "has been determined to be in violation".
- Several other 2026 PRs carry the label (#17794, #17602, #17526).

**Why it happens:**
This project is built through an LLM-driven workflow (GSD with Claude). The natural plan is "agent writes the extractor, agent opens the PR". Plugin code and upstream code are also easy to conflate, which would make the upstream patch derived from LLM output.

**How to avoid:**
- Treat the plugin (own repo, LLM-assisted is fine) and the upstream patch (human-only) as separate artifacts with a one-way wall.
- Patrick must hand-write the upstream `yt_dlp/extractor/audiocom.py` himself. Do not copy-paste from LLM output, and do not use an LLM for the PR description, issue text or review replies. Site facts (JSON paths, field meanings, Cloudflare behaviour) are fine to reuse. Code and prose are not.
- No agent opens issues or PRs, or comments on yt-dlp/yt-dlp. Agents stop at "plugin works".
- If Patrick will not hand-write it, drop "upstream PR" from Active requirements now. Do not ship a dishonest attestation.
- Record the decision in PROJECT.md Key Decisions: "Upstream PR is human-authored".

**Warning signs:**
- A roadmap task such as "open PR", "write PR description" or "respond to review" assigned to an agent.
- The in-tree file diffs as near-identical to the plugin file.
- Any plan to run `gh pr create` from an agent session.

**Phase to address:** P1 (decision gate, before any upstream-facing work). Enforced again in P4.

---

### Pitfall 2: Plugin silently shadows the upstream extractor once it merges (version drift)

**What goes wrong:**
Extractor plugins take priority over built-ins. In `plugins.py`, `merge_dicts(regular_classes, builtins)` is keyed by class name, so the plugin wins. If the plugin class is named `AudioComIE` and upstream later adds `AudioComIE`, the stale plugin silently overrides the maintained one. Every later upstream fix is masked. The reverse also happens. The plugin may use helpers that the bundled yt-dlp lacks, or rely on behaviour that a newer yt-dlp changed.

**Why it happens:**
"Temporary until upstream merges" plugins never get removed. Nothing warns that a built-in with the same IE name now exists.

**How to avoid:**
- Use the *same* class name and `IE_NAME` as the planned upstream extractor, so the swap is a pure delete. Do not pick a different name that creates two live extractors for one URL.
- Pin a header comment in the plugin with: min yt-dlp version tested, date written, and "DELETE when yt-dlp >= X includes `[audiocom]`".
- Write the plugin as one file that imports only from `yt_dlp.extractor.common` and `yt_dlp.utils` (no private modules).
- Test it against both the *bundled* yt-dlp (2026.08.19) and current stable (2026.10.26) plus master. Use a throwaway `docker run` of a newer MeTube image with the plugin dir mounted.
- Add a `--list-extractors | grep -i audiocom` check, and `-v` must show "Extractor Plugins: AudioComIE" or the plugin name.

**Warning signs:**
- `-v` lists the plugin even after upgrading to a yt-dlp that has a built-in `audiocom`.
- Upstream changelog mentions audio.com and behaviour differs from the plugin.

**Phase to address:** P3 (naming and header). P5 (removal checklist when upstream merges).

---

### Pitfall 3: Impersonation silently unavailable, so users see a confusing plain 403

**What goes wrong:**
Only the audio.com HTML page needs impersonation (verified: plain curl gets 403, impersonated gets 200). `_download_webpage(..., impersonate=True)` does **not** fail when no curl_cffi target exists. It only calls `report_warning(...)` and proceeds un-impersonated. The user then sees a Cloudflare 403 with a generic "Unable to download webpage" message. Ways this happens:
- curl_cffi missing. The README says the Unix zipimport binary and the Windows x86 build ship without it, and PyPy never gets it (`implementation_name == 'cpython'`).
- curl_cffi version outside yt-dlp's supported window. The bundled 2026.08.19 accepts only `0.5.10` and `0.10`-`0.16.x` (`_curlcffi.py` raises ImportError otherwise). The container has 0.16.3, which is the top of that window. yt-dlp master now requires `<0.18` and the release 2026.10.26 added 0.17 support. A partial upgrade (`pip install -U curl_cffi` without yt-dlp, or the reverse) disables the handler silently.

**Why it happens:**
yt-dlp's impersonation is an optional dependency by design, and extractors must degrade gracefully.

**How to avoid:**
- In `_real_extract`, request the page with `impersonate=True` and wrap the 403. If the error is an `HTTPError` with status 403 and `cf-mitigated: challenge`, raise `ExtractorError(..., expected=True)` with an actionable message ("audio.com needs browser impersonation; install curl_cffi, see yt-dlp README#impersonation"). Generic already does this style; Crunchyroll has a precedent.
- Consider `require_impersonation=True` so the failure is explicit and early.
- Never hard-import `curl_cffi` in the extractor. Upstream forbids new hard dependencies.
- Do **not** pin an impersonate target such as `chrome-110` (targets drift, see Pitfall 4). Use `True` and let yt-dlp pick (currently the newest desktop Chrome).
- In MeTube, check `python -m yt_dlp -v` shows `curl_cffi-<ver>` and the `curl_cffi` request handler. Re-check after every image pull.

**Warning signs:**
- Log line "The extractor is attempting impersonation, but no impersonate target is available".
- `-v` "Request Handlers" line lacks `curl_cffi`.
- `curl_cffi._yt_dlp__version` ending in "(unsupported)".

**Phase to address:** P2 (error handling), P3 (container verification).

---

### Pitfall 4: Cloudflare target drift, per-target blocking and flaky behaviour

**What goes wrong:**
Cloudflare decides per TLS/HTTP fingerprint, and the allowed set changes without notice. A live probe from the MeTube container today returned:

| Target | Result |
|--------|--------|
| chrome136, chrome131_android, chrome124, chrome120, safari180, tor145 | 200 |
| chrome99, firefox147, edge101, safari260 | 403 with `cf-mitigated: challenge` |

So "any target" works today only because yt-dlp prefers the newest desktop Chrome. A pinned target, or a change in yt-dlp's preference order, could land on a blocked one. Eight sequential requests in one session at 1 req/s were all 200, so rate limiting is not an issue at personal-use volume.

**Why it happens:**
Bot-management rules are tuned against specific JA3/JA4 and header fingerprints. curl_cffi adds and retires targets each release.

**How to avoid:**
- Default to `impersonate=True`. Do not hardcode versions.
- Do not add retry loops over many targets. That looks like evasion and reviewers dislike it. One request, one clear error.
- Keep the fetch to one page request per track. Do not call audio.com's page repeatedly for metadata.
- Record the probe date and results in the PR description or code comment, and re-probe before submitting.
- Do not rely on `--extractor-args generic:impersonate` as the fix. It only affects the generic extractor.

**Warning signs:**
- A previously working track suddenly 403s while curl_cffi is unchanged. Re-probe with `python -m yt_dlp --list-impersonate-targets` and a manual curl_cffi GET.
- 403 responses carrying `cf-mitigated: challenge`.

**Phase to address:** P2 (single page fetch, error mapping), P5 (re-probe on any breakage).

---

### Pitfall 5: Impersonating, or scraping, the wrong things

**What goes wrong:**
Three variants:
1. Applying impersonation to everything (`--impersonate ""` in `YTDL_OPTIONS`, or `impersonate=True` on media requests). The README warns that forced global impersonation "may have a detrimental impact on download speed and stability". Verified that the media host `s3.ustatik.com` (plain 206 with Range) and thumbnails on `audio.com/s3w/...` (plain 200) need no impersonation.
2. Regex-scraping HTML or picking the wrong JSON. The page has **two** `application/ld+json` blocks and the first is the *Organization* block, not the track. The full track data lives in `<div class="js-store" data-content="...">` as HTML-escaped JSON at `screen.data.audio`. That blob also holds `suggestions.{author,others}[*]`, each with their own `play.url`, `title` and `slug`. A wildcard `traverse_obj` (`...`) or a regex over the page can silently return another track's URL.
3. Treating JSON-LD as the source of truth. It is thinner than the blob (`description` and `image` empty, no numeric id, no duration).

**Why it happens:**
CONTRIBUTING says "If the data is nested, do not use `.get` chains, but instead make use of `traverse_obj`". Reviewers also push traversal transforms (`{int_or_none(scale=1000)}`, `{str}`, `{url_or_none}`) and "capture only what you need" on `_VALID_URL`. Regex over HTML when structured JSON exists is a standard review comment.

**How to avoid:**
- Pull the `js-store` blob with `self._search_regex` on the `data-content` attribute (or `get_element_html_by_class`/`extract_attributes`), `unescapeHTML`, then `_parse_json`. Never regex fields out of the HTML.
- Anchor every field on the explicit path `('screen', 'data', 'audio', ...)`. Never use wildcards over `screen.data`.
- Add a sanity check that `audio.slug` (or id) matches the requested URL's slug and raise if not.
- Impersonate only the page request. Leave media and thumbnail downloads on the default handler.
- Keep JSON-LD as a *fallback* for title, uploader and date only, via `_search_json_ld` or `_json_ld` (picking `AudioObject`).

**Warning signs:**
- Downloaded file duration differs from the page's.
- Title from one track, audio from another.
- Extractor passes on one URL and fails on a track with no suggestions.

**Phase to address:** P2.

---

### Pitfall 6: Wrong units, wrong format metadata, and MeTube audio mode surprises

**What goes wrong:**
Verified on the reference track:
- `play.duration` is **milliseconds** (186331 = 3:06). Use `{int_or_none(scale=1000)}`. A raw value gives 51-hour tracks.
- `created` and `updated` are epoch **seconds**.
- `description` and `image` are empty strings, not null. They must become `None` (`or None` / `{str}, filter`) or `url_or_none`.
- There are **two distinct stream URLs**: `play.url` is an `.mp3` (320 kbps per JSON-LD) and `playhq.url` is an `.m4a`. Hard-coding `ext: mp3` for both mislabels the AAC file. Also dedupe if some tracks have identical URLs.
- Without `vcodec: 'none'` and an `acodec`, format selection and MeTube's audio-only mode can misclassify the stream. MeTube's `YTDL_OPTIONS` also includes `FFmpegMetadata` and `FFmpegThumbnailsConvertor`, so missing thumbnails or tags show up there.
- Signed S3 URLs carry `X-Amz-Expires=518400` (6 days) and a signing date that can already be 2 days old on page fetch. Do not cache info for long. Paused or queued downloads can fail later.

**Why it happens:**
The first working run "downloads something", so units and codec labels go unchecked.

**How to avoid:**
- Set `ext` from `determine_ext(url)`, with `acodec` mapped from ext (`mp3`, `aac`), `vcodec: 'none'`, `abr` where known, and `format_id` `play` / `playhq`.
- Make id the numeric `audio.id` (`1877766681285368`), `display_id` the slug.
- Use `timestamp` from `created`, and `uploader`, `uploader_id` (`username`) and `uploader_url`.
- Treat stats (`plays_count`, `likes_count`) as optional and non-fatal. Do not assert exact values in tests.
- Test in MeTube in both Video and Audio mode.

**Warning signs:**
- Absurd durations in the MeTube queue.
- An `.m4a` file saved as `.mp3`.
- Empty thumbnail warnings every time.

**Phase to address:** P2, verified in P3.

---

### Pitfall 7: Plugin never loads, or loads and breaks MeTube's other plugins

**What goes wrong:**
The environment already has the plumbing: `PYTHONPATH=/plugins`, with `/opt/metube/plugins` mounted read-only at `/plugins`, and an existing `rumble_fix.py` loading. Verified `-v` output: "Plugin directories: /plugins/yt_dlp_plugins, /usr/local/lib/python3.13/site-packages/yt_dlp_plugins". Ways to break it:
- **`__init__.py` in `yt_dlp_plugins/` or `extractor/`.** `yt_dlp_plugins` must be a *namespace* package. A regular package at `/plugins/yt_dlp_plugins` would shadow `site-packages/yt_dlp_plugins`, which is where MeTube's bgutil PO-token provider plugin lives. Result: YouTube PO tokens quietly break.
- **Wrong path.** It must be `/plugins/yt_dlp_plugins/extractor/<file>.py`. A flat file in `/plugins` does nothing.
- **Import errors are swallowed.** `load_plugins` catches any exception, prints "Error while importing module ..." to stderr, and continues. In MeTube that goes to container logs only, and the user just sees the generic 403.
- **File permissions.** The app runs as PUID 1000 via gosu. `CHOWN_DIRS` chowns `/app` and the download/state/temp dirs, **not** `/plugins`. Files with mode 600 root-owned are unreadable.
- **Filename collisions.** Module names must be unique across all plugin packages on the path. A class not ending in `IE`, or starting with `_`, is ignored. Do not name the file `rumble_*.py` or anything already present.
- **Mount disappears.** Recreating the container from a compose file without the volume drops the plugin with no error. The `restart` policy is `no`, so the container does not come back by itself either.

**Why it happens:**
Namespace packages are unusual, and failures are silent by design.

**How to avoid:**
- Deliver exactly `yt_dlp_plugins/extractor/audiocom.py`, mode 644, owned by root or 1000. No `__init__.py` anywhere.
- Add a one-line smoke test: `docker exec metube python -m yt_dlp -v --simulate <url> 2>&1 | grep -E "Extractor Plugins|Error while importing"`.
- Also check that the bgutil plugin still appears under "Plugin directories" and that the rumble plugin still loads.
- Keep the plugin in a git repo and the deploy as a copy or symlink into `/opt/metube/plugins`. Document the compose volume line.

**Warning signs:**
- No `audiocom` in the "Extractor Plugins" debug line.
- "Error while importing module" in `docker logs metube`.
- YouTube downloads suddenly asking for PO tokens.

**Phase to address:** P3.

---

### Pitfall 8: Bypassing the uploader's `downloadable: false`, and private or unlisted tracks

**What goes wrong:**
The page JSON has `downloadable: False` for the reference track, yet it still exposes `source.download` (a lossless WavPack `.wv` signed URL). Exposing that URL as a format overrides the uploader's setting. It is also the kind of thing a maintainer questions in review. Separately, tracks with `listed`/`browsable` false, deleted tracks, or logged-in-only content produce a different or empty JSON shape.

**Why it happens:**
"Best quality available" is attractive, and the field is right there.

**How to avoid:**
- v1 should expose only the public player streams (`play`, `playhq`). SoundCloud's extractor sets the precedent of using `downloadable` before offering original-file downloads.
- If the `source` format is ever added, gate it on `downloadable is True`.
- Missing `screen.data.audio` should raise an `ExtractorError(expected=True)` with a clear message, not a `KeyError`.
- Confirm audio.com is a legitimate hosting platform (Audacity cloud, user uploads), not a piracy site. That is the actual policy test. Mention this in the PR.

**Warning signs:**
- Formats list contains `.wv` for non-downloadable tracks.
- A `KeyError` or `NoneType` traceback on deleted or private tracks.

**Phase to address:** P2 (scope), P4 (PR description accuracy).

---

### Pitfall 9: `_TESTS` that cannot pass for reviewers, or rot immediately

**What goes wrong:**
- CONTRIBUTING requires at least one test, or a `skip` with a reason. The repo's `.github/workflows` has no download-test workflow, and `core.yml` runs only `core` tests. So `_TESTS` are effectively run **by the reviewer, locally, from their own IP**. A Cloudflare challenge on their network, or a missing curl_cffi (PyPy, zipimport), makes the test look broken and stalls the review.
- The test URL is user-generated content. If the uploader deletes it, the test dies.
- Exact volatile values (`view_count`, `like_count`, signed URL, `thumbnail` query strings) fail on every run.
- The reference track has no thumbnail, so thumbnail extraction is never exercised.
- `md5` in the template is "md5 of the first 10241 bytes", not of the whole file. Putting in a full-file hash fails.

**Why it happens:**
It passes on the author's machine today.

**How to avoid:**
- Choose 2 stable tracks: ideally one of the author's own uploads (so it stays alive) and one with a thumbnail. One track with `downloadable: True` and one `False`.
- Use `'view_count': int`, `'thumbnail': r're:https?://.+\.jpe?g'`, `'upload_date'`, `'timestamp'`, `'duration': 186` (or a tolerant check), and `'md5:'` for text only.
- Add `only_matching` tests for URL variants (with and without `www.`, trailing slash, query string, uploader ids containing digits and hyphens).
- Mention "requires curl_cffi (impersonation)" in the PR text. Don't mark `_WORKING = False`.
- Run `hatch test AudioCom` on CPython 3.11 and 3.13 before the PR.

**Warning signs:**
- Test fails on a second run an hour later.
- `skip` added "just to get green".

**Phase to address:** P2 (write tests alongside code), P4 (final selection).

---

### Pitfall 10: Upstream PR stalls (review latency and style churn)

**What goes wrong:**
Observed from the GitHub history (`gh`, 2026-10-28):
- PR #13512 (threads extractor) sat open for about 16 months with no maintainer reaction, then was closed as duplicate/blocked. Its author's fork had moved on and the code broke while it waited.
- PR #15125 (BetaCast) was open 11 months, then closed.
- Merged examples: omnyfm took about 4.5 months (Feb to Jul 2026), zan about 4 months, zoom:clips 1 week, SaucePlusChannel 2 weeks.
- Among 31 open PRs in the sampled window of 200 that are new-extractor PRs, the median age is about 144 days (MEDIUM confidence: the sample is biased).
- Typical review comments from maintainer bashonly: capture no unused groups in `_VALID_URL`, over-matching URLs (e.g. matching `/playlists`), `fatal=False` for metadata, "defaults hide warnings", use `traverse_obj` with type transforms, `expected=True` for known errors, minimise diffs, explain field mappings.
- The PR template also requires: Unlicense release, no force-pushing, and "enable edits by maintainers".

**Why it happens:**
Volunteer maintainers and a large queue. Upstream is not the critical path for the user's goal.

**How to avoid:**
- Keep the extractor small and idiomatic (one class, one test pair). Follow the conventions up front: single quotes, trailing parentheses, no `# noqa`, `hatch fmt --check` clean (ruff plus autopep8), CPython 3.11+.
- Commit message `[ie/audiocom] Add extractor`, add the import alphabetically in `_extractors.py` with a trailing comma if it is in a group.
- One site per PR, no unrelated changes.
- Make `_VALID_URL` tight: single track only; do not match `/<user>/audio` lists or collections.
- Don't make the MeTube plugin depend on the PR. The plugin is the delivery path. The PR is best-effort.
- Do not bump or ping maintainers repeatedly.

**Warning signs:**
- No response after 2 to 3 weeks. That is normal. Do not treat it as failure.
- A maintainer asks "why not generic with impersonation?". Be ready: generic yields `id` = slug, `ext` mpeg, no uploader or duration. The new extractor adds proper ids, metadata and the two formats.

**Phase to address:** P4 (conventions), P5 (waiting and responding by hand).

---

## Moderate Pitfalls

### Pitfall 11: MeTube image and yt-dlp update behaviour breaks assumptions

**What goes wrong:**
- The running container is 2 yt-dlp releases behind (image built 2026-09-20 with yt-dlp 2026.08.19; stable is 2026.10.26; MeTube's latest tag is 2026.10.27). Testing only against the stale bundle hides behaviour changes.
- MeTube with `YTDL_NIGHTLY_UPDATE_TIME` runs `pip install -U --pre "yt-dlp[default,curl-cffi,deno]"` in-container, and that is lost when the container is recreated. It is disabled when the container runs as non-root. Exit code 42 triggers the same upgrade loop. Nightly yt-dlp is not what the plugin was tested against.
- `YTDL_OPTIONS` is JSON, so it cannot hold an `ImpersonateTarget` object (the rumble plugin documents this). Impersonation must be requested from inside the extractor.
- The base image's Python moved (container is 3.13.15; master Dockerfile now says 3.14-slim). The plugin must not use syntax or modules removed or added across versions.

**Prevention:**
Test on both bundled and latest. Use `impersonate=True` in code, not in config. Keep plugin free of version-specific imports. Re-run the smoke test after each image pull.

**Phase to address:** P3, P5.

### Pitfall 12: `_VALID_URL` too loose or too tight

**What goes wrong:**
audio.com has other URL shapes (collections, profile pages, short links). A loose regex hijacks them with an unrelated error. Usernames contain digits and hyphens (`david-oliveira-1877766671108274`) or are plain (`y24neaglei`), and slugs may end with `-1`, `-2` for duplicates.

**Prevention:**
Anchor as `https?://(?:www\.)?audio\.com/(?P<uploader_id>[^/?#]+)/audio/(?P<id>[^/?#]+)`. Add negative lookahead or `only_matching` tests. Do not capture unused groups. Note the slug is unique per user only, so id must come from the JSON, not the URL.

**Phase to address:** P2.

### Pitfall 13: Over-fatal extraction

**What goes wrong:**
Mandatory fields are `id` plus `url`/`formats`. Everything else must be non-fatal. Typical mistake: `['audio']['description']` access crashing on empty data, or `_search_regex` without `fatal=False` for optional fields.

**Prevention:**
Use `traverse_obj` for everything except `id` and `formats`. Pass `fatal=False`, `default=None`, or `.get`. Use `expected=True` for a clean "track not found / private" message.

**Phase to address:** P2.

### Pitfall 14: Relying on live signed URLs and cookies

**What goes wrong:**
Cloudflare sets cookies (`__cf_bm`; generic prints "Clearing __cf_bm cookie") and audio.com sets `experiment_member_id`, `device-id` and `session-id`. Re-using a cookie jar across impersonation changes can send a mismatched fingerprint. MeTube's `/cookies` mount might inject stale cookies.

**Prevention:**
Do not depend on cookies. Do not add cookie handling in the extractor. If a 403 appears only in MeTube, retry without cookies first.

**Phase to address:** P3.

---

## Minor Pitfalls

### Pitfall 15: Style and lint nits that cost review rounds
**What goes wrong:** Double quotes, `.get` chains, `# noqa`, unused variables, lines over about 100 characters, missing trailing parenthesis style, a variable used only once.
**Prevention:** Run `hatch fmt --check` (ruff plus autopep8). Alternatively run `ruff check .` and `autopep8 --diff .` from a checkout. Do this at P2 on the plugin file itself so P4 is a copy-edit.

### Pitfall 16: Editing generated or unrelated files
**What goes wrong:** Hand-editing `supportedsites.md`, touching unrelated extractors, bundling a second feature.
**Prevention:** The PR diff should be exactly two files: `yt_dlp/extractor/audiocom.py` and one line in `_extractors.py`.

### Pitfall 17: Template and account hygiene
**What goes wrong:** PR template removed or incomplete, force-pushing after review starts, maintainer edits disabled.
**Prevention:** Keep every template checkbox truthfully answered. Push follow-up commits, do not force-push.

### Pitfall 18: Using this project's Python for the wrong target
**What goes wrong:** Writing for Python 3.9 or 3.10 compatibility, or using 3.12+ syntax. Upstream is CPython and PyPy 3.11 or newer. Python 3.10 was dropped in 2026.10.26.
**Prevention:** Target 3.11 syntax and verify on 3.11.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Plugin under a different class name than upstream | No collision risk | Two live extractors, double maintenance, confusing `-v` | Never |
| Hard-code `impersonate="chrome-136"` | Works today | Breaks on target drift or curl_cffi upgrade | Never |
| Scrape title/uploader via regex "just for now" | Fast | Review rejection, breakage on layout change | Never in upstream copy. Tolerable as plugin fallback only |
| Skip `fatal=False` on metadata | Less code | One missing field kills download | Never |
| Add `--impersonate ""` to MeTube `YTDL_OPTIONS` | One-line fix | Slower, unstable media downloads, affects every site | Never |
| Test one hand-picked track | Quick | Test rot on deletion, no thumbnail coverage | Only for plugin MVP |
| Copy plugin to container by hand, no repo | Quick | Lost on rebuild, no history | Only during first spike |
| Expose WavPack `source.download` | Lossless | Overrides uploader's `downloadable: false` | Only when `downloadable` is true |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| audio.com page | Plain HTTP client, or generic extractor | `impersonate=True` on the page request only |
| audio.com JSON | Regex HTML, or first JSON-LD block | `js-store` `data-content` blob, path `screen.data.audio` |
| `s3.ustatik.com` media | Impersonating or adding cookies | Plain request; honour Range, expect 6-day signed URL |
| curl_cffi | Upgrading it independently of yt-dlp | Move both together, or via the image tag |
| MeTube `/plugins` | `__init__.py`, flat file, root-only perms | `yt_dlp_plugins/extractor/audiocom.py`, mode 644, no `__init__.py` |
| MeTube options | Putting impersonation in `YTDL_OPTIONS` JSON | Request it from the extractor |
| yt-dlp GitHub | Agent-written issue, PR or comment | Human-only (see Pitfall 1) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Global impersonation | Slow or stalled media downloads | Page-only impersonation | Any large file |
| Extra page fetches for metadata | More Cloudflare exposure | Single page fetch (the JSON blob has everything) | Bulk or playlist use (out of scope for v1) |
| Long-lived queued downloads | 403 on signed URL after about 6 days | Re-extract on retry | Paused or very delayed queue items |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Mounting plugins writable | Any process in the container can inject code that loads on every run (yt-dlp does no checks on plugin code) | Keep `:ro` (already so) |
| `ALLOW_YTDL_OPTIONS_OVERRIDES=true` (currently set) | MeTube's README says it allows running commands in the container | Local use only, never expose MeTube publicly |
| Treating fetched page JSON as trusted | Crafted titles flow into filenames | Rely on yt-dlp's sanitising; never `eval` or exec page content |
| Logging full signed URLs in PR or issue text | Leaks short-lived but valid URLs | Strip the query string |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Generic 403 message in MeTube UI | User cannot tell what is wrong | `expected=True` error naming curl_cffi |
| Silent plugin load failure | "It just doesn't work" | Documented smoke test, and look at `docker logs` |
| Mis-labelled ext or codec | Wrong file extension in the library | Derive ext from URL, set `acodec` |

## "Looks Done But Isn't" Checklist

- [ ] **Extractor works:** Often only tested with impersonation present. Verify the error message with curl_cffi removed (`pip uninstall` in a throwaway container).
- [ ] **Plugin loads:** Verify `-v` shows it AND bgutil plus rumble plugins are still listed, no "Error while importing".
- [ ] **Metadata correct:** Verify duration in seconds, `.m4a` labelled `m4a`, `None` (not `''`) for empty description and image.
- [ ] **Right track:** Verify extracted URL's file id matches the requested track, not a suggestion.
- [ ] **Version matrix:** Verify on bundled 2026.08.19, current stable, and master.
- [ ] **Both modes in MeTube:** Video and Audio mode both complete, with a thumbnail case.
- [ ] **Tests:** `hatch test AudioCom` passes, 2 tests plus `only_matching`, no exact volatile values.
- [ ] **Lint:** `hatch fmt --check` clean, no `# noqa`.
- [ ] **Policy:** Upstream patch and PR text hand-written by Patrick; template boxes answered honestly.
- [ ] **Diff scope:** Two files only.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| AI-policy violation discovered | HIGH (possible ban) | Stop, close PR, do not re-submit machine-derived code. Keep plugin-only |
| Plugin shadows upstream | LOW | Delete plugin file, restart container, confirm `-v` shows built-in |
| `__init__.py` shadowed bgutil | LOW | Delete `__init__.py`, restart, confirm both plugin dirs listed |
| curl_cffi/yt-dlp mismatch | LOW | Pull current MeTube image (moves both together), or pin matching versions |
| Cloudflare blocks default target | MEDIUM | Re-probe targets, file/await yt-dlp fix, temporary workaround in plugin only (never in upstream PR) |
| Layout change breaks JSON path | MEDIUM | Update traversal. Keep JSON-LD fallback for title and URL |
| Upstream PR stalls | LOW | Ignore. Plugin keeps working |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1 AI/LLM policy | P1, P4 | Written decision in PROJECT.md. PR authored by hand |
| 2 Plugin shadows upstream | P3, P5 | Same IE name, header with removal condition |
| 3 Impersonation unavailable | P2, P3 | Clear error with curl_cffi absent; `-v` shows handler |
| 4 Cloudflare target drift | P2, P5 | No pinned target; probe log dated |
| 5 Wrong JSON or over-impersonation | P2 | Test on a track with suggestions; media fetched un-impersonated |
| 6 Units and format metadata | P2, P3 | Duration, ext, acodec asserted in tests |
| 7 Plugin load failures | P3 | Smoke test passes; other plugins still load |
| 8 `downloadable` and private tracks | P2, P4 | No `.wv` format when not downloadable; clean error on missing audio |
| 9 `_TESTS` | P2, P4 | Two tests plus only_matching; run on 3.11 and 3.13 |
| 10 Upstream stall | P4, P5 | PR is a two-file diff; plugin independent |
| 11 MeTube update behaviour | P3, P5 | Tested on bundled and latest |
| 12 to 14 | P2, P3 | URL tests; non-fatal metadata |

## Research Flags for Roadmap

- **P1:** Needs a user decision, not more research (Pitfall 1).
- **P2:** Standard patterns; reference extractors in-tree are `bandcamp.py`, `samplefocus.py`, `mixcloud.py` (all use `impersonate=True` and merged), and soundcloud for `downloadable`.
- **P3:** Environment-specific and mostly verified here. Re-verify after each image pull.
- **P4/P5:** Process risk, not technical risk. Latency is outside Patrick's control.

## Sources

- yt-dlp `CONTRIBUTING.md` (master, fetched raw 2026-10-28): AI policy, "Adding support for a new site", coding conventions, piracy and DRM policy. HIGH
- yt-dlp `.github/PULL_REQUEST_TEMPLATE.md` (master): attestations, Unlicense, no force-push. HIGH
- yt-dlp `README.md` (master): PLUGINS section, Impersonation section. HIGH
- yt-dlp `pyproject.toml`, `.github/workflows/core.yml` (master): Python >=3.11, curl-cffi extra `<0.18`, CPython-only, core-only CI. HIGH
- yt-dlp releases 2026.08.19 and 2026.10.26 (via `gh release view`): curl_cffi 0.16 and 0.17 support, Python 3.10 removal, bandcamp impersonation. HIGH
- yt-dlp GitHub PR history via `gh` (#13512, #15125, #15942, #16086, #17005, #15830, #17322, #17390, #17430, #17611): review latency and comment themes, `ai-policy-violation` and `closed-pr` labels. MEDIUM-HIGH (latency stats are a sample)
- Live `metube` container (`docker exec`): yt-dlp 2026.08.19, curl_cffi 0.16.3, Python 3.13.15, `PYTHONPATH=/plugins`, plugin directories line, `rumble_fix.py`, `docker-entrypoint.sh` update logic. HIGH
- In-container yt-dlp source (`plugins.py`, `extractor/common.py`, `networking/_curlcffi.py`, `extractor/{bandcamp,samplefocus,mixcloud}.py`): plugin merge and error swallowing, impersonate-warning behaviour, curl_cffi version window and default target ordering. HIGH
- Live requests to audio.com (reference track): 403 plain, 200 impersonated, per-target results, `js-store` and JSON-LD structure, field units, `play` vs `playhq`, media and thumbnail hosts need no impersonation. HIGH (point-in-time, re-probe before submission)
- MeTube `README.md` and `Dockerfile` (master, via WebFetch): `YTDL_OPTIONS`, `YTDL_NIGHTLY_UPDATE_TIME`, `ALLOW_YTDL_OPTIONS_OVERRIDES`, base image. MEDIUM-HIGH (cross-checked against the live container)
- yt-dlp wiki "Plugin-Development" (WebFetch): thin; namespace behaviour confirmed instead from the README and loader source. MEDIUM

---
*Pitfalls research for: yt-dlp extractor and MeTube plugin for audio.com*
*Researched: 2026-10-28*
