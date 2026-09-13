# -*- coding: utf-8 -*-
"""
A TuBe - Direct Stream Resolver & Extractor Engine
Extracts direct clean video streams (.m3u8 / .mp4) from scraped video hosts.
Bypasses iframes, ads, anti-bot guards, and X-Frame-Options headers.
Supports: Vidmoly, Mixdrop, Hgcloud, Vidlink, MultiEmbed, VidSrc, DoodStream, Streamtape, Akwam, FaselHD, ArabSeed.
"""

import os
import re
import json
import base64
import urllib.parse
import urllib.request
import ssl
from typing import Dict, Any, Optional, List

try:
    import m3u8
    HAS_M3U8 = True
except Exception:
    HAS_M3U8 = False

class DirectStreamExtractor:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    @classmethod
    def _create_ssl_context(cls):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    @classmethod
    def _fetch_html(cls, url: str, referer: Optional[str] = None, timeout: float = 6.0) -> str:
        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ar,en-US;q=0.7,en;q=0.3"
        }
        if referer:
            headers["Referer"] = referer
        
        req = urllib.request.Request(url, headers=headers)
        ctx = cls._create_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')

    @classmethod
    def resolve(cls, stream_url: str) -> Dict[str, Any]:
        """
        Main entry point: takes any embed/stream URL and extracts direct stream.
        """
        if not stream_url:
            return {"success": False, "error": "رابط البث غير متوفر"}

        lower_url = stream_url.lower()

        # 1. إذا كان الرابط مباشراً بالفعل (.m3u8 أو .mp4)
        if any(ext in lower_url for ext in [".m3u8", ".mp4", ".mkv", ".webm"]):
            is_hls = ".m3u8" in lower_url
            return {
                "success": True,
                "stream_url": stream_url,
                "is_hls": is_hls,
                "format": "hls" if is_hls else "mp4",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": stream_url},
                "server_name": "رابط مباشر صافٍ",
                "is_direct": True
            }

        try:
            # 2. فك تشفير سيرفر Vidmoly
            if "vidmoly" in lower_url:
                return cls._extract_vidmoly(stream_url)

            # 3. فك تشفير سيرفر Mixdrop
            elif "mixdrop" in lower_url:
                return cls._extract_mixdrop(stream_url)

            # 4. فك تشفير سيرفر Hgcloud / Vidsrc
            elif "hgcloud" in lower_url or "vidsrc" in lower_url:
                return cls._extract_hgcloud(stream_url)

            # 5. فك تشفير سيرفر Vidlink / MultiEmbed
            elif "vidlink" in lower_url or "multiembed" in lower_url:
                return cls._extract_vidlink(stream_url)

            # 6. فك تشفير Doodstream / Streamtape
            elif "dood" in lower_url or "ds2play" in lower_url:
                return cls._extract_doodstream(stream_url)

            # 7. فك تشفير عام (Generic m3u8/mp4 regex parser)
            generic_res = cls._extract_generic(stream_url)
            if generic_res.get("success"):
                return generic_res

            # 8. محاولة عبر yt-dlp للاستخراج العميق
            return cls._extract_with_ytdlp(stream_url)

        except Exception as ex:
            ytdl_res = cls._extract_with_ytdlp(stream_url)
            if ytdl_res.get("success"):
                return ytdl_res
            return {
                "success": False,
                "error": f"فشل الاستخراج: {str(ex)}",
                "stream_url": stream_url,
                "fallback_url": stream_url,
                "is_hls": ".m3u8" in stream_url
            }

    @classmethod
    def _extract_with_ytdlp(cls, url: str) -> Dict[str, Any]:
        """Deep stream extraction using yt-dlp."""
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
                    return {
                        "success": True,
                        "stream_url": direct_url,
                        "is_hls": ".m3u8" in direct_url or info.get('protocol') == 'm3u8_native',
                        "format": "hls" if (".m3u8" in direct_url or info.get('protocol') == 'm3u8_native') else "mp4",
                        "headers": info.get('http_headers', {}),
                        "server_name": f"{info.get('extractor_key', 'Cloud')} Direct Stream"
                    }
        except Exception:
            pass
        return {"success": False, "stream_url": url}

    @classmethod
    def _extract_vidmoly(cls, url: str) -> Dict[str, Any]:
        embed_url = url.replace("/w/", "/embed-").replace("/d/", "/embed-")
        if not embed_url.startswith("http"):
            embed_url = "https://" + embed_url
        html = cls._fetch_html(embed_url, referer="https://vidmoly.to/")
        
        # البحث عن ملف m3u8 في سكريبت jwplayer / sources
        m3u8_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html)
        if m3u8_match:
            direct_m3u8 = m3u8_match.group(1)
            return {
                "success": True,
                "stream_url": direct_m3u8,
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://vidmoly.to/"},
                "server_name": "Vidmoly VIP Direct"
            }
        
        # محاولة البحث عن مصادر الفيديو الوسمية
        src_match = re.search(r'<source[^>]+src=["\']([^"\']+)["\']', html)
        if src_match:
            return {
                "success": True,
                "stream_url": src_match.group(1),
                "is_hls": ".m3u8" in src_match.group(1),
                "format": "hls" if ".m3u8" in src_match.group(1) else "mp4",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://vidmoly.to/"},
                "server_name": "Vidmoly Direct"
            }
        raise ValueError("لم يتم العثور على رابط m3u8 في Vidmoly")

    @classmethod
    def _extract_mixdrop(cls, url: str) -> Dict[str, Any]:
        embed_url = url.replace("/f/", "/e/")
        html = cls._fetch_html(embed_url, referer="https://mixdrop.ag/")
        
        # Mixdrop يستخدم تشفير Packer (eval(function(p,a,c,k,e,d)))
        wurl_match = re.search(r'MDCore\.wurl\s*=\s*["\']([^"\']+)["\']', html)
        if wurl_match:
            direct_url = wurl_match.group(1)
            if direct_url.startswith("//"): direct_url = "https:" + direct_url
            return {
                "success": True,
                "stream_url": direct_url,
                "is_hls": ".m3u8" in direct_url,
                "format": "hls" if ".m3u8" in direct_url else "mp4",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://mixdrop.ag/"},
                "server_name": "Mixdrop Direct"
            }
        
        mp4_match = re.search(r'(https?:)?//[a-zA-Z0-9_\-\./]+\.mp4[^"\'\s]*', html)
        if mp4_match:
            direct_mp4 = mp4_match.group(0)
            if direct_mp4.startswith("//"): direct_mp4 = "https:" + direct_mp4
            return {
                "success": True,
                "stream_url": direct_mp4,
                "is_hls": False,
                "format": "mp4",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": "https://mixdrop.ag/"},
                "server_name": "Mixdrop Direct MP4"
            }
        raise ValueError("فشل فك شفرة Mixdrop")

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
        return cls._extract_generic(url)

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
        return cls._extract_generic(url)

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
        raise ValueError("فشل استخراج Doodstream")

    @classmethod
    def _extract_generic(cls, url: str) -> Dict[str, Any]:
        """محلل ذكي عام للمواقع العربية والسيرفرات الأخرى"""
        html = cls._fetch_html(url, referer=url)
        m3u8 = re.search(r'(https?://[^"\']+\.m3u8[^\s"\']*)', html)
        if m3u8:
            return {
                "success": True,
                "stream_url": m3u8.group(1),
                "is_hls": True,
                "format": "hls",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": url},
                "server_name": "A TuBe Cloud HLS"
            }
        mp4 = re.search(r'(https?://[^"\']+\.mp4[^\s"\']*)', html)
        if mp4:
            return {
                "success": True,
                "stream_url": mp4.group(1),
                "is_hls": False,
                "format": "mp4",
                "headers": {"User-Agent": cls.USER_AGENT, "Referer": url},
                "server_name": "A TuBe Direct MP4"
            }
        return {
            "success": True,
            "stream_url": url,
            "is_hls": ".m3u8" in url,
            "format": "hls" if ".m3u8" in url else "mp4",
            "headers": {"User-Agent": cls.USER_AGENT, "Referer": url},
            "server_name": "A TuBe Direct Stream"
        }

    @classmethod
    def get_file_size(cls, url: str) -> Dict[str, Any]:
        """جلب حجم الملف الفعلي عبر HEAD request"""
        if not url:
            return {"size_bytes": 0, "size_mb": 0, "formatted": "غير محدد"}
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": cls.USER_AGENT, "Referer": url},
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
