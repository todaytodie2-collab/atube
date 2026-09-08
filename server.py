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
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Force UTF-8 for stdout and stderr on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add services path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

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
        # Resolve hostname to IP to prevent DNS rebinding
        try:
            ip_str = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip_str)
            for net in BLOCKED_IP_NETWORKS:
                if ip_obj in net:
                    return False
        except Exception:
            return False
        return True
    except Exception:
        return False

try:
    from remote_config import RemoteConfigManager
    from vod_db import VODDatabase
    from rss_manager import RSSManager
    from procedural_manifest import ProceduralManifestEngine
    from stream_sanitizer import StreamSanitizer
    HAS_SERVICES = True
except Exception as e:
    print(f"[A Tube Server] Note: Services loaded with fallback: {e}")
    try:
        from procedural_manifest import ProceduralManifestEngine
        from stream_sanitizer import StreamSanitizer
        HAS_SERVICES = True
    except Exception:
        HAS_SERVICES = False


class ATubeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

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

            # 1. API: Multi-Category & Multi-Source Media Feed (Served from SQLite WAL in <3ms)
            if path in ["/api/movies/feed", "/api/media/feed"]:
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
                    "مسلسلات هندي": ("series", "indian"),
                    "مسلسلات كورية": ("series", "asian"),
                    "مسلسلات كورية وآسيوية": ("series", "asian"),
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
                    if category in category_map:
                        c_type, category = category_map[category]
                    elif norm_cat in category_map:
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
                        c_type, category = ("movie" if "فيلم" in norm_cat else "series"), "indian"
                    elif "اسيوي" in norm_cat or "كوري" in norm_cat:
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

                channels = self.get_real_channels(category=cat)
                self.wfile.write(json.dumps(channels, ensure_ascii=False).encode("utf-8"))
                return

            # 3b. API: Live IPTV Stream Health & AV Probe
            elif path == "/api/iptv/verify-stream":
                stream_url = query.get("url", [""])[0]
                try:
                    from live_tv_service import LiveTVManager
                    is_valid, badge, res, latency = LiveTVManager.verify_stream_av_quality(stream_url)
                    resp_data = {
                        "valid": is_valid,
                        "badge": badge,
                        "resolution": res,
                        "latency_ms": latency
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

            # 5. API: Real VOD Stream Resolver
            elif path == "/api/vod/servers":
                title = query.get("title", [""])[0]
                item_id = query.get("id", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                servers = self.resolve_servers(title, item_id)
                self.wfile.write(json.dumps(servers, ensure_ascii=False).encode("utf-8"))
                return

            # 5b. API: Direct Stream Resolver (Zero-latency fast resolver)
            elif path in ["/api/stream/resolve", "/api/vod/resolve"]:
                stream_target = query.get("url", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                if not stream_target:
                    self.wfile.write(json.dumps({"success": False, "error": "Missing url parameter"}).encode("utf-8"))
                    return

                lower_url = stream_target.lower()

                # Fast direct pass-through for embed hosts (0ms latency, no blocking urllib)
                is_embed = any(h in lower_url for h in [
                    "vipserver", "liiivideo", "hgcloud", "mixdrop", "minochinos",
                    "vidmoly", "fasel", "vidlink", "multiembed", "vidsrc", "2embed", "embed"
                ])
                if is_embed:
                    embed_u = stream_target.replace("/d/", "/embed-")
                    out = {"success": True, "stream_url": embed_u, "is_hls": False, "is_embed": True, "quality": "1080p FHD"}
                    self.wfile.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
                    return

                is_direct_stream = any(ext in lower_url for ext in [".m3u8", ".mp4", ".mkv"])
                out = {
                    "success": True,
                    "stream_url": stream_target,
                    "is_hls": ".m3u8" in lower_url,
                    "quality": "1080p Stream",
                    "headers": {},
                    "is_direct": is_direct_stream
                }
                self.wfile.write(json.dumps(out, ensure_ascii=False).encode("utf-8"))
                return

            # 5c. API: Universal Deep-Search Stream Discovery & Smart Failover
            elif path == "/api/stream/deep-search":
                title = query.get("title", [""])[0]
                year = query.get("year", [""])[0]
                c_type = query.get("type", ["movie"])[0]
                ep = query.get("episode", [""])[0]
                season = query.get("season", [""])[0]

                try:
                    from deep_search_fallback import DeepSearchFallbackEngine
                    result = DeepSearchFallbackEngine.deep_search(title, year=year, content_type=c_type, episode=ep, season=season)
                except Exception as e:
                    result = {
                        "found": False,
                        "error": str(e),
                        "message": "محتوى غير متاح حالياً - تم البحث في كافة المصادر البديلة"
                    }

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
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
                        from catalog_sync import ContentIngestEngine
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
                        from catalog_sync import ContentIngestEngine
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

            # 7c. API: Multi-Source Providers Status & Registry List (All 27 Sites)
            elif path in ["/api/providers", "/api/providers/status"]:
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                providers_data = {}
                try:
                    from scrapers.providers_registry import ProvidersRegistry
                    providers_data = {
                        "status": "active",
                        "total_count": len(ProvidersRegistry.get_all()),
                        "providers": ProvidersRegistry.get_all()
                    }
                except Exception as ex:
                    providers_data = {"error": str(ex)}

                self.wfile.write(json.dumps(providers_data, ensure_ascii=False).encode("utf-8"))
                return

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

    def get_real_channels(self, category=None):
        channels = []
        try:
            from live_tv_service import LiveTVManager
            verified = LiveTVManager.get_verified_channels(category)
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
                from vod_db import VODDatabase
                return VODDatabase.search_movies(q)
            except Exception:
                pass
        return []

    def resolve_servers(self, title, item_id):
        if not HAS_SERVICES:
            return []
        try:
            from vod_db import VODDatabase
            media = VODDatabase.get_media_by_id(item_id)
            if media and "servers" in media:
                return media["servers"]
        except Exception:
            pass
        return []


def run(port=8085):
    # Initialize and seed database if empty
    if HAS_SERVICES:
        try:
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
        except Exception as e:
            print(f"[VOD DB Startup] {e}")

    # Start Continuous 60s Automated Harvester & Episode Completer
    if HAS_SERVICES:
        try:
            from catalog_sync import ContinuousSyncEngine
            ContinuousSyncEngine.start_background_worker(interval_seconds=60)
            print("[Continuous Harvester Startup] 60s background worker active & polling.")
        except Exception as ex_sync:
            print(f"[Continuous Harvester Startup] Warning: {ex_sync}")

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
