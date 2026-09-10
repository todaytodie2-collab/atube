import json
import re
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JS_DATA_FILE = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")
CATALOG_JSON_FILE = os.path.join(PROJECT_ROOT, "catalog.json")

# Poster replacements for movies that were sharing gladiator_hero.jpg
POSTER_FIXES = {
    "thor-love-and-thunder-2022-2022": {
        "poster": "https://iegybest.cimawbas.tv/uploads/thumbs/bjiS5ipwxb9JFy3XRRN4OAilSeX.jpg",
        "backdrop": "https://iegybest.cimawbas.tv/uploads/thumbs/bjiS5ipwxb9JFy3XRRN4OAilSeX.jpg"
    },
    "top-gun-maverick-2022-2022": {
        "poster": "https://iegybest.cimawbas.tv/uploads/thumbs/6206p111222.jpg",
        "backdrop": "https://iegybest.cimawbas.tv/uploads/thumbs/6206p111222.jpg"
    },
    "last-seen-alive-2022-2022": {
        "poster": "https://iegybest.cimawbas.tv/uploads/thumbs/64305abd5-1.jpg",
        "backdrop": "https://iegybest.cimawbas.tv/uploads/thumbs/64305abd5-1.jpg"
    },
    "ek-villain-returns-2022-2022": {
        "poster": "https://iegybest.cimawbas.tv/uploads/thumbs/817776a5c-1.jpg",
        "backdrop": "https://iegybest.cimawbas.tv/uploads/thumbs/817776a5c-1.jpg"
    },
    "don-039-t-breathe-2-2021-2021": {
        "poster": "https://iegybest.cimawbas.tv/uploads/thumbs/fca99b3b2-1.jpg",
        "backdrop": "https://iegybest.cimawbas.tv/uploads/thumbs/fca99b3b2-1.jpg"
    },
    "bharathanyam-2-mohiniyattam-2026-2026": {
        "poster": "https://iegybest.cimawbas.tv/uploads/thumbs/44ad17a6e-1.jpg",
        "backdrop": "https://iegybest.cimawbas.tv/uploads/thumbs/44ad17a6e-1.jpg"
    }
}

def fix_catalog_data(items):
    for item in items:
        item_id = item.get("id")
        title = item.get("title", "")

        # 1. Fix Reacher category (Problem 1)
        if item_id == "reacher-2026" or title == "Reacher":
            item["category"] = "foreign"
            item["sub_category"] = "subbed"
            print("Fixed Reacher category -> foreign")

        # 2. Fix Poster Mismatches (Problem 2)
        if item_id in POSTER_FIXES:
            item["poster"] = POSTER_FIXES[item_id]["poster"]
            item["backdrop"] = POSTER_FIXES[item_id]["backdrop"]
            print(f"Fixed poster for {title}")

    return items

def process_js_file():
    with open(JS_DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', content, re.DOTALL)
    if match:
        prefix = match.group(1)
        catalog = json.loads(match.group(2))
        suffix = match.group(3)

        fixed_catalog = fix_catalog_data(catalog)

        new_content = prefix + json.dumps(fixed_catalog, ensure_ascii=False) + ";" + suffix
        with open(JS_DATA_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated js/bundled-data.js successfully.")

def process_json_file():
    if os.path.exists(CATALOG_JSON_FILE):
        with open(CATALOG_JSON_FILE, 'r', encoding='utf-8') as f:
            catalog = json.load(f)

        fixed_catalog = fix_catalog_data(catalog)

        with open(CATALOG_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(fixed_catalog, f, ensure_ascii=False, indent=2)
        print("Updated catalog.json successfully.")

if __name__ == "__main__":
    process_js_file()
    process_json_file()
