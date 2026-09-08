# -*- coding: utf-8 -*-
"""
VOD SQLite Database Manager - Multi-Category & Episode Taxonomy
Supports Movies, Series, Anime, and TV Shows with hierarchical Seasons & Episodes
Categories:
- Movies: Foreign, Arabic, Turkish, Indian, Anime
- Series: Foreign, Turkish, Arabic, Asian/K-Drama
- Anime: Subbed, Dubbed, Movies
- TV Shows: Documentaries, Talk Shows, Sports/WWE
"""

import os
import sys
import json
import sqlite3
from typing import Dict, List, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "atube_data.sqlite")


class VODDatabase:
    _initialized = False

    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    @classmethod
    def init_schema(cls):
        if cls._initialized:
            return
        conn = cls.get_connection()
        cur = conn.cursor()

        # 1. Main Media Table (Movies, Series, Anime, Shows)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vod_media (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                arabic_title TEXT,
                content_type TEXT NOT NULL DEFAULT 'movie',  -- 'movie', 'series', 'anime', 'tv_show'
                category TEXT NOT NULL DEFAULT 'foreign',    -- 'foreign', 'arabic', 'turkish', 'asian', 'indian', 'documentary', 'wrestling'
                sub_category TEXT DEFAULT 'subbed',          -- 'subbed', 'dubbed'
                year TEXT,
                rating TEXT,
                duration TEXT,
                quality TEXT,
                language TEXT,
                translation TEXT,
                production TEXT,
                country TEXT,
                genres TEXT,
                poster TEXT,
                backdrop TEXT,
                synopsis TEXT,
                trailer_youtube_id TEXT,
                director TEXT,
                total_seasons INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Seasons Table (For Series, Anime & Shows)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vod_seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT NOT NULL,
                season_number INTEGER NOT NULL,
                season_title TEXT,
                UNIQUE(media_id, season_number),
                FOREIGN KEY (media_id) REFERENCES vod_media(id) ON DELETE CASCADE
            );
        """)

        # 3. Episodes Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vod_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT NOT NULL,
                season_number INTEGER NOT NULL DEFAULT 1,
                episode_number INTEGER NOT NULL,
                episode_title TEXT,
                thumbnail TEXT,
                duration TEXT,
                synopsis TEXT,
                UNIQUE(media_id, season_number, episode_number),
                FOREIGN KEY (media_id) REFERENCES vod_media(id) ON DELETE CASCADE
            );
        """)

        # 4. Multi-Source Streaming Servers (Attached to movie OR specific episode)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vod_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT NOT NULL,
                season_number INTEGER,
                episode_number INTEGER,
                site TEXT NOT NULL,
                quality TEXT,
                server_name TEXT,
                stream_url TEXT NOT NULL,
                badge TEXT,
                FOREIGN KEY (media_id) REFERENCES vod_media(id) ON DELETE CASCADE
            );
        """)

        # 5. Cast Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vod_cast (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT NOT NULL,
                name TEXT NOT NULL,
                arabic_name TEXT,
                role TEXT,
                photo TEXT,
                FOREIGN KEY (media_id) REFERENCES vod_media(id) ON DELETE CASCADE
            );
        """)

        # 6. Stills / Photos Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vod_stills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT NOT NULL,
                photo_url TEXT NOT NULL,
                FOREIGN KEY (media_id) REFERENCES vod_media(id) ON DELETE CASCADE
            );
        """)

        # Auto-migration for existing tables with previous column names
        try:
            cur.execute("PRAGMA table_info(vod_servers);")
            srv_cols = [c[1] for c in cur.fetchall()]
            if "media_id" not in srv_cols and "movie_id" in srv_cols:
                try:
                    cur.execute("ALTER TABLE vod_servers RENAME COLUMN movie_id TO media_id;")
                except Exception:
                    cur.execute("ALTER TABLE vod_servers ADD COLUMN media_id TEXT;")
                    cur.execute("UPDATE vod_servers SET media_id = movie_id WHERE media_id IS NULL;")

            # Re-fetch after rename
            cur.execute("PRAGMA table_info(vod_servers);")
            srv_cols = [c[1] for c in cur.fetchall()]
            if "season_number" not in srv_cols:
                cur.execute("ALTER TABLE vod_servers ADD COLUMN season_number INTEGER;")
            if "episode_number" not in srv_cols:
                cur.execute("ALTER TABLE vod_servers ADD COLUMN episode_number INTEGER;")

            cur.execute("PRAGMA table_info(vod_cast);")
            cast_cols = [c[1] for c in cur.fetchall()]
            if "media_id" not in cast_cols and "movie_id" in cast_cols:
                try:
                    cur.execute("ALTER TABLE vod_cast RENAME COLUMN movie_id TO media_id;")
                except Exception:
                    cur.execute("ALTER TABLE vod_cast ADD COLUMN media_id TEXT;")
                    cur.execute("UPDATE vod_cast SET media_id = movie_id WHERE media_id IS NULL;")

            cur.execute("PRAGMA table_info(vod_stills);")
            still_cols = [c[1] for c in cur.fetchall()]
            if "media_id" not in still_cols and "movie_id" in still_cols:
                try:
                    cur.execute("ALTER TABLE vod_stills RENAME COLUMN movie_id TO media_id;")
                except Exception:
                    cur.execute("ALTER TABLE vod_stills ADD COLUMN media_id TEXT;")
                    cur.execute("UPDATE vod_stills SET media_id = movie_id WHERE media_id IS NULL;")
        except Exception as mig_ex:
            print(f"[Schema Migration Note] {mig_ex}")

        # Indices for Sub-5ms queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_vod_media_type_cat ON vod_media(content_type, category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_vod_episodes_lookup ON vod_episodes(media_id, season_number);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_vod_servers_lookup ON vod_servers(media_id, season_number, episode_number);")

        conn.commit()
        conn.close()
        cls._initialized = True

    @classmethod
    def upsert_media(cls, media: Dict[str, Any]):
        cls.init_schema()
        conn = cls.get_connection()
        cur = conn.cursor()

        genres_str = json.dumps(media.get("genres", []), ensure_ascii=False)
        media_id = media.get("id")

        cur.execute("""
            INSERT INTO vod_media (
                id, title, arabic_title, content_type, category, sub_category,
                year, rating, duration, quality, language, translation,
                production, country, genres, poster, backdrop, synopsis,
                trailer_youtube_id, director, total_seasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                arabic_title=excluded.arabic_title,
                content_type=excluded.content_type,
                category=excluded.category,
                sub_category=excluded.sub_category,
                year=excluded.year,
                rating=excluded.rating,
                duration=excluded.duration,
                quality=excluded.quality,
                language=excluded.language,
                translation=excluded.translation,
                production=excluded.production,
                country=excluded.country,
                genres=excluded.genres,
                poster=excluded.poster,
                backdrop=excluded.backdrop,
                synopsis=excluded.synopsis,
                trailer_youtube_id=excluded.trailer_youtube_id,
                director=excluded.director,
                total_seasons=excluded.total_seasons,
                updated_at=CURRENT_TIMESTAMP;
        """, (
            media_id,
            media.get("title"),
            media.get("arabic_title"),
            media.get("content_type", "movie"),
            media.get("category", "foreign"),
            media.get("sub_category", "subbed"),
            str(media.get("year", "")),
            media.get("rating"),
            media.get("duration"),
            media.get("quality"),
            media.get("language"),
            media.get("translation"),
            media.get("production"),
            media.get("country", ""),
            genres_str,
            media.get("poster"),
            media.get("backdrop"),
            media.get("synopsis"),
            media.get("trailer_youtube_id"),
            media.get("director"),
            int(media.get("total_seasons", 1))
        ))

        # Insert Seasons & Episodes if provided (for series & anime)
        for season in media.get("seasons", []):
            s_num = int(season.get("season_number", 1))
            cur.execute("""
                INSERT INTO vod_seasons (media_id, season_number, season_title)
                VALUES (?, ?, ?)
                ON CONFLICT(media_id, season_number) DO UPDATE SET season_title=excluded.season_title;
            """, (media_id, s_num, season.get("title", f"الموسم {s_num}")))

            for ep in season.get("episodes", []):
                ep_num = int(ep.get("episode_number", 1))
                cur.execute("""
                    INSERT INTO vod_episodes (media_id, season_number, episode_number, episode_title, thumbnail, duration, synopsis)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(media_id, season_number, episode_number) DO UPDATE SET
                        episode_title=excluded.episode_title,
                        thumbnail=excluded.thumbnail,
                        duration=excluded.duration,
                        synopsis=excluded.synopsis;
                """, (
                    media_id, s_num, ep_num,
                    ep.get("title", f"الحلقة {ep_num}"),
                    ep.get("thumbnail", media.get("poster")),
                    ep.get("duration", "45 دقيقة"),
                    ep.get("synopsis", "")
                ))

                # Episode-level servers
                for srv in ep.get("servers", []):
                    cls._insert_server(cur, media_id, srv, season_num=s_num, ep_num=ep_num)

        # Standalone Movie Servers
        if media.get("servers"):
            cur.execute("DELETE FROM vod_servers WHERE media_id = ? AND season_number IS NULL", (media_id,))
            for srv in media.get("servers", []):
                cls._insert_server(cur, media_id, srv, season_num=None, ep_num=None)

        # Cast
        if "cast" in media:
            cur.execute("DELETE FROM vod_cast WHERE media_id = ?", (media_id,))
            for actor in media.get("cast", []):
                cur.execute("""
                    INSERT INTO vod_cast (media_id, name, arabic_name, role, photo)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    media_id,
                    actor.get("name", ""),
                    actor.get("arabic_name", ""),
                    actor.get("role", ""),
                    actor.get("photo", "")
                ))

        # Stills
        if "stills" in media:
            cur.execute("DELETE FROM vod_stills WHERE media_id = ?", (media_id,))
            for still in media.get("stills", []):
                cur.execute("INSERT INTO vod_stills (media_id, photo_url) VALUES (?, ?)", (media_id, still))

        conn.commit()
        conn.close()

    @classmethod
    def _insert_server(cls, cur: sqlite3.Cursor, media_id: str, srv: Dict[str, Any], season_num: Optional[int], ep_num: Optional[int]):
        stream_url = srv.get("stream_url", "")
        if not stream_url:
            return
        cur.execute("""
            INSERT INTO vod_servers (media_id, season_number, episode_number, site, quality, server_name, stream_url, badge)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            media_id,
            season_num,
            ep_num,
            srv.get("site", "Akwam"),
            srv.get("quality", "1080p"),
            srv.get("name", "سيرفر مباشر"),
            stream_url,
            srv.get("badge", "")
        ))

    @classmethod
    def get_feed(cls, content_type: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves de-duplicated catalog filtered strictly by content_type and category.
        Examples:
          - get_feed(content_type='series', category='turkish') -> Turkish Series only!
          - get_feed(content_type='movie', category='arabic') -> Arabic Movies only!
          - get_feed(content_type='anime') -> All Anime!
        """
        cls.init_schema()
        conn = cls.get_connection()
        cur = conn.cursor()

        query = """
            SELECT m.id, m.title, m.arabic_title, m.content_type, m.category, m.sub_category,
                   m.year, m.rating, m.duration, m.quality, m.genres, m.poster, m.total_seasons,
                   (SELECT COUNT(*) FROM vod_servers s WHERE s.media_id = m.id) as server_count
            FROM vod_media m
            WHERE 1=1
        """
        params = []

        # Handle Anime / Cartoon (can be movie or series, matched by category or content_type)
        if category in ["anime", "cartoon"] or content_type == "anime":
            query += " AND (m.category = 'anime' OR m.content_type = 'anime')"
            if content_type and content_type not in ["all", "anime"]:
                query += " AND m.content_type = ?"
                params.append(content_type)
        else:
            if content_type and content_type != "all":
                query += " AND m.content_type = ?"
                params.append(content_type)

            if category and category != "all":
                if category in ["arabic", "arabic_series"]:
                    if content_type == "series":
                        query += " AND m.category IN ('arabic', 'arabic_series')"
                    else:
                        query += " AND m.category = 'arabic'"
                else:
                    query += " AND m.category = ?"
                    params.append(category)

        query += " ORDER BY m.updated_at DESC;"

        cur.execute(query, params)
        rows = cur.fetchall()
        feed = []
        for r in rows:
            genres = []
            if r["genres"]:
                try:
                    genres = json.loads(r["genres"])
                except Exception:
                    pass

            feed.append({
                "id": r["id"],
                "title": r["title"],
                "arabic_title": r["arabic_title"],
                "content_type": r["content_type"],
                "category": r["category"],
                "sub_category": r["sub_category"],
                "year": r["year"],
                "rating": r["rating"],
                "duration": r["duration"],
                "quality": r["quality"],
                "genres": genres,
                "poster": r["poster"],
                "total_seasons": r["total_seasons"],
                "server_count": r["server_count"]
            })

        conn.close()
        return feed

    # Backward compatibility aliases
    @classmethod
    def get_all_movies_feed(cls) -> List[Dict[str, Any]]:
        return cls.get_feed(content_type="movie")

    @classmethod
    def upsert_movie(cls, movie: Dict[str, Any]):
        movie["content_type"] = "movie"
        cls.upsert_media(movie)

    @classmethod
    def get_media_details(cls, media_id: str) -> Optional[Dict[str, Any]]:
        """Returns full movie/series details, seasons, episodes, cast, stills, and servers."""
        cls.init_schema()
        conn = cls.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM vod_media WHERE id = ?", (media_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None

        # Fetch seasons & episodes if series or anime
        is_episodic = row["content_type"] in ["series", "anime", "tv_show"]
        seasons = []

        if is_episodic:
            cur.execute("SELECT season_number, season_title FROM vod_seasons WHERE media_id = ? ORDER BY season_number ASC", (media_id,))
            season_rows = cur.fetchall()
            for s_row in season_rows:
                s_num = s_row["season_number"]
                # Fetch episodes for this season
                cur.execute("""
                    SELECT episode_number, episode_title, thumbnail, duration, synopsis
                    FROM vod_episodes
                    WHERE media_id = ? AND season_number = ?
                    ORDER BY episode_number ASC
                """, (media_id, s_num))
                episodes = []
                for ep_row in cur.fetchall():
                    ep_num = ep_row["episode_number"]
                    # Fetch servers for this episode
                    cur.execute("""
                        SELECT site, quality, server_name as name, stream_url, badge
                        FROM vod_servers
                        WHERE media_id = ? AND season_number = ? AND episode_number = ?
                    """, (media_id, s_num, ep_num))
                    ep_servers = [dict(s) for s in cur.fetchall()]
                    episodes.append({
                        "episode_number": ep_num,
                        "title": ep_row["episode_title"],
                        "thumbnail": ep_row["thumbnail"],
                        "duration": ep_row["duration"],
                        "synopsis": ep_row["synopsis"],
                        "servers": ep_servers
                    })

                seasons.append({
                    "season_number": s_num,
                    "title": s_row["season_title"],
                    "episodes": episodes
                })

        # Fetch standalone servers (for movies or series trailer/overview)
        cur.execute("SELECT site, quality, server_name as name, stream_url, badge FROM vod_servers WHERE media_id = ? AND season_number IS NULL", (media_id,))
        movie_servers = [dict(s) for s in cur.fetchall()]

        # Fetch cast
        cur.execute("SELECT name, arabic_name, role, photo FROM vod_cast WHERE media_id = ?", (media_id,))
        cast = [dict(c) for c in cur.fetchall()]

        # Fetch stills
        cur.execute("SELECT photo_url FROM vod_stills WHERE media_id = ?", (media_id,))
        stills = [s["photo_url"] for s in cur.fetchall()]

        conn.close()

        genres = []
        if row["genres"]:
            try:
                genres = json.loads(row["genres"])
            except Exception:
                pass

        return {
            "id": row["id"],
            "title": row["title"],
            "arabic_title": row["arabic_title"],
            "content_type": row["content_type"],
            "category": row["category"],
            "sub_category": row["sub_category"],
            "year": row["year"],
            "rating": row["rating"],
            "duration": row["duration"],
            "quality": row["quality"],
            "language": row["language"],
            "translation": row["translation"],
            "production": row["production"],
            "country": row["country"],
            "genres": genres,
            "poster": row["poster"],
            "backdrop": row["backdrop"],
            "synopsis": row["synopsis"],
            "trailer_youtube_id": row["trailer_youtube_id"],
            "director": row["director"],
            "total_seasons": row["total_seasons"],
            "seasons": seasons,
            "servers": movie_servers,
            "cast": cast,
            "stills": stills
        }

    # Backward compatibility
    @classmethod
    def get_movie_details(cls, movie_id: str) -> Optional[Dict[str, Any]]:
        return cls.get_media_details(movie_id)

    @classmethod
    def search_media(cls, query: str, content_type: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        cls.init_schema()
        if not query:
            return cls.get_feed(content_type=content_type, category=category)

        conn = cls.get_connection()
        cur = conn.cursor()
        q = f"%{query.strip()}%"

        sql = """
            SELECT m.id, m.title, m.arabic_title, m.content_type, m.category, m.sub_category,
                   m.year, m.rating, m.duration, m.quality, m.genres, m.poster, m.total_seasons,
                   (SELECT COUNT(*) FROM vod_servers s WHERE s.media_id = m.id) as server_count
            FROM vod_media m
            WHERE (m.title LIKE ? OR m.arabic_title LIKE ? OR m.year LIKE ?)
        """
        params = [q, q, q]

        if content_type and content_type != "all":
            sql += " AND m.content_type = ?"
            params.append(content_type)
        if category and category != "all":
            sql += " AND m.category = ?"
            params.append(category)

        sql += " ORDER BY m.updated_at DESC;"

        cur.execute(sql, params)
        rows = cur.fetchall()
        results = []
        for r in rows:
            genres = []
            if r["genres"]:
                try:
                    genres = json.loads(r["genres"])
                except Exception:
                    pass

            results.append({
                "id": r["id"],
                "title": r["title"],
                "arabic_title": r["arabic_title"],
                "content_type": r["content_type"],
                "category": r["category"],
                "year": r["year"],
                "rating": r["rating"],
                "duration": r["duration"],
                "quality": r["quality"],
                "genres": genres,
                "poster": r["poster"],
                "server_count": r["server_count"]
            })
        conn.close()
        return results

    @classmethod
    def search_movies(cls, query: str) -> List[Dict[str, Any]]:
        return cls.search_media(query)

    @classmethod
    def add_or_merge_server(cls, movie_id: str, site: str, quality: str, server_name: str, stream_url: str, badge: str = "", season_num: Optional[int] = None, ep_num: Optional[int] = None):
        """Adds a streaming server to a movie or episode if not already present."""
        if not movie_id or not stream_url:
            return
        cls.init_schema()
        conn = cls.get_connection()
        cur = conn.cursor()

        if season_num is not None and ep_num is not None:
            cur.execute("""
                SELECT id FROM vod_servers
                WHERE media_id = ? AND stream_url = ? AND season_number = ? AND episode_number = ?
            """, (movie_id, stream_url, season_num, ep_num))
        else:
            cur.execute("""
                SELECT id FROM vod_servers
                WHERE media_id = ? AND stream_url = ? AND season_number IS NULL
            """, (movie_id, stream_url))

        exists = cur.fetchone()
        if not exists:
            cur.execute("""
                INSERT INTO vod_servers (media_id, season_number, episode_number, site, quality, server_name, stream_url, badge)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (movie_id, season_num, ep_num, site, quality or "1080p", server_name or site, stream_url, badge or ""))
            conn.commit()
        conn.close()

    @classmethod
    def seed_initial_catalog(cls, catalog_items: List[Dict[str, Any]]):
        """Seeds the SQLite database with verified multi-category items."""
        cls.init_schema()
        print(f"[VOD Database] Syncing {len(catalog_items)} multi-category catalog items into SQLite cache...")
        for item in catalog_items:
            cls.upsert_media(item)
        print(f"[VOD Database] Catalog sync complete.")
