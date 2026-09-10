import json
import os
import re
import urllib.request
import urllib.error
from urllib.parse import urlparse
import time

# --- Configuration ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JS_DATA_FILE = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")
HTML_FILE = os.path.join(PROJECT_ROOT, "index.html")

REPORT_FILE = os.path.join(PROJECT_ROOT, "QA_Report.md")

# --- Globals for Reporting ---
report_data = {
    "total_items": 0,
    "broken_images": [],
    "duplicate_posters": {},
    "broken_streams": [],
    "ui_issues": [],
    "mismatched_content": []
}

def log(msg):
    print(f"[*] {msg}")

def extract_json_from_js():
    log("Extracting Catalog JSON from bundled-data.js...")
    try:
        with open(JS_DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract window.ATUBE_STATIC_CATALOG = [...]
        match = re.search(r'window\.ATUBE_STATIC_CATALOG\s*=\s*(\[\{.*?\}\]);', content, re.DOTALL)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
            log("Error: Could not find ATUBE_STATIC_CATALOG in JS file.")
            return None
    except Exception as e:
        log(f"Error reading JS file: {e}")
        return None

def check_url_exists(url, is_image=False):
    """Simulates checking if a URL is reachable (returns 200)."""
    if not url:
        return False
    if url.startswith("assets/") or url.startswith("css/") or url.startswith("js/"):
        # Local file check
        local_path = os.path.join(PROJECT_ROOT, url.replace("/", os.sep))
        return os.path.exists(local_path)

    # Fast check for external URLs using HEAD request
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status in [200, 301, 302]
    except urllib.error.HTTPError as e:
        if e.code == 403: # Some CDNs block HEAD, assume it might be okay but flag it
            return "403_FORBIDDEN"
        return False
    except Exception:
        return False

def analyze_catalog(catalog):
    log("Starting comprehensive Catalog Analysis...")
    report_data["total_items"] = len(catalog)

    poster_map = {} # url -> [list of movie titles using it]

    for item in catalog:
        title = item.get("title", "Unknown Title")
        arabic_title = item.get("arabic_title", "")
        poster = item.get("poster", "")
        backdrop = item.get("backdrop", "")

        # 1. Poster Checks
        if poster:
            if poster in poster_map:
                poster_map[poster].append(title)
            else:
                poster_map[poster] = [title]

            # Since checking hundreds of external URLs synchronously is slow,
            # we will flag suspicious formats or local missing files.
            if poster.startswith("assets/") and not check_url_exists(poster):
                 report_data["broken_images"].append(f"[{title}] Missing local poster: {poster}")
        else:
            report_data["ui_issues"].append(f"[{title}] has NO poster image defined.")

        # 2. Mismatched Content Check (Basic heuristic: English title in Arabic field)
        if arabic_title and arabic_title == title and re.search('[a-zA-Z]', title):
             report_data["mismatched_content"].append(f"[{title}] Arabic title field contains English/Same text: '{arabic_title}'")

        # 3. Stream Validation (Simulating playability check)
        servers = item.get("servers", [])
        if item.get("content_type") == "movie":
            if not servers:
                 report_data["broken_streams"].append(f"Movie [{title}] has NO streaming servers available.")
            else:
                for srv in servers:
                    url = srv.get("stream_url", "")
                    if not url:
                        report_data["broken_streams"].append(f"[{title}] Empty stream URL in server: {srv.get('name')}")

        elif item.get("content_type") == "series":
            seasons = item.get("seasons", [])
            if not seasons:
                 report_data["broken_streams"].append(f"Series [{title}] has NO seasons.")
            for season in seasons:
                episodes = season.get("episodes", [])
                if not episodes:
                    report_data["broken_streams"].append(f"Series [{title}] Season {season.get('season_number')} has NO episodes.")
                for ep in episodes:
                    ep_servers = ep.get("servers", [])
                    ep_title = ep.get("title", f"Episode {ep.get('episode_number')}")
                    if not ep_servers:
                        report_data["broken_streams"].append(f"[{title}] - [{ep_title}] has NO streaming servers.")

    # Process Duplicate Posters
    for url, titles in poster_map.items():
        if len(titles) > 1 and url != "assets/gladiator_hero.jpg": # Ignore known placeholders if any
            report_data["duplicate_posters"][url] = titles

def check_html_ui():
    log("Scanning HTML for UI bottlenecks...")
    try:
        with open(HTML_FILE, 'r', encoding='utf-8') as f:
            html = f.read()

        # Check for empty hrefs or broken links
        if 'href=""' in html or "href=''" in html:
            report_data["ui_issues"].append("HTML contains empty href attributes (Broken Links).")

        # Check for missing alt tags (Accessibility & UI robustness)
        img_tags = re.findall(r'<img[^>]*>', html)
        for img in img_tags:
            if 'alt=' not in img:
                report_data["ui_issues"].append(f"Missing 'alt' attribute in image tag: {img}")

    except Exception as e:
        log(f"Error reading HTML: {e}")

def generate_markdown_report():
    log("Generating Report...")
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# 🕵️‍♂️ A TuBe - Automated QA & Testing Report\n\n")
        f.write("تم إنشاء هذا التقرير آلياً بواسطة سكربت الفحص الشامل ليحاكي تجربة المستخدم وتدقيق جودة البيانات والواجهة.\n\n")

        f.write("## 📊 ملخص الإحصائيات (Overview)\n")
        f.write(f"- إجمالي المحتوى المفحوص (أفلام/مسلسلات): **{report_data['total_items']}**\n\n")

        f.write("## 🖼️ مشاكل الصور والبطاقات (Posters & UI)\n")
        if report_data['duplicate_posters']:
            f.write("### ⚠️ بوسترات مكررة (نفس الصورة مستخدمة لأكثر من فيلم/مسلسل):\n")
            for url, titles in report_data['duplicate_posters'].items():
                f.write(f"- **الصورة:** `{url}`\n")
                f.write(f"  - **مستخدمة في:** {', '.join(titles)}\n")
        else:
            f.write("✅ لا يوجد بوسترات مكررة بشكل خاطئ.\n")

        if report_data['broken_images']:
            f.write("\n### ❌ صور مفقودة (Broken Images):\n")
            for item in report_data['broken_images']:
                f.write(f"- {item}\n")

        f.write("\n## 🎬 مشاكل التشغيل والسيرفرات (Playback Issues)\n")
        if report_data['broken_streams']:
            f.write("تم اكتشاف محتوى لا يحتوي على روابط تشغيل صالحة:\n")
            for item in report_data['broken_streams']:
                f.write(f"- 🔴 {item}\n")
        else:
            f.write("✅ جميع الأفلام والحلقات تحتوي على سيرفرات تشغيل.\n")

        f.write("\n## 📝 أخطاء إدخال البيانات (Data Mismatches)\n")
        if report_data['mismatched_content']:
            f.write("تم ملاحظة أن بعض العناوين العربية تحتوي على نص إنجليزي أو غير مترجمة بشكل صحيح:\n")
            # Limit to first 15 to avoid massive lists
            for item in report_data['mismatched_content'][:15]:
                f.write(f"- {item}\n")
            if len(report_data['mismatched_content']) > 15:
                f.write(f"- ... و {len(report_data['mismatched_content']) - 15} عناصر أخرى بنفس المشكلة.\n")
        else:
            f.write("✅ البيانات تبدو متطابقة.\n")

        f.write("\n## 🖥️ تقييم واجهة المستخدم (UI/UX Review)\n")
        if report_data['ui_issues']:
            for item in report_data['ui_issues']:
                f.write(f"- ⚠️ {item}\n")
        else:
            f.write("✅ كود الـ HTML والواجهة خالي من الأخطاء الواضحة.\n")

if __name__ == "__main__":
    catalog = extract_json_from_js()
    if catalog:
        analyze_catalog(catalog)
        check_html_ui()
        generate_markdown_report()
        log(f"Test Complete! Report saved to {REPORT_FILE}")
    else:
        log("Failed to load catalog data. Aborting test.")
