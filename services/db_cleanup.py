# -*- coding: utf-8 -*-
"""
Catalog & SQLite consolidation utility for A-Tube.

Problem
-------
`catalog.json` stored every episodic episode as a *separate top-level* `vod_media`
row (content_type = 'series'|'anime'|'tv_show', seasons=[], episodes=0) whose
title embeds an episode marker, e.g.:

    "في السابعة عشرة - الحلقة ١٦ - السادسة عشر - ايجي بست"

This produced two visible bugs:
  * duplicate / near-duplicate episode cards on the homepage, and
  * `/api/media/episodes?id=<episode_row>` returning 404 "Season 1 not found",
    because no *parent* series row exists for those ids.

What this script does
---------------------
  1. Loads `catalog.json` (a JSON array of media objects).
  2. Decodes HTML entities (&quot; -> ", etc.) on every text field at the *source*
     so downstream rendering never re-encodes garbage.
  3. Groups episode rows that share a parent-series name (Arabic episode/season
     markers are stripped from the title) and rebuilds them into proper parent
     series objects carrying nested `seasons[ { season_number, episodes:[...] } ]`,
     with each episode retaining its own `id`, `poster`, `duration`, `synopsis`
     and crucially its `servers`.
  4. Writes the cleaned catalog back to `catalog.json`.
  5. Clears the `vod_media` / `vod_seasons` / `vod_episodes` / `vod_servers` /
     `vod_cast` / `vod_stills` SQLite tables and re-seeds them from the cleaned
     catalog, so `/api/media/feed`, `/api/media/details`, `/api/media/episodes`
     and `/api/media/cast` immediately return consolidated data.

Run:
    python services/db_cleanup.py          # cleanup + reseed, in place
    python services/db_cleanup.py --dry-run  # report only, no changes

Safe to re-run: it is idempotent (episode-row detection is strict, parent ids are
deterministic from the cleaned parent name + year).
"""

import os
import re
import sys
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # .../A TuBe/services
PROJECT_DIR = os.path.dirname(BASE_DIR)                         # .../A TuBe
CATALOG_PATH = os.path.join(PROJECT_DIR, "catalog.json")

sys.path.insert(0, BASE_DIR)

from text_sanitizer import TextSanitizer
from vod_db import VODDatabase


EPISODIC_TYPES = ("series", "anime", "tv_show")

# Arabic + latin markers used to recognise episode/season tokens in titles.
# Titles look like:  "<series_name> الحلقة 16 السادسة عشر [ايجي بست]"
#  or:              "Record of Ragnarok الموسم الثاني الحلقة 12"
# The parent series name is the text BEFORE the first marker, so we match any
# of the markers first.
_MARKER_RE = re.compile(
    r"(?:الموسك|الموسم|موسم|season|الحلقة|حلقة|episode)",
    re.IGNORECASE,
)
# Episode number written as digits after an episode marker: "الحلقة 16"
_EPISODE_RE = re.compile(
    r"(?:الحلقة|حلقة|episode)\s*(\d+)",
    re.IGNORECASE,
)
# Season number written as digits after a season marker: "الموسك 2"
_SEASON_RE = re.compile(
    r"(?:الموسك|موسم|season)\s*(\d+)",
    re.IGNORECASE,
)
# Arabic ordinal words spoken after الموسم/موسم when no digit is present,
# e.g. "الموسم الثاني" -> season 2.
_AR_SEASON_ORDINALS = {
    "الاول": 1, "الأول": 1, "الاولى": 1, "الأولى": 1, "الواحد": 1,
    "الثاني": 2, "الثانية": 2,
    "الثالث": 3, "الثالثة": 3,
    "الرابع": 4, "الرابعة": 4,
    "الخامس": 5, "الخامسة": 5,
    "السادس": 6, "السادسة": 6,
    "السابع": 7, "السابعة": 7,
    "الثامن": 8, "الثامنة": 8,
    "التاسع": 9, "التاسعة": 9,
    "العاشر": 10, "العاشرة": 10,
}
_AR_SEASON_WORDS = ("الموسم", "موسم", "الموسك")
# Noise tokens that sometimes trail a parent name extracted via substring.
_TRAILING_NOISE_RE = re.compile(r"[\s\t,\-\u2013\u2014|]+$")

# Text fields we always run through entity decoding.
_TEXT_FIELDS = (
    "title", "arabic_title", "synopsis", "director",
    "language", "translation", "production", "country",
    "poster", "backdrop", "trailer_youtube_id",
    "rating", "duration", "quality", "year",
)


def _decode(text):
    """Decode HTML entities safely for non-string values."""
    if not isinstance(text, str):
        return text
    return TextSanitizer.decode_html_entities(text)


def _sanitize_item_text(item):
    """Decode HTML entities on every textual field of a catalog item."""
    if not isinstance(item, dict):
        return item
    for field in _TEXT_FIELDS:
        if field in item:
            item[field] = _decode(item[field])
    if isinstance(item.get("genres"), list):
        item["genres"] = [_decode(g) if isinstance(g, str) else g for g in item["genres"]]
    if isinstance(item.get("cast"), list):
        for actor in item["cast"]:
            if isinstance(actor, dict):
                for af in ("name", "arabic_name", "role", "character_name", "photo"):
                    if af in actor:
                        actor[af] = _decode(actor[af])
    if isinstance(item.get("seasons"), list):
        for season in item["seasons"]:
            if isinstance(season, dict):
                season["title"] = _decode(season.get("title", ""))
                eps = season.get("episodes") or []
                for ep in eps:
                    if isinstance(ep, dict):
                        for ef in ("title", "episode_title", "synopsis", "thumbnail", "duration"):
                            if ef in ep:
                                ep[ef] = _decode(ep[ef])
    return item


def _is_episode_row(item):
    """An item is an *episode* row when it is episodic-typed AND its title carries
    an Arabic episode marker (the catalog's broken-shape marker)."""
    ct = item.get("content_type") or ""
    if ct not in EPISODIC_TYPES:
        return False
    title = item.get("title") or item.get("arabic_title") or ""
    title = TextSanitizer.decode_html_entities(title)
    if _EPISODE_RE.search(title):
        return True
    # An episodic row whose title embeds a season word but no bare episode num
    # (rare) still counts as an episode row if it has no seasons already.
    if any(w in title for w in _AR_SEASON_WORDS):
        seasons = item.get("seasons")
        if not isinstance(seasons, list) or not seasons:
            return True
    return False


def _parse_season_number(title, fallback=1):
    # Prefer a digit-based season marker first ("الموسك 2").
    m = _SEASON_RE.search(title)
    if m:
        try:
            return int(m.group(1))
        except (TypeError, ValueError):
            return fallback
    # Otherwise read the Arabic ordinal spoken after الموسم/موسم
    # ("الموسم الثاني" -> 2).
    seg = re.search(r"(?:الموسك|الموسم|موسم)\s+(\S+)", title, re.IGNORECASE)
    if seg:
        word = re.sub(r"[^\w\s\u0600-\u06FF]", "", seg.group(1))
        for ordinal, num in _AR_SEASON_ORDINALS.items():
            if word == ordinal or word.startswith(ordinal):
                return num
    return fallback


def _parse_episode_number(title, fallback=1):
    m = _EPISODE_RE.search(title)
    if m:
        try:
            return int(m.group(1))
        except (TypeError, ValueError):
            return fallback
    return fallback


def _parent_series_name(title):
    """Return the parent series name: everything before the first episode/season
    marker, with trailing noise stripped."""
    name = TextSanitizer.decode_html_entities(title or "")
    m = _MARKER_RE.search(name)
    if m:
        name = name[:m.start()]
    name = _TRAILING_NOISE_RE.sub("", name).strip()
    name = re.sub(r"[\s\u2013\u2014\-]{2,}", " ", name).strip("\u2013\u2014 -")
    return name



def _slugify(text, year):
    """Deterministic parent-series id derived from cleaned name + year,
    mirroring catalog_sync.generate-id slug rules."""
    base = re.sub(r"[^\w\u0600-\u06FF]+", "-", (text or "").lower()).strip("-")
    if not base:
        import hashlib
        base = "item-" + hashlib.md5((text or "").encode("utf-8")).hexdigest()[:8]
    if year:
        year = re.sub(r"\D", "", str(year))
        if year:
            base = f"{base}-{year}"
    return base


def consolidate(catalog_items):
    """Return (cleaned_items, report).

    Episode rows are grouped into parent series; movies and already-parental
    series are passed through (with text sanitising) unchanged.
    """
    cleaned = []
    parents = {}      # parent_name -> parent series object (in progress)
    report = {
        "input": len(catalog_items),
        "episode_rows": 0,
        "movies": 0,
        "parent_series": 0,
        "consolidated_series": 0,
        "groups": [],
    }

    for item in catalog_items:
        item = _sanitize_item_text(item)

        if _is_episode_row(item):
            report["episode_rows"] += 1
            raw_title = item.get("title") or item.get("arabic_title") or ""
            title = TextSanitizer.decode_html_entities(raw_title)
            parent_name = _parent_series_name(title)
            if not parent_name or len(parent_name) < 2:
                # Could not derive a parent -> keep it standalone as a series so
                # it is never lost, but mark total_seasons so it still renders.
                item.setdefault("total_seasons", 1)
                item.setdefault("seasons", [])
                cleaned.append(item)
                continue

            season_num = _parse_season_number(title)
            ep_num = _parse_episode_number(title)

            parent = parents.get(parent_name)
            if parent is None:
                parent = _new_parent(item, parent_name)
                parents[parent_name] = parent
                cleaned.append(parent)

            # Ensure a bucket for this season exists.
            season_bucket = next(
                (s for s in parent["seasons"] if s["season_number"] == season_num), None
            )
            if season_bucket is None:
                season_bucket = {
                    "season_number": season_num,
                    "title": _season_title(season_num, title),
                    "episodes": [],
                }
                parent["seasons"].append(season_bucket)

            # De-duplicate episodes that share an episode number (the source
            # catalog often lists the same episode under multiple scrape ids).
            # Keep the duplicate with the most servers attached.
            new_ep = _to_episode(item, ep_num)
            existing_eps = season_bucket["episodes"]
            dup_idx = next(
                (i for i, e in enumerate(existing_eps)
                 if e.get("episode_number") == ep_num),
                -1,
            )
            if dup_idx == -1:
                existing_eps.append(new_ep)
            else:
                cur_ep = existing_eps[dup_idx]
                if len(new_ep.get("servers") or []) > len(cur_ep.get("servers") or []):
                    new_ep["id"] = new_ep.get("id") or cur_ep.get("id")
                    new_ep["thumbnail"] = new_ep.get("thumbnail") or cur_ep.get("thumbnail")
                    new_ep["synopsis"] = new_ep.get("synopsis") or cur_ep.get("synopsis")
                    existing_eps[dup_idx] = new_ep

            # Merge cast onto the parent (de-duplicated by name).
            _merge_cast(parent, item)
        else:
            cleaned.append(item)
            if item.get("content_type") == "movie":
                report["movies"] += 1
            elif item.get("content_type") in EPISODIC_TYPES:
                report["parent_series"] += 1

    # Finalise parent series metadata.
    for parent in parents.values():
        parent["total_seasons"] = len(parent["seasons"])
        report["consolidated_series"] += 1
        ep_total = sum(len(s["episodes"]) for s in parent["seasons"])
        report["groups"].append({
            "parent": parent["arabic_title"] or parent["title"],
            "seasons": parent["total_seasons"],
            "episodes": ep_total,
        })

    # Sort parents' seasons/episodes for stable output.
    for parent in parents.values():
        parent["seasons"].sort(key=lambda s: s["season_number"])
        for s in parent["seasons"]:
            s["episodes"].sort(key=lambda e: e.get("episode_number", 0))

    return cleaned, report


def _new_parent(template, parent_name):
    """Build a parent series object from the first episode row we see."""
    year = template.get("year")
    parent_id = _slugify(parent_name, year)
    return {
        "id": parent_id,
        "title": parent_name,
        "arabic_title": parent_name,
        "content_type": template.get("content_type", "series"),
        "category": template.get("category", "foreign"),
        "sub_category": template.get("sub_category", "subbed"),
        "year": year,
        "rating": template.get("rating", "★ 8.5 IMDb"),
        "duration": "45 دقيقة",
        "quality": template.get("quality", "WEB-DL 1080p FHD"),
        "language": template.get("language", "الإنجليزية"),
        "translation": template.get("translation", "مترجم للعربية"),
        "production": template.get("production", template.get("country", "إنتاج حقيقي")),
        "country": template.get("country", ""),
        "genres": list(template.get("genres") or ["دراما"]),
        "poster": template.get("poster"),
        "backdrop": template.get("backdrop") or template.get("poster"),
        "synopsis": _parent_synopsis(parent_name, template.get("synopsis")),
        "trailer_youtube_id": template.get("trailer_youtube_id", ""),
        "director": template.get("director", "إدارة المحتوى"),
        "total_seasons": 0,
        "seasons": [],
        "servers": [],          # episode-level servers, not top-level
        "cast": [],
    }


def _parent_synopsis(parent_name, first_synopsis):
    if first_synopsis and isinstance(first_synopsis, str) and first_synopsis.strip():
        return first_synopsis
    return f"{parent_name}: مجموعة كاملة من الحلقات."


def _season_title(season_num, _ctx):
    return "الموسم الأول" if season_num == 1 else f"الموسم {season_num}"


def _to_episode(item, ep_num):
    """Turn an episode row into an episode object the DB + frontend understand."""
    raw_title = item.get("title") or item.get("arabic_title") or ""
    return {
        "id": item.get("id"),
        "episode_number": ep_num,
        "title": TextSanitizer.decode_html_entities(raw_title),
        "thumbnail": (item.get("poster") or item.get("backdrop") or ""),
        "duration": item.get("duration", "45 دقيقة"),
        "synopsis": _decode(item.get("synopsis")) or "",
        "servers": item.get("servers") or [],
        "still": item.get("poster"),
    }


def _merge_cast(parent, episode_item):
    existing_ids = {a.get("name") for a in parent["cast"] if isinstance(a, dict)}
    for actor in episode_item.get("cast") or []:
        if isinstance(actor, dict) and actor.get("name") not in existing_ids:
            parent["cast"].append(actor)
            existing_ids.add(actor.get("name"))


def reset_database():
    """Wipe all vod_* tables so reseed produces a clean, consolidated DB."""
    VODDatabase.init_schema()
    conn = VODDatabase.get_connection()
    cur = conn.cursor()
    for table in ("vod_stills", "vod_cast", "vod_servers", "vod_episodes", "vod_seasons", "vod_media"):
        try:
            cur.execute(f"DELETE FROM {table};")
        except Exception as ex:  # table may not exist yet
            print(f"[db_cleanup] WARN clear {table}: {ex}")
    conn.commit()
    conn.close()
    print("[db_cleanup] SQLite vod_* tables cleared.")


def load_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # tolerate dict-of-items shaped like { "0": {...}, "1": {...} }
        items = list(data.values())
    else:
        items = data
    return items


def save_catalog(items):
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def main():
    dry_run = "--dry-run" in sys.argv
    if not os.path.exists(CATALOG_PATH):
        print(f"[db_cleanup] No catalog.json at {CATALOG_PATH}; nothing to do.")
        return 1

    items = load_catalog()
    cleaned, report = consolidate(items)

    print("=" * 64)
    print("[db_cleanup] Catalog consolidation report")
    print("=" * 64)
    print(f"  input items           : {report['input']}")
    print(f"  episode rows found    : {report['episode_rows']}")
    print(f"  movies (passthrough)  : {report['movies']}")
    print(f"  pre-existing series   : {report['parent_series']}")
    print(f"  consolidated parents  : {report['consolidated_series']}")
    for g in sorted(report["groups"], key=lambda x: x["episodes"], reverse=True)[:10]:
        print(f"   - {g['parent']}: {g['seasons']} season(s), {g['episodes']} eps")
    if len(report["groups"]) > 10:
        print(f"   ... and {len(report['groups']) - 10} more group(s).")
    print("=" * 64)

    if dry_run:
        print("[db_cleanup] --dry-run: catalog.json and DB left untouched.")
        return 0

    save_catalog(cleaned)
    print(f"[db_cleanup] Wrote cleaned catalog.json ({len(cleaned)} items).")

    # Reseed SQLite so the live API reflects the consolidated shape immediately.
    reset_database()
    VODDatabase.seed_initial_catalog(cleaned)
    print("[db_cleanup] Done. Restart the server to pick up fresh DB state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
