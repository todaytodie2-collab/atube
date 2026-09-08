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
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8'
}

mirrors_to_test = [
    # EgyDead mirrors
    ("EgyDead .top", "https://egydead.top/"),
    ("EgyDead .live", "https://egydead.live/"),
    ("EgyDead .pro", "https://egydead.pro/"),
    
    # FaselHD mirrors
    ("FaselHD .to", "https://www.faselhd.to/"),
    ("FaselHD .pro", "https://www.faselhd.pro/"),
    ("FaselHD .live", "https://www.faselhd.live/"),
    ("FaselHD .ac", "https://www.faselhd.ac/"),
    ("FaselHD .cc", "https://www.faselhd.cc/"),
    ("FaselHD .online", "https://www.faselhd.online/"),

    # WeCima / MyCima mirrors
    ("MyCima .click", "https://mycima.click/"),
    ("WeCima .click", "https://wecima.click/"),
    ("WeCima .tube", "https://wecima.tube/"),
    ("WeCima .tv", "https://wecima.tv/"),
    ("WeCima .icu", "https://wecima.icu/"),

    # Akwam mirrors / direct
    ("Akwam .cx", "https://akwam.cx/"),
    ("Akwam .cc", "https://akwam.cc/"),
    ("Akwam with tr_uuid", "http://akwam.to/?fp=-7")
]

for name, url in mirrors_to_test:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=5.0) as resp:
            final_url = resp.geturl()
            html = resp.read(2048).decode('utf-8', errors='ignore')
            title = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
            title_text = title.group(1).strip() if title else "No Title"
            print(f"[OK 200] {name} -> Final: {final_url} | Title: {title_text}")
    except Exception as e:
        print(f"[FAILED] {name} -> {e}")
