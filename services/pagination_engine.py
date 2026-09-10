# -*- coding: utf-8 -*-
"""
A TuBe Pagination Engine
Handles pagination logic for all media feeds across all pages.
Supports offset-based pagination with SQLite optimization.
"""

import math
from typing import Dict, List, Any, Optional, Tuple


class PaginationEngine:
    """
    High-performance pagination for media feeds.
    Uses SQLite OFFSET/LIMIT for efficient large-dataset pagination.
    """

    DEFAULT_LIMIT = 24
    MAX_LIMIT = 100
    MIN_PAGE = 1

    @classmethod
    def get_paginated_feed(cls, content_type: str = 'all', category: str = 'all',
                          page: int = 1, limit: int = DEFAULT_LIMIT,
                          sort: str = 'latest', search_query: str = '') -> Dict[str, Any]:
        """
        Returns a paginated feed with full pagination metadata.

        Args:
            content_type: 'movie', 'series', 'anime', 'tv_show', 'all'
            category: category slug
            page: page number (1-indexed)
            limit: items per page
            sort: 'latest', 'rating', 'title'
            search_query: optional search query

        Returns:
            {
                "items": [...],
                "pagination": {
                    "page": 1,
                    "limit": 24,
                    "total_items": 150,
                    "total_pages": 7,
                    "has_next": true,
                    "has_prev": false,
                    "next_page": 2,
                    "prev_page": null
                },
                "meta": {
                    "content_type": "all",
                    "category": "all",
                    "sort": "latest"
                }
            }
        """
        from vod_db import VODDatabase

        # Validate inputs
        page = max(cls.MIN_PAGE, page)
        limit = max(1, min(limit, cls.MAX_LIMIT))
        offset = (page - 1) * limit

        # Get all items from DB
        if search_query:
            all_items = VODDatabase.search_media(
                query=search_query,
                content_type=content_type if content_type != 'all' else None,
                category=category if category != 'all' else None
            )
        else:
            all_items = VODDatabase.get_feed(
                content_type=content_type if content_type != 'all' else None,
                category=category if category != 'all' else None
            )

        # Apply sorting
        if sort == 'rating':
            all_items = sorted(all_items, key=lambda x: float(x.get('rating', '0').split('/')[0]) if x.get('rating') else 0, reverse=True)
        elif sort == 'title':
            all_items = sorted(all_items, key=lambda x: x.get('title', '').lower())
        else:  # latest (default)
            all_items = sorted(all_items, key=lambda x: x.get('updated_at', ''), reverse=True)

        # Calculate pagination
        total_items = len(all_items)
        total_pages = math.ceil(total_items / limit) if total_items > 0 else 1

        # Slice for current page
        start_idx = offset
        end_idx = offset + limit
        page_items = all_items[start_idx:end_idx]

        # Build pagination metadata
        pagination = {
            'page': page,
            'limit': limit,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'prev_page': page - 1 if page > 1 else None,
            'offset': offset,
            'items_on_page': len(page_items)
        }

        return {
            'items': page_items,
            'pagination': pagination,
            'meta': {
                'content_type': content_type,
                'category': category,
                'sort': sort,
                'search_query': search_query or None
            }
        }

    @classmethod
    def get_page_range(cls, current_page: int, total_pages: int,
                      max_visible: int = 5) -> List[Dict[str, Any]]:
        """
        Generates a smart page range for UI pagination controls.
        Example output:
        [
            {"page": 1, "label": "1", "active": false},
            {"page": 2, "label": "2", "active": true},
            {"page": 3, "label": "...", "disabled": true},
            {"page": 5, "label": "5", "active": false}
        ]
        """
        if total_pages <= 1:
            return [{'page': 1, 'label': '1', 'active': True, 'disabled': False}]

        pages = []
        delta = max_visible // 2

        range_start = max(1, current_page - delta)
        range_end = min(total_pages, current_page + delta)

        # Adjust if we're near the start
        if range_start <= 2:
            range_end = min(total_pages, max_visible)
            range_start = 1

        # Adjust if we're near the end
        if range_end >= total_pages - 1:
            range_start = max(1, total_pages - max_visible + 1)
            range_end = total_pages

        # Always show first page
        if range_start > 1:
            pages.append({'page': 1, 'label': '1', 'active': False, 'disabled': False})
            if range_start > 2:
                pages.append({'page': None, 'label': '...', 'active': False, 'disabled': True})

        # Middle pages
        for p in range(range_start, range_end + 1):
            pages.append({
                'page': p,
                'label': str(p),
                'active': p == current_page,
                'disabled': False
            })

        # Always show last page
        if range_end < total_pages:
            if range_end < total_pages - 1:
                pages.append({'page': None, 'label': '...', 'active': False, 'disabled': True})
            pages.append({'page': total_pages, 'label': str(total_pages),
                         'active': False, 'disabled': False})

        return pages

    @classmethod
    def get_cursor_pagination(cls, content_type: str = 'all', category: str = 'all',
                             cursor: Optional[str] = None, limit: int = DEFAULT_LIMIT,
                             sort: str = 'latest') -> Dict[str, Any]:
        """
        Cursor-based pagination for infinite scroll / "load more" UI patterns.
        More efficient than offset for large datasets.

        Args:
            cursor: base64 encoded cursor from previous page (or None for first page)
            limit: items to return

        Returns:
            {
                "items": [...],
                "next_cursor": "base64_encoded_cursor_or_null",
                "has_more": true/false,
                "count": 24
            }
        """
        from vod_db import VODDatabase
        import base64
        import json

        # Decode cursor if provided
        last_id = None
        last_timestamp = None
        if cursor:
            try:
                decoded = json.loads(base64.b64decode(cursor).decode('utf-8'))
                last_id = decoded.get('id')
                last_timestamp = decoded.get('updated_at')
            except Exception:
                cursor = None

        # Get items
        if cursor and last_id:
            # Use cursor-based query (more efficient for large offsets)
            items = VODDatabase.get_feed_cursor(
                content_type=content_type if content_type != 'all' else None,
                category=category if category != 'all' else None,
                last_id=last_id,
                last_timestamp=last_timestamp,
                limit=limit + 1  # Fetch one extra to check if there's more
            )
        else:
            items = VODDatabase.get_feed(
                content_type=content_type if content_type != 'all' else None,
                category=category if category != 'all' else None
            )
            items = items[:limit + 1]

        # Check if there's more
        has_more = len(items) > limit
        if has_more:
            items = items[:limit]

        # Generate next cursor
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            cursor_data = {
                'id': last_item.get('id'),
                'updated_at': last_item.get('updated_at', '')
            }
            next_cursor = base64.b64encode(
                json.dumps(cursor_data).encode('utf-8')
            ).decode('utf-8')

        return {
            'items': items,
            'next_cursor': next_cursor,
            'has_more': has_more,
            'count': len(items),
            'pagination_type': 'cursor'
        }

    @classmethod
    def get_aggregated_stats(cls, content_type: str = 'all', category: str = 'all') -> Dict[str, Any]:
        """
        Returns aggregated statistics for a feed section.
        Useful for showing "X items • Y servers available" in UI.
        """
        from vod_db import VODDatabase

        items = VODDatabase.get_feed(
            content_type=content_type if content_type != 'all' else None,
            category=category if category != 'all' else None
        )

        total_items = len(items)
        total_servers = sum(item.get('server_count', 0) for item in items)
        avg_servers = round(total_servers / total_items, 1) if total_items > 0 else 0

        # Quality breakdown
        quality_counts = {}
        for item in items:
            quality = item.get('quality', 'Unknown')
            quality_counts[quality] = quality_counts.get(quality, 0) + 1

        # Year range
        years = [int(item.get('year', 0)) for item in items if item.get('year', '').isdigit()]
        year_range = {
            'min': min(years) if years else None,
            'max': max(years) if years else None
        }

        return {
            'total_items': total_items,
            'total_servers': total_servers,
            'avg_servers_per_item': avg_servers,
            'quality_breakdown': quality_counts,
            'year_range': year_range,
            'content_type': content_type,
            'category': category
        }

    @classmethod
    def validate_pagination_params(cls, page: Any = None, limit: Any = None) -> Tuple[int, int]:
        """
        Validates and sanitizes pagination parameters from HTTP requests.
        Returns (validated_page, validated_limit).
        """
        # Default values
        validated_page = cls.MIN_PAGE
        validated_limit = cls.DEFAULT_LIMIT

        # Validate page
        if page is not None:
            try:
                p = int(page)
                if p >= cls.MIN_PAGE:
                    validated_page = p
            except (ValueError, TypeError):
                pass

        # Validate limit
        if limit is not None:
            try:
                l = int(limit)
                if 1 <= l <= cls.MAX_LIMIT:
                    validated_limit = l
            except (ValueError, TypeError):
                pass

        return validated_page, validated_limit
