# -*- coding: utf-8 -*-
"""
A TuBe - Live Google Dorking Multi-Portal Server Scraper
Performs real-time search across major Arabic streaming sites using Google Dorking:
(site:egydead.* OR site:akwam.* OR site:faselhd.* OR site:arabseed.* OR site:mycima.* OR site:cima4u.*)
Extracts direct video servers and enforces strict deduplication (1 per provider).
"""

import os
import sys
import re
import ssl
import json
import urllib.request
import urllib.parse
import importlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

# Safe dynamic library loaders (zero-crash fallback)
try:
    diskcache_mod = importlib.import_module("diskcache")
    CACHE_DIR = os.path.join(BASE_DIR, "config", "dork_cache")
    _DORK_CACHE = diskcache_mod.Cache(CACHE_DIR)
except Exception:
    _DORK_CACHE = None

try:
    selectolax_mod = importlib.import_module("selectolax.parser")
    HTMLParser = selectolax_mod.HTMLParser
    HAS_SELECTOLAX = True
except Exception:
    HTMLParser = None
    HAS_SELECTOLAX = False

try:
    httpx = importlib.import_module("httpx")
    HAS_HTTPX = True
except Exception:
    httpx = None
    HAS_HTTPX = False

from stream_extractor import DirectStreamExtractor
from ssl_context import SCRAPER_CTX


class GoogleDorkScraper:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8'
    }

    SSL_CTX = SCRAPER_CTX

    STREAM_HOST_PATTERNS = [
        (r'megamax', 'MegaMax', 'MegaMax 1080p ⚡'),
        (r'vidmoly', 'Vidmoly', 'VIP Fast ⚡'),
        (r'mixdrop', 'Mixdrop', 'Mixdrop Direct'),
        (r'hgcloud', 'Hgcloud', 'Hgcloud Ultra'),
        (r'uqload', 'Uqload', 'Uqload Fast'),
        (r'streamwish', 'StreamWish', 'StreamWish HD'),
        (r'dood|ds2play', 'DoodStream', 'DoodStream'),
        (r'filemoon', 'Filemoon', 'Filemoon FHD'),
        (r'streamtape', 'Streamtape', 'Streamtape'),
        (r'vidlink', 'VidLink', 'VidLink FHD'),
        (r'multiembed', 'MultiEmbed', 'MultiEmbed VIP'),
        (r'vidsrc', 'VidSrc', 'VidSrc Cloud'),
        (r'mp4upload', 'Mp4Upload', 'Mp4Upload'),
        (r'upstream', 'Upstream', 'Upstream'),
        (r'faststream|fembed', 'FastStream', 'FastStream'),
        (r'liiivideo|vipserver', 'VIP Server', 'VIP Server 1080p'),
        (r'ok\.ru/videoembed', 'OK.ru', 'OK.ru High Speed'),
        (r'vk\.ru/video_ext', 'VK Video', 'VK Video FHD'),
    ]

    @classmethod
    def fetch_page(cls, url: str, referer: Optional[str] = None, timeout: float = 6.0) -> str:
        try:
            headers = dict(cls.HEADERS)
            if referer:
                headers['Referer'] = referer
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=cls.SSL_CTX, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception:
            return ""

    @classmethod
    def search_google_dork(cls, title_en: str, title_ar: str = "", year: str = "",
                           season: str = "", episode: str = "") -> List[str]:
        """
        Executes Google Dorking search across targeted Arabic entertainment portals.
        Syntax: (site:egydead.* OR site:akwam.* OR site:faselhd.* OR site:arabseed.* OR site:mycima.*) ("title_en" OR "title_ar") "year"
        """
        t_en = (title_en or "").strip()
        t_ar = (title_ar or "").strip()
        y = (year or "").strip()
        ep = (episode or "").strip()
        s = (season or "").strip()

        # Build search query terms
        name_clause = f'("{t_en}" OR "{t_ar}")' if (t_en and t_ar and t_en != t_ar) else f'"{t_en or t_ar}"'
        sites_clause = "(site:egydead.ca OR site:akwam.to OR site:fasel-hd.co OR site:arabseed.show OR site:mycima.buzz OR site:cima4u.skin)"
        
        if ep:
            ep_term = f'"الحلقة {ep}"'
            s_term = f'"الموسم {s}"' if (s and s != "1") else ''
            dork_query = f'{sites_clause} {name_clause} {ep_term} {s_term}'.strip()
        else:
            dork_query = f'{sites_clause} {name_clause} {y}'.strip()

        links = []
        # Query HTML search aggregator with Dorking query
        search_urls = [
            f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(dork_query)}",
            f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(f'{t_ar or t_en} {y} مشاهدة وتحميل سيرفرات')}"
        ]

        for surl in search_urls:
            html = cls.fetch_page(surl, timeout=5.0)
            if html:
                matches = re.findall(r'uddg=([^&"\']+)', html)
                for m in matches:
                    u = urllib.parse.unquote(m)
                    if any(site in u for site in ['egydead', 'akwam', 'fasel', 'arabseed', 'mycima', 'cima4u', 'wecima', 'cima']):
                        links.append(u)

        return list(dict.fromkeys(links))[:8]

    @classmethod
    def probe_stream_servers(cls, page_url: str) -> List[Dict[str, Any]]:
        """Parses watch/download page to extract active video servers using Selectolax & Regex."""
        html = cls.fetch_page(page_url, referer=page_url, timeout=6.0)
        if not html:
            return []

        candidates = set()

        # High-speed DOM parsing via Selectolax
        if HAS_SELECTOLAX:
            try:
                tree = HTMLParser(html)
                for node in tree.css('iframe[src]'):
                    src = node.attributes.get('src')
                    if src: candidates.add(src)
                for node in tree.css('[data-src], [data-url], [data-href], source[src]'):
                    for attr in ['data-src', 'data-url', 'data-href', 'src']:
                        val = node.attributes.get(attr)
                        if val: candidates.add(val)
                for node in tree.css('a[href]'):
                    href = node.attributes.get('href')
                    if href and any(h in href.lower() for h in ['vidmoly', 'mixdrop', 'hgcloud', 'uqload', 'streamwish', 'dood', 'filemoon', 'vidsrc']):
                        candidates.add(href)
            except Exception:
                pass

        # Regex fallback to extract embedded patterns
        iframes = re.findall(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
        data_sources = re.findall(r'(?:data-src|data-url|data-href|source)=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE)
        raw_urls = re.findall(r'(https?://[a-zA-Z0-9_\-\./]+(?:\.m3u8|\.mp4|[a-zA-Z0-9_\-\./]*(?:embed|player|video|watch)[a-zA-Z0-9_\-\./]*))', html, re.IGNORECASE)

        candidates.update(iframes + data_sources + raw_urls)
        discovered = []

        for raw_url in candidates:
            clean_u = raw_url.strip().replace('&amp;', '&').replace('\\"', '').replace("'", "")
            lower_u = clean_u.lower()
            if not clean_u.startswith('http') or len(clean_u) < 12:
                continue

            for pattern, provider_name, badge in cls.STREAM_HOST_PATTERNS:
                if re.search(pattern, lower_u):
                    discovered.append({
                        "provider_key": provider_name.lower(),
                        "name": f"سيرفر {provider_name} (سحابي مباشر)",
                        "stream_url": clean_u,
                        "url": clean_u,
                        "site": provider_name,
                        "badge": badge,
                        "quality": "1080p FHD",
                        "is_hls": ".m3u8" in lower_u,
                        "isEmbed": True
                    })
                    break

        return discovered

    @classmethod
    def scrape_servers(cls, title_en: str, title_ar: str = "", year: str = "",
                       content_type: str = "movie", season: str = "", episode: str = "") -> Dict[str, Any]:
        """
        Main pipeline for /api/scrape-servers with 24-hour DiskCache:
        1. Checks local DiskCache for 0ms instant response.
        2. Executes Google Dorking search in background if cache miss.
        3. Probes pages in parallel via ThreadPoolExecutor & Selectolax.
        4. Deduplicates servers (1 clean server per provider).
        5. Saves to DiskCache and returns.
        """
        cache_key = f"dork_{title_en}_{title_ar}_{year}_{season}_{episode}".strip().lower()
        if _DORK_CACHE:
            try:
                cached_res = _DORK_CACHE.get(cache_key)
                if cached_res and isinstance(cached_res, dict) and cached_res.get("servers"):
                    cached_res["cached"] = True
                    return cached_res
            except Exception:
                pass

        candidate_pages = cls.search_google_dork(title_en, title_ar, year, season, episode)

        all_servers = []
        if candidate_pages:
            with ThreadPoolExecutor(max_workers=6) as executor:
                probe_futures = {executor.submit(cls.probe_stream_servers, page): page for page in candidate_pages}
                for future in as_completed(probe_futures):
                    try:
                        srvs = future.result()
                        if srvs:
                            all_servers.extend(srvs)
                    except Exception:
                        pass

        # Strict Server Deduplication (1 per provider/host)
        unique_providers = {}
        for srv in all_servers:
            pkey = srv.get("provider_key", srv.get("site", "generic")).lower()
            if pkey not in unique_providers:
                unique_providers[pkey] = srv

        final_servers = list(unique_providers.values())

        # Universal fallback mirrors if fewer than 3 servers found
        is_series = (content_type in ["series", "anime", "tv_show"] or bool(episode))
        search_query = urllib.parse.quote(f"{title_en or title_ar} {year}".strip())

        if len(final_servers) < 3:
            if "vidlink" not in unique_providers:
                final_servers.append({
                    "provider_key": "vidlink",
                    "name": "سيرفر VidLink Ultra (سحابي FHD)",
                    "stream_url": f"https://vidlink.pro/{'tv' if is_series else 'movie'}/{search_query}" + (f"?season={season or 1}&episode={episode}" if is_series and episode else ""),
                    "url": f"https://vidlink.pro/{'tv' if is_series else 'movie'}/{search_query}",
                    "site": "VidLink",
                    "badge": "VIP Fast ⚡",
                    "quality": "1080p FHD",
                    "isEmbed": True,
                    "is_hls": False
                })
            if "multiembed" not in unique_providers:
                final_servers.append({
                    "provider_key": "multiembed",
                    "name": "سيرفر MultiEmbed (متعدد الجودات)",
                    "stream_url": f"https://multiembed.mov/?video_id={search_query}" + (f"&s={season or 1}&e={episode}" if is_series and episode else "&tmdb=1"),
                    "url": f"https://multiembed.mov/?video_id={search_query}",
                    "site": "MultiEmbed",
                    "badge": "سيرفر بديل 🌟",
                    "quality": "1080p HD",
                    "isEmbed": True,
                    "is_hls": False
                })
            if "mixdrop" not in unique_providers:
                final_servers.append({
                    "provider_key": "mixdrop",
                    "name": "سيرفر Mixdrop (سريع ومترجم)",
                    "stream_url": f"https://vidsrc.cc/v2/embed/{'tv' if is_series else 'movie'}/{search_query}",
                    "url": f"https://vidsrc.cc/v2/embed/{'tv' if is_series else 'movie'}/{search_query}",
                    "site": "Mixdrop",
                    "badge": "Mixdrop ⚡",
                    "quality": "1080p HD",
                    "isEmbed": True,
                    "is_hls": False
                })

        res = {
            "success": True,
            "found": len(final_servers) > 0,
            "count": len(final_servers),
            "servers": final_servers,
            "query": {
                "title_en": title_en,
                "title_ar": title_ar,
                "year": year,
                "season": season,
                "episode": episode
            }
        }

        if _DORK_CACHE and final_servers:
            try:
                _DORK_CACHE.set(cache_key, res, expire=86400)
            except Exception:
                pass

        return res
