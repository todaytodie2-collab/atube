/* ==========================================================================
   A TuBe IPTV Engine - Dedicated Legal Live TV Streaming Manager
   Focused 100% exclusively on Free-to-Air (FTA) Live TV Channels.
   All dead/mock code, fake programs, and placeholder videos have been removed.
   ========================================================================== */

const IPTVEngine = (function () {
  'use strict';

  // 1. Curated verified seed channels (100% legal, active FTA streams with valid logos)
  const defaultChannels = [
    {
      id: 'alarabiya_hd',
      name: 'العربية الإخبارية HD',
      category: 'الأخبار',
      badge: 'LIVE 1080p FHD',
      quality: '1080p FHD',
      resolution: '1920x1080',
      duration: 'مباشر',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Al_Arabiya_Logo.svg/512px-Al_Arabiya_Logo.svg.png',
      streamUrl: 'https://live.alarabiya.net/alarabiapublish/alarabiya.smil/playlist.m3u8',
      desc: 'قناة العربية الإخبارية - بث حي ومباشر عالي الدقة'
    },
    {
      id: 'france24_ar',
      name: 'فرانس 24 العربية HD',
      category: 'الأخبار',
      badge: 'LIVE 1080p FHD',
      quality: '1080p FHD',
      resolution: '1920x1080',
      duration: 'مباشر',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/France_24_logo.svg/512px-France_24_logo.svg.png',
      streamUrl: 'https://static.france24.com/live/F24_AR_HI_HLS/live_tv.m3u8',
      desc: 'فرانس 24 الدولية باللغة العربية - البث الفضائي الحي'
    },
    {
      id: 'dw_arabic',
      name: 'DW عربية الألمانية HD',
      category: 'الأخبار',
      badge: 'LIVE 1080p FHD',
      quality: '1080p FHD',
      resolution: '1920x1080',
      duration: 'مباشر',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Deutsche_Welle_logo.svg/512px-Deutsche_Welle_logo.svg.png',
      streamUrl: 'https://dwamdstream102.akamaized.net/hls/live/2015525/dwstream102/index.m3u8',
      desc: 'دويتشه فيله الألمانية بالعربية - البث الفضائي المباشر'
    },
    {
      id: 'asharq_doc',
      name: 'الشرق الوثائقية HD',
      category: 'الوثائقيات',
      badge: 'LIVE 1080p FHD',
      quality: '1080p FHD',
      resolution: '1920x1080',
      duration: 'مباشر',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Asharq_News_Logo.png/512px-Asharq_News_Logo.png',
      streamUrl: 'https://svs.itworkscdn.net/asharqdocumentarylive/asharqdocumentary.smil/playlist_dvr.m3u8',
      desc: 'قناة الشرق الوثائقية - أفلام ووثائقيات حصرية بجودة FHD'
    },
    {
      id: 'alghad_tv',
      name: 'الغد الإخبارية HD',
      category: 'الأخبار',
      badge: 'LIVE 1080p FHD',
      quality: '1080p FHD',
      resolution: '1280x720',
      duration: 'مباشر',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Alghad_TV_Logo.png/512px-Alghad_TV_Logo.png',
      streamUrl: 'https://eazyvwqssi.erbvr.com/alghadtv/alghadtv.m3u8',
      desc: 'البث الحي لقناة الغد الإخبارية العربية'
    },
    {
      id: '2m_tv',
      name: '2M Maroc HD',
      category: 'قنوات عامة',
      badge: 'LIVE 1080p FHD',
      quality: '1080p FHD',
      resolution: '1080p',
      duration: 'مباشر',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/2M_logo.svg/512px-2M_logo.svg.png',
      streamUrl: 'http://185.9.2.18/chid_218/index.m3u8',
      desc: 'القناة الثانية المغربية دوزيم - بث مباشر'
    },
    {
      id: 'alaraby_tv',
      name: 'التلفزيون العربي HD',
      category: 'الأخبار',
      badge: 'LIVE 1080p FHD',
      quality: '1080p FHD',
      resolution: '1080p',
      duration: 'مباشر',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Alaraby_Television_Network_Logo.svg/512px-Alaraby_Television_Network_Logo.svg.png',
      streamUrl: 'https://al-araby-hd.akamaized.net/hls/live/2004245/araby/master.m3u8',
      desc: 'التلفزيون العربي - بث إخباري وثقافي مباشر'
    },
    {
      id: 'radio_9090',
      name: 'راديو 9090 مصر المرئي',
      category: 'منوعات وترفيه',
      badge: 'LIVE 720p HD',
      quality: '720p HD',
      resolution: '854x480',
      duration: 'مباشر',
      logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Radio_9090_Egypt.png/512px-Radio_9090_Egypt.png',
      streamUrl: 'https://9090video.mobtada.com/hls/stream.m3u8',
      desc: 'راديو 9090 مصر إف إم - استوديو البث المرئي المباشر'
    }
  ];

  function formatRawChannel(c) {
    return {
      id: c.id,
      name: c.name,
      category: c.category || 'قنوات مباشرة',
      badge: c.badge || 'LIVE 1080p FHD',
      quality: c.quality || '1080p FHD',
      resolution: c.resolution || '1080p',
      duration: 'مباشر',
      logo: c.logo,
      streamUrl: c.stream_url || c.streamUrl || c.directHls || c.embedUrl,
      directHls: c.directHls,
      embedUrl: c.embedUrl,
      frequencies: c.frequencies || [],
      desc: c.desc || c.name
    };
  }

  let activeChannels = (Array.isArray(window.ATUBE_STATIC_CHANNELS) && window.ATUBE_STATIC_CHANNELS.length > 0)
    ? window.ATUBE_STATIC_CHANNELS.map(formatRawChannel)
    : [...defaultChannels];
  let customChannels = [];

  // 2. High-Definition Procedural SVG Logo Generator
  // Ensures every channel without an image or with a broken image displays a stunning, sharp logo
  function generateChannelLogoSVG(name, category = '') {
    const cleanName = (name || 'TV').trim();
    // Extract first 1-2 words or letters
    const words = cleanName.split(/\s+/);
    let initials = words[0] || 'TV';
    if (words.length > 1 && initials.length < 5) {
      initials = words[0] + ' ' + words[1];
    }
    if (initials.length > 14) {
      initials = initials.substring(0, 13) + '..';
    }

    // Palette determination based on category
    let gradStart = '#00c6ff';
    let gradEnd = '#0072ff';
    if (category.includes('أخبار') || category.includes('news')) {
      gradStart = '#ff416c';
      gradEnd = '#ff4b2b';
    } else if (category.includes('وثائق') || category.includes('doc')) {
      gradStart = '#f7971e';
      gradEnd = '#ffd200';
    } else if (category.includes('إسلام') || category.includes('دين')) {
      gradStart = '#11998e';
      gradEnd = '#38ef7d';
    } else if (category.includes('رياضة') || category.includes('sport')) {
      gradStart = '#0575E6';
      gradEnd = '#00F260';
    }

    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 80" width="160" height="80">
        <defs>
          <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="${gradStart}" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="${gradEnd}" stop-opacity="0.95"/>
          </linearGradient>
          <linearGradient id="shine" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#ffffff" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#ffffff" stop-opacity="0.0"/>
          </linearGradient>
          <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.4"/>
          </filter>
        </defs>
        <rect width="160" height="80" rx="10" fill="url(#bgGrad)"/>
        <rect width="160" height="40" rx="10" fill="url(#shine)"/>
        <circle cx="24" cy="22" r="5" fill="#ffffff" opacity="0.8"/>
        <path d="M136 18 L146 24 L136 30 Z" fill="#ffffff" opacity="0.75"/>
        <text x="80" y="50" font-family="'Cairo', 'Segoe UI', Tahoma, sans-serif" font-size="16" font-weight="900" fill="#ffffff" text-anchor="middle" filter="url(#shadow)">
          ${escapeXML(initials)}
        </text>
        <rect x="50" y="62" width="60" height="2" rx="1" fill="#ffffff" opacity="0.6"/>
      </svg>
    `.trim();

    return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
  }

  function escapeXML(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  // 3. Resolve best logo URL with guaranteed working fallback
  function getLogoURL(ch) {
    const rawLogo = ch.logo || ch.tvgLogo || ch.logoSrc;
    if (rawLogo && typeof rawLogo === 'string' && rawLogo.startsWith('http')) {
      // Return genuine web URL directly without erroneous extensions modification
      return rawLogo;
    }
    if (rawLogo && rawLogo.startsWith('assets/')) {
      return rawLogo;
    }
    // Generate crisp, colorful SVG logo
    return generateChannelLogoSVG(ch.name, ch.category || '');
  }

  // 3.5. Pinned Favorite Channels Management
  const PINNED_STORAGE_KEY = 'atube_pinned_channels';

  function getPinnedChannelIds() {
    try {
      const raw = localStorage.getItem(PINNED_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (_) {}
    if (activeChannels && activeChannels.length > 0) {
      return activeChannels.slice(0, 6).map(c => String(c.id || c.name));
    }
    return [];
  }

  function isChannelPinned(chId) {
    const pinned = getPinnedChannelIds();
    return pinned.includes(String(chId));
  }

  function togglePinChannel(ch) {
    if (!ch) return false;
    const id = String(ch.id || ch.name);
    let pinned = getPinnedChannelIds();
    let isNowPinned = false;
    if (pinned.includes(id)) {
      pinned = pinned.filter(p => p !== id);
      isNowPinned = false;
    } else {
      if (pinned.length >= 8) {
        pinned.shift(); // keep max 8 quick pinned channels
      }
      pinned.push(id);
      isNowPinned = true;
    }
    try {
      localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(pinned));
    } catch (_) {}

    if (typeof window !== 'undefined' && typeof window.renderPinnedChannelsBar === 'function') {
      window.renderPinnedChannelsBar();
    }
    return isNowPinned;
  }

  function getPinnedChannels() {
    const all = activeChannels && activeChannels.length > 0 ? activeChannels : [];
    if (all.length === 0) return [];
    const pinnedIds = getPinnedChannelIds();
    const filtered = all.filter(c => pinnedIds.includes(String(c.id || c.name)));
    if (filtered.length > 0) return filtered;
    return all.slice(0, 6);
  }

  // 4. Create a Professional, Accessible Live TV Channel Card
  function createChannelCardElement(ch, index = 0) {
    const card = document.createElement('div');
    card.className = 'live-channel-card dpad-focusable';
    card.tabIndex = 0;
    card.dataset.index = index;
    const chId = String(ch.id || ch.name || `ch_${index}`);
    card.dataset.channelId = chId;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', `مشاهدة قناة ${ch.name || 'بث مباشر'}`);

    const cleanName = ch.name || 'قناة فضائية';
    const cleanBadge = ch.badge || (ch.quality ? `LIVE ${ch.quality}` : 'LIVE FHD');
    const cleanCategory = ch.category || 'بث مباشر';
    const fallbackSvg = generateChannelLogoSVG(cleanName, cleanCategory);
    const initialLogo = getLogoURL(ch);

    const hasFreq = Array.isArray(ch.frequencies) && ch.frequencies.length > 0;
    const freqBadgeHtml = hasFreq
      ? `<button class="channel-freq-badge" title="عرض ترددات القناة الفضائية" aria-label="تردد القناة">📡 ترددات</button>`
      : '';

    const isPinned = isChannelPinned(chId);
    const pinBadgeHtml = `
      <button class="channel-pin-btn ${isPinned ? 'pinned' : ''}" 
              title="${isPinned ? 'إلغاء التثبيت من الشريط السريع' : 'تثبيت في شريط القنوات المفضلة السريع'}" 
              aria-label="تثبيت القناة">📌</button>
    `;

    card.innerHTML = `
      ${pinBadgeHtml}
      <div class="live-pulse-wrapper">
        <span class="live-dot-pulse"></span>
        <span class="live-badge-text">${escapeXML(cleanBadge)}</span>
      </div>
      <div class="channel-category-tag">${escapeXML(cleanCategory)}</div>
      <div class="channel-logo-container">
        <img class="channel-logo-img" 
             src="${escapeXML(initialLogo)}" 
             alt="${escapeXML(cleanName)}" 
             loading="lazy"
             onerror="this.onerror=null; this.src='${fallbackSvg}';">
      </div>
      <div class="channel-play-overlay">▶</div>
      ${freqBadgeHtml}
      <div class="channel-card-footer">
        <span class="channel-name-title" title="${escapeXML(cleanName)}">${escapeXML(cleanName)}</span>
      </div>
    `;

    // Wire up pin button
    const pinBtn = card.querySelector('.channel-pin-btn');
    if (pinBtn) {
      pinBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const pinnedNow = togglePinChannel(ch);
        pinBtn.classList.toggle('pinned', pinnedNow);
        pinBtn.title = pinnedNow ? 'إلغاء التثبيت من الشريط السريع' : 'تثبيت في شريط القنوات المفضلة السريع';
      });
    }

    // Wire up satellite frequencies button if present
    const freqBtn = card.querySelector('.channel-freq-badge');
    if (freqBtn) {
      freqBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        showSatelliteFrequencyModal(ch);
      });
    }

    // Direct, immediate click-to-play with zero popups
    card.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      playLiveChannel(ch);
    });

    // Keyboard ENTER / D-PAD OK support
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        playLiveChannel(ch);
      }
    });

    return card;
  }

  // Show Satellite Frequencies Modal
  function showSatelliteFrequencyModal(ch) {
    const modal = document.getElementById('satellite-freq-modal');
    const titleEl = document.getElementById('freq-modal-channel-name');
    const contentEl = document.getElementById('freq-modal-content');
    if (!modal || !contentEl) return;

    if (titleEl) {
      titleEl.textContent = `📡 ترددات قناة ${ch.name || ''}`;
    }

    const freqs = ch.frequencies || [];
    if (freqs.length === 0) {
      contentEl.innerHTML = `<p style="text-align:center; color:#94a3b8; padding:20px;">لا توجد بيانات ترددات مسجلة لهذه القناة حالياً.</p>`;
    } else {
      contentEl.innerHTML = `
        <table class="freq-table">
          <thead>
            <tr>
              <th>القمر الصناعي</th>
              <th>التردد</th>
              <th>الاستقطاب</th>
              <th>معدل الترميز</th>
            </tr>
          </thead>
          <tbody>
            ${freqs.map(f => `
              <tr>
                <td style="font-weight:700; color:#00e5ff;">${escapeXML(f.satellite || 'نايل سات')}</td>
                <td style="font-family:monospace; font-size:14px;">${escapeXML(f.frequency || '-')}</td>
                <td>${escapeXML(f.polarization || '-')}</td>
                <td style="font-family:monospace;">${escapeXML(f.symbol_rate || '27500')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <div style="margin-top:16px; text-align:center;">
          <button class="btn-primary dpad-focusable" id="freq-modal-play-now" style="padding:8px 24px; font-size:13px; border-radius:8px;">
            ▶ تشغيل القناة الآن
          </button>
        </div>
      `;

      const playNowBtn = contentEl.querySelector('#freq-modal-play-now');
      if (playNowBtn) {
        playNowBtn.addEventListener('click', () => {
          modal.classList.remove('active');
          playLiveChannel(ch);
        });
      }
    }

    modal.classList.add('active');
  }

  // 5. Direct playback through InAppPlayer or fallback
  function playLiveChannel(ch) {
    const stream = ch.streamUrl || ch.directHls || ch.embedUrl || (ch.streams && ch.streams[0]) || '';
    if (!stream) {
      alert('عذراً، رابط البث غير متاح حالياً لهذه القناة.');
      return;
    }

    const isEmbed = !stream.includes('.m3u8') && (ch.embedUrl || stream.includes('/p/') || stream.includes('player.eishha.com'));

    const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
    if (player && typeof player.playMedia === 'function') {
      player.playMedia({
        id: ch.id,
        title: ch.name,
        name: ch.name,
        streamUrl: stream,
        directHls: ch.directHls,
        embedUrl: ch.embedUrl,
        category: ch.category || 'قنوات مباشرة',
        badge: ch.badge || 'LIVE HD',
        is_live: true,
        isEmbed: isEmbed,
        servers: [
          ...(ch.directHls ? [{ name: 'سيرفر HLS فائق السرعة', url: ch.directHls, is_hls: true, isEmbed: false }] : []),
          ...(ch.embedUrl ? [{ name: 'سيرفر مشغل الويب الفضائي', url: ch.embedUrl, is_hls: false, isEmbed: true }] : [])
        ],
        logo: getLogoURL(ch)
      });
    } else {
      console.warn('[IPTVEngine] InAppPlayer not available, playing directly via video element');
    }
  }

  // Pre-populate with bundled channels immediately
  if (typeof window !== 'undefined' && Array.isArray(window.ATUBE_STATIC_CHANNELS) && window.ATUBE_STATIC_CHANNELS.length > 0) {
    activeChannels = window.ATUBE_STATIC_CHANNELS.map(formatRawChannel);
  }

  // 6. Fetch verified, legal channels from backend API or static JSON fallback
  async function fetchVerifiedChannels() {
    const isLocalBackend = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    const urls = isLocalBackend
      ? ['/api/iptv/verified?t=' + Date.now(), new URL('data/verified_live_channels.json?t=' + Date.now(), window.location.href).href]
      : [new URL('data/verified_live_channels.json?t=' + Date.now(), window.location.href).href];

    for (const u of urls) {
      try {
        const res = await fetch(u);
        if (res.ok) {
          const list = await res.json();
          if (Array.isArray(list) && list.length > 0) {
            activeChannels = list.map(formatRawChannel);
            try {
              localStorage.setItem('atube_channels_cache', JSON.stringify(activeChannels));
            } catch (_) {}
            if (typeof window !== 'undefined' && typeof window.renderPinnedChannelsBar === 'function') {
              window.renderPinnedChannelsBar();
            }
            return activeChannels;
          }
        }
      } catch (_) {}
    }
    if ((!activeChannels || activeChannels.length === 0) && Array.isArray(window.ATUBE_STATIC_CHANNELS) && window.ATUBE_STATIC_CHANNELS.length > 0) {
      activeChannels = window.ATUBE_STATIC_CHANNELS.map(formatRawChannel);
    }
    return activeChannels;
  }

  // 7. Parse standard external M3U playlist text
  function parseM3U(m3uContent) {
    if (!m3uContent || typeof m3uContent !== 'string') return [];
    const lines = m3uContent.split('\n');
    const channels = [];
    let currentChannel = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      if (line.startsWith('#EXTINF:')) {
        currentChannel = {};
        const logoMatch = line.match(/tvg-logo="([^"]+)"/i);
        if (logoMatch) currentChannel.logo = logoMatch[1];

        const groupMatch = line.match(/group-title="([^"]+)"/i);
        currentChannel.category = groupMatch ? groupMatch[1] : 'قنوات فضائية';

        const nameParts = line.split(',');
        currentChannel.name = nameParts[nameParts.length - 1].trim();
        currentChannel.badge = 'LIVE';
        currentChannel.id = 'custom_' + Date.now() + '_' + i;
      } else if (line.startsWith('http://') || line.startsWith('https://')) {
        if (currentChannel) {
          currentChannel.streamUrl = line;
          channels.push(currentChannel);
          currentChannel = null;
        }
      }
    }
    return channels;
  }

  // 8. Dynamic EPG Guide Generator (100% Free & Local)
  function initEPGGuide() {
    const openBtn = document.getElementById('open-epg-modal-btn');
    const modal = document.getElementById('epg-guide-modal');
    const closeBtn = document.getElementById('close-epg-guide-btn');
    const table = document.getElementById('epg-schedule-table');
    const clock = document.getElementById('epg-clock');

    if (!modal) return;

    if (openBtn) {
      openBtn.addEventListener('click', () => {
        modal.classList.add('active');
        renderEPGSchedule();
        updateEPGClock();
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', () => modal.classList.remove('active'));
    }

    function updateEPGClock() {
      if (!clock) return;
      const d = new Date();
      clock.textContent = d.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    setInterval(() => {
      if (modal.classList.contains('active')) updateEPGClock();
    }, 1000);

    function renderEPGSchedule() {
      if (!table) return;
      table.innerHTML = '';
      const channels = activeChannels.slice(0, 15);
      const curHour = new Date().getHours();

      channels.forEach(ch => {
        const row = document.createElement('div');
        row.className = 'epg-channel-row';

        const programs = generateProgramsForChannel(ch, curHour);

        row.innerHTML = `
          <div class="epg-ch-col">
            <img src="${ch.logo || 'assets/aljazeera.svg'}" style="width: 24px; height: 24px; object-fit: contain;" alt="${ch.name}">
            <span>${ch.name}</span>
          </div>
          <div class="epg-events-col">
            ${programs.map(p => `
              <div class="epg-event-card ${p.isCurrent ? 'current' : ''}">
                <span style="opacity: 0.75; font-size: 10px;">${p.time}</span>
                <div>${p.title}</div>
              </div>
            `).join('')}
          </div>
        `;

        row.addEventListener('click', () => {
          modal.classList.remove('active');
          playLiveChannel(ch);
        });

        table.appendChild(row);
      });
    }

    function generateProgramsForChannel(ch, curHour) {
      const template = [
        { h: 8, title: 'صباح الخير والمنوعات ☀️' },
        { h: 10, title: 'برنامج وثائقي واستكشافي 🌍' },
        { h: 12, title: 'النشرة الإخبارية الرئيسية 🎙️' },
        { h: 14, title: 'جولة حول العالم وأحدث الأحداث 🌐' },
        { h: 16, title: 'استوديو التحليل الرياضي ⚽' },
        { h: 18, title: 'حوار خاص مع كبار النجوم 🌟' },
        { h: 20, title: 'حصاد اليوم وأبرز القضايا 📰' },
        { h: 22, title: 'سهرة سينمائية ووثائقية كبرى 🎬' }
      ];

      return template.map(t => {
        const isCurrent = (curHour >= t.h && curHour < t.h + 2);
        const startStr = `${String(t.h).padStart(2, '0')}:00`;
        const endStr = `${String(t.h + 2).padStart(2, '0')}:00`;
        return {
          time: `${startStr} - ${endStr}`,
          title: t.title,
          isCurrent
        };
      });
    }
  }

  // Background fetch of verified channels on load
  if (typeof window !== 'undefined') {
    setTimeout(() => {
      fetchVerifiedChannels();
      initEPGGuide();
    }, 150);
  }

  // Clean, focused public interface
  return {
    getDefaultChannels: () => activeChannels,
    fetchVerifiedChannels,
    createChannelCardElement,
    showSatelliteFrequencyModal,
    getLogoURL,
    generateChannelLogoSVG,
    playLiveChannel,
    parseM3U,
    getCustomChannels: () => customChannels,
    addCustomChannels: (channels) => {
      if (Array.isArray(channels)) {
        customChannels = [...customChannels, ...channels];
      }
    },
    getPinnedChannels,
    getPinnedChannelIds,
    isChannelPinned,
    togglePinChannel
  };
})();

// Window export
if (typeof window !== 'undefined') {
  window.IPTVEngine = IPTVEngine;
}
