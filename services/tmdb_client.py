# -*- coding: utf-8 -*-
"""
A TuBe Official TMDB API Integration Client
Uses official TMDB API: checks env var, remote_config.json, or default fallback key.
Fetches pristine posters, high-res backdrops, movie stills gallery, and metadata.
Provides has_api_key(), enrich_entry(), and fix_all_posters() functions.
"""

import json
import os
import re
import sys
import tempfile
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, Tuple, List

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_JSON = os.path.join(PROJECT_ROOT, "config", "remote_config.json")
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")
DB_PATH = os.path.join(PROJECT_ROOT, "config", "atube_data.sqlite")

try:
    import env_loader
except ImportError:
    pass

DEFAULT_TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
IMG_BASE_W500 = "https://image.tmdb.org/t/p/w500"
IMG_BASE_ORIGINAL = "https://image.tmdb.org/t/p/original"


class TMDBClient:
    @classmethod
    def get_api_key(cls) -> str:
        """Retrieves active TMDB API key from env, config file, or fallback."""
        key = os.environ.get("TMDB_API_KEY", "").strip()
        if key:
            return key
        if os.path.exists(CONFIG_JSON):
            try:
                with open(CONFIG_JSON, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    cfg_key = cfg.get("tmdb", {}).get("api_key", "").strip()
                    if cfg_key:
                        return cfg_key
            except Exception:
                pass
        return DEFAULT_TMDB_API_KEY

    @classmethod
    def has_api_key(cls) -> bool:
        """Returns True if a valid API key is configured."""
        return bool(cls.get_api_key())

    @classmethod
    def normalize_title(cls, t: str) -> str:
        if not t:
            return ""
        t = re.sub(r'[\u064B-\u065F\u0670]', '', t)
        t = re.sub(r'[أإآا]', 'ا', t)
        t = re.sub(r'[ة]', 'ه', t)
        t = re.sub(r'[ى]', 'ي', t)
        t = re.sub(r'[^a-zA-Z0-9\u0600-\u06FF\s]', '', t)
        return t.strip().lower()

    @classmethod
    def score_candidate(cls, cand: Dict[str, Any], query_clean: str, expected_year: Optional[str]) -> int:
        score = 0
        cand_title = cand.get("title") or cand.get("name") or ""
        cand_orig = cand.get("original_title") or cand.get("original_name") or ""
        rel_date = cand.get("release_date") or cand.get("first_air_date") or ""
        cand_year = rel_date.split("-")[0] if rel_date else ""

        norm_q = cls.normalize_title(query_clean)
        norm_t = cls.normalize_title(cand_title)
        norm_o = cls.normalize_title(cand_orig)

        if norm_q == norm_t or norm_q == norm_o:
            score += 100
        elif norm_t.startswith(norm_q) or norm_o.startswith(norm_q):
            score += 50
        elif norm_q in norm_t or norm_q in norm_o:
            score += 30

        # Word difference penalty (e.g. query "اسد" vs candidate "اسد واربع قطط")
        words_q = set(norm_q.split())
        words_c = set((norm_t + " " + norm_o).split())
        extra = words_c - words_q
        if len(extra) > 1 and len(words_q) <= 2:
            score -= 40 * len(extra)

        # Strict year guard
        if expected_year and cand_year and expected_year.isdigit() and cand_year.isdigit():
            diff = abs(int(expected_year) - int(cand_year))
            if diff == 0:
                score += 80
            elif diff == 1:
                score += 40
            elif diff > 3:
                score -= 150

        return score

    @classmethod
    def search_media(cls, title: str, content_type: str = "movie", expected_year: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Extract explicit year from title if not passed
        if not expected_year:
            y_m = re.search(r'\b(202[0-9]|201[0-9]|19[0-9]{2})\b', title)
            if y_m:
                expected_year = y_m.group(1)

        clean_title = re.sub(r'\(.*?\)|202[0-9]|201[0-9]|مترجم|مدبلج|انمي|أنمي|فيلم|مسلسل|حلقة|\b[SE]\d+\b', '', title, flags=re.IGNORECASE).strip()
        media_type = "tv" if content_type == "series" else "movie"
        api_key = cls.get_api_key()
        if not api_key:
            return None

        year_param = f"&primary_release_year={expected_year}" if (expected_year and media_type == "movie") else ""
        if media_type == "tv" and expected_year:
            year_param = f"&first_air_date_year={expected_year}"

        url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={api_key}&query={urllib.parse.quote(clean_title)}{year_param}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get('results', [])
                if results:
                    scored = [(r, cls.score_candidate(r, clean_title, expected_year)) for r in results]
                    scored.sort(key=lambda x: x[1], reverse=True)
                    if scored[0][1] > 0:
                        return scored[0][0]
        except Exception:
            pass

        # Fallback search as multi
        try:
            multi_url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&query={urllib.parse.quote(clean_title)}"
            req = urllib.request.Request(multi_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = [r for r in data.get('results', []) if r.get('media_type') in ('movie', 'tv')]
                if results:
                    scored = [(r, cls.score_candidate(r, clean_title, expected_year)) for r in results]
                    scored.sort(key=lambda x: x[1], reverse=True)
                    if scored[0][1] > 0:
                        return scored[0][0]
        except Exception:
            pass
        return None

    @classmethod
    def get_media_details(cls, tmdb_id: int, content_type: str = "movie") -> Tuple[Optional[str], Optional[str], List[str]]:
        media_type = "tv" if content_type == "series" else "movie"
        api_key = cls.get_api_key()
        if not api_key:
            return None, None, []

        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={api_key}&append_to_response=images,credits"
        poster_url = None
        backdrop_url = None
        stills = []

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=6) as resp:
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

    @classmethod
    def get_cast_and_crew(cls, tmdb_id: int, content_type: str = "movie") -> List[Dict[str, Any]]:
        """Fetches cast and crew list with circular photo profile URLs and character roles."""
        media_type = "tv" if content_type == "series" else "movie"
        api_key = cls.get_api_key()
        if not api_key:
            return []

        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/credits?api_key={api_key}&language=ar-SA"
        cast_list = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for actor in data.get('cast', [])[:15]:
                    name = actor.get('name') or actor.get('original_name', '')
                    character = actor.get('character', 'شخصية رئيسية')
                    profile_path = actor.get('profile_path')
                    photo_url = f"https://image.tmdb.org/t/p/w185{profile_path}" if profile_path else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=120&q=80"
                    
                    cast_list.append({
                        "name": name,
                        "arabic_name": name,
                        "role": "actor",
                        "character_name": character,
                        "photo": photo_url
                    })
        except Exception:
            pass
        return cast_list

    @classmethod
    def enrich_entry(cls, media_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Enriches a media entry dictionary in-place with TMDB poster, backdrop, stills, rating, overview."""
        if not media_entry or not isinstance(media_entry, dict):
            return media_entry

        title = media_entry.get("title") or media_entry.get("arabic_title", "")
        c_type = media_entry.get("content_type", "movie")
        match = cls.search_media(title, c_type)
        if match:
            tmdb_id = match.get("id")
            resolved_type = "series" if (match.get("media_type") == "tv" or c_type == "series") else "movie"
            p, b, stills = cls.get_media_details(tmdb_id, resolved_type)

            if p:
                media_entry["poster"] = p
                media_entry["backdrop"] = b or p
            if stills:
                media_entry["stills"] = stills
            if match.get("vote_average") and not media_entry.get("rating"):
                media_entry["rating"] = f"★ {round(match['vote_average'], 1)} IMDb"
            if match.get("overview") and (not media_entry.get("synopsis") or "مشاهدة وتحميل" in media_entry.get("synopsis", "")):
                media_entry["synopsis"] = match["overview"]
            media_entry["tmdb_id"] = tmdb_id

        return media_entry


def fix_all_posters():
    """
    Scans catalog.json, enriches all items missing posters or backdrops via TMDB,
    and updates catalog.json, bundled-data.js, and atube_data.sqlite atomically.
    """
    print("[TMDBClient] Running fix_all_posters...")
    if not os.path.exists(CATALOG_JSON):
        print(f"[TMDBClient] Warning: {CATALOG_JSON} not found.")
        return

    with open(CATALOG_JSON, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    if not isinstance(catalog, list):
        return

    enriched_count = 0
    for item in catalog:
        poster = item.get("poster", "")
        needs_enrich = (
            not poster
            or "gladiator" in poster.lower()
            or "unsplash.com" in poster.lower()
            or not item.get("stills")
        )
        if needs_enrich:
            orig_poster = poster
            TMDBClient.enrich_entry(item)
            if item.get("poster") != orig_poster:
                enriched_count += 1
                print(f"  [TMDB Enriched] {item.get('title')[:50]} -> {item.get('poster')}")

    # Atomic write to catalog.json
    d = os.path.dirname(CATALOG_JSON)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp", prefix="catalog_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CATALOG_JSON)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    # Sync bundled-data.js
    if os.path.exists(BUNDLED_JS):
        try:
            with open(BUNDLED_JS, "r", encoding="utf-8") as f:
                js_content = f.read()
            m = re.search(
                r"(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)",
                js_content,
                re.DOTALL,
            )
            if m:
                new_js = m.group(1) + json.dumps(catalog, ensure_ascii=False) + ";" + m.group(3)
                with open(BUNDLED_JS, "w", encoding="utf-8") as f:
                    f.write(new_js)
        except Exception as e:
            print(f"[TMDBClient] Note updating bundled-data.js: {e}")

    # Sync SQLite database
    if os.path.exists(DB_PATH):
        try:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            for item in catalog:
                cur.execute(
                    "UPDATE vod_media SET poster = ?, backdrop = ? WHERE id = ?",
                    (item.get("poster"), item.get("backdrop"), item.get("id")),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[TMDBClient] Note updating SQLite: {e}")

    print(f"[TMDBClient] fix_all_posters completed: {enriched_count} items updated.")
