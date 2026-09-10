/* ==========================================================================
   A Tube Application Logic
   Matches Reference UI, Manages Data, Views, Routing, Interactions & Events
   ========================================================================== */

// 1. All Categorized Sections Configuration for Home Page Carousels & Internal Views
const CATEGORY_DEFINITIONS = [
  {
    key: 'أفلام أجنبي',
    title: 'أفلام أجنبي',
    icon: '🎬',
    desc: 'أحدث وأقوى إصدارات هوليوود والسينما العالمية بجودة Ultra HD 4K مع سيرفرات مشاهدة سريعة'
  },
  {
    key: 'مسلسلات أجنبي',
    title: 'مسلسلات أجنبي',
    icon: '📺',
    desc: 'أقوى المسلسلات الأجنبية والعالمية مترجمة بجميع المواسم والحلقات الكاملة'
  },
  {
    key: 'أفلام عربي',
    title: 'أفلام عربي',
    icon: '🎥',
    desc: 'أحدث أفلام السينما المصرية والعربية الحصرية بجودة فائقة'
  },
  {
    key: 'مسلسلات عربي',
    title: 'مسلسلات عربي',
    icon: '🍿',
    desc: 'روائع الدراما المصرية والسورية والخليجية بحلقات كاملة'
  },
  {
    key: 'أفلام تركي',
    title: 'أفلام تركي',
    icon: '🇹🇷',
    desc: 'روائع السينما التركية الرومانسية والدرامية والأكشن مترجمة ومدبلجة'
  },
  {
    key: 'مسلسلات تركي',
    title: 'مسلسلات تركي',
    icon: '🇹🇷',
    desc: 'أضخم المسلسلات التركية التاريخية والدرامية المدبلجة والمترجمة'
  },
  {
    key: 'أفلام أنمي',
    title: 'أفلام أنمي',
    icon: '⛩️',
    desc: 'أقوى أفلام الأنمي الياباني والرسوم المتحركة العالمية بجودة عالية'
  },
  {
    key: 'مسلسلات أنمي',
    title: 'مسلسلات أنمي',
    icon: '⛩️',
    desc: 'حلقات ومواسم مسلسلات الأنمي والكارتون الأسطورية مترجمة ومدبلجة'
  },
  {
    key: 'أفلام هندي',
    title: 'السينما الهندية (بوليوود)',
    icon: '🇮🇳',
    desc: 'أقوى أفلام الأكشن والإثارة والدراما الهندية المترجمة بجودة فائقة'
  },
  {
    key: 'مسلسلات هندي',
    title: 'مسلسلات هندي',
    icon: '🇮🇳',
    desc: 'أشهر وأحدث المسلسلات الهندية والدراما المدبلجة'
  },
  {
    key: 'قنوات مباشرة',
    title: 'قنوات البث المباشر HD',
    icon: '📺',
    desc: 'بث حي ومباشر بدون تقطيع للقنوات الإخبارية والمنوعة والرياضية'
  },
  {
    key: 'مصارعة حرة',
    title: 'برامج ومصارعة WWE',
    icon: '🤼‍♂️',
    desc: 'عروض المصارعة الحرة الأسبوعية والبرامج الرياضية والترفيهية'
  },
  {
    key: 'مسرحيات',
    title: 'مسرحيات كوميدية',
    icon: '🎭',
    desc: 'أشهر المسرحيات الكوميدية والنجوم العرب'
  },
  {
    key: 'أفلام وثائقية',
    title: 'أفلام وثائقية',
    icon: '🎞️',
    desc: 'أقوى الأفلام والبرامج الوثائقية عن الطبيعة والكون والتاريخ'
  }
];

let currentCategoryViewName = null;
let currentCategoryItems = [];

// ==========================================================================
// A TuBe Smart Splash Orchestrator (Zero-Lag Background Preparation)
// ==========================================================================
const SplashManager = (function () {
  let splashEl = null;
  let progressBar = null;
  let statusText = null;
  let isFinished = false;
  const mountTime = Date.now();

  function init() {
    splashEl = document.getElementById('app-splash-screen');
    progressBar = document.getElementById('splash-progress-bar');
    statusText = document.getElementById('splash-status-text');
  }

  function setProgress(percent, message) {
    if (progressBar) progressBar.style.width = `${Math.min(100, Math.max(5, percent))}%`;
    if (statusText && message) statusText.textContent = message;
  }

  function dismiss(onDone) {
    if (isFinished) return;
    isFinished = true;
    setProgress(100, 'اكتمل التجهيز • مرحباً بك في A TuBe');

    const elapsed = Date.now() - mountTime;
    const minWait = Math.max(0, 650 - elapsed);

    setTimeout(() => {
      if (splashEl) {
        splashEl.classList.add('is-hidden');
        setTimeout(() => {
          splashEl.style.display = 'none';
          if (typeof onDone === 'function') onDone();
        }, 500);
      } else if (typeof onDone === 'function') {
        onDone();
      }
    }, minWait);
  }

  return {
    init,
    setProgress,
    dismiss,
    isDone: () => isFinished
  };
})();

document.addEventListener('DOMContentLoaded', async () => {
  // 0. Initialize Splash Orchestrator
  SplashManager.init();
  SplashManager.setProgress(20, 'تهيئة مشغل الفيديو وقاعدة البيانات...');

  // 1. Initialize Video Player & Movie Details
  InAppPlayer.init();
  MovieDetails.init();

  // 2. Perform Storage Maintenance (Prune obsolete history/playhead tokens)
  cleanupOldStorage();
  SplashManager.setProgress(45, 'مزامنة الكتالوج والأقسام الحصرية...');

  // 3. Load Real Catalog from Server
  if (window.MediaCatalog && typeof MediaCatalog.loadCatalog === 'function') {
    try {
      await MediaCatalog.loadCatalog();
    } catch (e) {
      console.warn('Catalog load note:', e);
    }
  }
  SplashManager.setProgress(75, 'تجهيز القنوات والصفحة الرئيسية...');

  // 4. Render Hero Billboard Banner & Category Carousels
  renderHeroBillboard();
  renderHomeCarousels();

  // 4b. Background-preload API feeds for every home category, then re-render
  //     so the carousels reflect live /api/media/feed data (one card per series).
  preloadHomeFeeds().then(() => {
    renderHomeCarousels();
    if (window.RemoteControl && typeof RemoteControl.refresh === 'function') {
      setTimeout(() => RemoteControl.refresh(), 100);
    }
  }).catch(() => {});

  // 5. Setup App Navigation (Sidebar, Category Internal Pages, Quick Tabs)
  setupSidebarNavigation();
  setupFilterTabs();

  // 6. Setup Header Actions (Search, Modals, Language)
  setupHeaderActions();

  // 7. Setup IPTVSettings Modal
  setupIPTVModal();

  SplashManager.setProgress(95, 'جاهز للتصفح والتشغيل...');

  // 8. Dismiss Splash smoothly once UI is completely ready
  SplashManager.dismiss(() => {
    RemoteControl.init();
  });

  // Failsafe watchdog: Under no circumstances should splash screen stay longer than 1.8s
  setTimeout(() => {
    if (!SplashManager.isDone()) {
      SplashManager.dismiss(() => {
        RemoteControl.init();
      });
    }
  }, 1800);
});

// Storage Maintenance: Prevent localStorage bloat on Android TV
function cleanupOldStorage() {
  try {
    const histRaw = localStorage.getItem('atube_history');
    if (histRaw) {
      let history = JSON.parse(histRaw);
      const sixtyDaysAgo = Date.now() - (60 * 24 * 60 * 60 * 1000);
      history = history.filter(h => !h.timestamp || h.timestamp > sixtyDaysAgo);
      if (history.length > 50) history = history.slice(0, 50);
      localStorage.setItem('atube_history', JSON.stringify(history));
    }

    const posKeys = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith('atube_pos_')) {
        posKeys.push(k);
      }
    }
    if (posKeys.length > 60) {
      posKeys.slice(0, posKeys.length - 60).forEach(k => localStorage.removeItem(k));
    }
  } catch (e) {
    console.warn('[A Tube Storage Cleanup]', e);
  }
}

// Arabic Fuzzy Search Normalization
function normalizeArabicSearch(str) {
  if (!str) return '';
  return String(str)
    .toLowerCase()
    .replace(/[\u064B-\u065F\u0670]/g, '') // Tashkeel / Harakat
    .replace(/[أإآآ]/g, 'ا')
    .replace(/ة/g, 'ه')
    .replace(/[ىي]/g, 'ي')
    .replace(/ؤ/g, 'و')
    .replace(/ئ/g, 'ي')
    .replace(/[-_.,!?:]/g, ' ')
    .trim();
}

// Search History Utilities
function getSearchHistory() {
  try {
    return JSON.parse(localStorage.getItem('atube_search_history') || '[]');
  } catch (e) {
    return [];
  }
}

function saveSearchQuery(query) {
  const q = (query || '').trim();
  if (!q || q.length < 2) return;
  try {
    let hist = getSearchHistory();
    hist = hist.filter(item => item.toLowerCase() !== q.toLowerCase());
    hist.unshift(q);
    if (hist.length > 5) hist = hist.slice(0, 5);
    localStorage.setItem('atube_search_history', JSON.stringify(hist));
  } catch (e) {}
}

function clearSearchHistory() {
  try {
    localStorage.removeItem('atube_search_history');
  } catch (e) {}
}

function renderSearchHistoryDropdown(dropdownEl, searchInput) {
  if (!dropdownEl) return;
  const history = getSearchHistory();
  if (history.length === 0) {
    dropdownEl.classList.add('is-hidden');
    dropdownEl.innerHTML = '';
    return;
  }

  dropdownEl.innerHTML = `
    <div class="search-history-header">
      <span>🕒 عمليات البحث الأخيرة</span>
      <button type="button" class="search-history-clear-btn" id="clear-search-history-btn">مسح الكل</button>
    </div>
    <div class="search-history-chips"></div>
  `;

  const chipsContainer = dropdownEl.querySelector('.search-history-chips');
  history.forEach(term => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'search-history-chip dpad-focusable';
    chip.innerHTML = `<span>🔍</span> <span>${escapeHtml(term)}</span>`;
    chip.addEventListener('click', (e) => {
      e.stopPropagation();
      if (searchInput) {
        searchInput.value = term;
        filterContent(term);
        dropdownEl.classList.add('is-hidden');
      }
    });
    chipsContainer.appendChild(chip);
  });

  const clearBtn = dropdownEl.querySelector('#clear-search-history-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      clearSearchHistory();
      dropdownEl.classList.add('is-hidden');
      dropdownEl.innerHTML = '';
    });
  }

  dropdownEl.classList.remove('is-hidden');
}

// Security Utility: Strict HTML Sanitizer to prevent XSS injection
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Performance Utilities: High-Speed In-Memory Debounce
function debounce(fn, delay = 220) {
  let timer = null;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

// Performance Utilities: High-Efficiency IntersectionObserver Image Lazy Loader
const cardImageObserver = (typeof window !== 'undefined' && 'IntersectionObserver' in window)
  ? new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
          }
          observer.unobserve(img);
        }
      });
    }, { rootMargin: '180px 0px', threshold: 0.01 })
  : null;

// Helper: Create a standard movie/series card with instant Details open
function createMediaCard(m, index = 0) {
  const card = document.createElement('div');
  card.className = 'program-card dpad-focusable';
  card.tabIndex = 0;
  card.dataset.index = index;

  const isSeries = (m.content_type === 'series' || m.content_type === 'anime' || m.content_type === 'tv_show');
  let subLabel;
  if (isSeries) {
    const epCount = (m.total_episodes || m.episode_count || 0);
    const seasonCount = m.total_seasons || 1;
    if (epCount > 1) {
      subLabel = `${epCount} حلقة • ${seasonCount} موسم • حلقات كاملة`;
    } else if (epCount === 1) {
      subLabel = `مسلسل • ${seasonCount} موسم`;
    } else {
      subLabel = `${seasonCount || 1} مواسم • حلقات كاملة`;
    }
  } else {
    subLabel = `${(m.servers && m.servers.length) || m.server_count || 3} سيرفرات متاحة`;
  }

  const fallbackSvg = (typeof MediaCatalog !== 'undefined' && MediaCatalog.generateProceduralPosterSVG)
    ? MediaCatalog.generateProceduralPosterSVG(m.title, m.arabic_title, m.year, m.category_name || m.category, m.rating)
    : 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 200 300\' fill=\'%2308101a\'/%3E';

  const posterSrc = m.poster || fallbackSvg;
  const cleanTitle = safeHtml(m.arabic_title || m.title || 'عمل سينمائي');
  const cleanRating = safeHtml(m.rating || '★ 8.5 IMDb');
  const cleanSubLabel = safeHtml(subLabel);
  const cleanAlt = safeHtml(m.title || '');

  card.innerHTML = `
    <div class="program-thumb">
      <img src="${fallbackSvg}"
           data-src="${posterSrc}"
           alt="${cleanAlt}"
           decoding="async"
           class="lazy-poster-img">
      <span class="program-card-badge">${cleanRating}</span>
    </div>
    <div class="program-info">
      <div class="program-title">${cleanTitle}</div>
      <div class="program-category" style="color: var(--primary-cyan); font-weight: 700;">${cleanSubLabel}</div>
    </div>
  `;

  // Attach lazy loading observer and dynamic error fallback
  const imgEl = card.querySelector('.lazy-poster-img');
  if (imgEl) {
    imgEl.onerror = () => {
      imgEl.onerror = null;
      imgEl.src = fallbackSvg;
    };
    if (cardImageObserver) {
      cardImageObserver.observe(imgEl);
    } else {
      imgEl.src = posterSrc;
    }
  }

  card.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const ctrl = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
    if (ctrl && typeof ctrl.open === 'function') {
      ctrl.open(m);
    } else {
      console.warn('MovieDetails controller not ready');
    }
  });

  return card;
}

// Helper: Create a standard live channel card
function createChannelCard(ch, index = 0) {
  if (window.IPTVEngine && typeof window.IPTVEngine.createChannelCardElement === 'function') {
    return window.IPTVEngine.createChannelCardElement(ch, index);
  }

  const card = document.createElement('div');
  card.className = 'live-channel-card dpad-focusable';
  card.tabIndex = 0;
  card.dataset.index = index;

  const cleanName = escapeHtml(ch.name || 'قناة بث مباشر');
  const cleanBadge = escapeHtml(ch.badge || 'LIVE 1080p FHD');
  const cleanCategory = escapeHtml(ch.category || 'بث مباشر');
  const fallbackSvg = window.IPTVEngine && window.IPTVEngine.generateChannelLogoSVG
    ? window.IPTVEngine.generateChannelLogoSVG(cleanName, cleanCategory)
    : 'assets/aljazeera.svg';
  const logoSrc = (ch.logo && typeof ch.logo === 'string') ? ch.logo : fallbackSvg;

  card.innerHTML = `
    <div class="live-pulse-wrapper">
      <span class="live-dot-pulse"></span>
      <span class="live-badge-text">${cleanBadge}</span>
    </div>
    <div class="channel-category-tag">${cleanCategory}</div>
    <div class="channel-logo-container">
      <img class="channel-logo-img" src="${logoSrc}" alt="${cleanName}" onerror="this.onerror=null; this.src='${fallbackSvg}';">
    </div>
    <div class="channel-card-footer">
      <span class="channel-name-title" title="${cleanName}">${cleanName}</span>
    </div>
  `;

  card.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
    if (player && typeof player.playMedia === 'function') {
      player.playMedia({
        ...ch,
        is_live: true,
        category: ch.category || 'قنوات مباشرة'
      });
    }
  });

  return card;
}

// Fallback helper
function getDefaultMoviesFallback(categoryKey) {
  return [];
}

// Helper: Fetch items for a category (API-backed with in-memory fallback)
function getItemsForCategory(categoryKey) {
  if (categoryKey === 'قنوات مباشرة' || categoryKey === 'channels' || categoryKey === 'قنوات البث المباشر') {
    if (window.IPTVEngine && typeof window.IPTVEngine.getDefaultChannels === 'function') {
      return window.IPTVEngine.getDefaultChannels() || [];
    }
  }

  const catalog = window.MediaCatalog || (typeof MediaCatalog !== 'undefined' ? MediaCatalog : null);

  // Prefer the API-backed, cached + consolidated feed (one card per series)
  if (catalog && typeof catalog.getCachedFeed === 'function') {
    const cached = catalog.getCachedFeed(categoryKey, 1, 40);
    if (cached && cached.length > 0) return cached;
  }

  // Fallback to the in-memory catalog (file:// or cache miss)
  if (catalog && typeof catalog.getFeed === 'function') {
    const items = catalog.getFeed(categoryKey) || [];
    if (items.length > 0) {
      if (typeof catalog.consolidateSeriesItems === 'function') {
        return catalog.consolidateSeriesItems(items);
      }
      return items;
    }
  }

  if (categoryKey === 'قنوات مباشرة' || categoryKey === 'channels') {
    if (window.IPTVEngine && typeof window.IPTVEngine.getDefaultChannels === 'function') {
      return window.IPTVEngine.getDefaultChannels() || [];
    }
  }
  return [];
}

// Preload API feeds for all home categories in parallel (non-blocking)
async function preloadHomeFeeds() {
  const catalog = window.MediaCatalog || (typeof MediaCatalog !== 'undefined' ? MediaCatalog : null);
  if (!catalog || typeof catalog.fetchFeed !== 'function') return;
  const keys = CATEGORY_DEFINITIONS.map(d => d.key).filter(k => k !== 'قنوات مباشرة');
  try {
    await Promise.all(keys.map(k => catalog.fetchFeed(k, 1, 40).catch(() => null)));
  } catch (_) {}
}


// Render Hero Billboard Banner with real featured movie or keep empty if none
function renderHeroBillboard() {
  const bannerEl = document.getElementById('hero-banner');
  const contentEl = document.getElementById('hero-content');
  const bgImg = document.getElementById('hero-bg-img');
  if (!bannerEl || !contentEl) return;

  const allItems = (window.MediaCatalog && typeof MediaCatalog.getAll === 'function')
    ? MediaCatalog.getAll()
    : [];

  if (allItems.length === 0) {
    bannerEl.style.display = 'none';
    contentEl.innerHTML = '';
    return;
  }

  const featured = allItems[0];
  bannerEl.style.display = 'flex';

  if (bgImg) {
    bgImg.src = featured.backdrop || featured.poster;
    bgImg.style.display = 'block';
  }

  contentEl.innerHTML = `
    <div class="hero-badge">
      <span>★</span>
      <span>${safeHtml(featured.rating || '★ 8.8 IMDb')}</span>
      <span>•</span>
      <span>${safeHtml(featured.quality || '1080p FHD')}</span>
      <span>•</span>
      <span>${safeHtml(featured.year || '2026')}</span>
    </div>
    <h1 class="hero-title">${safeHtml(featured.arabic_title || featured.title)}</h1>
    <div class="hero-subtitle">${safeHtml(featured.title !== featured.arabic_title ? featured.title : (featured.translation || 'مترجم للعربية'))}</div>
    <p class="hero-desc">${safeHtml(featured.synopsis || '')}</p>
    <div class="hero-actions">
      <button class="btn-primary dpad-focusable" id="hero-watch-btn">
        <span>▶</span>
        <span>مشاهدة العمل</span>
      </button>
      <button class="btn-secondary dpad-focusable" id="hero-details-btn">
        <span>⚡</span>
        <span>سيرفرات البث (${(featured.servers || []).length})</span>
      </button>
    </div>
  `;

  const watchBtn = contentEl.querySelector('#hero-watch-btn');
  const detailsBtn = contentEl.querySelector('#hero-details-btn');

  if (watchBtn) {
    watchBtn.addEventListener('click', () => {
      const details = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
      if (details && typeof details.open === 'function') {
        details.open(featured);
      }
    });
  }

  if (detailsBtn) {
    detailsBtn.addEventListener('click', () => {
      const details = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
      if (details && typeof details.open === 'function') {
        details.open(featured);
      }
    });
  }
}

// Render All Home Category Carousels in animated horizontal tracks
function renderHomeCarousels() {
  const container = document.getElementById('home-categories-container');
  if (!container) return;
  container.innerHTML = '';

  CATEGORY_DEFINITIONS.forEach(def => {
    const items = getItemsForCategory(def.key);
    if (!items || items.length === 0) return;

    const section = document.createElement('section');
    section.className = 'category-row-section';
    section.id = `row-${encodeURIComponent(def.key)}`;

    // Row Header
    const header = document.createElement('div');
    header.className = 'category-row-header';
    header.innerHTML = `
      <div class="category-row-title-wrap">
        <span class="category-row-icon">${def.icon}</span>
        <h2 class="category-row-title">${def.title}</h2>
        <span class="category-count-pill">${items.length} عملاً</span>
      </div>
      <div class="category-row-actions">
        <button class="btn-view-all dpad-focusable" data-cat="${def.key}" title="فتح صفحة القسم كاملة">
          <span>عرض الكل</span>
          <span>❯</span>
        </button>
        <button class="slider-nav-btn dpad-focusable btn-next" title="التالي" aria-label="Next">❯</button>
        <button class="slider-nav-btn dpad-focusable btn-prev" title="السابق" aria-label="Previous">❮</button>
      </div>
    `;

    // Horizontal Scroll Track
    const track = document.createElement('div');
    track.className = 'carousel-track category-carousel-track';

    items.forEach((item, idx) => {
      if (def.key === 'قنوات مباشرة') {
        track.appendChild(createChannelCard(item, idx));
      } else {
        track.appendChild(createMediaCard(item, idx));
      }
    });

    // Wire "عرض الكل" button
    const btnViewAll = header.querySelector('.btn-view-all');
    btnViewAll.addEventListener('click', () => {
      showCategoryView(def.key);
    });

    // Wire arrow buttons
    const btnNext = header.querySelector('.btn-next');
    const btnPrev = header.querySelector('.btn-prev');
    btnNext.addEventListener('click', () => {
      track.scrollBy({ left: -360, behavior: 'smooth' });
    });
    btnPrev.addEventListener('click', () => {
      track.scrollBy({ left: 360, behavior: 'smooth' });
    });

    section.appendChild(header);
    section.appendChild(track);
    container.appendChild(section);
  });

  if (window.RemoteControl) setTimeout(() => RemoteControl.refresh(), 100);
}

// Show Dedicated Category Internal Page
function showCategoryView(categoryName) {
  currentCategoryViewName = categoryName;

  const homeView = document.getElementById('home-page-view');
  const catView = document.getElementById('category-page-view');
  if (!catView) return;

  if (homeView) {
    homeView.classList.add('is-hidden');
    homeView.style.display = 'none';
  }
  catView.classList.remove('is-hidden');
  catView.style.display = 'block';

  // Scroll content to top
  const wrapper = document.querySelector('.content-wrapper');
  if (wrapper) wrapper.scrollTop = 0;
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Match definition or create dynamic category metadata
  let def = CATEGORY_DEFINITIONS.find(d => d.key === categoryName || d.title === categoryName);
  if (!def) {
    def = {
      key: categoryName,
      title: categoryName,
      icon: '🎬',
      desc: `تصفح كافة أعمال ${categoryName} المتوفرة مع سيرفرات مشاهدة سريعة`
    };
  }

  const titleEl = document.getElementById('category-page-title');
  if (titleEl) titleEl.textContent = def.title;

  const headingEl = document.getElementById('category-page-heading');
  if (headingEl) headingEl.textContent = `${def.icon} ${def.title}`;

  const descEl = document.getElementById('category-page-desc');
  if (descEl) descEl.textContent = def.desc;

  // Retrieve all category items
  currentCategoryItems = getItemsForCategory(def.key);
  renderCategoryGrid(currentCategoryItems, def.key);

  // Setup search inside category
  const filterInput = document.getElementById('category-filter-input');
  if (filterInput) {
    filterInput.value = '';
    filterInput.oninput = (e) => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) {
        renderCategoryGrid(currentCategoryItems, def.key);
      } else {
        const filtered = currentCategoryItems.filter(item => {
          const t1 = (item.title || item.name || '').toLowerCase();
          const t2 = (item.arabic_title || '').toLowerCase();
          const t3 = (item.synopsis || item.desc || '').toLowerCase();
          return t1.includes(q) || t2.includes(q) || t3.includes(q);
        });
        renderCategoryGrid(filtered, def.key);
      }
    };
  }

  // Setup sort pills
  const sortPills = document.querySelectorAll('.category-sort-group .sort-pill');
  sortPills.forEach(pill => {
    pill.onclick = () => {
      sortPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const sortType = pill.getAttribute('data-sort');
      sortAndRenderCategoryItems(sortType, def.key);
    };
  });

  // Sync sidebar active state
  const subItems = document.querySelectorAll('.sub-item');
  subItems.forEach(s => {
    if (s.textContent.trim() === categoryName || s.textContent.trim() === def.title) {
      s.classList.add('active');
    } else {
      s.classList.remove('active');
    }
  });

  const navItems = document.querySelectorAll('.nav-item[data-nav]');
  navItems.forEach(n => {
    if (def.key === 'قنوات مباشرة' && n.getAttribute('data-nav') === 'channels') {
      n.classList.add('active');
    } else {
      n.classList.remove('active');
    }
  });

  if (window.RemoteControl) setTimeout(() => RemoteControl.refresh(), 100);
}

// Render the category responsive grid
function renderCategoryGrid(items, categoryKey) {
  const grid = document.getElementById('category-grid');
  const countBadge = document.getElementById('category-page-count');
  if (countBadge) countBadge.textContent = `${items.length} عملاً`;
  if (!grid) return;

  grid.innerHTML = '';
  if (items.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #94a3b8;">
        <div style="font-size: 38px; margin-bottom: 12px;">🔍</div>
        <div style="font-size: 18px; color: #fff; font-weight: 700;">لم يتم العثور على أعمال مطابقة</div>
        <div style="font-size: 13px; margin-top: 6px;">جرب تغيير كلمة البحث أو تصفح قسم آخر</div>
      </div>
    `;
    return;
  }

  items.forEach((item, idx) => {
    const isLiveChannel = categoryKey === 'قنوات مباشرة' ||
                          item.is_live === true ||
                          (item.category && item.streamUrl && (item.category.includes('قنوات') || item.category === 'الأخبار' || item.category === 'الوثائقيات' || item.category === 'إسلامية ودينية'));
    if (isLiveChannel) {
      grid.appendChild(createChannelCard(item, idx));
    } else {
      grid.appendChild(createMediaCard(item, idx));
    }
  });

  if (window.RemoteControl) setTimeout(() => RemoteControl.refresh(), 100);
}

// Sort items inside category
function sortAndRenderCategoryItems(sortType, categoryKey) {
  let sorted = [...currentCategoryItems];
  if (sortType === 'rating') {
    sorted.sort((a, b) => {
      const rA = parseFloat(a.rating ? String(a.rating).replace(/[^0-9.]/g, '') : 0);
      const rB = parseFloat(b.rating ? String(b.rating).replace(/[^0-9.]/g, '') : 0);
      return rB - rA;
    });
  } else if (sortType === 'title') {
    sorted.sort((a, b) => {
      const tA = (a.arabic_title || a.title || a.name || '').toLowerCase();
      const tB = (b.arabic_title || b.title || b.name || '').toLowerCase();
      return tA.localeCompare(tB, 'ar');
    });
  } else {
    // Latest by year
    sorted.sort((a, b) => (parseInt(b.year || 0) - parseInt(a.year || 0)));
  }
  renderCategoryGrid(sorted, categoryKey);
}

// Return to Home View
function showHomeView() {
  currentCategoryViewName = null;
  const homeView = document.getElementById('home-page-view');
  const catView = document.getElementById('category-page-view');
  if (catView) {
    catView.classList.add('is-hidden');
    catView.style.display = 'none';
  }
  if (homeView) {
    homeView.classList.remove('is-hidden');
    homeView.style.display = 'block';
  }

  // Scroll to top
  const wrapper = document.querySelector('.content-wrapper');
  if (wrapper) wrapper.scrollTop = 0;
  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Sync nav items
  const navItems = document.querySelectorAll('.nav-item[data-nav]');
  navItems.forEach(n => {
    if (n.getAttribute('data-nav') === 'home') n.classList.add('active');
    else n.classList.remove('active');
  });

  const subItems = document.querySelectorAll('.sub-item');
  subItems.forEach(s => s.classList.remove('active'));

  if (window.RemoteControl) setTimeout(() => RemoteControl.refresh(), 100);
}

// Sidebar & App Navigation
function setupSidebarNavigation() {
  const sidebar = document.getElementById('app-sidebar');
  const toggleBtn = document.getElementById('menu-toggle');
  const drawerOverlay = document.getElementById('mobile-overlay');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      if (window.innerWidth <= 768) {
        sidebar.classList.toggle('mobile-open');
        if (drawerOverlay) drawerOverlay.classList.toggle('active');
      } else {
        sidebar.classList.toggle('collapsed');
      }
    });
  }

  if (drawerOverlay && sidebar) {
    drawerOverlay.addEventListener('click', () => {
      sidebar.classList.remove('mobile-open');
      drawerOverlay.classList.remove('active');
    });
  }

  // Mobile Bottom Navigation Bar Actions
  const mobileNavBtns = document.querySelectorAll('.mobile-nav-btn[data-target]');
  mobileNavBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      mobileNavBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const target = btn.getAttribute('data-target');
      if (target === 'home') {
        showHomeView();
      } else {
        showCategoryView(target);
      }
      if (sidebar) sidebar.classList.remove('mobile-open');
      if (drawerOverlay) drawerOverlay.classList.remove('active');
    });
  });

  const mobileNavSearch = document.getElementById('mobile-nav-search-btn');
  if (mobileNavSearch) {
    mobileNavSearch.addEventListener('click', () => {
      const searchInput = document.getElementById('header-search-input');
      if (searchInput) {
        searchInput.focus();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  }

  // Top-Level Nav Items (الرئيسية / القنوات)
  const navItems = document.querySelectorAll('.nav-item[data-nav]');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const navTarget = item.getAttribute('data-nav');
      if (navTarget === 'home') {
        showHomeView();
      } else if (navTarget === 'channels') {
        showCategoryView('قنوات مباشرة');
      }
    });
  });

  // Home Brand link and Breadcrumb home link
  const brandHomeLink = document.getElementById('brand-home-link');
  if (brandHomeLink) brandHomeLink.addEventListener('click', (e) => { e.preventDefault(); showHomeView(); });

  const crumbHomeLink = document.getElementById('crumb-home-link');
  if (crumbHomeLink) crumbHomeLink.addEventListener('click', () => showHomeView());

  const categoryBackBtn = document.getElementById('category-back-btn');
  if (categoryBackBtn) categoryBackBtn.addEventListener('click', () => showHomeView());

  // Hero "إضافة للمفضلة" button
  const heroFavBtn = document.querySelector('.hero-actions .btn-secondary');
  if (heroFavBtn) {
    heroFavBtn.addEventListener('click', () => {
      let featured = null;
      if (window.MediaCatalog) {
        featured = MediaCatalog.getDetails('spider-man-brand-new-day-2026') || MediaCatalog.getDetails('gladiator-ii-2024');
        if (!featured) featured = MediaCatalog.getAll()[0];
      }
      if (featured) {
        let favs = [];
        try { favs = JSON.parse(localStorage.getItem('atube_favorites') || '[]'); } catch(e) {}
        const exists = favs.some(f => f.id === featured.id);
        if (!exists) {
          favs.unshift({ id: featured.id, title: featured.title, arabic_title: featured.arabic_title, poster: featured.poster, rating: featured.rating, quality: featured.quality });
          localStorage.setItem('atube_favorites', JSON.stringify(favs));
          heroFavBtn.style.background = 'rgba(255,42,68,0.3)';
          heroFavBtn.style.borderColor = '#ff2a44';
          heroFavBtn.querySelector('span:last-child').textContent = 'تم الإضافة للمفضلة ✓';
        } else {
          heroFavBtn.querySelector('span:last-child').textContent = 'موجود بالفعل في المفضلة ♥';
        }
      }
    });
  }

  if (drawerOverlay) {
    drawerOverlay.addEventListener('click', () => {
      sidebar.classList.remove('mobile-open');
      drawerOverlay.classList.remove('active');
    });
  }

  // Nav Groups collapsible
  const groups = document.querySelectorAll('.nav-group');
  groups.forEach(grp => {
    const header = grp.querySelector('.nav-group-header');
    if (header) {
      header.addEventListener('click', () => {
        grp.classList.toggle('expanded');
        setTimeout(() => RemoteControl.refresh(), 200);
      });
    }
  });

  // Hero Watch Button (Opens first available featured title in MovieDetails)
  const heroWatchBtn = document.getElementById('hero-watch-btn');
  if (heroWatchBtn) {
    heroWatchBtn.addEventListener('click', () => {
      if (window.MediaCatalog) {
        let featured = MediaCatalog.getDetails('spider-man-brand-new-day-2026') || MediaCatalog.getDetails('gladiator-ii-2024');
        if (!featured) {
          const all = MediaCatalog.getAll();
          featured = all.find(i => i.category === 'foreign') || all[0];
        }
        if (featured && window.MovieDetails) MovieDetails.open(featured);
      }
    });
  }

  // Sidebar Sub-items click (e.g. أفلام أجنبي, أفلام عربي, مسلسلات تركي) -> Open dedicated category view!
  const subItems = document.querySelectorAll('.sub-item');
  subItems.forEach(sub => {
    sub.addEventListener('click', () => {
      const text = sub.textContent.trim();
      showCategoryView(text);
      if (window.innerWidth <= 768 && sidebar) {
        sidebar.classList.remove('mobile-open');
        if (drawerOverlay) drawerOverlay.classList.remove('active');
      }
    });
  });

  // Quick Filter Tabs in Home Page
  const filterTabs = document.querySelectorAll('.filter-tab');
  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const cat = tab.getAttribute('data-cat');
      if (cat === 'all') {
        showHomeView();
      } else {
        showCategoryView(cat);
      }
    });
  });

  // Hero Dots
  const dots = document.querySelectorAll('.hero-dots .dot');
  dots.forEach((dot, idx) => {
    dot.addEventListener('click', () => {
      dots.forEach(d => d.classList.remove('active'));
      dot.classList.add('active');
    });
  });
}

// Setup filter tabs
function setupFilterTabs() {
  const tabs = document.querySelectorAll('.filter-tab');
  const anyActive = Array.from(tabs).some(t => t.classList.contains('active'));
  if (!anyActive && tabs.length > 0) {
    tabs[0].classList.add('active');
  }
}

// Header Actions (Search, Languages, Voice, Cast, Profile)
function setupHeaderActions() {
  const searchInput = document.getElementById('header-search-input');
  const searchDropdown = document.getElementById('search-history-dropdown');

  if (searchInput) {
    const debouncedFilter = debounce((q) => {
      filterContent(q);
    }, 250);

    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.trim();
      if (!q) {
        renderSearchHistoryDropdown(searchDropdown, searchInput);
      } else if (searchDropdown) {
        searchDropdown.classList.add('is-hidden');
      }
      debouncedFilter(q);
    });

    searchInput.addEventListener('focus', () => {
      if (!searchInput.value.trim()) {
        renderSearchHistoryDropdown(searchDropdown, searchInput);
      }
    });

    document.addEventListener('click', (e) => {
      if (searchDropdown && !searchDropdown.contains(e.target) && e.target !== searchInput) {
        searchDropdown.classList.add('is-hidden');
      }
    });
  }

  // Voice Search
  const micBtn = document.getElementById('voice-search-btn');
  if (micBtn && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRec();
    recognition.lang = 'ar-SA';
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (searchInput) {
        searchInput.value = transcript;
        filterContent(transcript.toLowerCase().trim());
      }
    };
    micBtn.addEventListener('click', () => {
      try {
        recognition.start();
        micBtn.style.color = '#ff2a44';
      } catch (err) {
        console.log(err);
      }
    });
    recognition.onend = () => {
      micBtn.style.color = '';
    };
  }

  // Language Switcher (AR, EN, FR)
  setupLanguageSwitcher();

  // Cast Modal
  setupCastModal();

  // User Profile & Settings Modal
  setupProfileModal();
}

function setupLanguageSwitcher() {
  const langPills = document.querySelectorAll('.lang-pill');
  langPills.forEach(pill => {
    pill.addEventListener('click', () => {
      langPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const lang = pill.getAttribute('data-lang') || pill.textContent.trim().toLowerCase();
      applyLanguage(lang);
    });
  });
}

function applyLanguage(lang) {
  const isArabic = (lang === 'ar');
  document.documentElement.dir = isArabic ? 'rtl' : 'ltr';
  document.documentElement.lang = lang;

  const searchInput = document.getElementById('header-search-input');
  if (searchInput) {
    if (lang === 'en') searchInput.placeholder = 'Search channels, movies, series, shows...';
    else if (lang === 'fr') searchInput.placeholder = 'Rechercher chaînes, films, séries...';
    else searchInput.placeholder = 'البحث في القنوات والأفلام والبرامج...';
  }
}

// Cast Screen Modal setup
function setupCastModal() {
  const modal = document.getElementById('cast-modal');
  const openBtn = document.getElementById('cast-screen-btn');
  const closeBtn = document.getElementById('close-cast-modal-btn');
  const nativeBtn = document.getElementById('start-native-cast-btn');
  const deviceCards = document.querySelectorAll('.cast-device-card');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('active');
    });
  }

  const closeModal = () => {
    if (modal) modal.classList.remove('active');
  };

  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  deviceCards.forEach(card => {
    card.addEventListener('click', () => {
      const devName = card.getAttribute('data-device') || 'Smart TV';
      alert(`جاري بدء بث الفيديو مباشرة إلى: ${devName} عبر بروتوكول A Tube Cast`);
      closeModal();
    });
  });

  if (nativeBtn) {
    nativeBtn.addEventListener('click', () => {
      const vid = document.getElementById('main-video');
      if (vid && vid.remote && typeof vid.remote.prompt === 'function') {
        vid.remote.prompt().catch(err => {
          alert('يرجى اختيار جهاز البث من شريط المتصفح أو تطبيق Google Home');
        });
      } else {
        alert('البحث عن أجهزة البث عبر الشبكة المحلية... جاري المزامنة مع الشاشة الذكية.');
      }
    });
  }
}

// User Profile & Settings Modal setup
function setupProfileModal() {
  const modal = document.getElementById('user-profile-modal');
  const openBtn = document.getElementById('user-profile-btn');
  const closeBtn = document.getElementById('close-profile-modal-btn');
  const tabBtns = document.querySelectorAll('.profile-tab-btn');
  const saveBtn = document.getElementById('save-settings-btn');
  const clearBtn = document.getElementById('clear-cache-btn');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('active');
      renderProfileFavorites();
      renderProfileHistory();
    });
  }

  const closeModal = () => {
    if (modal) modal.classList.remove('active');
  };

  if (closeBtn) closeBtn.addEventListener('click', closeModal);

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const targetTab = btn.getAttribute('data-tab');
      document.querySelectorAll('.profile-tab-content').forEach(c => c.classList.add('is-hidden'));
      const activeContent = document.getElementById(`profile-tab-${targetTab}`);
      if (activeContent) activeContent.classList.remove('is-hidden');

      if (targetTab === 'favorites') renderProfileFavorites();
      if (targetTab === 'history') renderProfileHistory();
    });
  });

  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const q = document.getElementById('setting-default-quality')?.value || '1080p';
      const eng = document.getElementById('setting-default-engine')?.value || 'native';
      localStorage.setItem('atube_quality', q);
      localStorage.setItem('atube_engine', eng);
      alert('تم حفظ إعدادات الجودة والمشغل بنجاح!');
      closeModal();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (confirm('هل أنت متأكد من مسح الذاكرة المؤقتة وسجل المشاهدة؟')) {
        localStorage.removeItem('atube_history');
        localStorage.removeItem('atube_favorites');
        alert('تم مسح الذاكرة المؤقتة بنجاح!');
        location.reload();
      }
    });
  }
}

function renderProfileFavorites() {
  const container = document.getElementById('favorites-list-container');
  if (!container) return;
  let favs = [];
  try {
    favs = JSON.parse(localStorage.getItem('atube_favorites') || '[]');
  } catch (e) {}

  if (favs.length === 0) {
    container.innerHTML = `
      <div style="text-align:center;padding:30px;color:#888;">
        <div style="font-size:32px;margin-bottom:8px;">★</div>
        <div>لا توجد عناصر محفوظة في المفضلة بعد.</div>
        <div style="font-size:12px;margin-top:4px;color:#666;">يمكنك إضافة أي فيلم أو مسلسل أو قناة بنقرة زر "إضافة للمفضلة".</div>
      </div>
    `;
    return;
  }

  container.innerHTML = '';
  favs.forEach(item => {
    const row = document.createElement('div');
    row.style.cssText = `
      display: flex; align-items: center; gap: 12px; padding: 8px 12px;
      background: rgba(255,255,255,0.05); border-radius: 8px; cursor: pointer;
    `;
    row.innerHTML = `
      <img src="${item.poster || item.poster_svg_fallback || 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 40 55\' fill=\'%2308101a\'/%3E'}" style="width:40px;height:55px;object-fit:cover;border-radius:4px;">
      <div style="flex:1;">
        <div style="font-weight:bold;color:#fff;">${item.arabic_title || item.title}</div>
        <div style="font-size:12px;color:#00e5ff;">${item.quality || '1080p'} • ${item.rating || '★ 8.5'}</div>
      </div>
      <button class="btn-primary" style="padding:4px 12px;font-size:12px;">تشغيل</button>
    `;
    row.addEventListener('click', () => {
      document.getElementById('user-profile-modal')?.classList.remove('active');
      const ctrl = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
      if (ctrl && typeof ctrl.open === 'function') {
        ctrl.open(item);
      }
    });
    container.appendChild(row);
  });
}

function renderProfileHistory() {
  const container = document.getElementById('history-list-container');
  if (!container) return;
  let history = [];
  try {
    history = JSON.parse(localStorage.getItem('atube_history') || '[]');
  } catch (e) {}

  if (history.length === 0) {
    container.innerHTML = `
      <div style="text-align:center;padding:30px;color:#888;">
        <div style="font-size:32px;margin-bottom:8px;">🕒</div>
        <div>سجل المشاهدة فارغ حالياً.</div>
        <div style="font-size:12px;margin-top:4px;color:#666;">سيتم حفظ الأفلام والقنوات التي تشاهدها هنا تلقائياً لمتابعتها لاحقاً.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = '';
  history.forEach(item => {
    const row = document.createElement('div');
    row.style.cssText = `
      display: flex; align-items: center; gap: 12px; padding: 8px 12px;
      background: rgba(255,255,255,0.05); border-radius: 8px; cursor: pointer;
    `;
    row.innerHTML = `
      <div style="font-size:20px;">🎬</div>
      <div style="flex:1;">
        <div style="font-weight:bold;color:#fff;">${item.title || item.name}</div>
        <div style="font-size:12px;color:#aaa;">${item.category || 'بث مباشر'} • ${item.time || 'مؤخراً'}</div>
      </div>
      <button class="btn-primary" style="padding:4px 12px;font-size:12px;">متابعة</button>
    `;
    row.addEventListener('click', () => {
      document.getElementById('user-profile-modal')?.classList.remove('active');
      const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
      if (player && typeof player.playMedia === 'function') {
        player.playMedia(item);
      }
    });
    container.appendChild(row);
  });
}

function filterContent(query) {
  if (!query || query.trim().length < 2) {
    if (currentCategoryViewName) {
      showCategoryView(currentCategoryViewName);
    } else {
      showHomeView();
    }
    return;
  }

  const rawQuery = query.trim();
  saveSearchQuery(rawQuery);

  const normQ = normalizeArabicSearch(rawQuery);
  const qTerms = normQ.split(/\s+/).filter(Boolean);
  let matched = [];

  // Search across MediaCatalog with Arabic fuzzy normalization
  if (window.MediaCatalog) {
    const allItems = MediaCatalog.getAll();
    matched = allItems.filter(m => {
      const t1 = normalizeArabicSearch(m.title);
      const t2 = normalizeArabicSearch(m.arabic_title);
      const t3 = normalizeArabicSearch(m.synopsis);
      const t4 = normalizeArabicSearch(m.category);
      const t5 = normalizeArabicSearch(m.genre);
      const combined = `${t1} ${t2} ${t3} ${t4} ${t5}`;
      return qTerms.every(term => combined.includes(term));
    });
  }

  // Also search live channels
  const allChannels = [
    ...(typeof IPTVEngine !== 'undefined' && IPTVEngine.getDefaultChannels ? IPTVEngine.getDefaultChannels() : []),
    ...(typeof IPTVEngine !== 'undefined' && IPTVEngine.getCustomChannels ? IPTVEngine.getCustomChannels() : [])
  ];
  const matchedChannels = allChannels.filter(c => {
    const c1 = normalizeArabicSearch(c.name);
    const c2 = normalizeArabicSearch(c.desc);
    const combined = `${c1} ${c2}`;
    return qTerms.every(term => combined.includes(term));
  });

  const totalResults = [...matched, ...matchedChannels];

  // Open dedicated view for search results
  const homeView = document.getElementById('home-page-view');
  const catView = document.getElementById('category-page-view');
  if (homeView) {
    homeView.classList.add('is-hidden');
    homeView.style.display = 'none';
  }
  if (catView) {
    catView.classList.remove('is-hidden');
    catView.style.display = 'block';
  }

  const titleEl = document.getElementById('category-page-title');
  if (titleEl) titleEl.textContent = `نتائج البحث: "${rawQuery}"`;
  const headingEl = document.getElementById('category-page-heading');
  if (headingEl) headingEl.textContent = `نتائج البحث عن: "${rawQuery}"`;
  const descEl = document.getElementById('category-page-desc');
  if (descEl) descEl.textContent = `تم العثور على ${totalResults.length} نتيجة مطابقة في جميع الأقسام والقنوات`;

  currentCategoryItems = totalResults;
  renderCategoryGrid(totalResults, 'search');
}

// IPTV Subscription modal setup
function setupIPTVModal() {
  const modal = document.getElementById('iptv-modal');
  const openBtn = document.getElementById('open-iptv-modal-btn');
  const closeBtn = document.getElementById('close-iptv-modal-btn');
  const cancelBtn = document.getElementById('cancel-iptv-btn');
  const saveBtn = document.getElementById('save-iptv-btn');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('active');
    });
  }

  const closeModal = () => {
    if (modal) modal.classList.remove('active');
  };

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const m3uUrl = document.getElementById('iptv-m3u-url')?.value.trim();
      const host = document.getElementById('xtream-host')?.value.trim();
      const user = document.getElementById('xtream-user')?.value.trim();
      const pass = document.getElementById('xtream-pass')?.value.trim();

      if (host && user && pass) {
        try {
          saveBtn.textContent = 'جاري الاتصال بالسيرفر...';
          await IPTVEngine.loadXtream(host, user, pass);
          alert('تم تحميل اشتراك الـ Xtream بنجاح!');
          closeModal();
        } catch (e) {
          alert('خطأ في الاتصال بسيرفر Xtream، يرجى مراجعة البيانات.');
        } finally {
          saveBtn.textContent = 'حفظ وتشغيل القنوات';
        }
      } else if (m3uUrl) {
        try {
          saveBtn.textContent = 'جاري قراءة الرابط...';
          const res = await fetch(m3uUrl);
          const txt = await res.text();
          const parsed = IPTVEngine.parseM3U(txt);
          IPTVEngine.addCustomChannels(parsed);
          alert(`تم استيراد ${parsed.length} قناة بنجاح!`);
          closeModal();
        } catch (e) {
          alert('تعذر تحميل رابط M3U المباشر. تأكد من أن الرابط يدعم CORS أو قم بتجربته داخل مشغل الأندرويد.');
        } finally {
          saveBtn.textContent = 'حفظ وتشغيل القنوات';
        }
      } else {
        alert('يرجى إدخال رابط M3U أو بيانات سيرفر Xtream.');
      }
    });
  }
}
