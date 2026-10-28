"""Record commit-safe audio.com API fixtures through the plugin's own request path.

Usage: .venv/bin/python scripts/record_fixture.py URL [URL ...]

For each track URL this runs AudioComIE.extract() against the live API, keeps the
oEmbed and /audio/<id> JSON the plugin itself fetched, projects them onto an
allowlist of fields the extractor reads, cuts every URL at its first '?' and '#'
(the S3 presign parameters live in the query string), and writes
tests/fixtures/<audio id>.json. It prints only "<id> <fixture path>" per track and
never prints API or media URLs. Exits non-zero if any URL failed.
"""
import json
import pathlib
import sys

from yt_dlp import YoutubeDL

from yt_dlp_plugins.extractor.audiocom import AudioComIE

FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent / 'tests' / 'fixtures'

AUDIO_KEYS = ('id', 'username', 'author_name', 'title', 'description', 'image', 'avatar',
              'date_created', 'tags', 'stats', 'transcodings')
STATS_KEYS = ('plays_count', 'likes_count', 'comments_count', 'shares_count')
TRANSCODING_KEYS = ('format', 'type', 'url', 'size', 'codec', 'sample_rate', 'channels',
                    'duration', 'bit_rate')
# Matched case-insensitively against the serialized record (RESEARCH.md redaction rule).
FORBIDDEN_MARKERS = ('x-amz-', 'signature', 'token', 'client_secret', 'stripe')


class RefusedError(Exception):
    pass


def strip_url(value):
    if isinstance(value, str):
        return value.split('?', 1)[0].split('#', 1)[0]
    return value


def _require(value, typ, name):
    # Fail closed: a field of an unexpected type (e.g. transcodings as a dict keyed
    # by format) would otherwise bypass the projection and be written verbatim.
    if value is not None and not isinstance(value, typ):
        raise RefusedError(f'unexpected type for {name}')
    return value


def strings(obj):
    """Yield every string (keys and values) in a JSON-like object."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings(k)
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def check_record(rec):
    """Raise RefusedError unless a projected record is safe to commit."""
    text = json.dumps(rec, ensure_ascii=False, sort_keys=True).lower()
    hits = [m for m in FORBIDDEN_MARKERS if m in text]
    if hits:
        raise RefusedError(f'forbidden marker(s) {hits}')
    # Free text (title, description, tags) is not URL-stripped, and presign
    # schemes beyond the markers (Azure SAS, ?key=, ?expires=) live in the query.
    for s in strings(rec):
        if '://' in s and ('?' in s or '#' in s):
            raise RefusedError('URL with query or fragment')


def project(url, captured):
    user, slug = AudioComIE._match_valid_url(url).group('user', 'slug')
    audio = _require(captured['audio'], dict, 'audio')
    oembed = _require(captured['oembed'], dict, 'oembed')
    record_audio = {k: audio[k] for k in AUDIO_KEYS if k in audio}
    for key in ('image', 'avatar'):
        if key in record_audio:
            record_audio[key] = strip_url(_require(record_audio[key], str, key))
    if _require(record_audio.get('stats'), dict, 'stats') is not None:
        record_audio['stats'] = {k: v for k, v in record_audio['stats'].items() if k in STATS_KEYS}
    if _require(record_audio.get('transcodings'), list, 'transcodings') is not None:
        record_audio['transcodings'] = [
            {k: strip_url(_require(v, str, 'transcodings[].url')) if k == 'url' else v
             for k, v in _require(t, dict, 'transcodings[]').items() if k in TRANSCODING_KEYS}
            for t in record_audio['transcodings']]
    return {
        'url': AudioComIE._canonical_url(user, slug),
        'oembed': {'iframe_url': strip_url(_require(oembed.get('iframe_url'), str, 'iframe_url'))},
        'audio': record_audio,
    }


def record(url):
    captured = {}
    with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
        ie = AudioComIE(ydl)
        original = ie._download_json

        def capture(url_or_request, *args, **kwargs):
            result = original(url_or_request, *args, **kwargs)
            req_url = url_or_request if isinstance(url_or_request, str) else url_or_request.url
            if req_url.endswith('/oembed'):
                captured['oembed'] = result
            elif '/audio/' in req_url:
                captured['audio'] = result
            return result

        ie._download_json = capture
        ie.extract(url)

    rec = project(url, captured)
    check_record(rec)
    text = json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURE_DIR / f'{rec["audio"]["id"]}.json'
    path.write_text(text, encoding='utf-8')
    return rec['audio']['id'], path


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    failed = 0
    for url in argv:
        try:
            track_id, path = record(url)
        except RefusedError as e:
            failed += 1
            print(f'REFUSED {e}', file=sys.stderr)
            continue
        except Exception as e:
            failed += 1
            # Exception text is reduced to its type so no URL can leak into logs.
            print(f'FAILED {type(e).__name__}', file=sys.stderr)
            continue
        try:
            shown = path.relative_to(pathlib.Path.cwd())
        except ValueError:
            shown = path
        print(f'{track_id} {shown}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
