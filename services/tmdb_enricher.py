# -*- coding: utf-8 -*-
"""
A TuBe Official TMDB Data Enricher Engine
Enriches all catalog items with official TMDB posters, backdrops, and genuine movie stills gallery.
"""

import json
import sqlite3
import os
import re
from tmdb_client import TMDBClient

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "config", "atube_data.sqlite")
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

def enrich_catalog_with_tmdb():
    print("[*] Starting Official TMDB API Enrichment...")
    if not os.path.exists(CATALOG_JSON):
        return

    with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    enriched_count = 0

    for item in catalog:
        title = item.get("title", "")
        c_type = item.get("content_type", "movie")
        poster = item.get("poster", "")

        match = TMDBClient.search_media(title, c_type)
        if match:
            tmdb_id = match.get("id")
            media_type = "series" if (match.get("media_type") == "tv" or c_type == "series") else "movie"

            p, b, stills = TMDBClient.get_media_details(tmdb_id, media_type)

            if p:
                item["poster"] = p
                item["backdrop"] = b or p
                if stills:
                    item["stills"] = stills

                if match.get("vote_average"):
                    item["rating"] = f"★ {round(match['vote_average'], 1)} IMDb"
                if match.get("overview") and not item.get("synopsis"):
                    item["synopsis"] = match["overview"]

                enriched_count += 1
                print(f"[TMDB] Enriched '{title}' successfully -> Poster: {p}")

    # Save to catalog.json
    with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    # Save to bundled-data.js
    if os.path.exists(BUNDLED_JS):
        with open(BUNDLED_JS, 'r', encoding='utf-8') as f:
            js_content = f.read()

        match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', js_content, re.DOTALL)
        if match:
            prefix = match.group(1)
            suffix = match.group(3)
            new_js = prefix + json.dumps(catalog, ensure_ascii=False) + ";" + suffix
            with open(BUNDLED_JS, 'w', encoding='utf-8') as f:
                f.write(new_js)

    # Save to SQLite DB
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for item in catalog:
            cursor.execute("UPDATE vod_media SET poster = ?, backdrop = ? WHERE id = ?",
                           (item.get("poster"), item.get("backdrop"), item.get("id")))
        conn.commit()
        conn.close()

    print(f"[*] TMDB Enrichment complete! Successfully enriched {enriched_count} items.")

if __name__ == "__main__":
    enrich_catalog_with_tmdb()
