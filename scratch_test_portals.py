# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8'
}

portals_to_test = [
    # Global Embed Gateways (Work with TMDB / IMDb IDs)
    ("VidSrc XYZ (Global Open API)", "https://vidsrc.xyz/embed/movie?imdb=tt15239678"),
    ("MultiEmbed (Global Open API)", "https://multiembed.mov/?video_id=tt15239678"),
    ("VidLink Pro (Global Open API)", "https://vidlink.pro/movie/tt15239678"),
    ("2Embed (Global Open API)", "https://www.2embed.cc/embed/tt15239678"),
    
    # Arabic Portals
    ("EgyDead", "https://egydead.top/"),
    ("Akwam", "https://akwam.to/"),
    ("FaselHD", "https://www.faselhd.club/"),
    ("Arabseed", "https://a.arabseed.site/"),
    ("WeCima / MyCima", "https://wecima.show/"),
    ("Cima4U", "https://cima4u.skin/"),
    ("CimaClub", "https://cimaclub.skin/")
]

for name, url in portals_to_test:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=6.0) as resp:
            print(f"[REACHABLE {resp.status}] {name} -> URL: {url}")
    except urllib.error.HTTPError as e:
        print(f"[HTTP {e.code}] {name}")
    except Exception as e:
        print(f"[FAILED] {name}: {e}")
