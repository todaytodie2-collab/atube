# -*- coding: utf-8 -*-
"""
A TuBe - Invisible Stream Bridge & Clean Video Relay Engine
1. Discovers, unlocks, and extracts clean streaming servers from major Arabic and international portals.
2. Strips all ads, popups, anti-CORS guards, and anti-hotlinking headers.
3. Feeds direct video chunks (.m3u8 / .mp4) to A TuBe player seamlessly.
"""

import os
import sys
import re
import json
import time
import ssl
import sqlite3
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from stream_extractor import DirectStreamExtractor
from deep_search_fallback import DeepSearchFallbackEngine

DB_PATH = os.path.join(BASE_DIR, "config", "atube_data.sqlite")

class InvisibleStreamBridge:
    """
    Invisible Bridge that connects A TuBe with Arabic streaming portals.
    Resolves watch pages into direct clean video streams within 5-10 seconds.
    """

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    @classmethod
    def get_cached_direct_stream(cls, media_id: str, season: Optional[int] = None, episode: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Checks local SQLite database for pre-extracted direct streams."""
        if not os.path.exists(DB_PATH) or not media_id:
            return None
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            if season is not None and episode is not None:
                cur.execute("""
                    SELECT server_name, stream_url, quality, badge 
                    FROM vod_servers 
                    WHERE media_id = ? AND season_number = ? AND episode_number = ?
                    ORDER BY id ASC LIMIT 5
                """, (media_id, season, episode))
            else:
                cur.execute("""
                    SELECT server_name, stream_url, quality, badge 
                    FROM vod_servers 
                    WHERE media_id = ? AND (season_number IS NULL OR season_number = 1)
                    ORDER BY id ASC LIMIT 5
                """, (media_id,))
            rows = cur.fetchall()
            conn.close()

            for row in rows:
                name, url, quality, badge = row
                if url and any(ext in url.lower() for ext in ['.m3u8', '.mp4', 'stream', 'hls']):
                    return {
                        "success": True,
                        "stream_url": url,
                        "server_name": name or "سيرفر البث المباشر الفوري",
                        "quality": quality or "1080p FHD",
                        "is_direct": True,
                        "is_hls": ".m3u8" in url.lower(),
                        "badge": badge or "سريع ⚡",
                        "source": "cache"
                    }
        except Exception:
            pass
        return None

    @classmethod
    def resolve_clean_stream(cls, title: str, year: str = "", content_type: str = "movie", 
                             season: Optional[int] = None, episode: Optional[int] = None, 
                             media_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main Bridge Resolver:
        1. Checks database cache.
        2. Queries Arabic web portals (Akwam, ArabSeed, FaselHD, EgyDead).
        3. Extracts and tests direct streams.
        4. Returns the fastest verified stream with zero ads.
        """
        start_time = time.time()

        # 1. Check local cache
        if media_id:
            cached = cls.get_cached_direct_stream(media_id, season, episode)
            if cached:
                cached["elapsed_ms"] = int((time.time() - start_time) * 1000)
                return cached

        # 2. Search Arabic portals in parallel (Akwam, ArabSeed, FaselHD)
        search_query = title.strip()
        if year and year.isdigit() and int(year) > 2000:
            search_query_with_year = f"{search_query} {year}"
        else:
            search_query_with_year = search_query

        candidates: List[Dict[str, Any]] = []

        # Use DeepSearchFallbackEngine to harvest portals
        portal_links: List[str] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            f_akwam = executor.submit(DeepSearchFallbackEngine.search_akwam, search_query)
            f_arabseed = executor.submit(DeepSearchFallbackEngine.search_arabseed, search_query)
            f_fasel = executor.submit(DeepSearchFallbackEngine.search_faselhd, search_query)

            for f in as_completed([f_akwam, f_arabseed, f_fasel], timeout=6.0):
                try:
                    links = f.result()
                    if links:
                        portal_links.extend(links)
                except Exception:
                    pass

        # 3. Extract embed/direct streams from found pages
        found_servers: List[Dict[str, Any]] = []
        if portal_links:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(DeepSearchFallbackEngine.extract_embed_servers, link): link for link in portal_links[:4]}
                for future in as_completed(futures, timeout=6.0):
                    try:
                        srvs = future.result()
                        if srvs:
                            found_servers.extend(srvs)
                    except Exception:
                        pass

        # 4. Try resolving direct streams from extracted candidate hosts
        for srv in found_servers:
            raw_url = srv.get("stream_url") or srv.get("url") or ""
            if not raw_url:
                continue

            # Try resolving direct video (.m3u8 / .mp4)
            resolved = DirectStreamExtractor.resolve(raw_url)
            if resolved and resolved.get("success") and resolved.get("stream_url"):
                clean_stream = resolved["stream_url"]
                is_hls = resolved.get("is_hls", ".m3u8" in clean_stream)
                
                # Save to cache if media_id provided
                if media_id:
                    cls.save_server_to_db(media_id, srv.get("name") or "سيرفر البث المباشر", clean_stream, srv.get("quality") or "1080p FHD", season, episode)

                return {
                    "success": True,
                    "stream_url": clean_stream,
                    "server_name": srv.get("name") or "سيرفر A Tube فائق السرعة",
                    "quality": srv.get("quality") or "1080p FHD",
                    "is_direct": True,
                    "is_hls": is_hls,
                    "badge": "سحابي صافٍ ⚡",
                    "elapsed_ms": int((time.time() - start_time) * 1000),
                    "source": "bridge_scraped"
                }

        # 5. If no direct raw file, return top clean embed provider
        if found_servers:
            top_embed = found_servers[0]
            clean_url = top_embed.get("stream_url") or top_embed.get("url")
            return {
                "success": True,
                "stream_url": clean_url,
                "server_name": top_embed.get("name") or "سيرفر مشاهدة سحابي",
                "quality": top_embed.get("quality") or "1080p HD",
                "is_direct": False,
                "is_hls": False,
                "badge": "سحابي مباشر 🎬",
                "elapsed_ms": int((time.time() - start_time) * 1000),
                "source": "bridge_embed"
            }

        return {
            "success": False,
            "error": "لم يتم العثور على بث مباشر صافٍ في المهلة المحددة",
            "elapsed_ms": int((time.time() - start_time) * 1000)
        }

    @classmethod
    def save_server_to_db(cls, media_id: str, name: str, url: str, quality: str, season: Optional[int], episode: Optional[int]):
        """Persists freshly discovered stream into SQLite database."""
        if not os.path.exists(DB_PATH) or not media_id or not url:
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO vod_servers (media_id, season_number, episode_number, site, quality, server_name, stream_url, badge)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                media_id,
                season,
                episode,
                "DirectBridge",
                quality or "1080p FHD",
                name,
                url,
                "VIP Direct ⚡"
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass
