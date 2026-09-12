# -*- coding: utf-8 -*-
"""
A TuBe Master Data Cleanup & Consolidation Script
- Deduplicates exact IDs and merges server mirrors.
- Merges fragmented series episodes (e.g. Star Wars Visions Ninth Jedi).
- Fixes numeric IDs (2026-2026 -> saqr-wa-kanaria-2026, 2025-2025 -> al-qasas-2025).
- Enriches missing TMDB metadata and stills.
- Synchronizes catalog.json, bundled-data.js, and atube_data.sqlite atomically.
"""

import json
import os
import re
import sys
import tempfile
import sqlite3
from collections import OrderedDict

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")
DB_PATH = os.path.join(PROJECT_ROOT, "config", "atube_data.sqlite")

sys.path.insert(0, os.path.join(PROJECT_ROOT, "services"))
from tmdb_client import TMDBClient


def run_cleanup():
    print("[*] Starting Master Data Cleanup & Consolidation...")

    if not os.path.exists(CATALOG_JSON):
        print("Error: catalog.json not found.")
        return

    with open(CATALOG_JSON, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"[*] Initial catalog items: {len(catalog)}")

    # 1. Fix numeric-only IDs
    for it in catalog:
        if it.get("id") == "2026-2026":
            it["id"] = "saqr-wa-kanaria-2026"
            it["arabic_title"] = "صقر وكناريا"
        elif it.get("id") == "2025-2025":
            it["id"] = "al-qasas-2025"
            it["arabic_title"] = "القصص"

    # 1b. Consolidate cross-year duplicate movies: Parasomnia and Bandar
    p25 = next((x for x in catalog if x.get("id") == "parasomnia-2025-2025-a9320e8cb"), None)
    p26 = next((x for x in catalog if x.get("id") == "parasomnia-2026-2026"), None)
    if p25 and p26:
        p25_urls = {s.get("stream_url") for s in p25.get("servers", [])}
        for s in p26.get("servers", []):
            if s.get("stream_url") not in p25_urls:
                p25.setdefault("servers", []).append(s)
        catalog = [x for x in catalog if x.get("id") != "parasomnia-2026-2026"]

    b26 = next((x for x in catalog if x.get("id") == "bandar-2026-2026"), None)
    b25 = next((x for x in catalog if x.get("id") == "bandar-2025-2025-368e04df4"), None)
    if b26 and b25:
        b26_urls = {s.get("stream_url") for s in b26.get("servers", [])}
        for s in b25.get("servers", []):
            if s.get("stream_url") not in b26_urls:
                b26.setdefault("servers", []).append(s)
        catalog = [x for x in catalog if x.get("id") != "bandar-2025-2025-368e04df4"]

    # 1c. Correct content_type for standalone items with direct servers but no seasons
    for it in catalog:
        if it.get("content_type") == "series" and it.get("servers") and not it.get("seasons"):
            it["content_type"] = "movie"

    # 2. Consolidate Star Wars Visions Ninth Jedi duplicates
    ninth_jedi_primary_id = "star-wars-visions-presents-the-ninth-jedi-2026"
    ninth_jedi_duplicates = [
        "انمي-star-wars-visions-presents-the-ninth-jedi-2024",
        "انمي-star-wars-visions-presents-the-ninth-jedi-2026"
    ]

    primary_jedi = next((it for it in catalog if it.get("id") == ninth_jedi_primary_id), None)
    if primary_jedi:
        primary_jedi["title"] = "Star Wars Visions: The Ninth Jedi"
        primary_jedi["arabic_title"] = "أنمي حرب النجوم: الرؤى - الجيداي التاسع"
        primary_jedi["content_type"] = "series"
        primary_jedi["category"] = "anime"

    # Filter out the duplicate items
    catalog = [it for it in catalog if it.get("id") not in ninth_jedi_duplicates]

    # 3. Deduplicate exact duplicate IDs and merge servers / episodes
    deduped_map = OrderedDict()
    for item in catalog:
        item_id = item.get("id")
        if not item_id:
            continue

        if item_id not in deduped_map:
            deduped_map[item_id] = item
        else:
            # Merge servers
            existing = deduped_map[item_id]
            existing_srv_urls = {s.get("stream_url") for s in existing.get("servers", []) if s.get("stream_url")}
            for s in item.get("servers", []):
                s_url = s.get("stream_url")
                if s_url and s_url not in existing_srv_urls:
                    existing.setdefault("servers", []).append(s)
                    existing_srv_urls.add(s_url)

            # Merge seasons/episodes
            existing_seasons = existing.setdefault("seasons", [])
            item_seasons = item.get("seasons", [])
            for s_item in item_seasons:
                s_num = s_item.get("season_number", 1)
                matching_s = next((s for s in existing_seasons if s.get("season_number") == s_num), None)
                if not matching_s:
                    existing_seasons.append(s_item)
                else:
                    existing_ep_nums = {ep.get("episode_number") for ep in matching_s.get("episodes", [])}
                    for ep in s_item.get("episodes", []):
                        if ep.get("episode_number") not in existing_ep_nums:
                            matching_s.setdefault("episodes", []).append(ep)
                            existing_ep_nums.add(ep.get("episode_number"))

    consolidated_items = list(deduped_map.values())
    print(f"[*] After deduplication and merge: {len(consolidated_items)} items")

    # 4. Enrich TMDB metadata for items with placeholders or missing info
    print("[*] Running TMDB enricher across items...")
    enriched_count = 0
    for it in consolidated_items:
        poster = it.get("poster", "")
        needs_enrich = (
            not poster
            or "gladiator" in poster.lower()
            or "unsplash.com" in poster.lower()
            or not it.get("stills")
        )
        if needs_enrich:
            orig = poster
            try:
                TMDBClient.enrich_entry(it)
                if it.get("poster") != orig:
                    enriched_count += 1
            except Exception:
                pass

    print(f"[*] Enriched {enriched_count} items with TMDB posters/stills.")

    # 5. Atomic write to catalog.json
    d = os.path.dirname(CATALOG_JSON)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp", prefix="catalog_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(consolidated_items, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CATALOG_JSON)
        print("[*] Successfully saved clean catalog.json")
    except Exception as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise e

    # 6. Update js/bundled-data.js
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
                new_js = m.group(1) + json.dumps(consolidated_items, ensure_ascii=False) + ";" + m.group(3)
                with open(BUNDLED_JS, "w", encoding="utf-8") as f:
                    f.write(new_js)
                print("[*] Successfully synchronized js/bundled-data.js")
        except Exception as e:
            print(f"[!] Note updating bundled-data.js: {e}")

    # 7. Update SQLite config/atube_data.sqlite
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            # Clear old and re-seed clean
            cur.execute("DELETE FROM vod_media")
            cur.execute("DELETE FROM vod_servers")
            cur.execute("DELETE FROM vod_seasons")
            cur.execute("DELETE FROM vod_episodes")
            cur.execute("DELETE FROM vod_stills")
            conn.commit()
            conn.close()

            from vod_db import VODDatabase
            for it in consolidated_items:
                VODDatabase.upsert_media(it)

            print("[*] Successfully synchronized SQLite atube_data.sqlite")
        except Exception as e:
            print(f"[!] Note updating SQLite DB: {e}")

    print("[*] Master Data Cleanup completed successfully!")


if __name__ == "__main__":
    run_cleanup()
