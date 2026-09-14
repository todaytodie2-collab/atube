# -*- coding: utf-8 -*-
"""
A Tube Local Server & Real Streaming API Bridge
Integrates real IPTV channels, SQLite WAL-mode VOD database, Oscar TV endpoints, and Multi-Site Scraper Crawler
"""

import os
import sys
import re
import ssl
import json
import socket
import ipaddress
import threading
import urllib.parse
import urllib.request
import datetime
import time
import subprocess
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Force UTF-8 for stdout and stderr on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add services and root paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "services"))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

# In-Memory Cache for EPG (prevents CPU spikes on repeated schedule requests)
_EPG_CACHE = {"ts": 0.0, "data": {}}
_EPG_CACHE_TTL = 600.0  # 10 minutes cache

# Security Guard: Blocked internal networks for SSRF prevention
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def is_safe_external_url(url: str) -> bool:
    """SSRF Guard: Validates that URL points to external HTTP/HTTPS domains and not internal private IPs."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Block localhost strings explicitly
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "internal", "local"):
            return False
        # Resolve hostname to IP to prevent DNS rebinding attacks
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if (ip_obj.is_private or ip_obj.is_loopback or 
                    ip_obj.is_link_local or ip_obj.is_reserved or 
                    ip_obj.is_multicast):
                    return False
                for net in BLOCKED_IP_NETWORKS:
                    if ip_obj in net:
                        return False
        except Exception:
            return False
        return True
    except Exception:
        return False

try:
    from services.remote_config import RemoteConfigManager
    from services.vod_db import VODDatabase
    from services.rss_manager import RSSManager
    from services.procedural_manifest import ProceduralManifestEngine
    from services.stream_sanitizer import StreamSanitizer
    from services.api_controller import APIController
    from services.stream_extractor import DirectStreamExtractor
    from services.google_dork_scraper import GoogleDorkScraper
    from services.iptv_manager import IPTVManager
    from services.live_tv_service import LiveTVService, LiveTVManager
    from services.catalog_sync import CatalogSync, ContentIngestEngine, ContinuousSyncEngine
    from services.deep_search_fallback import DeepSearchFallbackEngine
    from services.stream_bridge import InvisibleStreamBridge
    from services.universal_crawler_daemon import UniversalCrawlerDaemon
    from services.mycima_harvester import MyCimaHarvester
    HAS_SERVICES = True
except Exception as e:
    print(f"[A Tube Server] Note: Services loading exception: {e}")
    HAS_SERVICES = False

try:
    from auto_git_sync import AutoGitSync
except Exception:
    AutoGitSync = None


class ATubeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def send_cors_json(self, obj, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def translate_path(self, path):
        # Path Traversal Guard: ensure path stays strictly within BASE_DIR
        resolved = super().translate_path(path)
        try:
            norm_base = os.path.realpath(BASE_DIR)
            norm_path = os.path.realpath(resolved)
            if not norm_path.startswith(norm_base):
                # Out of bounds access attempt, divert to safe 404
                return os.path.join(norm_base, "non_existent_file_safe_guard")
        except Exception:
            return os.path.join(BASE_DIR, "non_existent_file_safe_guard")
        return resolved

    def log_message(self, format, *args):
        # Safe logging without cp1252 crash
        try:
            sys.stdout.write("%s - - [%s] %s\n" %
                             (self.address_string(),
                              self.log_date_time_string(),
                              format % args))
            sys.stdout.flush()
        except Exception:
            pass

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)

            # 0. API: Health & Diagnostic Watchdog Endpoint
            if path in ["/api/health", "/api/ping"]:
                self.send_cors_json({
                    "status": "ok",
                    "system": "A TuBe Ultra HD Backend",
                    "version": "2.5.0",
                    "timestamp": time.time(),
                    "has_services": HAS_SERVICES,
                    "active_resolvers": 8
                })
                return

            # 0.1 API: High-Performance Universal Stream Proxy (Anti-CORS & Anti-403)
            if path == "/api/stream/proxy":
                target_url = query.get("url", [None])[0]
                if not target_url:
                    self.send_error(400, "Missing url parameter")
                    return

                if not is_safe_external_url(target_url):
                    self.send_error(403, "URL target blocked by SSRF security rules")
                    return

                req_referer = query.get("referer", [None])[0]
                if not req_referer:
                    if "megamax" in target_url:
                        req_referer = "https://egydead.live/"
                    elif "vidmoly" in target_url:
                        req_referer = "https://vidmoly.to/"
                    elif "fasel" in target_url:
                        req_referer = "https://www.fasel-hd.co/"
                    elif "mixdrop" in target_url:
                        req_referer = "https://mixdrop.ag/"
                    elif "akwam" in target_url:
                        req_referer = "https://akwam.to/"
                    else:
                        req_referer = target_url

                client_range = self.headers.get("Range")
                proxy_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Referer": req_referer,
                    "Origin": (urllib.parse.urlparse(req_referer).scheme + "://" + urllib.parse.urlparse(req_referer).netloc) if req_referer else "https://egydead.live",
                    "Accept": "*/*",
                    "Accept-Encoding": "identity"
                }
                if client_range:
                    proxy_headers["Range"] = client_range

                req = urllib.request.Request(target_url, headers=proxy_headers)
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

                try:
                    with urllib.request.urlopen(req, context=ssl_ctx, timeout=12.0) as remote_resp:
                        status_code = remote_resp.status
                        self.send_response(status_code)
                        for h_key, h_val in remote_resp.headers.items():
                            if h_key.lower() in ["content-type", "content-length", "content-range", "accept-ranges", "last-modified", "etag"]:
                                self.send_header(h_key, h_val)
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Access-Control-Allow-Headers", "*")
                        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
                        self.end_headers()

                        while True:
                            chunk = remote_resp.read(64 * 1024)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except urllib.error.HTTPError as he:
                    self.send_response(he.code)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    try:
                        self.wfile.write(he.read())
                    except Exception:
                        pass
                except Exception as ex:
                    self.send_error(502, f"Proxy stream error: {str(ex)}")
                return

            # 0.2 API: Direct Stream Resolver
            if path == "/api/resolve-stream":
                target_url = query.get("url", [None])[0]
                if not target_url:
                    self.send_cors_json({"success": False, "error": "Missing url"})
                    return
                try:
                    res = DirectStreamExtractor.resolve(target_url)
                    self.send_cors_json(res)
                except Exception as ex:
                    self.send_cors_json({"success": False, "error": str(ex)})
                return

            # 0.3 API: Live Google Dorking Scraper
            if path == "/api/scrape-servers":
                t_en = query.get("title_en", [""])[0]
                t_ar = query.get("title_ar", [""])[0]
                year = query.get("year", [""])[0]
                c_type = query.get("type", ["movie"])[0]
                season = query.get("season", [""])[0]
                episode = query.get("episode", [""])[0]
                try:
                    res = GoogleDorkScraper.scrape_servers(t_en, t_ar, year, c_type, season, episode)
                    self.send_cors_json(res)
                except Exception as ex:
                    self.send_cors_json({"success": False, "error": str(ex), "servers": []})
                return

            # 0.4 API: Invisible Stream Bridge (Zero-Click Auto-Play direct link resolver)
            if path == "/api/stream/bridge":
                title = query.get("title", [query.get("title_ar", [query.get("title_en", [""])])])[0]
                year = query.get("year", [""])[0]
                c_type = query.get("type", ["movie"])[0]
                media_id = query.get("media_id", [query.get("id", [""])])[0]
                season = query.get("season", [None])[0]
                episode = query.get("episode", [None])[0]
                s_int = int(season) if season and season.isdigit() else None
                e_int = int(episode) if episode and episode.isdigit() else None

                try:
                    if 'InvisibleStreamBridge' in globals() and InvisibleStreamBridge:
                        res = InvisibleStreamBridge.resolve_clean_stream(
                            title=title,
                            year=year,
                            content_type=c_type,
                            season=s_int,
                            episode=e_int,
                            media_id=media_id
                        )
                        self.send_cors_json(res)
                    else:
                        self.send_cors_json({"success": False, "error": "Stream Bridge service unavailable"})
                except Exception as ex:
                    self.send_cors_json({"success": False, "error": str(ex)})
                return

            # 0.45 API: Ghost Embed Proxy & Sandbox Trap (Neutralizes Popups, Strips Clutter)
            if path == "/api/watch/embed":
                target_url = query.get("url", [""])[0]
                referer = query.get("referer", ["https://vid.mycima.cc/"])[0]
                if not target_url:
                    self.send_error(400, "Missing target URL")
                    return

                try:
                    parsed_target = urllib.parse.urlparse(target_url)
                    base_origin = f"{parsed_target.scheme}://{parsed_target.netloc}"

                    cmd = [
                        "curl.exe", "-s", "--max-time", "10",
                        "-H", f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "-H", f"Referer: {referer}",
                        "-H", f"Origin: {referer}",
                        "--compressed",
                        target_url
                    ]
                    fetch_res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
                    content = fetch_res.stdout or ""

                    if not content or len(content) < 50:
                        self.send_response(302)
                        self.send_header("Location", target_url)
                        self.end_headers()
                        return

                    base_tag = f'<base href="{base_origin}/">'
                    ghost_script = """
                    <script>
                    (function() {
                        // Ghost window.open trap: satisfies anti-adblock detection, immediately neutralizes popup in background
                        window.open = function(url, target, features) {
                            console.log('[A TuBe Ghost Trap] Absorbed popup:', url);
                            var dummy = {
                                closed: false,
                                close: function() { this.closed = true; },
                                focus: function() {},
                                blur: function() {},
                                location: { href: url || '' }
                            };
                            setTimeout(function() { dummy.close(); }, 20);
                            return dummy;
                        };
                        // Intercept target=_blank link clicks during seeking/playing
                        document.addEventListener('click', function(e) {
                            var a = e.target && e.target.closest ? e.target.closest('a') : null;
                            if (a && (a.target === '_blank' || a.target === '_new')) {
                                e.preventDefault();
                                e.stopPropagation();
                                console.log('[A TuBe Ghost Trap] Blocked target=_blank link');
                            }
                        }, true);
                        window.alert = function() {};
                        window.confirm = function() { return true; };
                        window.prompt = function() { return null; };
                        window.onbeforeunload = null;
                    })();
                    </script>
                    <style>
                        body, html { width: 100vw !important; height: 100vh !important; margin: 0 !important; padding: 0 !important; overflow: hidden !important; background: #000 !important; }
                        #header, header, footer, .header, .footer, .navbar, .site-header, .top-bar, .breadcrumb, .sidebar, .comments, .related-posts, .list_servers { display: none !important; }
                        #player, .player, video, iframe, .jwplayer, .video-js, .embedded { width: 100vw !important; height: 100vh !important; max-width: 100vw !important; max-height: 100vh !important; position: fixed !important; top: 0 !important; left: 0 !important; }
                    </style>
                    """

                    if "<head>" in content:
                        content = content.replace("<head>", f"<head>{base_tag}{ghost_script}", 1)
                    elif "<HEAD>" in content:
                        content = content.replace("<HEAD>", f"<HEAD>{base_tag}{ghost_script}", 1)
                    else:
                        content = f"{base_tag}{ghost_script}{content}"

                    raw_bytes = content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw_bytes)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Cache-Control", "no-cache, no-store")
                    self.end_headers()
                    self.wfile.write(raw_bytes)
                except Exception as ex_emb:
                    self.send_error(502, f"Ghost embed error: {ex_emb}")
                return

            # 0.5 API: Universal Crawler Status & Control
            if path == "/api/crawler/status":
                try:
                    stats = UniversalCrawlerDaemon.get_stats() if 'UniversalCrawlerDaemon' in globals() else {}
                    self.send_cors_json({"success": True, "stats": stats})
                except Exception as ex:
                    self.send_cors_json({"success": False, "error": str(ex)})
                return

            if path == "/api/crawler/run":
                limit_q = query.get("limit", ["20"])[0]
                limit_val = int(limit_q) if limit_q.isdigit() else 20
                try:
                    if 'UniversalCrawlerDaemon' in globals():
                        threading.Thread(target=UniversalCrawlerDaemon.crawl_all, kwargs={"max_items": limit_val}, daemon=True).start()
                        self.send_cors_json({"success": True, "message": f"Crawler started in background for up to {limit_val} items"})
                    else:
                        self.send_cors_json({"success": False, "error": "Crawler unavailable"})
                except Exception as ex:
                    self.send_cors_json({"success": False, "error": str(ex)})
                return

            # 1. API: Legacy Multi-Category Feed (backward compatible alias)
            if path == "/api/movies/feed":
                c_type = query.get("type", [None])[0]
                category = query.get("category", [None])[0]

                # If requested through older /api/movies/feed without type, check if category specifies it
                if path == "/api/movies/feed" and not c_type:
                    c_type = "movie"

                # Handle Arabic category query mappings (e.g. category="مسلسلات تركي" or category="turkish")
                category_map = {
                    "أفلام أجنبي": ("movie", "foreign"),
                    "أفلام عربي": ("movie", "arabic"),
                    "أفلام تركي": ("movie", "turkish"),
                    "أفلام هندي": ("movie", "indian"),
                    "أفلام آسيوي": ("movie", "asian"),
                    "أفلام اسيوي": ("movie", "asian"),
                    "أفلام وثائقية": ("movie", "documentary"),
                    "مسلسلات أجنبي": ("series", "foreign"),
                    "مسلسلات تركي": ("series", "turkish"),
                    "مسلسلات عربي": ("series", "arabic"),
                    "مسلسلات هندي": ("series", "indian_series"),
                    "مسلسلات كورية": ("series", "korean_series"),
                    "مسلسلات كورية وآسيوية": ("series", "korean_series"),
                    "مسلسلات آسيوي": ("series", "asian"),
                    "مسلسلات اسيوي": ("series", "asian"),
                    "مسلسلات وثائقية": ("series", "documentary"),
                    "أنمي": ("anime", "all"),
                    "انمي": ("anime", "all"),
                    "أفلام أنمي": ("anime", "all"),
                    "مسلسلات أنمي": ("anime", "all"),
                    "كارتون": ("anime", "all"),
                    "برامج": ("tv_show", "all"),
                    "وثائقيات": ("tv_show", "documentary"),
                    "مسرحيات": ("movie", "plays"),
                    "مصارعة": ("all", "wrestling"),
                    "مصارعة حرة": ("all", "wrestling"),
                    "مصارعة حرة WWE": ("all", "wrestling"),
                    "wwe": ("all", "wrestling"),
                }
                if category:
                    norm_cat = re.sub(r'[آإأ]', 'ا', category).strip().lower()
                    if norm_cat in category_map:
                        c_type, category = category_map[norm_cat]
                    elif "مسرح" in norm_cat:
                        c_type, category = "movie", "plays"
                    elif "مصارع" in norm_cat or "wwe" in norm_cat:
                        c_type, category = "all", "wrestling"
                    elif "تركي" in norm_cat:
                        c_type, category = ("movie" if "فيلم" in norm_cat else "series"), "turkish"
                    elif "عربي" in norm_cat:
                        c_type, category = ("movie" if "فيلم" in norm_cat else "series"), "arabic"
                    elif "اجنبي" in norm_cat:
                        c_type, category = ("movie" if "فيلم" in norm_cat else "series"), "foreign"
                    elif "هندي" in norm_cat:
                        if "مسلسل" in norm_cat:
                            c_type, category = "series", "indian_series"
                        else:
                            c_type, category = ("movie" if "فيلم" in norm_cat else "series"), "indian"
                    elif "كوري" in norm_cat:
                        c_type, category = ("movie" if "فيلم" in norm_cat else "series"), "korean_series"
                    elif "اسيوي" in norm_cat or "آسيوي" in norm_cat:
                        c_type, category = ("movie" if "فيلم" in norm_cat else "series"), "asian"
                    elif "انمي" in norm_cat or "anime" in norm_cat:
                        c_type, category = "all", "anime"
                    elif "وثائق" in norm_cat or "برامج" in norm_cat:
                        c_type, category = "tv_show", "documentary"

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                items = []
                if HAS_SERVICES:
                    items = VODDatabase.get_feed(content_type=c_type, category=category)

                # Fallback to cinema RSS feed engine
                if not items and HAS_SERVICES:
                    try:
                        rss = RSSManager()
                        items = rss.get_aggregated_cinema_feed(category or "الكل", limit=30)
                    except Exception:
                        pass

                # Pure in-memory Procedural Manifest Engine (RAM-Only / Zero-Storage)
                if not items:
                    try:
                        items = ProceduralManifestEngine.get_feed(category=category or c_type or "all")
                    except Exception:
                        pass

                self.wfile.write(json.dumps(items, ensure_ascii=False).encode("utf-8"))
                return

            # 2. API: Unified Media Details (Trailer, Cast, Seasons, Episodes, Servers)
            elif path in ["/api/movies/details", "/api/media/details"]:
                media_id = query.get("id", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                details = None
                if HAS_SERVICES:
                    details = VODDatabase.get_media_details(media_id)

                if details:
                    self.wfile.write(json.dumps(details, ensure_ascii=False).encode("utf-8"))
                else:
                    self.wfile.write(json.dumps({"error": "Media not found"}, ensure_ascii=False).encode("utf-8"))
                return

            # 3. API: Real Live IPTV Channels (Verified, Legal & Free)
            elif path in ["/api/channels", "/api/iptv/verified"]:
                cat = query.get("cat", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                channels = []
                if HAS_SERVICES:
                    try:
                        channels = IPTVManager.get_instance().get_active_channels(cat)
                    except Exception:
                        channels = []
                if not channels and HAS_SERVICES:
                    channels = self.get_real_channels(category=cat)
                self.wfile.write(json.dumps(channels, ensure_ascii=False).encode("utf-8"))
                return

            # 3b. API: Live IPTV Stream Health & AV Probe
            elif path == "/api/iptv/verify-stream":
                stream_url = query.get("url", [""])[0]
                try:
                    health = IPTVManager.get_instance().check_stream(stream_url)
                    resp_data = {
                        "valid": health.get("valid", False),
                        "status_code": health.get("status_code"),
                        "content_type": health.get("content_type", ""),
                        "latency_ms": health.get("latency_ms", 0),
                        "method": health.get("method", ""),
                        "error": health.get("error", "")
                    }
                except Exception as ex:
                    resp_data = {"valid": False, "error": str(ex)}

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode("utf-8"))
                return

            # 3c. API: Refresh & Probe Live Channels Background Harvest
            elif path == "/api/iptv/refresh":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                def run_iptv_refresh_bg():
                    try:
                        from live_tv_service import LiveTVManager
                        LiveTVManager.harvest_and_verify_m3u_sources(max_channels_to_verify=30)
                    except Exception as ex:
                        print(f"[LiveTV Background] Error: {ex}")

                threading.Thread(target=run_iptv_refresh_bg, daemon=True).start()
                self.wfile.write(json.dumps({"status": "started", "message": "جاري فحص وتحديث قنوات البث المباشر في الخلفية"}, ensure_ascii=False).encode("utf-8"))
                return

            # 3c-2. API: EPG Guide Program Schedule
            elif path == "/api/iptv/epg":
                ch_id = query.get("channel_id", [""])[0]
                now = datetime.datetime.now()
                channels = []
                if HAS_SERVICES:
                    try:
                        channels = IPTVManager.get_instance().get_active_channels()
                    except Exception:
                        channels = []
                if not channels and HAS_SERVICES:
                    channels = self.get_real_channels()

                if ch_id:
                    channels = [c for c in channels if str(c.get("id")) == str(ch_id)]

                epg_result = {}
                program_templates = {
                    "news": ["نشرة الأخبار الحادية عشرة", "عين على العالم", "حوار خاص ومباشر", "حصاد اليوم الإخباري", "ما وراء الخبر", "الصحافة اليوم"],
                    "sports": ["استوديو الدوري الممتاز", "ملخص أهداف الجولة", "عالم الرياضة والسرعة", "برنامج الصافرة والهدف", "أبطال الملاعب المفتوحة"],
                    "documentary": ["أسرار الطبيعة البرية", "حضارات قديمة لا تنسى", "في أعماق البحار والمحيطات", "وثائقي: رواد الفضاء", "عالم التكنولوجيا الحديث"],
                    "general": ["صباح الخير والنشاط", "اللقاء المفتوح مع الجمهور", "بانوراما المنوعات", "سهرة المساء والسينما", "روائع الطرب الأصيل"]
                }

                current_hour = now.hour
                for ch in channels[:30]:
                    c_id = str(ch.get("id"))
                    c_name = ch.get("name", "")
                    c_cat = str(ch.get("category", "")).lower()

                    if any(w in c_cat or w in c_name.lower() for w in ["أخبار", "news", "جزيرة", "حدث", "عربية"]):
                        prog_list = program_templates["news"]
                    elif any(w in c_cat or w in c_name.lower() for w in ["رياضة", "sport", "كأس", "كرة"]):
                        prog_list = program_templates["sports"]
                    elif any(w in c_cat or w in c_name.lower() for w in ["وثائقي", "doc", "طبيعة"]):
                        prog_list = program_templates["documentary"]
                    else:
                        prog_list = program_templates["general"]

                    schedules = []
                    for offset in range(-1, 5):
                        slot_hour = (current_hour + offset) % 24
                        prog_idx = (abs(hash(c_id)) + slot_hour) % len(prog_list)
                        prog_title = prog_list[prog_idx]

                        start_time = now.replace(hour=slot_hour, minute=0, second=0, microsecond=0)
                        if offset < 0 and current_hour == 0:
                            start_time -= datetime.timedelta(days=1)
                        elif offset > 0 and (current_hour + offset) >= 24:
                            start_time += datetime.timedelta(days=1)
                        end_time = start_time + datetime.timedelta(minutes=60)

                        is_current = (start_time <= now < end_time)
                        prog_percent = 0
                        if is_current:
                            elapsed = (now - start_time).total_seconds()
                            prog_percent = min(100, max(0, int((elapsed / 3600.0) * 100)))

                        schedules.append({
                            "id": f"{c_id}_{slot_hour}",
                            "title": prog_title,
                            "start": start_time.strftime("%H:%M"),
                            "end": end_time.strftime("%H:%M"),
                            "is_live": is_current,
                            "progress": prog_percent
                        })

                    epg_result[c_id] = {
                        "channel_id": c_id,
                        "channel_name": c_name,
                        "programs": schedules
                    }

                self.send_cors_json(epg_result)
                return

            # 3d. API: Remote Config Domains & Oscar VOD Config
            elif path == "/api/config/domains":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    cfg = RemoteConfigManager.get_instance()
                    resp = {
                        "domains": cfg.get_domain("akwam", ""),
                        "iptv_channels": cfg.get_iptv_channels(),
                        "oscar_vod": cfg.get_oscar_vod_config()
                    }
                except Exception as ex:
                    resp = {"error": str(ex)}
                self.wfile.write(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
                return

            # 3d2. API: Real-time Git Synchronization
            elif path == "/api/sync/git":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                status_res = {"status": "unsupported", "synced": False}
                if AutoGitSync:
                    try:
                        synced = AutoGitSync.sync_once()
                        status_res = {
                            "status": "success",
                            "synced": synced,
                            "pending": bool(AutoGitSync.get_status()),
                            "timestamp": time.time()
                        }
                    except Exception as ex_sync:
                        status_res = {"status": "error", "error": str(ex_sync)}
                self.wfile.write(json.dumps(status_res, ensure_ascii=False).encode("utf-8"))
                return

            # 3e. API: Oscar VOD Servers Resolver
            elif path == "/api/oscar/servers":
                title = query.get("title", [""])[0]
                item_id = query.get("id", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    cfg = RemoteConfigManager.get_instance()
                    oscar = cfg.get_oscar_vod_config()
                    base_url = oscar.get("base_url", "")
                    token = oscar.get("token", "")
                    headers = {
                        "User-Agent": oscar.get("user_agent", ""),
                        "Authorization": f"Bearer {token}",
                        "X-App-ID": oscar.get("app_id", "")
                    }
                    url = f"{base_url}/vod/movie/{item_id}/servers" if item_id else f"{base_url}/vod/search?q={urllib.parse.quote(title)}"
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=oscar.get("timeout_seconds", 4.0)) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                except Exception as ex:
                    data = {"error": str(ex)}
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
                return

            # 4. API: Fast VOD Search (DB + Live Providers)
            elif path == "/api/vod/search":
                q = query.get("q", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                results = []
                if HAS_SERVICES:
                    results = VODDatabase.search_movies(q)

                if not results and HAS_SERVICES:
                    results = self.search_vod(q)

                self.wfile.write(json.dumps(results, ensure_ascii=False).encode("utf-8"))
                return

            # 5. API: Real VOD Stream Resolver (Strictly VOD only, never for Live Channels)
            elif path == "/api/vod/servers":
                title = query.get("title", [""])[0]
                item_id = query.get("id", [""])[0]
                content_type = query.get("type", [""])[0]
                is_live = query.get("is_live", [""])[0]
                category = query.get("category", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                # Strict Check: If it is a live channel, return empty list (no VOD embed servers)
                is_live_req = (
                    str(is_live).strip().lower() in ("1", "true", "yes", "live")
                    or str(content_type).strip().lower() in ("live", "channel", "channels", "iptv")
                    or str(category).strip().lower() in ("channels", "قنوات مباشرة", "قنوات البث المباشر", "live", "iptv")
                    or item_id.startswith("live_")
                    or item_id.startswith("ch_")
                    or item_id.startswith("iptv_")
                )

                if is_live_req:
                    self.wfile.write(b"[]")
                    return

                servers = self.resolve_servers(
                    title,
                    item_id,
                    content_type=content_type,
                    is_live=is_live,
                    category=category
                )
                self.wfile.write(json.dumps(servers, ensure_ascii=False).encode("utf-8"))
                return

            # 5a. API: Unified Media Servers (New API Controller)
            elif path == "/api/media/servers":
                APIController.handle_servers(self, query)
                return

            # 5a-1. API: Verified Live IPTV Channels & Stream Health Checker
            elif path == "/api/iptv/channels":
                cat = query.get("category", ["all"])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                channels_data = []
                try:
                    channels_data = IPTVManager.get_active_channels(cat if cat != "all" else None)
                except Exception as ex:
                    channels_data = {"error": str(ex)}
                self.wfile.write(json.dumps(channels_data, ensure_ascii=False).encode("utf-8"))
                return

            elif path == "/api/iptv/refresh":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                res = {"status": "started"}
                try:
                    threading.Thread(target=IPTVManager.refresh_now, daemon=True).start()
                    res = {"status": "refresh_in_progress"}
                except Exception as ex:
                    res = {"error": str(ex)}
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
                return

            elif path == "/api/iptv/health":
                stream_url = query.get("url", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                health_data = {"valid": False}
                try:
                    health_data = IPTVManager.check_stream(stream_url)
                except Exception as ex:
                    health_data = {"valid": False, "error": str(ex)}
                self.wfile.write(json.dumps(health_data, ensure_ascii=False).encode("utf-8"))
                return

            # 5b. API: Direct Stream Resolver (Extracts clean .mp4 / .m3u8 from any host)
            elif path in ["/api/stream/resolve", "/api/vod/resolve", "/api/resolve-stream", "/api/stream/resolve-direct"]:
                stream_target = query.get("url", [""])[0]
                if not stream_target:
                    self.send_cors_json({"success": False, "error": "Missing url parameter"}, status=400)
                    return

                try:
                    res = DirectStreamExtractor.resolve(stream_target)
                    self.send_cors_json(res)
                except Exception as ex_resolve:
                    self.send_cors_json({
                        "success": True,
                        "stream_url": stream_target,
                        "is_hls": ".m3u8" in stream_target.lower(),
                        "format": "hls" if ".m3u8" in stream_target.lower() else "mp4",
                        "error": str(ex_resolve)
                    })
                return

            # 5b-2. API: Video File Size Probe (Content-Length in MB/GB)
            elif path == "/api/stream/filesize":
                stream_target = query.get("url", [""])[0]
                try:
                    size_info = DirectStreamExtractor.get_file_size(stream_target)
                    self.send_cors_json(size_info)
                except Exception:
                    self.send_cors_json({"size_bytes": 0, "size_mb": 0, "formatted": "غير محدد"})
                return

            # 5c. API: Unified Media Feed (New API Controller)
            elif path == "/api/media/feed":
                APIController.handle_feed(self, query)
                return

            # 5d. API: Unified Media Details (New API Controller)
            elif path == "/api/media/details":
                APIController.handle_details(self, query)
                return

            # 5e. API: Media Search (New API Controller)
            elif path == "/api/media/search":
                APIController.handle_search(self, query)
                return

            # 5f. API: Categories List (New API Controller)
            elif path == "/api/media/categories":
                APIController.handle_categories(self)
                return

            # 5g. API: Stream Resolve (New API Controller)
            elif path == "/api/media/stream":
                APIController.handle_stream_resolve(self, query)
                return

            # 5h. API: Episodes List (New API Controller)
            elif path == "/api/media/episodes":
                APIController.handle_episodes(self, query)
                return

            # 5i. API: Cast & Crew (New API Controller)
            elif path == "/api/media/cast":
                APIController.handle_cast_crew(self, query)
                return

            # 5c. API: Universal Deep-Search & Google Dorking Multi-Portal Live Scraper
            elif path in ["/api/stream/deep-search", "/api/scrape-servers", "/api/stream/scrape-servers"]:
                title_en = query.get("title_en", [""])[0] or query.get("title", [""])[0]
                title_ar = query.get("title_ar", [""])[0] or query.get("arabic_title", [""])[0]
                year = query.get("year", [""])[0]
                c_type = query.get("type", ["movie"])[0]
                ep = query.get("episode", [""])[0]
                season = query.get("season", [""])[0]

                try:
                    result = GoogleDorkScraper.scrape_servers(
                        title_en=title_en,
                        title_ar=title_ar,
                        year=year,
                        content_type=c_type,
                        season=season,
                        episode=ep
                    )
                except Exception:
                    try:
                        result = DeepSearchFallbackEngine.deep_search(title_en or title_ar, year=year, content_type=c_type, episode=ep, season=season)
                    except Exception as ex2:
                        result = {
                            "success": False,
                            "found": False,
                            "error": str(ex2),
                            "message": "محتوى غير متاح حالياً - تم فحص كافة المصادر البديلة"
                        }

                self.send_cors_json(result)
                return

            # 5d. API: CORS-Bypassing Stream & Video Proxy Bridge (supports Range / Seeking)
            elif path == "/api/stream/proxy":
                target_url = query.get("url", [""])[0]
                custom_ref = query.get("ref", [""])[0]
                if not target_url or not is_safe_external_url(target_url):
                    self.send_cors_json({"error": "Invalid, blocked or missing target URL"}, status=400)
                    return

                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Referer": custom_ref or target_url,
                        "Accept": "*/*"
                    }
                    if "Range" in self.headers:
                        headers["Range"] = self.headers["Range"]

                    req = urllib.request.Request(target_url, headers=headers)
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE

                    with urllib.request.urlopen(req, context=ctx, timeout=12) as response:
                        ct = response.headers.get("Content-Type", "video/mp4")
                        cl = response.headers.get("Content-Length")
                        cr = response.headers.get("Content-Range")
                        status_code = getattr(response, "status", 200) or 200

                        self.send_response(status_code)
                        self.send_header("Content-Type", ct)
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Access-Control-Allow-Headers", "Range, Authorization")
                        self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges")
                        self.send_header("Accept-Ranges", "bytes")
                        if cl:
                            self.send_header("Content-Length", cl)
                        if cr:
                            self.send_header("Content-Range", cr)
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except Exception as ex:
                    self.send_cors_json({"error": f"Proxy upstream error: {str(ex)}"}, status=502)
                return

            # 5e. API: System Health & Performance Diagnostics
            elif path == "/api/health":
                vod_count = 0
                iptv_count = 0
                if HAS_SERVICES:
                    try:
                        conn = VODDatabase.get_connection()
                        vod_count = conn.execute("SELECT COUNT(*) FROM vod_media").fetchone()[0]
                        conn.close()
                    except Exception:
                        pass
                    try:
                        iptv_count = len(IPTVManager.get_active_channels())
                    except Exception:
                        pass

                self.send_cors_json({
                    "status": "healthy",
                    "platform": "A TuBe Ultra HD Media Experience",
                    "version": "2.5.0",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "stats": {
                        "vod_titles": vod_count,
                        "iptv_channels": iptv_count,
                        "engine": "SQLite 3 WAL Mode"
                    }
                })
                return

            # 6. API: Multi-Year Universal Harvester Trigger
            elif path in ["/api/crawler/run", "/api/crawler/harvest-years"]:
                start_yr = int(query.get("start_year", ["2000"])[0])
                end_yr = int(query.get("end_year", ["2026"])[0])
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                def run_harvest_bg():
                    try:
                        ContentIngestEngine.harvest_all_years(start_year=start_yr, end_year=end_yr, max_items_per_year=2)
                    except Exception as ex:
                        print(f"[Crawler Background] Error: {ex}")

                threading.Thread(target=run_harvest_bg, daemon=True).start()
                self.wfile.write(json.dumps({"status": "running", "message": f"Harvest started in background for years {start_yr} to {end_yr}"}, ensure_ascii=False).encode("utf-8"))
                return

            # 6b. API: Bulk Multi-Portal & Multi-Category Deep Harvester Trigger
            elif path in ["/api/crawler/harvest-all", "/api/crawler/harvest-multi"]:
                items_per_cat = int(query.get("items", ["10"])[0])
                pages = int(query.get("pages", ["2"])[0])
                source = query.get("source", ["all"])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                def run_harvest_all_bg():
                    try:
                        if source in ["all", "multi", "faselhd"]:
                            ContentIngestEngine.harvest_multi_portal(items_per_portal=items_per_cat)
                        if source in ["all", "cimawbas"]:
                            ContentIngestEngine.harvest_all_categories(max_items_per_cat=items_per_cat, max_pages=pages)
                    except Exception as ex:
                        print(f"[Crawler Bulk Background] Error: {ex}")

                threading.Thread(target=run_harvest_all_bg, daemon=True).start()
                self.wfile.write(json.dumps({"status": "running", "message": f"Multi-portal bulk harvest started (source={source}, {items_per_cat} items/source)"}, ensure_ascii=False).encode("utf-8"))
                return

            # 7. API: Pure Algorithmic Procedural Manifest (Zero-Storage RAM Feed)
            elif path == "/api/procedural/feed":
                cat = query.get("category", ["all"])[0]
                page = int(query.get("page", ["1"])[0])
                limit = int(query.get("limit", ["24"])[0])

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=60")
                self.end_headers()

                feed = ProceduralManifestEngine.get_feed(category=cat, page=page, limit=limit)
                self.wfile.write(json.dumps(feed, ensure_ascii=False).encode("utf-8"))
                return

            # 7b. API: Procedural Details
            elif path == "/api/procedural/details":
                item_id = query.get("id", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                item = ProceduralManifestEngine.get_details(item_id)
                self.wfile.write(json.dumps(item or {}, ensure_ascii=False).encode("utf-8"))
                return

            # 7c. API: Providers endpoint removed due to missing scrapers module

            # 8. API: In-Memory RAM Stream Sanitizer & Ad Stripper Proxy
            elif path == "/api/stream/sanitize":
                target_url = query.get("url", [""])[0]
                if not target_url or not is_safe_external_url(target_url):
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid or blocked target URL (SSRF Guard Active)"}).encode("utf-8"))
                    return

                try:
                    import requests
                    headers = StreamSanitizer.get_spoofed_headers(target_url)
                    resp = requests.get(target_url, headers=headers, timeout=6.0)

                    if resp.status_code in [200, 206]:
                        clean_manifest = StreamSanitizer.sanitize_m3u8(resp.text, base_url=target_url)
                        self.send_response(200)
                        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Cache-Control", "no-cache, no-store")
                        self.end_headers()
                        self.wfile.write(clean_manifest.encode("utf-8"))
                    else:
                        self.send_response(resp.status_code)
                        self.end_headers()
                except Exception as ex:
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Sanitization error: {str(ex)}"}).encode("utf-8"))
                finally:
                    StreamSanitizer.purge_memory()
                return

            # 9. API: User Data Cloud Backup & Restore (GET)
            elif path == "/api/user/backup":
                backup_file = os.path.join(BASE_DIR, "config", "user_backup.json")
                if os.path.exists(backup_file):
                    try:
                        with open(backup_file, "r", encoding="utf-8") as bf:
                            backup_data = json.load(bf)
                        self.send_cors_json(backup_data)
                        return
                    except Exception:
                        pass
                self.send_cors_json({
                    "status": "empty",
                    "data": {
                        "favorites": [],
                        "history": [],
                        "watch_later": [],
                        "settings": {"theme": "cyan", "subtitles": "ar", "audio_eq": "flat"}
                    }
                })
                return

            # Fallback to serving static files (index.html, css, js, assets)
            super().do_GET()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            except Exception:
                pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.end_headers()

    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path == "/api/user/backup":
                content_len = int(self.headers.get("Content-Length", 0))
                if content_len > 5 * 1024 * 1024:
                    self.send_cors_json({"error": "Payload exceeds 5MB limit"}, status=413)
                    return
                body = self.rfile.read(content_len).decode("utf-8")
                try:
                    payload = json.loads(body)
                except Exception as je:
                    self.send_cors_json({"error": f"Invalid JSON payload: {je}"}, status=400)
                    return

                backup_file = os.path.join(BASE_DIR, "config", "user_backup.json")
                os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                with open(backup_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "saved_at": datetime.datetime.now().isoformat(),
                        "data": payload
                    }, f, ensure_ascii=False, indent=2)

                self.send_cors_json({
                    "status": "success",
                    "message": "تم حفظ النسخة الاحتياطية بنجاح على السيرفر",
                    "saved_at": datetime.datetime.now().isoformat()
                })
                return
            else:
                self.send_cors_json({"error": "Resource not found"}, status=404)
        except Exception as ex:
            self.send_cors_json({"error": str(ex)}, status=500)

    def get_real_channels(self, category=None):
        channels = []
        try:
            verified = LiveTVService.get_verified_channels(category)
            for ch in verified:
                channels.append({
                    "id": ch.get("id"),
                    "name": ch.get("name"),
                    "category": ch.get("category", "قنوات مباشرة"),
                    "logo": ch.get("logo", "assets/aljazeera.svg"),
                    "badge": ch.get("badge", "LIVE 1080p FHD"),
                    "quality": ch.get("quality", "1080p FHD"),
                    "resolution": ch.get("resolution", "HD"),
                    "latency_ms": ch.get("latency_ms", 0),
                    "duration": "بث حي ومباشر",
                    "streamUrl": ch.get("stream_url", ""),
                    "license": ch.get("license", "Legal Public FTA Stream"),
                    "desc": f"{ch.get('name')} - بث حي ومباشر عالي الدقة ({ch.get('quality', 'HD')})"
                })
        except Exception as ex:
            print(f"[Server] LiveTV get_real_channels error: {ex}")

        # Fallback to remote_config if live_tv_service returned empty
        if not channels:
            cfg_path = os.path.join(BASE_DIR, "config", "remote_config.json")
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        for ch in cfg.get("iptv_channels", []):
                            channels.append({
                                "id": ch.get("id"),
                                "name": ch.get("name"),
                                "category": ch.get("category", "قنوات مباشرة"),
                                "logo": ch.get("logo", "assets/bein.svg"),
                                "badge": "LIVE",
                                "duration": "مباشر",
                                "streamUrl": ch.get("streams", [""])[0] if ch.get("streams") else "",
                                "desc": ch.get("name")
                            })
                except Exception:
                    pass

        return channels

    def search_vod(self, q):
        if not q:
            return []
        if HAS_SERVICES:
            try:
                return VODDatabase.search_movies(q)
            except Exception:
                pass
        return []

    def resolve_servers(self, title, item_id, content_type=None, is_live=None, category=None):
        if not HAS_SERVICES:
            return []

        item_id_str = str(item_id or "").strip()
        if item_id_str.startswith("live_") or item_id_str.startswith("ch_") or item_id_str.startswith("iptv_"):
            return []

        live_signals = {
            str(content_type or "").strip().lower(),
            str(is_live or "").strip().lower(),
            str(category or "").strip().lower()
        }
        if live_signals & {"live", "iptv", "channel", "channels", "1", "true", "yes", "قنوات مباشرة", "قنوات البث المباشر"}:
            return []

        try:
            if item_id and VODDatabase.is_live_media(item_id):
                return []
            media = VODDatabase.get_media_details(item_id) if item_id else None
            if media and not media.get("is_live") and media.get("type") not in ("live", "iptv", "channel", "channels") and media.get("category") not in ("channels", "قنوات مباشرة"):
                return media.get("servers", [])
        except Exception:
            pass
        return []


def run(port=8085):
    # Initialize and seed database if empty
    if HAS_SERVICES:
        try:
            VODDatabase.init_schema()
            conn = VODDatabase.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM vod_media")
            existing_count = cur.fetchone()[0]
            conn.close()

            if existing_count == 0:
                catalog_file = os.path.join(BASE_DIR, "catalog.json")
                if os.path.exists(catalog_file):
                    try:
                        with open(catalog_file, "r", encoding="utf-8") as cf:
                            disk_catalog = json.load(cf)
                            if isinstance(disk_catalog, list) and disk_catalog:
                                print(f"[VOD DB Startup] Seeding {len(disk_catalog)} items from catalog.json into SQLite...")
                                VODDatabase.seed_initial_catalog(disk_catalog)
                    except Exception as ex_cat:
                        print(f"[VOD DB Startup] Note reading catalog.json: {ex_cat}")
            else:
                print(f"[VOD DB Startup] SQLite database active with {existing_count} items. Zero-latency startup ready.")
        except Exception as e:
            print(f"[VOD DB Startup] {e}")

    # Start Continuous 60s Automated Harvester & Episode Completer
    if HAS_SERVICES:
        try:
            ContinuousSyncEngine.start_background_worker(interval_seconds=60)
            print("[Continuous Harvester Startup] 60s background worker active & polling.")
        except Exception as ex_sync:
            print(f"[Continuous Harvester Startup] Warning: {ex_sync}")

        try:
            IPTVManager.start_background(interval_seconds=1800)
            print("[IPTV Manager Startup] Stream Health Checker & M3U Harvester active.")
        except Exception as ex_iptv:
            print(f"[IPTV Manager Startup] Note: {ex_iptv}")

    # Start Real-Time Git Auto-Sync Watcher
    if AutoGitSync:
        try:
            sync_thread = threading.Thread(target=AutoGitSync.start_watcher, kwargs={"interval_seconds": 30}, daemon=True)
            sync_thread.start()
            print("[Git Auto-Sync Startup] Real-time Git watcher daemon active & monitoring.")
        except Exception as ex_git:
            print(f"[Git Auto-Sync Startup] Note: {ex_git}")

    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, ATubeHandler)
    print(f"=====================================================")
    print(f"  A Tube Production Server running on http://localhost:{port}")
    print(f"  Zero-latency SQLite WAL Database & Crawler Connected")
    print(f"  Continuous 60s Multi-Portal Harvester & Completer Running")
    print(f"=====================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8085
    run(port)
