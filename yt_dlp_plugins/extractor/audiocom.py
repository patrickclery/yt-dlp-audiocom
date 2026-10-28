# yt-dlp plugin: audio.com single tracks.
#
# DELETE THIS FILE once the bundled yt-dlp ships a built-in audio.com extractor
# (check `yt-dlp --list-extractors | grep -i audiocom` after every yt-dlp upgrade).
#
# yt-dlp imports every plugin on every run, so this module does no work at
# import time: only imports and the class definition live at the top level.
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.networking.exceptions import HTTPError
from yt_dlp.utils import (
    KNOWN_EXTENSIONS,
    ExtractorError,
    float_or_none,
    int_or_none,
    mimetype2ext,
    str_or_none,
    url_or_none,
)
from yt_dlp.utils.traversal import traverse_obj


class AudioComIE(InfoExtractor):
    # Host is anchored so lookalike hosts and api.audio.com never match.
    # embed/ and audio/audio/ paths would otherwise match with user=embed|audio;
    # the lookahead is case-insensitive because user segments may be uppercase.
    _VALID_URL = r'https?://(?:www\.)?audio\.com/(?!(?i:embed|audio)/)(?P<user>[^/?#]+)/audio/(?P<slug>[^/?#]+)/?(?:[?#]|$)'
    _API_BASE = 'https://api.audio.com'
    _TESTS = [{
        'url': 'https://audio.com/david-oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best',
        'info_dict': {
            'id': '1877766681285368',
            'ext': 'm4a',
            'display_id': 'rusted-pitchfork-dana-liske-uncut-version-astrayal-best',
            'title': 'Rusted Pitchfork — Dana Liske (Uncut Version) - Astrayal best',
            'uploader': 'David Oliveira',
            'uploader_id': 'david-oliveira-1877766671108274',
            'uploader_url': 'https://audio.com/david-oliveira-1877766671108274',
            'duration': 186.358,
            'timestamp': 1790777856,
            'upload_date': '20260930',
            'tags': 'count:5',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {
        'url': 'https://www.audio.com/David-Oliveira-1877766671108274/audio/rusted-pitchfork-dana-liske-uncut-version-astrayal-best/?utm_source=share',
        'only_matching': True,
    }]

    @staticmethod
    def _canonical_url(user, slug):
        # oEmbed 404s on www., trailing slash, query and uppercase input.
        return f'https://audio.com/{user.lower()}/audio/{slug.lower()}'

    def _call_api(self, path, video_id, note, **kwargs):
        # A 404 is a deleted, private or mistyped track: a user error, not a bug,
        # so it must not carry yt-dlp's "report this issue" text (wrong project).
        try:
            return self._download_json(f'{self._API_BASE}/{path}', video_id, note, **kwargs)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 404:
                raise ExtractorError('Track not found, private, or removed', expected=True)
            raise

    def _real_extract(self, url):
        user, slug = self._match_valid_url(url).group('user', 'slug')
        slug = slug.lower()
        canonical = self._canonical_url(user, slug)
        oembed = self._call_api('oembed', slug, 'Downloading oEmbed JSON', query={'url': canonical})
        track_id = self._search_regex(
            r'/embed/audio/(\d+)(?:[/?#]|$)', traverse_obj(oembed, ('iframe_url', {str})) or '', 'track id',
            fatal=False)
        if not track_id:
            raise ExtractorError('oEmbed returned no embed URL for this track', expected=True)
        data = self._call_api(f'audio/{track_id}', track_id, 'Downloading track JSON')
        # str_or_none: an integer id must not bypass the mismatch check.
        returned_id = traverse_obj(data, ('id', {str_or_none}))
        if returned_id != track_id:
            raise ExtractorError(f'API returned track {returned_id}, expected {track_id}')

        formats = []
        for t in traverse_obj(data, ('transcodings', lambda _, v: url_or_none(v['url']))):
            # The API format label is only trusted if it is a known extension;
            # anything else (e.g. 'm4a_hq') falls back to the MIME type, so an
            # unusual label cannot reach the filename and fail at download time.
            ext = next((e for e in (
                traverse_obj(t, ('format', {str}, {str.lower})),
                mimetype2ext(traverse_obj(t, ('type', {str}))),
            ) if e in KNOWN_EXTENSIONS), None)
            abr = traverse_obj(t, ('bit_rate', {lambda x: float_or_none(x, 1000)}))
            formats.append({
                'url': t['url'],
                'format_id': ext,
                'ext': ext,
                'vcodec': 'none',
                'abr': abr,
                # The default sort ranks quality ahead of acodec, so the highest
                # bitrate wins (D-07). Without it a 9 kbps m4a beats a 160 kbps mp3.
                'quality': abr,
                **traverse_obj(t, {
                    'acodec': ('codec', {str}),
                    'asr': ('sample_rate', {int_or_none}),
                    'audio_channels': ('channels', {int_or_none}),
                    'filesize': ('size', {int_or_none}),
                }),
            })
        if not formats:
            raise ExtractorError('No playable transcodings found', expected=True)

        # author_name is '' on some tracks; fall back to the username (D-11).
        username = traverse_obj(data, ('username', {str}, filter)) or user.lower()
        # Cover art, else the uploader avatar (D-11).
        thumbnail = traverse_obj(data, ('image', {url_or_none})) or traverse_obj(data, ('avatar', {url_or_none}))

        return {
            'id': track_id,
            'display_id': slug,
            'uploader': traverse_obj(data, ('author_name', {str}, filter)) or username,
            'uploader_id': username,
            'uploader_url': f'https://audio.com/{username}',
            **({'thumbnail': thumbnail} if thumbnail else {}),
            # /audio/<id> has no top-level duration or created: duration is the
            # first transcoding's, in ms, and timestamp is date_created (D-10).
            # upload_date is left to yt-dlp, which derives it from timestamp.
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str}, filter),
                'timestamp': ('date_created', {int_or_none}),
                'duration': ('transcodings', 0, 'duration', {lambda x: float_or_none(x, 1000)}),
                'tags': ('tags', ..., {str}, filter, all, filter),
                'view_count': ('stats', 'plays_count', {int_or_none}),
                'like_count': ('stats', 'likes_count', {int_or_none}),
                'comment_count': ('stats', 'comments_count', {int_or_none}),
                'repost_count': ('stats', 'shares_count', {int_or_none}),
            }),
            'formats': formats,
        }
