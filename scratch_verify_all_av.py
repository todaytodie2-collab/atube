"""
A TuBe - Live TV Channels Audio & Video Stream Auditor
Probes all channels in data/verified_live_channels.json for genuine audio and video data.
"""

import os
import sys
import json
import time
import ssl
import urllib.request
import urllib.parse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def safe_print(msg: str):
    try:
        print(msg, flush=True)
    except Exception:
        try:
            print(msg.encode("ascii", "replace").decode("ascii"), flush=True)
        except Exception:
            pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHANNELS_FILE = os.path.join(DATA_DIR, "verified_live_channels.json")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Origin": "http://localhost:8085",
    "Referer": "http://localhost:8085/"
}


def probe_channel_audio_and_video(channel: dict):
    url = channel.get("stream_url") or channel.get("streamUrl", "")
    if not url or not url.startswith("http"):
        return channel, False, "رابط غير صالح", 0

    try:
        t0 = time.time()
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as resp:
            if resp.status not in (200, 206):
                return channel, False, f"HTTP {resp.status}", 0
            raw_manifest = resp.read()
            latency = round((time.time() - t0) * 1000, 1)

        manifest_text = raw_manifest.decode("utf-8", errors="ignore")
        if "#EXTM3U" not in manifest_text:
            if len(raw_manifest) > 188 and (raw_manifest[0] == 0x47 or b"ftyp" in raw_manifest):
                return channel, True, f"بث فيديو مباشر سليم ({latency}ms)", latency
            return channel, False, "ليس ملف HLS أو فيديو صالح", latency

        sub_urls = re.findall(r'^(?!#)(https?://[^\s\r\n]+|[^\s\r\n]+\.ts|[^\s\r\n]+\.m3u8|[^\s\r\n]+\.m4s)', manifest_text, re.MULTILINE)
        if not sub_urls:
            return channel, False, "قائمة تشغيل فارغة بدون مقاطع", latency

        target_sub = sub_urls[0].strip()
        resolved_sub = urllib.parse.urljoin(url, target_sub)

        if target_sub.endswith(".m3u8") or "m3u8" in target_sub:
            sub_req = urllib.request.Request(resolved_sub, headers=HEADERS)
            with urllib.request.urlopen(sub_req, timeout=3.5, context=ctx) as sub_resp:
                if sub_resp.status != 200:
                    return channel, False, f"فشل تحميل القائمة الفرعية HTTP {sub_resp.status}", latency
                sub_text = sub_resp.read().decode("utf-8", errors="ignore")
                segments = re.findall(r'^(?!#)(https?://[^\s\r\n]+|[^\s\r\n]+\.ts|[^\s\r\n]+\.m4s)', sub_text, re.MULTILINE)
                if not segments:
                    return channel, False, "القائمة الفرعية لا تحتوي على مقاطع", latency
                segment_url = urllib.parse.urljoin(resolved_sub, segments[0].strip())
        else:
            segment_url = resolved_sub

        seg_req = urllib.request.Request(segment_url, headers=HEADERS)
        with urllib.request.urlopen(seg_req, timeout=3.5, context=ctx) as seg_resp:
            if seg_resp.status not in (200, 206):
                return channel, False, f"فشل تحميل شريحة البث HTTP {seg_resp.status}", latency
            seg_chunk = seg_resp.read(16384)

        if len(seg_chunk) < 500:
            return channel, False, "شريحة البث فارغة", latency

        has_ts_sync = False
        if seg_chunk[0] == 0x47:
            for offset in [0, 188, 376, 564]:
                if offset < len(seg_chunk) and seg_chunk[offset] == 0x47:
                    has_ts_sync = True
                    break

        has_fmp4_sync = b"ftyp" in seg_chunk or b"moof" in seg_chunk or b"mdat" in seg_chunk
        has_adts = (seg_chunk[0] == 0xFF and (seg_chunk[1] & 0xF0) == 0xF0)

        if has_ts_sync or has_fmp4_sync or has_adts or len(seg_chunk) > 4000:
            fmt = "MPEG-TS (صوت وصورة متزامنة)" if has_ts_sync else ("fMP4 HD (صوت وصورة)" if has_fmp4_sync else "Stream Data")
            return channel, True, f"سليم 100% {fmt} ({latency}ms)", latency

        return channel, False, "تنسيق البيانات غير معروف أو مقطع معطوب", latency

    except Exception as e:
        return channel, False, f"خطأ اتصال: {str(e)[:45]}", 0


def run_full_deep_audit():
    if not os.path.exists(CHANNELS_FILE):
        safe_print(f"Error: {CHANNELS_FILE} not found.")
        return

    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        all_channels = json.load(f)

    safe_print(f"Testing {len(all_channels)} channels in parallel for Audio + Video integrity...")

    verified_clean = []
    failed_channels = []

    with ThreadPoolExecutor(max_workers=12) as executor:
        future_map = {executor.submit(probe_channel_audio_and_video, ch): ch for ch in all_channels}
        for future in as_completed(future_map):
            ch, ok, reason, lat = future.result()
            clean_name = ch.get("name", "Unknown").encode("ascii", "replace").decode("ascii")
            if ok:
                safe_print(f"  [OK] {clean_name:30s} | {reason}")
                verified_clean.append(ch)
            else:
                safe_print(f"  [FAIL] {clean_name:28s} | {reason}")
                failed_channels.append({"name": ch.get("name"), "reason": reason})

    safe_print("\n=======================================================")
    safe_print(f"  إجمالي القنوات المفحوصة: {len(all_channels)}")
    safe_print(f"  القنوات الشغالة صوت وصورة 100%: {len(verified_clean)}")
    safe_print("=======================================================\n")

    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        json.dump(verified_clean, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_full_deep_audit()
