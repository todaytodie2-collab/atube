# -*- coding: utf-8 -*-
"""
A TuBe - Fix Asad 2026 Mismatch & Enforce Strict Catalog Integrity Guard
Replaces Hany Ramzy (Asad w 4 Kotat 2007) backdrop/stills with authentic Mohamed Ramadan (Asad 2026) imagery.
Updates catalog.json, atube_data.sqlite, and bundled-data.js.
"""

import os
import sys
import json
import sqlite3

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")
DB_PATH = os.path.join(BASE_DIR, "config", "atube_data.sqlite")
BUNDLED_JS_PATH = os.path.join(BASE_DIR, "js", "bundled-data.js")

REAL_ASAD_BACKDROP = "https://image.tmdb.org/t/p/original/bQ4LuUFN3mozUKGewYj4IkLhwL4.jpg"
REAL_ASAD_POSTER = "https://image.tmdb.org/t/p/w500/jsm08DuftiIxPrnIXDm0SMD3m5M.jpg"
REAL_ASAD_STILLS = [
    "https://image.tmdb.org/t/p/w500/bQ4LuUFN3mozUKGewYj4IkLhwL4.jpg",
    "https://image.tmdb.org/t/p/w500/cpuwE1yYj4oNJeWLMr5ijsMf8DG.jpg"
]
REAL_ASAD_SYNOPSIS = "في إطار درامي تاريخي وحركي شيق، تدور أحداث الفيلم خلال ثورة الزنج في العصر العباسي، حيث يقود البطل (أسد) ثورة شعبية ضد الظلم والفساد في تلك الحقبة."
REAL_DIRECTOR = "محمد دياب"

WRONG_BACKDROP_SIGNATURE = "1H4c29pZ2CgbHIXapeEQsbnpstv.jpg"
WRONG_STILL_SIGNATURE = "9zFxy5IK0DlfNG2q1GLn0mZnKFH.jpg"


def fix_catalog_json():
    if not os.path.exists(CATALOG_PATH):
        print("catalog.json not found!")
        return 0

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    fixed = 0
    for item in catalog:
        m_id = str(item.get("id", ""))
        title = str(item.get("title", ""))
        backdrop = str(item.get("backdrop", ""))

        if "اسد" in title and "2026" in (item.get("year", "") + title + m_id):
            item["backdrop"] = REAL_ASAD_BACKDROP
            item["poster"] = REAL_ASAD_POSTER
            item["stills"] = REAL_ASAD_STILLS
            item["synopsis"] = REAL_ASAD_SYNOPSIS
            item["director"] = REAL_DIRECTOR
            item["tmdb_id"] = 1211185
            fixed += 1
        elif WRONG_BACKDROP_SIGNATURE in backdrop and "2026" in str(item.get("year", "")):
            item["backdrop"] = REAL_ASAD_BACKDROP
            item["stills"] = REAL_ASAD_STILLS
            fixed += 1

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"[catalog.json] Successfully corrected {fixed} entries for Asad 2026.")
    return fixed


def fix_sqlite_db():
    if not os.path.exists(DB_PATH):
        print("SQLite DB not found!")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Fix vod_media
    cur.execute("""
        UPDATE vod_media 
        SET backdrop = ?, poster = ?, synopsis = ?, director = ?, tmdb_id = 1211185
        WHERE (id LIKE '%اسد-2026%' OR (title LIKE '%اسد%' AND year = '2026'))
           OR backdrop LIKE ?
    """, (REAL_ASAD_BACKDROP, REAL_ASAD_POSTER, REAL_ASAD_SYNOPSIS, REAL_DIRECTOR, f"%{WRONG_BACKDROP_SIGNATURE}%"))
    rows_media = cur.rowcount

    # 2. Fix vod_stills
    cur.execute("DELETE FROM vod_stills WHERE media_id LIKE '%اسد-2026%' OR photo_url LIKE ? OR photo_url LIKE ?", 
                (f"%{WRONG_BACKDROP_SIGNATURE}%", f"%{WRONG_STILL_SIGNATURE}%"))
    
    # Insert authentic stills
    cur.execute("SELECT id FROM vod_media WHERE id LIKE '%اسد-2026%' OR (title LIKE '%اسد%' AND year = '2026')")
    m_row = cur.fetchone()
    if m_row:
        media_id = m_row[0]
        for still_url in REAL_ASAD_STILLS:
            cur.execute("INSERT INTO vod_stills (media_id, photo_url) VALUES (?, ?)", (media_id, still_url))

    conn.commit()
    conn.close()
    print(f"[SQLite] Successfully updated {rows_media} vod_media rows and refreshed vod_stills.")
    return rows_media


def fix_bundled_data_js():
    if not os.path.exists(BUNDLED_JS_PATH):
        print("bundled-data.js not found!")
        return 0

    with open(BUNDLED_JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    replaced = 0
    if WRONG_BACKDROP_SIGNATURE in content:
        content = content.replace("https://image.tmdb.org/t/p/original/" + WRONG_BACKDROP_SIGNATURE, REAL_ASAD_BACKDROP)
        content = content.replace("https://image.tmdb.org/t/p/w500/" + WRONG_BACKDROP_SIGNATURE, REAL_ASAD_STILLS[0])
        content = content.replace("https://image.tmdb.org/t/p/w500/" + WRONG_STILL_SIGNATURE, REAL_ASAD_STILLS[1])
        replaced += 1

    with open(BUNDLED_JS_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[bundled-data.js] Replaced {replaced} instances of wrong backdrop.")
    return replaced


if __name__ == "__main__":
    print("=== Fixing Asad 2026 Imagery Mismatch ===")
    fix_catalog_json()
    fix_sqlite_db()
    fix_bundled_data_js()
    print("=== Done fixing Asad 2026! ===")
