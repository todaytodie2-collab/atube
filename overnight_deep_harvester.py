# -*- coding: utf-8 -*-
"""
A TuBe Autonomous Overnight Harvester & Completer Daemon
Runs continuously in background, cycling every 60 seconds:
- Crawls new releases from FaselHD and Cimawbas
- Ingests missing episodes for all series
- Updates catalog.json and atube_data.sqlite
"""

import os
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from catalog_sync import ContentIngestEngine, ContinuousSyncEngine
from vod_db import VODDatabase

def main():
    print("=====================================================", flush=True)
    print("   A TuBe Autonomous Overnight Harvester Started", flush=True)
    print("=====================================================", flush=True)
    
    cycle_count = 0
    while True:
        cycle_count += 1
        print(f"\n[Overnight Harvester] === Cycle #{cycle_count} starting at {time.strftime('%Y-%m-%d %H:%M:%S')} ===", flush=True)
        
        try:
            # 1. Multi-Portal Harvester
            print("[Overnight Harvester] Scanning multi-portal releases...", flush=True)
            results = ContentIngestEngine.harvest_multi_portal(items_per_portal=6)
            print(f"[Overnight Harvester] Multi-portal results: {results}", flush=True)
        except Exception as e:
            print(f"[Overnight Harvester] Portal scan note: {e}", flush=True)

        try:
            # 2. Continuous real-time cycle & Episode Completer
            print("[Overnight Harvester] Checking missing episodes & live feeds...", flush=True)
            ContinuousSyncEngine.run_sync_cycle()
        except Exception as e:
            print(f"[Overnight Harvester] Sync cycle note: {e}", flush=True)

        print(f"[Overnight Harvester] Cycle #{cycle_count} done. Sleeping 60s until next cycle...", flush=True)
        time.sleep(60)

if __name__ == "__main__":
    main()
