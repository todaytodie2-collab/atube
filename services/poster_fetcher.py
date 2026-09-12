# -*- coding: utf-8 -*-
"""
A TuBe Smart Poster Fetcher & Classifier Engine
================================================
Automatically fetches real high-resolution poster images for movies & series.
Replaces missing or dummy 'assets/gladiator_hero.jpg' posters with real
images from TMDB (primary) or TVMaze (fallback).
Also fixes anime indexing (separates Anime Movies vs Anime Series).

Changed from previous version:
  - Removed hardcoded KNOWN_POSTER_MAP with fake TMDB IDs
  - Now uses TMDBClient.enrich_entry() as primary source
  - TVMaze kept as lightweight fallback for series with no TMDB match
  - Writes catalog.json atomically to prevent partial-file corruption
"""

import json
import os
import re
import tempfile
import urllib.request
import urllib.parse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS   = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")


# ── TVMaze fallback (no API key required) ─────────────────────────────────────

def _tvmaze_poster(title: str) -> str | None:
    """Search TVMaze for a series poster. Free, no key needed."""
    clean = re.sub(
        r"\(.*?\)|202\d|201\d|مترجم|مدبلج|انمي|فيلم|مسلسل", "", title
    ).strip()
    url = f"https://api.tvmaze.com/singlesearch/shows?q={urllib.parse.quote(clean)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            img  = (data or {}).get("image", {}) or {}
            return img.get("original") or img.get("medium")
    except Exception:
        return None


# ── Content-type classifier ───────────────────────────────────────────────────

def _classify_item(item: dict) -> dict:
    """
    Fix content_type for anime and episodic content based on title keywords
    and seasons data. Returns the (possibly modified) item.
    """
    title    = item.get("title", "") + " " + item.get("arabic_title", "")
    category = item.get("category", "")
    c_type   = item.get("content_type", "movie")

    is_anime = category == "anime" or bool(
        re.search(r"انمي|أنمي|anime|كرتون", title, re.IGNORECASE)
    )
    has_episodic = bool(
        re.search(
            r"الموسم|موسم|حلقة|حلقات|Season|Episode|Arc|\bS\d+\b|\bE\d+\b",
            title, re.IGNORECASE
        )
    )
    has_seasons = (
        item.get("total_seasons", 0) > 0
        or (isinstance(item.get("seasons"), list) and bool(item["seasons"]))
    )

    if is_anime:
        item["category"] = "anime"
        if has_episodic or has_seasons:
            item["content_type"] = "series"
        elif re.search(r"فيلم|movie", title, re.IGNORECASE):
            item["content_type"] = "movie"
    elif (has_episodic or has_seasons) and c_type != "series":
        item["content_type"] = "series"

    return item


# ── Atomic write helpers ──────────────────────────────────────────────────────

def _atomic_write_json(path: str, data) -> None:
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp", prefix="catalog_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _update_bundled_js(catalog: list) -> None:
    if not os.path.exists(BUNDLED_JS):
        return
    with open(BUNDLED_JS, "r", encoding="utf-8") as f:
        js = f.read()
    m = re.search(
        r"(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)",
        js, re.DOTALL,
    )
    if m:
        new_js = m.group(1) + json.dumps(catalog, ensure_ascii=False) + ";" + m.group(3)
        with open(BUNDLED_JS, "w", encoding="utf-8") as f:
            f.write(new_js)


# ── Main entry point ──────────────────────────────────────────────────────────

def fix_content_type_and_posters() -> None:
    """
    1. Fix content_type for every item (anime / series / movie).
    2. Replace missing/placeholder posters using TMDB → TVMaze → skip.
    Writes results atomically to catalog.json and js/bundled-data.js.
    """
    print("[PosterFetcher] Starting Smart Classifier & Poster Fetcher...")

    if not os.path.exists(CATALOG_JSON):
        print(f"[PosterFetcher] Error: {CATALOG_JSON} not found.")
        return

    with open(CATALOG_JSON, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    # Lazy import so the service still works even without tmdb_client
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from tmdb_client import TMDBClient
        has_tmdb = TMDBClient.has_api_key()
    except ImportError:
        TMDBClient  = None  # type: ignore
        has_tmdb    = False

    fixed_types   = 0
    fixed_posters = 0
    PLACEHOLDER   = "assets/gladiator_hero.jpg"

    for item in catalog:
        original_type   = item.get("content_type")
        original_poster = item.get("poster", "")

        # 1. Fix content_type
        _classify_item(item)
        if item.get("content_type") != original_type:
            fixed_types += 1
            print(f"  [Classifier] {original_type} → {item['content_type']}: {item.get('title')[:60]}")

        # 2. Fix poster
        needs_poster = (
            not item.get("poster")
            or item.get("poster") == PLACEHOLDER
            or "unsplash.com" in item.get("poster", "")
            or "gladiator" in item.get("poster", "").lower()
        )
        if needs_poster:
            new_url = None

            # Primary: TMDB (requires API key)
            if has_tmdb and TMDBClient:
                TMDBClient.enrich_entry(item)
                new_url = item.get("poster") if item.get("poster") != original_poster else None

            # Fallback: TVMaze (series / anime only, no key needed)
            if not new_url and item.get("content_type") in ("series", "anime"):
                new_url = _tvmaze_poster(item.get("title", ""))
                if new_url:
                    item["poster"]   = new_url
                    item["backdrop"] = item.get("backdrop") or new_url

            if new_url:
                fixed_posters += 1
                print(f"  [Poster] ✅ {item.get('title')[:55]} → {new_url[:60]}")

    # Save
    _atomic_write_json(CATALOG_JSON, catalog)
    _update_bundled_js(catalog)

    print(
        f"[PosterFetcher] Done — fixed {fixed_types} content types "
        f"and {fixed_posters} poster images."
    )


if __name__ == "__main__":
    fix_content_type_and_posters()
