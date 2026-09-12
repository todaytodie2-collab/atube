# -*- coding: utf-8 -*-
"""
A TuBe Official TMDB API Integration Client
Uses official TMDB API Key: cabefb963ee5db1ecd2c5778bda9b6d0
Fetches pristine posters, high-res backdrops, movie stills gallery, and cast details.
"""

import json
import os
import re
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, Tuple, List

TMDB_API_KEY = "cabefb963ee5db1ecd2c5778bda9b6d0"
IMG_BASE_W500 = "https://image.tmdb.org/t/p/w500"
IMG_BASE_ORIGINAL = "https://image.tmdb.org/t/p/original"

class TMDBClient:
    @staticmethod
    def search_media(title: str, content_type: str = "movie") -> Optional[Dict[str, Any]]:
        clean_title = re.sub(r'202[0-9]|201[0-9]|مترجم|مدبلج|انمي|فيلم|مسلسل', '', title).strip()
        media_type = "tv" if content_type == "series" else "movie"

        url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={TMDB_API_KEY}&query={urllib.parse.quote(clean_title)}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get('results', [])
                if results:
                    return results[0]
        except Exception:
            pass
        return None

    @staticmethod
    def get_media_details(tmdb_id: int, content_type: str = "movie") -> Tuple[Optional[str], Optional[str], List[str]]:
        media_type = "tv" if content_type == "series" else "movie"
        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={TMDB_API_KEY}&append_to_response=images,credits"

        poster_url = None
        backdrop_url = None
        stills = []

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))

                if data.get('poster_path'):
                    poster_url = IMG_BASE_W500 + data['poster_path']
                if data.get('backdrop_path'):
                    backdrop_url = IMG_BASE_ORIGINAL + data['backdrop_path']

                images = data.get('images', {})
                backdrops = images.get('backdrops', [])
                for b in backdrops[:5]:
                    if b.get('file_path'):
                        stills.append(IMG_BASE_W500 + b['file_path'])

        except Exception:
            pass

        if not stills and backdrop_url:
            stills = [backdrop_url, backdrop_url, backdrop_url]

        return poster_url, backdrop_url, stills
