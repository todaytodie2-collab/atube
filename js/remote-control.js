/* ==========================================================================
   Universal Remote Control & Spatial Navigation Engine
   Optimized for Android TV (D-Pad), Touchscreen (Mobile), and Mouse (PC)
   Compatible with Android 4.4+ WebViews up to Android 14
   ========================================================================== */

const RemoteControl = (function () {
  let currentFocusedIndex = -1;
  let focusableElements = [];
  let indicatorEl = null;
  let exitToastEl = null;
  let lastBackPressTime = 0;

  function init() {
    createRemoteToast();
    refreshFocusableElements();

    // Listen to physical keyboard & Android TV D-Pad Remote events
    window.addEventListener('keydown', handleKeyDown);

    // Initial focus on first interactive card or hero button
    setTimeout(() => {
      refreshFocusableElements();
      if (focusableElements.length > 0) {
        setFocus(0, false);
      }
    }, 400);

    // Setup touch gestures for horizontal carousels (Mobile Phones & Tablets)
    setupTouchScroll();
  }

  function createRemoteToast() {
    indicatorEl = document.createElement('div');
    indicatorEl.className = 'remote-indicator-toast';
    indicatorEl.innerHTML = `<span>🎮</span> <span>وضع التحكم بالريموت نشط</span>`;
    document.body.appendChild(indicatorEl);

    exitToastEl = document.createElement('div');
    exitToastEl.className = 'remote-indicator-toast tv-exit-toast';
    exitToastEl.innerHTML = `<span>🚪</span> <span>اضغط زر الرجوع مرة أخرى للخروج من A TuBe</span>`;
    document.body.appendChild(exitToastEl);
  }

  function showIndicator() {
    if (!indicatorEl) return;
    indicatorEl.classList.add('visible');
    clearTimeout(indicatorEl._timer);
    indicatorEl._timer = setTimeout(() => {
      indicatorEl.classList.remove('visible');
    }, 2000);
  }

  function showExitToast() {
    if (!exitToastEl) return;
    exitToastEl.classList.add('visible');
    clearTimeout(exitToastEl._timer);
    exitToastEl._timer = setTimeout(() => {
      exitToastEl.classList.remove('visible');
    }, 2500);
  }

  function refreshFocusableElements() {
    // If video modal is active, focus only on player controls
    const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
    if (player && typeof player.isModalActive === 'function' && player.isModalActive()) {
      focusableElements = Array.from(
        document.querySelectorAll('#video-modal .dpad-focusable, #video-modal button')
      ).filter(el => el.offsetParent !== null);
      return;
    }

    // If movie details modal is open, focus only within it
    const movieDet = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
    if (movieDet && typeof movieDet.isOpen === 'function' && movieDet.isOpen()) {
      focusableElements = Array.from(
        document.querySelectorAll('#movie-details-modal .dpad-focusable, #movie-details-modal button, #movie-details-modal .server-card-btn, #movie-details-modal .season-pill, #movie-details-modal .episode-card')
      ).filter(el => el.offsetParent !== null && !el.disabled);
      return;
    }

    // Otherwise, collect all focusable items across the app
    focusableElements = Array.from(
      document.querySelectorAll(
        '.dpad-focusable, .nav-item, .sub-item, .program-card, .live-channel-card, .video-card, .btn-primary, .btn-secondary, .filter-tab, .icon-btn, .atube-shortcut-btn, .play-bar-btn'
      )
    ).filter(el => {
      return el.offsetParent !== null && !el.disabled;
    });
  }

  function setFocus(index, smoothScroll = true) {
    if (index < 0 || index >= focusableElements.length) return;

    // Remove focus class from previous
    focusableElements.forEach(el => el.classList.remove('tv-focused'));

    currentFocusedIndex = index;
    const target = focusableElements[index];
    target.classList.add('tv-focused');
    target.focus({ preventScroll: true });

    // Center target into view smoothly for TV experience
    if (smoothScroll) {
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center'
      });
    }

    showIndicator();
  }

  // 2D Spatial Navigation calculation
  function moveFocus(direction) {
    refreshFocusableElements();
    if (focusableElements.length === 0) return;

    if (currentFocusedIndex === -1) {
      setFocus(0);
      return;
    }

    const currentEl = focusableElements[currentFocusedIndex];
    const currentRect = currentEl.getBoundingClientRect();
    const currentCenter = {
      x: currentRect.left + currentRect.width / 2,
      y: currentRect.top + currentRect.height / 2
    };

    let bestCandidateIndex = -1;
    let minDistance = Infinity;

    for (let i = 0; i < focusableElements.length; i++) {
      if (i === currentFocusedIndex) continue;
      const cand = focusableElements[i];
      const candRect = cand.getBoundingClientRect();
      const candCenter = {
        x: candRect.left + candRect.width / 2,
        y: candRect.top + candRect.height / 2
      };

      const dx = candCenter.x - currentCenter.x;
      const dy = candCenter.y - currentCenter.y;

      let isAllowedDirection = false;
      let primaryWeight = 1.0;
      let secondaryWeight = 2.5;

      switch (direction) {
        case 'up':
          if (dy < -10) {
            isAllowedDirection = true;
            // Prefer items vertically aligned
            const dist = Math.abs(dy) * primaryWeight + Math.abs(dx) * secondaryWeight;
            if (dist < minDistance) {
              minDistance = dist;
              bestCandidateIndex = i;
            }
          }
          break;

        case 'down':
          if (dy > 10) {
            isAllowedDirection = true;
            const dist = Math.abs(dy) * primaryWeight + Math.abs(dx) * secondaryWeight;
            if (dist < minDistance) {
              minDistance = dist;
              bestCandidateIndex = i;
            }
          }
          break;

        case 'left':
          if (dx < -10) {
            isAllowedDirection = true;
            const dist = Math.abs(dx) * primaryWeight + Math.abs(dy) * secondaryWeight;
            if (dist < minDistance) {
              minDistance = dist;
              bestCandidateIndex = i;
            }
          }
          break;

        case 'right':
          if (dx > 10) {
            isAllowedDirection = true;
            const dist = Math.abs(dx) * primaryWeight + Math.abs(dy) * secondaryWeight;
            if (dist < minDistance) {
              minDistance = dist;
              bestCandidateIndex = i;
            }
          }
          break;
      }
    }

    if (bestCandidateIndex !== -1) {
      setFocus(bestCandidateIndex);
    }
  }

  function handleBackKey() {
    const player = window.InAppPlayer || (typeof InAppPlayer !== 'undefined' ? InAppPlayer : null);
    const isPlayerActive = player && typeof player.isModalActive === 'function' && player.isModalActive();

    // 1. If Video Player is active: Close player and ensure Movie Details is returned to (for VOD/movies)
    if (isPlayerActive) {
      const currentMedia = player.getCurrentPlaying();
      player.closePlayer();
      if (currentMedia && !currentMedia.is_live && window.MovieDetails) {
        if (!window.MovieDetails.isOpen()) {
          window.MovieDetails.open(currentMedia);
        }
      }
      refreshFocusableElements();
      setTimeout(() => refreshFocusableElements(), 150);
      return;
    }

    // 1b. If Actor Filmography modal is open: Close it and stay on Movie Details!
    const actorModal = document.getElementById('actor-filmography-modal');
    if (actorModal && (actorModal.classList.contains('active') || actorModal.style.display === 'flex' || actorModal.style.display === 'block')) {
      actorModal.classList.remove('active');
      actorModal.style.display = 'none';
      refreshFocusableElements();
      setTimeout(() => refreshFocusableElements(), 150);
      return;
    }

    // 2. If Movie Details modal is open: Return to Category View (Not Home!)
    const movieDet = window.MovieDetails || (typeof MovieDetails !== 'undefined' ? MovieDetails : null);
    if (movieDet && typeof movieDet.isOpen === 'function' && movieDet.isOpen()) {
      movieDet.close();
      refreshFocusableElements();
      setTimeout(() => refreshFocusableElements(), 150);
      return;
    }

    // 3. If any other overlay modal is open: Close it
    const modal = document.querySelector('.modal-backdrop.active, .movie-modal-backdrop.active, #night-quiz-modal.active, #qr-remote-modal.active, #satellite-freq-modal.active, #multiview-modal.active, #sports-match-center-modal.active, #ai-concierge-modal.active');
    if (modal) {
      modal.classList.remove('active');
      if (modal.classList.contains('modal-backdrop')) modal.style.display = 'none';
      setTimeout(() => refreshFocusableElements(), 150);
      return;
    }

    // 4. If in Category View or Search: Return to Home View
    const catView = document.getElementById('category-page-view');
    const homeView = document.getElementById('home-page-view');
    if (catView && !catView.classList.contains('is-hidden') && catView.style.display !== 'none') {
      if (window.showHomeView) {
        window.showHomeView();
      } else {
        catView.classList.add('is-hidden');
        catView.style.display = 'none';
        if (homeView) {
          homeView.classList.remove('is-hidden');
          homeView.style.display = 'block';
        }
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
      setTimeout(() => refreshFocusableElements(), 150);
      return;
    }

    // 5. If at Home root: Double-Back Exit confirmation
    const now = Date.now();
    if (now - lastBackPressTime < 2500) {
      if (window.AndroidBridge) {
        if (typeof window.AndroidBridge.exitApp === 'function') {
          window.AndroidBridge.exitApp();
        } else if (typeof window.AndroidBridge.closeApp === 'function') {
          window.AndroidBridge.closeApp();
        }
      }
    } else {
      lastBackPressTime = now;
      showExitToast();
    }
  }

  function handleKeyDown(e) {
    // Android TV KeyCodes:
    // 19: UP, 20: DOWN, 21: LEFT, 22: RIGHT, 23: CENTER (OK), 4: BACK
    const key = e.key;
    const code = e.keyCode;

    if (key === 'ArrowUp' || code === 19) {
      e.preventDefault();
      moveFocus('up');
    } else if (key === 'ArrowDown' || code === 20) {
      e.preventDefault();
      moveFocus('down');
    } else if (key === 'ArrowLeft' || code === 21) {
      e.preventDefault();
      moveFocus('left');
    } else if (key === 'ArrowRight' || code === 22) {
      e.preventDefault();
      moveFocus('right');
    } else if (key === 'Enter' || code === 13 || code === 23 || code === 66) {
      e.preventDefault();
      if (currentFocusedIndex !== -1 && focusableElements[currentFocusedIndex]) {
        focusableElements[currentFocusedIndex].click();
      }
    } else if (key === 'Escape' || key === 'Backspace' || code === 27 || code === 4 || code === 8) {
      e.preventDefault();
      handleBackKey();
    }
  }

  // Setup Touch / Drag scrolling for horizontal carousels (Mobile Phones & Tablets)
  function setupTouchScroll() {
    const tracks = document.querySelectorAll('.carousel-track');
    tracks.forEach(track => {
      let isDown = false;
      let startX;
      let scrollLeft;

      function getClientX(e) {
        if (e.touches && e.touches.length > 0) return e.touches[0].clientX;
        if (e.changedTouches && e.changedTouches.length > 0) return e.changedTouches[0].clientX;
        return e.clientX;
      }

      function onStart(e) {
        isDown = true;
        startX = getClientX(e);
        scrollLeft = track.scrollLeft;
        track.style.cursor = 'grabbing';
      }

      function onEnd() {
        isDown = false;
        track.style.cursor = 'grab';
      }

      function onMove(e) {
        if (!isDown) return;
        e.preventDefault();
        const x = getClientX(e);
        const walk = (x - startX) * 1.5;
        track.scrollLeft = scrollLeft - walk;
      }

      track.addEventListener('mousedown', onStart);
      track.addEventListener('mouseleave', onEnd);
      track.addEventListener('mouseup', onEnd);
      track.addEventListener('mousemove', onMove);
      track.addEventListener('touchstart', onStart, { passive: true });
      track.addEventListener('touchend', onEnd);
      track.addEventListener('touchmove', onMove, { passive: false });
    });
  }

  return {
    init,
    refresh: refreshFocusableElements,
    setFocus,
    moveFocus,
    handleBackKey
  };
})();

// Explicit window and global binding for universal access
if (typeof window !== 'undefined') {
  window.RemoteControl = RemoteControl;
}
if (typeof globalThis !== 'undefined') {
  globalThis.RemoteControl = RemoteControl;
}

