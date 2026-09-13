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

  // Resolve whether a media object represents an episodic series
  function isSeriesMedia(movie) {
    const ct = (movie && movie.content_type) || '';
    return ct === 'series' || ct === 'anime' || ct === 'tv_show'
      || (movie && movie.total_seasons > 0)
      || (movie && Array.isArray(movie.seasons) && movie.seasons.length > 0);
  }

  // Fetch cast/crew for a media id from /api/media/cast
  async function fetchCastForMedia(mediaId) {
    if (!mediaId || window.location.protocol === 'file:') return null;
    try {
      const res = await fetch(`/api/media/cast?id=${encodeURIComponent(mediaId)}`);
      if (res.ok) return await res.json();
    } catch (_) {}
    return null;
  }

  // Fetch episodes for a season from /api/media/episodes
  async function fetchEpisodesForMedia(mediaId, season) {
    if (!mediaId || window.location.protocol === 'file:') return null;
    try {
      const res = await fetch(`/api/media/episodes?id=${encodeURIComponent(mediaId)}&season=${encodeURIComponent(season)}`);
      if (res.ok) return await res.json();
    } catch (_) {}
    return null;
  }

  // Merge freshly-fetched API details into currentMovie without wiping
  // client-side seasons/cast, and hydrate cast + episodes from dedicated endpoints.
  async function mergeFromApi(freshData) {
    if (!currentMovie || !freshData || !freshData.id) return;
    const merged = { ...currentMovie, ...freshData };

    // Guard against empty API arrays wiping existing client data
    if (!Array.isArray(freshData.seasons) || freshData.seasons.length === 0) {
      merged.seasons = currentMovie.seasons && currentMovie.seasons.length ? currentMovie.seasons : [];
    }
    if (!Array.isArray(freshData.cast) || freshData.cast.length === 0) {
      merged.cast = currentMovie.cast && currentMovie.cast.length ? currentMovie.cast : [];
    }

    // Hydrate cast from /api/media/cast (single source of truth for طاقم العمل)
    if ((!Array.isArray(merged.cast) || merged.cast.length === 0)) {
      const castRes = await fetchCastForMedia(merged.id);
      if (castRes && Array.isArray(castRes.cast) && castRes.cast.length > 0) {
        merged.cast = castRes.cast;
      }
    }

    // Hydrate episodes for series from /api/media/episodes
    if (isSeriesMedia(merged) && (!Array.isArray(merged.seasons) || merged.seasons.length === 0)) {
      const builtSeasons = [];
      const totalSeasons = merged.total_seasons || 1;
      for (let s = 1; s <= Math.max(totalSeasons, 1); s++) {
        const epRes = await fetchEpisodesForMedia(merged.id, s);
        if (epRes && Array.isArray(epRes.episodes) && epRes.episodes.length > 0) {
          builtSeasons.push({
            season_number: epRes.season_number || s,
            title: epRes.season_title || `الموسم ${s}`,
            episodes: epRes.episodes
          });
        } else {
          break;
        }
      }
      if (builtSeasons.length > 0) merged.seasons = builtSeasons;
    }

    currentMovie = merged;
    try { renderMovieDetails(merged); } catch (err) { console.error('render err:', err); }
    const rc = window.RemoteControl || (typeof RemoteControl !== 'undefined' ? RemoteControl : null);
    if (rc && typeof rc.refresh === 'function') setTimeout(() => rc.refresh(), 200);
  }

  // Open modal with movie data (either from object or fetched by id)
  async function open(movieOrId) {
    if (!modalEl) {
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
            if (freshData && freshData.id) mergeFromApi(freshData);
          })
          .catch(() => {});
      }
    } else if (movieOrId && typeof movieOrId === 'object') {
      currentMovie = movieOrId;

      const isFileProto = window.location.protocol === 'file:';
      const needsFetch = !isFileProto && movieOrId.id && (!movieOrId.servers || movieOrId.servers.length === 0);
      const needsSeriesEnhance = !isFileProto && movieOrId.id && (movieOrId.content_type === 'series' || movieOrId.content_type === 'anime' || movieOrId.content_type === 'tv_show') && (!movieOrId.seasons || movieOrId.seasons.length === 0);

      if (needsFetch || needsSeriesEnhance) {
        fetch(`/api/media/details?id=${encodeURIComponent(movieOrId.id)}`)
          .then(r => r.ok ? r.json() : null)
          .then(freshData => {
            if (freshData && freshData.id) mergeFromApi(freshData);
          })
          .catch(() => {});
      } else if (!isFileProto && movieOrId.id) {
        // Object already has servers; still hydrate cast + episodes from dedicated endpoints
        mergeFromApi(movieOrId);
      }
    }

    if (!currentMovie) return;

    try {
      renderMovieDetails(currentMovie);
    } catch (err) {
      console.error('Error in renderMovieDetails:', err);
    }

    // Hide main page views to make detail view a dedicated full in-page view
    const homeView = document.getElementById('home-page-view');
    const catView = document.getElementById('category-page-view');
    if (homeView) homeView.style.display = 'none';
    if (catView) catView.style.display = 'none';

    modalEl.classList.add('active');
    modalEl.style.display = 'block';

    // Update back button text based on context
    const backBtnText = document.querySelector('#movie-modal-back-btn span');
    if (backBtnText) {
      if (window.currentCategoryViewName) {
        backBtnText.textContent = `العودة إلى ${window.currentCategoryViewName}`;
      } else {
        backBtnText.textContent = 'العودة للرئيسية';
      }
    }

    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

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

    const homeView = document.getElementById('home-page-view');
    const catView = document.getElementById('category-page-view');

    // Restore previous view seamlessly
    if (window.currentCategoryViewName && catView) {
      catView.classList.remove('is-hidden');
      catView.style.display = 'block';
    } else if (homeView) {
      homeView.classList.remove('is-hidden');
      homeView.style.display = 'block';
    }

    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

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
        <div class="attr-item"><span class="attr-label">اللغة:</span> ${safeHtml(movie.language || 'الإنجليزية')}</div>
        <div class="attr-item"><span class="attr-label">الترجمة:</span> ${safeHtml(movie.translation || 'مترجم للعربية')}</div>
        <div class="attr-item"><span class="attr-label">السنة:</span> ${safeHtml(movie.year || '2026')}</div>
        <div class="attr-item"><span class="attr-label">المدة:</span> ${safeHtml(movie.duration || '92 دقيقة')}</div>
        <div class="attr-item"><span class="attr-label">الإنتاج:</span> ${safeHtml(movie.production || 'الولايات المتحدة')}</div>
      `;
    }

    // Genre Pills
    const genresContainer = document.getElementById('md-genres');
    if (genresContainer) {
      genresContainer.innerHTML = '';
      (movie.genres || ['غموض', 'دراما', 'جريمة']).forEach(g => {
        const pill = document.createElement('span');
        pill.className = 'movie-tag-pill';
        pill.textContent = decodeHtmlEntities(g);
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
              streamUrl: movie.servers[0].stream_url || movie.servers[0].url || ''
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

    // Dynamic Headings based on content type
    const isSeries = (
      movie.content_type === 'series' || 
      movie.content_type === 'anime' || 
      movie.content_type === 'tv_show' || 
      (movie.total_seasons && movie.total_seasons > 0) ||
      (Array.isArray(movie.seasons) && movie.seasons.length > 0)
    );

    const synopsisTitle = document.getElementById('md-synopsis-title');
    if (synopsisTitle) {
      synopsisTitle.textContent = isSeries ? '📖 قصة المسلسل' : '📖 قصة الفيلم';
    }

    const stillsTitle = document.getElementById('md-stills-title');
    if (stillsTitle) {
      stillsTitle.textContent = isSeries ? '📸 لقطات من العمل' : '📸 لقطات من الفيلم';
    }

    const castTitle = document.getElementById('md-cast-title');
    if (castTitle) {
      castTitle.textContent = isSeries ? '🌟 طاقم العمل ونجوم المسلسل' : '🌟 طاقم العمل والبطولة';
    }

    // Synopsis
    const synopsisEl = document.getElementById('md-synopsis');
    if (synopsisEl) {
      synopsisEl.textContent = decodeHtmlEntities(movie.synopsis) || (isSeries ? 'تفاصيل وقصة المسلسل قيد التحديث...' : 'تفاصيل وقصة الفيلم قيد التحديث...');
    }

    // Cast & Crew Pills - populated from /api/media/cast
    const castContainer = document.getElementById('md-cast-list');
    if (castContainer) {
      castContainer.innerHTML = '';
      let castList = movie.cast || [];

      function renderCastCards(actors) {
        castContainer.innerHTML = '';
        if (!actors || actors.length === 0) {
          castContainer.innerHTML = '<div style="color:#94a3b8;font-size:13px;padding:8px 0;">✨ جاري تحديث بيانات طاقم التمثيل من قاعدة البيانات...</div>';
          return;
        }
        actors.forEach(actor => {
          const card = document.createElement('div');
          card.className = 'actor-pill-card dpad-focusable';
          card.tabIndex = 0;
          const photoUrl = actor.photo ? decodeHtmlEntities(actor.photo) : '';
          const fallbackPhoto = photoUrl || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80';
          card.innerHTML = `
            <div class="actor-photo-circle">
              <img src="${escapeHtml(fallbackPhoto)}" alt="${safeHtml(actor.name)}" onerror="this.src='https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&q=80'">
            </div>
            <div class="actor-names-col">
              <span class="actor-name-text">${safeHtml(actor.name || actor.arabic_name || '')}</span>
              <span class="actor-role-text">${safeHtml(actor.character_name || actor.role || actor.arabic_name || 'ممثل')}</span>
            </div>
          `;
          castContainer.appendChild(card);
        });
      }

      if (castList.length > 0) {
        renderCastCards(castList);
      } else if (movie.id && window.location.protocol !== 'file:') {
        castContainer.innerHTML = '<div style="color:#94a3b8;font-size:13px;padding:8px 0;">✨ جاري جلب نجوم العمل...</div>';
        fetch(`/api/media/cast?id=${encodeURIComponent(movie.id)}`)
          .then(r => r.ok ? r.json() : null)
          .then(castData => {
            if (castData && Array.isArray(castData.cast) && castData.cast.length > 0) {
              movie.cast = castData.cast;
              renderCastCards(castData.cast);
            } else {
              renderCastCards([]);
            }
          })
          .catch(() => renderCastCards([]));
      } else {
        renderCastCards([]);
      }
    }

    // Handle Seasons & Episodes for Series, Anime & Shows
    const seriesHub = document.getElementById('md-series-hub');
    const seasonsContainer = document.getElementById('md-seasons-pills');
    const episodesTrack = document.getElementById('md-episodes-track');
    const serversContainer = document.getElementById('md-servers-list');

    if (isSeries && movie.seasons && movie.seasons.length > 0) {
      if (seriesHub) seriesHub.style.display = 'block';

      function renderSeason(seasonIndex) {
        if (!seasonsContainer || !episodesTrack) return;
        seasonsContainer.innerHTML = '';
        movie.seasons.forEach((season, sIdx) => {
          const pill = document.createElement('button');
          pill.className = `season-pill dpad-focusable ${sIdx === seasonIndex ? 'active' : ''}`;
          pill.textContent = season.title || `الموسم ${season.season_number || (sIdx + 1)}`;
          pill.onclick = () => renderSeason(sIdx);
          seasonsContainer.appendChild(pill);
        });

        const activeSeason = movie.seasons[seasonIndex] || movie.seasons[0];
        episodesTrack.innerHTML = '';
        const episodes = activeSeason.episodes || [];

        // Strict Numerical order: Episode 1, 2, 3, 4... N
        episodes.sort((a, b) => (parseInt(a.episode_number || 0) - parseInt(b.episode_number || 0)));

        function selectEpisode(ep) {
          const epCards = episodesTrack.querySelectorAll('.episode-card');
          epCards.forEach(c => c.classList.remove('active'));

          const serversTitle = document.querySelector('#md-servers-section .servers-hub-title span');
          if (serversTitle) {
            serversTitle.textContent = `سيرفرات مشاهدة وتحميل: ${movie.arabic_title || movie.title} - ${ep.title || 'الحلقة ' + ep.episode_number}`;
          }

          renderServersList(ep.servers && ep.servers.length > 0 ? ep.servers : movie.servers || [], `${movie.title} - ${ep.title || 'الحلقة ' + ep.episode_number}`);
        }

        episodes.forEach((ep, epIdx) => {
          const epCard = document.createElement('div');
          epCard.className = `episode-card dpad-focusable ${epIdx === 0 ? 'active' : ''}`;
          epCard.tabIndex = 0;
          epCard.innerHTML = `
            <div class="episode-thumb-wrapper">
              <img src="${ep.thumbnail || movie.poster}" alt="${ep.title}" loading="lazy" onerror="this.src='${movie.poster}'">
              <span class="episode-duration-tag">${ep.duration || '45 دقيقة'}</span>
            </div>
            <div class="episode-info-box">
              <div class="episode-num-title">${ep.title || `الحلقة ${ep.episode_number}`}</div>
              <div class="episode-server-count">${ep.air_date ? '📅 ' + ep.air_date : '⚡ 1080p FHD'}</div>
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

      const serversTitle = document.querySelector('#md-servers-section .servers-hub-title span');
      if (serversTitle) {
        serversTitle.textContent = `سيرفرات المشاهدة والتحميل المباشر - ${mediaTitle || movie.arabic_title || movie.title || 'A Tube Ultra HD'}`;
      }
      
      let allServers = [...(servers || [])];
      if (allServers.length === 0) {
        allServers = [
          { site: 'A Tube VIP', quality: '1080p FHD', stream_url: '', badge: 'VIP Fast ⚡' },
          { site: 'A Tube Cloud', quality: '720p HD', stream_url: '', badge: 'توفير باقة' }
        ];
      }

      // 1. Direct Streaming Section (Watch Online)
      const watchBlock = document.createElement('div');
      watchBlock.className = 'servers-sub-block';
      watchBlock.style.marginBottom = '20px';
      watchBlock.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
          <span style="font-size: 18px;">▶</span>
          <h4 style="margin: 0; font-size: 15px; color: var(--primary-cyan); font-weight: 700;">سيرفرات المشاهدة المباشرة (فائقة السرعة وبدون إعلانات):</h4>
        </div>
      `;
      const watchGrid = document.createElement('div');
      watchGrid.className = 'servers-grid-layout';

      // 2. Direct Downloads Section (Download Links with MB/GB sizes)
      const downloadBlock = document.createElement('div');
      downloadBlock.className = 'servers-sub-block download-sub-block';
      downloadBlock.style.marginTop = '24px';
      downloadBlock.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
          <span style="font-size: 18px;">📥</span>
          <h4 style="margin: 0; font-size: 15px; color: #10b981; font-weight: 700;">روابط التحميل المباشر وحفظ الفيديو (Download Links):</h4>
        </div>
      `;
      const downloadGrid = document.createElement('div');
      downloadGrid.className = 'servers-grid-layout';

      const qualitySizes = [
        { quality: '1080p FHD', size: '1.4 GB', tagClass: 'quality-1080p' },
        { quality: '720p HD', size: '680 MB', tagClass: 'quality-720p' },
        { quality: '480p SD', size: '320 MB', tagClass: 'quality-default' }
      ];

      allServers.forEach((srv, idx) => {
        const qInfo = qualitySizes[idx % qualitySizes.length];
        const quality = srv.quality || qInfo.quality;
        const sizeTag = srv.size || qInfo.size;
        const serverBadge = srv.badge || (idx === 0 ? 'A Tube VIP' : 'A Tube Fast');
        const serverTitle = `سيرفر مشاهدة ${idx + 1} - A Tube Direct`;

        // Watch Online Button
        const watchBtn = document.createElement('button');
        watchBtn.className = 'server-card-btn dpad-focusable';
        watchBtn.tabIndex = 0;
        watchBtn.innerHTML = `
          <div style="display: flex; flex-direction: column; gap: 2px;">
            <span class="server-site-badge">${serverBadge}</span>
            <span class="server-name-label">${serverTitle}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="server-size-tag">${sizeTag}</span>
            <span class="server-quality-tag ${qInfo.tagClass}">${quality}</span>
            <span style="color: var(--primary-cyan); font-size: 16px;">▶</span>
          </div>
        `;
        watchBtn.onclick = () => {
          closeModal();
          const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
          if (player && typeof player.playMedia === 'function') {
            player.playMedia({
              name: `${mediaTitle} (${quality})`,
              title: mediaTitle,
              category: movie.category_name || movie.category || 'A Tube Ultra HD',
              streamUrl: srv.url || srv.stream_url,
              quality: quality,
              content_type: movie.content_type
            });
          }
        };
        watchGrid.appendChild(watchBtn);

        // Download Link Button
        const dlBtn = document.createElement('button');
        dlBtn.className = 'server-card-btn download-btn dpad-focusable';
        dlBtn.tabIndex = 0;
        dlBtn.innerHTML = `
          <div style="display: flex; flex-direction: column; gap: 2px;">
            <span class="server-site-badge download-badge">تحميل مباشر 📥</span>
            <span class="server-name-label">تحميل بدقة (${quality})</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="server-size-tag">${sizeTag}</span>
            <span class="server-quality-tag ${qInfo.tagClass}">${quality}</span>
            <span style="color: #10b981; font-size: 16px;">⬇</span>
          </div>
        `;
        dlBtn.onclick = () => {
          const rawUrl = srv.url || srv.stream_url;
          if (rawUrl && (rawUrl.startsWith('http://') || rawUrl.startsWith('https://'))) {
            window.open(rawUrl, '_blank');
          } else {
            alert('⚡ جاري فك وتجهيز رابط التحميل السحابي المباشر...');
          }
        };
        downloadGrid.appendChild(dlBtn);
      });

      watchBlock.appendChild(watchGrid);
      downloadBlock.appendChild(downloadGrid);

      serversContainer.appendChild(watchBlock);
      serversContainer.appendChild(downloadBlock);
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

    // Render "More Like This" (أعمال مشابهة)
    renderMoreLikeThis(movie);
  }

  function renderMoreLikeThis(movie) {
    let container = document.getElementById('md-similar-container');
    if (!container) {
      const modalBody = document.querySelector('.movie-details-body') || document.getElementById('md-servers-section')?.parentElement;
      if (!modalBody) return;
      const section = document.createElement('div');
      section.className = 'similar-movies-section';
      section.innerHTML = `
        <div class="similar-header">
          <h3 class="similar-title">
            <span>✨ أعمال قد تنال إعجابك (More Like This)</span>
          </h3>
        </div>
        <div id="md-similar-container" class="similar-track"></div>
      `;
      modalBody.appendChild(section);
      container = document.getElementById('md-similar-container');
    }

    if (!container || !window.MediaCatalog) return;
    container.innerHTML = '';
    const all = MediaCatalog.getAll() || [];
    const targetGenre = (movie.genres && movie.genres[0]) || '';
    const targetCat = movie.category || '';

    const similar = all.filter(m => {
      if (m.id === movie.id) return false;
      const genreMatch = targetGenre && m.genres && m.genres.some(g => String(g).includes(targetGenre));
      const catMatch = targetCat && m.category === targetCat;
      return (genreMatch || catMatch) && m.poster;
    }).slice(0, 8);

    if (similar.length === 0) {
      container.parentElement.style.display = 'none';
      return;
    }
    container.parentElement.style.display = '';

    similar.forEach(sim => {
      const card = document.createElement('div');
      card.className = 'similar-card dpad-focusable';
      card.tabIndex = 0;
      card.innerHTML = `
        <img src="${sim.poster}" alt="${safeHtml(sim.title)}" loading="lazy" class="similar-thumb" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 130 190\\' fill=\\'%2308101a\\'/%3E'">
        <div class="similar-card-info">
          <div class="similar-card-title">${safeHtml(sim.arabic_title || sim.title)}</div>
          <div class="similar-card-badge">${safeHtml(sim.rating || '★ 8.5')}</div>
        </div>
      `;
      card.addEventListener('click', () => {
        open(sim);
      });
      container.appendChild(card);
    });
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

