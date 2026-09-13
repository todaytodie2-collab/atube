/**
 * A TuBe Next-Gen System Orchestrator
 * - 0ms Instant Boot & IndexedDB Hydration
 * - Background Stale-While-Revalidate (SWR) Engine
 * - Off-Thread Web Worker Search & Processing
 * - Viewport IntersectionObserver Lazy-Renderer
 * - Self-Healing Health Watchdog & Reconnect Engine
 */

const SystemOrchestrator = (function () {
  'use strict';

  let _worker = null;
  let _healthInterval = null;
  let _isOnline = true;
  let _lazyObserver = null;
  let _healthPillEl = null;

  function initWorker() {
    if (window.Worker && window.location.protocol !== 'file:') {
      try {
        _worker = new Worker('js/catalog-worker.js');
        _worker.onmessage = function (e) {
          const { action, results, count } = e.data || {};
          if (action === 'SET_CATALOG_ACK') {
            console.log(`[Worker] Catalog Indexed off-thread (${count} items).`);
          }
          if (action === 'SEARCH_RESULTS' && window.onWorkerSearchResults) {
            window.onWorkerSearchResults(results);
          }
        };
      } catch (err) {
        console.warn('[SystemOrchestrator] Web Worker init skipped:', err);
      }
    }
  }

  function postToWorker(action, payload) {
    if (_worker) {
      _worker.postMessage({ action, payload, id: Date.now() });
    }
  }

  // Self-Healing Watchdog
  function startHealthWatchdog() {
    if (window.location.protocol === 'file:') return;

    _healthPillEl = document.getElementById('system-health-pill');

    async function checkHealth() {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000);
        const res = await fetch('/api/health', { signal: controller.signal });
        clearTimeout(timeoutId);

        if (res.ok) {
          if (!_isOnline) {
            _isOnline = true;
            showHealthStatus('تمت استعادة الاتصال بالخادم بنجاح ✓', 'ok', 3000);
            // Silent refresh of fresh data
            if (window.MediaCatalog && typeof MediaCatalog.loadCatalog === 'function') {
              MediaCatalog.loadCatalog();
            }
          }
        } else {
          setOfflineState();
        }
      } catch (err) {
        setOfflineState();
      }
    }

    function setOfflineState() {
      if (_isOnline) {
        _isOnline = false;
        showHealthStatus('وضع عدم الاتصال: يتم العمل بالكتالوج المخزن محلياً', 'offline', 6000);
      }
    }

    // Initial check + 25s recurring interval
    setTimeout(checkHealth, 3000);
    _healthInterval = setInterval(checkHealth, 25000);

    window.addEventListener('online', checkHealth);
    window.addEventListener('offline', setOfflineState);
  }

  function showHealthStatus(message, state, duration = 4000) {
    if (!_healthPillEl) return;
    const textEl = _healthPillEl.querySelector('.health-text');
    const dotEl = _healthPillEl.querySelector('.system-health-dot');
    if (textEl) textEl.textContent = message;
    if (dotEl) {
      dotEl.className = 'system-health-dot ' + (state || 'ok');
    }
    _healthPillEl.classList.add('show');
    if (duration > 0) {
      setTimeout(() => {
        if (_healthPillEl) _healthPillEl.classList.remove('show');
      }, duration);
    }
  }

  // Progressive Viewport Lazy Loader
  function initLazyObserver(renderCallback) {
    if (!('IntersectionObserver' in window)) return null;

    _lazyObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const target = entry.target;
          observer.unobserve(target);
          if (typeof renderCallback === 'function') {
            renderCallback(target);
          }
        }
      });
    }, {
      root: null,
      rootMargin: '200px 0px', // Preload 200px before scrolling into view
      threshold: 0.01
    });

    return _lazyObserver;
  }

  function observeLazyContainer(element) {
    if (_lazyObserver && element) {
      _lazyObserver.observe(element);
    }
  }

  // High-Speed IndexedDB Hydrator & Stale-While-Revalidate
  async function hydrateCatalogFast(onHydrated) {
    let localData = null;

    // 1. Try IndexedDB first (0ms instantaneous boot)
    if (window.DBStorage) {
      try {
        localData = await DBStorage.getCatalog();
      } catch (_) {}
    }

    if (Array.isArray(localData) && localData.length > 0) {
      console.log(`[SystemOrchestrator] 0ms Hydrated ${localData.length} items from IndexedDB.`);
      if (typeof onHydrated === 'function') {
        onHydrated(localData, true); // true = from cache
      }
      postToWorker('SET_CATALOG', localData);
    }

    // 2. Silent background SWR revalidation
    if (window.location.protocol !== 'file:') {
      fetch('catalog.json?t=' + Date.now())
        .then(res => res.ok ? res.json() : null)
        .then(freshData => {
          if (Array.isArray(freshData) && freshData.length > 0) {
            console.log(`[SystemOrchestrator] SWR Background fetched ${freshData.length} items.`);
            if (window.DBStorage) {
              DBStorage.saveCatalog(freshData);
            }
            postToWorker('SET_CATALOG', freshData);
            if (typeof onHydrated === 'function') {
              onHydrated(freshData, false); // false = fresh
            }
          }
        })
        .catch(() => {});
    }
  }

  return {
    init: function () {
      initWorker();
      startHealthWatchdog();
    },
    postToWorker,
    hydrateCatalogFast,
    initLazyObserver,
    observeLazyContainer,
    showHealthStatus,
    isOnline: () => _isOnline
  };
})();

if (typeof window !== 'undefined') {
  window.SystemOrchestrator = SystemOrchestrator;
}
