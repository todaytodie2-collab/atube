/* ==========================================================================
   Movie Details Controller & Multi-Source Server Selector
   Matches Reference Screenshot from Akwam & Unified A Tube Experience
   ========================================================================== */

const MovieDetails = (function () {
  let modalEl = null;
  let currentMovie = null;

  function init() {
    modalEl = document.getElementById('movie-details-modal');
    if (!modalEl) return;

    // Close & Back button events
    const closeBtn = document.getElementById('movie-modal-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeModal);
    }
    const backBtn = document.getElementById('movie-modal-back-btn');
    if (backBtn) {
      backBtn.addEventListener('click', closeModal);
    }

    // Close on clicking backdrop outside container
    modalEl.addEventListener('click', (e) => {
      if (e.target === modalEl) {
        closeModal();
      }
    });
  }

  // Open modal with movie data (either from object or fetched by id)
  async function open(movieOrId) {
    if (!modalEl) {
      // Try re-init if modal not found yet
      modalEl = document.getElementById('movie-details-modal');
      if (!modalEl) return;
    }

    if (typeof movieOrId === 'string') {
      // Search by ID - prioritize instant retrieval from client-side catalog (<2ms)
      if (window.MediaCatalog) {
        currentMovie = MediaCatalog.getDetails(movieOrId);
      }
      if (!currentMovie) {
        currentMovie = getFallbackMovie(movieOrId);
      }

      // Background revalidation from server if online
      const isFileProto = window.location.protocol === 'file:';
      if (!isFileProto) {
        fetch(`/api/media/details?id=${encodeURIComponent(movieOrId)}`)
          .then(r => r.ok ? r.json() : null)
          .then(freshData => {
            if (freshData && freshData.id) {
              currentMovie = freshData;
              renderMovieDetails(currentMovie);
            }
          })
          .catch(() => {});
      }
    } else if (movieOrId && typeof movieOrId === 'object') {
      // Instant display from preloaded memory
      currentMovie = movieOrId;

      // Only fetch background enhancement if it is a series that lacks episode data
      const isFileProto = window.location.protocol === 'file:';
      if (!isFileProto && movieOrId.id && (movieOrId.content_type === 'series' || movieOrId.content_type === 'anime')) {
        if (!movieOrId.seasons || movieOrId.seasons.length === 0) {
          fetch(`/api/media/details?id=${encodeURIComponent(movieOrId.id)}`)
            .then(r => r.ok ? r.json() : null)
            .then(freshData => {
              if (freshData && freshData.id && freshData.seasons && freshData.seasons.length > 0) {
                currentMovie = { ...currentMovie, ...freshData };
                renderMovieDetails(currentMovie);
              }
            })
            .catch(() => {});
        }
      }
    }

    if (!currentMovie) return;

    try {
      renderMovieDetails(currentMovie);
    } catch (err) {
      console.error('Error in renderMovieDetails:', err);
    }

    modalEl.classList.add('active');
    modalEl.style.display = 'flex';

    // Scroll modal to top
    const container = modalEl.querySelector('.movie-modal-container');
    if (container) container.scrollTop = 0;

    // Refresh Remote Navigation elements
    const rc = window.RemoteControl || (typeof RemoteControl !== 'undefined' ? RemoteControl : null);
    if (rc && typeof rc.refresh === 'function') {
      setTimeout(() => rc.refresh(), 200);
    }
  }

  function closeModal() {
    if (!modalEl) {
      modalEl = document.getElementById('movie-details-modal');
      if (!modalEl) return;
    }
    modalEl.classList.remove('active');
    modalEl.style.display = 'none';
    const rc = window.RemoteControl || (typeof RemoteControl !== 'undefined' ? RemoteControl : null);
    if (rc && typeof rc.refresh === 'function') {
      setTimeout(() => rc.refresh(), 100);
    }
  }

  function renderMovieDetails(movie) {
    // Backdrop & Poster
    const backdropImg = document.getElementById('md-backdrop');
    if (backdropImg) backdropImg.src = movie.backdrop || movie.poster;

    const posterImg = document.getElementById('md-poster');
    if (posterImg) posterImg.src = movie.poster;

    // Titles
    const titleEl = document.getElementById('md-title');
    if (titleEl) titleEl.textContent = movie.title;

    const arTitleEl = document.getElementById('md-ar-title');
    if (arTitleEl) arTitleEl.textContent = movie.arabic_title || '';

    // Badges
    const imdbBadge = document.getElementById('md-imdb');
    if (imdbBadge) imdbBadge.textContent = movie.rating || '★ 8.5 IMDb';

    const qualityBadge = document.getElementById('md-quality');
    if (qualityBadge) qualityBadge.textContent = movie.quality || '1080p WEB-DL';

    // Attributes Grid
    const attrsContainer = document.getElementById('md-attributes');
    if (attrsContainer) {
      attrsContainer.innerHTML = `
        <div class="attr-item"><span class="attr-label">اللغة:</span> ${movie.language || 'الإنجليزية'}</div>
        <div class="attr-item"><span class="attr-label">الترجمة:</span> ${movie.translation || 'مترجم للعربية'}</div>
        <div class="attr-item"><span class="attr-label">السنة:</span> ${movie.year || '2026'}</div>
        <div class="attr-item"><span class="attr-label">المدة:</span> ${movie.duration || '92 دقيقة'}</div>
        <div class="attr-item"><span class="attr-label">الإنتاج:</span> ${movie.production || 'الولايات المتحدة'}</div>
      `;
    }

    // Genre Pills
    const genresContainer = document.getElementById('md-genres');
    if (genresContainer) {
      genresContainer.innerHTML = '';
      (movie.genres || ['غموض', 'دراما', 'جريمة']).forEach(g => {
        const pill = document.createElement('span');
        pill.className = 'movie-tag-pill';
        pill.textContent = g;
        genresContainer.appendChild(pill);
      });
    }

    // Trailer Button Action (Opens YouTube Trailer or First Server)
    const trailerBtn = document.getElementById('md-trailer-btn');
    if (trailerBtn) {
      trailerBtn.onclick = () => {
        const ytId = movie.trailer_youtube_id;
        if (ytId && window.open) {
          window.open(`https://www.youtube.com/watch?v=${ytId}`, '_blank');
        } else if (movie.servers && movie.servers.length > 0) {
          const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
          if (player && typeof player.playMedia === 'function') {
            player.playMedia({
              name: `إعلان: ${movie.arabic_title || movie.title}`,
              category: 'تريلر رسمي',
              streamUrl: movie.servers[0].stream_url
            });
          }
        }
      };
    }

    // Direct Watch Button (Scrolls to servers or plays first server)
    const watchBtn = document.getElementById('md-watch-btn');
    if (watchBtn) {
      watchBtn.onclick = () => {
        const serversSec = document.getElementById('md-servers-section');
        if (serversSec) {
          serversSec.scrollIntoView({ behavior: 'smooth' });
        }
      };
    }

    // Favorite Button Action (Persists in localStorage)
    const favBtn = document.getElementById('md-fav-btn');
    if (favBtn) {
      let favs = [];
      try {
        favs = JSON.parse(localStorage.getItem('atube_favorites') || '[]');
      } catch (e) {}
      const isFav = favs.some(f => f.id === movie.id);
      favBtn.innerHTML = isFav
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="#ff2a44"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg><span style="color:#ff2a44;">في المفضلة ✓</span>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg><span>إضافة للمفضلة</span>`;

      favBtn.onclick = () => {
        let currentFavs = [];
        try {
          currentFavs = JSON.parse(localStorage.getItem('atube_favorites') || '[]');
        } catch (e) {}
        const idx = currentFavs.findIndex(f => f.id === movie.id);
        if (idx >= 0) {
          currentFavs.splice(idx, 1);
          favBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg><span>إضافة للمفضلة</span>`;
        } else {
          currentFavs.push({
            id: movie.id,
            title: movie.title,
            arabic_title: movie.arabic_title,
            poster: movie.poster,
            rating: movie.rating,
            quality: movie.quality,
            category: movie.category,
            content_type: movie.content_type
          });
          favBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="#ff2a44"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg><span style="color:#ff2a44;">في المفضلة ✓</span>`;
        }
        localStorage.setItem('atube_favorites', JSON.stringify(currentFavs));
      };
    }

    // Synopsis
    const synopsisEl = document.getElementById('md-synopsis');
    if (synopsisEl) {
      synopsisEl.textContent = movie.synopsis || 'تفاصيل وقصة الفيلم قيد التحميل...';
    }

    // Cast & Crew Pills
    const castContainer = document.getElementById('md-cast-list');
    if (castContainer) {
      castContainer.innerHTML = '';
      const castList = movie.cast || [];
      castList.forEach(actor => {
        const card = document.createElement('div');
        card.className = 'actor-pill-card dpad-focusable';
        card.tabIndex = 0;
        card.innerHTML = `
          <div class="actor-photo-circle">
            <img src="${actor.photo}" alt="${actor.name}" onerror="this.src='https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80'">
          </div>
          <div class="actor-names-col">
            <span class="actor-name-text">${actor.name}</span>
            <span class="actor-role-text">${actor.role || actor.arabic_name || ''}</span>
          </div>
        `;
        castContainer.appendChild(card);
      });
    }

    // Handle Seasons & Episodes for Series, Anime & Shows
    const seriesHub = document.getElementById('md-series-hub');
    const seasonsContainer = document.getElementById('md-seasons-pills');
    const episodesTrack = document.getElementById('md-episodes-track');
    const serversContainer = document.getElementById('md-servers-list');

    if (movie.seasons && movie.seasons.length > 0) {
      if (seriesHub) seriesHub.style.display = 'block';

      function renderSeason(seasonIndex) {
        if (!seasonsContainer || !episodesTrack) return;
        seasonsContainer.innerHTML = '';
        movie.seasons.forEach((season, sIdx) => {
          const pill = document.createElement('button');
          pill.className = `season-pill dpad-focusable ${sIdx === seasonIndex ? 'active' : ''}`;
          pill.textContent = season.title || `الموسم ${season.season_number}`;
          pill.onclick = () => renderSeason(sIdx);
          seasonsContainer.appendChild(pill);
        });

        const activeSeason = movie.seasons[seasonIndex];
        episodesTrack.innerHTML = '';
        const episodes = activeSeason.episodes || [];

        function selectEpisode(ep) {
          // Highlight active episode
          const epCards = episodesTrack.querySelectorAll('.episode-card');
          epCards.forEach(c => c.classList.remove('active'));

          // Render servers for this episode
          renderServersList(ep.servers || [], `${movie.title} - ${ep.title}`);
        }

        episodes.forEach((ep, epIdx) => {
          const epCard = document.createElement('div');
          epCard.className = `episode-card dpad-focusable ${epIdx === 0 ? 'active' : ''}`;
          epCard.tabIndex = 0;
          epCard.innerHTML = `
            <div class="episode-thumb-wrapper">
              <img src="${ep.thumbnail || movie.poster}" alt="${ep.title}" loading="lazy">
              <span class="episode-duration-tag">${ep.duration || '45 دقيقة'}</span>
            </div>
            <div class="episode-info-box">
              <div class="episode-num-title">${ep.title || `الحلقة ${ep.episode_number}`}</div>
              <div class="episode-server-count">${(ep.servers || []).length} سيرفرات مشاهدة</div>
            </div>
          `;
          epCard.onclick = () => {
            epCard.classList.add('active');
            selectEpisode(ep);
          };
          episodesTrack.appendChild(epCard);
        });

        if (episodes.length > 0) {
          selectEpisode(episodes[0]);
        }
      }

      renderSeason(0);
    } else {
      if (seriesHub) seriesHub.style.display = 'none';
      renderServersList(movie.servers || [], movie.title);
    }

    function renderServersList(servers, mediaTitle) {
      if (!serversContainer) return;
      serversContainer.innerHTML = '';
      
      let allServers = [...(servers || [])];

      // Extract TMDB ID from id field - look for 4-8 digit number anywhere (not just year)
      // Avoid matching the 4-digit year at end like "2024" by requiring non-year context
      const tmdbIdMatch = movie.id && movie.id.match(/(?:series|movie|anime|film)-(\d{4,8})-/);
      const tmdbId = movie.tmdb_id || (tmdbIdMatch ? tmdbIdMatch[1] : null);

      // For series: if no top-level servers, check episode-level servers to see if any exist
      if ((movie.content_type === 'series' || movie.content_type === 'anime') && allServers.length === 0) {
        const firstSeason = movie.seasons && movie.seasons[0];
        const firstEp = firstSeason && firstSeason.episodes && firstSeason.episodes[0];
        if (firstEp && firstEp.servers && firstEp.servers.length > 0) {
          // Series has episode-level servers - inject them as top-level for display
          allServers = firstEp.servers.map(s => ({ ...s, isEmbed: !!(s.stream_url && s.stream_url.includes('/embed/')) }));
        }
      }

      // Auto-add embed servers if we have any valid embed URLs or TMDB id
      const hasEmbedInServers = allServers.some(s => s.stream_url && (
        s.stream_url.includes('vidsrc') || s.stream_url.includes('2embed') || 
        s.stream_url.includes('/embed/')
      ));

      // If servers already have embed URLs, mark them as embeds
      allServers = allServers.map(srv => ({
        ...srv,
        isEmbed: !!(srv.isEmbed || (srv.stream_url && (
          srv.stream_url.includes('vidlink') || srv.stream_url.includes('multiembed') ||
          srv.stream_url.includes('vidsrc') || srv.stream_url.includes('/embed/')
        )))
      }));

      // Add standardized 5-server cluster if available and not already there
      const targetIdentifier = tmdbId || movie.imdb_id;
      if (targetIdentifier && !hasEmbedInServers) {
        const isTV = movie.content_type === 'series' || movie.content_type === 'anime';
        const vidlinkEmbed = isTV 
          ? `https://vidlink.pro/tv/${targetIdentifier}/1/1?primaryColor=00e5ff&secondaryColor=ff0055`
          : `https://vidlink.pro/movie/${targetIdentifier}?primaryColor=00e5ff&secondaryColor=ff0055`;
        const multiEmbedUrl = isTV
          ? `https://multiembed.mov/?video_id=${targetIdentifier}&s=1&e=1`
          : `https://multiembed.mov/?video_id=${targetIdentifier}&tmdb=1`;
        const vidsrcEmbed = isTV
          ? `https://vidsrc.pm/embed/tv/${targetIdentifier}/1/1`
          : `https://vidsrc.pm/embed/movie/${targetIdentifier}`;

        allServers.push({
          site: 'Vipserver',
          quality: '1080p FHD',
          name: 'سيرفر Vipserver (سريع FHD • إيجي بست)',
          stream_url: vidlinkEmbed,
          badge: 'VIP ⭐ (إيجي بست)',
          isEmbed: true
        });
        allServers.push({
          site: 'Mixdrop',
          quality: '1080p HD',
          name: 'سيرفر Mixdrop (سحابي سريع)',
          stream_url: multiEmbedUrl,
          badge: 'Mixdrop',
          isEmbed: true
        });
        allServers.push({
          site: 'Hgcloud',
          quality: '1080p HD',
          name: 'سيرفر Hgcloud (سحابي مباشر)',
          stream_url: vidsrcEmbed,
          badge: 'Hgcloud ⚡',
          isEmbed: true
        });
        allServers.push({
          site: 'Minochinos',
          quality: '1080p HD',
          name: 'سيرفر Minochinos (بديل فائق)',
          stream_url: multiEmbedUrl,
          badge: 'Minochinos',
          isEmbed: true
        });
        allServers.push({
          site: 'Vidmoly',
          quality: '1080p HD',
          name: 'سيرفر Vidmoly (مشاهدة بدون تقطيع)',
          stream_url: vidlinkEmbed,
          badge: 'Vidmoly',
          isEmbed: true
        });
      } else if (!targetIdentifier && !hasEmbedInServers && allServers.length === 0) {
        const searchTitle = encodeURIComponent(movie.title || movie.arabic_title || '');
        const isTV = movie.content_type === 'series' || movie.content_type === 'anime';
        if (searchTitle) {
          allServers.push({
            site: 'Vipserver',
            quality: '1080p FHD',
            name: 'سيرفر Vipserver (سحابي دولي)',
            stream_url: `https://vidlink.pro/${isTV ? 'tv' : 'movie'}/${searchTitle}`,
            badge: 'VIP ⭐',
            isEmbed: true
          });
          allServers.push({
            site: 'Mixdrop',
            quality: '1080p HD',
            name: 'سيرفر Mixdrop (سيرفر بديل)',
            stream_url: `https://multiembed.mov/?video_id=${searchTitle}`,
            badge: 'Mixdrop',
            isEmbed: true
          });
        }
      }

      if (allServers.length === 0) {
        serversContainer.innerHTML = '<div style="color: #94a3b8; padding: 12px;">جاري تحديث السيرفرات السحابية لهذا العمل...</div>';
        return;
      }

      allServers.forEach((srv, idx) => {
        const btn = document.createElement('button');
        btn.className = 'server-card-btn dpad-focusable';
        btn.tabIndex = 0;

        const quality = srv.quality || '1080p';
        const serverBadge = srv.badge || (idx === 0 ? 'A Tube VIP' : 'A Tube Cloud');
        const serverTitle = srv.name || `سيرفر A Tube فائق السرعة - ${quality} (سيرفر ${idx + 1})`;

        btn.innerHTML = `
          <div style="display: flex; flex-direction: column; gap: 2px;">
            <span class="server-site-badge">${serverBadge}</span>
            <span class="server-name-label">${serverTitle}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 6px;">
            <span class="server-quality-tag">${quality}</span>
            <span style="color: var(--primary-cyan); font-size: 16px;">▶</span>
          </div>
        `;

        btn.onclick = () => {
          closeModal();
          const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
          if (player && typeof player.playMedia === 'function') {
            player.playMedia({
              name: `${mediaTitle} - ${serverTitle}`,
              title: mediaTitle,
              category: movie.category_name || movie.category || 'A Tube Ultra HD',
              streamUrl: srv.url || srv.stream_url,
              isEmbed: !!srv.isEmbed,
              servers: allServers.map(s => ({
                name: s.name,
                url: s.url || s.stream_url,
                is_hls: s.is_hls,
                isEmbed: !!s.isEmbed
              })),
              content_type: movie.content_type
            });
          }
        };

        serversContainer.appendChild(btn);
      });

      // Universal Deep-Search Fallback Action Button
      const deepSearchBtn = document.createElement('button');
      deepSearchBtn.className = 'server-card-btn dpad-focusable deep-search-trigger-btn';
      deepSearchBtn.style.cssText = 'background: rgba(0, 229, 255, 0.08); border: 1px dashed rgba(0, 229, 255, 0.4); justify-content: center;';
      deepSearchBtn.tabIndex = 0;
      deepSearchBtn.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-size: 16px;">🔍</span>
          <span style="color: var(--primary-cyan); font-weight: 700;">بحث تلقائي في محركات البحث عن سيرفرات إضافية</span>
        </div>
      `;

      deepSearchBtn.onclick = async () => {
        deepSearchBtn.innerHTML = `<span>⏳ جاري البحث عبر Google / DuckDuckGo / Bing...</span>`;
        try {
          const title = movie.title || movie.arabic_title || '';
          const year = movie.year || '';
          const res = await fetch(`/api/stream/deep-search?title=${encodeURIComponent(title)}&year=${encodeURIComponent(year)}&type=${encodeURIComponent(movie.content_type || 'movie')}`);
          if (res.ok) {
            const data = await res.json();
            if (data && data.found && data.server) {
              const srv = data.server;
              deepSearchBtn.style.display = 'none';
              const newBtn = document.createElement('button');
              newBtn.className = 'server-card-btn dpad-focusable';
              newBtn.style.borderColor = '#00e5ff';
              newBtn.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 2px;">
                  <span class="server-site-badge">${srv.badge || 'بديل ذكي ⚡'}</span>
                  <span class="server-name-label">${srv.name}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span class="server-quality-tag">${srv.quality || '1080p'}</span>
                  <span style="color: var(--primary-cyan); font-size: 16px;">▶</span>
                </div>
              `;
              newBtn.onclick = () => {
                closeModal();
                const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
                if (player && typeof player.playMedia === 'function') {
                  player.playMedia({
                    name: `${mediaTitle} - ${srv.name}`,
                    title: mediaTitle,
                    category: movie.category_name || movie.category || 'A Tube Ultra HD',
                    streamUrl: srv.url || srv.stream_url,
                    isEmbed: !!srv.isEmbed,
                    servers: [srv],
                    content_type: movie.content_type
                  });
                }
              };
              serversContainer.appendChild(newBtn);
              return;
            }
          }
          deepSearchBtn.innerHTML = `<span style="color: #ff3344;">❌ محتوى غير متاح حالياً - تم البحث في كافة المصادر البديلة</span>`;
        } catch (e) {
          deepSearchBtn.innerHTML = `<span style="color: #ff3344;">❌ خطأ في الاتصال بمحرك البحث</span>`;
        }
      };

      serversContainer.appendChild(deepSearchBtn);
    }

    // Stills Gallery
    const stillsContainer = document.getElementById('md-stills-list');
    if (stillsContainer) {
      stillsContainer.innerHTML = '';
      const stills = movie.stills && movie.stills.length > 0 ? movie.stills : [movie.poster, movie.backdrop].filter(Boolean);
      if (stills.length === 0) {
        // Hide the stills section
        stillsContainer.parentElement.style.display = 'none';
      } else {
        stillsContainer.parentElement.style.display = '';
        stills.forEach(stillUrl => {
          if (!stillUrl || stillUrl.includes('undefined')) return;
          const item = document.createElement('div');
          item.className = 'still-thumb-item dpad-focusable';
          item.tabIndex = 0;
          item.innerHTML = `<img src="${stillUrl}" alt="مشهد من العمل" loading="lazy" onerror="this.style.display='none'">`;
          stillsContainer.appendChild(item);
        });
      }
    }
  }

  function getFallbackMovie(id) {
    if (id && id.includes('girl')) {
      return {
        id: "the-girl-in-the-river-2026",
        title: "The Girl in the River",
        arabic_title: "الفتاة في النهر",
        year: "2026",
        rating: "4.1 / 10 IMDb",
        duration: "92 دقيقة",
        quality: "WEB-DL - 720p / 1080p",
        language: "الإنجليزية",
        translation: "مترجم للعربية",
        production: "الولايات المتحدة الأمريكية",
        genres: ["غموض", "دراما", "جريمة"],
        poster: "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=500&q=80",
        backdrop: "https://images.unsplash.com/photo-1518173946687-a4c8a383392e?w=1200&q=80",
        synopsis: "يقدم فيلم الجريمة والغموض والإثارة 'الفتاة في النهر' (The Girl in the River) قصة بوليسية مشحونة بالتوتر والترقب المستمر، حيث يغوص في العقول المظلمة للقتلة المتسلسلين وصراعات المحققين.",
        trailer_youtube_id: "kJQP7kiw5Fk",
        cast: [
          { name: "Devon Sawa", role: "Alan Kramer", photo: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&q=80" },
          { name: "Maggie Grace", role: "Amelia Pambrock", photo: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&q=80" },
          { name: "Tiffany Haddish", role: "Erica Grissom", photo: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&q=80" },
          { name: "Ralph Macchio", role: "Sheriff Miller", photo: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&q=80" }
        ],
        stills: [
          "https://images.unsplash.com/photo-1478760329108-5c3ed9d495a0?w=400&q=80",
          "https://images.unsplash.com/photo-1518173946687-a4c8a383392e?w=400&q=80"
        ],
        servers: [
          { site: "A Tube Cloud", quality: "1080p FHD", name: "سيرفر A Tube فائق السرعة - 1080p", stream_url: "https://flu.systemnet.tv/CBCDrama/index.m3u8", badge: "A Tube VIP" },
          { site: "A Tube Cloud", quality: "1080p", name: "سيرفر A Tube السحابي - 1080p", stream_url: "https://flu.systemnet.tv/CBC/index.m3u8", badge: "A Tube Cloud" },
          { site: "A Tube Cloud", quality: "720p", name: "سيرفر A Tube السريع - 720p", stream_url: "https://eazyvwqssi.erbvr.com/alghadtv/alghadtv.m3u8", badge: "A Tube Fast" },
          { site: "A Tube Cloud", quality: "4K UHD", name: "سيرفر A Tube 4K فائق السرعة", stream_url: "https://static.france24.com/live/F24_AR_HI_HLS/live_tv.m3u8", badge: "A Tube 4K" }
        ]
      };
    }
    return null;
  }

  return {
    init,
    open,
    close: closeModal,
    isOpen: () => modalEl && modalEl.classList.contains('active')
  };
})();

// Explicit window and global binding for universal access
if (typeof window !== 'undefined') {
  window.MovieDetails = MovieDetails;
}
if (typeof globalThis !== 'undefined') {
  globalThis.MovieDetails = MovieDetails;
}

