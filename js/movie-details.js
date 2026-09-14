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

    // Actor filmography modal close listeners
    const actorModal = document.getElementById('actor-filmography-modal');
    const closeActorBtn = document.getElementById('close-actor-modal-btn');
    if (closeActorBtn && actorModal) {
      closeActorBtn.addEventListener('click', () => {
        actorModal.classList.remove('active');
        actorModal.style.display = 'none';
        const rc = window.RemoteControl || (typeof RemoteControl !== 'undefined' ? RemoteControl : null);
        if (rc && typeof rc.refreshFocusableElements === 'function') rc.refreshFocusableElements();
      });
    }
    if (actorModal) {
      actorModal.addEventListener('click', (e) => {
        if (e.target === actorModal) {
          actorModal.classList.remove('active');
          actorModal.style.display = 'none';
          const rc = window.RemoteControl || (typeof RemoteControl !== 'undefined' ? RemoteControl : null);
          if (rc && typeof rc.refreshFocusableElements === 'function') rc.refreshFocusableElements();
        }
      });
    }
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

    // Save previous scroll position before opening details view
    window.previousScrollY = window.scrollY || document.documentElement.scrollTop || 0;

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

    // Also close actor filmography modal if open
    const actorModal = document.getElementById('actor-filmography-modal');
    if (actorModal) {
      actorModal.classList.remove('active');
      actorModal.style.display = 'none';
    }

    // When returning from Movie Details, return to the Movies category view, NOT Home!
    const targetCat = window.currentCategoryViewName || (currentMovie && (currentMovie.category_name || currentMovie.category)) || 'أفلام أجنبي';

    if (window.showCategoryView && typeof window.showCategoryView === 'function') {
      window.showCategoryView(targetCat);
    } else {
      const homeView = document.getElementById('home-page-view');
      const catView = document.getElementById('category-page-view');
      if (catView) {
        catView.classList.remove('is-hidden');
        catView.style.display = 'block';
      }
      if (homeView) {
        homeView.classList.add('is-hidden');
        homeView.style.display = 'none';
      }
    }

    const restoreY = window.previousScrollY || 0;
    window.scrollTo(0, restoreY);
    document.documentElement.scrollTop = restoreY;
    document.body.scrollTop = restoreY;

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

    // Trailer Button Action (Plays official trailer seamlessly inside InAppPlayer)
    const trailerBtn = document.getElementById('md-trailer-btn');
    if (trailerBtn) {
      trailerBtn.onclick = () => {
        const ytId = movie.trailer_youtube_id;
        const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
        if (player && typeof player.playMedia === 'function') {
          if (ytId) {
            player.playMedia({
              name: `الإعلان الرسمي: ${movie.arabic_title || movie.title}`,
              category: 'برومو وتريلر سينمائي 🎬',
              streamUrl: `https://www.youtube.com/embed/${ytId}?autoplay=1&rel=0`
            });
          } else if (movie.servers && movie.servers.length > 0) {
            player.playMedia({
              name: `إعلان: ${movie.arabic_title || movie.title}`,
              category: 'تريلر رسمي 🎬',
              streamUrl: movie.servers[0].stream_url || movie.servers[0].url || ''
            });
          }
        }
      };
    }

    // Direct Watch Button (Launches Video Player immediately without forcing manual server picking)
    const watchBtn = document.getElementById('md-watch-btn');
    if (watchBtn) {
      watchBtn.onclick = () => {
        closeModal();
        const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
        if (player && typeof player.playMedia === 'function') {
          player.playMedia(movie);
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

    // Share Button
    const shareBtn = document.getElementById('md-share-btn');
    if (shareBtn) {
      shareBtn.onclick = () => {
        const shareUrl = `${window.location.origin}${window.location.pathname}?play=${movie.id}`;
        if (navigator.share) {
          navigator.share({
            title: movie.arabic_title || movie.title,
            text: `شاهد "${movie.arabic_title || movie.title}" بجودة Ultra HD على A TuBe:`,
            url: shareUrl
          }).catch(() => {});
        } else if (navigator.clipboard) {
          navigator.clipboard.writeText(shareUrl).then(() => {
            alert('تم نسخ رابط العمل لمشاركته بنجاح! 🔗\n' + shareUrl);
          }).catch(() => {
            prompt('انسخ الرابط التالي:', shareUrl);
          });
        } else {
          prompt('انسخ الرابط التالي:', shareUrl);
        }
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
          card.title = `استكشف أعمال ${actor.name || actor.arabic_name || ''}`;
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
            <div class="actor-explore-arrow" aria-hidden="true">‹</div>
          `;
          const handleOpenActor = () => {
            openActorFilmography(actor);
          };
          card.addEventListener('click', handleOpenActor);
          card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.keyCode === 13) {
              e.preventDefault();
              handleOpenActor();
            }
          });
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
            closeModal();
            const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
            if (player && typeof player.playMedia === 'function') {
              player.playMedia({
                ...movie,
                name: `${movie.title} - ${ep.title || 'الحلقة ' + ep.episode_number}`,
                title: `${movie.title} - ${ep.title || 'الحلقة ' + ep.episode_number}`,
                episode: ep.episode_number,
                season: activeSeason.season_number || (seasonIndex + 1),
                servers: ep.servers && ep.servers.length > 0 ? ep.servers : movie.servers,
                streamUrl: (ep.servers && ep.servers[0] && (ep.servers[0].url || ep.servers[0].stream_url)) || ''
              });
            }
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
      const watchGrid = document.getElementById('md-watch-grid');
      const downloadGrid = document.getElementById('md-download-grid');
      const loaderEl = document.getElementById('md-servers-loader');
      const headerTitleEl = document.getElementById('md-servers-header-title');

      if (!watchGrid || !downloadGrid) return;

      watchGrid.innerHTML = '';
      downloadGrid.innerHTML = '';
      if (loaderEl) loaderEl.classList.add('is-hidden');

      if (headerTitleEl) {
        headerTitleEl.textContent = `سيرفرات المشاهدة والتحميل - ${mediaTitle || movie.arabic_title || movie.title || 'A Tube Cloud Hub'}`;
      }

      // Tab switcher wiring
      const watchTab = document.getElementById('tab-watch-btn');
      const downloadTab = document.getElementById('tab-download-btn');

      if (watchTab && downloadTab) {
        watchTab.onclick = () => {
          watchTab.classList.add('active');
          downloadTab.classList.remove('active');
          watchGrid.classList.remove('is-hidden');
          downloadGrid.classList.add('is-hidden');
        };
        downloadTab.onclick = () => {
          downloadTab.classList.add('active');
          watchTab.classList.remove('active');
          downloadGrid.classList.remove('is-hidden');
          watchGrid.classList.add('is-hidden');
        };
      }

      let allServers = [...(servers || [])];
      if (allServers.length === 0) {
        allServers = [
          { site: 'A Tube VIP', quality: '1080p FHD', stream_url: '', badge: 'VIP Fast ⚡', size: '1.4 GB', latency: '35ms' },
          { site: 'A Tube Cloud', quality: '720p HD', stream_url: '', badge: 'توفير باقة', size: '680 MB', latency: '65ms' }
        ];
      }

      const qualitySizes = [
        { quality: '1080p FHD', size: '1.4 GB', tagClass: 'quality-1080p', latency: '32ms', isFast: true },
        { quality: '720p HD', size: '680 MB', tagClass: 'quality-720p', latency: '68ms', isFast: true },
        { quality: '480p SD', size: '320 MB', tagClass: 'quality-default', latency: '110ms', isFast: false }
      ];

      // 0. Auto-Play Best Server Glowing Button
      const autoPlayBestBtn = document.createElement('button');
      autoPlayBestBtn.className = 'auto-play-best-btn dpad-focusable';
      autoPlayBestBtn.tabIndex = 0;
      autoPlayBestBtn.innerHTML = `
        <span style="font-size: 20px;">⚡</span>
        <span>تشغيل ذكي فوري (أفضل جودة وأسرع استجابة تلقائياً)</span>
      `;
      autoPlayBestBtn.onclick = () => {
        const bestServer = allServers[0] || {};
        const q = bestServer.quality || '1080p FHD';
        closeModal();
        const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
        if (player && typeof player.playMedia === 'function') {
          player.playMedia({
            ...movie,
            id: movie.id,
            tmdb_id: movie.tmdb_id,
            name: `${mediaTitle} (${q})`,
            title: mediaTitle,
            category: movie.category_name || movie.category || 'A Tube Ultra HD',
            streamUrl: bestServer.url || bestServer.stream_url,
            quality: q,
            content_type: movie.content_type,
            servers: allServers
          });
        }
      };
      watchGrid.appendChild(autoPlayBestBtn);

      // 0b. Quality Quick-Filter Bar
      const filterBar = document.createElement('div');
      filterBar.className = 'quality-filter-bar';
      filterBar.innerHTML = `
        <button class="quality-filter-pill active dpad-focusable" data-filter="all">🌟 الكل (${allServers.length})</button>
        <button class="quality-filter-pill dpad-focusable" data-filter="1080p">💎 1080p FHD</button>
        <button class="quality-filter-pill dpad-focusable" data-filter="720p">⚡ 720p HD</button>
        <button class="quality-filter-pill dpad-focusable" data-filter="480p">💾 480p (توفير)</button>
        <button class="quality-filter-pill dpad-focusable" data-filter="vip">🚀 VIP Fast</button>
      `;

      filterBar.querySelectorAll('.quality-filter-pill').forEach(pill => {
        pill.onclick = (e) => {
          e.stopPropagation();
          filterBar.querySelectorAll('.quality-filter-pill').forEach(p => p.classList.remove('active'));
          pill.classList.add('active');
          const f = pill.getAttribute('data-filter');
          watchGrid.querySelectorAll('.server-card-component:not(.auto-play-best-btn):not(.deep-search-trigger)').forEach(card => {
            if (f === 'all') {
              card.style.display = 'flex';
            } else if (f === '1080p') {
              card.style.display = card.textContent.includes('1080p') ? 'flex' : 'none';
            } else if (f === '720p') {
              card.style.display = card.textContent.includes('720p') ? 'flex' : 'none';
            } else if (f === '480p') {
              card.style.display = card.textContent.includes('480p') ? 'flex' : 'none';
            } else if (f === 'vip') {
              card.style.display = (card.textContent.includes('VIP') || card.textContent.includes('⚡') || card.textContent.includes('Direct')) ? 'flex' : 'none';
            }
          });
        };
      });
      watchGrid.appendChild(filterBar);

      // Render Individual Server Cards
      allServers.forEach((srv, idx) => {
        const qInfo = qualitySizes[idx % qualitySizes.length];
        const quality = srv.quality || qInfo.quality;
        const sizeTag = srv.size || qInfo.size;
        const latencyText = srv.latency || qInfo.latency;
        const latencyClass = qInfo.isFast ? 'fast' : 'stable';
        const serverBadge = srv.badge || (idx === 0 ? 'VIP Fast ⚡' : 'A Tube Direct');
        const serverTitle = srv.name || `سيرفر مشاهدة ${idx + 1} - A Tube Direct`;

        // 1. Redesigned Watch Card Component
        const watchCard = document.createElement('button');
        watchCard.className = 'server-card-component dpad-focusable';
        watchCard.tabIndex = 0;
        watchCard.innerHTML = `
          <div class="server-card-top-row">
            <span class="server-site-badge">${safeHtml(serverBadge)}</span>
            <span class="latency-badge ${latencyClass}">🟢 ${latencyText}</span>
            <div class="server-action-icon">▶</div>
          </div>
          <div class="server-card-middle-row">
            <span class="server-name-label">${safeHtml(serverTitle)}</span>
          </div>
          <div class="server-card-bottom-row">
            <span class="server-size-tag">💾 ${safeHtml(sizeTag)}</span>
            <span class="server-quality-tag ${qInfo.tagClass}">${safeHtml(quality)}</span>
          </div>
        `;
        watchCard.onclick = () => {
          closeModal();
          const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
          if (player && typeof player.playMedia === 'function') {
            player.playMedia({
              ...movie,
              id: movie.id,
              tmdb_id: movie.tmdb_id,
              name: `${mediaTitle} (${quality})`,
              title: mediaTitle,
              category: movie.category_name || movie.category || 'A Tube Ultra HD',
              streamUrl: srv.url || srv.stream_url,
              quality: quality,
              content_type: movie.content_type,
              servers: allServers
            });
          }
        };
        watchGrid.appendChild(watchCard);

        // 2. Redesigned Download Card Component
        const dlCard = document.createElement('button');
        dlCard.className = 'server-card-component download-card dpad-focusable';
        dlCard.tabIndex = 0;
        dlCard.innerHTML = `
          <div class="server-card-top-row">
            <span class="server-site-badge download-badge">تحميل مباشر 📥</span>
            <span class="latency-badge fast">🟢 سرعة قصوى</span>
            <div class="server-action-icon">⬇</div>
          </div>
          <div class="server-card-middle-row">
            <span class="server-name-label">تحميل بدقة (${safeHtml(quality)})</span>
          </div>
          <div class="server-card-bottom-row">
            <span class="server-size-tag">💾 ${safeHtml(sizeTag)}</span>
            <span class="server-quality-tag ${qInfo.tagClass}">${safeHtml(quality)}</span>
          </div>
        `;
        dlCard.onclick = () => {
          const rawUrl = srv.url || srv.stream_url;
          if (rawUrl && (rawUrl.startsWith('http://') || rawUrl.startsWith('https://'))) {
            window.open(rawUrl, '_blank');
          } else {
            alert('⚡ جاري فك وتجهيز رابط التحميل السحابي المباشر...');
          }
        };
        downloadGrid.appendChild(dlCard);
      });

      // 3. Multi-Portal Live Deep Search Card with Radar Live Scanner
      const deepSearchCard = document.createElement('button');
      deepSearchCard.className = 'server-card-component deep-search-trigger dpad-focusable';
      deepSearchCard.style.cssText = 'background: rgba(0, 229, 255, 0.08); border: 1px dashed rgba(0, 229, 255, 0.45); justify-content: center; align-items: center; min-height: 100px; width: 100%;';
      deepSearchCard.tabIndex = 0;
      deepSearchCard.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; text-align: center;">
          <span style="font-size: 24px;">🔍</span>
          <span style="color: var(--primary-cyan); font-weight: 800; font-size: 14px;">بحث حي متقدم في محركات السيرفرات العربية (Radar Scanner)...</span>
        </div>
      `;

      deepSearchCard.onclick = async () => {
        // Render Live Multi-Stage Radar Scanner
        watchGrid.innerHTML = `
          <div class="radar-scanner-container">
            <div class="radar-sweep-icon"></div>
            <div class="radar-stage-title">📡 جاري مسح محركات البث الحية عبر Google Dorking</div>
            <div id="radar-live-status-text" class="radar-stage-text">🔍 جاري فحص محرك جوجل وقاعدة بيانات أكوام (Akwam)...</div>
          </div>
        `;

        const statusTextEl = document.getElementById('radar-live-status-text');

        // Multi-stage radar ticker
        const radarStages = [
          '🔍 جاري فحص محرك جوجل وقاعدة بيانات أكوام (Akwam)...',
          '⚡ فحص فاصل إعلاني (FaselHD) وسيرفرات Vidmoly...',
          '🎬 فحص عرب سيد (ArabSeed) وإيجي ديد وسيرفرات Mixdrop...',
          '🛡️ تنقية السيرفرات وإزالة التكرار واستخراج الروابط المباشرة...',
          '✨ اكتمل البحث! جاري تجهيز أزرار المشاهدة والتحميل...'
        ];

        let stageIdx = 0;
        const tickerInterval = setInterval(() => {
          stageIdx++;
          if (stageIdx < radarStages.length && statusTextEl) {
            statusTextEl.textContent = radarStages[stageIdx];
          }
        }, 550);

        const titleEn = movie.title || '';
        const titleAr = movie.arabic_title || '';
        const year = movie.year || '';

        let epNum = '';
        let sNum = '';
        const activeEpCard = document.querySelector('.episode-card.active');
        if (activeEpCard) {
          const epTitleText = activeEpCard.querySelector('.episode-num-title')?.textContent || '';
          const epMatch = epTitleText.match(/\d+/);
          if (epMatch) epNum = epMatch[0];
        }

        try {
          const res = await fetch(`/api/scrape-servers?title_en=${encodeURIComponent(titleEn)}&title_ar=${encodeURIComponent(titleAr)}&year=${encodeURIComponent(year)}&type=${encodeURIComponent(movie.content_type || 'movie')}&episode=${encodeURIComponent(epNum)}&season=${encodeURIComponent(sNum)}`);
          clearInterval(tickerInterval);
          if (res.ok) {
            const data = await res.json();
            if (data && data.servers && data.servers.length > 0) {
              renderServersList(data.servers, mediaTitle);
              return;
            }
          }
        } catch (_) {
          clearInterval(tickerInterval);
        }

        clearInterval(tickerInterval);
        renderServersList(allServers, mediaTitle);
      };

      watchGrid.appendChild(deepSearchCard);
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

  // Open Actor & Star Filmography Explorer Modal
  function openActorFilmography(actor) {
    if (!actor) return;
    const actorModal = document.getElementById('actor-filmography-modal');
    if (!actorModal) return;

    const photoEl = document.getElementById('actor-modal-photo');
    const nameEl = document.getElementById('actor-modal-name');
    const roleBadgeEl = document.getElementById('actor-modal-role-badge');
    const worksCountEl = document.getElementById('actor-modal-works-count');
    const worksGrid = document.getElementById('actor-works-grid');
    const closeBtn = document.getElementById('close-actor-modal-btn');

    const actorName = actor.arabic_name || actor.name || 'النجم';
    const photoUrl = actor.photo ? decodeHtmlEntities(actor.photo) : 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&q=80';
    const roleText = actor.character_name || actor.character || actor.role || '⭐ نجم العمل';

    if (photoEl) {
      photoEl.src = photoUrl;
      photoEl.onerror = () => { photoEl.src = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&q=80'; };
    }
    if (nameEl) nameEl.textContent = actorName;
    if (roleBadgeEl) roleBadgeEl.textContent = roleText;

    let works = [];
    const filmography = window.BUNDLED_FILMOGRAPHY || {};
    const normName = (actor.name || '').trim().toLowerCase();
    const normArName = (actor.arabic_name || '').trim().toLowerCase();

    // 1. Direct match in BUNDLED_FILMOGRAPHY by key or person id
    let entry = (normName && filmography[normName]) || (normArName && filmography[normArName]);
    if (!entry && actor.id) {
      for (const k in filmography) {
        if (filmography[k] && filmography[k].id === actor.id) {
          entry = filmography[k];
          break;
        }
      }
    }

    if (entry && Array.isArray(entry.works) && entry.works.length > 0) {
      works = [...entry.works];
    }

    // 2. Comprehensive search across client MediaCatalog / BUNDLED_CATALOG
    const allCatalog = (window.MediaCatalog && typeof window.MediaCatalog.getAll === 'function')
      ? window.MediaCatalog.getAll()
      : (window.BUNDLED_CATALOG || []);

    if (allCatalog && allCatalog.length > 0) {
      allCatalog.forEach(m => {
        if (!m || !Array.isArray(m.cast)) return;
        const matchedCast = m.cast.find(c => {
          if (!c) return false;
          if (actor.id && c.id === actor.id) return true;
          const cName = (c.name || '').trim().toLowerCase();
          const cArName = (c.arabic_name || '').trim().toLowerCase();
          return (normName && (cName === normName || cArName === normName)) ||
                 (normArName && (cName === normArName || cArName === normArName));
        });
        if (matchedCast && !works.some(w => w.id === m.id)) {
          works.push({
            id: m.id,
            title: m.title,
            arabic_title: m.arabic_title || m.title,
            poster: m.poster,
            year: m.year,
            rating: m.rating,
            category: m.category,
            content_type: m.content_type,
            character: matchedCast.character || matchedCast.character_name || ''
          });
        }
      });
    }

    // 3. Guarantee current movie is present if this actor is listed in it
    if (currentMovie && currentMovie.id && !works.some(w => w.id === currentMovie.id)) {
      works.unshift({
        id: currentMovie.id,
        title: currentMovie.title,
        arabic_title: currentMovie.arabic_title || currentMovie.title,
        poster: currentMovie.poster,
        year: currentMovie.year,
        rating: currentMovie.rating,
        category: currentMovie.category,
        content_type: currentMovie.content_type,
        character: actor.character_name || actor.character || ''
      });
    }

    if (worksCountEl) {
      worksCountEl.textContent = `${works.length} أعمال متوفرة`;
    }

    function closeActorFilmography() {
      actorModal.classList.remove('active');
      actorModal.style.display = 'none';
      const rc = window.RemoteControl || (typeof RemoteControl !== 'undefined' ? RemoteControl : null);
      if (rc && typeof rc.refreshFocusableElements === 'function') {
        rc.refreshFocusableElements();
      }
    }

    if (closeBtn) {
      closeBtn.onclick = closeActorFilmography;
    }

    if (worksGrid) {
      worksGrid.innerHTML = '';
      if (works.length === 0) {
        worksGrid.innerHTML = `
          <div class="actor-works-empty">
            <div class="actor-works-empty-icon">🎬</div>
            <div>لا توجد أعمال أخرى مسجلة حالياً لهذا النجم في المكتبة.</div>
          </div>
        `;
      } else {
        works.forEach(work => {
          const workCard = document.createElement('div');
          workCard.className = 'actor-work-card dpad-focusable';
          workCard.tabIndex = 0;
          const charHtml = work.character ? `<div class="actor-work-char">بدور: ${safeHtml(work.character)}</div>` : '';
          const categoryBadge = work.category === 'foreign' ? 'أجنبي' : (work.category === 'arabic' ? 'عربي' : (work.category || 'سينما'));
          workCard.innerHTML = `
            <img src="${work.poster}" alt="${safeHtml(work.arabic_title || work.title)}" class="actor-work-poster" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\\'http://www.w3.org/2000/svg\\' viewBox=\\'0 0 130 190\\' fill=\\'%2308101a\\'/%3E'">
            <div class="actor-work-title" title="${safeHtml(work.arabic_title || work.title)}">${safeHtml(work.arabic_title || work.title)}</div>
            ${charHtml}
            <div class="actor-work-meta">
              <span>${safeHtml(work.year || '')} • ${categoryBadge}</span>
              <span class="actor-work-rating">${safeHtml(work.rating || '★ 8.5')}</span>
            </div>
          `;
          const handleSelectWork = () => {
            closeActorFilmography();
            open(work.id || work);
          };
          workCard.addEventListener('click', handleSelectWork);
          workCard.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.keyCode === 13) {
              e.preventDefault();
              handleSelectWork();
            }
          });
          worksGrid.appendChild(workCard);
        });
      }
    }

    actorModal.classList.add('active');
    actorModal.style.display = 'flex';

    const rc = window.RemoteControl || (typeof RemoteControl !== 'undefined' ? RemoteControl : null);
    if (rc && typeof rc.refreshFocusableElements === 'function') {
      setTimeout(() => rc.refreshFocusableElements(), 100);
    }
  }

  return {
    init,
    open,
    close: closeModal,
    isOpen: () => modalEl && modalEl.classList.contains('active'),
    openActorFilmography
  };
})();

// Explicit window and global binding for universal access
if (typeof window !== 'undefined') {
  window.MovieDetails = MovieDetails;
}
if (typeof globalThis !== 'undefined') {
  globalThis.MovieDetails = MovieDetails;
}

