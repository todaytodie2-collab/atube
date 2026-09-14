# -*- coding: utf-8 -*-
"""
A TuBe Cast & Filmography Automation Script
Fetches official cast, actor profiles, photos, character roles, and filmography
from TMDB for all catalog titles, building:
1. Enriched `cast` array on every movie/series in `catalog.json`.
2. Full `vod_cast` table entries in `config/atube_data.sqlite`.
3. Standalone fast inverted index `data/cast_filmography.json`.
4. Updates `js/bundled-data.js` for 100% instant offline TV & Mobile access.
"""

import os
import sys
import json
import sqlite3
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")
DB_PATH = os.path.join(BASE_DIR, "config", "atube_data.sqlite")
FILMOGRAPHY_INDEX_PATH = os.path.join(BASE_DIR, "data", "cast_filmography.json")
BUNDLED_JS_PATH = os.path.join(BASE_DIR, "js", "bundled-data.js")

TMDB_KEY = "4e44d9029b1270a757cddc766a1bcb63"
BASE_URL = "https://api.themoviedb.org/3"

def fetch_json(url, timeout=7):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ATube-UltraHD/2.0 (Android; WebOS; MediaHub)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

def fetch_cast_for_item(item):
    tmdb_id = item.get("tmdb_id")
    c_type = item.get("content_type", "movie")
    media_type = "tv" if c_type in ["series", "anime", "tv_show"] or item.get("is_series") else "movie"

    # If no tmdb_id, search by title
    if not tmdb_id:
        title = item.get("title", "") or item.get("arabic_title", "")
        clean_title = title.replace("انمي ", "").replace("أنمي ", "").strip()
        encoded = urllib.parse.quote(clean_title)
        year_str = f"&year={item.get('year')}" if item.get("year") else ""
        search_url = f"{BASE_URL}/search/{media_type}?api_key={TMDB_KEY}&query={encoded}&language=ar{year_str}"
        search_res = fetch_json(search_url)
        if search_res and search_res.get("results"):
            tmdb_id = search_res["results"][0].get("id")
            item["tmdb_id"] = tmdb_id

    if not tmdb_id:
        return item.get("id"), []

    # Fetch credits (Arabic first, then English fallback for missing photos/names)
    credits_url = f"{BASE_URL}/{media_type}/{tmdb_id}/credits?api_key={TMDB_KEY}&language=ar"
    credits_data = fetch_json(credits_url)
    if not credits_data or not credits_data.get("cast"):
        credits_url_en = f"{BASE_URL}/{media_type}/{tmdb_id}/credits?api_key={TMDB_KEY}&language=en"
        credits_data = fetch_json(credits_url_en)

    if not credits_data or not credits_data.get("cast"):
        return item.get("id"), []

    cast_list = []
    for c in credits_data.get("cast", [])[:8]:  # Top 8 actors
        name = c.get("name") or c.get("original_name") or ""
        char = c.get("character") or "شخصية رئيسية"
        p_path = c.get("profile_path")
        photo = f"https://image.tmdb.org/t/p/w200{p_path}" if p_path else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&q=80"
        person_id = c.get("id")

        cast_list.append({
            "id": person_id,
            "name": name,
            "arabic_name": name,
            "character": char,
            "role": "actor",
            "photo": photo
        })

    return item.get("id"), cast_list

def run():
    print("=" * 70)
    print("      🌟 A TuBe Cast & Star Filmography Extraction Pipeline")
    print("=" * 70)

    if not os.path.exists(CATALOG_PATH):
        print(f"❌ Catalog file not found at: {CATALOG_PATH}")
        return

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"[*] Loaded catalog with {len(catalog)} titles.")
    print("[*] Launching parallel TMDB credits extraction (12 threads)...")

    item_map = {it.get("id"): it for it in catalog}
    results = {}
    total = len(catalog)
    completed = 0

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_cast_for_item, it): it.get("id") for it in catalog}
        for future in as_completed(futures):
            item_id = futures[future]
            completed += 1
            try:
                mid, cast = future.result()
                if cast:
                    results[mid] = cast
                    item_map[mid]["cast"] = cast
            except Exception:
                pass
            if completed % 50 == 0 or completed == total:
                print(f"  -> Progress: {completed}/{total} items processed ({len(results)} with cast)")

    print(f"\n[+] Successfully extracted cast for {len(results)} movies and series!")

    # 1. Update catalog.json
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"[✓] Saved enriched catalog.json ({os.path.getsize(CATALOG_PATH):,} bytes)")

    # 2. Build Inverted Filmography Index (Actor -> List of Works)
    print("\n[*] Building Inverted Star Filmography Index...")
    filmography_index = {}

    for it in catalog:
        m_id = it.get("id")
        title = it.get("title", "")
        arabic_title = it.get("arabic_title", "") or title
        poster = it.get("poster") or it.get("backdrop") or ""
        year = it.get("year", "")
        rating = it.get("rating") or "8.5"
        category = it.get("category", "")
        c_type = it.get("content_type", "movie")

        work_summary = {
            "id": m_id,
            "title": title,
            "arabic_title": arabic_title,
            "poster": poster,
            "year": year,
            "rating": rating,
            "category": category,
            "content_type": c_type
        }

        cast_list = it.get("cast", [])
        for actor in cast_list:
            a_name = actor.get("name", "").strip()
            if not a_name:
                continue
            key = a_name.lower()
            if key not in filmography_index:
                filmography_index[key] = {
                    "id": actor.get("id"),
                    "name": a_name,
                    "arabic_name": actor.get("arabic_name", a_name),
                    "photo": actor.get("photo"),
                    "works": []
                }
            # Check if work already added
            if not any(w["id"] == m_id for w in filmography_index[key]["works"]):
                filmography_index[key]["works"].append({
                    **work_summary,
                    "character": actor.get("character", "")
                })

    os.makedirs(os.path.dirname(FILMOGRAPHY_INDEX_PATH), exist_ok=True)
    with open(FILMOGRAPHY_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(filmography_index, f, ensure_ascii=False, indent=2)
    print(f"[✓] Generated data/cast_filmography.json ({len(filmography_index):,} stars indexed)")

    # 3. Synchronize with SQLite database (vod_cast table)
    print("\n[*] Synchronizing with SQLite config/atube_data.sqlite...")
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vod_cast (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_id TEXT,
                    name TEXT,
                    arabic_name TEXT,
                    role TEXT,
                    character_name TEXT,
                    photo TEXT,
                    order_num INTEGER DEFAULT 0
                )
            """)
            cur.execute("DELETE FROM vod_cast")
            insert_rows = []
            for mid, cast_list in results.items():
                for idx, a in enumerate(cast_list):
                    insert_rows.append((
                        mid,
                        a.get("name", ""),
                        a.get("arabic_name", ""),
                        a.get("role", "actor"),
                        a.get("character", ""),
                        a.get("photo", ""),
                        idx
                    ))
            cur.executemany("""
                INSERT INTO vod_cast (media_id, name, arabic_name, role, character_name, photo, order_num)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, insert_rows)
            conn.commit()
            conn.close()
            print(f"[✓] Inserted {len(insert_rows):,} actor records into SQLite database.")
        except Exception as ex:
            print(f"[-] SQLite note: {ex}")

    # 4. Synchronize js/bundled-data.js
    print("\n[*] Synchronizing js/bundled-data.js for instant offline access...")
    with open(BUNDLED_JS_PATH, "w", encoding="utf-8") as f:
        f.write("/* Auto-generated Bundled Data for Instant Offline Startup */\n")
        f.write("window.BUNDLED_CATALOG = " + json.dumps(catalog, ensure_ascii=False) + ";\n")
        f.write("window.BUNDLED_FILMOGRAPHY = " + json.dumps(filmography_index, ensure_ascii=False) + ";\n")
    print(f"[✓] Generated js/bundled-data.js ({os.path.getsize(BUNDLED_JS_PATH):,} bytes)")

    print("\n" + "=" * 70)
    print("      🎉 Star & Cast Filmography Extraction Completed Successfully!")
    print("=" * 70)

if __name__ == "__main__":
    run()
