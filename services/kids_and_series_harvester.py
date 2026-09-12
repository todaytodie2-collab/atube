# -*- coding: utf-8 -*-
"""
A TuBe Kids & Series Harvester
Adds YouTube Kids curated ad-free cartoons and missing series categories (Turkish, Asian, Documentary).
"""

import json
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_JSON = os.path.join(PROJECT_ROOT, "catalog.json")
BUNDLED_JS = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

KIDS_AND_SERIES_ITEMS = [
    # YouTube Kids Cartoons
    {
        "id": "tom-and-jerry-kids",
        "title": "Tom and Jerry Kids Collection",
        "arabic_title": "توم وجيري كلاسيك للأطفال (بدون إعلانات)",
        "content_type": "series",
        "category": "كارتون للأطفال",
        "year": "2026",
        "rating": "★ 9.0 Kids",
        "quality": "1080p HD",
        "language": "العربية",
        "translation": "ناطق بالعربية",
        "synopsis": "مغامرات توم وجيري الممتعة المخصصة للأطفال بجودة عالية وبدون إعلانات مزعجة.",
        "poster": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=500&q=80",
        "backdrop": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1280&q=80",
        "total_seasons": 1,
        "seasons": [
            {
                "season_number": 1,
                "title": "الموسم الأول",
                "episodes": [
                    {
                        "episode_number": 1,
                        "title": "توم وجيري - الحلقة الأولى",
                        "duration": "15 دقيقة",
                        "thumbnail": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=300&q=80",
                        "servers": [
                            {"name": "سيرفر يوتيوب كيدز آمن 🎈", "stream_url": "https://www.youtube-nocookie.com/embed/kFF5hN6D93E?autoplay=1&modestbranding=1&rel=0", "site": "YouTubeKids", "badge": "Kids 🎈", "quality": "1080p HD", "isEmbed": True}
                        ]
                    },
                    {
                        "episode_number": 2,
                        "title": "توم وجيري - مغامرة القط والفأر",
                        "duration": "15 دقيقة",
                        "thumbnail": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=300&q=80",
                        "servers": [
                            {"name": "سيرفر يوتيوب كيدز آمن 🎈", "stream_url": "https://www.youtube-nocookie.com/embed/5qap5aO4i9A?autoplay=1&modestbranding=1&rel=0", "site": "YouTubeKids", "badge": "Kids 🎈", "quality": "1080p HD", "isEmbed": True}
                        ]
                    }
                ]
            }
        ],
        "servers": []
    },
    {
        "id": "spacetoon-classic-cartoons",
        "title": "Spacetoon Classic Cartoons",
        "arabic_title": "قناة سبيستون كارتون الطفولة الذكية",
        "content_type": "series",
        "category": "كارتون للأطفال",
        "year": "2026",
        "rating": "★ 9.4 Kids",
        "quality": "1080p HD",
        "language": "العربية",
        "translation": "ناطق بالعربية",
        "synopsis": "أروع أغاني وأبرز كارتون طفولتنا الجميل على سبيستون بدون إعلانات.",
        "poster": "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?w=500&q=80",
        "backdrop": "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?w=1280&q=80",
        "total_seasons": 1,
        "seasons": [
            {
                "season_number": 1,
                "title": "الموسم الأول",
                "episodes": [
                    {
                        "episode_number": 1,
                        "title": "ذكريات سبيستون - الباقة الذهبية",
                        "duration": "20 دقيقة",
                        "thumbnail": "https://images.unsplash.com/photo-1513542789411-b6a5d4f31634?w=300&q=80",
                        "servers": [
                            {"name": "سيرفر سبيستون آمن 🎈", "stream_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1&modestbranding=1&rel=0", "site": "YouTubeKids", "badge": "Kids 🎈", "quality": "1080p HD", "isEmbed": True}
                        ]
                    }
                ]
            }
        ],
        "servers": []
    },

    # Turkish Series (مسلسلات تركي)
    {
        "id": "kurulus-osman-season-5",
        "title": "Kurulus Osman Season 5",
        "arabic_title": "مسلسل المؤسس عثمان الموسم الخامس",
        "content_type": "series",
        "category": "turkish",
        "year": "2024",
        "rating": "★ 8.2 IMDb",
        "quality": "1080p FHD",
        "language": "التركية",
        "translation": "مترجم للعربية",
        "synopsis": "ملحمة قيام الدولة العثمانية ومعارك الغازي عثمان ضد الصليبيين والمغول.",
        "total_seasons": 1,
        "seasons": [
            {
                "season_number": 1,
                "title": "الموسم 5",
                "episodes": [
                    {"episode_number": 1, "title": "المؤسس عثمان - الحلقة 1", "duration": "120 دقيقة", "servers": [{"name": "سيرفر VIP ⭐", "stream_url": "https://vipserver.liiivideo.com/embed-osman1.html", "site": "Vipserver", "badge": "VIP ⭐", "quality": "1080p FHD", "isEmbed": True}]}
                ]
            }
        ],
        "servers": []
    },

    # Asian Series (مسلسلات آسيوي)
    {
        "id": "crash-landing-on-you",
        "title": "Crash Landing on You",
        "arabic_title": "مسلسل هبوط اضطراري للحب (كوري)",
        "content_type": "series",
        "category": "مسلسلات آسيوي",
        "year": "2020",
        "rating": "★ 8.7 IMDb",
        "quality": "1080p FHD",
        "language": "الكورية",
        "translation": "مترجم للعربية",
        "synopsis": "وريثة ثروة كورية جنوبية تهبط اضطرارياً بمظلتها في كوريا الشمالية وتقع في حب ضابط جيش.",
        "total_seasons": 1,
        "seasons": [
            {
                "season_number": 1,
                "title": "الموسم الأول",
                "episodes": [
                    {"episode_number": 1, "title": "هبوط اضطراري للحب - الحلقة 1", "duration": "75 دقيقة", "servers": [{"name": "سيرفر VIP ⭐", "stream_url": "https://vipserver.liiivideo.com/embed-crash1.html", "site": "Vipserver", "badge": "VIP ⭐", "quality": "1080p FHD", "isEmbed": True}]}
                ]
            }
        ],
        "servers": []
    }
]

def add_kids_and_series():
    print("[*] Adding Kids Cartoon & Missing Series items...")
    if not os.path.exists(CATALOG_JSON):
        return

    with open(CATALOG_JSON, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    existing_ids = {x.get("id") for x in catalog}

    for item in KIDS_AND_SERIES_ITEMS:
        if item["id"] not in existing_ids:
            catalog.append(item)
            print(f"[Harvester] Added: {item['arabic_title']}")

    with open(CATALOG_JSON, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    if os.path.exists(BUNDLED_JS):
        with open(BUNDLED_JS, 'r', encoding='utf-8') as f:
            js_content = f.read()

        match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', js_content, re.DOTALL)
        if match:
            prefix = match.group(1)
            suffix = match.group(3)
            new_js = prefix + json.dumps(catalog, ensure_ascii=False) + ";" + suffix
            with open(BUNDLED_JS, 'w', encoding='utf-8') as f:
                f.write(new_js)

    print("[*] Kids & Series Harvester finished successfully!")

if __name__ == "__main__":
    add_kids_and_series()
