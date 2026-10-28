"""Offline metadata mapping (EXTR-05, D-08, D-10, D-11) against recorded fixtures."""
import pytest

from conftest import FIXTURE_PATHS, REFERENCE_ID, load_fixture, patch_api, run_extract
from yt_dlp_plugins.extractor.audiocom import AudioComIE

# id: (uploader, duration s, upload_date, thumbnail present, description present)
EXPECTED = {
    '1877766681285368': ('David Oliveira', 186.358, '20260930', False, False),
    '1782423994666898': ('Jasa Sisemore', 44.722, '20231113', False, False),
    '1795055938670272': ('Beards and Banter Podcast', 4211.644, '20240331', False, False),
    '1861573231849291': ('Arthur Hpcp', 2335.644, '20260404', False, False),
    '1880272428195927': ('roshimakr21', 304.464, '20261028', True, False),  # username fallback, cover
    '1880272004207526': ('davidmoreno-musician', 351.53, '20261028', True, False),  # fallback, avatar as image
    '1880273150344633': ('james-gant', 153.574, '20261028', False, False),  # username fallback
    '1880272651234303': ('SHIVGAS', 189.675, '20261028', True, True),
    '1880272945380630': ('alec Murray', 38.792, '20261028', False, False),
    '1880272416485027': ('Andrea Mathiopoulos', 10.789, '20261028', False, False),
}
COUNT_KEYS = ('view_count', 'like_count', 'comment_count', 'repost_count')
COVER_FIXTURE_ID = '1880272428195927'  # roshimakr21: real cover art


def test_expected_table_covers_every_fixture():
    assert set(EXPECTED) == {p.stem for p in FIXTURE_PATHS}


def test_metadata_fields(fx):
    data, _ = fx
    audio = data['audio']
    uploader, duration, upload_date, has_thumb, has_desc = EXPECTED[audio['id']]
    info, processed = run_extract(data['url'])

    assert info['title'] == audio['title']
    assert info['uploader'] == uploader
    assert info['uploader_id'] == audio['username']
    assert info['uploader_url'] == 'https://audio.com/' + audio['username']
    assert isinstance(info['duration'], float)
    assert info['duration'] == audio['transcodings'][0]['duration'] / 1000 == duration
    assert info['timestamp'] == audio['date_created']
    assert processed['upload_date'] == upload_date
    assert ('thumbnail' in info) is has_thumb
    assert ('description' in info) is has_desc
    assert isinstance(info['tags'], list) and len(info['tags']) == len(audio['tags'])
    assert all(isinstance(t, str) and t for t in info['tags'])
    for key in COUNT_KEYS:
        assert isinstance(info[key], int)


def test_no_empty_string_values(fx):
    data, _ = fx
    info, _ = run_extract(data['url'])
    assert [k for k, v in info.items() if v == ''] == []


def _reference():
    return load_fixture(REFERENCE_ID)


def _extract_mutated(monkeypatch, data):
    patch_api(monkeypatch, data['oembed'], data['audio'])
    return run_extract(data['url'])[0]


def test_mutation_thumbnail_falls_back_to_avatar(monkeypatch):
    avatar = load_fixture(COVER_FIXTURE_ID)['audio']['image']
    assert avatar
    data = _reference()
    data['audio']['image'] = ''
    data['audio']['avatar'] = avatar
    assert _extract_mutated(monkeypatch, data)['thumbnail'] == avatar


def test_mutation_no_stats_no_counts(monkeypatch):
    data = _reference()
    del data['audio']['stats']
    info = _extract_mutated(monkeypatch, data)
    assert [k for k in COUNT_KEYS if k in info] == []


def test_mutation_empty_tags_no_tags_key(monkeypatch):
    data = _reference()
    data['audio']['tags'] = []
    assert 'tags' not in _extract_mutated(monkeypatch, data)


def test_mutation_empty_description_no_key(monkeypatch):
    data = _reference()
    data['audio']['description'] = ''
    assert 'description' not in _extract_mutated(monkeypatch, data)


def test_mutation_empty_author_name_falls_back_to_username(monkeypatch):
    data = _reference()
    data['audio']['author_name'] = ''
    assert _extract_mutated(monkeypatch, data)['uploader'] == 'david-oliveira-1877766671108274'


DOWNLOADABLE_TESTS = [t for t in AudioComIE._TESTS if not t.get('only_matching')]
_TEST_IDS = [t['info_dict']['id'] for t in DOWNLOADABLE_TESTS]


@pytest.mark.parametrize('test', DOWNLOADABLE_TESTS, ids=_TEST_IDS)
def test_tests_info_dict_matches_offline_fixture(monkeypatch, test):
    # PLUG-03: every live _TESTS entry replays against its recorded fixture.
    data = load_fixture(test['info_dict']['id'])
    assert test['url'] == data['url']
    patch_api(monkeypatch, data['oembed'], data['audio'])
    _, processed = run_extract(test['url'])
    for key, expected in test['info_dict'].items():
        if isinstance(expected, type):
            assert isinstance(processed[key], expected), key
        elif isinstance(expected, str) and expected.startswith('count:'):
            assert len(processed[key]) == int(expected[len('count:'):]), key
        else:
            assert processed[key] == expected, key


def test_tests_cover_reference_and_jasa_only():
    # D-08: live _TESTS use only the reference and the 2023 jasa-sisemore track.
    assert {t['url'] for t in DOWNLOADABLE_TESTS} == {
        load_fixture(REFERENCE_ID)['url'],
        'https://audio.com/jasa-sisemore/audio/jasasisemore-audacitypractice-autoduck-assignment-4aup',
    }
    assert len(DOWNLOADABLE_TESTS) == 2
    assert AudioComIE._TESTS[-1].get('only_matching') is True
    assert [t for t in AudioComIE._TESTS[:-1] if t.get('only_matching')] == []


@pytest.mark.parametrize('test', DOWNLOADABLE_TESTS, ids=_TEST_IDS)
@pytest.mark.parametrize('key', ['thumbnail', 'description', 'md5'])
def test_tests_info_dict_omits_absent_fields(key, test):
    assert key not in test['info_dict']
