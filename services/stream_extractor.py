import os
import re
from typing import Dict, Any, Optional
import yt_dlp
from .db_manager import DatabaseManager

# Comprehensive YouTube Video ID regex supporting watch?v=, youtu.be/, /shorts/, /live/, /embed/, /v/
YOUTUBE_URL_REGEX = re.compile(
    r'(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
)
VIDEO_ID_STRICT_REGEX = re.compile(r'^[a-zA-Z0-9_-]{11}$')


class StreamExtractor:
    """
    Extracts direct playback and HLS stream links locally using embedded yt-dlp,
    with local SQLite caching to optimize network round-trips.
    """
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.ydl_opts = {
            # Target both progressive streams and separate high-res video + audio
            'format': 'best[protocol=https]/best[ext=mp4]/bestvideo+bestaudio/best',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'tv']
                }
            },
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }

    @staticmethod
    def extract_video_id(video_id_or_url: str) -> Optional[str]:
        """
        Robustly extracts an 11-character YouTube video ID from various URL formats:
        - https://www.youtube.com/watch?v=dQw4w9WgXcQ
        - https://youtu.be/dQw4w9WgXcQ
        - https://www.youtube.com/shorts/dQw4w9WgXcQ
        - https://www.youtube.com/live/dQw4w9WgXcQ
        - Raw video ID: dQw4w9WgXcQ
        """
        video_id_or_url = video_id_or_url.strip()
        if VIDEO_ID_STRICT_REGEX.match(video_id_or_url):
            return video_id_or_url

        match = YOUTUBE_URL_REGEX.search(video_id_or_url)
        if match:
            return match.group(1)

        # Fallback query param parser
        if "v=" in video_id_or_url:
            parts = video_id_or_url.split("v=")[1].split("&")[0].split("#")[0]
            if len(parts) == 11:
                return parts

        return None

    def extract_stream_info(self, video_id_or_url: str) -> Optional[Dict[str, Any]]:
        video_id = self.extract_video_id(video_id_or_url)
        if not video_id:
            print(f"[StreamExtractor] Invalid YouTube URL or video ID: {video_id_or_url}")
            return None

        # 1. Check local SQLite cache first (valid for 5 hours)
        cached = self.db.get_cached_stream(video_id)
        if cached:
            video_url = cached.get('video_url')
            audio_url = cached.get('audio_url')
            hls_url = cached.get('hls_manifest_url')
            is_live = bool(cached.get('is_live'))

            # For cached results, stream_url defaults to progressive/HLS/video
            stream_url = hls_url if (is_live and hls_url) else (video_url or hls_url)

            return {
                'video_id': video_id,
                'title': cached.get('title') or f"Video {video_id}",
                'channel_id': cached.get('channel_id') or '',
                'channel_title': cached.get('channel_title') or '',
                'duration': float(cached.get('duration') or 0.0),
                'stream_url': stream_url,
                'video_url': video_url,
                'audio_url': audio_url,
                'hls_manifest_url': hls_url,
                'is_live': is_live,
                'resolution': cached.get('resolution') or 'best',
                'from_cache': True
            }

        # 2. Extract live metadata and direct stream URLs via yt-dlp
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                is_live = bool(info.get('is_live')) or (info.get('live_status') == 'is_live')
                hls_url: Optional[str] = None
                progressive_url: Optional[str] = None
                best_video_url: Optional[str] = None
                best_audio_url: Optional[str] = None
                resolution = f"{info.get('width', 1920)}x{info.get('height', 1080)}"

                # Check for direct HLS manifest (.m3u8)
                manifest_url = info.get('manifest_url')
                if manifest_url and '.m3u8' in manifest_url:
                    hls_url = manifest_url

                formats = info.get('formats', [])

                # Scan formats
                for fmt in reversed(formats):
                    fmt_url = fmt.get('url', '')
                    if not fmt_url:
                        continue

                    vcodec = fmt.get('vcodec', 'none')
                    acodec = fmt.get('acodec', 'none')

                    # Capture HLS playlist
                    if ('.m3u8' in fmt_url or fmt.get('protocol') == 'm3u8_native') and not hls_url:
                        hls_url = fmt_url

                    # Progressive format: contains BOTH video and audio
                    if vcodec != 'none' and acodec != 'none' and acodec is not None and not progressive_url:
                        progressive_url = fmt_url
                        width = fmt.get('width')
                        height = fmt.get('height')
                        if width and height:
                            resolution = f"{width}x{height}"

                    # Video format
                    if vcodec != 'none' and not best_video_url:
                        best_video_url = fmt_url

                    # Audio format (AAC / Opus / MP4A)
                    if acodec != 'none' and acodec is not None and (vcodec == 'none' or vcodec is None) and not best_audio_url:
                        best_audio_url = fmt_url

                # Primary stream selection:
                # If progressive is available, it guarantees audio and video in one stream.
                # If only separate streams exist, primary_stream is best_video_url and best_audio_url is passed to dual-player.
                if is_live and hls_url:
                    primary_stream = hls_url
                elif progressive_url:
                    primary_stream = progressive_url
                elif best_video_url:
                    primary_stream = best_video_url
                elif hls_url:
                    primary_stream = hls_url
                else:
                    primary_stream = info.get('url')

                title = info.get('title') or f"Video {video_id}"
                channel_id = info.get('channel_id') or ""
                channel_title = info.get('uploader') or info.get('channel') or ""
                duration = float(info.get('duration') or 0.0)

                # Save to local database cache with full metadata
                self.db.cache_stream(
                    video_id=video_id,
                    video_url=primary_stream,
                    audio_url=best_audio_url or "",
                    hls_url=hls_url or "",
                    is_live=is_live,
                    resolution=resolution,
                    title=title,
                    channel_title=channel_title,
                    channel_id=channel_id,
                    duration=duration
                )

                return {
                    'video_id': video_id,
                    'title': title,
                    'channel_id': channel_id,
                    'channel_title': channel_title,
                    'duration': duration,
                    'stream_url': primary_stream,
                    'video_url': progressive_url or best_video_url or primary_stream,
                    'audio_url': best_audio_url or "",
                    'hls_manifest_url': hls_url,
                    'is_live': is_live,
                    'resolution': resolution,
                    'from_cache': False
                }
        except Exception as e:
            print(f"[StreamExtractor] Error extracting stream info for {video_id}: {e}")
            return None
