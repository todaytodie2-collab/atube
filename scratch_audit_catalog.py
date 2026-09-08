# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': '*/*'
}

DEAD_KEYWORDS = [
    'file was deleted', 'file has been removed', 'video not found',
    'deleted by the owner', 'video has expired', 'copyright infringement',
    'no longer available', 'error 404', '404 not found'
]

def check_url(url, timeout=5.0):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            if resp.status not in [200, 206]:
                return False, f"HTTP {resp.status}"
            content = resp.read(32768).decode('utf-8', errors='ignore').lower()
            for kw in DEAD_KEYWORDS:
                if kw in content:
                    return False, f"Dead content: {kw}"
            return True, "200 OK"
    except urllib.error.HTTPError as e:
        return False, f"HTTPError {e.code}"
    except Exception as e:
        return False, f"Exception: {e}"

with open("catalog.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

print(f"Auditing current catalog: {len(catalog)} items...")
clean_catalog = []
total_servers_checked = 0
live_servers = 0
dead_servers = 0

for item in catalog:
    title = item.get("title", "Untitled")
    valid_servers = []
    for s in item.get("servers", []):
        total_servers_checked += 1
        s_url = s.get("stream_url", "")
        ok, reason = check_url(s_url)
        if ok:
            valid_servers.append(s)
            live_servers += 1
        else:
            dead_servers += 1
            print(f"  [DEAD SERVER REMOVED] {title} -> {s.get('name')}: {reason}")
    
    if len(valid_servers) > 0:
        item["servers"] = valid_servers
        clean_catalog.append(item)
    else:
        print(f"  [DEAD ITEM REMOVED] {title} had 0 working servers.")

print(f"\nAudit Results:")
print(f"Original items: {len(catalog)}")
print(f"Clean items with verified working servers: {len(clean_catalog)}")
print(f"Servers checked: {total_servers_checked} | Live: {live_servers} | Dead removed: {dead_servers}")

with open("catalog.json", "w", encoding="utf-8") as f:
    json.dump(clean_catalog, f, ensure_ascii=False, indent=2)
print("Updated catalog.json with 100% verified working servers.")
