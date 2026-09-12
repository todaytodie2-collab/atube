# -*- coding: utf-8 -*-
"""
A TuBe Image Hash Deduplicator & Procedural SVG Fallback Engine
1. Calculates MD5 hash of poster images to detect and eliminate duplicate posters across different movies.
2. Generates stunning, unique SVG gradient fallback cards for rare or duplicate-blocked movies.
"""

import hashlib
import urllib.request
import os
import json
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

class ImageHashDeduplicator:
    _seen_hashes = set()

    @staticmethod
    def compute_image_hash(url: str) -> str:
        if not url or url.startswith("data:image") or url.startswith("assets/"):
            return hashlib.md5(str(url).encode('utf-8')).hexdigest()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                content = resp.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return hashlib.md5(str(url).encode('utf-8')).hexdigest()

    @staticmethod
    def generate_procedural_svg_card(title: str, year: str, category: str) -> str:
        safe_t = re.sub(r'[^\w\s\u0600-\u06FF]', '', title).strip()
        safe_cat = category.replace('"', '').replace("'", "")
        safe_year = str(year or "2026")

        # Unique gradient colors based on title length
        h = int(hashlib.md5(safe_t.encode('utf-8')).hexdigest(), 16)
        c1 = f"#{h & 0xFFFFFF:06x}"
        c2 = f"#{(h >> 8) & 0xFFFFFF:06x}"

        svg = f'''data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="500" height="750" viewBox="0 0 500 750"><defs><linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="{c1}"/><stop offset="50%" stop-color="%23081018"/><stop offset="100%" stop-color="{c2}"/></linearGradient><radialGradient id="glow" cx="50%" cy="30%" r="60%"><stop offset="0%" stop-color="%2300e5ff" stop-opacity="0.25"/><stop offset="100%" stop-color="%2300e5ff" stop-opacity="0"/></radialGradient></defs><rect width="100%" height="100%" fill="url(%23bg)"/><rect width="100%" height="100%" fill="url(%23glow)"/><circle cx="250" cy="220" r="90" fill="%23ffffff" fill-opacity="0.05" stroke="%2300e5ff" stroke-opacity="0.3" stroke-width="2"/><text x="50%" y="230" font-family="Arial, sans-serif" font-size="48" font-weight="bold" fill="%2300e5ff" text-anchor="middle">A TuBe</text><text x="50%" y="380" font-family="Arial, sans-serif" font-size="32" font-weight="900" fill="%23ffffff" text-anchor="middle" width="440">{safe_t[:35]}</text><text x="50%" y="440" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="%2300cbff" text-anchor="middle">{safe_cat} • {safe_year}</text></svg>'''
        return svg

    @classmethod
    def process_item(cls, item: dict) -> dict:
        poster = item.get("poster", "")
        title = item.get("title", "Unknown")
        year = item.get("year", "2026")
        cat = item.get("category", "cinema")

        img_hash = cls.compute_image_hash(poster)

        if img_hash in cls._seen_hashes and not poster.startswith("data:image"):
            # Duplicate image detected! Replace with unique procedural SVG card
            unique_svg = cls.generate_procedural_svg_card(title, year, cat)
            item["poster"] = unique_svg
            item["backdrop"] = unique_svg
            print(f"[ImageHashDeduplicator] Duplicate poster detected for '{title}'; replaced with unique SVG card.")
        else:
            cls._seen_hashes.add(img_hash)

        return item
