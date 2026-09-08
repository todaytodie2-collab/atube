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

for name, u in [("EgyDead CA", "https://egydead.ca/"), ("Akwam SS", "https://akwam.ss/"), ("Fasel-HD CO", "https://www.fasel-hd.co/")]:
    try:
        req = urllib.request.Request(u, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=6.0) as resp:
            text = resp.read(2048).decode('utf-8', errors='ignore')
            title = re.search(r'<title>([^<]+)</title>', text, re.IGNORECASE)
            t_str = title.group(1).strip() if title else "No Title"
            print(f"[OK 200] {name} -> Final: {resp.geturl()} | Title: {t_str}")
    except Exception as e:
        print(f"[FAILED] {name} -> {e}")
