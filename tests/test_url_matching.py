import pytest
from yt_dlp import YoutubeDL

from yt_dlp_plugins.extractor.audiocom import AudioComIE

REF = 'https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best'
COMBINED = ('https://www.audio.com/David-Oliveira-1877766671108274/audio/'
            'rusted-pitchfork-dana-liske-uncut-version-astrayal-best/?utm_source=share')

POSITIVE = [
    REF,
    REF.replace('https://audio.com/', 'https://www.audio.com/'),
    REF + '/',
    REF + '?utm_source=share',
    REF + '#t=10',
    REF.replace('david-oliveira-', 'David-Oliveira-'),
    REF.replace('https://', 'http://'),
    COMBINED,
]

NEGATIVE = [
    'https://audio.com/david-oliveira-1877766671108274',
    'https://audio.com/david-oliveira-1877766671108274/collections/my-list',
    'https://audio.com/embed/audio/1877766681285368',
    'https://audio.com/audio/audio/1877766681285368',
    'https://audio.com/Embed/audio/1877766681285368',
    'https://audio.com/AUDIO/audio/1877766681285368',
    'https://audio.com.evil.example/u/audio/s',
    'https://notaudio.com/u/audio/s',
    'https://api.audio.com/audio/1877766681285368',
    'https://audio.com/u/audio/',
    'https://audio.com//audio/s',
    'https://audio.com/u/audio/s/extra',
]


@pytest.mark.parametrize('url', POSITIVE)
def test_suitable(url):
    assert AudioComIE.suitable(url)


@pytest.mark.parametrize('url', NEGATIVE)
def test_not_suitable(url):
    assert not AudioComIE.suitable(url)


class _Stop(Exception):
    pass


def test_canonical_url_sent_to_oembed(monkeypatch):
    calls = []

    def fake(self, url_or_request, *args, query=None, **kwargs):
        calls.append((url_or_request, query, kwargs))
        raise _Stop

    monkeypatch.setattr(AudioComIE, '_download_json', fake)
    with pytest.raises(_Stop):
        AudioComIE(YoutubeDL({'quiet': True})).extract(COMBINED)

    assert calls[0][0] == 'https://api.audio.com/oembed'
    assert calls[0][1] == {'url': REF}
    for _, _, kwargs in calls:
        assert not any('imperson' in key for key in kwargs)
