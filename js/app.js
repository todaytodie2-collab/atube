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
  },
  {
    key: 'أفلام آسيوي',
    title: 'أفلام آسيوي وكوري',
    icon: '⛩️',
    desc: 'روائع السينما الآسيوية والكورية المترجمة بجودة Ultra HD'
  },
  {
    key: 'مسلسلات آسيوي',
    title: 'مسلسلات آسيوي',
    icon: '🇰🇷',
    desc: 'أروع الدراما الكورية والآسيوية المترجمة'
  },
  {
    key: 'مسلسلات وثائقية',
    title: 'مسلسلات وثائقية',
    icon: '📽️',
    desc: 'أقوى السلاسل الوثائقية التاريخية والعلمية'
  },
  {
    key: 'كارتون للأطفال',
    title: 'كارتون كيدز للأطفال',
    icon: '🎈',
    desc: 'أشهر برامج وأفلام الكارتون وأغاني الأطفال الآمنة وبدون إعلانات'
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

  // 0b. Register Service Worker for Offline Resilience & PWA Support
  if ('serviceWorker' in navigator && window.location.protocol !== 'file:') {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }

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

  // 4. Render Hero Billboard Banner, Quick Feeds & Category Carousels
  renderHeroBillboard();
  renderContinueWatching();
  renderTrendingTop10();
  renderHomeCarousels();

  // 4b. Background-preload API feeds for every home category, then re-render
  //     so the carousels reflect live /api/media/feed data (one card per series).
  preloadHomeFeeds().then(() => {
    renderHomeCarousels();
    renderContinueWatching();
    renderTrendingTop10();
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

  // 8. Next-Gen Features: Moods, Quiz, Watch Together, Themes, Gamepad, Screensaver
  setupMoodFilter();
  setupCinemaQuiz();
  setupWatchTogether();
  setupThemesCustomizer();
  setupShortcutsHUD();
  setupAerialScreensaver();
  setupGamepadSupport();
  setupHapticFeedback();
  setupKidsSafeMode();

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

  const isWatched = (m.id && localStorage.getItem('atube_watched_' + m.id) === 'true');
  const watchedBadge = isWatched ? `<span class="watched-card-badge">تمت المشاهدة ✓</span>` : '';

  card.innerHTML = `
    <div class="program-thumb">
      <img src="${fallbackSvg}"
           data-src="${posterSrc}"
           alt="${cleanAlt}"
           decoding="async"
           class="lazy-poster-img">
      <span class="program-card-badge">${cleanRating}</span>
      ${watchedBadge}
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
  if (window.location.protocol === 'file:') return; // Skip remote API calls on file:// protocol
  const catalog = window.MediaCatalog || (typeof MediaCatalog !== 'undefined' ? MediaCatalog : null);
  if (!catalog || typeof catalog.fetchFeed !== 'function') return;
  const keys = CATEGORY_DEFINITIONS.map(d => d.key).filter(k => k !== 'قنوات مباشرة');
  try {
    await Promise.all(keys.map(k => catalog.fetchFeed(k, 1, 40).catch(() => null)));
  } catch (_) {}
}


let heroSliderTimer = null;
let heroCurrentSlideIndex = 0;
let heroFeaturedItems = [];

// Render Hero Billboard Banner (Cinematic Dynamic Auto-Slider & Ambient Glow)
function renderHeroBillboard() {
  const bannerEl = document.getElementById('hero-banner');
  const contentEl = document.getElementById('hero-content');
  const bgImg = document.getElementById('hero-bg-img');
  const dotsContainer = document.getElementById('hero-slider-dots');
  if (!bannerEl || !contentEl) return;

  const allItems = (window.MediaCatalog && typeof MediaCatalog.getAll === 'function')
    ? MediaCatalog.getAll()
    : [];

  if (allItems.length === 0) {
    bannerEl.style.display = 'none';
    contentEl.innerHTML = '';
    return;
  }

  // Pick top 6 rich featured items with backdrops/posters
  heroFeaturedItems = allItems.filter(item => item.poster && !item.poster.includes('gladiator_hero')).slice(0, 6);
  if (heroFeaturedItems.length === 0) heroFeaturedItems = allItems.slice(0, 6);

  bannerEl.style.display = 'flex';

  function displaySlide(idx) {
    if (!heroFeaturedItems || heroFeaturedItems.length === 0) return;
    heroCurrentSlideIndex = (idx + heroFeaturedItems.length) % heroFeaturedItems.length;
    const featured = heroFeaturedItems[heroCurrentSlideIndex];

    // Smooth transition & guaranteed image display
    if (bgImg) {
      bgImg.classList.remove('is-hidden');
      bgImg.classList.add('fade-out');
      bgImg.onerror = () => {
        bgImg.src = 'https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=1000&q=80';
      };
      setTimeout(() => {
        bgImg.src = featured.backdrop || featured.poster;
        bgImg.classList.remove('fade-out');
      }, 200);
      bgImg.style.display = 'block';
    }

    contentEl.classList.add('fade-anim');
    setTimeout(() => {
      // Dynamic promo badge
      const promoBadges = [
        '🔥 الأكثر مشاهدة هذا الأسبوع',
        '⚡ حصرياً Ultra HD 4K',
        '✨ العرض الأول والأحدث',
        '🌟 يوصى به بشدة لك',
        '🎬 مشاهدة فائقة السرعة'
      ];
      const promoText = promoBadges[heroCurrentSlideIndex % promoBadges.length];

      // Dynamic ambient glow
      const glowClasses = ['glow-cyan', 'glow-gold', 'glow-red'];
      bannerEl.className = 'hero-banner ' + glowClasses[heroCurrentSlideIndex % glowClasses.length];

      contentEl.innerHTML = `
        <div class="hero-promo-badge">${promoText}</div>
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
            <span>تشغيل فوري ⚡</span>
          </button>
          <button class="btn-secondary dpad-focusable" id="hero-details-btn">
            <span>🎬</span>
            <span>تفاصيل والسيرفرات (${(featured.servers || []).length})</span>
          </button>
        </div>
      `;

      contentEl.classList.remove('fade-anim');

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
    }, 200);

    // Update Dots UI
    if (dotsContainer) {
      dotsContainer.innerHTML = '';
      heroFeaturedItems.forEach((_, dIdx) => {
        const dot = document.createElement('button');
        dot.className = `hero-dot dpad-focusable ${dIdx === heroCurrentSlideIndex ? 'active' : ''}`;
        dot.title = `الشريحة ${dIdx + 1}`;
        dot.onclick = () => {
          resetAutoSlider();
          displaySlide(dIdx);
        };
        dotsContainer.appendChild(dot);
      });
    }
  }

  function startAutoSlider() {
    if (heroSliderTimer) clearInterval(heroSliderTimer);
    heroSliderTimer = setInterval(() => {
      displaySlide(heroCurrentSlideIndex + 1);
    }, 6500);
  }

  function resetAutoSlider() {
    if (heroSliderTimer) clearInterval(heroSliderTimer);
    startAutoSlider();
  }

  bannerEl.onmouseenter = () => { if (heroSliderTimer) clearInterval(heroSliderTimer); };
  bannerEl.onmouseleave = () => { startAutoSlider(); };

  displaySlide(0);
  startAutoSlider();
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

  const grid = document.getElementById('category-grid');
  const bouquetBar = document.getElementById('channels-bouquet-filter-bar');
  const isChannels = (def.key === 'قنوات مباشرة' || def.key === 'channels' || def.key === 'قنوات البث المباشر');

  if (grid) {
    if (isChannels) {
      grid.classList.add('is-channels-view');
    } else {
      grid.classList.remove('is-channels-view');
    }
  }

  const pinnedBar = document.getElementById('channels-pinned-bar');
  if (pinnedBar) {
    if (isChannels) {
      renderPinnedChannelsBar();
    } else {
      pinnedBar.classList.add('is-hidden');
    }
  }

  if (bouquetBar) {
    if (isChannels) {
      bouquetBar.classList.remove('is-hidden');
      setupChannelsBouquetFilterBar();
    } else {
      bouquetBar.classList.add('is-hidden');
    }
  }

  renderCategoryGrid(currentCategoryItems, def.key);

  // Render per-section animated mini-hero banner
  const miniHeroEl = document.getElementById('category-mini-hero');
  if (miniHeroEl) {
    if (currentCategoryItems.length > 0 && !isChannels) {
      const topItem = currentCategoryItems[0];
      miniHeroEl.classList.remove('is-hidden');
      miniHeroEl.innerHTML = `
        <img src="${topItem.backdrop || topItem.poster}" class="category-mini-hero-bg" alt="${safeHtml(topItem.title)}">
        <div class="category-mini-hero-overlay"></div>
        <div class="category-mini-hero-content">
          <div class="hero-badge">★ ${safeHtml(topItem.rating || '★ 8.5 IMDb')} • ${safeHtml(topItem.quality || '1080p FHD')}</div>
          <h2 style="font-size:22px;font-weight:900;color:#fff;text-shadow:0 2px 8px rgba(0,0,0,0.8);">${safeHtml(topItem.arabic_title || topItem.title)}</h2>
          <button class="btn-primary dpad-focusable" style="padding:6px 16px;font-size:12px;width:fit-content;margin-top:4px;" id="mini-hero-play">
            ▶ مشاهدة فورية
          </button>
        </div>
      `;
      const playBtn = miniHeroEl.querySelector('#mini-hero-play');
      if (playBtn) {
        playBtn.onclick = () => {
          const details = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
          if (details && typeof details.open === 'function') details.open(topItem);
        };
      }
    } else {
      miniHeroEl.classList.add('is-hidden');
    }
  }

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

// Render Quick Pinned Favorite Channels Bar
function renderPinnedChannelsBar() {
  const pinnedBar = document.getElementById('channels-pinned-bar');
  const track = document.getElementById('channels-pinned-track');
  if (!pinnedBar || !track) return;

  const pinnedChannels = (window.IPTVEngine && typeof window.IPTVEngine.getPinnedChannels === 'function')
    ? window.IPTVEngine.getPinnedChannels()
    : [];

  if (!pinnedChannels || pinnedChannels.length === 0) {
    pinnedBar.classList.add('is-hidden');
    return;
  }

  pinnedBar.classList.remove('is-hidden');
  track.innerHTML = '';
  pinnedChannels.slice(0, 6).forEach((ch, idx) => {
    const card = (window.IPTVEngine && typeof window.IPTVEngine.createChannelCardElement === 'function')
      ? window.IPTVEngine.createChannelCardElement(ch, idx)
      : createChannelCard(ch, idx);
    track.appendChild(card);
  });

  if (window.RemoteControl && typeof RemoteControl.refresh === 'function') {
    setTimeout(() => RemoteControl.refresh(), 50);
  }
}
window.renderPinnedChannelsBar = renderPinnedChannelsBar;

// Setup Bouquet Filter Bar for Live TV Channels
function setupChannelsBouquetFilterBar() {
  const bouquetBar = document.getElementById('channels-bouquet-filter-bar');
  if (!bouquetBar || bouquetBar.dataset.initialized === 'true') return;
  bouquetBar.dataset.initialized = 'true';

  const pills = bouquetBar.querySelectorAll('.bouquet-pill');
  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');

      const bouquet = pill.getAttribute('data-bouquet');
      filterChannelsByBouquet(bouquet);
    });
  });

  // Wire satellite freq modal close button once
  const closeFreqBtn = document.getElementById('close-freq-modal-btn');
  const freqModal = document.getElementById('satellite-freq-modal');
  if (closeFreqBtn && freqModal) {
    closeFreqBtn.addEventListener('click', () => {
      freqModal.classList.remove('active');
    });
    freqModal.addEventListener('click', (e) => {
      if (e.target === freqModal) freqModal.classList.remove('active');
    });
  }
}

// Filter channels by country / genre bouquet
function filterChannelsByBouquet(bouquet) {
  const allChannels = (window.IPTVEngine && typeof window.IPTVEngine.getDefaultChannels === 'function')
    ? window.IPTVEngine.getDefaultChannels()
    : currentCategoryItems;

  if (bouquet === 'all' || !bouquet) {
    renderCategoryGrid(allChannels, 'قنوات مباشرة');
    return;
  }

  const bouquetMap = {
    egypt: ['مصر', 'مصري', 'مصرية'],
    ksa: ['السعودية', 'سعودي', 'سعودية'],
    emarat: ['الإمارات', 'امارات', 'إماراتي', 'دبي', 'أبوظبي'],
    lebanon: ['لبنان', 'لبناني', 'لبنانية'],
    iraq: ['العراق', 'عراقي', 'عراقية'],
    sport: ['رياض', 'sport', 'كأس', 'دوري', 'أون تايم', 'on time'],
    drama: ['دراما', 'مسلسل', 'أفلام', 'سينما', 'روتانا سينما'],
    kids: ['أطفال', 'كرتون', 'كارتون', 'spacetoon', 'طيور الجنة', 'ماجد'],
    news: ['أخبار', 'news', 'إخبارية', 'الحدث', 'العربية', 'الجزيرة', 'فرانس', 'dw'],
    religion: ['دين', 'قرآن', 'إسلام', 'سنة', 'مجد', 'الناس', 'رسالة']
  };

  const keywords = bouquetMap[bouquet] || [];
  const filtered = allChannels.filter(ch => {
    const text = `${ch.name || ''} ${ch.category || ''} ${ch.desc || ''}`.toLowerCase();
    return keywords.some(kw => text.includes(kw.toLowerCase()));
  });

  renderCategoryGrid(filtered, 'قنوات مباشرة');
}

// Render the category responsive grid
function renderCategoryGrid(items, categoryKey) {
  const grid = document.getElementById('category-grid');
  const countBadge = document.getElementById('category-page-count');
  const isChannels = (categoryKey === 'قنوات مباشرة' || categoryKey === 'channels' || categoryKey === 'قنوات البث المباشر');

  if (countBadge) countBadge.textContent = `${items.length} ${isChannels ? 'قناة' : 'عملاً'}`;
  if (!grid) return;

  if (isChannels) {
    grid.classList.add('is-channels-view');
  } else {
    grid.classList.remove('is-channels-view');
  }

  grid.innerHTML = '';
  if (items.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #94a3b8;">
        <div style="font-size: 38px; margin-bottom: 12px;">🔍</div>
        <div style="font-size: 18px; color: #fff; font-weight: 700;">لم يتم العثور على ${isChannels ? 'قنوات' : 'أعمال'} مطابقة</div>
        <div style="font-size: 13px; margin-top: 6px;">جرب تغيير كلمة البحث أو اختيار باقة أخرى</div>
      </div>
    `;
    return;
  }

  items.forEach((item, idx) => {
    const isLiveChannel = isChannels ||
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

  // Nav Groups collapsible & smart navigation
  const groups = document.querySelectorAll('.nav-group');
  groups.forEach(grp => {
    const header = grp.querySelector('.nav-group-header');
    if (header) {
      header.addEventListener('click', (e) => {
        const isCollapsed = sidebar && sidebar.classList.contains('collapsed');
        if (isCollapsed) {
          // If sidebar is collapsed into mini-icons, clicking the icon navigates directly to the group's first category
          const firstSub = grp.querySelector('.sub-item');
          if (firstSub) {
            showCategoryView(firstSub.textContent.trim());
          }
          sidebar.classList.remove('collapsed');
        } else {
          grp.classList.toggle('expanded');
        }
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

  // Multi-View Quad Player Modal
  setupMultiViewModal();

  // QR Phone Remote Modal
  setupQRRemoteModal();

  // Random Surprise Cinema
  setupSurpriseMe();

  // Watch Together Modal
  setupWatchTogether();

  // Themes Customizer
  setupThemesCustomizer();

  // Shortcuts HUD
  setupShortcutsHUD();
}

const ATUBE_I18N = {
  ar: {
    home: 'الرئيسية',
    channels: 'القنوات',
    movies: 'الأفلام',
    series: 'المسلسلات',
    anime: 'الأنمي',
    shows_sports: 'البرامج والرياضة',
    search_placeholder: 'البحث في القنوات والأفلام والبرامج...',
    top10_title: '🔥 أفضل 10 أعمال اليوم في الوطن العربي (Top 10 Today)',
    more_like_this: '✨ أعمال قد تنال إعجابك (More Like This)',
    sub_items: {
      'أفلام عربي': 'أفلام عربي', 'أفلام أجنبي': 'أفلام أجنبي', 'أفلام تركي': 'أفلام تركي',
      'أفلام هندي': 'أفلام هندي', 'أفلام آسيوي': 'أفلام آسيوي', 'مسرحيات': 'مسرحيات',
      'أفلام وثائقية': 'أفلام وثائقية', 'مسلسلات عربي': 'مسلسلات عربي', 'مسلسلات تركي': 'مسلسلات تركي',
      'مسلسلات أجنبي': 'مسلسلات أجنبي', 'مسلسلات هندي': 'مسلسلات هندي', 'مسلسلات آسيوي': 'مسلسلات آسيوي',
      'مسلسلات وثائقية': 'مسلسلات وثائقية', 'أفلام أنمي': 'أفلام أنمي', 'مسلسلات أنمي': 'مسلسلات أنمي',
      'كارتون للأطفال': 'كارتون للأطفال', 'برامج وتلفزيون': 'برامج وتلفزيون', 'مصارعة حرة WWE': 'مصارعة حرة WWE', 'وثائقيات': 'وثائقيات'
    }
  },
  en: {
    home: 'Home',
    channels: 'Channels',
    movies: 'Movies',
    series: 'Series',
    anime: 'Anime',
    shows_sports: 'Shows & Sports',
    search_placeholder: 'Search channels, movies, series, shows...',
    top10_title: '🔥 Top 10 Trending Today',
    more_like_this: '✨ More Like This',
    sub_items: {
      'أفلام عربي': 'Arabic Movies', 'أفلام أجنبي': 'Foreign Movies', 'أفلام تركي': 'Turkish Movies',
      'أفلام هندي': 'Indian Movies', 'أفلام آسيوي': 'Asian Movies', 'مسرحيات': 'Plays',
      'أفلام وثائقية': 'Documentaries', 'مسلسلات عربي': 'Arabic Series', 'مسلسلات تركي': 'Turkish Series',
      'مسلسلات أجنبي': 'Foreign Series', 'مسلسلات هندي': 'Indian Series', 'مسلسلات آسيوي': 'Asian Series',
      'مسلسلات وثائقية': 'Docuseries', 'أفلام أنمي': 'Anime Movies', 'مسلسلات أنمي': 'Anime Series',
      'كارتون للأطفال': 'Kids Cartoons', 'برامج وتلفزيون': 'TV Shows', 'مصارعة حرة WWE': 'WWE Wrestling', 'وثائقيات': 'Documentaries'
    }
  },
  fr: {
    home: 'Accueil',
    channels: 'Chaînes',
    movies: 'Films',
    series: 'Séries',
    anime: 'Animés',
    shows_sports: 'Émissions & Sport',
    search_placeholder: 'Rechercher chaînes, films, séries...',
    top10_title: '🔥 Top 10 Aujourd\'hui',
    more_like_this: '✨ Recommandations',
    sub_items: {
      'أفلام عربي': 'Films Arabes', 'أفلام أجنبي': 'Films Étrangers', 'أفلام تركي': 'Films Turcs',
      'أفلام هندي': 'Films Indiens', 'أفلام آسيوي': 'Films Asiatiques', 'مسرحيات': 'Théâtre',
      'أفلام وثائقية': 'Documentaires', 'مسلسلات عربي': 'Séries Arabes', 'مسلسلات تركي': 'Séries Turques',
      'مسلسلات أجنبي': 'Séries Étrangères', 'مسلسلات هندي': 'Séries Indiennes', 'مسلسلات آسيوي': 'Séries Asiatiques',
      'مسلسلات وثائقية': 'Séries Documentaires', 'أفلام أنمي': 'Films d\'Animation', 'مسلسلات أنمي': 'Séries Animées',
      'كارتون للأطفال': 'Dessins Animés', 'برامج وتلفزيون': 'Émissions TV', 'مصارعة حرة WWE': 'Catch WWE', 'وثائقيات': 'Documentaires'
    }
  }
};

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

  // Restore saved language on boot
  const savedLang = localStorage.getItem('atube_lang') || 'ar';
  const targetPill = Array.from(langPills).find(p => p.getAttribute('data-lang') === savedLang);
  if (targetPill) {
    langPills.forEach(p => p.classList.remove('active'));
    targetPill.classList.add('active');
  }
  applyLanguage(savedLang);
}

function applyLanguage(lang) {
  const dict = ATUBE_I18N[lang] || ATUBE_I18N.ar;
  const isArabic = (lang === 'ar');
  document.documentElement.dir = isArabic ? 'rtl' : 'ltr';
  document.documentElement.lang = lang;
  try { localStorage.setItem('atube_lang', lang); } catch (_) {}

  // Search input
  const searchInput = document.getElementById('header-search-input');
  if (searchInput) {
    searchInput.placeholder = dict.search_placeholder;
  }

  // Nav labels
  const navHome = document.querySelector('.nav-item[data-nav="home"] .nav-label');
  if (navHome) navHome.textContent = dict.home;

  const navChannels = document.querySelector('.nav-item[data-nav="channels"] .nav-label');
  if (navChannels) navChannels.textContent = dict.channels;

  // Nav groups
  const groupLabels = document.querySelectorAll('.nav-group .nav-group-title .nav-label');
  if (groupLabels.length >= 4) {
    groupLabels[0].textContent = dict.movies;
    groupLabels[1].textContent = dict.series;
    groupLabels[2].textContent = dict.anime;
    groupLabels[3].textContent = dict.shows_sports;
  }

  // Sub items
  const subItems = document.querySelectorAll('.sub-item');
  subItems.forEach(sub => {
    const originalText = sub.getAttribute('data-original-text') || sub.textContent.trim();
    if (!sub.hasAttribute('data-original-text')) {
      sub.setAttribute('data-original-text', originalText);
    }
    if (dict.sub_items && dict.sub_items[originalText]) {
      sub.textContent = dict.sub_items[originalText];
    }
  });

  // Top 10 Title
  const top10Title = document.querySelector('.trending-top10-title');
  if (top10Title) {
    top10Title.textContent = dict.top10_title;
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

// ==========================================================================
// CONTINUE WATCHING & RESUME PLAYHEAD MANAGER
// ==========================================================================
function renderContinueWatching() {
  const section = document.getElementById('continue-watching-section');
  const track = document.getElementById('continue-watching-track');
  if (!section || !track) return;

  let history = [];
  try {
    history = JSON.parse(localStorage.getItem('atube_history') || '[]');
  } catch (_) {}

  const itemsWithProgress = [];
  history.forEach(item => {
    if (!item || !item.id) return;
    const pos = parseFloat(localStorage.getItem(`atube_pos_${item.id}`) || '0');
    const dur = parseFloat(localStorage.getItem(`atube_dur_${item.id}`) || '0');
    let pct = 30;
    if (dur > 0 && pos > 0) {
      pct = Math.min(95, Math.max(5, Math.round((pos / dur) * 100)));
    }
    itemsWithProgress.push({
      ...item,
      progressPct: pct,
      positionSec: pos
    });
  });

  if (itemsWithProgress.length === 0) {
    section.classList.add('is-hidden');
    return;
  }

  section.classList.remove('is-hidden');
  track.innerHTML = '';

  itemsWithProgress.slice(0, 12).forEach(item => {
    const card = document.createElement('div');
    card.className = 'continue-card dpad-focusable';
    card.tabIndex = 0;
    const title = escapeHtml(item.arabic_title || item.title || item.name || 'متابعة المشاهدة');
    const poster = item.poster || item.backdrop || 'data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 200 120\' fill=\'%2308101a\'/%3E';
    const subLabel = item.is_live ? 'بث مباشر' : `متبقي ${100 - item.progressPct}% • استئناف`;

    card.innerHTML = `
      <div class="continue-thumb-wrap">
        <img src="${poster}" alt="${title}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 200 120\' fill=\'%2308101a\'/%3E'">
        <div class="continue-progress-bar">
          <div class="continue-progress-fill" style="width: ${item.progressPct}%"></div>
        </div>
      </div>
      <div class="continue-info">
        <div class="continue-title">${title}</div>
        <div class="continue-meta">${subLabel}</div>
      </div>
    `;

    card.addEventListener('click', () => {
      const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
      if (player && typeof player.playMedia === 'function') {
        player.playMedia(item);
      } else if (window.MovieDetails && typeof MovieDetails.open === 'function') {
        MovieDetails.open(item);
      }
    });

    track.appendChild(card);
  });
}

// ==========================================================================
// TRENDING TOP 10 TODAY RIBBON
// ==========================================================================
function renderTrendingTop10() {
  const section = document.getElementById('trending-top10-section');
  const track = document.getElementById('trending-top10-track');
  if (!section || !track) return;

  const catalog = window.MediaCatalog || (typeof MediaCatalog !== 'undefined' ? MediaCatalog : null);
  if (!catalog || typeof catalog.getAll !== 'function') return;

  const all = catalog.getAll() || [];
  if (all.length === 0) return;

  const top10 = all.filter(m => m.poster && !m.is_live).slice(0, 10);
  if (top10.length === 0) return;

  track.innerHTML = '';
  top10.forEach((item, index) => {
    const rank = index + 1;
    const card = document.createElement('div');
    card.className = 'top10-card dpad-focusable';
    card.tabIndex = 0;
    const title = escapeHtml(item.arabic_title || item.title || '');
    const poster = item.poster;

    card.innerHTML = `
      <div class="top10-rank">${rank}</div>
      <div class="top10-poster-wrap">
        <img src="${poster}" alt="${title}" loading="lazy" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 130 190\' fill=\'%2308101a\'/%3E'">
      </div>
    `;

    card.addEventListener('click', () => {
      const details = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
      if (details && typeof details.open === 'function') {
        details.open(item);
      }
    });

    track.appendChild(card);
  });
}

// ==========================================================================
// MULTI-VIEW 4-SCREEN QUAD PLAYER
// ==========================================================================
// ==========================================================================
// MULTI-VIEW DUAL SPLIT-SCREEN & QUAD PLAYER
// ==========================================================================
let multiViewHlsInstances = [];
let multiViewCurrentMode = 'dual'; // Default: Dual Split-Screen 1fr 1fr

function setMultiViewAudio(targetTileNum) {
  const modal = document.getElementById('multiview-modal');
  if (!modal) return;
  const count = (multiViewCurrentMode === 'dual') ? 2 : 4;

  for (let i = 1; i <= 4; i++) {
    const vid = document.getElementById(`mv-video-${i}`);
    const mBtn = modal.querySelector(`.mv-mute-btn[data-tile="${i}"]`);
    const tile = document.getElementById(`mv-tile-${i}`);
    if (vid) {
      if (String(i) === String(targetTileNum) && i <= count) {
        vid.muted = false;
        if (mBtn) mBtn.textContent = '🔊';
        if (tile) tile.classList.add('audio-active');
      } else {
        vid.muted = true;
        if (mBtn) mBtn.textContent = '🔇';
        if (tile) tile.classList.remove('audio-active');
      }
    }
  }
}

function setMultiViewMode(mode) {
  multiViewCurrentMode = mode;
  const grid = document.querySelector('.multiview-grid-layout');
  const dualBtn = document.getElementById('mv-mode-dual');
  const quadBtn = document.getElementById('mv-mode-quad');

  if (dualBtn && quadBtn) {
    dualBtn.classList.toggle('active', mode === 'dual');
    quadBtn.classList.toggle('active', mode === 'quad');
  }

  if (grid) {
    if (mode === 'dual') {
      grid.classList.add('split-dual');
    } else {
      grid.classList.remove('split-dual');
    }
  }

  startMultiViewPlayback();
}

function setupMultiViewModal() {
  const modal = document.getElementById('multiview-modal');
  const openBtn = document.getElementById('open-multiview-btn');
  const closeBtn = document.getElementById('close-multiview-modal-btn');
  if (!modal) return;

  const dualBtn = document.getElementById('mv-mode-dual');
  const quadBtn = document.getElementById('mv-mode-quad');

  if (dualBtn) {
    dualBtn.addEventListener('click', () => setMultiViewMode('dual'));
  }
  if (quadBtn) {
    quadBtn.addEventListener('click', () => setMultiViewMode('quad'));
  }

  if (openBtn) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('active');
      setMultiViewMode(multiViewCurrentMode);
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      stopMultiViewPlayback();
      modal.classList.remove('active');
    });
  }

  // Expand / Maximize button on tiles to fill the container
  function toggleMaximizeTile(tileNum) {
    const targetTile = document.getElementById(`mv-tile-${tileNum}`);
    if (!targetTile) return;
    const isMax = targetTile.classList.contains('maximized');
    modal.querySelectorAll('.multiview-screen-tile').forEach(t => {
      t.classList.remove('maximized');
      const b = t.querySelector('.mv-expand-btn');
      if (b) {
        b.textContent = '⛶';
        b.title = 'تكبير لملء الشاشة';
      }
    });
    if (!isMax) {
      targetTile.classList.add('maximized');
      const b = targetTile.querySelector('.mv-expand-btn');
      if (b) {
        b.textContent = '🗗';
        b.title = 'استعادة العرض المنقسم';
      }
      setMultiViewAudio(tileNum);
    }
  }

  const expandBtns = modal.querySelectorAll('.mv-expand-btn');
  expandBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const tileNum = btn.getAttribute('data-tile');
      toggleMaximizeTile(tileNum);
    });
  });

  // Click on tile to swap audio directly, double click to maximize
  const tiles = modal.querySelectorAll('.multiview-screen-tile');
  tiles.forEach(tile => {
    tile.addEventListener('click', (e) => {
      if (e.target.closest('.mv-mute-btn') || e.target.closest('.mv-expand-btn')) return;
      const tileNum = tile.id.replace('mv-tile-', '');
      setMultiViewAudio(tileNum);
    });
    tile.addEventListener('dblclick', () => {
      const tileNum = tile.id.replace('mv-tile-', '');
      toggleMaximizeTile(tileNum);
    });
  });

  const muteBtns = modal.querySelectorAll('.mv-mute-btn');
  muteBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const tileNum = btn.getAttribute('data-tile');
      setMultiViewAudio(tileNum);
    });
  });
}

function startMultiViewPlayback() {
  stopMultiViewPlayback();
  const channels = (window.IPTVEngine && typeof IPTVEngine.getDefaultChannels === 'function')
    ? IPTVEngine.getDefaultChannels()
    : [];

  const count = (multiViewCurrentMode === 'dual') ? 2 : 4;
  const activeStreams = channels.slice(0, count);

  activeStreams.forEach((ch, idx) => {
    const tileIdx = idx + 1;
    const titleEl = document.getElementById(`mv-title-${tileIdx}`);
    const videoEl = document.getElementById(`mv-video-${tileIdx}`);
    const mBtn = document.querySelector(`.mv-mute-btn[data-tile="${tileIdx}"]`);
    const tile = document.getElementById(`mv-tile-${tileIdx}`);

    if (titleEl) titleEl.textContent = ch.name || `قناة ${tileIdx}`;
    if (!videoEl || !ch.streamUrl) return;

    // Default tile 1 has audio, other tiles muted
    videoEl.muted = (tileIdx !== 1);
    if (mBtn) mBtn.textContent = (tileIdx === 1) ? '🔊' : '🔇';
    if (tile) tile.classList.toggle('audio-active', tileIdx === 1);

    if (window.Hls && Hls.isSupported() && ch.streamUrl.includes('.m3u8')) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 0,
        maxBufferLength: 4,
        maxMaxBufferLength: 8
      });
      hls.loadSource(ch.streamUrl);
      hls.attachMedia(videoEl);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (hls.levels && hls.levels.length > 2) {
          hls.autoLevelCapping = 1;
        }
        videoEl.play().catch(() => {});
      });
      multiViewHlsInstances.push(hls);
    } else {
      videoEl.src = ch.streamUrl;
      videoEl.play().catch(() => {});
    }
  });
}

function stopMultiViewPlayback() {
  const modal = document.getElementById('multiview-modal');
  if (modal) {
    modal.querySelectorAll('.multiview-screen-tile').forEach(t => {
      t.classList.remove('maximized');
      const b = t.querySelector('.mv-expand-btn');
      if (b) {
        b.textContent = '⛶';
        b.title = 'تكبير لملء الشاشة';
      }
    });
  }
  multiViewHlsInstances.forEach(h => {
    try { h.destroy(); } catch (_) {}
  });
  multiViewHlsInstances = [];
  for (let i = 1; i <= 4; i++) {
    const vid = document.getElementById(`mv-video-${i}`);
    if (vid) {
      vid.pause();
      vid.removeAttribute('src');
      vid.load();
    }
  }
}

// ==========================================================================
// QR PHONE REMOTE CONTROLLER MODAL
// ==========================================================================
function setupQRRemoteModal() {
  const modal = document.getElementById('qr-remote-modal');
  const openBtn = document.getElementById('open-qr-remote-btn');
  const closeBtn = document.getElementById('close-qr-remote-btn');
  const qrImg = document.getElementById('qr-code-img');
  const urlDisplay = document.getElementById('qr-local-url-display');

  if (!modal) return;

  if (openBtn) {
    openBtn.addEventListener('click', () => {
      const remoteUrl = `${window.location.origin}/#remote`;
      if (urlDisplay) urlDisplay.textContent = remoteUrl;
      if (qrImg) {
        qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(remoteUrl)}`;
      }
      modal.classList.add('active');
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.classList.remove('active');
    });
  }
}

// ==========================================================================
// SURPRISE ME (RANDOM TITLE PICKER)
// ==========================================================================
function setupSurpriseMe() {
  const surpriseBtn = document.getElementById('surprise-me-btn');
  if (surpriseBtn) {
    surpriseBtn.addEventListener('click', () => {
      const catalog = window.MediaCatalog || (typeof MediaCatalog !== 'undefined' ? MediaCatalog : null);
      if (!catalog || typeof catalog.getAll !== 'function') return;
      const all = catalog.getAll();
      if (!all || all.length === 0) return;
      const randomItem = all[Math.floor(Math.random() * all.length)];
      const details = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
      if (details && typeof details.open === 'function') {
        details.open(randomItem);
      }
    });
  }
}

// ==========================================================================
// MOOD-BASED CINEMA FILTER
// ==========================================================================
function setupMoodFilter() {
  const container = document.getElementById('mood-pills-container');
  if (!container) return;

  const moodKeywords = {
    action: ['اكشن', 'أكشن', 'حركة', 'إثارة', 'قتال', 'action'],
    horror: ['رعب', 'تشويق', 'مخيف', 'horror', 'thriller'],
    comedy: ['كوميدي', 'كوميديا', 'مضحك', 'ساخر', 'comedy'],
    mystery: ['غموض', 'جريمة', 'تحقيق', 'ذكاء', 'mystery', 'crime'],
    drama: ['دراما', 'رومانسي', 'اجتماعي', 'drama'],
    scifi: ['خيال', 'فضاء', 'مستقبل', 'sci-fi', 'scifi', 'خيال علمي'],
    kids: ['كارتون', 'أنمي', 'انمي', 'اطفال', 'أطفال', 'عائلي', 'animation']
  };

  const pills = container.querySelectorAll('.mood-pill');
  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const mood = pill.getAttribute('data-mood');

      if (mood === 'all') {
        showHomeView();
        return;
      }

      const catalog = window.MediaCatalog || (typeof MediaCatalog !== 'undefined' ? MediaCatalog : null);
      if (!catalog || typeof catalog.getAll !== 'function') return;

      const all = catalog.getAll() || [];
      const keywords = moodKeywords[mood] || [];

      const filtered = all.filter(item => {
        const titleStr = `${item.title || ''} ${item.arabic_title || ''} ${item.synopsis || ''}`.toLowerCase();
        const genreStr = Array.isArray(item.genres) ? item.genres.join(' ').toLowerCase() : '';
        const combined = `${titleStr} ${genreStr} ${item.category || ''}`.toLowerCase();
        return keywords.some(k => combined.includes(k));
      });

      // Render dedicated category view with mood results
      const homeView = document.getElementById('home-page-view');
      const catView = document.getElementById('category-page-view');
      if (homeView && catView) {
        homeView.classList.add('is-hidden');
        homeView.style.display = 'none';
        catView.classList.remove('is-hidden');
        catView.style.display = 'block';

        const titleEl = document.getElementById('category-page-title');
        if (titleEl) titleEl.textContent = `أجواء: ${pill.textContent.trim()}`;
        const headingEl = document.getElementById('category-page-heading');
        if (headingEl) headingEl.textContent = `سينما المزاج: ${pill.textContent.trim()}`;
        const descEl = document.getElementById('category-page-desc');
        if (descEl) descEl.textContent = `تم العثور على ${filtered.length} عملاً يطابق هذه الأجواء الخاصة`;

        renderCategoryGrid(filtered, mood);
      }
    });
  });
}

// ==========================================================================
// 30s CINEMA QUIZ ("ماذا تشاهد الليلة؟")
// ==========================================================================
function setupCinemaQuiz() {
  const openBtn = document.getElementById('open-cinema-quiz-btn');
  const modal = document.getElementById('cinema-quiz-modal');
  const closeBtn = document.getElementById('close-quiz-modal-btn');
  const body = document.getElementById('quiz-body-container');

  if (!modal || !body) return;

  if (openBtn) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('active');
      startQuizFlow();
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  }

  const quizState = { mood: null, type: null, lang: null };

  function startQuizFlow() {
    quizState.mood = null;
    quizState.type = null;
    quizState.lang = null;
    renderQuizStep1();
  }

  function renderQuizStep1() {
    body.innerHTML = `
      <div class="quiz-question">السؤال 1 من 3: ما هو نوع المشاهدة التي تبحث عنها الليلة؟</div>
      <div class="quiz-options-grid">
        <button class="quiz-opt-btn dpad-focusable" data-answer="action">⚡ أكشن وحماس وإثارة</button>
        <button class="quiz-opt-btn dpad-focusable" data-answer="comedy">😂 ضحك ومرح وتسلية</button>
        <button class="quiz-opt-btn dpad-focusable" data-answer="horror">😱 رعب وتشويق وحبس أنفاس</button>
        <button class="quiz-opt-btn dpad-focusable" data-answer="drama">🎭 دراما عميقة وقصة قوية</button>
      </div>
    `;
    body.querySelectorAll('.quiz-opt-btn').forEach(btn => {
      btn.onclick = () => {
        quizState.mood = btn.getAttribute('data-answer');
        renderQuizStep2();
      };
    });
  }

  function renderQuizStep2() {
    body.innerHTML = `
      <div class="quiz-question">السؤال 2 من 3: هل تفضل فيلماً سريعاً أم مسلسلاً بحلقات كاملة؟</div>
      <div class="quiz-options-grid">
        <button class="quiz-opt-btn dpad-focusable" data-answer="movie">🎬 فيلم سهرة كامل (ساعتين)</button>
        <button class="quiz-opt-btn dpad-focusable" data-answer="series">📺 مسلسل حلقات كاملة</button>
      </div>
    `;
    body.querySelectorAll('.quiz-opt-btn').forEach(btn => {
      btn.onclick = () => {
        quizState.type = btn.getAttribute('data-answer');
        renderQuizStep3();
      };
    });
  }

  function renderQuizStep3() {
    body.innerHTML = `
      <div class="quiz-question">السؤال 3 من 3: ما هي لغة العمل المفضلة لديك؟</div>
      <div class="quiz-options-grid">
        <button class="quiz-opt-btn dpad-focusable" data-answer="foreign">🌍 أجنبي وعالمي مترجم</button>
        <button class="quiz-opt-btn dpad-focusable" data-answer="arabic">🇪🇬 مصري وعربي</button>
        <button class="quiz-opt-btn dpad-focusable" data-answer="turkish">🇹🇷 تركي دراما</button>
        <button class="quiz-opt-btn dpad-focusable" data-answer="anime">⛩️ أنمي ياباني</button>
      </div>
    `;
    body.querySelectorAll('.quiz-opt-btn').forEach(btn => {
      btn.onclick = () => {
        quizState.lang = btn.getAttribute('data-answer');
        calculateQuizResult();
      };
    });
  }

  function calculateQuizResult() {
    const catalog = window.MediaCatalog || (typeof MediaCatalog !== 'undefined' ? MediaCatalog : null);
    if (!catalog || typeof catalog.getAll !== 'function') return;

    const all = catalog.getAll() || [];
    let candidates = all.filter(m => m.poster);

    if (quizState.type) {
      candidates = candidates.filter(m => quizState.type === 'movie' ? (m.content_type === 'movie' || !m.content_type) : m.content_type === 'series');
    }
    if (quizState.lang && candidates.some(m => m.category === quizState.lang)) {
      candidates = candidates.filter(m => m.category === quizState.lang);
    }

    const winner = candidates.length > 0 ? candidates[Math.floor(Math.random() * Math.min(5, candidates.length))] : all[0];
    if (!winner) return;

    body.innerHTML = `
      <div style="text-align: center;">
        <div style="font-size: 14px; color: var(--primary-cyan); font-weight: 700; margin-bottom: 6px;">🎉 عملك المثالي لهذه السهرة وفق اختياراتك هو:</div>
        <img src="${winner.backdrop || winner.poster}" style="width: 100%; height: 200px; object-fit: cover; border-radius: 12px; margin-bottom: 12px; border: 1px solid rgba(0,229,255,0.4);" alt="${winner.title}">
        <h3 style="font-size: 20px; font-weight: 900; color: #fff; margin-bottom: 4px;">${winner.arabic_title || winner.title}</h3>
        <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 16px;">★ ${winner.rating || '8.8'} • ${winner.quality || '1080p FHD'} • ${winner.year || '2026'}</div>
        <div style="display: flex; gap: 10px; justify-content: center;">
          <button id="quiz-play-winner-btn" class="btn-primary dpad-focusable" style="padding: 10px 24px; font-size: 14px;">▶ مشاهدة فورية الآن</button>
          <button id="quiz-retry-btn" class="btn-secondary dpad-focusable" style="padding: 10px 18px; font-size: 14px;">إعادة الاختبار 🔄</button>
        </div>
      </div>
    `;

    document.getElementById('quiz-play-winner-btn')?.addEventListener('click', () => {
      modal.classList.remove('active');
      if (window.MovieDetails && typeof MovieDetails.open === 'function') {
        MovieDetails.open(winner);
      }
    });

    document.getElementById('quiz-retry-btn')?.addEventListener('click', () => {
      startQuizFlow();
    });
  }
}

// ==========================================================================
// WATCH TOGETHER (SYNCPLAY ROOM VIA BROADCASTCHANNEL)
// ==========================================================================
let syncBroadcastChannel = null;

function setupWatchTogether() {
  const openBtn = document.getElementById('open-watch-together-btn');
  const modal = document.getElementById('watch-together-modal');
  const closeBtn = document.getElementById('close-wt-modal-btn');
  const joinBtn = document.getElementById('wt-join-btn');
  const copyBtn = document.getElementById('wt-copy-link-btn');
  const roomInput = document.getElementById('wt-room-input');

  if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
    syncBroadcastChannel = new BroadcastChannel('atube_sync_room');
    syncBroadcastChannel.onmessage = (event) => {
      const data = event.data;
      const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
      const vid = document.getElementById('main-video');
      if (!vid) return;

      if (data.action === 'play') {
        if (vid.paused) vid.play().catch(() => {});
      } else if (data.action === 'pause') {
        if (!vid.paused) vid.pause();
      } else if (data.action === 'seek') {
        if (Math.abs(vid.currentTime - data.time) > 2) {
          vid.currentTime = data.time;
        }
      }
    };
  }

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('active');
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  }

  if (copyBtn && roomInput) {
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(`${window.location.origin}/?room=${roomInput.value}`).then(() => {
        copyBtn.textContent = 'تم النسخ بنجاح ✓';
        setTimeout(() => copyBtn.textContent = 'نسخ الرابط 📋', 2000);
      });
    });
  }

  if (joinBtn && modal) {
    joinBtn.addEventListener('click', () => {
      modal.classList.remove('active');
      alert('تم الاتصال بغرفة المشاهدة الجماعية! أي إيقاف أو تشغيل سيتزامن مع الجميع في نفس الوقت.');
    });
  }
}

// ==========================================================================
// CUSTOM THEMES SWITCHER
// ==========================================================================
function setupThemesCustomizer() {
  const openBtn = document.getElementById('open-themes-modal-btn');
  const modal = document.getElementById('themes-modal');
  const closeBtn = document.getElementById('close-themes-modal-btn');

  // Load saved theme on boot
  const savedTheme = localStorage.getItem('atube_theme') || 'cyan';
  document.documentElement.setAttribute('data-theme', savedTheme);

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      modal.classList.add('active');
      modal.querySelectorAll('.theme-card').forEach(card => {
        card.classList.toggle('active', card.getAttribute('data-theme') === savedTheme);
      });
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  }

  const themeCards = document.querySelectorAll('.theme-card');
  themeCards.forEach(card => {
    card.addEventListener('click', () => {
      themeCards.forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      const theme = card.getAttribute('data-theme');
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('atube_theme', theme);
      if (modal) modal.classList.remove('active');
    });
  });
}

// ==========================================================================
// KEYBOARD SHORTCUTS HUD
// ==========================================================================
function setupShortcutsHUD() {
  const openBtn = document.getElementById('open-shortcuts-btn');
  const modal = document.getElementById('shortcuts-hud-modal');
  const closeBtn = document.getElementById('close-shortcuts-modal-btn');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => modal.classList.add('active'));
  }
  if (closeBtn && modal) {
    closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === '?' && modal) {
      modal.classList.toggle('active');
    }
  });
}

// ==========================================================================
// AERIAL 4K SCREENSAVER (3-MINUTE IDLE DETECTOR)
// ==========================================================================
function setupAerialScreensaver() {
  const saverEl = document.getElementById('aerial-screensaver');
  const clockEl = document.getElementById('screensaver-clock');
  const videoBg = document.getElementById('screensaver-video');
  if (!saverEl) return;

  let idleTimer = null;
  const IDLE_TIME_MS = 3 * 60 * 1000; // 3 minutes

  function resetIdleTimer() {
    if (saverEl.classList.contains('active')) {
      saverEl.classList.remove('active');
      saverEl.classList.add('is-hidden');
      if (videoBg) videoBg.pause();
    }
    clearTimeout(idleTimer);
    idleTimer = setTimeout(triggerScreensaver, IDLE_TIME_MS);
  }

  function triggerScreensaver() {
    const vidModal = document.getElementById('video-modal');
    if (vidModal && vidModal.classList.contains('active')) return; // Do not interrupt movie watching

    saverEl.classList.remove('is-hidden');
    saverEl.classList.add('active');
    if (videoBg) {
      videoBg.src = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4';
      videoBg.play().catch(() => {});
    }
    updateClock();
  }

  function updateClock() {
    if (!clockEl) return;
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
  }

  setInterval(() => {
    if (saverEl.classList.contains('active')) updateClock();
  }, 1000);

  ['mousemove', 'keydown', 'touchstart', 'click'].forEach(evt => {
    window.addEventListener(evt, resetIdleTimer, { passive: true });
  });

  resetIdleTimer();
}

// ==========================================================================
// GAMEPAD / CONTROLLER SUPPORT (XBOX & PLAYSTATION)
// ==========================================================================
function setupGamepadSupport() {
  if (typeof window === 'undefined' || !('getGamepads' in navigator)) return;

  let lastButtonPress = 0;

  function pollGamepad() {
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
    const gp = gamepads[0];

    if (gp && Date.now() - lastButtonPress > 220) {
      // D-Pad / Left Stick
      if (gp.buttons[12] && gp.buttons[12].pressed) {
        dispatchVirtualKey('ArrowUp');
        lastButtonPress = Date.now();
      } else if (gp.buttons[13] && gp.buttons[13].pressed) {
        dispatchVirtualKey('ArrowDown');
        lastButtonPress = Date.now();
      } else if (gp.buttons[14] && gp.buttons[14].pressed) {
        dispatchVirtualKey('ArrowLeft');
        lastButtonPress = Date.now();
      } else if (gp.buttons[15] && gp.buttons[15].pressed) {
        dispatchVirtualKey('ArrowRight');
        lastButtonPress = Date.now();
      } else if (gp.buttons[0] && gp.buttons[0].pressed) {
        // Button A / Cross: Select / Click
        const focused = document.activeElement;
        if (focused && typeof focused.click === 'function') focused.click();
        lastButtonPress = Date.now();
      } else if (gp.buttons[1] && gp.buttons[1].pressed) {
        // Button B / Circle: Back / Escape
        dispatchVirtualKey('Escape');
        lastButtonPress = Date.now();
      }
    }
    requestAnimationFrame(pollGamepad);
  }

  function dispatchVirtualKey(keyName) {
    const ev = new KeyboardEvent('keydown', { key: keyName, bubbles: true });
    document.dispatchEvent(ev);
  }

  window.addEventListener('gamepadconnected', () => {
    console.log('[A TuBe] Gamepad connected successfully');
    requestAnimationFrame(pollGamepad);
  });
}

// ==========================================================================
// HAPTIC FEEDBACK (VIBRATION API)
// ==========================================================================
function setupHapticFeedback() {
  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    document.addEventListener('click', (e) => {
      if (e.target.closest('button, .dpad-focusable, .program-card, .mood-pill')) {
        try { navigator.vibrate(12); } catch (_) {}
      }
    }, { passive: true });
  }
}

// ==========================================================================
// KIDS SAFE MODE
// ==========================================================================
function setupKidsSafeMode() {
  const isKids = localStorage.getItem('atube_kids_mode') === 'true';
  if (isKids) {
    document.body.classList.add('kids-mode-active');
  }
}


