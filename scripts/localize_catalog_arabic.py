# -*- coding: utf-8 -*-
"""
A TuBe Ultra-Fast Multithreaded Arabic Localization Engine
Localizes all remaining English titles and synopses across catalog.json in parallel.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")
DB_PATH = os.path.join(BASE_DIR, "config", "atube_data.sqlite")
BUNDLED_JS = os.path.join(BASE_DIR, "js", "bundled-data.js")
TMDB_KEY = "4e44d9029b1270a757cddc766a1bcb63"

def has_arabic(text):
    if not text:
        return False
    return any('\u0600' <= c <= '\u06FF' for c in str(text))

def translate_gtx(text):
    if not text or not text.strip():
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ar&dt=t&q=" + urllib.parse.quote(text.strip()[:400])
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and data[0]:
                res = "".join([part[0] for part in data[0] if part and part[0]])
                return res.strip()
    except Exception:
        pass
    return text

def get_tmdb_arabic(tmdb_id, content_type="movie"):
    if not tmdb_id:
        return None, None
    media_type = "tv" if content_type in ["series", "anime", "tv_show"] else "movie"
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={TMDB_KEY}&language=ar"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            title = data.get("title") or data.get("name")
            overview = data.get("overview")
            ar_title = title if (title and has_arabic(title)) else None
            ar_overview = overview if (overview and has_arabic(overview)) else None
            return ar_title, ar_overview
    except Exception:
        return None, None

def process_item(item):
    title = item.get("title", "")
    ar_title = item.get("arabic_title", "")
    c_type = item.get("content_type", "movie")
    tmdb_id = item.get("tmdb_id")

    needs_title = (not has_arabic(ar_title)) or (ar_title == title and any(c.isalpha() and ord(c) < 128 for c in title))
    needs_synopsis = (not has_arabic(item.get("synopsis", ""))) and (not has_arabic(item.get("overview", "")))

    if not needs_title and not needs_synopsis:
        return None

    # Step 1: TMDB check
    tmdb_title, tmdb_overview = get_tmdb_arabic(tmdb_id, c_type)

    # Resolve Title
    if needs_title:
        if tmdb_title:
            item["arabic_title"] = tmdb_title
        else:
            clean_t = title
            for y in ["2026", "2025", "2024", "2023", "2022", "2021", "2020"]:
                clean_t = clean_t.replace(y, "")
            tr = translate_gtx(clean_t.strip())
            if tr and has_arabic(tr):
                item["arabic_title"] = tr
            else:
                item["arabic_title"] = title

    # Resolve Synopsis
    if needs_synopsis:
        if tmdb_overview:
            item["synopsis"] = tmdb_overview
            item["overview"] = tmdb_overview
        else:
            orig = item.get("synopsis") or item.get("overview") or ""
            if orig and len(orig) > 5:
                tr_syn = translate_gtx(orig[:400])
                if tr_syn and has_arabic(tr_syn):
                    item["synopsis"] = tr_syn
                    item["overview"] = tr_syn

    return item.get("id")

def run_multithreaded_localization():
    print("[*] Loading catalog.json for parallel localization...")
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"[*] Processing {len(catalog)} items with 12 parallel threads...")
    completed = 0

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(process_item, item): item for item in catalog}
        for future in as_completed(futures):
            res = future.result()
            if res:
                completed += 1
                if completed % 20 == 0:
                    print(f"  [+] Localized {completed} items...")

    print(f"[+] Total items enriched with Arabic metadata: {completed}")

    # Save to catalog.json
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"[+] Successfully saved {len(catalog)} items to catalog.json")

    # Save to bundled-data.js
    with open(BUNDLED_JS, "w", encoding="utf-8") as f:
        f.write("/* Auto-generated Bundled Data for Instant Offline Startup */\n")
        f.write("window.BUNDLED_CATALOG = " + json.dumps(catalog, ensure_ascii=False) + ";\n")
    print("[+] Successfully synchronized js/bundled-data.js")

    # Update SQLite database
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            for item in catalog:
                cur.execute("UPDATE vod_media SET arabic_title = ?, overview = ? WHERE id = ?", (item.get("arabic_title"), item.get("synopsis") or item.get("overview"), item.get("id")))
            conn.commit()
            conn.close()
            print("[+] Updated SQLite database vod_media records.")
        except Exception as e:
            print(f"[-] SQLite note: {e}")

if __name__ == "__main__":
    run_multithreaded_localization()
