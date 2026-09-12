# -*- coding: utf-8 -*-
"""
IPTV Manager - Legal Open-Source M3U/M3U8 Playlist Harvester & Verifier
==========================================================================
Manages legal, free-to-air (FTA) and open-source M3U playlists (e.g. iptv-org)
with a fallback sources array. Parses EXTINF / tvg-logo / group-title metadata,
verifies stream health asynchronously using asyncio.to_thread + requests
(no aiohttp dependency), performs Arabic/English title matching across sources
to find alternatives for the same logical channel, filters dead links, persists
verified channels to a standalone SQLite DB (config/iptv_channels.sqlite), and
exposes a JSON surface (id, name, logo, category, current_stream_url, status).

Usable from server.py:
    from iptv_manager import IPTVManager
    IPTVManager.get_active_channels(category)
    IPTVManager.refresh_now()
    IPTVManager.start_background(interval_seconds)
    IPTVManager.stop_background()
    IPTVManager.check_stream(stream_url)
    IPTVManager.parse_m3u_text(text, source_name)
"""

import os
import sys
import re
import json
import time
import uuid
import sqlite3
import asyncio
import hashlib
import threading
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except Exception as _req_err:  # pragma: no cover - hard dependency
    requests = None
    _REQUESTS_IMPORT_ERROR = _req_err
else:
    _REQUESTS_IMPORT_ERROR = None

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_DIR = os.path.join(_BASE_DIR, "config")
DB_PATH = os.path.join(_CONFIG_DIR, "iptv_channels.sqlite")
_CACHE_FILE = os.path.join(_CONFIG_DIR, "iptv_verified_cache.json")

# ---------------------------------------------------------------------------
# Legal open / free-to-air M3U sources with fallback ordering
# ---------------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    "Origin": "http://localhost:8085",
    "Referer": "http://localhost:8085/",
}

# Primary legal OSS M3U sources; each may declare fallback_sources that are
# tried when the primary source fails.
LEGAL_M3U_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "iptv-org Arab World",
        "url": "https://iptv-org.github.io/iptv/regions/arab.m3u",
        "category_default": "قنوات عربية",
        "fallback_sources": [
            "https://raw.githubusercontent.com/iptv-org/iptv/master/regions/arab.m3u",
            "https://iptv-org.github.io/iptv/countries/za.m3u",
        ],
    },
    {
        "name": "iptv-org Arabic Language",
        "url": "https://iptv-org.github.io/iptv/languages/ara.m3u",
        "category_default": "قنوات عربية",
        "fallback_sources": [
            "https://raw.githubusercontent.com/iptv-org/iptv/master/languages/ara.m3u",
        ],
    },
    {
        "name": "iptv-org Egypt",
        "url": "https://iptv-org.github.io/iptv/countries/eg.m3u",
        "category_default": "قنوات مصرية",
        "fallback_sources": [
            "https://raw.githubusercontent.com/iptv-org/iptv/master/countries/eg.m3u",
        ],
    },
    {
        "name": "iptv-org Saudi Arabia",
        "url": "https://iptv-org.github.io/iptv/countries/sa.m3u",
        "category_default": "قنوات سعودية",
        "fallback_sources": [
            "https://raw.githubusercontent.com/iptv-org/iptv/master/countries/sa.m3u",
        ],
    },
    {
        "name": "iptv-org UAE",
        "url": "https://iptv-org.github.io/iptv/countries/ae.m3u",
        "category_default": "قنوات إماراتية",
        "fallback_sources": [
            "https://raw.githubusercontent.com/iptv-org/iptv/master/countries/ae.m3u",
        ],
    },
    {
        "name": "iptv-org Iraq",
        "url": "https://iptv-org.github.io/iptv/countries/iq.m3u",
        "category_default": "قنوات عراقية",
        "fallback_sources": [
            "https://raw.githubusercontent.com/iptv-org/iptv/master/countries/iq.m3u",
        ],
    },
    {
        "name": "iptv-org Gulf",
        "url": "https://iptv-org.github.io/iptv/countries/qa.m3u",
        "category_default": "قنوات خليجية",
        "fallback_sources": [
            "https://raw.githubusercontent.com/iptv-org/iptv/master/countries/qa.m3u",
        ],
    },
    {
        "name": "iptv-org Religious",
        "url": "https://iptv-org.github.io/iptv/categories/religious.m3u",
        "category_default": "إسلامية ودينية",
        "fallback_sources": [
            "https://raw.githubusercontent.com/iptv-org/iptv/master/categories/religious.m3u",
        ],
    },
]

# Hard-coded fallback seeds kept available for offline bootstrap / verification.
CURATED_SEEDS: List[Dict[str, Any]] = [
    {
        "id": "france24_ar",
        "name": "فرانس 24 العربية HD",
        "category": "الأخبار",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/France_24_logo.svg/512px-France_24_logo.svg.png",
        "stream_url": "https://static.france24.com/live/F24_AR_HI_HLS/live_tv.m3u8",
        "quality": "1080p FHD",
    },
    {
        "id": "dw_arabic",
        "name": "DW عربية HD",
        "category": "الأخبار",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Deutsche_Welle_logo.svg/512px-Deutsche_Welle_logo.svg.png",
        "stream_url": "https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/index.m3u8",
        "quality": "1080p FHD",
    },
]

# Mapping of English group-title keywords to Arabic categories, mirroring
# the conventions used by live_tv_service / server.py.
_EN_GROUP_MAP = {
    "news": "الأخبار",
    "sports": "الرياضة",
    "documentary": "الوثائقيات",
    "general": "قنوات عامة",
    "entertainment": "منوعات وترفيه",
    "movies": "أفلام ومسلسلات",
    "series": "أفلام ومسلسلات",
    "kids": "أطفال",
    "animation": "أطفال",
    "music": "موسيقى",
    "religious": "إسلامية ودينية",
}

_EXTINF_RE = {
    "logo": re.compile(r'tvg-logo="([^"]+)"'),
    "group": re.compile(r'group-title="([^"]+)"'),
    "id": re.compile(r'tvg-id="([^"]*)"'),
}


def _safe_log(msg: str) -> None:
    try:
        print(msg)
    except Exception:
        pass


def _normalize_key(text: str) -> str:
    """Normalize channel names for Arabic/English cross-source matching."""
    if not text:
        return ""
    t = text.strip().lower()
    # Normalize Arabic letters to a canonical form.
    t = re.sub(r"[إأٱآ]", "ا", t)
    t = re.sub(r"[ه]", "ة", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[().\-]", "", t)
    t = re.sub(r"\d+p\b", "", t)
    # Keep only alphanumerics (Arabic + Latin) for comparison.
    t = re.sub(r"[^\w\u0600-\u06ff ]", "", t, flags=re.UNICODE)
    return t.strip()


def _content_type_is_hls(content_type: str) -> bool:
    ct = (content_type or "").lower().strip()
    return (
        "mpegurl" in ct
        or "m3u8" in ct
        or "application/x-mpegurl" in ct
        or "application/vnd.apple.mpegurl" in ct
    )


class IPTVManager:
    """
    Verifies legal open-source M3U playlists and persists healthy channels to
    a dedicated SQLite database (config/iptv_channels.sqlite).
    """

    _initialized = False
    _bg_task: Optional[asyncio.Task] = None
    _bg_running = False
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _cache_lock = asyncio.Lock()
    _thread_pool: Optional[ThreadPoolExecutor] = None

    @classmethod
    def get_instance(cls):
        return cls

    # ------------------------------------------------------------------
    # Initialization / schema
    # ------------------------------------------------------------------
    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    @classmethod
    def _init_db(cls) -> None:
        if cls._initialized:
            return
        try:
            conn = cls._get_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS iptv_channels (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    logo TEXT,
                    category TEXT,
                    current_stream_url TEXT,
                    status TEXT,
                    quality TEXT,
                    verified_at REAL,
                    last_checked REAL,
                    source TEXT,
                    UNIQUE(current_stream_url)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_iptv_cat ON iptv_channels(category);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_iptv_status ON iptv_channels(status);")
            conn.commit()
            conn.close()
        except Exception as e:
            _safe_log(f"[IPTVManager] DB init error: {e}")
        cls._initialized = True

    # ------------------------------------------------------------------
    # M3U parsing
    # ------------------------------------------------------------------
    @classmethod
    def parse_m3u_text(cls, text: str, source_name: str = "unknown") -> List[Dict[str, Any]]:
        """
        Parse raw M3U text, extracting EXTINF metadata including tvg-logo
        and group-title. Returns structured channel dicts.
        """
        channels: List[Dict[str, Any]] = []
        if not text or "#EXTM3U" not in text:
            return channels

        lines = text.splitlines()
        current_meta: Optional[Dict[str, Any]] = None

        for line in lines:
            raw = line.strip()
            if not raw or raw.startswith("#EXTM3U"):
                continue

            if raw.startswith("#EXTINF"):
                current_meta = {"source": source_name}
                logo_m = _EXTINF_RE["logo"].search(raw)
                if logo_m:
                    current_meta["logo"] = logo_m.group(1)
                id_m = _EXTINF_RE["id"].search(raw)
                if id_m and id_m.group(1):
                    current_meta["_tvg_id"] = id_m.group(1)
                group_m = _EXTINF_RE["group"].search(raw)
                if group_m:
                    raw_group = group_m.group(1)
                    mapped = _EN_GROUP_MAP.get(raw_group.lower().strip())
                    current_meta["category"] = mapped or raw_group
                else:
                    current_meta["category"] = "قنوات عامة"

                comma_idx = raw.rfind(",")
                if comma_idx != -1:
                    raw_name = raw[comma_idx + 1:].strip()
                else:
                    raw_name = ""
                clean_name = re.sub(r"\(\d+p\)|\[.*?\]", "", raw_name).strip()
                current_meta["name"] = clean_name or raw_name or "قناة فضائية"

            elif current_meta is not None and (raw.startswith("http://") or raw.startswith("https://")):
                current_meta["stream_url"] = raw
                h = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
                current_meta["id"] = f"live_{h}"
                if not current_meta.get("logo"):
                    current_meta["logo"] = "https://i.imgur.com/8apNaLP.png"
                current_meta.setdefault("quality", "HD")
                channels.append(current_meta)
                current_meta = None

        return channels

    # ------------------------------------------------------------------
    # Stream verification
    # ------------------------------------------------------------------
    @classmethod
    def _do_head(cls, url: str, timeout: float) -> Optional[requests.Response]:
        try:
            return requests.head(
                url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True
            )
        except Exception:
            return None

    @classmethod
    def _do_get(cls, url: str, timeout: float) -> Optional[requests.Response]:
        try:
            return requests.get(
                url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True, stream=True
            )
        except Exception:
            return None

    @classmethod
    def _probe_url(cls, url: str, timeout: float = 4.0) -> Tuple[bool, str, str]:
        """
        HEAD the URL first, then fall back to GET when content-type is
        ambiguous. Verifies HTTP 200/206, HLS content-type, or m3u8/#EXTM3U
        payload when no clear content-type is present.
        """
        if not url or not url.startswith(("http://", "https://")):
            return False, "invalid_url", "Unknown"

        status_code = 0
        content_type = ""
        sample = b""

        head_ok = False
        try:
            r = cls._do_head(url, timeout=timeout)
            if r is not None:
                status_code = r.status_code
                content_type = r.headers.get("Content-Type", "").lower()
                head_ok = True
        except Exception:
            head_ok = False

        if status_code in (200, 206):
            if _content_type_is_hls(content_type):
                return True, "hls", "HD"
            # No clear content-type: accept if URL ends with .m3u8 or .m3u
            if url.lower().endswith((".m3u8", ".m3u")):
                return True, "hls", "HD"
            # Do a GET and inspect payload for #EXTM3U / m3u8 markers
            r = cls._do_get(url, timeout=timeout)
            if r is not None:
                try:
                    sample = r.raw.read(8192) if r.raw else r.content[:8192]
                except Exception:
                    sample = r.content[:8192] if hasattr(r, "content") else b""
                text = sample.decode("utf-8", errors="ignore")
                if "#EXTM3U" in text or ".m3u8" in text.lower() or "mpegurl" in text.lower():
                    return True, "hls", "HD"
                if _content_type_is_hls(content_type):
                    return True, "hls", "HD"
            return False, f"HTTP {status_code}", "Unknown"

        # HEAD failed or non-200/206: try GET directly
        if not head_ok:
            r = cls._do_get(url, timeout=timeout)
            if r is None:
                return False, "connection_failed", "Unknown"
            status_code = r.status_code
            content_type = r.headers.get("Content-Type", "").lower()
            try:
                sample = r.raw.read(8192) if r.raw else r.content[:8192]
            except Exception:
                sample = r.content[:8192] if hasattr(r, "content") else b""

            if status_code in (200, 206):
                if _content_type_is_hls(content_type):
                    return True, "hls", "HD"
                text = sample.decode("utf-8", errors="ignore")
                if "#EXTM3U" in text or ".m3u8" in text.lower() or "mpegurl" in text.lower():
                    return True, "hls", "HD"
                if url.lower().endswith((".m3u8", ".m3u")):
                    return True, "hls", "HD"
            return False, f"HTTP {status_code}", "Unknown"

        return False, f"HTTP {status_code}", "Unknown"

    @classmethod
    def check_stream(cls, stream_url: str, timeout: float = 4.0) -> Dict[str, Any]:
        """
        Public single-stream health check. Returns a JSON-friendly dict.
        """
        ok, label, quality = cls._probe_url(stream_url, timeout=timeout)
        return {
            "url": stream_url,
            "status": "online" if ok else "offline",
            "healthy": ok,
            "detail": label,
            "quality": quality,
            "checked_at": time.time(),
        }

    @classmethod
    async def _check_channel_async(cls, channel: Dict[str, Any], sem: asyncio.Semaphore) -> Optional[Dict[str, Any]]:
        async with sem:
            ok, label, quality = await asyncio.to_thread(cls._probe_url, channel.get("stream_url", ""), 4.0)
            if not ok:
                return None
            out = {
                "id": channel.get("id") or f"live_{hashlib.md5(channel.get('stream_url','').encode('utf-8')).hexdigest()[:8]}",
                "name": channel.get("name", "قناة فضائية"),
                "logo": channel.get("logo") or "https://i.imgur.com/8apNaLP.png",
                "category": channel.get("category", "قنوات عامة"),
                "current_stream_url": channel.get("stream_url"),
                "status": "online",
                "quality": quality,
                "verified_at": time.time(),
                "last_checked": time.time(),
                "source": channel.get("source", "unknown"),
            }
            return out

    # ------------------------------------------------------------------
    # Sources fetching
    # ------------------------------------------------------------------
    @classmethod
    def _fetch_source(cls, url: str, timeout: float = 5.0) -> Optional[str]:
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text:
                return r.text
        except Exception:
            return None
        return None

    @classmethod
    def _gather_candidate_channels(cls, limit_per_source: int = 30) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        seen_urls: set = set()

        for src in LEGAL_M3U_SOURCES:
            text = cls._fetch_source(src["url"])
            if not text:
                text = cls._fetch_source(src.get("fallback_sources", [None])[0]) if src.get("fallback_sources") else None
            if not text:
                for fb in src.get("fallback_sources", []):
                    text = cls._fetch_source(fb)
                    if text:
                        break
            if not text:
                _safe_log(f"[IPTVManager] Source unavailable: {src['name']}")
                continue

            parsed = cls.parse_m3u_text(text, source_name=src["name"])
            count_added = 0
            for ch in parsed:
                url = ch.get("stream_url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append(ch)
                count_added += 1
                if count_added >= limit_per_source:
                    break

        # Always seed with curated live sources for offline reliability.
        for seed in CURATED_SEEDS:
            if seed["stream_url"] not in seen_urls:
                seen_urls.add(seed["stream_url"])
                candidates.append(seed)

        _safe_log(f"[IPTVManager] Candidate channels gathered: {len(candidates)}")
        return candidates

    # ------------------------------------------------------------------
    # Title matching (Arabic/English) across sources
    # ------------------------------------------------------------------
    @classmethod
    def _title_matches(cls, a: str, b: str) -> bool:
        ka, kb = _normalize_key(a), _normalize_key(b)
        if not ka or not kb:
            return False
        # Exact normalized match, or containment on either side.
        if ka == kb:
            return True
        la, lb = len(ka), len(kb)
        shorter, longer = (ka, kb) if la <= lb else (kb, ka)
        if shorter in longer and max(la, lb) >= 3:
            return True
        # Loose token overlap when both contain spaces.
        ta, tb = set(ka.split()), set(kb.split())
        common = ta & tb
        if common and len(common) >= max(1, min(len(ta), len(tb)) // 2):
            return True
        return False

    @classmethod
    def _merge_dedupe(cls, verified: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate verified channels by Arabic/English title match across
        sources, keeping the first healthy URL per logical channel.
        """
        merged: List[Dict[str, Any]] = []
        for ch in verified:
            existing = None
            for m in merged:
                if (
                    m.get("current_stream_url") == ch.get("current_stream_url")
                    or cls._title_matches(m.get("name", ""), ch.get("name", ""))
                ):
                    existing = m
                    break
            if existing is None:
                merged.append(ch)
            else:
                # Prefer higher quality / more recent verification.
                if ch.get("quality") == "1080p FHD" and existing.get("quality") != "1080p FHD":
                    existing["quality"] = ch["quality"]
                    existing["current_stream_url"] = ch["current_stream_url"]
                    existing["source"] = ch.get("source", existing.get("source"))
        return merged

    # ------------------------------------------------------------------
    # Verification pipeline
    # ------------------------------------------------------------------
    @classmethod
    def _verify_all(cls, max_concurrent: int = 25) -> List[Dict[str, Any]]:
        if not _REQUESTS_AVAILABLE():
            raise RuntimeError(f"requests library not available: {_REQUESTS_IMPORT_ERROR}")

        candidates = cls._gather_candidate_channels()
        if not candidates:
            return []

        async def _run() -> List[Dict[str, Any]]:
            sem = asyncio.Semaphore(max_concurrent)
            tasks = [cls._check_channel_async(ch, sem) for ch in candidates]
            results = await asyncio.gather(*tasks)
            return [r for r in results if r is not None]

        try:
            running = asyncio.get_event_loop()
            if running.is_running():
                results = asyncio.run_coroutine_threadsafe(
                    _run(), cls._get_loop()
                ).result()
            else:
                results = asyncio.run(_run())
        except Exception:
            # Fallback: run in a dedicated thread with a fresh loop.
            results = cls._run_in_thread_loop(_run)

        merged = cls._merge_dedupe(results)
        merged.sort(key=lambda c: (c.get("category", ""), c.get("name", "")))
        _safe_log(f"[IPTVManager] Verified & merged channels: {len(merged)}")
        return merged

    @classmethod
    def _get_loop(cls) -> asyncio.AbstractEventLoop:
        if cls._loop is None or cls._loop.is_closed():
            cls._loop = asyncio.new_event_loop()
            threading.Thread(target=cls._loop.run_forever, daemon=True).start()
        return cls._loop

    @classmethod
    def _run_in_thread_loop(cls, coro_factory) -> List[Dict[str, Any]]:
        import threading

        result_holder: List[Dict[str, Any]] = []
        exc_holder: List[BaseException] = []

        def _runner():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result_holder.extend(loop.run_until_complete(coro_factory()))
            except Exception as e:
                exc_holder.append(e)

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join(timeout=120)
        if exc_holder:
            _safe_log(f"[IPTVManager] verify runner error: {exc_holder[0]}")
        return result_holder

    # ------------------------------------------------------------------
    # Persistence (SQLite + JSON cache)
    # ------------------------------------------------------------------
    @classmethod
    def _persist(cls, channels: List[Dict[str, Any]]) -> None:
        cls._init_db()
        try:
            conn = cls._get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM iptv_channels;")
            now = time.time()
            for ch in channels:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO iptv_channels
                        (id, name, logo, category, current_stream_url, status,
                         quality, verified_at, last_checked, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ch.get("id"),
                        ch.get("name"),
                        ch.get("logo"),
                        ch.get("category"),
                        ch.get("current_stream_url"),
                        ch.get("status", "online"),
                        ch.get("quality", "HD"),
                        now,
                        now,
                        ch.get("source", "unknown"),
                    ),
                )
            conn.commit()
            conn.close()
        except Exception as e:
            _safe_log(f"[IPTVManager] persist error: {e}")

        # JSON cache for zero-dependency consumers (server.py fallback path).
        try:
            os.makedirs(_CONFIG_DIR, exist_ok=True)
            with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(channels, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def _load_cache(cls) -> List[Dict[str, Any]]:
        # Prefer SQLite.
        cls._init_db()
        try:
            conn = cls._get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, name, logo, category, current_stream_url, status, quality, verified_at "
                "FROM iptv_channels WHERE status='online'"
            )
            rows = cur.fetchall()
            conn.close()
            if rows:
                return [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "logo": r["logo"],
                        "category": r["category"],
                        "current_stream_url": r["current_stream_url"],
                        "stream_url": r["current_stream_url"],
                        "streamUrl": r["current_stream_url"],
                        "status": r["status"],
                        "quality": r["quality"],
                    }
                    for r in rows
                ]
        except Exception as e:
            _safe_log(f"[IPTVManager] cache load (sqlite) error: {e}")

        # Fallback to JSON cache.
        if os.path.exists(_CACHE_FILE):
            try:
                with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        return data
            except Exception:
                pass

        # Fallback to data/verified_live_channels.json
        verified_path = os.path.join(_BASE_DIR, "data", "verified_live_channels.json")
        if os.path.exists(verified_path):
            try:
                with open(verified_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        out = []
                        for ch in data:
                            out.append({
                                "id": ch.get("id"),
                                "name": ch.get("name"),
                                "logo": ch.get("logo"),
                                "category": ch.get("category"),
                                "current_stream_url": ch.get("stream_url") or ch.get("current_stream_url"),
                                "status": ch.get("status", "online"),
                                "quality": ch.get("quality", "1080p FHD")
                            })
                        try:
                            cls._persist(out)
                        except Exception:
                            pass
                        return out
            except Exception:
                pass
        return []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def _REQUESTS_AVAILABLE(cls) -> bool:
        return requests is not None

    @classmethod
    def get_active_channels(cls, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return verified, online channels (JSON surface: id, name, logo,
        category, current_stream_url, status), optionally filtered by category.
        """
        channels = cls._load_cache()
        if category and category not in ("all", "الكل", "", None):
            channels = [c for c in channels if c.get("category") == category]
        return channels

    @classmethod
    def refresh_now(cls, max_concurrent: int = 25, limit_per_source: int = 30) -> List[Dict[str, Any]]:
        """
        Synchronous end-to-end refresh: fetch sources, verify streams, dedupe,
        persist, and return the active channel list.
        """
        channels = cls._verify_all(max_concurrent=max_concurrent)
        cls._persist(channels)
        return cls.get_active_channels()

    # ------------------------------------------------------------------
    # Background refresh lifecycle
    # ------------------------------------------------------------------
    @classmethod
    def _bg_loop(cls, interval_seconds: int, stop_event: threading.Event) -> None:
        _safe_log(f"[IPTVManager] Background refresh started (interval={interval_seconds}s)")
        # Run an immediate first pass.
        try:
            cls.refresh_now()
        except Exception as e:
            _safe_log(f"[IPTVManager] bg first pass error: {e}")
        while not stop_event.wait(timeout=interval_seconds):
            try:
                cls.refresh_now()
            except Exception as e:
                _safe_log(f"[IPTVManager] bg refresh error: {e}")
        _safe_log("[IPTVManager] Background refresh stopped")

    _bg_thread: Optional[threading.Thread] = None
    _bg_stop_event: Optional[threading.Event] = None

    @classmethod
    def start_background(cls, interval_seconds: int = 300) -> bool:
        """Start a cancellable background refresh worker."""
        if cls._bg_thread is not None and cls._bg_thread.is_alive():
            return False
        cls._bg_stop_event = threading.Event()
        cls._bg_thread = threading.Thread(
            target=cls._bg_loop,
            args=(max(interval_seconds, 30), cls._bg_stop_event),
            daemon=True,
        )
        cls._bg_thread.start()
        return True

    @classmethod
    def stop_background(cls) -> bool:
        """Signal the background worker to stop (cancellable)."""
        if cls._bg_stop_event is not None:
            cls._bg_stop_event.set()
        if cls._bg_thread is not None and cls._bg_thread.is_alive():
            cls._bg_thread.join(timeout=5)
        stopped = cls._bg_thread is None or not cls._bg_thread.is_alive()
        cls._bg_thread = None
        cls._bg_stop_event = None
        return stopped

    @classmethod
    def is_background_running(cls) -> bool:
        return cls._bg_thread is not None and cls._bg_thread.is_alive()


# Module-level guard used by _verify_all.
def _REQUESTS_AVAILABLE() -> bool:
    return requests is not None
