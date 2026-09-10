# -*- coding: utf-8 -*-
"""
A TuBe API Controller
Unified REST-like API endpoints for the local server.
Handles feed, details, search, servers, cast/crew, pagination, and categories.
"""

import os
import sys
import json
import re
import urllib.parse
from http.server import SimpleHTTPRequestHandler

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from vod_db import VODDatabase
from categorizer import SmartCategorizer
from text_sanitizer import TextSanitizer
from stream_sanitizer import StreamSanitizer
from pagination_engine import PaginationEngine
from cast_crew_api import CastCrewAPI


class APIController:
    """
    Centralized API controller for A Tube server.
    All API endpoints are routed through this controller.
    """

    @staticmethod
    def send_cors_json(handler: SimpleHTTPRequestHandler, obj: dict, status: int = 200):
        """Sends a JSON response with CORS headers."""
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        handler.send_header("Access-Control-Allow-Headers", "Content-Type")
        handler.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        handler.end_headers()
        handler.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    @staticmethod
    def send_error(handler: SimpleHTTPRequestHandler, message: str, status: int = 400):
        """Sends a standardized error response."""
        APIController.send_cors_json(handler, {"error": message}, status)

    @classmethod
    def resolve_feed_params(cls, content_type: str, category: str):
        """
        Resolves an incoming (possibly Arabic) content_type + category into the
        canonical (type, category) pair that VODDatabase.get_feed expects.

        Mirrors the legacy server-side category_map so the new API controller
        behaves identically to the old /api/movies/feed handler for Arabic
        category names coming from the UI (e.g. "مسلسلات تركي").
        """
        if not content_type or content_type == "all":
            content_type = "all"

        # Direct canonical slugs pass through untouched
        canonical_slugs = {"all", "movie", "series", "anime", "tv_show",
                           "foreign", "arabic", "arabic_series", "turkish",
                           "indian", "indian_series", "korean_series",
                           "asian", "anime", "wrestling", "documentary",
                           "plays", "channels"}
        if category in canonical_slugs:
            return content_type, category

        norm_cat = re.sub(r'[آإأ]', 'ا', (category or '')).strip().lower()

        # If a bare Arabic word slips through, resolve by keyword heuristics
        if norm_cat in cls.CATEGORY_ARABIC_MAP:
            c_type, c_cat = cls.CATEGORY_ARABIC_MAP[norm_cat]
            if content_type == "all":
                content_type = c_type
            return content_type, c_cat

        for needle, (c_type, c_cat) in cls.CATEGORY_ARABIC_MAP.items():
            if needle in norm_cat:
                if content_type == "all":
                    content_type = c_type
                return content_type, c_cat

        return content_type, category

    @classmethod
    def _sanitize_feed_item(cls, item: dict) -> dict:
        """Decode HTML entities and clean text fields on a single feed item."""
        if not isinstance(item, dict):
            return item
        for field in ("title", "arabic_title", "synopsis", "director"):
            val = item.get(field)
            if val and isinstance(val, str):
                item[field] = TextSanitizer.decode_html_entities(val)
        # Build a clean episode_count hint for series cards
        if item.get("content_type") in ("series", "anime", "tv_show"):
            item["episode_count"] = item.get("total_seasons", 0) or 0
        return item

    # ==========================================================================
    # 1. MEDIA FEED API (with Pagination)
    # ==========================================================================
    @classmethod
    def handle_feed(cls, handler: SimpleHTTPRequestHandler, query: dict):
        """
        GET /api/media/feed
        Parameters:
        - type: 'movie', 'series', 'anime', 'all' (or Arabic category text)
        - category: 'foreign', 'arabic', 'turkish', 'indian', etc. (or Arabic)
        - page: integer (default 1)
        - limit: integer (default 24)
        - sort: 'latest', 'rating', 'title'
        """
        try:
            content_type = query.get("type", ["all"])[0]
            category = query.get("category", ["all"])[0]
            page = int(query.get("page", ["1"])[0])
            limit = int(query.get("limit", ["24"])[0])
            sort = query.get("sort", ["latest"])[0]

            # Validate pagination params
            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 24

            # Resolve Arabic category/type names to canonical slugs
            content_type, category = cls.resolve_feed_params(content_type, category)

            # Use the pagination engine
            result = PaginationEngine.get_paginated_feed(
                content_type=content_type,
                category=category,
                page=page,
                limit=limit,
                sort=sort
            )

            # Sanitize all item text fields (decode HTML entities like &quot;)
            items = result.get("items", [])
            if isinstance(items, list):
                result["items"] = [cls._sanitize_feed_item(i) for i in items]

            cls.send_cors_json(handler, result)

        except Exception as e:
            import traceback
            traceback.print_exc()
            cls.send_error(handler, f"Feed error: {str(e)}", 500)

    # Map of Arabic category display keys -> (content_type, canonical_category)
    CATEGORY_ARABIC_MAP = {
        "افلام اجنبي": ("movie", "foreign"),
        "افلام اجنبية": ("movie", "foreign"),
        "مسلسلات اجنبي": ("series", "foreign"),
        "مسلسلات اجنبية": ("series", "foreign"),
        "افلام عربي": ("movie", "arabic"),
        "افلام عربية": ("movie", "arabic"),
        "مسلسلات عربي": ("series", "arabic"),
        "مسلسلات عربية": ("series", "arabic"),
        "افلام تركي": ("movie", "turkish"),
        "مسلسلات تركي": ("series", "turkish"),
        "افلام هندي": ("movie", "indian"),
        "مسلسلات هندي": ("series", "indian_series"),
        "مسلسلات كوري": ("series", "korean_series"),
        "مسلسلات كورية": ("series", "korean_series"),
        "افلام انمي": ("anime", "all"),
        "مسلسلات انمي": ("anime", "all"),
        "انمي": ("anime", "all"),
        "كرتون": ("anime", "all"),
        "كارتون": ("anime", "all"),
        "مسرحيات": ("movie", "plays"),
        "مصارعة": ("all", "wrestling"),
        "مصارعة حرة": ("all", "wrestling"),
        "برامج": ("tv_show", "all"),
        "وثائقيات": ("movie", "documentary"),
        "افلام وثائقية": ("movie", "documentary"),
        "مسلسلات وثائقية": ("movie", "documentary"),
    }

    # ==========================================================================
    # 2. MEDIA DETAILS API
    # ==========================================================================
    @classmethod
    def handle_details(cls, handler: SimpleHTTPRequestHandler, query: dict):
        """
        GET /api/media/details
        Parameters:
        - id: media ID
        """
        try:
            media_id = query.get("id", [""])[0]
            if not media_id:
                cls.send_error(handler, "Missing id parameter", 400)
                return

            details = VODDatabase.get_media_details(media_id)

            if details:
                # Sanitize all text fields before sending
                if details.get('synopsis'):
                    details['synopsis'] = TextSanitizer.sanitize(details['synopsis'])
                if details.get('title'):
                    details['title'] = TextSanitizer.sanitize(details['title'], max_length=200)
                if details.get('arabic_title'):
                    details['arabic_title'] = TextSanitizer.sanitize(details['arabic_title'], max_length=200)

                # Ensure servers have A Tube branding
                for server in details.get('servers', []):
                    if not server.get('server_name'):
                        server['server_name'] = 'A Tube Cloud Server'

                cls.send_cors_json(handler, details)
            else:
                cls.send_error(handler, "Media not found", 404)

        except Exception as e:
            cls.send_error(handler, f"Details error: {str(e)}", 500)

    # ==========================================================================
    # 3. SEARCH API
    # ==========================================================================
    @classmethod
    def handle_search(cls, handler: SimpleHTTPRequestHandler, query: dict):
        """
        GET /api/media/search
        Parameters:
        - q: search query
        - type: content type filter
        - category: category filter
        """
        try:
            search_query = query.get("q", [""])[0]
            content_type = query.get("type", ["all"])[0]
            category = query.get("category", ["all"])[0]

            if not search_query or len(search_query.strip()) < 2:
                cls.send_error(handler, "Query too short (minimum 2 characters)", 400)
                return

            # Sanitize search query
            safe_query = TextSanitizer.sanitize(search_query, max_length=100)

            results = VODDatabase.search_media(
                query=safe_query,
                content_type=content_type if content_type != "all" else None,
                category=category if category != "all" else None
            )

            # Decode HTML entities in results
            for item in results:
                if item.get('title'):
                    item['title'] = TextSanitizer.decode_html_entities(item['title'])
                if item.get('arabic_title'):
                    item['arabic_title'] = TextSanitizer.decode_html_entities(item['arabic_title'])

            response = {
                "query": safe_query,
                "count": len(results),
                "results": results
            }

            cls.send_cors_json(handler, response)

        except Exception as e:
            cls.send_error(handler, f"Search error: {str(e)}", 500)

    # ==========================================================================
    # 4. SERVERS API
    # ==========================================================================
    @classmethod
    def handle_servers(cls, handler: SimpleHTTPRequestHandler, query: dict):
        """
        GET /api/media/servers
        Parameters:
        - id: media ID
        - season: season number (optional)
        - episode: episode number (optional)
        """
        try:
            media_id = query.get("id", [""])[0]
            content_type = query.get("type", [""])[0]
            is_live = query.get("is_live", [""])[0]
            category = query.get("category", [""])[0]
            season = query.get("season", [""])[0]
            episode = query.get("episode", [""])[0]

            if not media_id:
                cls.send_error(handler, "Missing id parameter", 400)
                return

            live_signals = {
                content_type.strip().lower(),
                is_live.strip().lower(),
                category.strip().lower()
            }
            if live_signals & {"live", "iptv", "channel", "channels", "1", "true", "yes", "قنوات مباشرة", "قنوات البث المباشر"}:
                cls.send_cors_json(handler, {
                    "media_id": media_id,
                    "season": season,
                    "episode": episode,
                    "servers": []
                })
                return

            # Get media details which includes servers
            details = VODDatabase.get_media_details(media_id)

            if not details:
                cls.send_error(handler, "Media not found", 404)
                return

            if details.get("is_live") or details.get("type") in ("live", "iptv", "channel", "channels"):
                cls.send_cors_json(handler, {
                    "media_id": media_id,
                    "season": season,
                    "episode": episode,
                    "servers": []
                })
                return

            servers = []

            if season and episode:
                # Get episode-specific servers
                try:
                    season_num = int(season)
                    ep_num = int(episode)
                    season_data = next((s for s in details.get('seasons', [])
                                      if s['season_number'] == season_num), None)
                    if season_data:
                        ep_data = next((e for e in season_data.get('episodes', [])
                                      if e['episode_number'] == ep_num), None)
                        if ep_data:
                            servers = ep_data.get('servers', [])
                except (ValueError, TypeError):
                    pass

            if not servers:
                # Fallback to movie-level servers
                servers = details.get('servers', [])

            # Sanitize server URLs and ensure A Tube branding
            clean_servers = []
            for server in servers:
                stream_url = server.get('stream_url', '')
                if not stream_url:
                    continue

                # Sanitize URL
                clean_url = TextSanitizer.sanitize(stream_url, decode_html=True,
                                                    normalize_arabic=False, strip_noise=False)

                # Validate URL safety
                if not cls._is_safe_url(clean_url):
                    continue

                clean_servers.append({
                    'id': server.get('id'),
                    'site': 'A Tube',
                    'quality': server.get('quality', '1080p'),
                    'name': server.get('server_name', f'سيرفر A Tube'),
                    'url': clean_url,
                    'badge': server.get('badge', 'A Tube VIP'),
                    'is_active': True
                })

            cls.send_cors_json(handler, {
                "media_id": media_id,
                "season": season,
                "episode": episode,
                "servers": clean_servers
            })

        except Exception as e:
            cls.send_error(handler, f"Servers error: {str(e)}", 500)

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """Validates URL safety for serving."""
        if not url or not isinstance(url, str):
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return False
            # Block ad/tracking domains
            blocked = ['doubleclick', 'googlesyndication', 'popads', 'adservice',
                      'bet365', '1xbet', 'melbet', 'onclickads']
            hostname = parsed.hostname or ''
            if any(b in hostname.lower() for b in blocked):
                return False
            return True
        except Exception:
            return False

    # ==========================================================================
    # 5. CAST & CREW API
    # ==========================================================================
    @classmethod
    def handle_cast_crew(cls, handler: SimpleHTTPRequestHandler, query: dict):
        """
        GET /api/media/cast
        Parameters:
        - id: media ID
        """
        try:
            media_id = query.get("id", [""])[0]
            if not media_id:
                cls.send_error(handler, "Missing id parameter", 400)
                return

            response = CastCrewAPI.get_cast_api_response(media_id)
            cls.send_cors_json(handler, response)

        except Exception as e:
            cls.send_error(handler, f"Cast/Crew error: {str(e)}", 500)

    # ==========================================================================
    # 6. CATEGORIES API
    # ==========================================================================
    @classmethod
    def handle_categories(cls, handler: SimpleHTTPRequestHandler):
        """
        GET /api/media/categories
        Returns all available categories with metadata.
        """
        try:
            categories = []

            # Get categories from categorizer
            cat_signals = SmartCategorizer.CATEGORY_SIGNALS

            for cat_key in cat_signals.keys():
                meta = SmartCategorizer.get_category_metadata(cat_key)
                categories.append({
                    'slug': cat_key,
                    'display_name_ar': meta['display_name_ar'],
                    'display_name_en': meta['display_name_en'],
                    'icon': meta['icon'],
                    'color': meta['color']
                })

            # Add special composite categories
            composite_cats = [
                {'slug': 'all', 'display_name_ar': 'الكل', 'display_name_en': 'All', 'icon': '🎬', 'color': '#ffffff'},
                {'slug': 'anime', 'display_name_ar': 'أنمي', 'display_name_en': 'Anime', 'icon': '⛩️', 'color': '#ff69b4'},
                {'slug': 'indian_series', 'display_name_ar': 'مسلسلات هندي', 'display_name_en': 'Indian Series', 'icon': '🎭', 'color': '#ff9900'},
                {'slug': 'korean_series', 'display_name_ar': 'مسلسلات كوري', 'display_name_en': 'Korean Series', 'icon': '🇰🇷', 'color': '#ff6b9d'},
            ]

            for cat in composite_cats:
                if cat['slug'] not in [c['slug'] for c in categories]:
                    categories.append(cat)

            cls.send_cors_json(handler, {
                "categories": categories,
                "count": len(categories)
            })

        except Exception as e:
            cls.send_error(handler, f"Categories error: {str(e)}", 500)

    # ==========================================================================
    # 7. STREAM RESOLVE API
    # ==========================================================================
    @classmethod
    def handle_stream_resolve(cls, handler: SimpleHTTPRequestHandler, query: dict):
        """
        GET /api/media/stream
        Parameters:
        - url: stream URL to resolve
        - is_movie: boolean flag
        """
        try:
            stream_url = query.get("url", [""])[0]
            is_movie = query.get("is_movie", ["true"])[0].lower() == "true"

            if not stream_url:
                cls.send_error(handler, "Missing url parameter", 400)
                return

            # Decode URL if it has HTML entities
            clean_url = TextSanitizer.decode_html_entities(stream_url)

            # Check if it's a direct stream
            lower_url = clean_url.lower()
            is_direct = any(ext in lower_url for ext in ['.m3u8', '.mp4', '.mkv', '.avi'])

            # Check if it's an embed
            is_embed = any(h in lower_url for h in [
                'vipserver', 'liiivideo', 'hgcloud', 'mixdrop',
                'minochinos', 'vidmoly', 'vidlink', 'multiembed',
                'vidsrc', '2embed', 'embed', 'fasel'
            ])

            response = {
                "success": True,
                "stream_url": clean_url,
                "is_hls": '.m3u8' in lower_url,
                "is_embed": is_embed,
                "is_direct": is_direct,
                "is_movie": is_movie,
                "quality": "1080p FHD",
                "headers": StreamSanitizer.get_spoofed_headers(clean_url) if is_direct or is_embed else {}
            }

            cls.send_cors_json(handler, response)

        except Exception as e:
            cls.send_error(handler, f"Stream resolve error: {str(e)}", 500)

    # ==========================================================================
    # 8. EPISODES API
    # ==========================================================================
    @classmethod
    def handle_episodes(cls, handler: SimpleHTTPRequestHandler, query: dict):
        """
        GET /api/media/episodes
        Parameters:
        - id: series media ID
        - season: season number (optional, defaults to 1)
        """
        try:
            media_id = query.get("id", [""])[0]
            season_num = query.get("season", ["1"])[0]

            if not media_id:
                cls.send_error(handler, "Missing id parameter", 400)
                return

            details = VODDatabase.get_media_details(media_id)

            if not details:
                cls.send_error(handler, "Media not found", 404)
                return

            # Find the requested season
            try:
                season_number = int(season_num)
            except ValueError:
                season_number = 1

            season_data = next((s for s in details.get('seasons', [])
                              if s['season_number'] == season_number), None)

            if not season_data:
                cls.send_error(handler, f"Season {season_num} not found", 404)
                return

            # Sanitize episode data
            episodes = []
            for ep in season_data.get('episodes', []):
                episodes.append({
                    'episode_number': ep.get('episode_number'),
                    'title': TextSanitizer.sanitize(ep.get('title', ''), max_length=100),
                    'thumbnail': ep.get('thumbnail', ''),
                    'duration': ep.get('duration', ''),
                    'synopsis': TextSanitizer.sanitize(ep.get('synopsis', ''), max_length=200),
                    'server_count': len(ep.get('servers', []))
                })

            cls.send_cors_json(handler, {
                "media_id": media_id,
                "season_number": season_number,
                "season_title": season_data.get('title', f'الموسم {season_number}'),
                "episodes": episodes,
                "count": len(episodes)
            })

        except Exception as e:
            cls.send_error(handler, f"Episodes error: {str(e)}", 500)
