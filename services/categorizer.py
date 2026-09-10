# -*- coding: utf-8 -*-
"""
A TuBe Smart Categorization Engine
Routes content into correct Arabic taxonomy buckets:
- Movies: Foreign, Arabic, Turkish, Indian, Asian
- Series: Foreign, Arabic, Turkish, Indian (separate from foreign), Korean/Asian
- Special: Anime, Wrestling, Documentaries, Plays, TV Shows
"""

import re
from typing import Optional


class SmartCategorizer:
    """
    Intelligent content classification system.
    Prevents cross-category contamination (e.g., Indian series in Foreign series).
    Uses multi-signal detection: title keywords, language patterns, genre hints.
    """

    # Arabic normalization map
    AR_NORM = str.maketrans({
        'أ': 'ا', 'إ': 'ا', 'آ': 'ا',
        'ة': 'ه', 'ى': 'ي', 'ؤ': 'و',
    })

    # Category keyword dictionaries
    CATEGORY_SIGNALS = {
        'wrestling': {
            'keywords': ['wwe', 'raw', 'smackdown', 'wrestlemania', 'royal rumble',
                        'مصارع', 'مصارعة', 'مصارعة حرة', 'wwe raw', 'wwe smackdown',
                        'nxt', 'aew', 'impact wrestling', 'roh'],
            'weight': 10
        },
        'anime': {
            'keywords': ['انمي', 'anime', 'رسوم متحركة', 'كرتون', 'كارتون',
                        'dragon ball', 'one piece', 'naruto', 'attack on titan',
                        'demon slayer', 'jujutsu kaisen', 'spy x family',
                        'مانغا', 'seasons', 'حلقات أنمي'],
            'weight': 10
        },
        'documentary': {
            'keywords': ['وثائقي', 'documentary', 'وثائقيات', 'وثائقي',
                        'planet earth', 'cosmos', 'blue planet', 'our planet'],
            'weight': 9
        },
        'plays': {
            'keywords': ['مسرحي', 'مسرح', 'مسرحية', 'مسرحيات',
                        'play', 'theater', 'مسرحيات كوميدية'],
            'weight': 9
        },
        'turkish': {
            'keywords': ['تركي', 'turkish', 'dizi', 'قيامة عثمان', 'طائر الرفراف',
                        'المتوحش', 'اسطنبول', 'حربnee', 'الحر',
                        'مؤسس عثمان', 'السيد الخطأ', 'الحرب'],
            'weight': 8
        },
        'indian': {
            'keywords': ['هندي', 'indian', 'bollywood', 'tollywood', 'بوليوود',
                        'شاروخان', 'سلمان خان', 'عامر خان', 'priyanka',
                        'deepika', 'ranveer', 'alia', 'karan johar',
                        'bahubali', 'rrr', 'pushpa', 'kgf', 'pathaan',
                        'jawan', 'animal', 'dangal', '3 idiots'],
            'weight': 8
        },
        'korean': {
            'keywords': ['كوري', 'korean', 'كورية', 'kor',
                        'squid game', 'k-drama', 'kdrama',
                        'jun ho', 'song kang', 'kim soo hyun',
                        'parasite', 'crash landing on you',
                        'goblin', 'descendants of the sun'],
            'weight': 8
        },
        'asian': {
            'keywords': ['آسيوي', 'asian', 'اسيوي', 'صيني', 'chinese',
                        'ياباني', 'japanese', 'تايلندي', 'thai',
                        'هونج كونج', 'hong kong', 'wuxia', 'martial arts'],
            'weight': 6
        },
        'arabic': {
            'keywords': ['مصري', 'عربي', 'arabic', 'سوري', 'سعودي', 'خليجي',
                        'لبناني', 'أردني', 'عراقي', 'مغربي', 'تونسي',
                        'جزائري', 'ليبي', 'سوداني', 'يمني', 'فلسطيني',
                        'ولاد رزق', 'الفيل الازرق', 'الاختيار', 'الكبير اوي',
                        'بيت الروبي', 'lahazat harega', 'hob elbanat',
                        'مملكة bees', 'كازابلانكا', 'الفارس'],
            'weight': 7
        },
        'foreign': {
            'keywords': ['hollywood', 'اميركي', 'امريكي', 'اجنبي', 'اجنبية',
                        'foreign', 'western', 'غربي', 'انجليزي', 'english',
                        'فرنسي', 'french', 'اسباني', 'spanish',
                        'ألماني', 'german', 'ايطالي', 'italian',
                        'marvel', 'dc', 'disney', 'pixar', 'netflix',
                        'hbo', 'amazon', 'apple tv', 'paramount'],
            'weight': 5
        }
    }

    # Content type detection keywords
    SERIES_KEYWORDS = [
        'مسلسل', 'مسلسلات', 'series', 'حلقة', 'حلقات', 'الموسم', 'مواسم',
        'season', 'episode', 's01', 's02', 's03', 's1', 's2', 's3',
        'e01', 'e02', 'e03', 'e1', 'e2', 'e3', 'ep01', 'ep02',
        'ح1', 'ح2', 'ح3', 'ح4', 'ح5', 'ح6', 'ح7', 'ح8', 'ح9', 'ح10',
        'موسم 1', 'موسم 2', 'موسم 3', 'موسم 4', 'موسم 5',
        'part 1', 'part 2', 'part 3', 'جزء 1', 'جزء 2', 'جزء 3',
        'الحلقة 1', 'الحلقة 2', 'الحلقة 3', 'الحلقة 4', 'الحلقة 5',
        'episode 1', 'episode 2', 'episode 3', 'episode 4', 'episode 5',
        'ep ', 's0', 'e0', 'حلقة كاملة'
    ]

    @classmethod
    def _normalize(cls, text: str) -> str:
        """Normalizes Arabic text for consistent matching."""
        if not text:
            return ''
        return text.lower().translate(cls.AR_NORM).strip()

    @classmethod
    def detect_content_type(cls, title: str, content_type_hint: str = '') -> str:
        """
        Determines if content is a movie or series based on title patterns.
        Returns 'movie' or 'series'.
        """
        if content_type_hint in ['series', 'anime', 'tv_show']:
            return 'series'

        norm_title = cls._normalize(title)

        for keyword in cls.SERIES_KEYWORDS:
            if keyword in norm_title:
                return 'series'

        # Additional heuristics
        if re.search(r'\bS\d{1,2}\s*E\d{1,2}\b', title, re.IGNORECASE):
            return 'series'
        if re.search(r'Season\s*\d+', title, re.IGNORECASE):
            return 'series'
        if re.search(r'Episode\s*\d+', title, re.IGNORECASE):
            return 'series'

        return 'movie'

    @classmethod
    def classify(cls, title: str, arabic_title: str = '', content_type_hint: str = '',
                 genres: list = None, year: str = '') -> dict:
        """
        Full classification pipeline.
        Returns a dict with:
        - content_type: 'movie' or 'series'
        - category: one of the canonical categories
        - confidence: float 0-1
        - signals: list of matched signals for debugging
        """
        # Strip generic site/subbing noise words that distort language detection
        noise_pattern = r'ايجي\s*بست|ماي\s*سيما|مترجم|مدبلج|مشاهدة|تحميل|اون\s*لاين|بجودة|عالية|ايجي|فيديو|سيما|حلقة|موسم|كامل|فيلم|مسلسل'
        clean_title = re.sub(noise_pattern, '', f"{title} {arabic_title}", flags=re.IGNORECASE)

        combined = f"{clean_title} {' '.join(genres or [])}"
        norm_combined = cls._normalize(combined)

        # Step 1: Detect content type
        content_type = cls.detect_content_type(title, content_type_hint)

        # Step 2: Score each category
        scores = {}
        matched_signals = {}

        for category, config in cls.CATEGORY_SIGNALS.items():
            score = 0
            matched = []
            for keyword in config['keywords']:
                if keyword in norm_combined:
                    score += config['weight']
                    matched.append(keyword)
            scores[category] = score
            matched_signals[category] = matched

        # Step 3: Special case - Indian series should be separate from foreign series
        # If Indian score is high AND content_type is series, prefer 'indian_series'
        if (scores.get('indian', 0) >= 8 and content_type == 'series'):
            return {
                'content_type': 'series',
                'category': 'indian_series',
                'confidence': min(scores['indian'] / 20, 1.0),
                'signals': matched_signals.get('indian', [])
            }

        # Step 4: Korean series should be separate
        if (scores.get('korean', 0) >= 8 and content_type == 'series'):
            return {
                'content_type': 'series',
                'category': 'korean_series',
                'confidence': min(scores['korean'] / 20, 1.0),
                'signals': matched_signals.get('korean', [])
            }

        # Step 5: Find highest scoring category
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        if best_score >= 6:
            confidence = min(best_score / 20, 1.0)
            return {
                'content_type': content_type,
                'category': best_category,
                'confidence': confidence,
                'signals': matched_signals.get(best_category, [])
            }

        # Step 6: Fallback logic
        if content_type == 'series':
            # Default series to foreign unless Arabic detected
            if scores.get('arabic', 0) > 0:
                return {
                    'content_type': 'series',
                    'category': 'arabic_series',
                    'confidence': 0.5,
                    'signals': matched_signals.get('arabic', [])
                }
            return {
                'content_type': 'series',
                'category': 'foreign_series',
                'confidence': 0.4,
                'signals': []
            }

        # Default movie classification
        if scores.get('arabic', 0) > 0:
            return {
                'content_type': 'movie',
                'category': 'arabic',
                'confidence': 0.6,
                'signals': matched_signals.get('arabic', [])
            }

        return {
            'content_type': 'movie',
            'category': 'foreign',
            'confidence': 0.3,
            'signals': []
        }

    @classmethod
    def get_category_metadata(cls, category: str) -> dict:
        """
        Returns display metadata for a given category slug.
        """
        metadata = {
            'foreign': {
                'display_name_ar': 'أفلام أجنبي',
                'display_name_en': 'Foreign Movies',
                'icon': '🌍',
                'color': '#00e5ff'
            },
            'arabic': {
                'display_name_ar': 'أفلام عربي',
                'display_name_en': 'Arabic Movies',
                'icon': '🎬',
                'color': '#ff2a44'
            },
            'arabic_series': {
                'display_name_ar': 'مسلسلات عربي',
                'display_name_en': 'Arabic Series',
                'icon': '📺',
                'color': '#ff6b6b'
            },
            'turkish': {
                'display_name_ar': 'مسلسلات تركي',
                'display_name_en': 'Turkish Series',
                'icon': '🇹🇷',
                'color': '#ff9500'
            },
            'indian': {
                'display_name_ar': 'أفلام هندي',
                'display_name_en': 'Indian Movies',
                'icon': '🇮🇳',
                'color': '#ffcc00'
            },
            'indian_series': {
                'display_name_ar': 'مسلسلات هندي',
                'display_name_en': 'Indian Series',
                'icon': '🎭',
                'color': '#ff9900'
            },
            'korean_series': {
                'display_name_ar': 'مسلسلات كوري',
                'display_name_en': 'Korean Series',
                'icon': '🇰🇷',
                'color': '#ff6b9d'
            },
            'asian': {
                'display_name_ar': 'أفلام آسيوي',
                'display_name_en': 'Asian Movies',
                'icon': '🌏',
                'color': '#7b68ee'
            },
            'anime': {
                'display_name_ar': 'أنمي وكارتون',
                'display_name_en': 'Anime & Cartoon',
                'icon': '⛩️',
                'color': '#ff69b4'
            },
            'wrestling': {
                'display_name_ar': 'مصارعة حرة',
                'display_name_en': 'Wrestling',
                'icon': '💪',
                'color': '#dc143c'
            },
            'documentary': {
                'display_name_ar': 'وثائقيات',
                'display_name_en': 'Documentaries',
                'icon': '🎥',
                'color': '#20b2aa'
            },
            'plays': {
                'display_name_ar': 'مسرحيات',
                'display_name_en': 'Plays',
                'icon': '🎭',
                'color': '#da70d6'
            },
            'foreign_series': {
                'display_name_ar': 'مسلسلات أجنبي',
                'display_name_en': 'Foreign Series',
                'icon': '🌐',
                'color': '#00bfff'
            },
        }

        return metadata.get(category, {
            'display_name_ar': category,
            'display_name_en': category,
            'icon': '🎬',
            'color': '#888888'
        })
