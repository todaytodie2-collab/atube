/* ==========================================================================
   A TuBe Media Catalog Engine (Clean Slate)
   Holds live items and custom added media entities.
   ========================================================================== */

// --- Global HTML entity decoder (mirrors TextSanitizer.decode_html_entities) ---
function decodeHtmlEntities(text) {
  if (text === null || text === undefined) return '';
  let result = String(text);
  const map = {
    '&quot;': '"', '&#039;': "'", '&amp;': '&', '&lt;': '<', '&gt;': '>',
    '&nbsp;': ' ', '&ldquo;': '"', '&rdquo;': '"', '&lsquo;': "'", '&rsquo;': "'",
    '&mdash;': '—', '&ndash;': '–', '&hellip;': '...', '&copy;': '©', '&reg;': '®',
    '&trade;': '™', '&euro;': '€', '&pound;': '£', '&yen;': '¥', '&deg;': '°',
    '&times;': '×', '&divide;': '÷'
  };
  for (const [entity, ch] of Object.entries(map)) {
    result = result.split(entity).join(ch);
  }
  // Decode remaining named entities (&amp; already handled above)
  const tmp = document.createElement('textarea');
  tmp.innerHTML = result;
  let decoded = tmp.value;
  // Decode numeric entities that may survive
  decoded = decoded.replace(/&#(?:x[0-9a-fA-F]+|[0-9]+);/g, (m) => {
    try {
      const n = m.replace(/&#|;/g, '');
      return String.fromCharCode(parseInt(n.startsWith('x') ? n.slice(1) : n, n.startsWith('x') ? 16 : 10));
    } catch (e) { return m; }
  });
  return decoded;
}

// Decode HTML entities THEN escape for safe innerHTML insertion
function safeHtml(text) {
  if (typeof escapeHtml === 'function') return escapeHtml(decodeHtmlEntities(text));
  // Fallback (escapeHtml lives in app.js which loads later; safe at runtime)
  return decodeHtmlEntities(text);
}

const MediaCatalog = (function () {
  'use strict';

  const _ramCache = new Map();
  let _inMemoryCatalog = Array.isArray(window.ATUBE_STATIC_CATALOG) ? window.ATUBE_STATIC_CATALOG.slice() : [];
  if (_inMemoryCatalog.length > 0) {
    _inMemoryCatalog.forEach(item => {
      if (item && item.id) _ramCache.set(item.id, item);
    });
  }
  const _feedCache = new Map();

  function normalizeText(txt) {
    if (!txt) return '';
    return String(txt)
      .toLowerCase()
      .replace(/[أإآ]/g, 'ا')
      .replace(/ة/g, 'ه')
      .replace(/ى/g, 'ي')
      .trim();
  }

  const CANONICAL_REGIONS = {
    'foreign': 'foreign',
    'أفلام أجنبي': 'foreign',
    'أفلام أجنبية': 'foreign',
    'افلام اجنبي': 'foreign',
    'مسلسلات أجنبي': 'foreign',
    'مسلسلات أجنبية': 'foreign',
    'مسلسلات اجنبي': 'foreign',
    'movies': 'foreign',
    'hollywood': 'foreign',
    
    'arabic': 'arabic',
    'أفلام عربي': 'arabic',
    'أفلام عربية': 'arabic',
    'افلام عربي': 'arabic',
    'مسلسلات عربي': 'arabic',
    'مسلسلات عربية': 'arabic',
    'arabic_series': 'arabic',
    'دراما عربية': 'arabic',
    
    'turkish': 'turkish',
    'أفلام تركي': 'turkish',
    'افلام تركي': 'turkish',
    'مسلسلات تركي': 'turkish',
    'دراما تركية': 'turkish',
    'تركي': 'turkish',
    
    'anime': 'anime',
    'أنمي': 'anime',
    'انمي': 'anime',
    'الأنمي والكارتون': 'anime',
    'أفلام أنمي': 'anime',
    'مسلسلات أنمي': 'anime',
    'كارتون': 'anime',
    
    'indian': 'indian',
    'أفلام هندي': 'indian',
    'مسلسلات هندي': 'indian',
    'هندي': 'indian',
    'بوليوود': 'indian',

    'asian': 'asian',
    'أفلام آسيوي': 'asian',
    'مسلسلات آسيوي': 'asian',
    'كوري': 'asian',
    
    'channels': 'channels',
    'قنوات مباشرة': 'channels',
    'قنوات البث المباشر': 'channels',
    'قنوات': 'channels',
    'live': 'channels',
    
    'wrestling': 'wrestling',
    'مصارعة حرة': 'wrestling',
    'مصارعة': 'wrestling',
    'مصارعة حرة wwe': 'wrestling',
    'wwe': 'wrestling',
    
    'plays': 'plays',
    'مسرحيات': 'plays',
    'مسرحيات كوميدية': 'plays',
    
    'documentary': 'documentary',
    'أفلام وثائقية': 'documentary',
    'مسلسلات وثائقية': 'documentary',
    'وثائقي': 'documentary',
    'وثائقيات': 'documentary'
  };

  function parseTargetContentType(target) {
    if (!target) return null;
    const norm = normalizeText(target);
    if (norm.includes('مسلسل') || norm.includes('حلقات') || norm.includes('series') || norm.includes('دراما')) {
      return 'series';
    }
    if (norm.includes('فيلم') || norm.includes('افلام') || norm.includes('أفلام') || norm.includes('movie') || norm.includes('سينما')) {
      return 'movie';
    }
    return null;
  }

  function resolveRegion(catStr) {
    if (!catStr) return '';
    const norm = normalizeText(catStr);
    if (CANONICAL_REGIONS[norm]) return CANONICAL_REGIONS[norm];
    for (const [k, v] of Object.entries(CANONICAL_REGIONS)) {
      if (norm === normalizeText(k)) return v;
    }
    if (norm.includes('تركي')) return 'turkish';
    if (norm.includes('هندي') || norm.includes('بوليوود')) return 'indian';
    if (norm.includes('اسيوي') || norm.includes('كوري')) return 'asian';
    if (norm.includes('انمي') || norm.includes('كرتون')) return 'anime';
    if (norm.includes('مسرح')) return 'plays';
    if (norm.includes('مصارع') || norm.includes('wwe')) return 'wrestling';
    if (norm.includes('وثائق')) return 'documentary';
    if (norm.includes('قنوات') || norm.includes('مباشر')) return 'channels';
    if (norm.includes('عربي') || norm === 'arabic' || norm === 'arabic_series') return 'arabic';
    if (norm.includes('اجنبي') || norm === 'foreign') return 'foreign';
    return norm;
  }

  function getItemContentType(item) {
    if (!item) return 'movie';
    const rawType = (item.content_type || '').toLowerCase();
    const title = (item.title || '') + ' ' + (item.arabic_title || '');
    if (rawType === 'series' || rawType === 'tv_show') return 'series';
    if (item.total_seasons > 0 || (Array.isArray(item.seasons) && item.seasons.length > 0)) return 'series';
    if (title.includes('حلقة') || title.includes('الحلقة') || title.includes('الموسم') || title.includes('موسم')) return 'series';
    return 'movie';
  }

  function isCategoryMatch(item, targetCategory) {
    if (!targetCategory || targetCategory === 'all' || targetCategory === 'الكل') return true;
    if (!item) return false;

    const expectedType = parseTargetContentType(targetCategory);
    const itemType = getItemContentType(item);

    if (expectedType && expectedType !== itemType) {
      return false;
    }

    const targetRegion = resolveRegion(targetCategory);
    const itemRegion = resolveRegion(item.category || item.category_name || '');

    if (targetRegion === 'plays') return itemRegion === 'plays' || (item.category === 'plays');
    if (targetRegion === 'wrestling') return itemRegion === 'wrestling';
    if (targetRegion === 'documentary') return itemRegion === 'documentary';
    if (targetRegion === 'channels') return itemRegion === 'channels';

    if (targetRegion && itemRegion) {
      return targetRegion === itemRegion;
    }
    return true;
  }

  function getFeed(category, page = 1, limit = 40) {
    if (!category || category === 'all' || category === 'الكل') {
      return _inMemoryCatalog.slice(0, limit);
    }
    const matched = _inMemoryCatalog.filter(i => isCategoryMatch(i, category));
    const start = (page - 1) * limit;
    return matched.slice(start, start + limit);
  }

  function getDetails(id) {
    if (!id) return null;
    if (_ramCache.has(id)) return _ramCache.get(id);
    const found = _inMemoryCatalog.find(i => i.id === id);
    if (found) {
      _ramCache.set(id, found);
      return found;
    }
    return null;
  }

  function searchByTitle(query) {
    if (!query || query.length < 2) return [];
    const q = normalizeText(query);
    return _inMemoryCatalog.filter(i => {
      const t = normalizeText(i.title);
      const ar = normalizeText(i.arabic_title);
      return t.includes(q) || ar.includes(q);
    });
  }

  function addItem(item) {
    if (!item || !item.id) return;
    _inMemoryCatalog.unshift(item);
    _ramCache.set(item.id, item);
  }

  function clearCatalog() {
    _inMemoryCatalog = [];
    _ramCache.clear();
  }

  async function loadCatalog() {
    // 1. Instant 0ms IndexedDB retrieval
    if (window.DBStorage) {
      try {
        const cached = await window.DBStorage.getCatalog();
        if (Array.isArray(cached) && cached.length > 0) {
          _inMemoryCatalog = cached;
          cached.forEach(item => {
            if (item && item.id) _ramCache.set(item.id, item);
          });
        }
      } catch (_) {}
    }

    // 2. Fallback to bundled static data if memory cache still empty
    if (_inMemoryCatalog.length === 0 && Array.isArray(window.ATUBE_STATIC_CATALOG) && window.ATUBE_STATIC_CATALOG.length > 0) {
      _inMemoryCatalog = window.ATUBE_STATIC_CATALOG.slice();
      _inMemoryCatalog.forEach(item => {
        if (item && item.id) _ramCache.set(item.id, item);
      });
    }

    // 3. Ultra-Fast Zero-Latency initial feed from SQLite backend
    if (window.location.protocol === 'http:' || window.location.protocol === 'https:') {
      try {
        const fastFeed = await fetch('/api/media/feed?page=1&limit=60');
        if (fastFeed.ok) {
          const feedJson = await fastFeed.json();
          const items = Array.isArray(feedJson) ? feedJson : (feedJson.items || []);
          if (items.length > 0) {
            _inMemoryCatalog = items;
            items.forEach(item => {
              if (item && item.id) _ramCache.set(item.id, item);
            });
          }
        }
      } catch (e) {}

      // 4. Background non-blocking sync for full catalog
      setTimeout(async () => {
        try {
          const res = await fetch('catalog.json?t=' + Date.now());
          if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data) && data.length > 0) {
              _inMemoryCatalog = data;
              data.forEach(item => {
                if (item && item.id) _ramCache.set(item.id, item);
              });
              if (window.DBStorage) {
                window.DBStorage.saveCatalog(data).catch(() => {});
              }
            }
          }
        } catch (e) {
          console.warn('[MediaCatalog] Background catalog sync note:', e);
        }
      }, 1000);
    }

    return _inMemoryCatalog;
  }

  // ---- Series consolidation helpers (prevents episode-as-separate-card bug) ----
  const AR_SEASON_WORDS = {
    'الأول': 1, 'الثاني': 2, 'الثالث': 3, 'الرابع': 4, 'الخامس': 5,
    'السادس': 6, 'السابع': 7, 'الثامن': 8, 'التاسع': 9, 'العاشر': 10
  };

  function _parseEpisodeInfo(title) {
    if (!title) return null;
    let season = 1;
    let seasonMatch = title.match(/الموسم\s+(الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|\d+)/i);
    if (seasonMatch) {
      season = AR_SEASON_WORDS[seasonMatch[1]] || parseInt(seasonMatch[1], 10) || 1;
    }
    let epMatch = title.match(/الحلقة\s+(\d+)/i)
      || title.match(/[Ss](\d{1,2})[Ee](\d{1,2})/)
      || title.match(/Episode\s+(\d+)/i)
      || title.match(/[Ee](\d{1,3})(?:\s|$)/);
    const episode = epMatch ? parseInt(epMatch[1] || (epMatch[0].match(/(\d+)/) || ['', 0])[1], 10) : null;
    if (!episode) return null;
    return { season, episode };
  }

  function _parentSeriesName(title) {
    if (!title) return '';
    return title
      .replace(/\s*الحلقة\s*.*$/i, '')
      .replace(/\s*الموسم\s*.*$/i, '')
      .replace(/\s*[Ss]\d{1,2}[Ee]\d{1,2}.*$/, '')
      .replace(/\s*Episode\s*\d+.*$/i, '')
      .replace(/\s*[Ee]\d{1,3}\s+.*?$/, '')
      .trim();
  }

  // Groups flat episode-rows (content_type=series with episode markers in the
  // title) into a single series entity with nested seasons/episodes so the
  // home page renders ONE card per series instead of one card per episode.
   function consolidateSeriesItems(items) {
     if (!Array.isArray(items) || items.length === 0) return items;
     const episodicTypes = ['series', 'anime', 'tv_show'];
     const groups = new Map();                 // parentName -> { episodes: [] }
     const standaloneParents = new Map();       // parentName -> complete parent item
     const result = [];

     for (const item of items) {
       if (!episodicTypes.includes(item.content_type)) {
         result.push(item);
         continue;
       }
       const title = decodeHtmlEntities(item.arabic_title || item.title || '');
       const info = _parseEpisodeInfo(title);
       if (!info) {
         // Episodic-typed item with NO episode marker: a complete parent series
         // (carries seasons/servers of its own). Remember it so episodic children
         // sharing its name collapse into it instead of rendering a duplicate card.
         const parentName = _parentSeriesName(title) || title;
         standaloneParents.set(parentName, item);
         continue;
       }
       const parentName = _parentSeriesName(title) || (item.arabic_title || item.title || '');
       let g = groups.get(parentName);
       if (!g) {
         g = { parentName, episodes: [] };
         groups.set(parentName, g);
       }
       g.episodes.push({ ...item, _info: info });
     }

     // Emit standalone parents that have NO episodic children (already complete).
     for (const [name, parent] of standaloneParents) {
       if (!groups.has(name)) result.push(parent);
     }

     for (const g of groups.values()) {
       // De-duplicate by episode number, keeping the copy with the most servers.
       const byNum = new Map();
       const _serverCount = (ep) => (Array.isArray(ep.servers) ? ep.servers.length : 0) || ep.server_count || 0;
       for (const ep of g.episodes) {
         const n = ep._info.episode || 0;
         const prev = byNum.get(n);
         if (!prev || _serverCount(ep) > _serverCount(prev)) {
           byNum.set(n, ep);
         }
       }
       g.episodes = Array.from(byNum.values());
       g.episodes.sort((a, b) => {
         const sa = a._info.season || 1, sb = b._info.season || 1;
         if (sa !== sb) return sa - sb;
         return (a._info.episode || 0) - (b._info.episode || 0);
       });

       const rep = g.episodes[0];
       const seasonsMap = new Map();
       let serverCount = 0;
       g.episodes.forEach((ep) => {
         serverCount += ep.server_count || 0;
         const s = ep._info.season || 1;
         if (!seasonsMap.has(s)) seasonsMap.set(s, []);
         seasonsMap.get(s).push({
           episode_number: ep._info.episode,
           title: decodeHtmlEntities(ep.arabic_title || ep.title || ''),
           arabic_title: decodeHtmlEntities(ep.arabic_title || ep.title || ''),
           thumbnail: ep.poster || rep.poster,
           duration: ep.duration || '',
           synopsis: decodeHtmlEntities(ep.synopsis || ''),
           server_count: ep.server_count || 0
         });
       });
       const seasons = [];
       for (const [sNum, eps] of seasonsMap) {
         seasons.push({ season_number: sNum, title: g.parentName, episodes: eps, episode_count: eps.length });
       }

       // If a complete parent series (rich metadata / full seasons) already
       // exists for this name, prefer it so we do not duplicate the card. The
       // parent's own seasons/servers win; episode servers from children are
       // folded in only when the parent had none.
       const standalone = standaloneParents.get(g.parentName);
       const parentHasSeasons = standalone && Array.isArray(standalone.seasons) &&
         standalone.seasons.some(s => Array.isArray(s.episodes) && s.episodes.length > 0);
       if (parentHasSeasons) {
         const merged = {
           ...standalone,
           id: standalone.id,
           title: standalone.title,
           arabic_title: decodeHtmlEntities(standalone.arabic_title || standalone.title || g.parentName),
           content_type: standalone.content_type,
           total_seasons: (standalone.seasons || []).length,
           total_episodes: g.episodes.length,
           server_count: serverCount || standalone.server_count,
           episode_count: g.episodes.length,
           is_consolidated_series: true
         };
         result.push(merged);
         continue;
       }

       // Otherwise build a consolidated card from the episode rows, enriching
       // with any standalone-parent metadata if present.
       const base = standalone || rep;
       result.push({
         ...rep,
         ...(standalone ? {} : {}),
         id: (standalone && standalone.id) || rep.id,
         title: (standalone && standalone.title) || rep.title,
         arabic_title: decodeHtmlEntities((standalone && standalone.arabic_title) || g.parentName),
         poster: (standalone && standalone.poster) || rep.poster,
         backdrop: (standalone && standalone.backdrop) || rep.backdrop,
         synopsis: (standalone && standalone.synopsis) || rep.synopsis,
         rating: (standalone && standalone.rating) || rep.rating,
         year: (standalone && standalone.year) || rep.year,
         content_type: rep.content_type,
         total_seasons: seasons.length,
         total_episodes: g.episodes.length,
         server_count: serverCount || (standalone && standalone.server_count) || 0,
         episode_count: g.episodes.length,
         is_consolidated_series: true,
         seasons: seasons
       });
     }

     return result;
   }

  // ---- Async API-backed feed with caching & in-memory fallback ----
  async function fetchFeed(categoryKey, page = 1, limit = 30) {
    const key = `${categoryKey || 'all'}::${page}::${limit}`;
    const cached = _feedCache.get(key);
    if (cached && (Date.now() - cached.ts) < 60000) {
      return cached.data;
    }

    // Only query local backend API if actually running on localhost
    const isLocalBackend = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    if (!isLocalBackend) {
      const items = consolidateSeriesItems(getFeed(categoryKey, page, limit));
      const data = { items, pagination: { page, limit, total_items: items.length }, meta: { source: 'catalog' } };
      _feedCache.set(key, { data, ts: Date.now() });
      return data;
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);
      const res = await fetch(
        `/api/media/feed?category=${encodeURIComponent(categoryKey || 'all')}&page=${page}&limit=${limit}`,
        { signal: controller.signal }
      );
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        let items = Array.isArray(data) ? data : (data && Array.isArray(data.items) ? data.items : []);
        items = consolidateSeriesItems(items);
        const wrapped = { items, pagination: data.pagination || { page, limit, total_items: items.length }, meta: data.meta || {} };
        _feedCache.set(key, { data: wrapped, ts: Date.now() });
        return wrapped;
      }
    } catch (e) {
      // fall through to in-memory
    }

    const items = consolidateSeriesItems(getFeed(categoryKey, page, limit));
    const data = { items, pagination: { page, limit, total_items: items.length }, meta: { source: 'catalog-fallback' } };
    _feedCache.set(key, { data, ts: Date.now() });
    return data;
  }

  function getCachedFeed(categoryKey, page = 1, limit = 30) {
    const key = `${categoryKey || 'all'}::${page}::${limit}`;
    const cached = _feedCache.get(key);
    return cached ? cached.data.items : null;
  }

  function purgeFeedCache() {
    _feedCache.clear();
  }

  return {
    getAll: () => _inMemoryCatalog,
    getFeed: getFeed,
    getDetails: getDetails,
    search: searchByTitle,
    addItem: addItem,
    clearCatalog: clearCatalog,
    loadCatalog: loadCatalog,
    count: () => _inMemoryCatalog.length,
    generateProceduralPosterSVG: function(title, arabicTitle, year, category, rating) {
      const displayTitle = (arabicTitle || title || 'A TuBe Cinema').slice(0, 32);
      const displayYear = year ? String(year).slice(0, 4) : '';
      const displayCat = category || 'سينما';
      const displayRating = rating || '★ 8.5';
      const safeTitle = displayTitle.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const safeCat = displayCat.replace(/&/g, '&amp;').replace(/</g, '&lt;');

      const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450" width="100%" height="100%">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="50%" stop-color="#1e1b4b" />
      <stop offset="100%" stop-color="#020617" />
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00f2fe" />
      <stop offset="100%" stop-color="#4facfe" />
    </linearGradient>
  </defs>
  <rect width="300" height="450" fill="url(#g)" />
  <circle cx="150" cy="180" r="70" fill="none" stroke="url(#accent)" stroke-width="2" opacity="0.3" />
  <g transform="translate(115, 145)" fill="url(#accent)">
    <path d="M60 10H10C4.48 10 0 14.48 0 20v30c0 5.52 4.48 10 10 10h50c5.52 0 10-4.48 10-10V20c0-5.52-4.48-10-10-10zM20 20h10v10H20V20zm0 20h10v10H20V40zm20-20h10v10H40V20zm0 20h10v10H40V40z" opacity="0.8"/>
  </g>
  <rect x="20" y="24" width="70" height="22" rx="6" fill="rgba(255,255,255,0.1)" stroke="rgba(255,255,255,0.2)"/>
  <text x="55" y="39" fill="#94a3b8" font-size="11" font-family="sans-serif" text-anchor="middle" font-weight="bold">${safeCat}</text>
  <rect x="210" y="24" width="70" height="22" rx="6" fill="rgba(245,158,11,0.15)" stroke="rgba(245,158,11,0.3)"/>
  <text x="245" y="39" fill="#fbbf24" font-size="11" font-family="sans-serif" text-anchor="middle" font-weight="bold">${displayRating}</text>
  <text x="150" y="320" fill="#64748b" font-size="14" font-family="sans-serif" text-anchor="middle" font-weight="bold">${displayYear}</text>
  <text x="150" y="360" fill="#f8fafc" font-size="18" font-family="sans-serif" text-anchor="middle" font-weight="bold">${safeTitle}</text>
  <text x="150" y="420" fill="#38bdf8" font-size="12" font-family="sans-serif" text-anchor="middle" letter-spacing="2" opacity="0.6">A TUBE ULTRA HD</text>
</svg>`;
      return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    },
    generatePosterSVG: function(title, arabicTitle, year, category, rating) {
      return this.generateProceduralPosterSVG(title, arabicTitle, year, category, rating);
    },
    fetchFeed: fetchFeed,
    getCachedFeed: getCachedFeed,
    consolidateSeriesItems: consolidateSeriesItems,
    fetchFeedAsync: async function(category, page = 1, limit = 30) {
      const data = await fetchFeed(category, page, limit);
      return data.items;
    },
    purgeCache: () => {
      _ramCache.clear();
      purgeFeedCache();
    }
  };
})();

if (typeof window !== 'undefined') {
  window.MediaCatalog = MediaCatalog;
}
if (typeof globalThis !== 'undefined') {
  globalThis.MediaCatalog = MediaCatalog;
}

