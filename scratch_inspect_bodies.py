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

for name, url in [("EgyDead", "https://egydead.top/"), ("Akwam", "https://akwam.to/"), ("WeCima", "https://wecima.show/")]:
    print(f"\n--- {name} ---")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=7.0) as resp:
            text = resp.read().decode('utf-8', errors='ignore')
            print(f"Final URL: {resp.geturl()}")
            print(text[:500])
    except Exception as e:
        print(f"Error: {e}")
