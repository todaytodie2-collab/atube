import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "services"))

from stream_aggregator import SmartStreamAggregator

CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

def run_harvest_and_aggregate():
    print("[*] Running Smart Universal Stream Aggregator...")

    if not os.path.exists(CATALOG_JSON):
        print(f"Error: {CATALOG_JSON} not found.")
        return

    with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
        raw_catalog = json.load(f)

    print(f"[*] Raw Catalog Items: {len(raw_catalog)}")

    # Run Aggregator
    aggregated_catalog = SmartStreamAggregator.aggregate_catalog(raw_catalog)
    print(f"[*] Aggregated Catalog Items: {len(aggregated_catalog)}")

    # Write back to catalog.json
    with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
        json.dump(aggregated_catalog, f, ensure_ascii=False, indent=2)

    # Write back to js/bundled-data.js
    if os.path.exists(BUNDLED_JS):
        with open(BUNDLED_JS, 'r', encoding='utf-8') as f:
            js_content = f.read()

        import re
        match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', js_content, re.DOTALL)
        if match:
            prefix = match.group(1)
            suffix = match.group(3)
            new_js = prefix + json.dumps(aggregated_catalog, ensure_ascii=False) + ";" + suffix
            with open(BUNDLED_JS, 'w', encoding='utf-8') as f:
                f.write(new_js)
            print("[*] Successfully updated js/bundled-data.js")

    print("[*] Cloud Harvester & Aggregator finished 100% successfully!")

if __name__ == "__main__":
    run_harvest_and_aggregate()
