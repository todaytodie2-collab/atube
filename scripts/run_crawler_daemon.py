# -*- coding: utf-8 -*-
"""
A TuBe - Run Universal Crawler Daemon
Can be invoked manually or scheduled via Windows Task Scheduler / Cron
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from universal_crawler_daemon import UniversalCrawlerDaemon

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="A TuBe Periodic Stream Crawler")
    parser.add_argument("--limit", type=int, default=30, help="Max items to process in this run")
    parser.add_argument("--force", action="store_true", help="Force re-harvesting")
    args = parser.parse_args()

    print(f"=== A TuBe Universal Stream Crawler ===")
    print(f"Checking catalog and database for unlinked media...")
    UniversalCrawlerDaemon.crawl_all(max_items=args.limit, force=args.force)
    stats = UniversalCrawlerDaemon.get_stats()
    print(f"Crawler finished. Processed: {stats['total_scanned']}, Streams added/verified: {stats['successful_extractions']}")
