# -*- coding: utf-8 -*-
"""
A TuBe Real Catalog Manifest Engine
Reads from real data sources:
1. catalog.json (real harvested media)
2. vod_catalog.db / atube_data.sqlite (SQLite VOD database)
3. RSS Manager (live feeds)

Falls back to empty list if no data is available. No fake data.
"""

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_JSON_PATH = os.path.join(BASE_DIR, "catalog.json")
VOD_DB_PATH = os.path.join(BASE_DIR, "config", "vod_catalog.db")
VOD_DB_PATH2 = os.path.join(BASE_DIR, "config", "atube_data.sqlite")


class ProceduralManifestEngine:
    """
    Real catalog manifest engine.
    Reads from actual data sources: catalog.json and SQLite database.
    """

    _catalog_cache: Optional[List[Dict[str, Any]]] = None
    _db_cache: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def _load_catalog_json(cls) -> List[Dict[str, Any]]:
        if cls._catalog_cache is not None:
            return cls._catalog_cache

        if not os.path.exists(CATALOG_JSON_PATH):
            cls._catalog_cache = []
            return cls._catalog_cache

        try:
            with open(CATALOG_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    cls._catalog_cache = data
                else:
                    cls._catalog_cache = []
        except Exception:
            cls._catalog_cache = []

        return cls._catalog_cache

    @classmethod
    def _load_vod_db(cls) -> List[Dict[str, Any]]:
        if cls._db_cache is not None:
            return cls._db_cache

        db_path = VOD_DB_PATH if os.path.exists(VOD_DB_PATH) else VOD_DB_PATH2
        if not os.path.exists(db_path):
            cls._db_cache = []
            return cls._db_cache

        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT * FROM vod_media LIMIT 5000")
            rows = cur.fetchall()
            items = []
            for row in rows:
                item = dict(row)
                try:
                    item["genres"] = json.loads(item.get("genres", "[]") or "[]")
                except Exception:
                    item["genres"] = []
                try:
                    item["servers"] = json.loads(item.get("servers", "[]") or "[]")
                except Exception:
                    item["servers"] = []
                items.append(item)

            conn.close()
            cls._db_cache = items
        except Exception:
            cls._db_cache = []

        return cls._db_cache

    @classmethod
    def get_feed(cls, category: Optional[str] = None, page: int = 1, limit: int = 24) -> List[Dict[str, Any]]:
        items = cls._load_catalog_json()
        if not items:
            items = cls._load_vod_db()

        if category and category != "all":
            filtered = []
            for it in items:
                cat = (it.get("category") or "").lower()
                cat_code = (it.get("category") or "").lower()
                content_type = (it.get("content_type") or "").lower()

                if cat == category or cat_code == category:
                    filtered.append(it)
                    continue

                if category == "foreign" and content_type == "movie" and cat in ["foreign", "western"]:
                    filtered.append(it)
                elif category == "arabic" and cat in ["arabic", "arabic_series"]:
                    filtered.append(it)
                elif category == "turkish" and cat == "turkish":
                    filtered.append(it)
                elif category == "asian" and cat in ["asian", "korean"]:
                    filtered.append(it)
                elif category == "indian" and cat == "indian":
                    filtered.append(it)
                elif category == "anime" and content_type in ["anime", "cartoon"]:
                    filtered.append(it)
                elif category == "wrestling" and cat == "wrestling":
                    filtered.append(it)
                elif category == "documentary" and (cat == "documentary" or content_type == "documentary"):
                    filtered.append(it)
                elif category == "tv_show" and content_type in ["tv_show", "talk_show", "sports"]:
                    filtered.append(it)
            items = filtered

        start = (page - 1) * limit
        end = start + limit
        return items[start:end]

    @classmethod
    def get_details(cls, item_id: str) -> Optional[Dict[str, Any]]:
        items = cls._load_catalog_json()
        if not items:
            items = cls._load_vod_db()

        for it in items:
            if it.get("id") == item_id:
                return it

        return None

    @classmethod
    def search(cls, query: str) -> List[Dict[str, Any]]:
        if not query or len(query.strip()) < 2:
            return []

        q = query.lower().strip()
        items = cls._load_catalog_json()
        if not items:
            items = cls._load_vod_db()

        results = []
        for it in items:
            title = (it.get("title") or "").lower()
            ar_title = (it.get("arabic_title") or "").lower()
            if q in title or q in ar_title:
                results.append(it)
            if len(results) >= 15:
                break

        return results

    @classmethod
    def invalidate_cache(cls):
        cls._catalog_cache = None
        cls._db_cache = None
