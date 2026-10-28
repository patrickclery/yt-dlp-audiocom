"""Recorded fixtures must be commit-safe: no signed URLs, secrets or unread fields (D-09, D-13).

The redaction rules live in scripts/record_fixture.py; this module reuses them so
the recorder and this test cannot drift apart (WR-07).
"""
import json
import pathlib

import pytest

from scripts.record_fixture import RefusedError, check_record, project

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
], ids=['audio-key', 'stats-key', 'transcoding-key', 'oembed-key', 'top-key', 'marker', 'query'])
def test_recorder_check_rejects(mutate):
    rec = _load(FIXTURE_DIR / '1877766681285368.json')
    mutate(rec)
    with pytest.raises(RefusedError):
        check_record(rec)


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_stem_equals_audio_id(path):
    assert path.stem == _load(path)['audio']['id']


def _bit_rate(audio, fmt):
    return next((t['bit_rate'] for t in audio['transcodings'] if t.get('format') == fmt), None)


def test_shape_coverage():
    audios = [_load(p)['audio'] for p in FIXTURES]
    assert any(len(a['transcodings']) == 1 and a['transcodings'][0]['format'] == 'mp3' for a in audios), 'mp3-only'
    assert any((_bit_rate(a, 'mp3') or 0) > (_bit_rate(a, 'm4a') or float('inf')) for a in audios), 'mp3 > m4a bitrate'
    assert any(a['author_name'] == '' for a in audios), 'empty author_name'
    assert any(a['image'] for a in audios), 'non-empty image'
    assert any(a['description'] for a in audios), 'non-empty description'


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
])
def test_recorder_refuses_unexpected_shapes(key, value):
    url, captured = _reference_captured()
    captured['audio'][key] = value
    with pytest.raises(RefusedError):
        project(url, captured)


@pytest.mark.parametrize('description', [
    'Stream: https://cdn.example/a.mp3?sv=2024&se=2026&sp=r&sig=abc',
    'More at https://example.com/page#section',
])
def test_recorder_refuses_urls_with_query_in_free_text(description):
    url, captured = _reference_captured()
    captured['audio']['description'] = description
    with pytest.raises(RefusedError):
        check_record(project(url, captured))
