/**
 * A TuBe Catalog Web Worker
 * Performs off-thread fuzzy search, category indexing, and JSON processing.
 */
let catalog = [];
let indexedSearch = [];

function normalizeArabic(txt) {
  if (!txt) return '';
  return String(txt)
    .toLowerCase()
    .replace(/[أإآ]/g, 'ا')
    .replace(/ة/g, 'ه')
    .replace(/ى/g, 'ي')
    .replace(/[\u064B-\u065F]/g, '') // Remove harakat
    .trim();
}

self.onmessage = function (e) {
  const { action, payload, id } = e.data || {};

  switch (action) {
    case 'SET_CATALOG': {
      catalog = Array.isArray(payload) ? payload : [];
      // Build search index in background
      indexedSearch = catalog.map((item, idx) => ({
        index: idx,
        id: item.id,
        normTitle: normalizeArabic(item.title || ''),
        normArTitle: normalizeArabic(item.arabic_title || ''),
        genres: (item.genres || []).map(g => normalizeArabic(g)).join(' '),
        category: item.category || '',
        year: String(item.year || '')
      }));
      self.postMessage({ id, action: 'SET_CATALOG_ACK', count: catalog.length });
      break;
    }

    case 'SEARCH': {
      const query = normalizeArabic(payload && payload.query ? payload.query : '');
      if (!query || query.length < 2) {
        self.postMessage({ id, action: 'SEARCH_RESULTS', results: [] });
        return;
      }
      const terms = query.split(/\s+/).filter(Boolean);
      const matches = [];

      for (let i = 0; i < indexedSearch.length && matches.length < 50; i++) {
        const itemIdx = indexedSearch[i];
        const fullString = `${itemIdx.normTitle} ${itemIdx.normArTitle} ${itemIdx.genres} ${itemIdx.year}`;
        const allMatch = terms.every(t => fullString.includes(t));
        if (allMatch) {
          matches.push(catalog[itemIdx.index]);
        }
      }

      self.postMessage({ id, action: 'SEARCH_RESULTS', results: matches });
      break;
    }

    case 'FILTER_CATEGORY': {
      const { category, contentType } = payload || {};
      const filtered = catalog.filter(item => {
        if (contentType && item.content_type !== contentType) return false;
        if (category && item.category !== category) return false;
        return true;
      });
      self.postMessage({ id, action: 'FILTER_RESULTS', results: filtered });
      break;
    }

    default:
      self.postMessage({ id, error: 'Unknown action' });
  }
};
