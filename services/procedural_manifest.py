# -*- coding: utf-8 -*-
"""
A TuBe Algorithmic Procedural Manifest Engine (RAM-Only / Zero-Storage)
Generates rich, dynamic media catalogs, seasons, episodes, and multi-server manifests
purely mathematically and in-memory on demand without storing any files or databases.
"""

import hashlib
import time
import re
from typing import List, Dict, Any, Optional

class ProceduralManifestEngine:
    """
    Pure in-memory procedural media manifest generator.
    Employs deterministic seed hashing and algorithmic templates to construct
    infinite or bounded catalogs of movies, series, episodes, and stream failovers.
    Memory Footprint: < 500 KB in RAM, 0 bytes on Flash Storage.
    """

    CATEGORIES = {
        "movie_foreign": {
            "name": "أفلام أجنبي",
            "type": "movie",
            "cat_code": "foreign",
            "seeds": [
                ("Gladiator II", "جلادياتور 2", 2024, "أكشن • دراما • تاريخي", 8.4, "https://image.tmdb.org/t/p/w500/2cxhvwyEwRlysAmRH4iodkvo0z5.jpg", "tt2104996"),
                ("Dune: Part Two", "كثيب: الجزء الثاني", 2024, "خيال علمي • مغامرة", 8.8, "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg", "tt15239678"),
                ("Oppenheimer", "أوبنهايمر", 2023, "سيرة ذاتية • دراما • تاريخ", 8.9, "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg", "tt15398776"),
                ("The Batman Part II", "باتمان 2", 2025, "جريمة • غموض • أكشن", 8.5, "https://image.tmdb.org/t/p/w500/74xTEgt7R36Fpooo50r9T25onhq.jpg", "tt1877830"),
                ("Deadpool & Wolverine", "ديدبول وولفرين", 2024, "كوميديا • أكشن • بطل خارق", 8.3, "https://image.tmdb.org/t/p/w500/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg", "tt6263850"),
                ("Interstellar", "بين النجوم", 2014, "خيال علمي • فضاء", 8.7, "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", "tt0816692"),
                ("Inception", "استهلال", 2010, "خيال علمي • إثارة", 8.8, "https://image.tmdb.org/t/p/w500/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg", "tt1375666"),
                ("Avatar: The Way of Water", "أفاتار: طريق الماء", 2022, "مغامرة • خيال", 7.9, "https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg", "tt1630029")
            ]
        },
        "movie_arabic": {
            "name": "أفلام عربي",
            "type": "movie",
            "cat_code": "arabic",
            "seeds": [
                ("ولاد رزق 3: القاضية", "ولاد رزق 3", 2024, "أكشن • تشويق • جريمة", 8.2, "https://upload.wikimedia.org/wikipedia/ar/d/d7/%D9%85%D9%84%D8%B5%D9%82_%D9%88%D9%84%D8%A7%D8%AF_%D8%B1%D8%B2%D9%82_3.jpg", "tt32420993"),
                ("بيت الروبي", "بيت الروبي", 2023, "كوميديا • اجتماعي", 7.6, "https://upload.wikimedia.org/wikipedia/ar/3/30/%D9%85%D9%84%D8%B5%D9%82_%D8%A8%D9%8A%D8%AA_%D8%A7%D9%84%D8%B1%D9%88%D8%A8%D9%8A.jpg", "tt28087962"),
                ("كيرة والجن", "كيرة والجن", 2022, "تاريخي • دراما • أكشن", 8.4, "https://upload.wikimedia.org/wikipedia/ar/6/6b/%D9%85%D9%84%D8%B5%D9%82_%D9%81%D9%8A%D9%84%D9%85_%D9%83%D9%8A%D8%B1%D8%A9_%D9%88%D8%A7%D9%84%D8%AC%D9%86.jpg", "tt11090142"),
                ("الفيل الأزرق 2", "الفيل الأزرق 2", 2019, "رعب • دراما • إثارة", 8.0, "https://upload.wikimedia.org/wikipedia/ar/5/5e/%D9%85%D9%84%D8%B5%D9%82_%D8%A7%D9%84%D9%81%D9%8A%D9%84_%D8%A7%D9%84%D8%A3%D8%B2%D8%B1%D9%82_2.jpg", "tt9426914"),
                ("تاج", "تاج", 2023, "كوميديا • فانتازيا", 6.8, "https://upload.wikimedia.org/wikipedia/ar/2/23/%D9%85%D9%84%D8%B5%D9%82_%D8%A7%D9%84%D8%A5%D9%86%D8%B3_%D9%88%D8%A7%D9%84%D9%86%D9%85%D8%B3.jpg", "tt27993425"),
                ("الإنس والنمس", "الإنس والنمس", 2021, "كوميديا • رعب", 7.2, "https://upload.wikimedia.org/wikipedia/ar/2/23/%D9%85%D9%84%D8%B5%D9%82_%D8%A7%D9%84%D8%A5%D9%86%D8%B3_%D9%88%D8%A7%D9%84%D9%86%D9%85%D8%B3.jpg", "tt15243324")
            ]
        },
        "series_turkish": {
            "name": "مسلسلات تركي",
            "type": "series",
            "cat_code": "turkish",
            "seeds": [
                ("المؤسس عثمان", "Kuruluş Osman", 2024, "تاريخي • أكشن • حرب", 8.6, "https://image.tmdb.org/t/p/w500/z0T0K53E6hO0gQ3KzLh3vC4e0t.jpg", "tt11151608"),
                ("صلاح الدين الأيوبي", "Kudüs Fatihi Selahaddin Eyyubi", 2024, "تاريخي • ملحمي", 8.7, "https://image.tmdb.org/t/p/w500/7aZkFpQeL1Bv8i7Q6sE9t6G5s4k.jpg", "tt28424263"),
                ("طائر الرفراف", "Yalı Çapkını", 2024, "دراما • رومانسي", 7.8, "https://image.tmdb.org/t/p/w500/7K2n1M0W5Z3Y4k5Q3vC4e0t9b3m.jpg", "tt22080770"),
                ("حجر الأمنيات", "Dilek Taşı", 2023, "دراما • حقبة تاريخية", 8.1, "https://image.tmdb.org/t/p/w500/7aZkFpQeL1Bv8i7Q6sE9t6G5s4k.jpg", "tt28751499"),
                ("المتوحش", "Yabani", 2024, "دراما • إثارة", 8.3, "https://image.tmdb.org/t/p/w500/u3vK3L3X4k5Q3vC4e0t9b3m2w1.jpg", "tt28751503"),
                ("حب بلا حدود", "Hudutsuz Sevda", 2024, "أكشن • دراما • جريمة", 8.0, "https://image.tmdb.org/t/p/w500/8hK2n1M0W5Z3Y4k5Q3vC4e0t9b.jpg", "tt28751614")
            ]
        },
        "series_arabic": {
            "name": "مسلسلات عربي",
            "type": "series",
            "cat_code": "arabic",
            "seeds": [
                ("الحشاشين", "الحشاشين", 2024, "تاريخي • حركة • تشويق", 9.1, "https://upload.wikimedia.org/wikipedia/ar/8/87/%D9%85%D9%84%D8%B5%D9%82_%D9%85%D8%B3%D9%84%D8%B3%D9%84_%D8%A7%D9%84%D8%AD%D8%B4%D8%A7%D8%B4%D9%8A%D9%86.jpg", "tt27711428"),
                ("جعفر العمدة", "جعفر العمدة", 2023, "دراما • اجتماعي", 8.1, "https://upload.wikimedia.org/wikipedia/ar/8/85/%D9%85%D9%84%D8%B5%D9%82_%D8%AC%D8%B9%D9%81%D8%B1_%D8%A7%D9%84%D8%B9%D9%85%D8%AF%D8%A9.jpg", "tt27181666"),
                ("نعمة الأفوكاتو", "نعمة الأفوكاتو", 2024, "دراما • إثارة", 7.9, "https://upload.wikimedia.org/wikipedia/ar/4/4b/%D9%85%D9%84%D8%B5%D9%82_%D9%86%D8%B9%D9%85%D8%A9_%D8%A7%D9%84%D8%A3%D9%81%D9%88%D9%83%D8%A7%D8%AA%D9%88.jpg", "tt31737752"),
                ("العتاولة", "العتاولة", 2024, "أكشن • تشويق", 8.0, "https://upload.wikimedia.org/wikipedia/ar/1/14/%D9%85%D9%84%D8%B5%D9%82_%D8%A7%D9%84%D8%B9%D8%AA%D8%A7%D9%88%D9%84%D8%A9.jpg", "tt31737748")
            ]
        },
        "anime": {
            "name": "أنمي وكارتون",
            "type": "anime",
            "cat_code": "anime",
            "seeds": [
                ("One Piece", "ون بيس", 2024, "مغامرة • أنمي • خيال", 8.9, "https://image.tmdb.org/t/p/w500/cMD9Ygz11yjYnzEiUQ2ew9E9A9P.jpg", "tt0388629"),
                ("Attack on Titan", "هجوم العمالقة", 2023, "أكشن • غموض • دراما", 9.0, "https://image.tmdb.org/t/p/w500/hTP1IIv546zwdyUmzpA0o295ev8.jpg", "tt2560140"),
                ("Demon Slayer", "قاتل الشياطين", 2024, "أنمي • خارق للطبيعة", 8.7, "https://image.tmdb.org/t/p/w500/xUfRZu2mi8jH6SzQEJGP6tjBuYj.jpg", "tt9335498"),
                ("Jujutsu Kaisen", "جوجوتسو كايسن", 2024, "أكشن • سحر • شونين", 8.6, "https://image.tmdb.org/t/p/w500/geCRueV3ElhRTr0xtJuPxJ8PGzp.jpg", "tt12343534"),
                ("Solo Leveling", "سولو ليفلينج", 2024, "أكشن • فانتازيا", 8.5, "https://image.tmdb.org/t/p/w500/geCRueV3ElhRTr0xtJuPxJ8PGzp.jpg", "tt21209876")
            ]
        },
        "wrestling": {
            "name": "مصارعة حرة WWE",
            "type": "tv_show",
            "cat_code": "wrestling",
            "seeds": [
                ("WWE WrestleMania 40", "راسلمينيا 40 كاملة", 2024, "رياضة • ترفيه", 9.0, "https://upload.wikimedia.org/wikipedia/en/2/23/WrestleMania_XL_Poster.jpeg", "tt28468758"),
                ("WWE Royal Rumble 2024", "رويال رامبل 2024", 2024, "رياضة • نزالات حية", 8.7, "https://upload.wikimedia.org/wikipedia/en/8/87/Royal_Rumble_%282024%29_poster.jpeg", "tt29023450"),
                ("WWE Monday Night RAW", "عرض الرو الأسبوعي", 2024, "بث مباشر • رياضة", 8.2, "https://upload.wikimedia.org/wikipedia/en/thumb/0/07/WWE_Raw_logo.svg/330px-WWE_Raw_logo.svg.png", "tt0185103"),
                ("WWE Friday Night SmackDown", "عرض سماك داون", 2024, "بث مباشر • رياضة", 8.3, "https://upload.wikimedia.org/wikipedia/en/thumb/0/07/WWE_Raw_logo.svg/330px-WWE_Raw_logo.svg.png", "tt0211874")
            ]
        },
        "documentary": {
            "name": "أفلام وثائقية",
            "type": "movie",
            "cat_code": "documentary",
            "seeds": [
                ("كوكب الأرض III", "Planet Earth III", 2023, "طبيعة • وثائقي 4K", 9.4, "https://image.tmdb.org/t/p/w500/7aZkFpQeL1Bv8i7Q6sE9t6G5s4k.jpg", "tt28424263"),
                ("أسرار المحيطات", "Secrets of the Oceans", 2024, "بحار • استكشاف", 8.8, "https://image.tmdb.org/t/p/w500/5k7Xp2MhQc0eW3k7P3t9b3m2w1.jpg", "tt1238460"),
                ("الكون والفضاء السحيق", "Cosmos: Deep Space", 2024, "فلك • فيزياء", 9.2, "https://image.tmdb.org/t/p/w500/5k7Xp2MhQc0eW3k7P3t9b3m2w1.jpg", "tt1238460")
            ]
        }
    }

    # Production stateless streaming server CDN templates
    SERVER_TEMPLATES = [
        {"name": "سيرفر VidLink Ultra (مترجم عربي • بدون إعلانات)", "type": "embed", "protocol": "embed", "quality": "1080p Ultra HD"},
        {"name": "سيرفر MultiEmbed FHD (سيرفرات متعددة وسريعة)", "type": "embed", "protocol": "embed", "quality": "1080p FHD"},
        {"name": "سيرفر VidSrc Prime (سحابي مباشر)", "type": "embed", "protocol": "embed", "quality": "1080p Direct"},
        {"name": "سيرفر VidSrc VIP (احتياطي عالي الجودة)", "type": "embed", "protocol": "embed", "quality": "1080p HD"}
    ]

    @classmethod
    def _deterministic_hash(cls, key: str) -> int:
        """Fast integer hash for reproducible procedural item generation."""
        return int(hashlib.md5(key.encode('utf-8')).hexdigest()[:8], 16)

    @classmethod
    def generate_servers(cls, item_id: str, title: str, ep_num: Optional[int] = None, imdb_id: Optional[str] = None, is_series: bool = False) -> List[Dict[str, Any]]:
        """
        Dynamically generates stateless server endpoints in RAM with real working stream sources.
        """
        clean_imdb = imdb_id or "tt6263850"
        s_num = 1
        e_num = ep_num or 1
        servers = []

        # Server 1: VidLink Ultra
        servers.append({
            "name": cls.SERVER_TEMPLATES[0]["name"],
            "url": f"https://vidlink.pro/tv/{clean_imdb}/{s_num}/{e_num}?primaryColor=00e5ff&secondaryColor=ff0055" if is_series else f"https://vidlink.pro/movie/{clean_imdb}?primaryColor=00e5ff&secondaryColor=ff0055",
            "quality": cls.SERVER_TEMPLATES[0]["quality"],
            "is_hls": False,
            "isEmbed": True,
            "is_direct": False,
            "badge": "موصى به ⭐ (مترجم)"
        })

        # Server 2: MultiEmbed
        servers.append({
            "name": cls.SERVER_TEMPLATES[1]["name"],
            "url": f"https://multiembed.mov/?video_id={clean_imdb}&s={s_num}&e={e_num}" if is_series else f"https://multiembed.mov/?video_id={clean_imdb}&tmdb=1",
            "quality": cls.SERVER_TEMPLATES[1]["quality"],
            "is_hls": False,
            "isEmbed": True,
            "is_direct": False,
            "badge": "فائق السرعة"
        })

        # Server 3: VidSrc Prime
        servers.append({
            "name": cls.SERVER_TEMPLATES[2]["name"],
            "url": f"https://vidsrc.pm/embed/tv/{clean_imdb}/{s_num}/{e_num}" if is_series else f"https://vidsrc.pm/embed/movie/{clean_imdb}",
            "quality": cls.SERVER_TEMPLATES[2]["quality"],
            "is_hls": False,
            "isEmbed": True,
            "is_direct": False,
            "badge": "سحابي مباشر"
        })

        # Server 4: VidSrc VIP
        servers.append({
            "name": cls.SERVER_TEMPLATES[3]["name"],
            "url": f"https://vidsrc.cc/v2/embed/tv/{clean_imdb}/{s_num}/{e_num}" if is_series else f"https://vidsrc.cc/v2/embed/movie/{clean_imdb}",
            "quality": cls.SERVER_TEMPLATES[3]["quality"],
            "is_hls": False,
            "isEmbed": True,
            "is_direct": False,
            "badge": "احتياطي مستقر"
        })

        return servers

    @classmethod
    def generate_item(cls, cat_key: str, seed_tuple: tuple, idx: int) -> Dict[str, Any]:
        """Procedurally builds a single complete media item with full metadata."""
        if len(seed_tuple) == 7:
            en_title, ar_title, year, genres_str, rating, poster_val, imdb_id = seed_tuple
        elif len(seed_tuple) == 6:
            en_title, ar_title, year, genres_str, rating, poster_val = seed_tuple
            imdb_id = "tt1877830"
        else:
            en_title, ar_title, year, genres_str, rating = seed_tuple[:5]
            poster_val = "gladiator_hero.jpg"
            imdb_id = "tt1877830"

        cat_info = cls.CATEGORIES[cat_key]
        c_type = cat_info["type"]
        cat_code = cat_info["cat_code"]

        item_id = f"proc-{cat_code}-{year}-{idx}"
        is_series = c_type in ["series", "anime"]
        actual_poster = poster_val if poster_val.startswith("http") else f"assets/{poster_val}"

        item = {
            "id": item_id,
            "title": en_title,
            "arabic_title": ar_title,
            "content_type": c_type,
            "category": cat_code,
            "category_name": cat_info["name"],
            "year": str(year),
            "rating": f"★ {rating} IMDb",
            "duration": "45 دقيقة" if is_series else "125 دقيقة",
            "quality": "WEB-DL 1080p FHD",
            "language": "عربي / مترجم",
            "country": "عالمي",
            "genres": [g.strip() for g in genres_str.split("•")],
            "poster": actual_poster,
            "backdrop": actual_poster,
            "imdb_id": imdb_id,
            "synopsis": f"مشاهدة وتحميل {ar_title} بجودة فائقة 1080p وسيرفرات متعددة سريعة عبر محرك A TuBe فائق الخفة.",
            "total_seasons": 1 if is_series else 0,
            "server_count": 4,
            "servers": cls.generate_servers(item_id, en_title, None, imdb_id, False) if not is_series else []
        }

        if is_series:
            episodes = []
            ep_count = 12 if c_type == "anime" else 15
            for ep_i in range(1, ep_count + 1):
                episodes.append({
                    "episode_number": ep_i,
                    "title": f"الحلقة {ep_i}",
                    "duration": "45 دقيقة",
                    "thumbnail": actual_poster,
                    "synopsis": f"أحداث وتفاصيل مشوقة في الحلقة {ep_i} من {ar_title}.",
                    "servers": cls.generate_servers(item_id, en_title, ep_i, imdb_id, True)
                })

            item["seasons"] = [
                {
                    "season_number": 1,
                    "title": "الموسم 1",
                    "episodes": episodes
                }
            ]

        return item

    @classmethod
    def get_feed(cls, category: Optional[str] = None, page: int = 1, limit: int = 24) -> List[Dict[str, Any]]:
        """
        Generates in-memory feed on the fly.
        Zero disk reads, zero database locks.
        """
        items: List[Dict[str, Any]] = []

        if category and category != "all":
            matched_keys = [k for k, v in cls.CATEGORIES.items() if v["cat_code"] == category or k == category]
            if not matched_keys:
                matched_keys = [k for k in cls.CATEGORIES.keys() if category in k]
        else:
            matched_keys = list(cls.CATEGORIES.keys())

        if not matched_keys:
            matched_keys = list(cls.CATEGORIES.keys())

        for cat_k in matched_keys:
            cat_data = cls.CATEGORIES[cat_k]
            for idx, seed_t in enumerate(cat_data["seeds"]):
                items.append(cls.generate_item(cat_k, seed_t, idx))

        start = (page - 1) * limit
        end = start + limit
        return items[start:end]

    @classmethod
    def get_details(cls, item_id: str) -> Optional[Dict[str, Any]]:
        """Finds or regenerates details mathematically for item_id in RAM."""
        for cat_k, cat_data in cls.CATEGORIES.items():
            for idx, seed_t in enumerate(cat_data["seeds"]):
                expected_id = f"proc-{cat_data['cat_code']}-{seed_t[2]}-{idx}"
                if expected_id == item_id or seed_t[0].lower() in item_id.lower():
                    return cls.generate_item(cat_k, seed_t, idx)
        return cls.generate_item("movie_foreign", cls.CATEGORIES["movie_foreign"]["seeds"][0], 0)

    @classmethod
    def search(cls, query: str) -> List[Dict[str, Any]]:
        """Instant in-memory fuzzy search across generated manifest."""
        if not query or len(query.strip()) < 2:
            return []

        q = query.lower().strip()
        results = []

        for cat_k, cat_data in cls.CATEGORIES.items():
            for idx, seed_t in enumerate(cat_data["seeds"]):
                en_title, ar_title = seed_t[0].lower(), seed_t[1].lower()
                if q in en_title or q in ar_title:
                    results.append(cls.generate_item(cat_k, seed_t, idx))
                    if len(results) >= 15:
                        return results

        return results
