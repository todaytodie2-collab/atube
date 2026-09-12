# -*- coding: utf-8 -*-
"""
A TuBe IPTV Stream Health Check & Auto-Repair
===============================================
Checks every stream URL in config/remote_config.json:
  1. Probes each stream URL with a lightweight HEAD/GET request.
  2. For dead streams, tries fallback URLs from iptv-org open playlists.
  3. Updates remote_config.json with the best working URL first in the list.
  4. Writes atomically so the file is never partially written.

Designed to run as a GitHub Actions job every 12 hours:
    python services/iptv_health_check.py

Exit codes:
  0 — all channels have at least one working stream (or fixed)
  1 — one or more channels remain dead after repair attempts
"""

import os
import re
import sys
import json
import ssl
import time
import tempfile
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG     = os.path.join(_BASE_DIR, "config", "remote_config.json")

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode    = ssl.CERT_NONE

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

# ── Fallback open M3U sources (iptv-org, free-to-air) ────────────────────────
# Keyed by channel-id patterns for targeted lookup.
FALLBACK_SOURCES: Dict[str, List[str]] = {
    "mazzika": [
        "https://iptv-org.github.io/iptv/regions/arab.m3u",
        "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    ],
    "cbc": [
        "https://iptv-org.github.io/iptv/countries/eg.m3u",
    ],
    "alghad": [
        "https://iptv-org.github.io/iptv/countries/jo.m3u",
    ],
    "france24": [
        "https://iptv-org.github.io/iptv/languages/ara.m3u",
    ],
    "almasriyah": [
        "https://iptv-org.github.io/iptv/countries/eg.m3u",
    ],
    # Generic Arabic fallback for any channel not matched above
    "_default": [
        "https://iptv-org.github.io/iptv/regions/arab.m3u",
        "https://iptv-org.github.io/iptv/languages/ara.m3u",
    ],
}


# ── Probe helper ──────────────────────────────────────────────────────────────

def _probe(url: str, timeout: float = 5.0) -> bool:
    """Return True if the stream URL responds with HTTP 200/206."""
    if not url or not url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(url, headers=_HEADERS, method="HEAD")
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            return resp.status in (200, 206)
    except Exception:
        try:
            # Retry with GET for servers that reject HEAD
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
                return resp.status in (200, 206)
        except Exception:
            return False


# ── M3U parser ────────────────────────────────────────────────────────────────

def _fetch_m3u(url: str, timeout: float = 10.0) -> str:
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_m3u_streams(text: str, keyword: str) -> List[str]:
    """Extract stream URLs whose EXTINF line contains `keyword`."""
    results = []
    keyword_low = keyword.lower()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF") and keyword_low in line.lower():
            # The stream URL is on the very next non-comment line
            for j in range(i + 1, min(i + 3, len(lines))):
                nxt = lines[j].strip()
                if nxt and not nxt.startswith("#"):
                    results.append(nxt)
                    break
    return results


# ── Repair logic ──────────────────────────────────────────────────────────────

def _find_fallback(channel_id: str, channel_name: str) -> Optional[str]:
    """Search open M3U playlists for a working stream for this channel."""
    combined = f"{channel_id} {channel_name}".lower()

    # Pick the most relevant fallback source list
    m3u_sources: List[str] = FALLBACK_SOURCES.get("_default", [])
    for key, sources in FALLBACK_SOURCES.items():
        if key != "_default" and key in combined:
            m3u_sources = sources
            break

    # Try each keyword (channel id words, channel name words)
    keywords = re.sub(r"[^a-z\u0600-\u06FF ]+", " ", combined).split()
    keywords = [k for k in keywords if len(k) > 2][:4]  # top 4 keywords

    for m3u_url in m3u_sources:
        text = _fetch_m3u(m3u_url)
        if not text:
            continue
        for kw in keywords:
            for stream_url in _parse_m3u_streams(text, kw):
                if _probe(stream_url):
                    print(f"    ✅ Fallback found via {m3u_url}: {stream_url}")
                    return stream_url
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def check_and_repair(config_path: str = _CONFIG) -> int:
    """
    Load remote_config.json, health-check every IPTV stream, attempt repair,
    save updated config. Returns 0 on success, 1 if any channel stays dead.
    """
    if not os.path.exists(config_path):
        print(f"[IPTV Health] Config not found: {config_path}")
        return 1

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    channels: List[Dict[str, Any]] = config.get("iptv_channels", [])
    if not channels:
        print("[IPTV Health] No channels defined.")
        return 0

    total = len(channels)
    dead  = 0
    fixed = 0

    for ch in channels:
        cid   = ch.get("id", "unknown")
        name  = ch.get("name", cid)
        streams: List[str] = ch.get("streams", [])

        print(f"\n[IPTV Health] Checking: {name}")

        working: List[str] = []
        dead_streams: List[str] = []

        for url in streams:
            if _probe(url):
                print(f"  ✅ OK  {url}")
                working.append(url)
            else:
                print(f"  ❌ DEAD {url}")
                dead_streams.append(url)

        if not working:
            print(f"  ⚠️  All streams dead — searching fallback...")
            fb = _find_fallback(cid, name)
            if fb:
                working.append(fb)
                fixed += 1
                print(f"  🔧 Fixed: {fb}")
            else:
                dead += 1
                print(f"  💀 No fallback found for '{name}'")

        # Put working streams first, dead streams last (as last-resort fallbacks)
        ch["streams"] = working + [d for d in dead_streams if d not in working]

    # Persist updated config atomically
    d = os.path.dirname(config_path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp", prefix="remote_config_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        os.replace(tmp, config_path)
        print(f"\n[IPTV Health] Done — {total} channels, {fixed} fixed, {dead} still dead.")
    except Exception as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        print(f"[IPTV Health] Error saving config: {e}")
        return 1

    return 0 if dead == 0 else 1


if __name__ == "__main__":
    raise SystemExit(check_and_repair())
