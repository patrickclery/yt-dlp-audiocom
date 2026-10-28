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
    assert _raises_extractor_error(data['url']).expected is True


def test_edge_iframe_url_without_digits(monkeypatch):
    data = _reference()
    patch_api(monkeypatch, {'iframe_url': 'https://audio.com/embed/audio/abc'}, data['audio'])
    assert _raises_extractor_error(data['url']).expected is True


def _patch_404(monkeypatch, failing_url):
    data = _reference()
    patch_api(monkeypatch, data['oembed'], data['audio'])
    served = AudioComIE._download_json

    def fake(self, url_or_request, video_id, *args, **kwargs):
        if url_or_request == failing_url:
            response = Response(io.BytesIO(b''), url_or_request, {}, status=404)
            raise ExtractorError('HTTP Error 404: Not Found', cause=HTTPError(response))
        return served(self, url_or_request, video_id, *args, **kwargs)

    monkeypatch.setattr(AudioComIE, '_download_json', fake)
    return data


@pytest.mark.parametrize('failing_url', [f'{API}/oembed', f'{API}/audio/{REFERENCE_ID}'])
def test_edge_404_is_expected_error(monkeypatch, failing_url):
    data = _patch_404(monkeypatch, failing_url)
    err = _raises_extractor_error(data['url'])
    assert err.expected is True
    assert 'report this issue' not in str(err)


def test_edge_no_transcodings(monkeypatch):
    data = _reference()
    data['audio']['transcodings'] = []
    patch_api(monkeypatch, data['oembed'], data['audio'])
    assert _raises_extractor_error(data['url']).expected is True


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
    msg = str(_raises_extractor_error(data['url']))
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
