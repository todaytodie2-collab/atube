# -*- coding: utf-8 -*-
"""
A TuBe Content Registry — Single Source of Truth for Deduplication
====================================================================
Replaces the scattered dedup logic that existed independently in:
  - catalog_sync._sync_to_catalog_json()
  - stream_aggregator.SmartStreamAggregator.aggregate_catalog()

All dedup decisions now go through ONE place:  ContentRegistry.

Matching priority:
  1. TMDB ID  (tmdb_12345)         ← most reliable, cross-language
  2. IMDb ID  (imdb_tt1234567)
  3. Normalized title + year + type ← fuzzy fallback

Usage (catalog_sync.py):
    from content_registry import ContentRegistry
    media_id = ContentRegistry.register(entry)   # dedup + save

Usage (read):
    match_id = ContentRegistry.find(title, year, tmdb_id)
"""

import os
import re
import json
import hashlib
import tempfile
from typing import Dict, List, Any, Optional

_BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(_BASE_DIR, "catalog.json")


# ── Title normalization ───────────────────────────────────────────────────────

_AR_NORM = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي", "ؤ": "و"})

_NOISE_RE = re.compile(
    r"مشاهدة|تحميل|مترجم|مدبلج|كامل|اون\s*لاين|بجودة\s*عالية|"
    r"ايجي\s*بست|ايجي\s*ديد|فاصل\s*اعلاني|اكوام|عرب\s*سيد|ماي\s*سيما|"
    r"فيلم|مسلسل|انمي|برنامج|"
    r"HD|FHD|4K|1080p|720p|"
    r"egybest|egydead|topcinema|faselhd|akwam|arabseed|mycima|"
    r"FASELHD|FaselHD",
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")


def _normalize(title: str) -> str:
    """Canonical title for matching — strips noise, diacritics, punctuation."""
    if not title:
        return ""
    t = title.lower().translate(_AR_NORM)
    t = _NOISE_RE.sub(" ", t)
    t = _YEAR_RE.sub(" ", t)
    t = re.sub(r"[^\w\u0600-\u06FF]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ── ID generators ─────────────────────────────────────────────────────────────

def _tmdb_key(tmdb_id: str) -> str:
    return f"tmdb_{tmdb_id}"


def _imdb_key(imdb_id: str) -> str:
    return f"imdb_{imdb_id}"


def _title_key(title: str, year: str, content_type: str) -> str:
    norm = _normalize(title)
    yr   = re.sub(r"\D", "", str(year or ""))
    if not norm:
        norm = "item_" + hashlib.md5(title.encode("utf-8", "replace")).hexdigest()[:8]
    return f"{content_type}_{norm}_{yr}"


def _slug(title: str) -> str:
    return re.sub(r"[^\w\u0600-\u06FF]+", "-", title.lower()).strip("-") or "item"


# ── Registry ──────────────────────────────────────────────────────────────────

class ContentRegistry:
    """
    Manages catalog.json as a dict keyed by canonical match-key for O(1) lookup.
    All mutations write atomically to disk.
    """

    # In-memory index:  match_key → catalog list index
    _index: Dict[str, int]     = {}
    _items: List[Dict]         = []
    _loaded: bool              = False

    # ── Load / save ───────────────────────────────────────────────────────────

    @classmethod
    def _load(cls) -> None:
        if cls._loaded:
            return
        cls._loaded = True
        if not os.path.exists(CATALOG_PATH):
            cls._items = []
            cls._index = {}
            return
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            cls._items = data if isinstance(data, list) else list(data.values())
        except Exception:
            cls._items = []
        cls._rebuild_index()

    @classmethod
    def _rebuild_index(cls) -> None:
        """Build all lookup keys for every existing item."""
        cls._index = {}
        for i, item in enumerate(cls._items):
            for key in cls._keys_for(item):
                if key not in cls._index:
                    cls._index[key] = i

    @classmethod
    def _save(cls) -> None:
        """Atomically write catalog.json."""
        d = os.path.dirname(CATALOG_PATH)
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp", prefix="catalog_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(cls._items, f, ensure_ascii=False, indent=2)
            os.replace(tmp, CATALOG_PATH)
        except Exception as e:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            print(f"[ContentRegistry] ⚠️  save error: {e}")

    # ── Key generation ────────────────────────────────────────────────────────

    @classmethod
    def _keys_for(cls, item: Dict) -> List[str]:
        keys = []
        tmdb = str(item.get("tmdb_id") or "").strip()
        imdb = str(item.get("imdb_id") or "").strip()
        title = item.get("title") or item.get("arabic_title") or ""
        year  = str(item.get("year") or "")
        ctype = item.get("content_type", "movie")

        if tmdb:
            keys.append(_tmdb_key(tmdb))
        if imdb and imdb.startswith("tt"):
            keys.append(_imdb_key(imdb))
        # Always add a title key as final fallback
        title_k = _title_key(title, year, ctype)
        if title_k:
            keys.append(title_k)
        return keys

    # ── Public API ────────────────────────────────────────────────────────────

    @classmethod
    def find(cls,
             title: str,
             year: str = "",
             content_type: str = "movie",
             tmdb_id: str = "",
             imdb_id: str = "") -> Optional[int]:
        """
        Return the list-index of an existing matching item, or None.
        Checks TMDB ID → IMDb ID → normalized title.
        """
        cls._load()

        if tmdb_id:
            idx = cls._index.get(_tmdb_key(str(tmdb_id)))
            if idx is not None:
                return idx

        if imdb_id and imdb_id.startswith("tt"):
            idx = cls._index.get(_imdb_key(imdb_id))
            if idx is not None:
                return idx

        return cls._index.get(_title_key(title, year, content_type))

    @classmethod
    def register(cls, entry: Dict[str, Any]) -> str:
        """
        Dedup-aware insert/merge.
        • If a match exists: merge servers + update stills/poster if richer.
        • If new: append to catalog.
        Returns the canonical media_id used.
        """
        cls._load()

        title    = entry.get("title") or entry.get("arabic_title") or ""
        year     = str(entry.get("year") or "")
        ctype    = entry.get("content_type", "movie")
        tmdb_id  = str(entry.get("tmdb_id") or "").strip()
        imdb_id  = str(entry.get("imdb_id") or "").strip()

        idx = cls.find(title, year, ctype, tmdb_id, imdb_id)

        if idx is not None:
            # ── Merge into existing ──────────────────────────────────────────
            target = cls._items[idx]
            cls._merge_servers(target, entry.get("servers") or [])
            cls._merge_stills(target, entry.get("stills") or [])
            cls._upgrade_poster(target, entry.get("poster"), entry.get("backdrop"))
            if tmdb_id and not target.get("tmdb_id"):
                target["tmdb_id"] = tmdb_id
            media_id = target["id"]
            print(f"[ContentRegistry] Merged servers into '{target.get('title')}'")
        else:
            # ── New entry ────────────────────────────────────────────────────
            slug = _slug(title)
            yr   = re.sub(r"\D", "", year)
            tmdb_suffix = f"-tmdb{tmdb_id}" if tmdb_id else ""
            media_id = entry.get("id") or f"{slug}-{yr}{tmdb_suffix}"
            entry["id"] = media_id

            cls._items.append(entry)
            new_idx = len(cls._items) - 1

            # Register all keys for this new item
            for key in cls._keys_for(entry):
                cls._index.setdefault(key, new_idx)

            print(f"[ContentRegistry] New entry: '{title}' → {media_id}")

        cls._save()
        return media_id

    @classmethod
    def get_all(cls) -> List[Dict]:
        """Return all catalog items (read-only snapshot)."""
        cls._load()
        return list(cls._items)

    @classmethod
    def reload(cls) -> None:
        """Force reload from disk (call after external writes)."""
        cls._loaded = False
        cls._load()

    # ── Merge helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _merge_servers(target: Dict, new_servers: List[Dict]) -> None:
        existing = target.get("servers") or []
        seen     = {s.get("stream_url") for s in existing if s.get("stream_url")}
        added    = 0
        for s in new_servers:
            url = s.get("stream_url")
            if url and url not in seen:
                existing.append(s)
                seen.add(url)
                added += 1
        target["servers"] = existing
        if added:
            print(f"  [ContentRegistry] +{added} server(s) merged.")

    @staticmethod
    def _merge_stills(target: Dict, new_stills: List[str]) -> None:
        existing = set(target.get("stills") or [])
        combined = list(existing) + [s for s in new_stills if s not in existing]
        if combined:
            target["stills"] = combined[:10]  # cap at 10

    @staticmethod
    def _upgrade_poster(target: Dict, new_poster: Optional[str], new_backdrop: Optional[str]) -> None:
        """Replace placeholder poster/backdrop with a real one."""
        BAD = ("gladiator_hero.jpg", "unsplash.com", "")
        cur_poster = target.get("poster", "")
        is_bad = not cur_poster or any(b in cur_poster for b in BAD)
        if is_bad and new_poster and not any(b in new_poster for b in BAD):
            target["poster"] = new_poster
        cur_bd = target.get("backdrop", "")
        is_bad_bd = not cur_bd or any(b in cur_bd for b in BAD)
        if is_bad_bd and new_backdrop and not any(b in new_backdrop for b in BAD):
            target["backdrop"] = new_backdrop


# ── Quick CLI test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    items = ContentRegistry.get_all()
    print(f"[ContentRegistry] Catalog loaded: {len(items)} items, {len(ContentRegistry._index)} index keys.")
