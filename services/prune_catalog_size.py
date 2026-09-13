# -*- coding: utf-8 -*-
"""
A TuBe Catalog Size Optimizer
Compresses and prunes catalog.json and js/bundled-data.js to keep file size
well under GitHub's 100MB limit (~20-25MB max).
"""

import json
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

def optimize_catalog_size():
    print("[*] Optimizing catalog size for GitHub compliance...")
    if not os.path.exists(CATALOG_JSON):
        return

    with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    # Prune empty or redundant fields from episodes
    for item in catalog:
        if item.get("content_type") == "series" and "seasons" in item:
            for s in item.get("seasons", []):
                # Keep top 30 episodes per season to avoid huge file bloat
                eps = s.get("episodes", [])
                if len(eps) > 30:
                    s["episodes"] = eps[:30]
                for ep in s.get("episodes", []):
                    # Prune unused empty keys
                    if not ep.get("thumbnail"): ep.pop("thumbnail", None)
                    if not ep.get("servers"): ep.pop("servers", None)

    # Save minified catalog.json
    with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(',', ':'))

    print(f"[*] Optimized catalog.json size: {os.path.getsize(CATALOG_JSON) / (1024*1024):.2f} MB")

    # Save minified bundled-data.js
    if os.path.exists(BUNDLED_JS):
        with open(BUNDLED_JS, 'r', encoding='utf-8') as f:
            js_content = f.read()

        match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', js_content, re.DOTALL)
        if match:
            prefix = match.group(1)
            suffix = match.group(3)
            new_js = prefix + json.dumps(catalog, ensure_ascii=False, separators=(',', ':')) + ";" + suffix
            with open(BUNDLED_JS, 'w', encoding='utf-8') as f:
                f.write(new_js)
        print(f"[*] Optimized bundled-data.js size: {os.path.getsize(BUNDLED_JS) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    optimize_catalog_size()
