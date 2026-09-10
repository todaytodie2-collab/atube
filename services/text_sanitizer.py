# -*- coding: utf-8 -*-
"""
A TuBe HTML Entities Decoder & Text Sanitizer
Decodes HTML entities, strips noise, normalizes Arabic text for safe storage and display.
"""

import re
import html
import unicodedata


class TextSanitizer:
    """
    Handles all text cleaning operations:
    - HTML entity decoding (&quot;, &#039;, &amp;, etc.)
    - Arabic character normalization
    - Noise word stripping
    - Safe truncation
    """

    # HTML entities to explicitly decode
    HTML_ENTITY_MAP = {
        '&quot;': '"',
        '&#039;': "'",
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&nbsp;': ' ',
        '&ldquo;': '"',
        '&rdquo;': '"',
        '&lsquo;': "'",
        '&rsquo;': "'",
        '&mdash;': '—',
        '&ndash;': '–',
        '&hellip;': '...',
        '&copy;': '©',
        '&reg;': '®',
        '&trade;': '™',
        '&eacute;': 'é',
        '&euro;': '€',
        '&pound;': '£',
        '&yen;': '¥',
        '&deg;': '°',
        '&times;': '×',
        '&divide;': '÷',
        '&alpha;': 'α',
        '&beta;': 'β',
        '&gamma;': 'γ',
    }

    # Regex pattern for numeric HTML entities like &#1234; or &#x1F600;
    NUMERIC_ENTITY_PATTERN = re.compile(r'&#(?:x[0-9a-fA-F]+|[0-9]+);')

    @classmethod
    def decode_html_entities(cls, text: str) -> str:
        """
        Decodes all HTML entities in the given text.
        Handles both named entities (&quot;) and numeric entities (&#039;).
        """
        if not text or not isinstance(text, str):
            return ''

        # First pass: replace known named entities
        result = text
        for entity, char in cls.HTML_ENTITY_MAP.items():
            result = result.replace(entity, char)

        # Second pass: decode any remaining named entities using html.unescape
        result = html.unescape(result)

        # Third pass: handle numeric entities that might remain
        def replace_numeric_entity(match):
            entity_str = match.group(0)
            try:
                # Remove &# and ; to get the number
                num_str = entity_str[2:-1]
                if num_str.lower().startswith('x'):
                    code_point = int(num_str[1:], 16)
                else:
                    code_point = int(num_str)
                return chr(code_point)
            except (ValueError, OverflowError):
                return entity_str

        result = cls.NUMERIC_ENTITY_PATTERN.sub(replace_numeric_entity, result)

        return result

    @classmethod
    def normalize_arabic(cls, text: str) -> str:
        """
        Normalizes Arabic text by:
        - Removing diacritics (tashkeel)
        - Unifying alef forms (أ, إ, آ -> ا)
        - Unifying ta marbuta (ة -> ه)
        - Unifying yeh forms (ى, ي -> ي)
        - Unifying waw forms (ؤ, و -> و)
        """
        if not text:
            return ''

        # Remove Arabic diacritics (tashkeel)
        text = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]', '', text)

        # Unify alef forms
        text = re.sub(r'[أإآٱٲٳٴ]', 'ا', text)

        # Unify ta marbuta to ha
        text = text.replace('ة', 'ه')

        # Unify yeh forms
        text = re.sub(r'[ىٮٰ]', 'ي', text)

        # Unify waw forms
        text = re.sub(r'[ؤٷ]', 'و', text)

        # Unify noon forms (optional, ن -> ن is same, but ٹ -> ت etc)
        text = re.sub(r'[ٹٽٺٻݕݖ]', 'ت', text)

        return text

    @classmethod
    def strip_noise_words(cls, text: str, extra_noise: list = None) -> str:
        """
        Removes common noise words from titles:
        - watch/download prefixes
        - site names ( EgyBest, FaselHD, etc.)
        - quality tags
        - translation tags
        """
        if not text:
            return ''

        noise_words = [
            'مشاهدة', 'مشاهده', 'تحميل', 'فيلم', 'مسلسل', 'انمي',
            'اون لاين', 'اونلاين', 'اون-لاين',
            'ايجي بست', 'ايجي ديد', 'فاصل اعلاني', 'فاصل إعلاني',
            'اكوام', 'ماي سيما', 'وي سيما', 'سيما فور يو', 'سيما لايت',
            'سيما كلوب', 'شاهد فور يو', 'توب سينما',
            'faselhd', 'egybest', 'egydead', 'akwam', 'wecima', 'mycima',
            'cima4u', 'cimaclub', 'shahid4u', 'topcinema',
            'مترجم', 'مدبلج', 'كامل', 'بجودة عالية',
            'hd', 'fhd', '1080p', '720p', '4k', 'web-dl', 'bluray', 'brrip',
            'hdcam', 'hdtc', 'ts', 'cam', 'tc', ' screener',
            'النسخة الأصلية', 'النسخة العربية', 'المدبلجة', 'المترجمة',
            'جودة عالية', 'عالي الجودة', 'مباشر', 'لايف', 'live',
            'حصرياً', 'حصريا', 'حصرية', 'جديد', 'جديدة', 'جديد 2024', 'جديد 2025', 'جديد 2026',
            'ن鑑', 'يضاي', 'اضغط هنا', 'تابع القراءة', 'اقرأ المزيد',
            'season', 'episode', 's0', 's1', 's2', 'e0', 'e1', 'e2',
            'الحلقة', 'الموسم', 'part', 'part 1', 'part 2',
        ]

        if extra_noise:
            noise_words.extend(extra_noise)

        result = text.lower()
        for noise in noise_words:
            result = re.sub(r'\b' + re.escape(noise) + r'\b', ' ', result, flags=re.IGNORECASE)

        # Remove anything after a dash, pipe, or hyphen that looks like extra info
        result = re.sub(r'\s*[-–|:]\s*.*$', '', result).strip()

        # Collapse multiple spaces
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    @classmethod
    def sanitize(cls, text: str, decode_html: bool = True, normalize_arabic: bool = True,
                 strip_noise: bool = True, max_length: int = 500) -> str:
        """
        Full sanitization pipeline:
        1. Decode HTML entities
        2. Normalize Arabic characters
        3. Strip noise words
        4. Truncate to max_length
        """
        if not text or not isinstance(text, str):
            return ''

        result = text

        if decode_html:
            result = cls.decode_html_entities(result)

        if normalize_arabic:
            result = cls.normalize_arabic(result)

        if strip_noise:
            result = cls.strip_noise_words(result)

        # Final cleanup
        result = result.strip()
        if len(result) > max_length:
            result = result[:max_length].rsplit(' ', 1)[0] + '...'

        return result

    @classmethod
    def sanitize_for_dedup(cls, text: str) -> str:
        """
        Aggressive sanitization for deduplication matching.
        Returns a normalized, lowercase, noise-free string.
        """
        if not text:
            return ''

        result = text.lower()
        result = cls.normalize_arabic(result)
        result = cls.strip_noise_words(result)
        result = re.sub(r'[^\w\u0600-\u06FF\s]', '', result)
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    @classmethod
    def is_safe_text(cls, text: str) -> bool:
        """
        Validates that text doesn't contain suspicious patterns or XSS attempts.
        """
        if not text:
            return False

        dangerous_patterns = [
            r'<script[^>]*>', r'</script>',
            r'javascript:', r'on\w+\s*=',
            r'<iframe[^>]*>', r'</iframe>',
            r'<object[^>]*>', r'</object>',
            r'<embed[^>]*>', r'</embed>',
            r'<link[^>]*>', r'<meta[^>]*>',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        return True

    @classmethod
    def truncate(cls, text: str, max_length: int = 200, suffix: str = '...') -> str:
        """
        Safely truncates text to max_length, breaking at word boundaries.
        """
        if not text or len(text) <= max_length:
            return text or ''

        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.7:
            truncated = truncated[:last_space]

        return truncated + suffix
