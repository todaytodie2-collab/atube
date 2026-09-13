# -*- coding: utf-8 -*-
"""
A TuBe High-Speed M3U Bulk VOD Importer
Parses large M3U/M3U8 VOD playlists containing thousands of movies & series.
Automatically categorizes them, standardizes metadata, and injects them instantly into the catalog.
"""

import os
import re
import json
import sqlite3
from typing import List, Dict, Any
from tmdb_client import TMDBClient
from categorizer import SmartCategorizer

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "config", "atube_data.sqlite")
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

class M3UBulkImporter:
    @staticmethod
    def parse_m3u(file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            print(f"[M3U Importer] Error: File {file_path} not found.")
            return []

        entries = []
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_item = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#EXTINF:"):
                # Extract title
                title_match = re.search(r',(.*?)$', line)
                if title_match:
                    raw_title = title_match.group(1).strip()
                    current_item["title"] = raw_title

                # Extract logo
                logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                if logo_match:
                    current_item["poster"] = logo_match.group(1)

                # Extract group/category
                group_match = re.search(r'group-title="([^"]+)"', line)
                if group_match:
                    current_item["raw_category"] = group_match.group(1)

            elif not line.startswith("#"):
                # This is the URL
                if "title" in current_item:
                    current_item["url"] = line
                    entries.append(current_item)
                    current_item = {}

        return entries

    @staticmethod
    def convert_to_catalog_format(m3u_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        catalog_items = []
        print(f"[M3U Importer] Processing {len(m3u_entries)} VOD entries...")

        for entry in m3u_entries:
            raw_title = entry.get("title", "")
            if not raw_title: continue

            # Clean title (remove year, tags like [1080p], etc.)
            clean_title = re.sub(r'\[.*?\]|\(.*?\)|1080p|720p|4k|FHD|HD', '', raw_title).strip()

            # Extract Year if present
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', raw_title)
            year = year_match.group(1) if year_match else "2026"

            # Smart Categorization
            hint = entry.get("raw_category", "")
            cat_data = SmartCategorizer.classify(clean_title, content_type_hint=hint)

            # Create standard server format
            server = {
                "name": "سيرفر VOD المباشر ⚡",
                "stream_url": entry["url"],
                "site": "VOD_Stream",
                "badge": "VOD ⚡",
                "quality": "1080p HD",
                "isEmbed": False
            }

            # Generate Safe ID
            item_id = f"vod_{re.sub(r'[^a-zA-Z0-9]', '', clean_title.lower())}_{year}"

            item = {
                "id": item_id,
                "title": clean_title,
                "arabic_title": clean_title,
                "content_type": cat_data["content_type"],
                "category": cat_data["category"],
                "year": year,
                "rating": "★ 8.5 VOD",
                "quality": "1080p HD",
                "poster": entry.get("poster", "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500&q=80"),
                "backdrop": entry.get("poster", "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=1280&q=80"),
                "servers": [server]
            }

            catalog_items.append(item)

        return catalog_items

    @classmethod
    def import_and_inject(cls, m3u_file_path: str):
        print(f"[*] Starting M3U Bulk Import from: {m3u_file_path}")
        raw_entries = cls.parse_m3u(m3u_file_path)
        new_items = cls.convert_to_catalog_format(raw_entries)

        if not new_items:
            print("[!] No valid VOD items found to import.")
            return

        # Load existing
        with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
            existing_catalog = json.load(f)

        existing_ids = {x.get("id") for x in existing_catalog}
        added_count = 0

        for item in new_items:
            if item["id"] not in existing_ids:
                existing_catalog.append(item)
                existing_ids.add(item["id"])
                added_count += 1

        # Save back
        with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(existing_catalog, f, ensure_ascii=False, indent=2)

        # Update JS
        if os.path.exists(BUNDLED_JS):
            with open(BUNDLED_JS, 'r', encoding='utf-8') as f:
                js_content = f.read()

            match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', js_content, re.DOTALL)
            if match:
                prefix = match.group(1)
                suffix = match.group(3)
                new_js = prefix + json.dumps(existing_catalog, ensure_ascii=False) + ";" + suffix
                with open(BUNDLED_JS, 'w', encoding='utf-8') as f:
                    f.write(new_js)

        # Update DB
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for item in new_items:
                cursor.execute("""
                    INSERT OR IGNORE INTO vod_media (id, title, category, content_type, poster, backdrop, year)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (item["id"], item["title"], item["category"], item["content_type"], item["poster"], item["backdrop"], item["year"]))
            conn.commit()
            conn.close()

        print(f"[*] M3U Import Complete! Successfully injected {added_count} new VOD items.")

if __name__ == "__main__":
    # Example usage: M3UBulkImporter.import_and_inject("sample_movies.m3u")
    pass
