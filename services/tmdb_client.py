# -*- coding: utf-8 -*-
"""
A TuBe TMDB (The Movie Database) Client
========================================
Free-tier API integration providing:
  - Poster images (w500 / original)
  - Backdrop / still images per movie or episode
  - TMDB ID lookup by title + year
  - IMDb ID cross-reference

API key: free registration at https://www.themoviedb.org/settings/api
Place your key in config/remote_config.json under:
    { "tmdb": { "api_key": "YOUR_KEY_HERE" } }
or set environment variable TMDB_API_KEY.

Falls back gracefully when no key is available — callers always get a
safe return value (None / []) instead of an exception.
"""

import os
import re
import json
import time
import ssl
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

# ── Paths ───────────────────────────────────────────────────────────────────
_BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_DIR = os.path.join(_BASE_DIR, "config")
_CACHE_FILE = os.path.join(_CONFIG_DIR, "tmdb_cache.json")

# ── SSL (same permissive context used elsewhere in the project) ──────────────
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode    = ssl.CERT_NONE

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

TMDB_BASE = "https://api.themoviedb.org/3"
IMG_BASE  = "https://image.tmdb.org/t/p"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_api_key() -> str:
    """Load TMDB API key from env var or remote_config.json."""
    key = os.environ.get("TMDB_API_KEY", "").strip()
    if key:
        return key
    cfg_path = os.path.join(_CONFIG_DIR, "remote_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            key = data.get("tmdb", {}).get("api_key", "").strip()
        except Exception:
            pass
    return key


def _get(path: str, params: Dict[str, str], timeout: float = 5.0) -> Optional[Dict]:
    """GET a TMDB endpoint and return parsed JSON, or None on error."""
    api_key = _load_api_key()
    if not api_key:
        return None
    params["api_key"] = api_key
    qs  = urllib.parse.urlencode(params)
    url = f"{TMDB_BASE}{path}?{qs}"
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


# ── In-memory + disk cache ───────────────────────────────────────────────────

class _Cache:
    _data: Dict[str, Any] = {}
    _loaded = False

    @classmethod
    def _ensure(cls):
        if cls._loaded:
            return
        cls._loaded = True
        if os.path.exists(_CACHE_FILE):
            try:
                with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                    cls._data = json.load(f)
            except Exception:
                cls._data = {}

    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        cls._ensure()
        entry = cls._data.get(key)
        if not entry:
            return None
        # Expire after 14 days
        if time.time() - entry.get("ts", 0) > 1_209_600:
            del cls._data[key]
            return None
        return entry["val"]

    @classmethod
    def set(cls, key: str, val: Any):
        cls._ensure()
        cls._data[key] = {"val": val, "ts": time.time()}
        try:
            os.makedirs(_CONFIG_DIR, exist_ok=True)
            with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cls._data, f, ensure_ascii=False)
        except Exception:
            pass


# ── Public API ────────────────────────────────────────────────────────────────

class TMDBClient:
    """Thin wrapper around TMDB free-tier REST API."""

    # ── Search ────────────────────────────────────────────────────────────────

    @classmethod
    def search(cls, title: str, year: str = "", content_type: str = "movie") -> Optional[Dict]:
        """
        Search TMDB for a movie or TV show.
        Returns the best-matching result dict or None.
        """
        cache_key = f"search_{content_type}_{title}_{year}"
        cached = _Cache.get(cache_key)
        if cached is not None:
            return cached

        media   = "tv" if content_type in ("series", "anime", "tv_show") else "movie"
        clean   = cls._clean_title(title)
        params  = {"query": clean, "language": "ar", "include_adult": "false"}
        if year:
            yr = re.sub(r"\D", "", str(year))
            if yr:
                params["year" if media == "movie" else "first_air_date_year"] = yr

        data = _get(f"/search/{media}", params)
        result = None
        if data and data.get("results"):
            result = data["results"][0]

        # Try English if Arabic returned nothing
        if not result:
            params["language"] = "en-US"
            data = _get(f"/search/{media}", params)
            if data and data.get("results"):
                result = data["results"][0]

        _Cache.set(cache_key, result)
        return result

    @classmethod
    def get_tmdb_id(cls, title: str, year: str = "", content_type: str = "movie") -> Optional[str]:
        """Return TMDB ID string (e.g. '12345') or None."""
        r = cls.search(title, year, content_type)
        if r:
            return str(r.get("id", ""))
        return None

    # ── Posters ──────────────────────────────────────────────────────────────

    @classmethod
    def get_poster_url(cls, title: str, year: str = "", content_type: str = "movie",
                       size: str = "w500") -> Optional[str]:
        """Return a poster URL or None. size: w92/w185/w342/w500/w780/original."""
        cache_key = f"poster_{content_type}_{title}_{year}"
        cached = _Cache.get(cache_key)
        if cached is not None:
            return cached or None

        r = cls.search(title, year, content_type)
        url = None
        if r:
            path = r.get("poster_path")
            if path:
                url = f"{IMG_BASE}/{size}{path}"

        _Cache.set(cache_key, url or "")
        return url

    @classmethod
    def get_poster_url_by_id(cls, tmdb_id: str, content_type: str = "movie",
                              size: str = "w500") -> Optional[str]:
        """Fetch poster directly by TMDB numeric ID."""
        cache_key = f"poster_id_{tmdb_id}"
        cached = _Cache.get(cache_key)
        if cached is not None:
            return cached or None

        media = "tv" if content_type in ("series", "anime", "tv_show") else "movie"
        data  = _get(f"/{media}/{tmdb_id}", {"language": "ar"})
        url   = None
        if data:
            path = data.get("poster_path")
            if path:
                url = f"{IMG_BASE}/{size}{path}"

        _Cache.set(cache_key, url or "")
        return url

    # ── Backdrops / Stills ────────────────────────────────────────────────────

    @classmethod
    def get_stills(cls, title: str, year: str = "", content_type: str = "movie",
                   count: int = 5, size: str = "w780") -> List[str]:
        """Return a list of backdrop/still image URLs (up to `count`)."""
        cache_key = f"stills_{content_type}_{title}_{year}"
        cached = _Cache.get(cache_key)
        if cached is not None:
            return cached

        r = cls.search(title, year, content_type)
        stills: List[str] = []
        if r:
            tmdb_id = str(r.get("id", ""))
            media   = "tv" if content_type in ("series", "anime", "tv_show") else "movie"
            data    = _get(f"/{media}/{tmdb_id}/images", {})
            if data:
                backdrops = data.get("backdrops", [])[:count]
                stills    = [f"{IMG_BASE}/{size}{b['file_path']}" for b in backdrops if b.get("file_path")]

        _Cache.set(cache_key, stills)
        return stills

    @classmethod
    def get_episode_still(cls, tmdb_series_id: str, season: int,
                          episode: int, size: str = "w780") -> Optional[str]:
        """Return still image URL for a specific episode, or None."""
        cache_key = f"ep_still_{tmdb_series_id}_s{season}e{episode}"
        cached = _Cache.get(cache_key)
        if cached is not None:
            return cached or None

        data = _get(f"/tv/{tmdb_series_id}/season/{season}/episode/{episode}/images", {})
        url  = None
        if data:
            stills = data.get("stills", [])
            if stills and stills[0].get("file_path"):
                url = f"{IMG_BASE}/{size}{stills[0]['file_path']}"

        _Cache.set(cache_key, url or "")
        return url

    # ── Full enrichment ───────────────────────────────────────────────────────

    @classmethod
    def enrich_entry(cls, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a catalog entry in-place with TMDB data:
          - tmdb_id
          - poster (if missing or placeholder)
          - backdrop (if missing)
          - stills list
        Returns the (possibly modified) entry.
        """
        title        = entry.get("title") or entry.get("arabic_title") or ""
        year         = str(entry.get("year") or "")
        content_type = entry.get("content_type", "movie")

        # Skip if already has a valid TMDB id
        existing_tmdb = entry.get("tmdb_id", "")
        if not existing_tmdb:
            tmdb_id = cls.get_tmdb_id(title, year, content_type)
            if tmdb_id:
                entry["tmdb_id"] = tmdb_id

        tmdb_id = entry.get("tmdb_id", "")

        # Poster
        needs_poster = (
            not entry.get("poster")
            or entry.get("poster", "").endswith("gladiator_hero.jpg")
            or "unsplash.com" in entry.get("poster", "")
        )
        if needs_poster:
            if tmdb_id:
                url = cls.get_poster_url_by_id(tmdb_id, content_type)
            else:
                url = cls.get_poster_url(title, year, content_type)
            if url:
                entry["poster"]   = url
                entry["backdrop"] = entry.get("backdrop") or url

        # Backdrop (if still placeholder)
        needs_backdrop = (
            not entry.get("backdrop")
            or entry.get("backdrop", "").endswith("gladiator_hero.jpg")
        )
        if needs_backdrop and tmdb_id:
            stills = cls.get_stills(title, year, content_type, count=1, size="original")
            if stills:
                entry["backdrop"] = stills[0]

        # Stills list
        if not entry.get("stills") and tmdb_id:
            stills = cls.get_stills(title, year, content_type, count=5)
            if stills:
                entry["stills"] = stills

        return entry

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_title(title: str) -> str:
        """Strip noise words before searching TMDB."""
        noise = (
            r"مشاهدة|تحميل|مترجم|مدبلج|كامل|اون\s*لاين|بجودة\s*عالية|"
            r"ايجي\s*بست|ايجي\s*ديد|فاصل\s*اعلاني|اكوام|عرب\s*سيد|"
            r"فيلم|مسلسل|انمي|HD|FHD|4K|1080p|720p|FASELHD|FaselHD|"
            r"egybest|egydead|topcinema"
        )
        t = re.sub(noise, " ", title, flags=re.IGNORECASE)
        t = re.sub(r"[-–|·].*$", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    @classmethod
    def has_api_key(cls) -> bool:
        """Return True if a TMDB API key is configured."""
        return bool(_load_api_key())


# ── Batch fixer (run standalone) ──────────────────────────────────────────────

def fix_all_posters():
    """
    CLI: iterate catalog.json and enrich every entry with TMDB data.
    Usage:  python services/tmdb_client.py
    """
    import sys
    import tempfile

    if not TMDBClient.has_api_key():
        print(
            "[TMDB] ⚠️  No API key found!\n"
            "  1. Register at https://www.themoviedb.org/settings/api (free)\n"
            "  2. Add to config/remote_config.json:\n"
            '     { "tmdb": { "api_key": "YOUR_KEY" } }\n'
            "  3. Or set environment variable TMDB_API_KEY=YOUR_KEY\n"
        )
        return

    catalog_path = os.path.join(_BASE_DIR, "catalog.json")
    if not os.path.exists(catalog_path):
        print(f"[TMDB] catalog.json not found at {catalog_path}")
        return

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"[TMDB] Enriching {len(catalog)} catalog entries...")
    enriched = 0
    for i, entry in enumerate(catalog):
        original_poster = entry.get("poster", "")
        TMDBClient.enrich_entry(entry)
        if entry.get("poster") != original_poster:
            enriched += 1
            print(f"  [{i+1}/{len(catalog)}] ✅ {entry.get('title')[:50]}")
        elif (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(catalog)}] ... processing")

    # Atomic write
    catalog_dir = os.path.dirname(catalog_path)
    fd, tmp = tempfile.mkstemp(dir=catalog_dir, suffix=".tmp", prefix="catalog_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        os.replace(tmp, catalog_path)
    except Exception as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        print(f"[TMDB] Error writing catalog: {e}")
        return

    print(f"[TMDB] Done — enriched {enriched}/{len(catalog)} entries.")


if __name__ == "__main__":
    fix_all_posters()
