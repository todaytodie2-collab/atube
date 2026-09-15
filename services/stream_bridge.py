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
import sqlite3
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from stream_extractor import DirectStreamExtractor
from deep_search_fallback import DeepSearchFallbackEngine
from mycima_harvester import MyCimaHarvester

DB_PATH = os.path.join(BASE_DIR, "config", "atube_data.sqlite")

class InvisibleStreamBridge:
    """
    Invisible Bridge that connects A TuBe with Arabic streaming portals.
    Resolves watch pages into direct clean video streams within 5-10 seconds.
    """

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    @classmethod
    def get_cached_direct_stream(cls, media_id: str, season: Optional[int] = None, episode: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Checks local SQLite database and resolves direct streams on-demand via TTL cache."""
        if not os.path.exists(DB_PATH) or not media_id:
            return None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=15.0)
            conn.execute("PRAGMA busy_timeout=15000;")
            cur = conn.cursor()
            if season is not None and episode is not None:
                cur.execute("""
                    SELECT server_name, stream_url, quality, badge 
                    FROM vod_servers 
                    WHERE media_id = ? AND season_number = ? AND episode_number = ?
                    ORDER BY id ASC
                """, (media_id, season, episode))
            else:
                cur.execute("""
                    SELECT server_name, stream_url, quality, badge 
                    FROM vod_servers 
                    WHERE media_id = ? AND (season_number IS NULL OR season_number = 1)
                    ORDER BY id ASC
                """, (media_id,))
            rows = cur.fetchall()

            # Also retrieve TMDB ID if available
            cur.execute("SELECT tmdb_id, content_type FROM vod_media WHERE id = ?", (media_id,))
            m_row = cur.fetchone()
            tmdb_id = m_row[0] if m_row else None
            c_type = m_row[1] if m_row else "movie"
            conn.close()

            if not rows:
                return None

            servers_matrix = []
            direct_match = None

            for row in rows:
                name, url, quality, badge = row
                if not url:
                    continue

                is_trusted = any(h in url.lower() for h in ["vidlink", "multiembed", "2embed", "vidsrc", "streamingnow", "autoembed", "hgcloud"])
                if is_trusted:
                    servers_matrix.append({
                        "name": name or "سيرفر عالمي سحابي",
                        "url": url,
                        "stream_url": url,
                        "raw_url": url,
                        "quality": quality or "1080p FHD",
                        "is_direct": False,
                        "is_hls": False,
                        "isEmbed": True,
                        "tier": 3,
                        "badge": "عالمي ⭐"
                    })
                    continue

                # On-demand resolution with TTL RAM caching
                resolved = DirectStreamExtractor.resolve(url)
                if resolved.get("success") and resolved.get("stream_url"):
                    item_entry = {
                        "name": f"{name or 'سيرفر فائق السرعة'} (مباشر ⚡)",
                        "url": resolved["stream_url"],
                        "stream_url": resolved["stream_url"],
                        "raw_url": url,
                        "quality": quality or "1080p FHD",
                        "is_direct": True,
                        "is_hls": resolved.get("is_hls", False),
                        "isEmbed": False,
                        "tier": 1,
                        "badge": "سريع ⚡"
                    }
                    servers_matrix.append(item_entry)
                    if not direct_match:
                        direct_match = item_entry
                else:
                    final_u = f"/api/watch/embed?url={urllib.parse.quote(url)}"
                    servers_matrix.append({
                        "name": name or "سيرفر سحابي",
                        "url": final_u,
                        "stream_url": final_u,
                        "raw_url": url,
                        "quality": quality or "1080p FHD",
                        "is_direct": False,
                        "is_hls": False,
                        "isEmbed": True,
                        "tier": 2,
                        "badge": "درع خفي 🛡️"
                    })

            # Sort matrix so direct streams (tier 1) come first
            servers_matrix.sort(key=lambda x: x.get("tier", 99))

            if direct_match:
                return {
                    "success": True,
                    "stream_url": direct_match["stream_url"],
                    "raw_url": direct_match.get("raw_url", ""),
                    "server_name": direct_match["name"],
                    "quality": direct_match["quality"],
                    "is_direct": True,
                    "is_hls": direct_match["is_hls"],
                    "badge": direct_match["badge"],
                    "source": "db_direct_resolved",
                    "servers_matrix": servers_matrix
                }
            elif servers_matrix:
                first = servers_matrix[0]
                return {
                    "success": True,
                    "stream_url": first["stream_url"],
                    "server_name": first["name"],
                    "quality": first["quality"],
                    "is_direct": False,
                    "is_hls": False,
                    "isEmbed": True,
                    "badge": first["badge"],
                    "source": "db_embed_fallback",
                    "servers_matrix": servers_matrix
                }
        except Exception as ex:
            print(f"[StreamBridge] DB cached stream error: {ex}")
        return None

    @classmethod
    def _sanitize_input(cls, value: str, max_len: int = 200, allow_digits_only: bool = False) -> str:
        """Strict input sanitizer: strips control characters, enforces max length, prevents injection."""
        if not value or not isinstance(value, str):
            return ""
        # Remove control characters and null bytes
        sanitized = re.sub(r'[\x00-\x1f\x7f]', '', value)
        # Remove potentially dangerous shell/SQL/path injection patterns
        sanitized = re.sub(r'[;|&`$(){}]', '', sanitized)
        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()
        # Enforce max length
        return sanitized[:max_len]

    @classmethod
    def resolve_clean_stream(cls, title: str, year: str = "", content_type: str = "movie",
                             season: Optional[int] = None, episode: Optional[int] = None,
                             media_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main Bridge Resolver:
        1. Validates and sanitizes all inputs.
        2. Checks database cache.
        3. Queries Arabic web portals (Akwam, ArabSeed, FaselHD, EgyDead).
        4. Extracts and tests direct streams.
        5. Returns the fastest verified stream with zero ads.
        """
        # ── Input Validation & Sanitization ─────────────────────────────────
        title = cls._sanitize_input(title, max_len=200)
        year = cls._sanitize_input(year, max_len=4)
        media_id = cls._sanitize_input(str(media_id or ""), max_len=100)
        content_type = cls._sanitize_input(content_type, max_len=30)

        # Validate year is a real numeric year
        if year and (not year.isdigit() or not (1900 <= int(year) <= 2100)):
            year = ""

        # Validate season/episode are safe integers
        if season is not None:
            try:
                season = max(1, min(int(season), 50))
            except (ValueError, TypeError):
                season = None
        if episode is not None:
            try:
                episode = max(1, min(int(episode), 500))
            except (ValueError, TypeError):
                episode = None

        if not title and not media_id:
            return {"success": False, "error": "العنوان أو معرف المحتوى مطلوب"}
        # ─────────────────────────────────────────────────────────────────────

        start_time = time.time()

        # 1. Check local cache
        if media_id:
            cached = cls.get_cached_direct_stream(media_id, season, episode)
            if cached:
                cached["elapsed_ms"] = int((time.time() - start_time) * 1000)
                return cached

        # 1b. Query MyCima & Cima4U Portal First (Priority Source for 5 Core Servers)
        try:
            mycima_res = MyCimaHarvester.search_and_harvest(title, year)
            if mycima_res.get("success") and mycima_res.get("servers"):
                mycima_servers = mycima_res["servers"]
                processed_matrix: List[Dict[str, Any]] = []

                for srv in mycima_servers:
                    raw_u = srv.get("url", "")
                    # Try resolving direct video (.m3u8 / .mp4)
                    res_direct = DirectStreamExtractor.resolve(raw_u)
                    if res_direct and res_direct.get("success") and res_direct.get("stream_url"):
                        processed_matrix.append({
                            "name": srv.get("name") or "سيرفر مباشر فائق السرعة",
                            "raw_name": srv.get("raw_name") or "",
                            "url": res_direct["stream_url"],
                            "stream_url": res_direct["stream_url"],
                            "quality": srv.get("quality") or "1080p FHD",
                            "is_direct": True,
                            "is_hls": res_direct.get("is_hls", False),
                            "isEmbed": False,
                            "badge": "سحابي صافٍ ⚡"
                        })
                    else:
                        # Route through Ghost Embed Proxy & Ad Absorber
                        ghost_proxy_url = f"/api/watch/embed?url={urllib.parse.quote(raw_u)}&referer={urllib.parse.quote('https://vid.mycima.cc/')}"
                        processed_matrix.append({
                            "name": srv.get("name") or "سيرفر مشاهدة سحابي",
                            "raw_name": srv.get("raw_name") or "",
                            "url": ghost_proxy_url,
                            "stream_url": ghost_proxy_url,
                            "original_url": raw_u,
                            "quality": srv.get("quality") or "1080p FHD",
                            "is_direct": False,
                            "is_hls": False,
                            "isEmbed": True,
                            "badge": "درع خفي 🛡️"
                        })

                if processed_matrix:
                    top_stream = processed_matrix[0]
                    if media_id:
                        source_url = top_stream.get("original_url") or top_stream["url"]
                        cls.save_server_to_db(media_id, top_stream["name"], source_url, top_stream["quality"], season, episode)

                    return {
                        "success": True,
                        "stream_url": top_stream["url"],
                        "server_name": top_stream["name"],
                        "quality": top_stream["quality"],
                        "is_direct": top_stream.get("is_direct", False),
                        "is_hls": top_stream.get("is_hls", False),
                        "isEmbed": top_stream.get("isEmbed", True),
                        "badge": top_stream.get("badge", "VIP ⚡"),
                        "servers_matrix": processed_matrix,
                        "downloads": mycima_res.get("downloads", []),
                        "elapsed_ms": int((time.time() - start_time) * 1000),
                        "source": "mycima_portal"
                    }
        except Exception as ex_mc:
            print(f"[StreamBridge] MyCima harvest notice: {ex_mc}")

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
            conn = sqlite3.connect(DB_PATH, timeout=15.0)
            conn.execute("PRAGMA busy_timeout=15000;")
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
