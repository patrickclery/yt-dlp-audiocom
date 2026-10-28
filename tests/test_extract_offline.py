"""Offline extraction against recorded fixtures: requests, formats, selection, EXTR-02 edges."""
import io

import pytest
from yt_dlp.networking import Response
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import ExtractorError

from conftest import API, FIXTURE_PATHS, REFERENCE_ID, load_fixture, patch_api, run_extract
from yt_dlp_plugins.extractor.audiocom import AudioComIE

# Highest-bitrate format per fixture (context table "best" column, D-07).
BEST = {
    '1877766681285368': 'm4a',  # mp3 192 < m4a 306.343
    '1782423994666898': 'mp3',  # mp3-only
    '1795055938670272': 'mp3',  # mp3-only
    '1861573231849291': 'mp3',  # mp3 160 > m4a 8.946
    '1880272428195927': 'm4a',
    '1880272004207526': 'm4a',
    '1880273150344633': 'm4a',
    '1880272651234303': 'mp3',  # mp3 160 > m4a 111.6
}


REFERENCE_SLUG = 'rusted-pitchfork-dana-liske-uncut-version-astrayal-best'
# Locked user-facing messages (D-04, D-09).
UNAVAILABLE = 'This audio.com track is unavailable (removed, private, or wrong URL)'
RESTRICTED = 'This audio.com track is private or restricted'
# Verbatim 404 bodies observed live (RESEARCH Finding 1).
OEMBED_404_BODY = b'{"name": "Not Found", "message": "Resource not found!", "code": 0, "status": 404}'
AUDIO_404_BODY = b'{"name": "Not Found", "message": "Audio not found!", "code": 0, "status": 404}'
REASONS = {401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found', 410: 'Gone', 500: 'Internal Server Error'}
# endpoint: (failing URL, video_id the error must carry, 404 body)
ENDPOINTS = {
    'oembed': (f'{API}/oembed', REFERENCE_SLUG, OEMBED_404_BODY),
    'audio': (f'{API}/audio/{REFERENCE_ID}', REFERENCE_ID, AUDIO_404_BODY),
}


def test_best_table_covers_every_fixture():
    assert set(BEST) == {p.stem for p in FIXTURE_PATHS}


def test_requests_are_canonical_without_impersonation(fx):
    data, calls = fx
    run_extract(data['url'])
    assert [(u, q) for u, q, _ in calls] == [
        ('https://api.audio.com/oembed', {'url': data['url']}),
        ('https://api.audio.com/audio/' + data['audio']['id'], None),
    ]
    assert not [k for _, _, kw in calls for k in kw if 'imperson' in k]


def test_formats_mirror_transcodings(fx):
    data, _ = fx
    info, _ = run_extract(data['url'])
    playable = [t for t in data['audio']['transcodings'] if t.get('url')]
    assert len(info['formats']) == len(playable)
    for f, t in zip(info['formats'], playable):
        assert f['ext'] == t['format']
        assert f['ext'] in {'mp3', 'm4a'}
        assert f['format_id'] == f['ext']
        assert f['vcodec'] == 'none'
        assert f['acodec'] == t['codec']
        assert f['abr'] == t['bit_rate'] / 1000
        assert f['quality'] == f['abr']
        assert f['asr'] == t['sample_rate']
        assert f['audio_channels'] == t['channels']
        assert f['filesize'] == t['size']
        assert f['url'] == t['url']


def test_mp3_only_yields_one_format(fx):
    data, _ = fx
    if [t['format'] for t in data['audio']['transcodings']] != ['mp3']:
        pytest.skip('not an mp3-only fixture')
    info, _ = run_extract(data['url'])
    assert len(info['formats']) == 1


def test_highest_bitrate_selected(fx):
    data, _ = fx
    _, processed = run_extract(data['url'])
    assert processed['format_id'] == BEST[data['audio']['id']]


def _raises_extractor_error(url):
    # extract() wraps KeyError/StopIteration as ExtractorError(cause=...); reject that too.
    with pytest.raises(ExtractorError) as exc:
        run_extract(url)
    assert not isinstance(exc.value.cause, (KeyError, TypeError, StopIteration, IndexError))
    return exc.value


def _reference():
    return load_fixture(REFERENCE_ID)


def _m4a(audio):
    return next(t for t in audio['transcodings'] if t['format'] == 'm4a')


def test_mutation_ext_from_mime_when_format_missing(monkeypatch):
    data = _reference()
    del _m4a(data['audio'])['format']
    patch_api(monkeypatch, data['oembed'], data['audio'])
    info, _ = run_extract(data['url'])
    assert sorted(f['ext'] for f in info['formats']) == ['m4a', 'mp3']


@pytest.mark.parametrize(('label', 'expected'), [('M4A', 'm4a'), ('m4a_hq', 'm4a'), ('', 'm4a')])
def test_mutation_unknown_format_label_falls_back_to_mime(monkeypatch, label, expected):
    data = _reference()
    _m4a(data['audio'])['format'] = label
    patch_api(monkeypatch, data['oembed'], data['audio'])
    info, processed = run_extract(data['url'])
    assert sorted(f['ext'] for f in info['formats']) == sorted(['mp3', expected])
    assert sorted(f['ext'] for f in processed['formats']) == sorted(['mp3', expected])


def test_mutation_unknown_format_label_without_mime_is_dropped_from_ext(monkeypatch):
    data = _reference()
    m4a = _m4a(data['audio'])
    m4a['format'] = 'm4a_hq'
    del m4a['type']
    patch_api(monkeypatch, data['oembed'], data['audio'])
    info, _ = run_extract(data['url'])
    assert 'm4a_hq' not in [f['ext'] for f in info['formats']]


def test_mutation_ext_ignores_url_path(monkeypatch):
    data = _reference()
    m4a = _m4a(data['audio'])
    m4a['url'] = m4a['url'].rsplit('.', 1)[0] + '.bin'
    patch_api(monkeypatch, data['oembed'], data['audio'])
    info, _ = run_extract(data['url'])
    assert [f['ext'] for f in info['formats'] if f['url'].endswith('.bin')] == ['m4a']


def test_edge_empty_oembed(monkeypatch):
    data = _reference()
    patch_api(monkeypatch, {}, data['audio'])
    err = _raises_extractor_error(data['url'])
    assert err.expected is True
    assert err.video_id == REFERENCE_SLUG


def test_edge_iframe_url_without_digits(monkeypatch):
    data = _reference()
    patch_api(monkeypatch, {'iframe_url': 'https://audio.com/embed/audio/abc'}, data['audio'])
    err = _raises_extractor_error(data['url'])
    assert err.expected is True
    assert err.video_id == REFERENCE_SLUG


def _patch_http_error(monkeypatch, failing_url, status, body=b''):
    """Serve the reference fixture, except `failing_url`, which fails with HTTP `status`."""
    data = _reference()
    patch_api(monkeypatch, data['oembed'], data['audio'])
    served = AudioComIE._download_json

    def fake(self, url_or_request, video_id, *args, **kwargs):
        if url_or_request == failing_url:
            response = Response(io.BytesIO(body), url_or_request, {}, status=status, reason=REASONS[status])
            raise ExtractorError(f'HTTP Error {status}: {REASONS[status]}', cause=HTTPError(response))
        return served(self, url_or_request, video_id, *args, **kwargs)

    monkeypatch.setattr(AudioComIE, '_download_json', fake)
    return data


def _http_error(monkeypatch, endpoint, status):
    failing_url, _, body_404 = ENDPOINTS[endpoint]
    data = _patch_http_error(monkeypatch, failing_url, status, body_404 if status == 404 else b'')
    return _raises_extractor_error(data['url'])


def _assert_one_line_expected(err, msg, video_id):
    assert err.expected is True
    assert err.msg == msg
    assert err.video_id == video_id
    text = str(err)
    assert 'report this issue' not in text
    assert 'HTTP Error' not in text
    assert '\n' not in text


@pytest.mark.parametrize('status', [404, 410])
@pytest.mark.parametrize('endpoint', list(ENDPOINTS))
def test_edge_unavailable_is_one_line_expected_error(monkeypatch, endpoint, status):
    _assert_one_line_expected(_http_error(monkeypatch, endpoint, status), UNAVAILABLE, ENDPOINTS[endpoint][1])


@pytest.mark.parametrize('status', [401, 403])
@pytest.mark.parametrize('endpoint', list(ENDPOINTS))
def test_edge_restricted_is_one_line_expected_error(monkeypatch, endpoint, status):
    _assert_one_line_expected(_http_error(monkeypatch, endpoint, status), RESTRICTED, ENDPOINTS[endpoint][1])


@pytest.mark.parametrize('endpoint', list(ENDPOINTS))
def test_edge_500_is_reraised_unchanged(monkeypatch, endpoint):
    err = _http_error(monkeypatch, endpoint, 500)
    assert err.msg not in (UNAVAILABLE, RESTRICTED)
    assert isinstance(err.cause, HTTPError) and err.cause.status == 500


def test_unlisted_track_extracts_like_public(monkeypatch):
    # D-09: is_public false means unlisted, which plays anonymously by link.
    results = {}
    for is_public in (True, False):
        data = _reference()
        data['audio']['is_public'] = is_public
        patch_api(monkeypatch, data['oembed'], data['audio'])
        info, _ = run_extract(data['url'])
        results[is_public] = ([f['format_id'] for f in info['formats']], info['title'], info['duration'])
    assert results[False] == results[True]
    assert results[False][0]


def test_edge_no_transcodings(monkeypatch):
    data = _reference()
    data['audio']['transcodings'] = []
    patch_api(monkeypatch, data['oembed'], data['audio'])
    err = _raises_extractor_error(data['url'])
    assert err.expected is True
    assert err.video_id == REFERENCE_ID


def test_edge_all_transcoding_urls_null(monkeypatch):
    data = _reference()
    for t in data['audio']['transcodings']:
        t['url'] = None
    patch_api(monkeypatch, data['oembed'], data['audio'])
    _raises_extractor_error(data['url'])


def test_edge_api_id_mismatch(monkeypatch):
    data = _reference()
    data['audio']['id'] = '0000000000000000'
    patch_api(monkeypatch, data['oembed'], data['audio'], track_id=REFERENCE_ID)
    err = _raises_extractor_error(data['url'])
    assert err.video_id == REFERENCE_ID
    msg = str(err)
    assert '0000000000000000' in msg and REFERENCE_ID in msg


@pytest.mark.parametrize('bad_id', [999, None])
def test_edge_api_id_non_string_mismatch(monkeypatch, bad_id):
    data = _reference()
    data['audio']['id'] = bad_id
    patch_api(monkeypatch, data['oembed'], data['audio'], track_id=REFERENCE_ID)
    assert REFERENCE_ID in str(_raises_extractor_error(data['url']))


def test_edge_api_id_integer_match_accepted(monkeypatch):
    data = _reference()
    data['audio']['id'] = int(REFERENCE_ID)
    patch_api(monkeypatch, data['oembed'], data['audio'], track_id=REFERENCE_ID)
    assert run_extract(data['url'])[0]['id'] == REFERENCE_ID


def test_edge_iframe_url_partial_digit_run(monkeypatch):
    data = _reference()
    patch_api(monkeypatch, {'iframe_url': f'https://audio.com/embed/audio/{REFERENCE_ID}abc'}, data['audio'])
    _raises_extractor_error(data['url'])
