/**
 * A TuBe High-Performance IndexedDB Storage Engine
 * Non-blocking, multi-megabyte offline storage for catalog, feeds, and playback history.
 */
const DBStorage = (function () {
  'use strict';

  const DB_NAME = 'atube_storage_v2';
  const DB_VERSION = 1;
  let _db = null;
  let _initPromise = null;

  function init() {
    if (_initPromise) return _initPromise;
    _initPromise = new Promise((resolve) => {
      if (!('indexedDB' in window)) {
        console.warn('[DBStorage] IndexedDB not available, fallback to in-memory/localStorage.');
        return resolve(null);
      }
      try {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = (e) => {
          const db = e.target.result;
          if (!db.objectStoreNames.contains('catalog_store')) {
            db.createObjectStore('catalog_store', { keyPath: 'key' });
          }
          if (!db.objectStoreNames.contains('feeds_store')) {
            db.createObjectStore('feeds_store', { keyPath: 'key' });
          }
          if (!db.objectStoreNames.contains('meta_store')) {
            db.createObjectStore('meta_store', { keyPath: 'key' });
          }
        };
        req.onsuccess = (e) => {
          _db = e.target.result;
          resolve(_db);
        };
        req.onerror = () => {
          console.warn('[DBStorage] IndexedDB open error, continuing with fallback');
          resolve(null);
        };
      } catch (err) {
        console.warn('[DBStorage] IndexedDB init exception:', err);
        resolve(null);
      }
    });
    return _initPromise;
  }

  async function setItem(storeName, key, data) {
    const db = await init();
    if (!db) {
      try {
        localStorage.setItem(`atube_db_${storeName}_${key}`, JSON.stringify(data));
      } catch (_) {}
      return;
    }
    return new Promise((resolve) => {
      try {
        const tx = db.transaction([storeName], 'readwrite');
        const store = tx.objectStore(storeName);
        store.put({ key, data, updated_at: Date.now() });
        tx.oncomplete = () => resolve(true);
        tx.onerror = () => resolve(false);
      } catch (_) {
        resolve(false);
      }
    });
  }

  async function getItem(storeName, key) {
    const db = await init();
    if (!db) {
      try {
        const val = localStorage.getItem(`atube_db_${storeName}_${key}`);
        return val ? JSON.parse(val) : null;
      } catch (_) {
        return null;
      }
    }
    return new Promise((resolve) => {
      try {
        const tx = db.transaction([storeName], 'readonly');
        const store = tx.objectStore(storeName);
        const req = store.get(key);
        req.onsuccess = () => {
          if (req.result && req.result.data) {
            resolve(req.result.data);
          } else {
            resolve(null);
          }
        };
        req.onerror = () => resolve(null);
      } catch (_) {
        resolve(null);
      }
    });
  }

  return {
    init,
    saveCatalog: (items) => setItem('catalog_store', 'main_catalog', items),
    getCatalog: () => getItem('catalog_store', 'main_catalog'),
    saveFeed: (catKey, items) => setItem('feeds_store', `feed_${catKey}`, items),
    getFeed: (catKey) => getItem('feeds_store', `feed_${catKey}`),
    setMeta: (k, v) => setItem('meta_store', k, v),
    getMeta: (k) => getItem('meta_store', k)
  };
})();

if (typeof window !== 'undefined') {
  window.DBStorage = DBStorage;
}
