# -*- coding: utf-8 -*-
"""
A TuBe Master Data & SQLite Repair Engine
Applies:
1. Strict Taxonomic Guard (taxonomy_rules.json + Pre-Ingestion Filter)
2. Image Hash Deduplication (Prevents duplicate posters)
3. Database & JSON Synchronization
"""

import sqlite3
import json
import os
import re
from strict_guard import StrictTaxonomicGuard
from image_hash_deduplicator import ImageHashDeduplicator

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "config", "atube_data.sqlite")
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

def run_master_repair():
    print("[*] Running Master Data & Strict Taxonomy Repair...")
    if not os.path.exists(CATALOG_JSON):
        return

    with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    cleaned_catalog = []
    seen_ids = set()

    for item in catalog:
        item_id = item.get("id", "")
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)

        # 1. Apply Strict Taxonomic Guard
        item = StrictTaxonomicGuard.guard_and_classify(item)

        # 2. Apply Image Hash Deduplication
        item = ImageHashDeduplicator.process_item(item)

        cleaned_catalog.append(item)

    # Save to catalog.json
    with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
        json.dump(cleaned_catalog, f, ensure_ascii=False, indent=2)

    # Save to bundled-data.js
    if os.path.exists(BUNDLED_JS):
        with open(BUNDLED_JS, 'r', encoding='utf-8') as f:
            js_content = f.read()

        match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', js_content, re.DOTALL)
        if match:
            prefix = match.group(1)
            suffix = match.group(3)
            new_js = prefix + json.dumps(cleaned_catalog, ensure_ascii=False) + ";" + suffix
            with open(BUNDLED_JS, 'w', encoding='utf-8') as f:
                f.write(new_js)

    # Sync to SQLite DB
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for item in cleaned_catalog:
            cursor.execute("""
                UPDATE vod_media
                SET category = ?, content_type = ?, poster = ?, backdrop = ?
                WHERE id = ?
            """, (item.get("category"), item.get("content_type"), item.get("poster"), item.get("backdrop"), item.get("id")))
        conn.commit()
        conn.close()

    print("[*] Master Data & Strict Taxonomy Repair completed 100% successfully!")

if __name__ == "__main__":
    run_master_repair()
