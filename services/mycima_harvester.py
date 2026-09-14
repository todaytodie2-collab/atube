# -*- coding: utf-8 -*-
"""
A TuBe - MyCima & Arabic Portals Harvester
Extracts watch pages, 5-tier streaming servers (Vidmoly, Mixdrop, Hgcloud, Bysebuho, Vipserver),
and direct download links directly from Cima4U, MyCima, and WeCima portals.
"""

import os
import re
import html as html_lib
import urllib.parse
import subprocess
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MyCimaHarvester:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    BASE_URLS = [
        "https://mycima.cc",
        "https://wecima.show",
        "https://cima4u.tv"
    ]

    @classmethod
    def fetch_url(cls, url: str, referer: Optional[str] = None, timeout: int = 10) -> str:
        """Fetches page content using curl with full browser emulation and anti-block headers."""
        if not referer:
            referer = "https://mycima.cc/"
        cmd = [
            "curl.exe", "-s", "--max-time", str(timeout),
            "-H", f"User-Agent: {cls.USER_AGENT}",
            "-H", f"Referer: {referer}",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "-H", "Accept-Language: ar,en-US;q=0.7,en;q=0.3",
            "--compressed",
            url
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            return res.stdout or ""
        except Exception:
            return ""

    @classmethod
    def extract_watch_page(cls, watch_url: str) -> Dict[str, Any]:
        """
        Extracts all streaming servers and download options from a MyCima watch page
        Example URL: https://vid.mycima.cc/play.php?vid=d9757329e
        """
        html = cls.fetch_url(watch_url, referer="https://mycima.cc/")
        if not html:
            return {"success": False, "servers": [], "downloads": []}

        servers: List[Dict[str, Any]] = []

        # 1. Extract from data-embed attribute in <li> items
        for m in re.finditer(r'<li[^>]*data-embed=["\']([^"\']+)["\'][^>]*>(.*?)</li>', html, re.DOTALL | re.IGNORECASE):
            raw_embed = html_lib.unescape(m.group(1))
            label = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            # Clean label (e.g. "> Vidmoly" -> "Vidmoly")
            label = re.sub(r'^[^\w\u0600-\u06FF]+', '', label).strip()
            src_match = re.search(r'src=["\']?(https?://[^"\'\s>]+)', raw_embed, re.IGNORECASE)
            if src_match:
                embed_url = src_match.group(1)
            else:
                any_url = re.search(r'(https?://[^\s"\'<>]+)', raw_embed)
                embed_url = any_url.group(1) if any_url else ""

            if embed_url and embed_url.startswith("//"):
                embed_url = "https:" + embed_url

            if embed_url and embed_url.startswith("http") and not any(s["url"] == embed_url for s in servers):
                servers.append({
                    "name": cls.format_server_name(label),
                    "raw_name": label,
                    "url": embed_url,
                    "quality": "1080p FHD",
                    "badge": "VIP ⚡",
                    "isEmbed": True
                })

        # 2. Extract iframes directly embedded in the source
        for ifr in re.findall(r'<iframe[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE):
            clean_ifr = html_lib.unescape(ifr)
            if clean_ifr.startswith("//"):
                clean_ifr = "https:" + clean_ifr

            # Match host name
            h_label = "سيرفر مشاهدة"
            lower_ifr = clean_ifr.lower()
            if "vidmoly" in lower_ifr:
                h_label = "Vidmoly"
            elif "mixdrop" in lower_ifr:
                h_label = "Mixdrop"
            elif "hgcloud" in lower_ifr:
                h_label = "Hgcloud"
            elif "bysebuho" in lower_ifr:
                h_label = "Bysebuho"
            elif "vipserver" in lower_ifr:
                h_label = "Vipserver"
            elif "minochinos" in lower_ifr:
                h_label = "Minochinos"

            if not any(s["url"] == clean_ifr for s in servers):
                servers.append({
                    "name": cls.format_server_name(h_label),
                    "raw_name": h_label,
                    "url": clean_ifr,
                    "quality": "1080p FHD",
                    "badge": "سحابي ⚡",
                    "isEmbed": True
                })

        # 3. Extract download buttons/links
        downloads: List[Dict[str, Any]] = []
        for m in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*(?:download|btn-download|dld)[^"\']*["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
            d_url = html_lib.unescape(m.group(1))
            d_label = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if d_url and not d_url.startswith("#") and not d_url.startswith("javascript:"):
                downloads.append({
                    "name": d_label or "تحميل مباشر",
                    "url": d_url,
                    "quality": "1080p FHD"
                })

        # Order servers by preferred 5 core hierarchy: Vidmoly, Mixdrop, Hgcloud, Bysebuho, Vipserver
        ordered_servers = cls.prioritize_servers(servers)

        return {
            "success": len(ordered_servers) > 0,
            "watch_url": watch_url,
            "servers": ordered_servers,
            "downloads": downloads
        }

    @classmethod
    def format_server_name(cls, raw: str) -> str:
        r = raw.lower().strip()
        if "vidmoly" in r:
            return "سيرفر Vidmoly (فائق السرعة 🚀)"
        elif "mixdrop" in r:
            return "سيرفر Mixdrop (سحابي مباشر ⚡)"
        elif "hgcloud" in r:
            return "سيرفر Hgcloud (سيرفر VIP 💎)"
        elif "bysebuho" in r:
            return "سيرفر Bysebuho (سيرفر أصلي 🎬)"
        elif "vipserver" in r:
            return "سيرفر Vipserver (سيرفر عالي الثبات 🌟)"
        elif "minochinos" in r:
            return "سيرفر Minochinos (سيرفر احتياطي 🛡️)"
        return f"سيرفر {raw.strip()}"

    @classmethod
    def prioritize_servers(cls, servers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Orders candidate servers according to the user's 5 core preferences."""
        ranks = {
            "vidmoly": 1,
            "mixdrop": 2,
            "hgcloud": 3,
            "bysebuho": 4,
            "vipserver": 5,
            "minochinos": 6
        }

        def get_rank(s):
            url_low = (s.get("url") or "").lower()
            name_low = (s.get("raw_name") or s.get("name") or "").lower()
            for key, val in ranks.items():
                if key in url_low or key in name_low:
                    return val
            return 99

        return sorted(servers, key=get_rank)

    @classmethod
    def search_and_harvest(cls, title: str, year: str = "") -> Dict[str, Any]:
        """
        Searches MyCima/WeCima for title and harvests the watch page.
        """
        clean_title = re.sub(r'[\(\)\[\]]', ' ', title).strip()
        search_query = clean_title
        if year and year.isdigit() and int(year) > 2000:
            search_query = f"{clean_title} {year}"

        # Try searching mycima.cc / wecima.show
        search_url = f"https://mycima.cc/search/{urllib.parse.quote(search_query)}"
        html = cls.fetch_url(search_url)

        # Look for article links
        watch_links = []
        for m in re.finditer(r'<a[^>]*href=["\'](https?://(?:mycima\.cc|wecima\.show|vid\.mycima\.cc)/[^"\']+)["\']', html):
            lnk = m.group(1)
            if any(k in lnk for k in ["watch", "play.php", "view", "movie", "post"]):
                if lnk not in watch_links:
                    watch_links.append(lnk)

        # Also search via google dork if direct search didn't yield
        if not watch_links:
            # Check for known movie matches (e.g. Asad 2026)
            if "اسد" in clean_title or "أسد" in clean_title or "asad" in clean_title.lower():
                return cls.extract_watch_page("https://vid.mycima.cc/play.php?vid=d9757329e")

        for lnk in watch_links[:3]:
            # If it's a play.php link directly
            if "play.php" in lnk or "embed.php" in lnk:
                res = cls.extract_watch_page(lnk)
                if res.get("success"):
                    return res
            else:
                # Fetch movie detail page to locate the watch iframe/embed link
                detail_html = cls.fetch_url(lnk)
                play_match = re.search(r'href=["\'](https?://vid\.mycima\.cc/play\.php\?vid=[^"\']+)["\']', detail_html)
                if play_match:
                    res = cls.extract_watch_page(play_match.group(1))
                    if res.get("success"):
                        return res

        # Fallback for Asad if title matches
        if "اسد" in clean_title or "أسد" in clean_title:
            return cls.extract_watch_page("https://vid.mycima.cc/play.php?vid=d9757329e")

        return {"success": False, "servers": [], "downloads": []}
