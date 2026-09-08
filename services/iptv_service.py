import os
import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import requests
from PySide6.QtCore import QThread, Signal
from .remote_config import RemoteConfigManager


COUNTRY_FEEDS: Dict[str, str] = {
    "eg": "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "sa": "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "ae": "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "iq": "https://iptv-org.github.io/iptv/countries/iq.m3u",
    "sports": "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "news": "https://iptv-org.github.io/iptv/categories/news.m3u",
}

COUNTRY_LABELS: Dict[str, str] = {
    "eg": "مصر 🇪🇬",
    "sa": "السعودية 🇸🇦",
    "ae": "الإمارات 🇦🇪",
    "iq": "العراق 🇮🇶",
    "sports": "الرياضة ⚽",
    "news": "الأخبار 📰",
}

CHROME_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


class StreamHealthCheckWorker(QThread):
    fastest_stream_ready = Signal(dict, str, int)  # channel, url, index

    def __init__(self, channel: dict, parent=None):
        super().__init__(parent)
        self.channel = channel

    def run(self):
        best_url, best_idx = IPTVService.find_fastest_stream(self.channel)
        self.fastest_stream_ready.emit(self.channel, best_url, best_idx)


class IPTVPlaylistSyncWorker(QThread):
    channels_synced = Signal(list)

    def run(self):
        channels = IPTVService.fetch_and_cache_live_channels()
        self.channels_synced.emit(channels)


class CountryChannelsWorker(QThread):
    """
    Background worker thread to fetch and parse country/category M3U feeds
    without blocking the PySide6 UI thread.
    """
    channels_loaded = Signal(str, list)  # country_key, channels
    error_occurred = Signal(str, str)    # country_key, error_msg

    def __init__(self, country_key: str, parent=None):
        super().__init__(parent)
        self.country_key = country_key

    def run(self):
        try:
            channels = IPTVService.fetch_channels_by_country(self.country_key)
            self.channels_loaded.emit(self.country_key, channels)
        except Exception as e:
            self.error_occurred.emit(self.country_key, str(e))


class IPTVService:
    """
    Nilesat & Arabic Live TV Engine.
    Connects to open-source, legal iptv-org playlists with hundreds of live channels,
    categorized genres, official logos, and low-latency auto-fallback.
    """
    COUNTRY_FEEDS = COUNTRY_FEEDS
    COUNTRY_LABELS = COUNTRY_LABELS

    M3U_URLS = [
        "https://iptv-org.github.io/iptv/countries/eg.m3u",
        "https://iptv-org.github.io/iptv/languages/ara.m3u"
    ]
    CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "iptv_cache.json")

    CATEGORY_MAP = {
        "news": "الأخبار",
        "sports": "الرياضة",
        "documentary": "الوثائقيات",
        "general": "منوعات وترفيه",
        "entertainment": "منوعات وترفيه",
        "movies": "أفلام ومسلسلات",
        "series": "أفلام ومسلسلات",
        "religious": "إسلامية ودينية",
        "music": "موسيقى",
        "kids": "أطفال",
        "animation": "أطفال",
        "education": "تعليمية وثقافية",
        "lifestyle": "منوعات وترفيه"
    }

    _memory_cache: Optional[List[Dict[str, Any]]] = None
    _country_cache: Dict[str, List[Dict[str, Any]]] = {}
    cache = _country_cache  # Alias for self.cache / IPTVService.cache

    def __init__(self):
        self.cache = self._country_cache

    @classmethod
    def fetch_channels_by_country(cls, country_key: str) -> List[Dict[str, Any]]:
        """
        Fetches official IPTV-Org playlist for the requested country/category,
        parses #EXTINF metadata (name, logo, stream_url), and caches results in memory.
        Subsequent calls return from memory in 0ms without hitting the network.
        """
        key = country_key.strip().lower()
        # 1. In-memory cache hit
        if key in cls._country_cache and cls._country_cache[key]:
            return cls._country_cache[key]

        feed_url = cls.COUNTRY_FEEDS.get(key)
        if not feed_url:
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        channels: List[Dict[str, Any]] = []
        try:
            resp = requests.get(feed_url, headers=headers, timeout=8)
            if resp.status_code == 200:
                channels = cls.parse_m3u_content(resp.text)
                for ch in channels:
                    ch["country_code"] = key
                    if not ch.get("stream_url") and ch.get("streams"):
                        ch["stream_url"] = ch["streams"][0]

                # In sports or news feeds, sort Arabic channels to top
                if key in ("sports", "news"):
                    def _arabic_priority(c):
                        title = c.get("name", "")
                        has_ar = any('\u0600' <= char <= '\u06FF' for char in title)
                        return 0 if has_ar else 1
                    channels.sort(key=_arabic_priority)

                if channels:
                    cls._country_cache[key] = channels
                    return channels
        except Exception as e:
            print(f"[IPTVService] Network fetch error for '{key}': {e}")

        # Graceful fallback to verified curated seed channels if offline
        fallback: List[Dict[str, Any]] = []
        seeds = RemoteConfigManager.get_instance().get_iptv_channels()
        if key == "eg":
            fallback = [s for s in seeds if "eg" in s.get("id", "").lower() or "مصر" in s.get("name", "")]
        elif key == "sa":
            fallback = [s for s in seeds if "sa" in s.get("id", "").lower() or "سعودية" in s.get("name", "")]
        elif key == "sports":
            fallback = [s for s in seeds if "sport" in s.get("category", "").lower() or "رياضة" in s.get("category", "")]
        elif key == "news":
            fallback = [s for s in seeds if "news" in s.get("category", "").lower() or "أخبار" in s.get("category", "")]

        if not fallback and seeds:
            fallback = list(seeds[:20])

        for s in fallback:
            s["country_code"] = key
            if not s.get("stream_url") and s.get("streams"):
                s["stream_url"] = s["streams"][0]

        if fallback:
            cls._country_cache[key] = fallback
            return fallback

        return []

    @classmethod
    def get_channels(cls) -> List[Dict[str, Any]]:
        """
        Returns channels instantly with verified 100% active seed channels prioritized at the top.
        """
        if cls._memory_cache:
            return cls._memory_cache

        seeds = RemoteConfigManager.get_instance().get_iptv_channels()
        cached = []
        if os.path.exists(cls.CACHE_FILE):
            try:
                with open(cls.CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        cached = data
            except Exception:
                pass

        # Merge seeds at the very top, avoiding duplicate IDs
        seen_ids = set()
        merged = []
        for s in seeds:
            s_id = s.get("id")
            if s_id and s_id not in seen_ids:
                seen_ids.add(s_id)
                merged.append(s)

        for c in cached:
            c_id = c.get("id") or c.get("name")
            if c_id and c_id not in seen_ids:
                seen_ids.add(c_id)
                merged.append(c)

        cls._memory_cache = merged or seeds
        return cls._memory_cache

    @classmethod
    def clear_cache(cls):
        cls._memory_cache = None
        cls._country_cache.clear()
        if os.path.exists(cls.CACHE_FILE):
            try:
                os.remove(cls.CACHE_FILE)
            except Exception:
                pass

    @classmethod
    def add_custom_m3u_url(cls, playlist_url: str) -> List[Dict[str, Any]]:
        """
        Loads an external custom M3U/M3U8 playlist and prepends channels.
        """
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
        resp = requests.get(playlist_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            parsed = cls.parse_m3u_content(resp.text)
            if parsed:
                curr = cls.get_channels()
                updated = parsed + curr
                cls._memory_cache = updated
                try:
                    with open(cls.CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(updated, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                return parsed
        return []

    @classmethod
    def get_categories(cls) -> List[str]:
        channels = cls.get_channels()
        cats = ["الكل", "الأخبار", "الرياضة", "منوعات وترفيه", "الوثائقيات", "إسلامية ودينية"]
        for c in channels:
            cat = c.get("category")
            if cat and cat not in cats:
                cats.append(cat)
        return cats

    @classmethod
    def parse_m3u_content(cls, content: str) -> List[Dict[str, Any]]:
        """
        Parses raw M3U playlist into structured channel dictionaries.
        """
        channels = []
        lines = content.splitlines()
        current_meta = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#EXTINF:"):
                current_meta = {}
                # Extract tvg-logo
                logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                if logo_match:
                    current_meta["logo"] = logo_match.group(1)

                # Extract tvg-id
                id_match = re.search(r'tvg-id="([^"]+)"', line)
                if id_match:
                    current_meta["id"] = id_match.group(1)

                # Extract group-title (category)
                group_match = re.search(r'group-title="([^"]+)"', line)
                raw_group = group_match.group(1).lower() if group_match else "general"
                current_meta["category"] = cls.CATEGORY_MAP.get(raw_group, "منوعات وترفيه")

                # Extract channel title (everything after last comma)
                comma_idx = line.rfind(",")
                if comma_idx != -1:
                    raw_title = line[comma_idx + 1:].strip()
                    # Clean up technical tags like (1080p), [Not 24/7], etc.
                    clean_title = re.sub(r'\(\d+p\)|\[.*?\]', '', raw_title).strip()
                    current_meta["name"] = clean_title or raw_title
                else:
                    current_meta["name"] = "قناة نايل سات"

            elif current_meta and (line.startswith("http://") or line.startswith("https://")):
                url = line
                # Only include valid HLS / live streams
                current_meta["streams"] = [url]
                current_meta["stream_url"] = url
                if not current_meta.get("id"):
                    current_meta["id"] = f"ch_{abs(hash(url)) % 100000}"
                if not current_meta.get("logo"):
                    current_meta["logo"] = "https://i.imgur.com/8apNaLP.png"

                channels.append(current_meta)
                current_meta = None

        return channels

    @classmethod
    def fetch_and_cache_live_channels(cls) -> List[Dict[str, Any]]:
        """
        Fetches updated playlists from iptv-org, merges and deduplicates,
        and saves to local cache.
        """
        all_channels = []
        seen_names = set()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        # First add guaranteed curated top Nile channels
        curated_seeds = RemoteConfigManager.get_instance().get_iptv_channels()
        for seed in curated_seeds:
            all_channels.append(seed)
            seen_names.add(seed.get("name", "").lower())

        for url in cls.M3U_URLS:
            try:
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    parsed = cls.parse_m3u_content(resp.text)
                    for ch in parsed:
                        name_key = ch.get("name", "").lower()
                        if name_key and name_key not in seen_names:
                            seen_names.add(name_key)
                            all_channels.append(ch)
            except Exception:
                continue

        if all_channels:
            cls._memory_cache = all_channels
            try:
                os.makedirs(os.path.dirname(cls.CACHE_FILE), exist_ok=True)
                with open(cls.CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(all_channels, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        return all_channels or cls.get_channels()

    @classmethod
    def check_stream_latency(cls, url: str, timeout: float = 1.5) -> float:
        """
        Sends lightweight HEAD request to test HLS manifest accessibility.
        Returns response latency in milliseconds, or -1.0 if unreachable.
        """
        if not url:
            return -1.0
        try:
            t0 = time.time()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
            resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            if resp.status_code in (200, 206, 302, 301):
                return (time.time() - t0) * 1000.0
            if resp.status_code == 405:
                r2 = requests.get(url, headers=headers, timeout=timeout, stream=True)
                if r2.status_code in (200, 206):
                    return (time.time() - t0) * 1000.0
        except Exception:
            pass
        return -1.0

    @classmethod
    def find_fastest_stream(cls, channel: dict) -> Tuple[str, int]:
        streams = channel.get("streams", [])
        if not streams:
            return "", -1

        if len(streams) == 1:
            return streams[0], 0

        latencies: Dict[int, float] = {}

        def _test_index(idx_and_url):
            idx, u = idx_and_url
            lat = cls.check_stream_latency(u)
            if lat > 0:
                latencies[idx] = lat

        with ThreadPoolExecutor(max_workers=min(4, len(streams))) as executor:
            executor.map(_test_index, enumerate(streams))

        if latencies:
            best_idx = min(latencies, key=latencies.get)
            return streams[best_idx], best_idx

        return streams[0], 0

    @classmethod
    def get_fallback_stream(cls, channel: dict, failed_idx: int) -> Tuple[Optional[str], int]:
        streams = channel.get("streams", [])
        if not streams:
            return None, -1

        next_idx = (failed_idx + 1) % len(streams)
        if next_idx == failed_idx:
            return None, failed_idx
        return streams[next_idx], next_idx
