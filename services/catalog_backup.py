# -*- coding: utf-8 -*-
"""
A TuBe Automated Catalog Backup & SQLite Index Optimizer Engine
1. Creates timestamped snapshot backups of catalog.json in config/backups/
2. Adds high-performance indexes on SQLite database fields (category, content_type, year)
"""

import json
import sqlite3
import os
import shutil
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "config", "backups")
DB_PATH = os.path.join(PROJECT_ROOT, "config", "atube_data.sqlite")

def run_backup_and_index():
    print("[*] Running Catalog Backup & SQLite Index Optimizer...")

    # 1. Backup catalog.json
    if os.path.exists(CATALOG_JSON):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"catalog_backup_{timestamp}.json")
        shutil.copy(CATALOG_JSON, backup_file)
        print(f"[*] Created snapshot backup at: {backup_file}")

    # 2. Add SQLite Database Indexes for Sub-Millisecond Speed
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vod_category ON vod_media(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vod_content_type ON vod_media(content_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vod_year ON vod_media(year)")
            conn.commit()
            conn.close()
            print("[*] Optimized SQLite database with sub-millisecond query indexes!")
        except Exception as e:
            print(f"[!] SQLite Index warning: {e}")

if __name__ == "__main__":
    run_backup_and_index()
