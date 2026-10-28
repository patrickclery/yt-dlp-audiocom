# yt-dlp plugin: audio.com single tracks.
#
# DELETE THIS FILE once the bundled yt-dlp ships a built-in audio.com extractor
# (check `yt-dlp --list-extractors | grep -i audiocom` after every yt-dlp upgrade).
#
# yt-dlp imports every plugin on every run, so this module does no work at
# import time: only imports and the class definition live at the top level.
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError, float_or_none, url_or_none
from yt_dlp.utils.traversal import traverse_obj


class AudioComIE(InfoExtractor):
    # Host is anchored so lookalike hosts and api.audio.com never match.
    # embed/ and audio/audio/ paths would otherwise match with user=embed|audio.
    _VALID_URL = r'https?://(?:www\.)?audio\.com/(?!embed/|audio/)(?P<user>[^/?#]+)/audio/(?P<slug>[^/?#]+)/?(?:[?#]|$)'
    _API_BASE = 'https://api.audio.com'
    _TESTS = [{
        'url': 'https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best',
        'info_dict': {
            'id': '1877766681285368',
            'ext': 'm4a',
            'display_id': 'rusted-pitchfork-dana-liske-uncut-version-astrayal-best',
            'title': 'Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best',
        },
    }, {
        'url': 'https://www.audio.com/David-Oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best/?utm_source=share',
        'only_matching': True,
    }]

    @staticmethod
    def _canonical_url(user, slug):
        # oEmbed 404s on www., trailing slash, query and uppercase input.
        return f'https://audio.com/{user.lower()}/audio/{slug.lower()}'

    def _real_extract(self, url):
        user, slug = self._match_valid_url(url).group('user', 'slug')
        slug = slug.lower()
        canonical = self._canonical_url(user, slug)
        oembed = self._download_json(
            f'{self._API_BASE}/oembed', slug, 'Downloading oEmbed JSON', query={'url': canonical})
        track_id = self._search_regex(
            r'/embed/audio/(\d+)', traverse_obj(oembed, ('iframe_url', {str})) or '', 'track id')
        data = self._download_json(f'{self._API_BASE}/audio/{track_id}', track_id, 'Downloading track JSON')
        returned_id = traverse_obj(data, ('id', {str}))
        if returned_id and returned_id != track_id:
            raise ExtractorError(f'API returned track {returned_id}, expected {track_id}')

        formats = []
        for t in traverse_obj(data, ('transcodings', lambda _, v: url_or_none(v['url']))):
            ext = traverse_obj(t, ('format', {str}))
            formats.append({
                'url': t['url'],
                'format_id': ext,
                'ext': ext,
                'vcodec': 'none',
                **traverse_obj(t, {
                    'acodec': ('codec', {str}),
                    'abr': ('bit_rate', {lambda x: float_or_none(x, 1000)}),
                }),
            })
        if not formats:
            raise ExtractorError('No playable transcodings found', expected=True)

        return {
            'id': track_id,
            'display_id': slug,
            'title': traverse_obj(data, ('title', {str})),
            'formats': formats,
        }
