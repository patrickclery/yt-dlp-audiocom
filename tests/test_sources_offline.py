"""Offline EXTR-04: the opt-in original upload, gated on is_downloadable (D-01, D-02, D-03, D-12)."""
import json

import pytest
from yt_dlp.utils import ExtractorError

from conftest import FIXTURE_PATHS, REFERENCE_ID, load_fixture, patch_api, run_extract
from test_extract_offline import BEST, BESO_ID
from yt_dlp_plugins.extractor.audiocom import AudioComIE

# Expected original ext per fixture; None = no original (not flagged downloadable).
ORIGINAL = {
    '1877766681285368': None,  # reference, wv source
    '1782423994666898': None,  # jasa-sisemore, plain wav source
    '1795055938670272': None,
    '1861573231849291': 'm4a',  # arthur-hpcp (missing on S3 live)
    '1880272428195927': 'mp3',  # roshimakr21
    '1880272004207526': None,
    '1880273150344633': None,
    '1880272651234303': 'mp3',  # shivgas: original and transcoding both mp3
    '1880272945380630': 'm4a',  # alec-murray
    '1880272416485027': 'wav',  # andrea-mathiopoulos: wavpack served as PCM wav
    '1772828397072996': None,
    '1858402410391836': None,
}
ALEC_ID = '1880272945380630'
ANDREA_ID = '1880272416485027'
SHIVGAS_ID = '1880272651234303'
RANGE = {'Range': 'bytes=0-0'}
NOT_AVAILABLE = 'Requested format is not available'


def _current_source(audio):
    # Newest by date_created; a tie goes to the later entry (D-11).
    return max(reversed(audio['sources']), key=lambda s: s['date_created'])


def _originals(info):
    return [f for f in info['formats'] if f['format_id'] == 'original']


def _debug_recorder(monkeypatch):
    messages = []
    monkeypatch.setattr(AudioComIE, 'write_debug', lambda self, msg, *args, **kwargs: messages.append(msg))
    return messages


def _skips(messages):
    return [m for m in messages if m.startswith('Skipping original upload')]


def _extract(monkeypatch, data, params=None):
    patch_api(monkeypatch, data['oembed'], data['audio'])
    return run_extract(data['url'], params)


def _alec():
    return load_fixture(ALEC_ID)


def test_original_table_matches_fixtures():
    assert set(ORIGINAL) == {p.stem for p in FIXTURE_PATHS}
    for track_id, ext in ORIGINAL.items():
        assert (ext is not None) == (load_fixture(track_id)['audio']['is_downloadable'] is True), track_id


def test_original_only_when_downloadable(fx, probe):
    data, _ = fx
    audio = data['audio']
    info, _ = run_extract(data['url'])
    originals = _originals(info)
    expected = ORIGINAL[audio['id']]
    assert len(originals) == (expected is not None)
    if expected is None:
        return
    (original,) = originals
    assert original['ext'] == expected
    assert original['url'] == _current_source(audio)['url']
    assert original['preference'] == -10
    assert original['vcodec'] == 'none'
    assert original['format_note'] == 'original upload'
    assert 'quality' not in original


def test_probe_only_for_downloadable(fx, probe):
    data, _ = fx
    audio = data['audio']
    run_extract(data['url'])
    if ORIGINAL[audio['id']] is None:
        assert probe.calls == []
        return
    assert len(probe.calls) == 1
    url, headers, kwargs = probe.calls[0]
    assert url == _current_source(audio)['url']
    assert headers == RANGE
    assert not [k for k in kwargs if 'imperson' in k]


def test_no_source_url_leaks_when_not_downloadable(fx):
    # Signed source URLs download without auth, so none may reach the info dict.
    data, _ = fx
    audio = data['audio']
    if ORIGINAL[audio['id']] is not None:
        pytest.skip('downloadable fixture')
    info, processed = run_extract(data['url'])
    dumped = json.dumps(info, default=str) + json.dumps(processed, default=str)
    for source in audio['sources']:
        assert source['url'] not in dumped


@pytest.mark.parametrize('params', [{}, {'format': 'ba'}, {'format_sort': ['abr']}, {'format_sort': ['size']}],
                         ids=['default', 'f-ba', 'S-abr', 'S-size'])
def test_original_never_selected_by_default_or_ranking(fx, params):
    data, _ = fx
    if ORIGINAL[data['audio']['id']] is None:
        pytest.skip('no original on this fixture')
    _, processed = run_extract(data['url'], params)
    assert processed['format_id'] != 'original'
    if not params:
        assert processed['format_id'] == BEST[data['audio']['id']]


def test_f_original_selects_original_or_is_unavailable(fx):
    data, _ = fx
    if ORIGINAL[data['audio']['id']] is None:
        with pytest.raises(ExtractorError, match=NOT_AVAILABLE):
            run_extract(data['url'], {'format': 'original'})
        return
    _, processed = run_extract(data['url'], {'format': 'original'})
    assert processed['format_id'] == 'original'
    assert processed['ext'] == ORIGINAL[data['audio']['id']]


def test_wavpack_original_keeps_only_matching_metadata(monkeypatch):
    data = load_fixture(ANDREA_ID)
    source = _current_source(data['audio'])
    assert source['codec'] == 'wavpack' and source['format'] == 'wav'
    (original,) = _originals(_extract(monkeypatch, data)[0])
    assert original['ext'] == 'wav'
    for key in ('acodec', 'abr', 'filesize'):
        assert key not in original
    assert original['asr'] == source['sample_rate']
    assert original['audio_channels'] == source['channels']


def test_plain_original_carries_source_metadata(monkeypatch):
    data = _alec()
    source = _current_source(data['audio'])
    (original,) = _originals(_extract(monkeypatch, data)[0])
    assert original['ext'] == 'm4a'
    assert original['acodec'] == 'aac'
    assert original['abr'] == source['bit_rate'] / 1000
    assert original['filesize'] == source['size']
    assert original['asr'] == source['sample_rate']
    assert original['audio_channels'] == source['channels']


def test_shivgas_format_ids_distinct(monkeypatch):
    # Edge (adjacency): original and transcoding are both mp3, but ids stay distinct.
    _, processed = _extract(monkeypatch, load_fixture(SHIVGAS_ID))
    ids = [f['format_id'] for f in processed['formats']]
    assert sorted(ids) == ['m4a', 'mp3', 'original']


def test_mutation_wv_source_on_downloadable_track_is_skipped(monkeypatch, probe):
    data = load_fixture(REFERENCE_ID)
    assert _current_source(data['audio'])['format'] == 'wv'
    data['audio']['is_downloadable'] = True
    messages = _debug_recorder(monkeypatch)
    info, _ = _extract(monkeypatch, data)
    assert _originals(info) == []
    assert probe.calls == []
    assert len(_skips(messages)) == 1


@pytest.mark.parametrize('flag', [False, None, 1, 'true', 'missing'])
def test_mutation_only_literal_true_opens_gate(monkeypatch, probe, flag):
    data = _alec()
    if flag == 'missing':
        del data['audio']['is_downloadable']
    else:
        data['audio']['is_downloadable'] = flag
    info, _ = _extract(monkeypatch, data)
    assert _originals(info) == []
    assert probe.calls == []


def test_mutation_probe_failure_drops_original(monkeypatch, probe):
    probe.reachable = False
    screen = []
    monkeypatch.setattr(AudioComIE, 'to_screen', lambda self, msg, *args, **kwargs: screen.append(msg))
    data = _alec()
    info, processed = _extract(monkeypatch, data)
    assert _originals(info) == []
    assert len(probe.calls) == 1
    assert sorted(f['format_id'] for f in info['formats']) == ['m4a', 'mp3']
    assert processed['format_id'] == BEST[ALEC_ID]
    (skip,) = [m for m in screen if 'original upload URL is invalid, skipping' in m]
    assert 'http' not in skip  # only the HTTP status, never the URL (T-02-11)


def test_mutation_source_without_url(monkeypatch, probe):
    data = _alec()
    _current_source(data['audio'])['url'] = None
    info, _ = _extract(monkeypatch, data)
    assert _originals(info) == []
    assert probe.calls == []


def test_mutation_flac_source(monkeypatch):
    data = _alec()
    source = _current_source(data['audio'])
    source.update(format='flac', type='audio/flac', codec='flac')
    (original,) = _originals(_extract(monkeypatch, data)[0])
    assert original['ext'] == 'flac'


def test_mutation_unknown_label_without_mime(monkeypatch, probe):
    data = _alec()
    source = _current_source(data['audio'])
    source['format'] = 'bogus'
    del source['type']
    messages = _debug_recorder(monkeypatch)
    info, _ = _extract(monkeypatch, data)
    assert _originals(info) == []
    assert probe.calls == []
    (skip,) = _skips(messages)
    assert 'bogus' in skip


def test_mutation_download_url_is_never_used(monkeypatch):
    data = _alec()
    source = _current_source(data['audio'])
    download = source['url'].rsplit('/', 1)[0] + '/download-attachment.m4a'
    source['download'] = download
    info, _ = _extract(monkeypatch, data)
    (original,) = _originals(info)
    assert original['url'] == source['url']
    assert download not in json.dumps(info, default=str)


def test_mutation_multi_version_original_is_newest(monkeypatch):
    data = load_fixture(BESO_ID)
    data['audio']['is_downloadable'] = True
    old, new = sorted(data['audio']['sources'], key=lambda s: s['date_created'])
    info, _ = _extract(monkeypatch, data)
    (original,) = _originals(info)
    assert original['url'] == new['url']
    assert old['url'] not in json.dumps(info, default=str)
