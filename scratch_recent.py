import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json

with open("catalog.json", "r", encoding="utf-8") as f:
    items = json.load(f)

for item in items:
    cat = item.get('category')
    title = item.get('title')
    servers_count = len(item.get('servers', []))
    print(f"[{cat}] {title} -> {servers_count} servers")

