"""Recorded fixtures must be commit-safe: no signed URLs, secrets or unread fields (D-09, D-13).

The redaction rules live in scripts/record_fixture.py; this module reuses them so
the recorder and this test cannot drift apart (WR-07).
"""
import json
import pathlib

import pytest

from scripts.record_fixture import SOURCE_KEYS, RefusedError, check_record, project

FIXTURE_DIR = pathlib.Path(__file__).parent / 'fixtures'
FIXTURES = sorted(FIXTURE_DIR.glob('*.json'))


def _load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_fixture_count():
    assert len(FIXTURES) >= 5


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_passes_recorder_check(path):
    # Allowlisted keys, no forbidden markers, no URL with a query or fragment.
    check_record(_load(path))


@pytest.mark.parametrize('mutate', [
    lambda r: r['audio'].update(secret='x'),
    lambda r: r['audio']['stats'].update(revenue=1),
    lambda r: r['audio']['transcodings'][0].update(signed='x'),
    lambda r: r['oembed'].update(html='x'),
    lambda r: r.update(extra={}),
    lambda r: r['audio'].update(title='Bearer token'),
    lambda r: r['audio'].update(title='https://cdn.example/a?x=1'),
    lambda r: r['audio']['sources'][0].update(download='https://cdn.example/a.wv'),
    lambda r: r['audio']['sources'][0].update(name='my mix final.wv'),
    lambda r: r['audio']['sources'][0].update(md5='d41d8cd98f00b204e9800998ecf8427e'),
    lambda r: r['audio'].update(sources={'wv': {'url': 'https://cdn.example/a.wv'}}),
], ids=['audio-key', 'stats-key', 'transcoding-key', 'oembed-key', 'top-key', 'marker', 'query',
        'sources-download', 'sources-name', 'sources-md5', 'sources-dict'])
def test_recorder_check_rejects(mutate):
    rec = _load(FIXTURE_DIR / '1877766681285368.json')
    mutate(rec)
    with pytest.raises(RefusedError):
        check_record(rec)


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_stem_equals_audio_id(path):
    assert path.stem == _load(path)['audio']['id']


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_download_flag_and_sources(path):
    # The data invariant newest-source selection and the EXTR-04 gate rely on.
    audio = _load(path)['audio']
    assert isinstance(audio['is_downloadable'], bool)
    assert isinstance(audio['is_public'], bool)
    sources = audio['sources']
    assert isinstance(sources, list) and sources
    assert all(isinstance(s, dict) and s.get('id') for s in sources)
    if len(sources) == 1:
        assert {t.get('source_id') for t in audio['transcodings']} == {sources[0]['id']}


def _bit_rate(audio, fmt):
    return next((t['bit_rate'] for t in audio['transcodings'] if t.get('format') == fmt), None)


def test_shape_coverage():
    audios = [_load(p)['audio'] for p in FIXTURES]
    assert any(len(a['transcodings']) == 1 and a['transcodings'][0]['format'] == 'mp3' for a in audios), 'mp3-only'
    assert any((_bit_rate(a, 'mp3') or 0) > (_bit_rate(a, 'm4a') or float('inf')) for a in audios), 'mp3 > m4a bitrate'
    assert any(a['author_name'] == '' for a in audios), 'empty author_name'
    assert any(a['image'] for a in audios), 'non-empty image'
    assert any(a['description'] for a in audios), 'non-empty description'
    assert any(a['is_downloadable'] is True for a in audios), 'downloadable'
    assert any(a['is_downloadable'] is False for a in audios), 'not downloadable'
    source_formats = {s['format'] for a in audios for s in a['sources']}
    assert {'wv', 'wav', 'mp3', 'm4a'} <= source_formats, 'source formats'
    assert any(s['format'] == 'wav' and s['codec'] == 'wavpack' for a in audios for s in a['sources']), \
        'wav served from a wavpack upload'


def _reference_captured():
    data = _load(FIXTURE_DIR / '1877766681285368.json')
    return data['url'], {'oembed': data['oembed'], 'audio': data['audio']}


def test_recorder_projection_accepts_reference():
    url, captured = _reference_captured()
    check_record(project(url, captured))


@pytest.mark.parametrize(('key', 'value'), [
    ('stats', ['https://cdn.example/x?sig=abc']),
    ('transcodings', {'mp3': {'url': 'https://cdn.example/a.mp3?sig=abc'}}),
    ('transcodings', ['https://cdn.example/a.mp3?sig=abc']),
    ('image', {'url': 'https://cdn.example/i.jpg?sig=abc'}),
    ('avatar', ['https://cdn.example/i.jpg?sig=abc']),
    ('sources', {'wv': {'url': 'https://cdn.example/a.wv?sig=abc'}}),
    ('sources', ['https://cdn.example/a.wv?sig=abc']),
])
def test_recorder_refuses_unexpected_shapes(key, value):
    url, captured = _reference_captured()
    captured['audio'][key] = value
    with pytest.raises(RefusedError):
        project(url, captured)


def test_recorder_projection_drops_source_extras():
    url, captured = _reference_captured()
    source = captured['audio']['sources'][0]
    source.update(
        url=source['url'] + '?X-Amz-Expires=518400&X-Amz-Signature=abc#t=1',
        download=source['url'] + '?response-content-disposition=attachment',
        name='uploader original.wv', md5='d41d8cd98f00b204e9800998ecf8427e',
        waveform=[0, 1, 2], date_updated=1, date_uploaded=1, **{'from': 'audacity'})
    rec = project(url, captured)
    projected = rec['audio']['sources'][0]
    assert set(projected) <= set(SOURCE_KEYS)
    assert not {'download', 'name', 'md5', 'from', 'waveform', 'date_updated', 'date_uploaded'} & set(projected)
    assert '?' not in projected['url'] and '#' not in projected['url']
    assert projected['url'] == source['url'].split('?', 1)[0]
    check_record(rec)


@pytest.mark.parametrize('description', [
    'Stream: https://cdn.example/a.mp3?sv=2024&se=2026&sp=r&sig=abc',
    'More at https://example.com/page#section',
])
def test_recorder_refuses_urls_with_query_in_free_text(description):
    url, captured = _reference_captured()
    captured['audio']['description'] = description
    with pytest.raises(RefusedError):
        check_record(project(url, captured))
