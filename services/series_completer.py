# -*- coding: utf-8 -*-
"""
A TuBe Series Completer & Episode Normalizer Engine (Multi-Threaded)
Resolves incomplete series by querying TMDB API for the exact number of seasons and episodes,
filling missing episodes from 1 to N in strict sequential order.
"""

import json
import os
import re
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from tmdb_client import TMDBClient, DEFAULT_TMDB_API_KEY

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

def get_tmdb_tv_seasons(tmdb_id: int) -> list:
    url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={DEFAULT_TMDB_API_KEY}&language=ar-SA"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            seasons_meta = data.get('seasons', [])
            full_seasons = []

            for s in seasons_meta:
                s_num = s.get('season_number', 1)
                if s_num == 0: continue
                ep_count = s.get('episode_count', 1)

                season_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{s_num}?api_key={DEFAULT_TMDB_API_KEY}&language=ar-SA"
                episodes = []
                try:
                    s_req = urllib.request.Request(season_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(s_req, timeout=3) as s_resp:
                        s_data = json.loads(s_resp.read().decode('utf-8'))
                        for ep in s_data.get('episodes', []):
                            ep_num = ep.get('episode_number')
                            ep_title = ep.get('name') or f"الحلقة {ep_num}"
                            ep_still = f"https://image.tmdb.org/t/p/w500{ep.get('still_path')}" if ep.get('still_path') else ""

                            episodes.append({
                                "id": f"s{s_num}e{ep_num}_{tmdb_id}",
                                "episode_number": ep_num,
                                "title": f"الحلقة {ep_num}: {ep_title}",
                                "thumbnail": ep_still,
                                "duration": "45 دقيقة",
                                "servers": []
                            })
                except Exception:
                    for i in range(1, ep_count + 1):
                        episodes.append({
                            "id": f"s{s_num}e{i}_{tmdb_id}",
                            "episode_number": i,
                            "title": f"الحلقة {i}",
                            "thumbnail": "",
                            "duration": "45 دقيقة",
                            "servers": []
                        })

                full_seasons.append({
                    "season_number": s_num,
                    "title": s.get('name') or f"الموسم {s_num}",
                    "episodes": episodes
                })
            return full_seasons
    except Exception:
        pass
    return []

def process_single_series(item):
    if item.get("content_type") != "series":
        return item

    title = item.get("title", "")
    existing_seasons = item.get("seasons", [])

    match = TMDBClient.search_media(title, "series")
    if match:
        tmdb_id = match.get("id")
        tmdb_seasons = get_tmdb_tv_seasons(tmdb_id)

        if tmdb_seasons:
            for t_season in tmdb_seasons:
                s_num = t_season["season_number"]
                match_s = next((s for s in existing_seasons if s.get("season_number") == s_num), None)
                if match_s:
                    existing_eps = match_s.get("episodes", [])
                    for t_ep in t_season["episodes"]:
                        ep_num = t_ep["episode_number"]
                        match_ep = next((e for e in existing_eps if int(e.get("episode_number", 0)) == ep_num), None)
                        if match_ep and match_ep.get("servers"):
                            t_ep["servers"] = match_ep["servers"]
                            if match_ep.get("thumbnail"):
                                t_ep["thumbnail"] = match_ep["thumbnail"]

            item["seasons"] = tmdb_seasons
            item["total_seasons"] = len(tmdb_seasons)
            print(f"[SeriesCompleter] Completed series '{title}' with {len(tmdb_seasons)} seasons in sequential order.")

    return item

def complete_all_series():
    print("[*] Starting Multi-Threaded Series Completer...")
    if not os.path.exists(CATALOG_JSON):
        return

    with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    with ThreadPoolExecutor(max_workers=8) as executor:
        completed_catalog = list(executor.map(process_single_series, catalog))

    with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
        json.dump(completed_catalog, f, ensure_ascii=False, indent=2)

    if os.path.exists(BUNDLED_JS):
        with open(BUNDLED_JS, 'r', encoding='utf-8') as f:
            js_content = f.read()

        match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', js_content, re.DOTALL)
        if match:
            prefix = match.group(1)
            suffix = match.group(3)
            new_js = prefix + json.dumps(completed_catalog, ensure_ascii=False) + ";" + suffix
            with open(BUNDLED_JS, 'w', encoding='utf-8') as f:
                f.write(new_js)

    print("[*] Multi-Threaded Series Completer finished successfully!")

if __name__ == "__main__":
    complete_all_series()
