"""Offline test helpers: recorded fixtures replace AudioComIE._download_json (RESEARCH Pattern 1)."""
import copy
import json
import pathlib

import pytest
from yt_dlp import YoutubeDL

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


def run_extract(url):
    """Return (info, processed): the extractor's raw result and yt-dlp's processed copy."""
    with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
        info = AudioComIE(ydl).extract(url)
        # Deep copy: processing fills format fields in place (e.g. ext from the URL
        # path), which would mask what the extractor itself returned.
        processed = ydl.process_ie_result(copy.deepcopy(info), download=False)
    return info, processed
