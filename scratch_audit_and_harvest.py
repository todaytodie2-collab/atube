# -*- coding: utf-8 -*-
import sys
import os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import urllib.request
import urllib.parse
import ssl
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from stream_validator import StreamHealthValidator
from vod_db import VODDatabase
from catalog_sync import ContentIngestEngine

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': '*/*'
}

DEAD_KEYWORDS = [
    'file was deleted', 'file has been removed', 'video not found',
    'deleted by the owner', 'video has expired', 'copyright infringement',
    'no longer available', 'error 404', '404 not found'
]

def probe_server(server_dict, timeout=4.5):
    url = server_dict.get("stream_url", "").strip()
    if not url or not StreamHealthValidator.is_free_server(url):
        return False, "Not free or invalid URL"
    
    # Probing URL
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            if resp.status not in (200, 206):
                return False, f"HTTP {resp.status}"
            # Read first 16KB to check for dead notices
            data = resp.read(16384).decode('utf-8', errors='ignore').lower()
            for kw in DEAD_KEYWORDS:
                if kw in data:
                    return False, f"Dead notice: {kw}"
            return True, "200 OK"
    except urllib.error.HTTPError as e:
        return False, f"HTTPError {e.code}"
    except Exception as e:
        return False, f"Connection failure: {e}"

def clean_and_audit_catalog():
    print("[1/3] Auditing existing catalog.json...")
    cat_path = os.path.join(BASE_DIR, "catalog.json")
    if not os.path.exists(cat_path):
        return []
    with open(cat_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    cleaned = []
    total_servers = sum(len(x.get("servers", [])) for x in catalog)
    print(f"  Checking {len(catalog)} titles ({total_servers} servers)...", flush=True)

    with ThreadPoolExecutor(max_workers=10) as executor:
        for item in catalog:
            servers = item.get("servers", [])
            future_to_server = {executor.submit(probe_server, s): s for s in servers}
            alive_servers = []
            for future in as_completed(future_to_server):
                s = future_to_server[future]
                is_ok, reason = future.result()
                if is_ok:
                    alive_servers.append(s)
                else:
                    pass
            
            if len(alive_servers) > 0:
                item["servers"] = alive_servers
                cleaned.append(item)
            else:
                print(f"  [REMOVED ZERO-SERVER ITEM] '{item.get('title')}'")

    with open(cat_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print(f"  Audit complete: {len(cleaned)} items retained with 100% active servers.\n", flush=True)
    return cleaned

def harvest_deep_and_validate(items_per_category=6, pages_per_category=2):
    print(f"[2/3] Deep Harvesting & Validating New Titles (items_per_cat={items_per_category}, pages={pages_per_category})...", flush=True)
    sections = [
        ("https://iegybest.cimawbas.tv/category.php?cat=aflam-arbe", "arabic", "أفلام عربية"),
        ("https://iegybest.cimawbas.tv/category.php?cat=mslslat-arbe", "arabic_series", "مسلسلات عربية"),
        ("https://iegybest.cimawbas.tv/category.php?cat=mslslat-trkeh", "turkish", "مسلسلات تركية"),
        ("https://iegybest.cimawbas.tv/category.php?cat=mslslat-anme", "anime", "أنمي وكارتون"),
        ("https://iegybest.cimawbas.tv/category.php?cat=aflam-hnde", "indian", "أفلام هندية"),
        ("https://iegybest.cimawbas.tv/category.php?cat=aflam-2025", "foreign", "أفلام أجنبية 2025"),
        ("https://iegybest.cimawbas.tv/category.php?cat=aflam-2024", "foreign", "أفلام أجنبية 2024")
    ]

    total_added = 0
    for url, cat_code, cat_ar in sections:
        print(f"\n--> Harvesting category: {cat_ar} ({cat_code})...", flush=True)
        try:
            results = ContentIngestEngine.crawl_category(
                category_url=url,
                category_name=cat_code,
                max_items=items_per_category,
                max_pages=pages_per_category
            )
            print(f"  [OK] {cat_ar}: Ingested & Verified {len(results)} titles.")
            total_added += len(results)
        except Exception as e:
            print(f"  [ERROR] Failed to crawl {cat_ar}: {e}")

    return total_added

def print_final_summary():
    cat_path = os.path.join(BASE_DIR, "catalog.json")
    with open(cat_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    by_cat = {}
    total_servers = 0
    for item in catalog:
        c = item.get("category", "other")
        by_cat[c] = by_cat.get(c, 0) + 1
        total_servers += len(item.get("servers", []))

    print("\n" + "="*50)
    print("      FINAL VERIFIED CATALOG SUMMARY")
    print("="*50)
    print(f"Total Titles in Catalog: {len(catalog)}")
    print(f"Total Active Free Servers: {total_servers}")
    print("\nBreakdown by Category:")
    cat_names = {
        "foreign": "الأفلام الأجنبية (Foreign Movies)",
        "arabic": "الأفلام العربية (Arabic Movies)",
        "arabic_series": "المسلسلات العربية (Arabic Series)",
        "turkish": "المسلسلات التركية (Turkish Series)",
        "anime": "الأنمي والكارتون (Anime)",
        "indian": "السينما الهندية (Indian Movies)"
    }
    for c, count in by_cat.items():
        print(f"  - {cat_names.get(c, c)}: {count} عمل")
    print("="*50, flush=True)

if __name__ == "__main__":
    clean_and_audit_catalog()
    # Deep harvest Arabic Movies and Arabic Series with fixed unique IDs
    sections = [
        ("https://iegybest.cimawbas.tv/category.php?cat=aflam-arbe", "arabic", "أفلام عربية"),
        ("https://iegybest.cimawbas.tv/category.php?cat=mslslat-arbe", "arabic_series", "مسلسلات عربية"),
        ("https://iegybest.cimawbas.tv/category.php?cat=mslslat-trkeh", "turkish", "مسلسلات تركية")
    ]
    for url, cat_code, cat_ar in sections:
        try:
            results = ContentIngestEngine.crawl_category(url, cat_code, max_items=8, max_pages=3)
            print(f"  [OK] {cat_ar}: Ingested & Verified {len(results)} titles.")
        except Exception as e:
            print(f"  [ERROR] {e}")
    print_final_summary()
