# -*- coding: utf-8 -*-
"""
A TuBe Smart Universal Stream Aggregator
Unifies media cards from multiple sources (EgyBest, EgyDead, TopCinema, FaselHD, Akwam, MyCima, ArabSeed)
Matches items using TMDB/IMDb IDs or normalized title signatures,
and aggregates all watching servers under a single unified card or episode.
"""

import re
import json
import os
from typing import List, Dict, Any


class SmartStreamAggregator:
    """
    Aggregates multi-source media entries and merges their streaming mirrors.
    Assigns clear badges:
    - (سيرفر إيجي بست VIP ⭐)
    - (سيرفر إيجي ديد HD ⚡)
    - (سيرفر توب سينما Fast 🚀)
    - (سيرفر فاصل إعلاني FHD 🎬)
    - (سيرفر أكوام Cloud ☁️)
    """

    AR_NORM = str.maketrans({
        'أ': 'ا', 'إ': 'ا', 'آ': 'ا',
        'ة': 'ه', 'ى': 'ي', 'ؤ': 'و',
    })

    SITE_BADGES = {
        'egybest': {'badge': 'إيجي بست VIP ⭐', 'label': 'سيرفر إيجي بست VIP'},
        'egydead': {'badge': 'إيجي ديد HD ⚡', 'label': 'سيرفر إيجي ديد HD'},
        'topcinema': {'badge': 'توب سينما Fast 🚀', 'label': 'سيرفر توب سينما Fast'},
        'faselhd': {'badge': 'فاصل إعلاني FHD 🎬', 'label': 'سيرفر فاصل إعلاني FHD'},
        'akwam': {'badge': 'أكوام Cloud ☁️', 'label': 'سيرفر أكوام Cloud'},
        'arabseed': {'badge': 'عرب سيد Direct ⚡', 'label': 'سيرفر عرب سيد Direct'},
        'mycima': {'badge': 'ماي سيما VIP 🌟', 'label': 'سيرفر ماي سيما VIP'},
        'vipserver': {'badge': 'VIP ⭐', 'label': 'سيرفر Vipserver المباشر'},
        'hgcloud': {'badge': 'Hgcloud ⚡', 'label': 'سيرفر Hgcloud السحابي'},
        'mixdrop': {'badge': 'Mixdrop 🚀', 'label': 'سيرفر Mixdrop السريع'},
        'minochinos': {'badge': 'Minochinos 💎', 'label': 'سيرفر Minochinos البديل'},
        'vidmoly': {'badge': 'Vidmoly 🎬', 'label': 'سيرفر Vidmoly بدون تقطيع'}
    }

    @classmethod
    def normalize_title(cls, title: str) -> str:
        if not title:
            return ""
        # Lowercase and normalize Arabic letters
        t = title.lower().translate(cls.AR_NORM)
        # Strip noise words
        noise = r'فيلم|مسلسل|برنامج|انمي|مترجم|مدبلج|مشاهدة|تحميل|اون\s*لاين|بجودة|عالية|fhd|hd|4k|1080p|720p|ايجي\s*بست|ايجي\s*ديد|توب\s*سينما|فاصل\s*اعلاني|اكوام|عرب\s*سيد|ماي\s*سيما|egybest|egydead|faselhd|akwam|topcinema'
        t = re.sub(noise, '', t, flags=re.IGNORECASE)
        # Remove years (2020-2026) to match base title signature
        t = re.sub(r'\b(202[0-9]|201[0-9])\b', '', t)
        # Remove non-alphanumeric except spaces
        t = re.sub(r'[^\w\s]', '', t)
        return re.sub(r'\s+', ' ', t).strip()

    @classmethod
    def get_server_site_key(cls, server: Dict[str, Any]) -> str:
        site = (server.get("site") or "").lower()
        name = (server.get("name") or "").lower()
        url = (server.get("stream_url") or server.get("url") or "").lower()

        combined = f"{site} {name} {url}"
        for key in cls.SITE_BADGES.keys():
            if key in combined:
                return key
        return "cloud"

    @classmethod
    def standardize_server(cls, server: Dict[str, Any]) -> Dict[str, Any]:
        key = cls.get_server_site_key(server)
        meta = cls.SITE_BADGES.get(key, {'badge': 'سحابي ☁️', 'label': 'سيرفر مشاهدة سحابي'})

        raw_url = server.get("stream_url") or server.get("url") or ""

        return {
            "name": server.get("name") or meta["label"],
            "stream_url": raw_url,
            "site": server.get("site") or key.capitalize(),
            "badge": server.get("badge") or meta["badge"],
            "quality": server.get("quality") or "1080p FHD",
            "isEmbed": True
        }

    @classmethod
    def aggregate_servers(cls, existing_servers: List[Dict[str, Any]], new_servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged = []
        seen_urls = set()

        for s in existing_servers + new_servers:
            std_s = cls.standardize_server(s)
            url = std_s.get("stream_url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(std_s)

        return merged

    @classmethod
    def merge_episodes(cls, existing_episodes: List[Dict[str, Any]], new_episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ep_map = {}

        for ep in existing_episodes + new_episodes:
            ep_num = ep.get("episode_number") or 1
            if ep_num not in ep_map:
                ep_map[ep_num] = {
                    "id": ep.get("id"),
                    "episode_number": ep_num,
                    "title": ep.get("title") or f"الحلقة {ep_num}",
                    "thumbnail": ep.get("thumbnail") or ep.get("still") or "",
                    "duration": ep.get("duration") or "45 دقيقة",
                    "synopsis": ep.get("synopsis") or "",
                    "servers": cls.aggregate_servers([], ep.get("servers", []))
                }
            else:
                # Merge servers into existing episode!
                current_ep = ep_map[ep_num]
                current_ep["servers"] = cls.aggregate_servers(current_ep["servers"], ep.get("servers", []))
                if not current_ep["thumbnail"] and (ep.get("thumbnail") or ep.get("still")):
                    current_ep["thumbnail"] = ep.get("thumbnail") or ep.get("still")

        # Return sorted by episode_number ascending (1, 2, 3, 4...)
        sorted_eps = list(ep_map.values())
        sorted_eps.sort(key=lambda x: int(x.get("episode_number") or 0))
        return sorted_eps

    @classmethod
    def merge_seasons(cls, existing_seasons: List[Dict[str, Any]], new_seasons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        season_map = {}

        for s in existing_seasons + new_seasons:
            s_num = s.get("season_number") or 1
            if s_num not in season_map:
                season_map[s_num] = {
                    "season_number": s_num,
                    "title": s.get("title") or f"الموسم {s_num}",
                    "episodes": cls.merge_episodes([], s.get("episodes", []))
                }
            else:
                current_s = season_map[s_num]
                current_s["episodes"] = cls.merge_episodes(current_s["episodes"], s.get("episodes", []))

        sorted_seasons = list(season_map.values())
        sorted_seasons.sort(key=lambda x: int(x.get("season_number") or 0))
        return sorted_seasons

    @classmethod
    def aggregate_catalog(cls, catalog_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main entry point: Scans catalog and merges matching items across portals.
        """
        aggregated_map = {}

        for item in catalog_items:
            tmdb_id = item.get("tmdb_id") or item.get("imdb_id")
            norm_title = cls.normalize_title(item.get("title") or item.get("arabic_title") or "")
            year = item.get("year") or ""
            c_type = item.get("content_type") or "movie"

            # Generate unique match key
            if tmdb_id:
                key = f"tmdb_{tmdb_id}"
            else:
                key = f"{c_type}_{norm_title}_{year}"

            if key not in aggregated_map:
                # Initialize aggregated item
                new_item = dict(item)
                new_item["servers"] = cls.aggregate_servers([], item.get("servers", []))
                if c_type == "series" and item.get("seasons"):
                    new_item["seasons"] = cls.merge_seasons([], item.get("seasons", []))
                aggregated_map[key] = new_item
            else:
                # Merge into existing aggregated item
                target = aggregated_map[key]
                target["servers"] = cls.aggregate_servers(target.get("servers", []), item.get("servers", []))

                # Merge seasons/episodes if series
                if c_type == "series":
                    target["seasons"] = cls.merge_seasons(target.get("seasons", []), item.get("seasons", []))

                # Preserve richest metadata (poster, backdrop, synopsis)
                if not target.get("poster") or target.get("poster").endswith("gladiator_hero.jpg"):
                    if item.get("poster") and not item.get("poster").endswith("gladiator_hero.jpg"):
                        target["poster"] = item["poster"]

                if not target.get("synopsis") and item.get("synopsis"):
                    target["synopsis"] = item["synopsis"]

        return list(aggregated_map.values())
