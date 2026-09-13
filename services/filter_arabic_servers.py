# -*- coding: utf-8 -*-
"""
A TuBe Smart Arabic vs Foreign Server Filter
Ensures Arabic movies & series (like صقر وكناريا) DO NOT use foreign TMDB-based fallback servers (VidLink / MultiEmbed).
Forces Arabic media to rely exclusively on native Arabic servers (EgyDead, FaselHD, Akwam, TopCinema, Hgcloud, Mixdrop).
"""

import json
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

def filter_arabic_servers():
    print("[*] Filtering Arabic servers to prevent foreign movie mismatches...")
    if not os.path.exists(CATALOG_JSON):
        return

    with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    cleaned_count = 0

    for item in catalog:
        cat = item.get("category", "")
        title = item.get("title", "") + " " + item.get("arabic_title", "")
        lang = item.get("language", "")

        is_arabic = (cat in ["arabic", "arabic_series", "plays"] or
                     "عربي" in cat or "عربية" in lang or "العربية" in lang or
                     any(kw in title for kw in ["صقر وكناريا", "أفلام عربي", "مسلسلات عربي", "مسرحية"]))

        if is_arabic and "servers" in item:
            filtered_servers = []
            for srv in item.get("servers", []):
                srv_url = str(srv.get("url") or srv.get("stream_url") or "").lower()
                srv_name = str(srv.get("name") or "").lower()

                # Remove VidLink, VidSrc, MultiEmbed from Arabic media
                if any(f_kw in srv_url or f_kw in srv_name for f_kw in ["vidlink", "vidsrc", "multiembed"]):
                    continue
                filtered_servers.append(srv)

            if len(filtered_servers) < len(item["servers"]):
                item["servers"] = filtered_servers
                cleaned_count += 1
                print(f"[ArabicFilter] Removed foreign TMDB fallbacks from Arabic item: '{item.get('title')}'")

    with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(',', ':'))

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

    print(f"[*] Arabic Server Filter completed! Cleaned {cleaned_count} Arabic items.")

if __name__ == "__main__":
    filter_arabic_servers()
