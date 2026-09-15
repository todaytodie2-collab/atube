# -*- coding: utf-8 -*-
"""
A TuBe - High-Performance Dynamic Stream Resolver, TTL Cache & Resilient Extractor Engine
Extracts direct clean video streams (.m3u8 / .mp4) from scraped video hosts and embeds on-demand.
Features:
- In-memory thread-safe TTL cache (1-3 hours) for instantaneous sub-10ms playback
- Resilient Semantic Heuristic Parsing (JWPlayer, VideoJS, base64, tokenized CDN sources)
- Dean Edwards JavaScript Packer unpacker for Mixdrop, Vidmoly, Voe, Upstream
- Multi-tier server failover matrix builder
- Full Spoofed Header Generation (Referer, Origin, User-Agent)
"""

import os
import re
import sys
import time
import json
import base64
import threading
import urllib.parse
import urllib.request
import ssl
import importlib
from typing import Dict, Any, Optional, List, Tuple

try:
    m3u8 = importlib.import_module("m3u8")
    HAS_M3U8 = True
except Exception:
    m3u8 = None
    HAS_M3U8 = False

try:
    import certifi
    HAS_CERTIFI = True
except Exception:
    certifi = None
    HAS_CERTIFI = False


# ==============================================================================
# 1. Thread-Safe In-Memory TTL Cache (RAM Cache)
# ==============================================================================
class StreamTTLCache:
    """
    High-performance, thread-safe in-memory cache for resolved media streams.
    Prevents repeated requests to upstream hosts, eliminates IP rate-limiting,
    and returns resolved stream URLs in sub-5ms on subsequent plays.
    """
    def __init__(self, default_ttl_seconds: int = 7200):
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        if not url:
            return None
        key = url.strip()
        now = time.time()
        with self._lock:
            item = self._cache.get(key)
            if not item:
                return None
            if now > item["expires_at"]:
                del self._cache[key]
                return None
            res = dict(item["data"])
            res["cached"] = True
            res["ttl_remaining"] = int(item["expires_at"] - now)
            return res

    def set(self, url: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        if not url or not data:
            return
        key = url.strip()
        ttl = ttl_seconds if (ttl_seconds is not None and ttl_seconds > 0) else self.default_ttl
        with self._lock:
            self._cache[key] = {
                "data": dict(data),
                "expires_at": time.time() + ttl
            }
            if len(self._cache) > 2000:
                self._evict_expired()

    def _evict_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, v in self._cache.items() if now > v["expires_at"]]
        for k in expired_keys:
            self._cache.pop(k, None)

    def stats(self) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            valid_items = sum(1 for v in self._cache.values() if v["expires_at"] > now)
            return {
                "total_cached": len(self._cache),
                "active_items": valid_items,
                "default_ttl_seconds": self.default_ttl
            }

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# ==============================================================================
# 2. Dean Edwards JavaScript Packer Decoder
# ==============================================================================
def unpack_dean_edwards_packer(packed_js: str) -> str:
    """
    Decodes Dean Edwards JavaScript Packer:
    eval(function(p,a,c,k,e,d){...}(payload, radix, count, words.split('|')))
    Used by Vipserver, Mixdrop, Vidmoly, Minochinos, Voe, Upstream.
    """
    if not packed_js:
        return ""

    # Search for parameters: radix, count, words
    end_match = re.search(r",\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"]([^'\"]*)['\"]\s*\.split\(\s*['\"]\|['\"]\s*\)", packed_js)
    if not end_match:
        return ""

    try:
        radix = int(end_match.group(1))
        count = int(end_match.group(2))
        symtab = end_match.group(3).split('|')
    except (ValueError, IndexError):
        return ""

    # Find the payload: starts after "return p}('" or 'return p}("'
    func_end = re.search(r'return\s+p\s*\}\s*\(\s*[\'"]', packed_js)
    if func_end:
        payload = packed_js[func_end.end() : end_match.start()]
    else:
        paren_idx = packed_js.rfind("}(", 0, end_match.start())
        if paren_idx != -1:
            payload = packed_js[paren_idx + 2 : end_match.start()].strip("'\" \t\r\n")
        else:
            return ""

    if payload.endswith("'") or payload.endswith('"'):
        payload = payload[:-1]

    def base_n(num: int, b: int) -> str:
        digits = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if num == 0:
            return "0"
        res = []
        while num > 0:
            res.append(digits[num % b])
            num //= b
        return "".join(reversed(res))

    lookup = {}
    for i in range(count):
        k = base_n(i, radix)
        val = symtab[i] if (i < len(symtab) and symtab[i]) else k
        lookup[k] = val

    return re.sub(r'\b[0-9a-zA-Z]+\b', lambda m: lookup.get(m.group(0), m.group(0)), payload)


def unpack_all_packers(html: str) -> str:
    """Finds all packed JavaScript blocks in HTML and un-packs them."""
    if not html:
        return ""
    packer_matches = re.findall(r'(eval\(function\(p,a,c,k,e,d\).+?\.split\([\'"]\|[\'"]\).*?\)\)+)', html, re.DOTALL)
    unpacked_blocks = []
    for block in packer_matches:
        decoded = unpack_dean_edwards_packer(block)
        if decoded:
            unpacked_blocks.append(decoded)
    return html + "\n" + "\n".join(unpacked_blocks)


# ==============================================================================
# 3. Main Direct Stream Extractor & Resolver Engine
# ==============================================================================
class DirectStreamExtractor:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    # Shared thread-safe in-memory cache instance (2-hour TTL by default)
    cache = StreamTTLCache(default_ttl_seconds=7200)

    # Domain to optimal Spoofed Referer / Origin mapping
    HOST_SPOOF_MAP = {
        "vipserver": ("https://mycima.buzz/", "https://mycima.buzz"),
        "liiivideo": ("https://mycima.buzz/", "https://mycima.buzz"),
        "bysebuho": ("https://egydead.live/", "https://egydead.live"),
        "minochinos": ("https://egydead.live/", "https://egydead.live"),
        "megamax": ("https://egydead.live/", "https://egydead.live"),
        "vidmoly": ("https://vidmoly.to/", "https://vidmoly.to"),
        "mixdrop": ("https://mixdrop.ag/", "https://mixdrop.ag"),
        "voe": ("https://voe.sx/", "https://voe.sx"),
        "streamtape": ("https://streamtape.com/", "https://streamtape.com"),
        "dood": ("https://dood.to/", "https://dood.to"),
        "ds2play": ("https://dood.to/", "https://dood.to"),
        "akwam": ("https://akwam.to/", "https://akwam.to"),
        "mycima": ("https://vid.mycima.cc/", "https://vid.mycima.cc"),
        "wecima": ("https://vid.mycima.cc/", "https://vid.mycima.cc"),
        "fasel": ("https://www.fasel-hd.co/", "https://www.fasel-hd.co"),
        "arabseed": ("https://m.arabseed.site/", "https://m.arabseed.site"),
        "byse": ("https://egydead.live/", "https://egydead.live"),
        "vidsrc": ("https://vidsrc.pm/", "https://vidsrc.pm"),
        "hgcloud": ("https://vidsrc.pm/", "https://vidsrc.pm"),
        "vidlink": ("https://vidlink.pro/", "https://vidlink.pro"),
        "multiembed": ("https://multiembed.mov/", "https://multiembed.mov"),
    }

    @classmethod
    def get_spoofed_headers(cls, url: str, custom_referer: Optional[str] = None) -> Dict[str, str]:
        """Generates spoofed HTTP headers required to bypass 403 Forbidden and hotlinking."""
        lower_u = url.lower() if url else ""
        referer = custom_referer
        origin = None

        if not referer:
            for key, (ref, orig) in cls.HOST_SPOOF_MAP.items():
                if key in lower_u:
                    referer = ref
                    origin = orig
                    break

        if not referer:
            try:
                parsed = urllib.parse.urlparse(url)
                referer = f"{parsed.scheme}://{parsed.netloc}/"
                origin = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                referer = "https://egydead.live/"
                origin = "https://egydead.live"

        if not origin:
            try:
                parsed = urllib.parse.urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                origin = referer

        return {
            "User-Agent": cls.USER_AGENT,
            "Referer": referer,
            "Origin": origin,
            "Accept": "*/*",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        }

    @classmethod
    def _create_ssl_context(cls, insecure_fallback: bool = False):
        if not insecure_fallback:
            try:
                if HAS_CERTIFI and certifi:
                    return ssl.create_default_context(cafile=certifi.where())
                return ssl.create_default_context()
            except Exception:
                pass
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    @classmethod
    def _fetch_html(cls, url: str, referer: Optional[str] = None, timeout: float = 6.0) -> str:
        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
        }
        if referer:
            headers["Referer"] = referer
        elif referer is None:
            lower_u = url.lower()
            for k, (ref, _) in cls.HOST_SPOOF_MAP.items():
                if k in lower_u:
                    headers["Referer"] = ref
                    break

        req = urllib.request.Request(url, headers=headers)
        try:
            ctx = cls._create_ssl_context(insecure_fallback=False)
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except ssl.SSLError as ssl_err:
            if os.environ.get("ATUBE_STRICT_TLS", "0") == "1":
                raise ssl_err
            ctx_fallback = cls._create_ssl_context(insecure_fallback=True)
            with urllib.request.urlopen(req, context=ctx_fallback, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='ignore')

    @classmethod
    def resolve(cls, stream_url: str, use_cache: bool = True, ttl: int = 7200) -> Dict[str, Any]:
        """
        Main on-demand resolution entry point:
        1. Checks in-memory TTL cache for instant return.
        2. Resolves direct media (.m3u8, .mp4).
        3. Executes specialized extractor or resilient semantic parsing.
        4. Saves successful result in TTL cache and returns clean JSON.
        """
        if not stream_url:
            return {"success": False, "error": "رابط البث غير متوفر"}

        stream_url = stream_url.strip()
        lower_url = stream_url.lower()

        # 1. Check TTL Cache first
        if use_cache:
            cached_res = cls.cache.get(stream_url)
            if cached_res:
                return cached_res

        headers = cls.get_spoofed_headers(stream_url)

        # 2. Already direct media file (.m3u8, .mp4, .mkv, .webm)
        if any(ext in lower_url for ext in [".m3u8", ".mp4", ".mkv", ".webm"]):
            is_hls = ".m3u8" in lower_url
            result = {
                "success": True,
                "stream_url": stream_url,
                "is_hls": is_hls,
                "format": "hls" if is_hls else "mp4",
                "headers": headers,
                "server_name": "رابط مباشر صافٍ ⚡",
                "is_direct": True,
                "cached": False
            }
            if use_cache:
                cls.cache.set(stream_url, result, ttl_seconds=ttl)
            return result

        try:
            resolved_dict: Optional[Dict[str, Any]] = None

            # 3. Host-specific fast extractors
            if "vipserver" in lower_url or "liiivideo" in lower_url:
                resolved_dict = cls._extract_vipserver(stream_url)
            elif "minochinos" in lower_url:
                resolved_dict = cls._extract_minochinos(stream_url)
            elif "bysebuho" in lower_url:
                resolved_dict = cls._extract_bysebuho(stream_url)
            elif "vidmoly" in lower_url:
                resolved_dict = cls._extract_vidmoly(stream_url)
            elif "mixdrop" in lower_url:
                resolved_dict = cls._extract_mixdrop(stream_url)
            elif "voe" in lower_url:
                resolved_dict = cls._extract_voe(stream_url)
            elif "hgcloud" in lower_url or "vidsrc" in lower_url:
                resolved_dict = cls._extract_hgcloud(stream_url)
            elif "vidlink" in lower_url or "multiembed" in lower_url:
                resolved_dict = cls._extract_vidlink(stream_url)
            elif "megamax" in lower_url:
                resolved_dict = cls._extract_megamax(stream_url)
            elif "dood" in lower_url or "ds2play" in lower_url:
                resolved_dict = cls._extract_doodstream(stream_url)
            elif "streamtape" in lower_url:
                resolved_dict = cls._extract_streamtape(stream_url)

            # 4. Resilient Semantic Heuristic Parser (Handles changes in host DOM)
            if not resolved_dict or not resolved_dict.get("success"):
                resolved_dict = cls._extract_resilient_semantic(stream_url)

            # 5. yt-dlp fallback if available
            if not resolved_dict or not resolved_dict.get("success"):
                resolved_dict = cls._extract_with_ytdlp(stream_url)

            if resolved_dict and resolved_dict.get("success"):
                resolved_dict["cached"] = False
                if use_cache:
                    cls.cache.set(stream_url, resolved_dict, ttl_seconds=ttl)
                return resolved_dict

            return {
                "success": False,
                "error": resolved_dict.get("error", "لم يتم العثور على رابط مباشر قابل للاستخراج"),
                "fallback_url": stream_url,
                "isEmbed": True,
                "headers": headers
            }

        except Exception as ex:
            return {
                "success": False,
                "error": f"خطأ استخراج: {str(ex)}",
                "fallback_url": stream_url,
                "isEmbed": True,
                "headers": headers
            }

    # ==========================================================================
    # Resilient Semantic Heuristic Parser (Layout-Change Resistant)
    # ==========================================================================
    @classmethod
    def _extract_resilient_semantic(cls, url: str) -> Dict[str, Any]:
        """
        Parses pages via semantic heuristics rather than brittle CSS selectors.
        Unpacks Dean Edwards scripts, extracts JWPlayer/VideoJS video configs,
        and searches for valid tokenized HLS/MP4 stream URLs.
        """
        try:
            raw_html = cls._fetch_html(url, referer=url)
            full_text = unpack_all_packers(raw_html)

            # 1. HLS .m3u8 patterns (priority)
            hls_matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', full_text)
            for m in hls_matches:
                # Filter out obvious ad/pixel domains
                if any(bad in m.lower() for bad in ["doubleclick", "pixel", "analytics", "banner"]):
                    continue
                return {
                    "success": True,
                    "stream_url": m,
                    "is_hls": True,
                    "format": "hls",
                    "headers": cls.get_spoofed_headers(m, custom_referer=url),
                    "server_name": "بث مباشر سحابي HLS"
                }

            # 2. MP4 patterns
            mp4_matches = re.findall(r'https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*', full_text)
            for m in mp4_matches:
                if any(bad in m.lower() for bad in ["sample", "intro", "ad.", "ad_", "preview"]):
                    continue
                return {
                    "success": True,
                    "stream_url": m,
                    "is_hls": False,
                    "format": "mp4",
                    "headers": cls.get_spoofed_headers(m, custom_referer=url),
                    "server_name": "بث مباشر سحابي MP4"
                }

            # 3. JWPlayer / VideoJS source configs
            jw_match = re.search(r'(?:file|source|src)\s*:\s*["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', full_text)
            if jw_match:
                stream_u = jw_match.group(1)
                is_hls = ".m3u8" in stream_u.lower()
                return {
                    "success": True,
                    "stream_url": stream_u,
                    "is_hls": is_hls,
                    "format": "hls" if is_hls else "mp4",
                    "headers": cls.get_spoofed_headers(stream_u, custom_referer=url),
                    "server_name": "سيرفر سحابي نقي"
                }

        except Exception:
            pass

        return {"success": False, "error": "Semantic parsing found no direct media"}

    # ==========================================================================
    # Specialized Host Extractors
    # ==========================================================================
    @classmethod
    def _extract_vipserver(cls, url: str) -> Dict[str, Any]:
        """Extracts direct m3u8 stream from Vipserver / liiivideo."""
        html = cls._fetch_html(url, referer="")
        unpacked = unpack_all_packers(html)
        m3u8_match = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', unpacked)
        if m3u8_match:
            stream_u = m3u8_match.group(0)
            return {
                "success": True,
                "stream_url": stream_u,
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://vipserver.liiivideo.com/"},
                "server_name": "سيرفر Vipserver Direct FHD ⚡"
            }
        return {"success": False, "error": "Vipserver m3u8 not found"}

    @classmethod
    def _extract_minochinos(cls, url: str) -> Dict[str, Any]:
        """Extracts direct m3u8 stream from Minochinos."""
        html = cls._fetch_html(url, referer="https://egydead.live/")
        unpacked = unpack_all_packers(html)
        m3u8_match = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', unpacked)
        if m3u8_match:
            stream_u = m3u8_match.group(0)
            return {
                "success": True,
                "stream_url": stream_u,
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://minochinos.com/"},
                "server_name": "سيرفر Minochinos Direct FHD ⚡"
            }
        return {"success": False, "error": "Minochinos m3u8 not found"}

    @classmethod
    def _extract_bysebuho(cls, url: str) -> Dict[str, Any]:
        """Extracts direct stream from Bysebuho."""
        html = cls._fetch_html(url, referer="https://egydead.live/")
        unpacked = unpack_all_packers(html)
        m3u8_match = re.search(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', unpacked)
        if m3u8_match:
            stream_u = m3u8_match.group(0)
            return {
                "success": True,
                "stream_url": stream_u,
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://bysebuho.com/"},
                "server_name": "سيرفر Bysebuho Direct FHD ⚡"
            }
        return cls._extract_resilient_semantic(url)

    @classmethod
    def _extract_vidmoly(cls, url: str) -> Dict[str, Any]:
        embed_url = url.replace("/w/", "/embed-").replace("/d/", "/embed-")
        if not embed_url.startswith("http"):
            embed_url = "https://" + embed_url
        html = cls._fetch_html(embed_url, referer="https://vidmoly.to/")
        unpacked = unpack_all_packers(html)

        m3u8_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', unpacked)
        if m3u8_match:
            return {
                "success": True,
                "stream_url": m3u8_match.group(1),
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://vidmoly.to/"},
                "server_name": "Vidmoly VIP Direct"
            }
        return {"success": False, "error": "Vidmoly direct stream not found"}

    @classmethod
    def _extract_mixdrop(cls, url: str) -> Dict[str, Any]:
        embed_url = url.replace("/f/", "/e/")
        html = cls._fetch_html(embed_url, referer="https://mixdrop.ag/")
        unpacked = unpack_all_packers(html)

        wurl_match = re.search(r'MDCore\.wurl\s*=\s*["\']([^"\']+)["\']', unpacked)
        if wurl_match:
            direct_url = wurl_match.group(1)
            if direct_url.startswith("//"):
                direct_url = "https:" + direct_url
            return {
                "success": True,
                "stream_url": direct_url,
                "is_hls": ".m3u8" in direct_url,
                "format": "hls" if ".m3u8" in direct_url else "mp4",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://mixdrop.ag/"},
                "server_name": "Mixdrop Direct"
            }
        return {"success": False, "error": "Mixdrop direct stream not found"}

    @classmethod
    def _extract_voe(cls, url: str) -> Dict[str, Any]:
        html = cls._fetch_html(url, referer="https://voe.sx/")
        unpacked = unpack_all_packers(html)

        # Look for HLS source in Voe JS config
        hls_match = re.search(r'[\'"]hls[\'"]\s*:\s*[\'"](https?://[^\'"]+)[\'"]', unpacked)
        if hls_match:
            hls_u = hls_match.group(1)
            return {
                "success": True,
                "stream_url": hls_u,
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://voe.sx/"},
                "server_name": "Voe Ultra HD"
            }
        return {"success": False, "error": "Voe direct stream not found"}

    @classmethod
    def _extract_streamtape(cls, url: str) -> Dict[str, Any]:
        embed_url = url.replace("/v/", "/e/")
        html = cls._fetch_html(embed_url, referer="https://streamtape.com/")
        unpacked = unpack_all_packers(html)

        # Search for robotlink concatenation
        link_part = re.search(r'document\.getElementById\([\'"]robotlink[\'"]\)\.innerHTML\s*=\s*[\'"]([^\'"]+)[\'"]', unpacked)
        token_part = re.search(r'\+[\s\'"]*([^\'";]+)&token=([^\'";]+)', unpacked)
        if link_part and token_part:
            direct_url = f"https:{link_part.group(1)}&token={token_part.group(2)}"
            return {
                "success": True,
                "stream_url": direct_url,
                "is_hls": False,
                "format": "mp4",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://streamtape.com/"},
                "server_name": "Streamtape Direct MP4"
            }
        return {"success": False, "error": "Streamtape direct stream not found"}

    @classmethod
    def _extract_megamax(cls, url: str) -> Dict[str, Any]:
        clean_url = url
        if "megamax.me" in clean_url:
            clean_url = clean_url.replace("megamax.me", "eg.megamax.cam")
        try:
            html = cls._fetch_html(clean_url, referer="https://egydead.live/", timeout=5.0)
            unpacked = unpack_all_packers(html)
            m3u8_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', unpacked)
            if m3u8_match:
                return {
                    "success": True,
                    "stream_url": m3u8_match.group(1),
                    "is_hls": True,
                    "format": "hls",
                    "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://egydead.live/"},
                    "server_name": "MegaMax Direct FHD"
                }
        except Exception:
            pass

        return {
            "success": False,
            "error": "MegaMax direct m3u8 stream not found",
            "stream_url": clean_url,
            "is_hls": False,
            "isEmbed": True,
            "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://egydead.live/"},
            "server_name": "MegaMax Cloud"
        }

    @classmethod
    def _extract_hgcloud(cls, url: str) -> Dict[str, Any]:
        html = cls._fetch_html(url, referer="https://vidsrc.pm/")
        m3u8_match = re.search(r'(https?://[^"\']+\.m3u8[^"\']*)', html)
        if m3u8_match:
            return {
                "success": True,
                "stream_url": m3u8_match.group(1),
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://vidsrc.pm/"},
                "server_name": "Hgcloud Ultra Direct"
            }
        return cls._extract_resilient_semantic(url)

    @classmethod
    def _extract_vidlink(cls, url: str) -> Dict[str, Any]:
        html = cls._fetch_html(url, referer="https://vidlink.pro/")
        m3u8_match = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html)
        if m3u8_match:
            return {
                "success": True,
                "stream_url": m3u8_match.group(1),
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://vidlink.pro/"},
                "server_name": "Vidlink Direct Master"
            }
        return cls._extract_resilient_semantic(url)

    @classmethod
    def _extract_doodstream(cls, url: str) -> Dict[str, Any]:
        embed_url = url.replace("/d/", "/e/")
        html = cls._fetch_html(embed_url, referer=url)
        pass_match = re.search(r'/pass_md5/([^"\']+)', html)
        if pass_match:
            pass_url = f"https://dood.to/pass_md5/{pass_match.group(1)}"
            token_data = cls._fetch_html(pass_url, referer=embed_url)
            final_stream = token_data + "zZwue Tucker?token=" + pass_match.group(1)
            return {
                "success": True,
                "stream_url": final_stream,
                "is_hls": False,
                "format": "mp4",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": embed_url},
                "server_name": "Doodstream Direct"
            }
        return {"success": False, "error": "Doodstream direct stream not found"}

    @classmethod
    def _extract_with_ytdlp(cls, url: str) -> Dict[str, Any]:
        """Deep stream extraction using yt-dlp when installed."""
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extract_flat': False,
                'socket_timeout': 5,
                'http_headers': {
                    'User-Agent': cls.USER_AGENT,
                    'Referer': url
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and info.get('url'):
                    direct_url = info['url']
                    # Guard: yt-dlp generic extractor returns the input webpage itself if no stream found
                    if direct_url == url or not any(ext in direct_url.lower() for ext in ['.m3u8', '.mp4', '.mkv', '.webm', '.ts', 'googlevideo', 'cdn']):
                        return {"success": False, "stream_url": url}
                    is_hls = ".m3u8" in direct_url or info.get('protocol') == 'm3u8_native'
                    return {
                        "success": True,
                        "stream_url": direct_url,
                        "is_hls": is_hls,
                        "format": "hls" if is_hls else "mp4",
                        "headers": info.get('http_headers', {}),
                        "server_name": f"{info.get('extractor_key', 'Cloud')} Direct Stream"
                    }
        except Exception:
            pass
        return {"success": False, "stream_url": url}

    # ==========================================================================
    # Multi-Tier Failover Matrix Builder
    # ==========================================================================
    @classmethod
    def build_failover_matrix(
        cls,
        servers: List[Dict[str, Any]],
        tmdb_id: Optional[str] = None,
        content_type: str = "movie",
        season: Optional[int] = None,
        episode: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Organizes stream candidates into a 3-tier high-availability matrix:
        - Tier 1: Real direct video streams (HLS/MP4) or resolvable harvesters.
        - Tier 2: Ghost Embed Proxied links (/api/watch/embed) with ad-shielding.
        - Tier 3: Universal Guaranteed TMDB Embed Mirrors (VidLink, MultiEmbed, 2Embed).
        """
        tier1: List[Dict[str, Any]] = []
        tier2: List[Dict[str, Any]] = []
        tier3: List[Dict[str, Any]] = []

        seen_urls = set()

        for srv in servers:
            url = srv.get("stream_url") or srv.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            name = srv.get("server_name") or srv.get("name") or "سيرفر البث"
            is_direct = any(ext in url.lower() for ext in [".m3u8", ".mp4", ".mkv", ".webm"])

            if is_direct or any(h in url.lower() for h in ["vidmoly", "mixdrop", "voe", "streamtape", "dood"]):
                tier1.append({
                    "name": f"{name} (مباشر)",
                    "url": url,
                    "stream_url": url,
                    "tier": 1,
                    "badge": "سريع ⚡",
                    "is_direct": is_direct,
                    "is_hls": ".m3u8" in url.lower()
                })
            else:
                # Wrap through Ghost Embed Proxy
                ghost_url = f"/api/watch/embed?url={urllib.parse.quote(url)}"
                tier2.append({
                    "name": f"{name} (درع الإعلانات)",
                    "url": ghost_url,
                    "stream_url": ghost_url,
                    "raw_url": url,
                    "tier": 2,
                    "badge": "درع خفي 🛡️",
                    "is_direct": False,
                    "isEmbed": True
                })

        # Add Tier 3 (Universal TMDB Mirrors) if tmdb_id is available
        if tmdb_id and str(tmdb_id).isdigit():
            t_id = str(tmdb_id).strip()
            if content_type == "series" and season and episode:
                tier3.append({
                    "name": "VidLink Global FHD",
                    "url": f"https://vidlink.pro/tv/{t_id}/{season}/{episode}",
                    "stream_url": f"https://vidlink.pro/tv/{t_id}/{season}/{episode}",
                    "tier": 3,
                    "badge": "عالمي ⭐",
                    "isEmbed": True
                })
                tier3.append({
                    "name": "MultiEmbed VIP",
                    "url": f"https://multiembed.mov/?video_id={t_id}&tmdb=1&s={season}&e={episode}",
                    "stream_url": f"https://multiembed.mov/?video_id={t_id}&tmdb=1&s={season}&e={episode}",
                    "tier": 3,
                    "badge": "احتياطي 🌐",
                    "isEmbed": True
                })
            else:
                tier3.append({
                    "name": "VidLink Global FHD",
                    "url": f"https://vidlink.pro/movie/{t_id}",
                    "stream_url": f"https://vidlink.pro/movie/{t_id}",
                    "tier": 3,
                    "badge": "عالمي ⭐",
                    "isEmbed": True
                })
                tier3.append({
                    "name": "MultiEmbed VIP",
                    "url": f"https://multiembed.mov/?video_id={t_id}&tmdb=1",
                    "stream_url": f"https://multiembed.mov/?video_id={t_id}&tmdb=1",
                    "tier": 3,
                    "badge": "احتياطي 🌐",
                    "isEmbed": True
                })

        return tier1 + tier2 + tier3

    @classmethod
    def get_file_size(cls, url: str) -> Dict[str, Any]:
        """Probes remote content length using HEAD request."""
        if not url:
            return {"size_bytes": 0, "size_mb": 0, "formatted": "غير محدد"}
        try:
            req = urllib.request.Request(
                url,
                headers=cls.get_spoofed_headers(url),
                method="HEAD"
            )
            ctx = cls._create_ssl_context()
            with urllib.request.urlopen(req, context=ctx, timeout=3.0) as resp:
                cl = resp.headers.get("Content-Length")
                if cl and cl.isdigit():
                    bytes_len = int(cl)
                    mb_len = round(bytes_len / (1024 * 1024), 1)
                    formatted = f"{mb_len} MB" if mb_len < 1000 else f"{round(mb_len / 1024, 2)} GB"
                    return {"size_bytes": bytes_len, "size_mb": mb_len, "formatted": formatted}
        except Exception:
            pass
        return {"size_bytes": 0, "size_mb": 0, "formatted": "حجم تقديري"}
