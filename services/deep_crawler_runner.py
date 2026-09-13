# -*- coding: utf-8 -*-
"""
A TuBe Deep Multi-Threaded Pagination Crawler
Expands the portal crawlers to extract thousands of movies and series from page 1 to 50
in parallel across multiple sites.
"""

import os
import json
import time
from concurrent.futures import ThreadPoolExecutor
from portal_crawlers import FaselHDAdapter, EgyDeadAdapter, TopCinemaAdapter

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")

def deep_crawl_site(adapter_class, site_name, section, start_page, end_page):
    print(f"[*] Starting deep crawl on {site_name} | Section: {section} | Pages: {start_page} to {end_page}")
    results = []

    try:
        if hasattr(adapter_class, "crawl_section"):
            items = adapter_class.crawl_section(section_key=section, min_page=start_page, max_page=end_page, max_workers=10)
            results.extend(items)
            print(f"[*] {site_name} ({section}) yielded {len(items)} verified items.")
    except Exception as e:
        print(f"[!] Error crawling {site_name}: {e}")

    return results

def run_deep_harvest():
    print("==================================================")
    print("   A TuBe Deep Multi-Threaded Crawler Engine")
    print("==================================================")

    tasks = [
        (FaselHDAdapter, "FaselHD", "movies", 1, 5),
        (FaselHDAdapter, "FaselHD", "foreign_series", 1, 3),
        (FaselHDAdapter, "FaselHD", "indian", 1, 3),
        (EgyDeadAdapter, "EgyDead", "movies", 1, 5),
        (EgyDeadAdapter, "EgyDead", "series", 1, 3),
        (TopCinemaAdapter, "TopCinema", "movies", 1, 3)
    ]

    all_harvested = []

    # Run heavy site crawling sequentially to avoid IP blocks,
    # but the internal `crawl_section` uses multithreading for video servers
    for task in tasks:
        adapter, name, sec, p_start, p_end = task
        items = deep_crawl_site(adapter, name, sec, p_start, p_end)
        all_harvested.extend(items)
        time.sleep(2) # Breath between portals

    print(f"\n[*] Total Deep Harvest Extracted: {len(all_harvested)} items.")

    if all_harvested:
        print("[*] Injecting into Master Catalog via Aggregator...")
        from stream_aggregator import SmartStreamAggregator

        with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
            current_catalog = json.load(f)

        combined_catalog = current_catalog + all_harvested
        final_catalog = SmartStreamAggregator.aggregate_catalog(combined_catalog)

        with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(final_catalog, f, ensure_ascii=False, indent=2)

        # Optional: Sync to DB and JS via master repair
        import subprocess
        subprocess.run(["python", os.path.join(os.path.dirname(__file__), "master_data_repair.py")])

        print(f"[*] Deep Harvest Complete! Catalog grew to {len(final_catalog)} items.")

if __name__ == "__main__":
    # Note: Running this will actually ping servers and download data
    # run_deep_harvest()
    print("Deep Crawler is ready. Call run_deep_harvest() to execute.")
