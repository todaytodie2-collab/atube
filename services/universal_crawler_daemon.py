# -*- coding: utf-8 -*-
"""
A TuBe - Universal Content Crawler & Auto-Stream Discovery Daemon
Periodically scans all catalog and database items, searches major Arabic & global streaming portals,
extracts direct/clean streaming links, and persists them into the SQLite database.
"""

import os
import sys
import json
import time
import sqlite3
import threading
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from stream_bridge import InvisibleStreamBridge

CATALOG_PATH = os.path.join(BASE_DIR, "data", "catalog.json")
DB_PATH = os.path.join(BASE_DIR, "config", "atube_data.sqlite")


class UniversalCrawlerDaemon:
    _is_running = False
    _thread = None
    _stats = {
        "last_run": None,
        "total_scanned": 0,
        "successful_extractions": 0,
        "status": "idle"
    }

    @classmethod
    def get_all_media_items(cls) -> List[Dict[str, Any]]:
        """Loads all media items from catalog.json and SQLite."""
        items_dict: Dict[str, Dict[str, Any]] = {}

        # 1. Load from catalog.json
        if os.path.exists(CATALOG_PATH):
            try:
                with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                    cat_items = json.load(f)
                    if isinstance(cat_items, list):
                        for item in cat_items:
                            m_id = item.get("id") or item.get("title")
                            if m_id:
                                items_dict[m_id] = item
            except Exception as e:
                print(f"[CrawlerDaemon] Error reading catalog.json: {e}")

        # 2. Load from SQLite
        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                rows = cur.execute("SELECT id, title, arabic_title, year, content_type FROM vod_media").fetchall()
                conn.close()
                for r in rows:
                    m_id = r["id"]
                    if m_id not in items_dict:
                        items_dict[m_id] = {
                            "id": m_id,
                            "title": r["arabic_title"] or r["title"],
                            "year": r["year"],
                            "type": r["content_type"]
                        }
            except Exception as e:
                print(f"[CrawlerDaemon] Error reading SQLite: {e}")

        return list(items_dict.values())

    @classmethod
    def check_has_valid_stream(cls, media_id: str) -> bool:
        """Returns True if the media already has direct high-speed streams saved."""
        if not os.path.exists(DB_PATH) or not media_id:
            return False
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM vod_servers WHERE media_id = ? AND stream_url LIKE 'http%'", (media_id,))
            cnt = cur.fetchone()[0]
            conn.close()
            return cnt > 0
        except Exception:
            return False

    @classmethod
    def process_media_item(cls, item: Dict[str, Any]) -> bool:
        """Searches portals and resolves direct stream for a single media item."""
        media_id = item.get("id") or ""
        title = item.get("title") or item.get("arabic_title") or item.get("name") or ""
        year = str(item.get("year") or "")
        c_type = item.get("type") or item.get("content_type") or "movie"

        if not title:
            return False

        # If already has direct working stream, skip to conserve bandwidth
        if cls.check_has_valid_stream(media_id):
            return True

        # Perform discovery via InvisibleStreamBridge
        res = InvisibleStreamBridge.resolve_clean_stream(
            title=title,
            year=year,
            content_type=c_type,
            media_id=media_id
        )

        if res.get("success"):
            return True
        return False

    @classmethod
    def crawl_all(cls, max_items: Optional[int] = None, force: bool = False):
        """Single pass crawl over all catalog content."""
        items = cls.get_all_media_items()
        cls._stats["status"] = "crawling"
        cls._stats["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        cls._stats["total_scanned"] = 0
        cls._stats["successful_extractions"] = 0

        target_items = items if max_items is None else items[:max_items]

        for item in target_items:
            cls._stats["total_scanned"] += 1
            media_id = item.get("id") or ""
            title = item.get("title") or ""

            if not force and cls.check_has_valid_stream(media_id):
                continue

            try:
                ok = cls.process_media_item(item)
                if ok:
                    cls._stats["successful_extractions"] += 1
            except Exception as ex:
                pass

            # Polite crawl delay
            time.sleep(1.0)

        cls._stats["status"] = "idle"

    @classmethod
    def _daemon_loop(cls, interval_seconds: int = 1800):
        while cls._is_running:
            try:
                cls.crawl_all(max_items=50)
            except Exception as e:
                print(f"[CrawlerDaemon] Exception in loop: {e}")
            
            # Wait for next interval
            waited = 0
            while waited < interval_seconds and cls._is_running:
                time.sleep(5)
                waited += 5

    @classmethod
    def start_background_daemon(cls, interval_seconds: int = 1800):
        """Starts the crawler daemon in a non-blocking background thread."""
        if cls._is_running:
            return
        cls._is_running = True
        cls._thread = threading.Thread(target=cls._daemon_loop, args=(interval_seconds,), daemon=True)
        cls._thread.start()

    @classmethod
    def stop_daemon(cls):
        cls._is_running = False

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        return dict(cls._stats)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A TuBe Universal Crawler Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single pass and exit")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items")
    parser.add_argument("--force", action="store_true", help="Force re-crawl even if streams exist")
    args = parser.parse_args()

    print(f"Starting A TuBe Universal Crawler Daemon (limit={args.limit}, force={args.force})...")
    UniversalCrawlerDaemon.crawl_all(max_items=args.limit, force=args.force)
    stats = UniversalCrawlerDaemon.get_stats()
    print(f"Done! Scanned: {stats['total_scanned']}, New Streams: {stats['successful_extractions']}")
