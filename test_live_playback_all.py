# -*- coding: utf-8 -*-
"""
A TuBe Live End-to-End Playback and Stream Diagnostics Tester
Simulates real user playback across catalog movies, series, server resolvers, and Google Dorking.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from stream_extractor import DirectStreamExtractor
from google_dork_scraper import GoogleDorkScraper

def test_stream_resolver(url, site_name=""):
    print(f"\n[Test Resolver] Testing Server: {site_name} | URL: {url[:75]}...")
    start_t = time.time()
    res = DirectStreamExtractor.resolve(url)
    elapsed = round((time.time() - start_t) * 1000, 1)
    
    if res.get("success"):
        direct_url = res.get("stream_url", "")
        print(f"  -> SUCCESS ({elapsed}ms)! Extracted Stream: {direct_url[:80]}... (Format: {res.get('format')})")
        
        # Test probing proxy for stream headers
        proxy_url = f"http://localhost:8085/api/stream/proxy?url={urllib.parse.quote(direct_url)}"
        try:
            req = urllib.request.Request(proxy_url, headers={"Range": "bytes=0-1024"})
            with urllib.request.urlopen(req, timeout=8) as proxy_res:
                print(f"  -> Proxy Test: Status {proxy_res.status}, Content-Type: {proxy_res.headers.get('Content-Type')}")
                return True
        except Exception as pe:
            print(f"  -> Proxy Note (Local streaming check): {pe}")
            return True
    else:
        print(f"  -> FALLBACK / NOTE: {res.get('error', 'Requires embed/iframe fallback')}")
        return False

def test_google_dork_scraper(title_en, title_ar="", year=""):
    print(f"\n[Test Live Scraper] Scraping servers for: {title_en} ({title_ar}) [{year}]...")
    start_t = time.time()
    res = GoogleDorkScraper.scrape_servers(title_en, title_ar, year)
    elapsed = round((time.time() - start_t) * 1000, 1)
    
    servers = res.get("servers", [])
    print(f"  -> Result: Found {len(servers)} unique servers in {elapsed}ms.")
    for idx, s in enumerate(servers[:4], 1):
        print(f"     {idx}. {s.get('name')} | Quality: {s.get('quality')} | URL: {s.get('stream_url')[:65]}...")
    return len(servers) > 0

def run_diagnostics():
    print("=" * 70)
    print("       A TuBe Ultra HD - Live Real-User Playback Diagnostics")
    print("=" * 70)
    
    # 1. Test top stream resolvers on actual live hosts
    sample_servers = [
        ("https://hgcloud.to/e/7288k22qybqn", "Hgcloud Cloud Player"),
        ("https://vidmoly.net/embed-htlpgxzx715p.html", "Vidmoly Direct FHD"),
        ("https://mixdrop.top/e/vk7ggd78ao1w8r", "Mixdrop Stream"),
        ("https://vidlink.pro/movie/969681", "VidLink Ultra 4K/FHD")
    ]
    
    for url, site in sample_servers:
        test_stream_resolver(url, site)
        
    # 2. Test Live Google Dorking on Popular Works
    test_titles = [
        ("Spider-Man: Brand New Day", "سبايدرمان", "2026"),
        ("Game of Thrones", "صراع العروش", "2011"),
        ("Top Gun: Maverick", "توب غان مافريك", "2022")
    ]
    
    for t_en, t_ar, y in test_titles:
        test_google_dork_scraper(t_en, t_ar, y)

if __name__ == "__main__":
    run_diagnostics()
