# -*- coding: utf-8 -*-
"""
A Tube Cast & Crew API
Handles extraction, storage, and retrieval of cast and crew information.
Supports multi-source merging (TMDB, IMDB, portal scrapers).
"""

import os
import sys
import json
import re
import urllib.request
from typing import Dict, List, Any, Optional
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "services"))

from vod_db import VODDatabase
from text_sanitizer import TextSanitizer
from stream_validator import StreamHealthValidator


class CastCrewAPI:
    """
    Cast and Crew management API.
    Handles:
    - Cast extraction from portals
    - Cast deduplication and merging
    - Role-based categorization (actor, director, writer, producer)
    - Image URL handling with fallbacks
    """

    # Role type mappings
    ROLE_TYPES = {
        'actor': ['actor', 'actress', 'نجم', 'ممثل', 'ممثلة', 'بطولة', 'star'],
        'director': ['director', 'مخرج', 'directed by', 'إخراج'],
        'writer': ['writer', 'كاتب', 'سيناريو', 'screenplay', 'قصة'],
        'producer': ['producer', 'منتج', 'production', 'إنتاج'],
        'cinematographer': ['cinematographer', 'مدير تصوير', 'تصوير سينمائي'],
        'composer': ['composer', 'موسيقى', 'music', 'ملحن'],
        'editor': ['editor', 'مونتاج', 'montage', 'محرر'],
    }

    # Fallback avatar patterns
    FALLBACK_AVATARS = [
        'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&q=80',
        'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&q=80',
        'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&q=80',
        'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&q=80',
    ]

    @classmethod
    def extract_cast_from_html(cls, html: str, media_id: str) -> List[Dict[str, Any]]:
        """
        Extracts cast and crew information from HTML pages.
        Handles multiple portal formats (Akwam, FaselHD, EgyDead, etc.)
        """
        cast_members = []

        # Pattern 1: Structured cast blocks (common in cinema portals)
        # Look for cast containers with actor info
        cast_patterns = [
            # Pattern: actor name + role in structured HTML
            r'<div[^>]*class="[^"]*cast[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>.*?<span[^>]*>([^<]+)</span>.*?</div>',
            # Pattern: actor img + name + role
            r'<img[^>]+alt="([^"]+)"[^>]*>.*?<[^>]+>([^<]+)</[^>]+>.*?<[^>]+>([^<]+)</[^>]+>',
            # Pattern: Simple name lists
            r'<li[^>]*>([^<]+)</li>\s*<li[^>]*>([^<]+)</li>',
        ]

        for pattern in cast_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    name = match[0].strip()
                    role = match[1].strip() if len(match) > 1 else ''
                    if cls._is_valid_cast_name(name):
                        cast_members.append(cls._create_cast_entry(name, role, media_id))

        # Pattern 2: JSON-LD structured data
        json_ld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
        json_matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)
        for json_str in json_matches:
            try:
                data = json.loads(json_str)
                if isinstance(data, dict) and data.get('@type') == 'Movie':
                    # Extract from Movie schema
                    actors = data.get('actor', [])
                    director = data.get('director', {})
                    if isinstance(director, dict):
                        director = [director]
                    for actor in actors:
                        if isinstance(actor, dict):
                            cast_members.append(cls._create_cast_entry(
                                actor.get('name', ''),
                                'actor',
                                media_id,
                                actor.get('image', '')
                            ))
                    for director in director:
                        if isinstance(director, dict):
                            cast_members.append(cls._create_cast_entry(
                                director.get('name', ''),
                                'director',
                                media_id,
                                director.get('image', '')
                            ))
            except (json.JSONDecodeError, AttributeError):
                pass

        # Pattern 3: Meta tags (og:title with cast info)
        meta_cast = re.findall(r'<meta[^>]+name="(?:cast|actor|stars)"[^>]+content="([^"]+)"', html, re.IGNORECASE)
        for cast_str in meta_cast:
            names = [n.strip() for n in re.split(r'[,،/]', cast_str) if n.strip()]
            for name in names:
                if cls._is_valid_cast_name(name):
                    cast_members.append(cls._create_cast_entry(name, 'actor', media_id))

        # Deduplicate by name
        seen = set()
        unique_cast = []
        for member in cast_members:
            name_key = cls._normalize_name(member['name'])
            if name_key not in seen:
                seen.add(name_key)
                unique_cast.append(member)

        return unique_cast

    @classmethod
    def _is_valid_cast_name(cls, name: str) -> bool:
        """Validates that a string looks like a person's name."""
        if not name or not isinstance(name, str):
            return False
        name = name.strip()
        if len(name) < 2 or len(name) > 100:
            return False
        # Reject common non-name patterns
        invalid_patterns = [
            r'^\d+$', r'^[a-z]{1,2}$', r'^www\.', r'^http',
            r'movie', r'series', r'episode', r'season', r'watch',
            r'stream', r'video', r'play', r'download'
        ]
        for pattern in invalid_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return False
        return True

    @classmethod
    def _normalize_name(cls, name: str) -> str:
        """Creates a normalized key for deduplication."""
        return TextSanitizer.sanitize_for_dedup(name)

    @classmethod
    def _create_cast_entry(cls, name: str, role: str, media_id: str,
                          photo_url: str = '') -> Dict[str, Any]:
        """Creates a standardized cast entry."""
        # Determine role type
        role_type = 'actor'
        norm_role = TextSanitizer.sanitize_for_dedup(role)
        for rtype, keywords in cls.ROLE_TYPES.items():
            if any(kw in norm_role for kw in keywords):
                role_type = rtype
                break

        # Sanitize name
        clean_name = TextSanitizer.sanitize(name, max_length=100, strip_noise=False)

        # Handle photo URL
        if not photo_url or not StreamHealthValidator.is_free_server(photo_url):
            photo_url = cls.FALLBACK_AVATARS[hash(name) % len(cls.FALLBACK_AVATARS)]

        return {
            'name': clean_name,
            'arabic_name': clean_name if any('\u0600' <= c <= '\u06FF' for c in clean_name) else '',
            'role': role_type,
            'character_name': TextSanitizer.sanitize(role, max_length=50),
            'photo': photo_url,
            'media_id': media_id
        }

    @classmethod
    def merge_cast_from_multiple_sources(cls, media_id: str,
                                         new_cast: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merges cast from multiple sources (TMDB, IMDB, portals) into unified list.
        Prioritizes:
        1. Existing cast in DB (preserve manually added entries)
        2. New cast with photos over cast without photos
        3. More specific role titles
        """
        existing = VODDatabase.get_media_details(media_id)
        if not existing:
            return new_cast

        existing_cast = existing.get('cast', [])

        # Build lookup by normalized name
        existing_by_name = {}
        for member in existing_cast:
            key = cls._normalize_name(member.get('name', ''))
            existing_by_name[key] = member

        # Merge
        merged = list(existing_cast)
        new_names = {cls._normalize_name(c.get('name', '')) for c in existing_cast}

        for new_member in new_cast:
            name_key = cls._normalize_name(new_member.get('name', ''))
            if name_key not in new_names:
                merged.append(new_member)
                new_names.add(name_key)
            else:
                # Update existing entry if new one has more info
                existing = existing_by_name.get(name_key)
                if existing:
                    if not existing.get('photo') and new_member.get('photo'):
                        existing['photo'] = new_member['photo']
                    if not existing.get('arabic_name') and new_member.get('arabic_name'):
                        existing['arabic_name'] = new_member['arabic_name']
                    if not existing.get('character_name') and new_member.get('character_name'):
                        existing['character_name'] = new_member['character_name']

        return merged

    @classmethod
    def save_cast_for_media(cls, media_id: str, cast_list: List[Dict[str, Any]]) -> bool:
        """
        Saves cast list for a media item, replacing existing entries.
        Returns True on success.
        """
        try:
            VODDatabase.init_schema()
            conn = VODDatabase.get_connection()
            cur = conn.cursor()

            # Clear existing cast
            cur.execute("DELETE FROM vod_cast WHERE media_id = ?", (media_id,))

            # Insert new cast
            for member in cast_list:
                cur.execute("""
                    INSERT INTO vod_cast (media_id, name, arabic_name, role, photo)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    media_id,
                    member.get('name', ''),
                    member.get('arabic_name', ''),
                    member.get('role', 'actor'),
                    member.get('photo', '')
                ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"[CastCrewAPI] Error saving cast: {e}")
            return False

    @classmethod
    def get_cast_for_media(cls, media_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves cast and crew for a media item.
        Returns a list with standardized format.
        """
        details = VODDatabase.get_media_details(media_id)
        if not details:
            return []

        cast = details.get('cast', [])

        # Enrich with director info if available
        director = details.get('director', '')
        if director and not any(c.get('role') == 'director' for c in cast):
            cast.insert(0, {
                'name': TextSanitizer.sanitize(director, max_length=100),
                'arabic_name': '',
                'role': 'director',
                'character_name': 'مخرج',
                'photo': ''
            })

        return cast

    @classmethod
    def get_cast_api_response(cls, media_id: str) -> Dict[str, Any]:
        """
        Returns a full API-ready response for cast/crew endpoint.
        """
        cast = cls.get_cast_for_media(media_id)

        # Group by role type
        grouped = {
            'directors': [c for c in cast if c.get('role') == 'director'],
            'actors': [c for c in cast if c.get('role') == 'actor'],
            'writers': [c for c in cast if c.get('role') == 'writer'],
            'producers': [c for c in cast if c.get('role') == 'producer'],
            'other': [c for c in cast if c.get('role') not in ['director', 'actor', 'writer', 'producer']]
        }

        return {
            'media_id': media_id,
            'total_cast': len(cast),
            'cast': cast,
            'grouped': grouped
        }

    @classmethod
    def search_people(cls, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Searches for people across all media in the database.
        Returns matching cast/crew members with their associated works.
        """
        if not query or len(query.strip()) < 2:
            return []

        norm_query = cls._normalize_name(query)

        conn = VODDatabase.get_connection()
        cur = conn.cursor()

        # Search in vod_cast table
        cur.execute("""
            SELECT c.*, m.title, m.arabic_title, m.poster, m.content_type, m.category
            FROM vod_cast c
            JOIN vod_media m ON c.media_id = m.id
            WHERE LOWER(c.name) LIKE ? OR LOWER(c.arabic_name) LIKE ?
            ORDER BY m.updated_at DESC
            LIMIT ?
        """, (f'%{norm_query}%', f'%{norm_query}%', limit))

        results = []
        seen_people = set()

        for row in cur.fetchall():
            person_key = cls._normalize_name(row['name'])
            if person_key not in seen_people:
                seen_people.add(person_key)
                results.append({
                    'name': row['name'],
                    'arabic_name': row['arabic_name'],
                    'role': row['role'],
                    'photo': row['photo'],
                    'works_count': 1,  # Could aggregate
                    'sample_work': {
                        'id': row['media_id'],
                        'title': row['title'],
                        'arabic_title': row['arabic_title'],
                        'poster': row['poster'],
                        'content_type': row['content_type'],
                        'category': row['category']
                    }
                })

        conn.close()
        return results

    @classmethod
    def enrich_media_with_cast(cls, media_id: str, cast_data: List[Dict[str, Any]]) -> bool:
        """
        Adds cast data to an existing media entry.
        Merges with existing cast without duplicates.
        """
        try:
            existing_cast = cls.get_cast_for_media(media_id)
            merged = cls.merge_cast_from_multiple_sources(media_id, cast_data)
            return cls.save_cast_for_media(media_id, merged)
        except Exception as e:
            print(f"[CastCrewAPI] Error enriching media: {e}")
            return False
