/* ==========================================================================
   A TuBe Media Catalog Engine (Clean Slate)
   Holds live items and custom added media entities.
   ========================================================================== */

const MediaCatalog = (function () {
  'use strict';

  const _ramCache = new Map();
  let _inMemoryCatalog = [];

  function normalizeText(txt) {
    if (!txt) return '';
    return String(txt)
      .toLowerCase()
      .replace(/[أإآ]/g, 'ا')
      .replace(/ة/g, 'ه')
      .replace(/ى/g, 'ي')
      .trim();
  }

  const TARGET_TO_CANONICAL = {
    'foreign': 'foreign',
    'أفلام أجنبي': 'foreign',
    'أفلام أجنبية': 'foreign',
    'افلام اجنبي': 'foreign',
    'افلام اجنبية': 'foreign',
    'movies': 'foreign',
    'hollywood': 'foreign',
    
    'arabic': 'arabic',
    'أفلام عربي': 'arabic',
    'أفلام عربية': 'arabic',
    'افلام عربي': 'arabic',
    'افلام عربية': 'arabic',
    
    'arabic_series': 'arabic_series',
    'مسلسلات عربي': 'arabic_series',
    'مسلسلات عربية': 'arabic_series',
    'دراما عربية': 'arabic_series',
    
    'turkish': 'turkish',
    'مسلسلات تركي': 'turkish',
    'مسلسلات وأفلام تركي': 'turkish',
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
    
    'channels': 'channels',
    'قنوات مباشرة': 'channels',
    'قنوات البث المباشر': 'channels',
    'قنوات': 'channels',
    'live': 'channels',
    
    'wrestling': 'wrestling',
    'مصارعة حرة': 'wrestling',
    'مصارعة': 'wrestling',
    'wwe': 'wrestling',
    
    'plays': 'plays',
    'مسرحيات': 'plays',
    'مسرحيات كوميدية': 'plays',
    
    'documentary': 'documentary',
    'أفلام وثائقية': 'documentary',
    'وثائقي': 'documentary'
  };

  function resolveCanonicalCategory(catStr) {
    if (!catStr) return '';
    const norm = normalizeText(catStr);
    if (TARGET_TO_CANONICAL[norm]) return TARGET_TO_CANONICAL[norm];
    for (const [k, v] of Object.entries(TARGET_TO_CANONICAL)) {
      if (norm === normalizeText(k)) return v;
    }
    // Keyword Fallbacks - ordered from most specific to general
    if (norm.includes('تركي')) return 'turkish';
    if (norm.includes('هندي') || norm.includes('بوليوود')) return 'indian';
    if (norm.includes('انمي') || norm.includes('كرتون')) return 'anime';
    if (norm.includes('مسرح')) return 'plays';
    if (norm.includes('مصارع') || norm.includes('wwe')) return 'wrestling';
    if (norm.includes('وثائق')) return 'documentary';
    if (norm.includes('قنوات') || norm.includes('مباشر')) return 'channels';
    if (norm.includes('مسلسلات عربي') || norm.includes('مسلسل عربي') || norm.includes('arabic_series')) return 'arabic_series';
    if (norm.includes('افلام عربي') || norm.includes('فيلم عربي') || norm === 'arabic') return 'arabic';
    if (norm.includes('اجنبي') || norm === 'foreign') return 'foreign';
    return norm;
  }

  function isCategoryMatch(itemCategory, targetCategory) {
    if (!targetCategory || targetCategory === 'all' || targetCategory === 'الكل') return true;
    const targetCanon = resolveCanonicalCategory(targetCategory);
    const itemCanon = resolveCanonicalCategory(itemCategory);
    return targetCanon === itemCanon;
  }

  function getFeed(category, page = 1, limit = 30) {
    if (!category || category === 'all' || category === 'الكل') {
      return _inMemoryCatalog.slice(0, limit);
    }
    const matched = _inMemoryCatalog.filter(i => {
      return isCategoryMatch(i.category, category) || isCategoryMatch(i.category_name, category);
    });
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
    const idx = _inMemoryCatalog.findIndex(i => i.id === item.id);
    if (idx >= 0) {
      _inMemoryCatalog[idx] = item;
    } else {
      _inMemoryCatalog.push(item);
    }
    _ramCache.set(item.id, item);
  }

  function clearCatalog() {
    _inMemoryCatalog = [];
    _ramCache.clear();
  }

  async function loadCatalog() {
    try {
      const res = await fetch('/catalog.json?t=' + Date.now());
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          _inMemoryCatalog = data;
          data.forEach(item => {
            if (item && item.id) _ramCache.set(item.id, item);
          });
          return _inMemoryCatalog;
        }
      }
    } catch (e) {
      console.warn('[MediaCatalog] Failed to load catalog.json:', e);
    }
    return _inMemoryCatalog;
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
    generateProceduralPosterSVG: () => 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450" fill="%230b0f19"/%3E',
    generatePosterSVG: () => 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450" fill="%230b0f19"/%3E',
    fetchFeedAsync: async function(category, page = 1, limit = 30) {
      try {
        const res = await fetch(`/api/media/feed?category=${encodeURIComponent(category || 'all')}&page=${page}&limit=${limit}`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) return data;
          if (data && Array.isArray(data.items)) return data.items;
        }
      } catch (_) {}
      return getFeed(category, page, limit);
    },
    purgeCache: () => {
      _ramCache.clear();
    }
  };
})();

if (typeof window !== 'undefined') {
  window.MediaCatalog = MediaCatalog;
}
if (typeof globalThis !== 'undefined') {
  globalThis.MediaCatalog = MediaCatalog;
}

