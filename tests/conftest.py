"""Offline test helpers: recorded fixtures replace AudioComIE._download_json (RESEARCH Pattern 1).

The original-upload probe (_probe_original -> _request_webpage) is a second network
path, so the autouse `probe` fixture stubs it for every test (RESEARCH Pattern 3).
"""
import copy
import io
import json
import pathlib

import pytest
from yt_dlp import YoutubeDL
from yt_dlp.networking import Response
from yt_dlp.networking.exceptions import HTTPError, TransportError
from yt_dlp.utils import ExtractorError

from yt_dlp_plugins.extractor.audiocom import AudioComIE

FIXTURE_DIR = pathlib.Path(__file__).parent / 'fixtures'
FIXTURE_PATHS = sorted(FIXTURE_DIR.glob('*.json'))
API = 'https://api.audio.com'
REFERENCE_ID = '1877766681285368'


def load_fixture(stem):
    return json.loads((FIXTURE_DIR / f'{stem}.json').read_text(encoding='utf-8'))


def _date(source):
    try:
        return int(source.get('date_created'))
    except (TypeError, ValueError):
        return 0


def current_transcodings(audio):
    """The test oracle's statement of D-11: the transcodings of the newest upload.

    Newest = largest integer date_created (missing or non-numeric counts as 0; a
    tie goes to the later list entry). Returns the URL-bearing transcodings whose
    source_id is that source's id, or every URL-bearing transcoding when there are
    no sources or none match.
    """
    playable = [t for t in audio.get('transcodings') or [] if t.get('url')]
    newest = None
    for source in audio.get('sources') or []:
        if source.get('id') and (newest is None or _date(source) >= _date(newest)):
            newest = source
    if newest is None:
        return playable
    return [t for t in playable if str(t.get('source_id')) == str(newest['id'])] or playable


def patch_api(monkeypatch, oembed, audio, track_id=None):
    """Serve `oembed` and `audio` for the two API requests; any other URL fails the test.

    `track_id` is the id the /audio/<id> request is expected to use. It defaults to
    audio['id'] and only needs passing when a test deliberately mutates that id.
    """
    calls = []
    audio_url = f'{API}/audio/{track_id or audio["id"]}'

    def fake(self, url_or_request, video_id, *args, query=None, **kwargs):
        calls.append((url_or_request, query, kwargs))
        if url_or_request == f'{API}/oembed':
            return copy.deepcopy(oembed)
        if url_or_request == audio_url:
            return copy.deepcopy(audio)
        raise AssertionError('unexpected request')

    monkeypatch.setattr(AudioComIE, '_download_json', fake)
    return calls


@pytest.fixture(params=FIXTURE_PATHS, ids=lambda p: p.stem)
def fx(request, monkeypatch):
    data = json.loads(request.param.read_text(encoding='utf-8'))
    calls = patch_api(monkeypatch, data['oembed'], data['audio'])
    yield data, calls


class _Probe:
    """Record of the stubbed probe: `calls` lists (url, headers, kwargs) per request."""

    def __init__(self):
        self.calls = []
        self.reachable = True
        self.transport_error = None  # message for a TransportError, e.g. a URL-quoting one


@pytest.fixture(autouse=True)
def probe(monkeypatch):
    """Stub AudioComIE._request_webpage so no test can reach S3; never does I/O.

    While `probe.reachable` is True (default) the request succeeds; set it to
    False to make it fail like a missing S3 object (HTTP 404). Set
    `probe.transport_error` to a message to make it fail like a connection error.
    """
    state = _Probe()

    def fake(self, url_or_request, video_id, *args, headers=None, **kwargs):
        state.calls.append((url_or_request, headers, kwargs))
        if state.transport_error:
            # yt-dlp's own wrapping: the ExtractorError text embeds str(cause).
            raise ExtractorError(f'Unable to download webpage: {state.transport_error}',
                                 cause=TransportError(state.transport_error))
        if not state.reachable:
            response = Response(io.BytesIO(b''), url_or_request, {}, status=404, reason='Not Found')
            raise ExtractorError('HTTP Error 404: Not Found', cause=HTTPError(response))
        return Response(io.BytesIO(b'\0'), url_or_request, {}, status=206)

    monkeypatch.setattr(AudioComIE, '_request_webpage', fake)
    return state


def run_extract(url, params=None):
    """Return (info, processed): the extractor's raw result and yt-dlp's processed copy.

    `params` (e.g. {'format': 'original'} or {'format_sort': ['abr']}) is merged into
    the YoutubeDL options, mirroring -f and -S.
    """
    with YoutubeDL({'quiet': True, 'no_warnings': True, **(params or {})}) as ydl:
        ie = AudioComIE(ydl)
        info = ie.extract(url)
        # Deep copy: processing fills format fields in place (e.g. ext from the URL
        # path), which would mask what the extractor itself returned. The extra info
        # (extractor, webpage_url, ...) is what extract_info adds; yt-dlp's
        # "Requested format is not available" path needs it.
        processed = copy.deepcopy(info)
        ydl.add_default_extra_info(processed, ie, url)
        processed = ydl.process_ie_result(processed, download=False)
    return info, processed
