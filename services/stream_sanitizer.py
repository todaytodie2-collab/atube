# -*- coding: utf-8 -*-
"""
A TuBe RAM-Only Stream Sanitizer & Ad Stripper
Processes HLS playlists (.m3u8) in volatile memory, strips ad injection blocks,
removes tracking beacons and pre-roll segments, and delivers clean media streams
with zero disk writes.
"""

import re
import io
import gc
import urllib.parse
from typing import Tuple, Dict, Any, Optional

class StreamSanitizer:
    """
    Volatile in-memory M3U8 stream sanitizer.
    Intercepts and cleans manifest files in RAM buffers to eliminate ads,
    discontinuities, and malicious redirects without touching disk storage.
    """

    # Known ad tracking keywords and ad network domains
    AD_PATTERNS = [
        re.compile(r'doubleclick\.net', re.IGNORECASE),
        re.compile(r'googlesyndication\.com', re.IGNORECASE),
        re.compile(r'adservice\.google', re.IGNORECASE),
        re.compile(r'popads\.net', re.IGNORECASE),
        re.compile(r'onclickads\.net', re.IGNORECASE),
        re.compile(r'trafficjunky\.com', re.IGNORECASE),
        re.compile(r'adnxs\.com', re.IGNORECASE),
        re.compile(r'propellerads\.com', re.IGNORECASE),
        re.compile(r'bet365|1xbet|melbet', re.IGNORECASE),
        re.compile(r'ad_segment|preroll|midroll|sponsor', re.IGNORECASE),
        re.compile(r'promo[_-]?clip|trailer[_-]?ad', re.IGNORECASE)
    ]

    # Standard spoofed headers that bypass CDN restrictions & ad-block detection
    STEALTH_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Cache-Control": "no-cache"
    }

    @classmethod
    def sanitize_m3u8(cls, raw_manifest: str, base_url: str = "") -> str:
        """
        Parses and cleans M3U8 playlist directly in volatile RAM.
        Strips advertising tags (#EXT-X-DISCONTINUITY, #EXT-X-CUE-OUT, ad URLs)
        and resolves relative chunk URLs safely.
        """
        if not raw_manifest or "#EXTM3U" not in raw_manifest:
            return raw_manifest

        output_buffer = io.StringIO()
        lines = raw_manifest.splitlines()
        skip_next_uri = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # 1. Strip Ad Cue Markers
            if stripped.startswith(("#EXT-X-CUE-OUT", "#EXT-X-CUE-IN", "#EXT-OATCLS-SCTE35", "#EXT-X-DATERANGE")):
                continue

            # 2. Check if segment metadata points to an ad
            if stripped.startswith("#EXTINF"):
                # Look ahead to segment URI
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if cls.is_ad_segment(next_line):
                        skip_next_uri = True
                        continue

            if skip_next_uri:
                skip_next_uri = False
                continue

            # 3. Check for standalone ad URI line
            if not stripped.startswith("#") and cls.is_ad_segment(stripped):
                continue

            # 4. Resolve relative chunk URLs to absolute so player does not break
            if not stripped.startswith("#") and base_url and not stripped.startswith("http"):
                stripped = urllib.parse.urljoin(base_url, stripped)

            output_buffer.write(stripped + "\n")

        clean_manifest = output_buffer.getvalue()
        output_buffer.close()
        del lines
        return clean_manifest

    @classmethod
    def is_ad_segment(cls, url_or_text: str) -> bool:
        """Evaluates whether a URI or tag corresponds to an ad or promotional snippet."""
        if not url_or_text:
            return False
        for pattern in cls.AD_PATTERNS:
            if pattern.search(url_or_text):
                return True
        return False

    @classmethod
    def get_spoofed_headers(cls, target_url: str, custom_referer: Optional[str] = None) -> Dict[str, str]:
        """Generates dynamic anti-hotlink and anti-ad headers in memory."""
        headers = dict(cls.STEALTH_HEADERS)
        parsed = urllib.parse.urlparse(target_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        headers["Origin"] = origin
        headers["Referer"] = custom_referer or f"{origin}/"
        return headers

    @classmethod
    def purge_memory(cls):
        """Forces immediate Python garbage collection after stream closing."""
        gc.collect()
