"""Recorded fixtures must be commit-safe: no signed URLs, secrets or unread fields (D-09, D-13)."""
import json
import pathlib

import pytest

FIXTURE_DIR = pathlib.Path(__file__).parent / 'fixtures'
FIXTURES = sorted(FIXTURE_DIR.glob('*.json'))

FORBIDDEN_MARKERS = ('x-amz-', 'signature', 'token', 'client_secret', 'stripe')
AUDIO_KEYS = {'id', 'username', 'author_name', 'title', 'description', 'image', 'avatar',
              'date_created', 'tags', 'stats', 'transcodings'}
STATS_KEYS = {'plays_count', 'likes_count', 'comments_count', 'shares_count'}
TRANSCODING_KEYS = {'format', 'type', 'url', 'size', 'codec', 'sample_rate', 'channels',
                    'duration', 'bit_rate'}


def _load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def test_fixture_count():
    assert len(FIXTURES) >= 5


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_no_forbidden_markers(path):
    text = path.read_text(encoding='utf-8').lower()
    assert [m for m in FORBIDDEN_MARKERS if m in text] == []


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_urls_have_no_query_or_fragment(path):
    for s in _strings(_load(path)):
        if '://' in s:
            assert '?' not in s and '#' not in s, 'URL with query or fragment in fixture'


@pytest.mark.parametrize('path', FIXTURES, ids=lambda p: p.stem)
def test_keys_within_allowlist(path):
    data = _load(path)
    assert set(data) == {'url', 'oembed', 'audio'}
    assert set(data['oembed']) == {'iframe_url'}
    audio = data['audio']
    assert set(audio) <= AUDIO_KEYS
    if 'stats' in audio:
        assert set(audio['stats']) <= STATS_KEYS
    for t in audio.get('transcodings') or []:
        assert set(t) <= TRANSCODING_KEYS


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
