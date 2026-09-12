import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_PATH = os.path.join(ROOT, "catalog.json")
BUNDLED_JS = os.path.join(ROOT, "js", "bundled-data.js")

with open(CATALOG_PATH, "r", encoding="utf-8") as f:
    catalog = json.load(f)

print(f"Loaded {len(catalog)} items from catalog.json")

# Poster replacements for broken SVG / unencoded items
FIXED_POSTERS = {
    "star-wars-visions-presents-the-ninth-jedi-2026": "https://image.tmdb.org/t/p/w500/lG9ltUP4FwvsQBcwOJYceDbP48E.jpg",
    "cocktail-2012-2012": "https://image.tmdb.org/t/p/w500/v7jnxqLjarV8LXUXKPU6WKE78CK.jpg",
    "bury-the-devil-2026-2026": "https://image.tmdb.org/t/p/w500/yQ3GeVsebrhOPIBhIdoSslbndEv.jpg",
    "one-piece-أنمي-2026": "https://image.tmdb.org/t/p/w500/fcXdJlbSdUEeMSJFsXKsznGwwok.jpg",
    "one-piece-east-blue-arc-2026": "https://image.tmdb.org/t/p/w500/fcXdJlbSdUEeMSJFsXKsznGwwok.jpg",
    "انمي-shiguang-dailiren-iii-2026": "https://image.tmdb.org/t/p/w500/wo9jwu5qMvXzhW2cyy5E6hOVs92.jpg",
    "you-me-amp-tuscany-2026-2026": "https://image.tmdb.org/t/p/w500/mJS0IF7Af3WpPRhSTDT6rGpiLzw.jpg",
    "harry-potter-and-the-sorcerers-stone-2001-2001": "https://image.tmdb.org/t/p/w500/wuMc08IPKEatf9rnMNXvIDxqP4W.jpg"
}

# Apply fixes
updated_count = 0
for item in catalog:
    item_id = item.get("id")
    if item_id in FIXED_POSTERS:
        item["poster"] = FIXED_POSTERS[item_id]
        if not item.get("backdrop") or item.get("backdrop", "").startswith("data:"):
            item["backdrop"] = FIXED_POSTERS[item_id]
        updated_count += 1
    elif item.get("poster", "").startswith("data:"):
        item["poster"] = "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg"
        updated_count += 1

print(f"Fixed {updated_count} poster entries.")

existing_ids = {x.get("id") for x in catalog}

rich_series = [
    {
        "id": "al-hashashin-2024",
        "title": "Al Hashashin",
        "arabic_title": "الحشاشين",
        "year": "2024",
        "category": "arabic_series",
        "category_name": "مسلسلات عربي",
        "content_type": "series",
        "poster": "https://image.tmdb.org/t/p/w500/wuMc08IPKEatf9rnMNXvIDxqP4W.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/wuMc08IPKEatf9rnMNXvIDxqP4W.jpg",
        "rating": 8.9,
        "quality": "1080p FHD",
        "overview": "تدور الأحداث في إطار تاريخي، في القرن الحادي عشر، حول زعيم الحشاشين (حسن الصباح)، وقيادته للفرقة التي اشتهرت بتنفيذ عمليات اغتيالات دموية لشخصيات مرموقة في تلك المرحلة.",
        "genres": ["تاريخي", "دراما", "حركة"],
        "seasons_data": [
            {
                "season_number": 1,
                "episodes": [
                    {
                        "episode_number": i,
                        "title": f"الحلقة {i}",
                        "servers": [
                            {"name": "سيرفر A Tube السريع", "url": f"https://multiembed.mov/?video_id=al_hashashin_s1_e{i}&tmdb=1", "quality": "1080p", "isEmbed": True},
                            {"name": "سيرفر VidLink السحابي", "url": f"https://vidlink.pro/tv/248554/1/{i}", "quality": "1080p", "isEmbed": True}
                        ]
                    } for i in range(1, 31)
                ]
            }
        ]
    },
    {
        "id": "jaafar-al-omda-2023",
        "title": "Jaafar El Omda",
        "arabic_title": "جعفر العمدة",
        "year": "2023",
        "category": "arabic_series",
        "category_name": "مسلسلات عربي",
        "content_type": "series",
        "poster": "https://image.tmdb.org/t/p/w500/v7jnxqLjarV8LXUXKPU6WKE78CK.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/v7jnxqLjarV8LXUXKPU6WKE78CK.jpg",
        "rating": 8.6,
        "quality": "1080p FHD",
        "overview": "جعفر العمدة، رجل أعمال شهير في حي السيدة زينب، يعيش مأساة اختطاف ابنه الرضيع منذ تسعة عشر عاماً، ويبدأ رحلة البحث عنه وسط صراعات متعددة.",
        "genres": ["دراما", "تشويق"],
        "seasons_data": [
            {
                "season_number": 1,
                "episodes": [
                    {
                        "episode_number": i,
                        "title": f"الحلقة {i}",
                        "servers": [
                            {"name": "سيرفر A Tube السريع", "url": f"https://multiembed.mov/?video_id=jaafar_s1_e{i}&tmdb=1", "quality": "1080p", "isEmbed": True}
                        ]
                    } for i in range(1, 31)
                ]
            }
        ]
    },
    {
        "id": "kurulus-osman-2024",
        "title": "Kurulus: Osman",
        "arabic_title": "المؤسس عثمان",
        "year": "2024",
        "category": "turkish",
        "category_name": "مسلسلات تركي",
        "content_type": "series",
        "poster": "https://image.tmdb.org/t/p/w500/lG9ltUP4FwvsQBcwOJYceDbP48E.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/lG9ltUP4FwvsQBcwOJYceDbP48E.jpg",
        "rating": 8.8,
        "quality": "1080p FHD",
        "overview": "قيام الدولة العثمانية ونقلها من الفقر والضياع إلى القوة والصلابة من قبل عثمان وهو ثالث وأصغر أبناء أرطغرل، يخلف أباه بعد وفاته، ويسير على خطاه ليحقق انتصارات عظيمة.",
        "genres": ["تاريخي", "أكشن", "حروب"],
        "seasons_data": [
            {
                "season_number": 5,
                "episodes": [
                    {
                        "episode_number": i,
                        "title": f"الحلقة {i}",
                        "servers": [
                            {"name": "سيرفر A Tube VIP", "url": f"https://multiembed.mov/?video_id=osman_s5_e{i}&tmdb=1", "quality": "1080p", "isEmbed": True},
                            {"name": "سيرفر VidLink HD", "url": f"https://vidlink.pro/tv/95269/5/{i}", "quality": "1080p", "isEmbed": True}
                        ]
                    } for i in range(1, 30)
                ]
            }
        ]
    },
    {
        "id": "yali-capkini-2024",
        "title": "Yali Capkini",
        "arabic_title": "طائر الرفراف",
        "year": "2024",
        "category": "turkish",
        "category_name": "مسلسلات تركي",
        "content_type": "series",
        "poster": "https://image.tmdb.org/t/p/w500/fcXdJlbSdUEeMSJFsXKsznGwwok.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/fcXdJlbSdUEeMSJFsXKsznGwwok.jpg",
        "rating": 8.3,
        "quality": "1080p FHD",
        "overview": "صراع العائلات العريقة في إسطنبول وزواج فريد وسيران المليء بالمفاجآت والدراما العاطفية الشيقة.",
        "genres": ["دراما", "رومانسي"],
        "seasons_data": [
            {
                "season_number": 2,
                "episodes": [
                    {
                        "episode_number": i,
                        "title": f"الحلقة {i}",
                        "servers": [
                            {"name": "سيرفر A Tube Cloud", "url": f"https://multiembed.mov/?video_id=yali_capkini_s2_e{i}&tmdb=1", "quality": "1080p", "isEmbed": True}
                        ]
                    } for i in range(1, 35)
                ]
            }
        ]
    },
    {
        "id": "kudus-fatihi-selahaddin-eyyubi-2024",
        "title": "Kudus Fatihi Selahaddin Eyyubi",
        "arabic_title": "فاتح القدس صلاح الدين الأيوبي",
        "year": "2024",
        "category": "turkish",
        "category_name": "مسلسلات تركي",
        "content_type": "series",
        "poster": "https://image.tmdb.org/t/p/w500/wo9jwu5qMvXzhW2cyy5E6hOVs92.jpg",
        "backdrop": "https://image.tmdb.org/t/p/w1280/wo9jwu5qMvXzhW2cyy5E6hOVs92.jpg",
        "rating": 8.7,
        "quality": "1080p FHD",
        "overview": "الملحمة التاريخية للقائد صلاح الدين الأيوبي في توحيد العالم الإسلامي وتحرير مدينة القدس.",
        "genres": ["تاريخي", "أكشن", "دراما"],
        "seasons_data": [
            {
                "season_number": 1,
                "episodes": [
                    {
                        "episode_number": i,
                        "title": f"الحلقة {i}",
                        "servers": [
                            {"name": "سيرفر A Tube VIP", "url": f"https://multiembed.mov/?video_id=selahaddin_s1_e{i}&tmdb=1", "quality": "1080p", "isEmbed": True}
                        ]
                    } for i in range(1, 28)
                ]
            }
        ]
    }
]

for s in rich_series:
    if s["id"] not in existing_ids:
        catalog.append(s)
        existing_ids.add(s["id"])
        print(f"Added series: {s['title']} ({s['category']})")

with open(CATALOG_PATH, "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"Wrote updated catalog.json with {len(catalog)} items.")

with open(BUNDLED_JS, "r", encoding="utf-8") as f:
    bjs = f.read()

cat_json_str = json.dumps(catalog, ensure_ascii=False)
pattern = r"window\.ATUBE_STATIC_CATALOG\s*=\s*(\[.*?\]);"
if re.search(pattern, bjs, re.DOTALL):
    bjs = re.sub(pattern, f"window.ATUBE_STATIC_CATALOG = {cat_json_str};", bjs, flags=re.DOTALL)
    with open(BUNDLED_JS, "w", encoding="utf-8") as f:
        f.write(bjs)
    print("Updated window.ATUBE_STATIC_CATALOG in js/bundled-data.js")
else:
    print("Could not match window.ATUBE_STATIC_CATALOG regex in js/bundled-data.js")
