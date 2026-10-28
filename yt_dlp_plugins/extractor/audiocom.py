# yt-dlp plugin: audio.com single tracks.
#
# DELETE THIS FILE once the bundled yt-dlp ships a built-in audio.com extractor
# (check `yt-dlp --list-extractors | grep -i audiocom` after every yt-dlp upgrade).
#
# yt-dlp imports every plugin on every run, so this module does no work at
# import time: only imports and the class definition live at the top level.
import re

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
        'url': 'https://audio.com/jasa-sisemore/audio/jasasisemore-audacitypractice-autoduck-assignment-4aup',
        'info_dict': {
            'id': '1782423994666898',
            'ext': 'mp3',
            'display_id': 'jasasisemore-audacitypractice-autoduck-assignment-4aup',
            'title': 'JasaSisemore_AudacityPractice_AUTODUCK_assignment 4.aup',
            'uploader': 'Jasa Sisemore',
            'uploader_id': 'jasa-sisemore',
            'uploader_url': 'https://audio.com/jasa-sisemore',
            'duration': 44.722,
            'timestamp': 1699851984,
            'upload_date': '20231113',
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

    @staticmethod
    def _known_ext(obj):
        # The API format label is only trusted if it is a known extension;
        # anything else (e.g. 'm4a_hq', 'wv') falls back to the MIME type, so an
        # unusual label cannot reach the filename and fail at download time.
        return next((e for e in (
            traverse_obj(obj, ('format', {str}, {str.lower})),
            mimetype2ext(traverse_obj(obj, ('type', {str}))),
        ) if e in KNOWN_EXTENSIONS), None)

    def _original_requested(self):
        # The original is listed only when asked for: by name in -f (-f original,
        # -f original/ba, ...), for -F, or for interactive -f -. A generic selector
        # (worst, wa, ba[ext=wav], ...) then never sees it, and a plain download makes
        # no S3 request. Pluralsight narrows its formats on -f / -F the same way.
        if self.get_param('listformats'):
            return True
        spec = self.get_param('format')
        return isinstance(spec, str) and (
            spec == '-' or re.search(r'(?<![\w-])original(?![\w-])', spec) is not None)

    def _probe_original(self, url, track_id):
        # Not _is_valid_url: its skip line prints str(cause), and a transport error
        # (e.g. urllib3's MaxRetryError under the requests handler) quotes the path
        # and presigned query. Only the HTTP status or the error type is printed.
        try:
            self._request_webpage(
                url, track_id, 'Checking original upload URL', headers={'Range': 'bytes=0-0'}).close()
        except ExtractorError as e:
            reason = str(e.cause) if isinstance(e.cause, HTTPError) else type(e.cause or e).__name__
            self.to_screen(f'{track_id}: original upload URL is invalid, skipping: {reason}')
            return False
        return True

    def _call_api(self, path, video_id, note, **kwargs):
        # A missing or restricted track is a user-side condition, not a bug, so the
        # error is expected: one line, no traceback and no "report this issue" text
        # (which would point at the wrong project). The HTTPError is not attached as
        # cause, because yt-dlp would append "(caused by ...)" to the line; -v still
        # shows the request. Other statuses keep yt-dlp's own error.
        try:
            return self._download_json(f'{self._API_BASE}/{path}', video_id, note, **kwargs)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                if e.cause.status in (404, 410):
                    raise ExtractorError(
                        'This audio.com track is unavailable (removed, private, or wrong URL)',
                        video_id=video_id, expected=True)
                if e.cause.status in (401, 403):  # never seen anonymously; a guard
                    raise ExtractorError(
                        'This audio.com track is private or restricted', video_id=video_id, expected=True)
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
            raise ExtractorError('oEmbed returned no embed URL for this track', video_id=slug, expected=True)
        data = self._call_api(f'audio/{track_id}', track_id, 'Downloading track JSON')
        # str_or_none: an integer id must not bypass the mismatch check.
        returned_id = traverse_obj(data, ('id', {str_or_none}))
        if returned_id != track_id:
            raise ExtractorError(f'API returned track {returned_id}, expected {track_id}', video_id=track_id)

        # A re-uploaded track keeps every version in sources[], and transcodings[]
        # mixes them. The site plays the newest upload (RESEARCH Finding 2), so
        # keep only its transcodings: newest = largest date_created, a tie goes to
        # the later entry. Without sources or a matching source_id, keep them all.
        sources = traverse_obj(data, ('sources', lambda _, v: str_or_none(v['id'])))
        current = max(reversed(sources), key=lambda s: int_or_none(s.get('date_created')) or 0, default=None)
        current_id = traverse_obj(current, ('id', {str_or_none}))
        transcodings = traverse_obj(data, ('transcodings', lambda _, v: url_or_none(v['url'])))
        if current_id:
            transcodings = [t for t in transcodings
                            if str_or_none(t.get('source_id')) == current_id] or transcodings

        formats = []
        for t in transcodings:
            ext = self._known_ext(t)
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
            raise ExtractorError('No playable transcodings found', video_id=track_id, expected=True)

        # EXTR-04: the uploader's original file, opt-in via -f original, only when
        # the uploader allows downloads. Signed source URLs download without auth
        # even when downloads are disallowed, so this check is the only control:
        # only the literal True opens it, and no source URL is touched otherwise.
        if (data.get('is_downloadable') is True and self._original_requested()
                and url_or_none(traverse_obj(current, 'url'))):
            ext = self._known_ext(current)
            if not ext:
                # e.g. WavPack ('wv'): yt-dlp refuses the extension at download time.
                self.write_debug(f'Skipping original upload: unsupported format {current.get("format")!r}')
            # One-byte GET (HEAD gets 403 on these GET-signed URLs); some originals
            # are missing on S3.
            elif self._probe_original(current['url'], track_id):
                # A wavpack source is served as a converted PCM wav, so the API's
                # codec, bitrate and size describe a different file; omit them.
                converted = traverse_obj(current, ('codec', {str})) == 'wavpack'
                formats.append({
                    'url': current['url'],  # never the 'download' URL
                    'format_id': 'original',
                    'format_note': 'original upload',
                    'ext': ext,
                    'vcodec': 'none',
                    # When listed (-F, or -f original/ba), ie_pref outranks every sort
                    # field, so neither the default sort nor -S picks it. No quality.
                    'preference': -10,
                    **({} if converted else traverse_obj(current, {
                        'acodec': ('codec', {str}),
                        'abr': ('bit_rate', {lambda x: float_or_none(x, 1000)}),
                        'filesize': ('size', {int_or_none}),
                    })),
                    **traverse_obj(current, {
                        'asr': ('sample_rate', {int_or_none}),
                        'audio_channels': ('channels', {int_or_none}),
                    }),
                })

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
            # current upload's first transcoding's, in ms (D-11), and timestamp is
            # date_created (D-10). upload_date is left to yt-dlp (from timestamp).
            **traverse_obj(transcodings, {
                'duration': (0, 'duration', {lambda x: float_or_none(x, 1000)}),
            }),
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('description', {str}, filter),
                'timestamp': ('date_created', {int_or_none}),
                'tags': ('tags', ..., {str}, filter, all, filter),
                'view_count': ('stats', 'plays_count', {int_or_none}),
                'like_count': ('stats', 'likes_count', {int_or_none}),
                'comment_count': ('stats', 'comments_count', {int_or_none}),
                'repost_count': ('stats', 'shares_count', {int_or_none}),
            }),
            'formats': formats,
        }
