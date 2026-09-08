# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8'
}

def inspect_portal(name, url):
    print(f"\n{'='*20} {name} {'='*20}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=8.0) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            print(f"Status: {resp.status} | HTML Size: {len(html)} chars")
            
            # Find navigation links and categories
            links = re.findall(r'href=["\']([^"\']+)["\']', html)
            cat_links = [l for l in set(links) if any(k in l.lower() for k in ['category', 'movies', 'series', 'aflam', 'mosalsalat', 'section', 'genre', 'anime', 'turkish'])]
            print(f"Found {len(cat_links)} potential category links. Sample:")
            for l in sorted(cat_links)[:6]:
                print(f"  - {l}")

            # Find media card items / watch links
            watch_links = [l for l in set(links) if any(k in l.lower() for k in ['watch', 'play', 'episode', 'film', 'movie', 'series', 'video', 'post', 'view'])]
            print(f"Found {len(watch_links)} watch/item links. Sample:")
            for l in sorted(watch_links)[:6]:
                print(f"  - {l}")
    except Exception as e:
        print(f"Error inspecting {name}: {e}")

inspect_portal("EgyDead", "https://egydead.top/")
inspect_portal("FaselHD", "https://www.faselhd.club/")
inspect_portal("Akwam", "https://akwam.to/")
inspect_portal("WeCima", "https://wecima.show/")
