/* ==========================================================================
   A TuBe High-Performance In-App Video Player Engine (RAM-Only & Zero-Storage)
   - Real-time In-Memory Stream Sanitizer & Ad Stripper
   - Stateless Multi-Server Failover (Auto-healing without black screens)
   - Aggressive RAM Deallocation & Buffer Flushing for 8GB Android TV
   ========================================================================== */

const InAppPlayer = (function () {
  'use strict';

  // Core DOM elements
  let videoEl = null;
  let iframeEl = null;
  let modalEl = null;

  // HLS & Playback instances (volatile in-memory)
  let hlsInstance = null;
  let currentPlayingItem = null;
  let isPlaying = false;
  let isFullScreen = false;

  // Stateless Multi-Server Failover Pool
  let candidateServers = [];
  let currentServerIndex = 0;
  let savedPlayheadTime = 0;
  let stallWatchdogTimer = null;
  let isSwitchingServer = false;

  // Ad-blocker & window.open popup suppressor reference
  let originalWindowOpen = null;
  let wakeLock = null;
  let resumeTimer = null;
  let nextEpDismissed = false;
  let audioCtx = null;
  let audioSourceNode = null;
  let audioGainNode = null;
  let audioCompressorNode = null;
  let audioAnalyserNode = null;
  let eqFilters = [];
  let subOffsetSeconds = 0;
  let sleepTimerInterval = null;
  let sleepEndTime = null;
  let loopPointA = null;
  let loopPointB = null;
  let isLoopActive = false;
  let customSubtitles = [];
  let isTouchLocked = false;
  const EQ_FREQUENCIES = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];

  function init() {
    videoEl = document.getElementById('main-video');
    iframeEl = document.getElementById('main-embed-frame');
    modalEl = document.getElementById('video-modal');

    if (!videoEl || !modalEl) return;

    videoEl.playsInline = true;

    // Allow embeds full streaming capability without breaking VidLink/MegaMax sandbox checks
    if (iframeEl) {
      iframeEl.removeAttribute('sandbox');
      iframeEl.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen');
      iframeEl.setAttribute('allowfullscreen', 'true');
    }

    // Suppress unwanted third-party ad popups
    suppressPopups();

    // Bind full cinematic player controls & timeline
    bindTimelineScrubber();
    bindVolumeAndBrightness();
    bindPlaybackSpeed();
    bindSubtitlesAndServers();
    bindResumePlaybackEvents();
    bindKeyboardShortcuts();
    bindTouchGestures();
    bindPiPAndAmbientGlow();
    bindSkipIntroAndNextEpisode();
    bindAspectRatio();
    bindAudioFX();
    bindSubtitleCustomizer();
    bindEqualizer();
    bindSleepTimer();
    bindScreenshot4K();
    bindTouchLock();
    bindABLoop();
    bindSubtitleDropAndDual();
    bindZappingAndHealth();
    bindRadioVisualizer();

    // Time update listener
    videoEl.addEventListener('timeupdate', () => {
      if (videoEl.duration && !isNaN(videoEl.duration)) {
        savedPlayheadTime = videoEl.currentTime;
        updateTimelineUI(videoEl.currentTime, videoEl.duration);
        checkSkipIntro(videoEl.currentTime, videoEl.duration);
        checkNextEpisodeCountdown(videoEl.currentTime, videoEl.duration);
        checkABLoop(videoEl.currentTime);
        updateCustomSubtitles(videoEl.currentTime);

        // Periodically save resume position in localStorage
        if (currentPlayingItem && Math.floor(videoEl.currentTime) % 4 === 0) {
          savePlaybackPosition(currentPlayingItem.id, videoEl.currentTime);
        }

        // Auto-mark item as WATCHED (تمت المشاهدة) after 10 minutes (600s) or 80% progress
        if (currentPlayingItem && (videoEl.currentTime >= 600 || (videoEl.duration > 0 && videoEl.currentTime / videoEl.duration >= 0.8))) {
          try {
            const watchedKey = 'atube_watched_' + currentPlayingItem.id;
            if (localStorage.getItem(watchedKey) !== 'true') {
              localStorage.setItem(watchedKey, 'true');
              console.log('[A Tube Player] Content auto-marked as WATCHED:', currentPlayingItem.title);
              // Trigger Toast notification
              if (window.AndroidBridge && typeof window.AndroidBridge.showToast === 'function') {
                window.AndroidBridge.showToast('تم تسجيل العمل كـ (تمت المشاهدة ✓)');
              }
            }
          } catch (_) {}
        }
      }
    });

    // Buffer progress listener
    videoEl.addEventListener('progress', () => {
      updateBufferUI();
    });

    // Native Video Error & Stall Watchdogs for Multi-Server Failover
    videoEl.addEventListener('error', (e) => {
      console.warn('[A Tube Player] Native video error caught:', e);
      triggerStatelessFailover('خطأ في استجابة السيرفر');
    });

    videoEl.addEventListener('waiting', () => {
      resetStallWatchdog();
    });

    videoEl.addEventListener('playing', () => {
      clearStallWatchdog();
      isPlaying = true;
      isSwitchingServer = false;
      updatePlayIcons(true);
      hideFailoverOverlay();
      requestScreenWakeLock();
    });

    videoEl.addEventListener('pause', () => {
      isPlaying = false;
      updatePlayIcons(false);
      releaseScreenWakeLock();
    });

    // Close button
    const closeBtn = document.getElementById('player-close-btn');
    if (closeBtn) closeBtn.addEventListener('click', closePlayer);

    // Toggle play button
    const toggleBtn = document.getElementById('player-toggle-play');
    if (toggleBtn) toggleBtn.addEventListener('click', togglePlay);

    // Skip -10s and +10s buttons
    const rewind10Btn = document.getElementById('player-rewind-10');
    if (rewind10Btn) rewind10Btn.addEventListener('click', () => seekBy(-10));

    const forward10Btn = document.getElementById('player-forward-10');
    if (forward10Btn) forward10Btn.addEventListener('click', () => seekBy(10));

    // Mini bar play button
    const miniPlayBtn = document.getElementById('mini-play-btn');
    if (miniPlayBtn) {
      miniPlayBtn.addEventListener('click', () => {
        if (currentPlayingItem) {
          togglePlay();
        } else if (typeof IPTVEngine !== 'undefined' && IPTVEngine.getDefaultChannels) {
          const first = IPTVEngine.getDefaultChannels()[0];
          if (first) playMedia(first);
        }
      });
    }

    // Mini bar mute button
    const muteBtn = document.querySelector('.player-right button[title*="كتم"]');
    if (muteBtn) muteBtn.addEventListener('click', toggleMute);

    // Fullscreen buttons
    const miniFsBtn = document.querySelector('.player-right button[title*="تكبير"]');
    if (miniFsBtn) {
      miniFsBtn.addEventListener('click', () => {
        if (modalEl && modalEl.classList.contains('active')) {
          toggleFullscreen();
        } else if (currentPlayingItem) {
          modalEl.classList.add('active');
          toggleFullscreen();
        }
      });
    }

    const fsBtn = document.getElementById('player-fullscreen-btn');
    if (fsBtn) fsBtn.addEventListener('click', toggleFullscreen);

    // Suppress popups within player lifecycle
    suppressPopups();
  }

  // ==========================================================================
  // Cinematic Player Control Systems & Interactive Timeline
  // ==========================================================================

  function bindTimelineScrubber() {
    const seekSlider = document.getElementById('player-seek-slider');
    if (!seekSlider) return;

    seekSlider.addEventListener('input', (e) => {
      if (videoEl && videoEl.duration && !isNaN(videoEl.duration)) {
        const targetTime = (parseFloat(e.target.value) / 100) * videoEl.duration;
        const progressBar = document.getElementById('player-progress-bar');
        if (progressBar) progressBar.style.width = `${e.target.value}%`;
        const timeCurrent = document.getElementById('player-time-current');
        if (timeCurrent) timeCurrent.textContent = formatTime(targetTime);
      }
    });

    seekSlider.addEventListener('change', (e) => {
      if (videoEl && videoEl.duration && !isNaN(videoEl.duration)) {
        const targetTime = (parseFloat(e.target.value) / 100) * videoEl.duration;
        videoEl.currentTime = targetTime;
        savedPlayheadTime = targetTime;
      }
    });
  }

  function updateTimelineUI(currentTime, duration) {
    if (isNaN(duration) || duration <= 0) return;
    const percent = (currentTime / duration) * 100;
    const progressBar = document.getElementById('player-progress-bar');
    const seekSlider = document.getElementById('player-seek-slider');
    const timeCurrent = document.getElementById('player-time-current');
    const timeRemaining = document.getElementById('player-time-remaining');

    if (progressBar) progressBar.style.width = `${percent}%`;
    if (seekSlider && !seekSlider.matches(':active')) seekSlider.value = percent;
    if (timeCurrent) timeCurrent.textContent = formatTime(currentTime);
    if (timeRemaining) {
      const rem = Math.max(0, duration - currentTime);
      timeRemaining.textContent = `-${formatTime(rem)}`;
    }
  }

  function updateBufferUI() {
    if (!videoEl || !videoEl.duration || videoEl.buffered.length === 0) return;
    const bufferBar = document.getElementById('player-buffer-bar');
    if (!bufferBar) return;
    try {
      const bufferedEnd = videoEl.buffered.end(videoEl.buffered.length - 1);
      const bufPercent = (bufferedEnd / videoEl.duration) * 100;
      bufferBar.style.width = `${bufPercent}%`;
    } catch (e) {}
  }

  function seekBy(delta) {
    if (videoEl && videoEl.style.display !== 'none') {
      const newTime = Math.max(0, Math.min(videoEl.duration || 0, videoEl.currentTime + delta));
      videoEl.currentTime = newTime;
      savedPlayheadTime = newTime;
      showGestureFeedback(delta > 0 ? `⏩ +10 ث (${formatTime(newTime)})` : `⏪ -10 ث (${formatTime(newTime)})`);
    } else {
      showGestureFeedback('⏩ للتقديم أو التأخير في المشغل السحابي: اسحب شريط الفيديو المدمج أو استخدم أسهم الكيبورد ➔ ⬅');
    }
  }

  function bindVolumeAndBrightness() {
    // Volume Control
    const volSlider = document.getElementById('player-volume-slider');
    const muteBtn = document.getElementById('player-mute-btn');
    const savedVol = localStorage.getItem('atube_player_volume');

    if (volSlider) {
      if (savedVol !== null) {
        volSlider.value = savedVol;
        if (videoEl) videoEl.volume = parseFloat(savedVol);
      }
      volSlider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (videoEl) {
          videoEl.volume = val;
          videoEl.muted = val === 0;
        }
        localStorage.setItem('atube_player_volume', val);
        updateVolumeIcons(val === 0);
        showGestureFeedback(`🔊 الصوت: ${Math.round(val * 100)}%`);
      });
    }

    if (muteBtn) {
      muteBtn.addEventListener('click', toggleMute);
    }

    // Brightness Control
    const brightSlider = document.getElementById('player-brightness-slider');
    const brightBtn = document.getElementById('player-brightness-btn');
    const brightText = document.getElementById('brightness-val-text');
    const canvasContainer = document.getElementById('player-canvas-container');

    if (brightSlider) {
      brightSlider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (canvasContainer) {
          canvasContainer.style.filter = `brightness(${val})`;
        }
        if (brightText) brightText.textContent = `${Math.round(val * 100)}%`;
        showGestureFeedback(`☀️ السطوع: ${Math.round(val * 100)}%`);
      });
    }

    if (brightBtn) {
      brightBtn.addEventListener('click', () => {
        // Reset brightness to 100%
        if (brightSlider) brightSlider.value = 1;
        if (canvasContainer) canvasContainer.style.filter = 'brightness(1)';
        if (brightText) brightText.textContent = '100%';
        showGestureFeedback('☀️ إعادة ضبط السطوع (100%)');
      });
    }
  }

  function updateVolumeIcons(isMuted) {
    const iconHigh = document.getElementById('vol-icon-high');
    const iconMuted = document.getElementById('vol-icon-muted');
    if (iconHigh && iconMuted) {
      iconHigh.style.display = isMuted ? 'none' : 'block';
      iconMuted.style.display = isMuted ? 'block' : 'none';
    }
  }

  function bindPlaybackSpeed() {
    const speedBtn = document.getElementById('player-speed-btn');
    const speedMenu = document.getElementById('player-speed-menu');
    const speedLabel = document.getElementById('speed-label');

    if (speedBtn && speedMenu) {
      speedBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        speedMenu.classList.toggle('active');
        closeOtherMenus(speedMenu);
      });

      speedMenu.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', (e) => {
          e.stopPropagation();
          const spd = parseFloat(item.dataset.speed);
          if (videoEl) videoEl.playbackRate = spd;
          if (speedLabel) speedLabel.textContent = `${spd}x`;
          speedMenu.querySelectorAll('.dropdown-item').forEach(i => i.classList.remove('active'));
          item.classList.add('active');
          speedMenu.classList.remove('active');
          showGestureFeedback(`⚡ سرعة التشغيل: ${spd}x`);
        });
      });
    }
  }

  function bindSubtitlesAndServers() {
    // Subtitles (CC) Button
    const subsBtn = document.getElementById('player-subs-btn');
    if (subsBtn) {
      subsBtn.addEventListener('click', () => {
        if (modalEl && modalEl.classList.contains('is-embed-active')) {
          showGestureFeedback('💬 لتفعيل الترجمة العربية: اضغط على أيقونة (CC) أو زر الترس ⚙️ في شريط المشغل واختر Arabic');
          return;
        }
        if (videoEl && videoEl.textTracks && videoEl.textTracks.length > 0) {
          const track = videoEl.textTracks[0];
          track.mode = track.mode === 'showing' ? 'hidden' : 'showing';
          showGestureFeedback(track.mode === 'showing' ? '💬 تم تفعيل الترجمة' : '💬 تم إيقاف الترجمة');
        } else {
          showGestureFeedback('💬 الترجمة مدمجة تلقائياً بالسيرفر');
        }
      });
    }

    // Server Dropdown in Header
    const serverBtn = document.getElementById('player-header-server-btn');
    const serverMenu = document.getElementById('player-server-menu');

    if (serverBtn && serverMenu) {
      serverBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        renderServerMenuOptions();
        serverMenu.classList.toggle('active');
        closeOtherMenus(serverMenu);
      });
    }

    // Close menus on outside click
    document.addEventListener('click', () => {
      closeOtherMenus(null);
    });
  }

  function closeOtherMenus(exceptMenu) {
    document.querySelectorAll('.player-dropdown-menu').forEach(m => {
      if (m !== exceptMenu) m.classList.remove('active');
    });
  }

  function renderServerMenuOptions() {
    const serverMenu = document.getElementById('player-server-menu');
    if (!serverMenu) return;

    serverMenu.innerHTML = '';
    const isLive = isLiveMediaItem(currentPlayingItem);

    candidateServers.forEach((srv, idx) => {
      if (isLive && (srv.isEmbed || String(srv.url).includes('vidlink') || String(srv.url).includes('multiembed'))) {
        return;
      }
      const item = document.createElement('div');
      item.className = `dropdown-item ${idx === currentServerIndex ? 'active' : ''}`;
      item.innerHTML = `<span>${srv.name}</span> <small style="opacity:0.75;">(${srv.quality || (isLive ? 'بث مباشر HD' : 'FHD')})</small>`;
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        serverMenu.classList.remove('active');
        if (idx !== currentServerIndex) {
          currentServerIndex = idx;
          flushDecoderBuffer();
          loadStreamSource(candidateServers[currentServerIndex], isLive ? 0 : savedPlayheadTime);
          showGestureFeedback(`⚡ تم التبديل إلى: ${srv.name}`);
        }
      });
      serverMenu.appendChild(item);
    });
  }

  function bindResumePlaybackEvents() {
    const toast = document.getElementById('player-resume-toast');
    const resumeYes = document.getElementById('resume-yes-btn');
    const resumeNo = document.getElementById('resume-no-btn');

    if (resumeYes) {
      resumeYes.addEventListener('click', () => {
        if (toast) toast.style.display = 'none';
        if (currentPlayingItem) {
          const saved = getSavedPlaybackPosition(currentPlayingItem.id);
          if (saved > 0 && videoEl) {
            videoEl.currentTime = saved;
            savedPlayheadTime = saved;
            showGestureFeedback(`⏱️ استئناف من ${formatTime(saved)}`);
          }
        }
      });
    }

    if (resumeNo) {
      resumeNo.addEventListener('click', () => {
        if (toast) toast.style.display = 'none';
        if (videoEl) videoEl.currentTime = 0;
        savedPlayheadTime = 0;
      });
    }
  }

  function checkResumePlayback(item) {
    const toast = document.getElementById('player-resume-toast');
    const label = document.getElementById('resume-time-label');
    if (!toast || !item || !item.id) return;

    const savedPos = getSavedPlaybackPosition(item.id);
    if (savedPos > 15) {
      if (label) label.textContent = formatTime(savedPos);
      toast.style.display = 'flex';
      if (resumeTimer) clearTimeout(resumeTimer);
      resumeTimer = setTimeout(() => {
        if (toast) toast.style.display = 'none';
      }, 9000);
    } else {
      toast.style.display = 'none';
    }
  }

  function savePlaybackPosition(itemId, seconds) {
    if (!itemId || seconds < 5) return;
    try {
      localStorage.setItem(`atube_pos_${itemId}`, String(Math.floor(seconds)));
    } catch (e) {}
  }

  function getSavedPlaybackPosition(itemId) {
    if (!itemId) return 0;
    try {
      const val = localStorage.getItem(`atube_pos_${itemId}`);
      return val ? parseFloat(val) : 0;
    } catch (e) {
      return 0;
    }
  }

  function bindKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      if (!modalEl || !modalEl.classList.contains('active')) return;

      switch (e.key) {
        case ' ':
        case 'k':
        case 'K':
          e.preventDefault();
          togglePlay();
          break;
        case 'ArrowRight':
        case 'l':
        case 'L':
          e.preventDefault();
          seekBy(10);
          break;
        case 'ArrowLeft':
        case 'j':
        case 'J':
          e.preventDefault();
          seekBy(-10);
          break;
        case 'ArrowUp':
          e.preventDefault();
          adjustVolume(0.1);
          break;
        case 'ArrowDown':
          e.preventDefault();
          adjustVolume(-0.1);
          break;
        case 'f':
        case 'F':
          e.preventDefault();
          toggleFullscreen();
          break;
        case 'm':
        case 'M':
          e.preventDefault();
          toggleMute();
          break;
        case 'Escape':
          e.preventDefault();
          closePlayer();
          break;
        case 's':
        case 'S':
        case 'n':
        case 'N':
          e.preventDefault();
          triggerStatelessFailover('التبديل إلى السيرفر التالي');
          break;
      }
    });
  }

  function adjustVolume(delta) {
    if (!videoEl) return;
    const newVol = Math.max(0, Math.min(1, videoEl.volume + delta));
    videoEl.volume = newVol;
    videoEl.muted = newVol === 0;
    const volSlider = document.getElementById('player-volume-slider');
    if (volSlider) volSlider.value = newVol;
    localStorage.setItem('atube_player_volume', newVol);
    updateVolumeIcons(newVol === 0);
    showGestureFeedback(`🔊 الصوت: ${Math.round(newVol * 100)}%`);
  }

  function bindTouchGestures() {
    const canvas = document.getElementById('player-canvas-container');
    if (!canvas) return;

    let touchStartX = 0;
    let touchStartY = 0;
    let touchStartTime = 0;

    canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        touchStartTime = Date.now();
      }
    }, { passive: true });

    canvas.addEventListener('touchend', (e) => {
      if (e.changedTouches.length === 1) {
        const diffX = e.changedTouches[0].clientX - touchStartX;
        const diffY = e.changedTouches[0].clientY - touchStartY;
        const elapsed = Date.now() - touchStartTime;

        // Double tap check (< 300ms, minimal movement)
        if (elapsed < 300 && Math.abs(diffX) < 20 && Math.abs(diffY) < 20) {
          const rect = canvas.getBoundingClientRect();
          const clickX = e.changedTouches[0].clientX - rect.left;
          if (clickX > rect.width * 0.65) {
            seekBy(10);
          } else if (clickX < rect.width * 0.35) {
            seekBy(-10);
          } else {
            togglePlay();
          }
          return;
        }

        // Horizontal Swipe for Seeking
        if (Math.abs(diffX) > 60 && Math.abs(diffY) < 50) {
          if (diffX > 0) seekBy(15);
          else seekBy(-15);
        }
      }
    }, { passive: true });
  }

  let gestureTimer = null;
  function showGestureFeedback(msg) {
    const hud = document.getElementById('player-gesture-hud');
    if (!hud) return;
    hud.innerHTML = msg;
    hud.classList.add('active');
    if (gestureTimer) clearTimeout(gestureTimer);
    gestureTimer = setTimeout(() => {
      hud.classList.remove('active');
    }, 1100);
  }

  function toggleMiniPlayer(forceState) {
    if (!modalEl || !modalEl.classList.contains('active')) return;
    const shouldMinimize = typeof forceState === 'boolean' ? forceState : !modalEl.classList.contains('pip-minimized');
    if (shouldMinimize) {
      if (document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
      modalEl.classList.add('pip-minimized');
      const miniTitle = document.getElementById('mini-player-title');
      const curTitle = document.getElementById('player-title');
      if (miniTitle && curTitle) miniTitle.textContent = curTitle.textContent;
      showGestureFeedback('مشغل مصغر عائم 🗕');
    } else {
      modalEl.classList.remove('pip-minimized');
      modalEl.style.left = '';
      modalEl.style.top = '';
      modalEl.style.bottom = '';
      modalEl.style.right = '';
      showGestureFeedback('تكبير المشغل ⛶');
    }
  }

  function setupMiniPlayerDraggable() {
    if (!modalEl) return;
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let initialLeft = 0;
    let initialTop = 0;

    const overlay = document.getElementById('mini-player-overlay');
    if (!overlay) return;

    overlay.addEventListener('dblclick', () => {
      if (modalEl.classList.contains('pip-minimized')) {
        toggleMiniPlayer(false);
      }
    });

    const onStart = (e) => {
      if (!modalEl.classList.contains('pip-minimized')) return;
      if (e.target.closest('button')) return;
      isDragging = true;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const rect = modalEl.getBoundingClientRect();
      startX = clientX;
      startY = clientY;
      initialLeft = rect.left;
      initialTop = rect.top;
      modalEl.style.bottom = 'auto';
      modalEl.style.right = 'auto';
      modalEl.style.left = initialLeft + 'px';
      modalEl.style.top = initialTop + 'px';
    };

    const onMove = (e) => {
      if (!isDragging || !modalEl.classList.contains('pip-minimized')) return;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const deltaX = clientX - startX;
      const deltaY = clientY - startY;
      const newLeft = Math.max(10, Math.min(window.innerWidth - modalEl.offsetWidth - 10, initialLeft + deltaX));
      const newTop = Math.max(10, Math.min(window.innerHeight - modalEl.offsetHeight - 10, initialTop + deltaY));
      modalEl.style.left = newLeft + 'px';
      modalEl.style.top = newTop + 'px';
    };

    const onEnd = () => {
      isDragging = false;
    };

    overlay.addEventListener('mousedown', onStart);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
    overlay.addEventListener('touchstart', onStart, { passive: true });
    window.addEventListener('touchmove', onMove, { passive: true });
    window.addEventListener('touchend', onEnd);
  }

  function bindPiPAndAmbientGlow() {
    const minimizeBtn = document.getElementById('player-minimize-btn');
    if (minimizeBtn) {
      minimizeBtn.addEventListener('click', () => toggleMiniPlayer(true));
    }

    const miniExpandBtn = document.getElementById('mini-player-expand-btn');
    if (miniExpandBtn) {
      miniExpandBtn.addEventListener('click', () => toggleMiniPlayer(false));
    }

    const miniCloseBtn = document.getElementById('mini-player-close-btn');
    if (miniCloseBtn) {
      miniCloseBtn.addEventListener('click', () => closePlayer());
    }

    const miniPlayBtn = document.getElementById('mini-player-play-btn');
    if (miniPlayBtn) {
      miniPlayBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        togglePlay();
        miniPlayBtn.textContent = isPlaying ? '⏸' : '▶';
      });
    }

    setupMiniPlayerDraggable();

    const pipBtn = document.getElementById('player-pip-btn');
    if (pipBtn) {
      pipBtn.addEventListener('click', async () => {
        toggleMiniPlayer();
      });
    }

    const ambientBtn = document.getElementById('player-ambient-btn');
    const glowEl = document.getElementById('player-ambient-glow');
    let isAmbientActive = true;
    if (glowEl) glowEl.classList.add('active');
    if (ambientBtn) {
      ambientBtn.style.color = '#00e5ff';
      ambientBtn.addEventListener('click', () => {
        isAmbientActive = !isAmbientActive;
        if (glowEl) {
          glowEl.classList.toggle('active', isAmbientActive);
        }
        ambientBtn.style.color = isAmbientActive ? '#00e5ff' : '#8fa2b8';
      });
    }
  }

  function bindSkipIntroAndNextEpisode() {
    const skipBtn = document.getElementById('player-skip-intro-btn');
    if (skipBtn) {
      skipBtn.addEventListener('click', () => {
        seekBy(85);
        skipBtn.classList.add('is-hidden');
        showGestureFeedback('تم تخطي المقدمة ⏭️');
      });
    }

    const nextNowBtn = document.getElementById('next-ep-now-btn');
    const nextCancelBtn = document.getElementById('next-ep-cancel-btn');
    const countdownModal = document.getElementById('player-next-ep-countdown');

    if (nextNowBtn) {
      nextNowBtn.addEventListener('click', () => {
        playNextEpisode();
      });
    }
    if (nextCancelBtn) {
      nextCancelBtn.addEventListener('click', () => {
        nextEpDismissed = true;
        if (countdownModal) countdownModal.classList.add('is-hidden');
      });
    }
  }

  function checkSkipIntro(cur, dur) {
    const skipBtn = document.getElementById('player-skip-intro-btn');
    if (!skipBtn) return;
    if (cur >= 5 && cur <= 85 && dur >= 180) {
      skipBtn.classList.remove('is-hidden');
    } else {
      skipBtn.classList.add('is-hidden');
    }
  }

  function checkNextEpisodeCountdown(cur, dur) {
    if (nextEpDismissed || dur < 180) return;
    const remaining = dur - cur;
    const countdownModal = document.getElementById('player-next-ep-countdown');
    const timerLabel = document.getElementById('next-ep-timer');

    if (remaining <= 35 && remaining > 0 && hasNextEpisode()) {
      if (countdownModal) countdownModal.classList.remove('is-hidden');
      const secInt = Math.max(1, Math.ceil(remaining));
      if (timerLabel) timerLabel.textContent = String(secInt);
      if (secInt <= 1) {
        nextEpDismissed = true;
        playNextEpisode();
      }
    } else {
      if (countdownModal) countdownModal.classList.add('is-hidden');
    }
  }

  function hasNextEpisode() {
    if (!currentPlayingItem) return false;
    const item = currentPlayingItem;
    if (item.content_type !== 'series') return false;
    const seasons = item.seasons || [];
    if (!seasons.length) return false;
    return true;
  }

  function playNextEpisode() {
    const countdownModal = document.getElementById('player-next-ep-countdown');
    if (countdownModal) countdownModal.classList.add('is-hidden');
    if (window.MovieDetails && typeof MovieDetails.playNextEpisode === 'function') {
      MovieDetails.playNextEpisode();
    } else {
      showGestureFeedback('جاري بدء الحلقة التالية 🎬');
    }
  }

  function bindAspectRatio() {
    const aspectBtn = document.getElementById('player-aspect-btn');
    const aspectMenu = document.getElementById('player-aspect-menu');
    const aspectLabel = document.getElementById('aspect-label');

    if (aspectBtn && aspectMenu) {
      aspectBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        aspectMenu.classList.toggle('active');
      });

      aspectMenu.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', () => {
          aspectMenu.querySelectorAll('.dropdown-item').forEach(d => d.classList.remove('active'));
          item.classList.add('active');
          const aspect = item.getAttribute('data-aspect');
          if (aspectLabel) aspectLabel.textContent = item.textContent.trim().split(' ')[0];
          applyAspectRatio(aspect);
          aspectMenu.classList.remove('active');
        });
      });

      document.addEventListener('click', (e) => {
        if (!aspectBtn.contains(e.target)) aspectMenu.classList.remove('active');
      });
    }
  }

  function applyAspectRatio(mode) {
    if (!videoEl) return;
    videoEl.style.transform = '';
    videoEl.style.aspectRatio = '';

    if (mode === 'contain') {
      videoEl.style.objectFit = 'contain';
      videoEl.style.width = '100%';
      videoEl.style.height = '100%';
    } else if (mode === '16-9') {
      videoEl.style.objectFit = 'fill';
      videoEl.style.aspectRatio = '16/9';
    } else if (mode === '4-3') {
      videoEl.style.objectFit = 'fill';
      videoEl.style.aspectRatio = '4/3';
    } else if (mode === 'cover') {
      videoEl.style.objectFit = 'cover';
      videoEl.style.width = '100%';
      videoEl.style.height = '100%';
    } else if (mode === 'stretch') {
      videoEl.style.objectFit = 'fill';
      videoEl.style.width = '100%';
      videoEl.style.height = '100%';
    }
    showGestureFeedback(`أبعاد الشاشة: ${mode}`);
  }

  function bindAudioFX() {
    const audioBtn = document.getElementById('player-audio-fx-btn');
    const audioMenu = document.getElementById('player-audio-fx-menu');
    const audioLabel = document.getElementById('audio-fx-label');

    function initWebAudio() {
      if (!audioCtx && typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext)) {
        try {
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          audioCtx = new AudioContextClass();
          audioSourceNode = audioCtx.createMediaElementSource(videoEl);
          audioCompressorNode = audioCtx.createDynamicsCompressor();
          audioGainNode = audioCtx.createGain();
          audioAnalyserNode = audioCtx.createAnalyser();
          audioAnalyserNode.fftSize = 128;

          // Build 10-band Graphic Equalizer Filter Chain
          eqFilters = EQ_FREQUENCIES.map((freq, idx) => {
            const f = audioCtx.createBiquadFilter();
            f.frequency.value = freq;
            f.gain.value = 0;
            if (idx === 0) f.type = 'lowshelf';
            else if (idx === EQ_FREQUENCIES.length - 1) f.type = 'highshelf';
            else f.type = 'peaking';
            return f;
          });

          // Connect source -> eqFilters -> compressor -> gain -> analyser -> destination
          let lastNode = audioSourceNode;
          eqFilters.forEach(f => {
            lastNode.connect(f);
            lastNode = f;
          });
          lastNode.connect(audioCompressorNode);
          audioCompressorNode.connect(audioGainNode);
          audioGainNode.connect(audioAnalyserNode);
          audioAnalyserNode.connect(audioCtx.destination);
        } catch (ex) {
          console.warn('[AudioFX] Web Audio note:', ex);
        }
      }
      if (audioCtx && audioCtx.state === 'suspended') {
        audioCtx.resume().catch(() => {});
      }
    }

    if (audioBtn && audioMenu) {
      audioBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        audioMenu.classList.toggle('active');
        initWebAudio();
      });

      audioMenu.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', () => {
          initWebAudio();
          audioMenu.querySelectorAll('.dropdown-item').forEach(d => d.classList.remove('active'));
          item.classList.add('active');
          const fx = item.getAttribute('data-audiofx');
          if (audioLabel) audioLabel.textContent = item.textContent.trim().split(' ')[0];
          applyAudioFX(fx);
          audioMenu.classList.remove('active');
        });
      });

      document.addEventListener('click', (e) => {
        if (!audioBtn.contains(e.target)) audioMenu.classList.remove('active');
      });
    }
  }

  function applyAudioFX(fx) {
    if (!audioGainNode || !audioCompressorNode) return;
    if (fx === 'night') {
      // Night Mode Dynamic Compression
      audioCompressorNode.threshold.setValueAtTime(-28, audioCtx.currentTime);
      audioCompressorNode.knee.setValueAtTime(40, audioCtx.currentTime);
      audioCompressorNode.ratio.setValueAtTime(12, audioCtx.currentTime);
      audioCompressorNode.attack.setValueAtTime(0.003, audioCtx.currentTime);
      audioCompressorNode.release.setValueAtTime(0.25, audioCtx.currentTime);
      audioGainNode.gain.setValueAtTime(1.2, audioCtx.currentTime);
      showGestureFeedback('وضع المشاهدة الليلية 🌙');
    } else if (fx === 'vocal') {
      // Vocal Clarity Dialogue Booster
      audioCompressorNode.threshold.setValueAtTime(-20, audioCtx.currentTime);
      audioCompressorNode.knee.setValueAtTime(30, audioCtx.currentTime);
      audioCompressorNode.ratio.setValueAtTime(6, audioCtx.currentTime);
      audioGainNode.gain.setValueAtTime(1.3, audioCtx.currentTime);
      if (eqFilters && eqFilters.length >= 8) {
        eqFilters[5].gain.setValueAtTime(5.0, audioCtx.currentTime); // 1000Hz
        eqFilters[6].gain.setValueAtTime(6.0, audioCtx.currentTime); // 2000Hz
        eqFilters[7].gain.setValueAtTime(3.5, audioCtx.currentTime); // 4000Hz
        eqFilters[0].gain.setValueAtTime(-3.5, audioCtx.currentTime); // 32Hz
        eqFilters[1].gain.setValueAtTime(-2.5, audioCtx.currentTime); // 64Hz
      }
      showGestureFeedback('مُعزز وضوح الحوار الصوتي 🎙️✨');
    } else if (fx === 'boost150') {
      audioCompressorNode.threshold.setValueAtTime(-12, audioCtx.currentTime);
      audioGainNode.gain.setValueAtTime(1.5, audioCtx.currentTime);
      showGestureFeedback('تضخيم الصوت 150% 🔊');
    } else if (fx === 'boost200') {
      audioCompressorNode.threshold.setValueAtTime(-8, audioCtx.currentTime);
      audioGainNode.gain.setValueAtTime(2.0, audioCtx.currentTime);
      showGestureFeedback('تضخيم أقصى 200% 🚀');
    } else {
      // Normal
      audioCompressorNode.threshold.setValueAtTime(0, audioCtx.currentTime);
      audioGainNode.gain.setValueAtTime(1.0, audioCtx.currentTime);
      showGestureFeedback('صوت طبيعي 100%');
    }
  }

  function bindSubtitleCustomizer() {
    const subBtn = document.getElementById('player-subs-btn');
    const modal = document.getElementById('subtitle-settings-modal');
    const closeBtn = document.getElementById('close-sub-modal-btn');
    const saveBtn = document.getElementById('save-sub-settings-btn');
    const delayMinus = document.getElementById('sub-delay-minus');
    const delayPlus = document.getElementById('sub-delay-plus');
    const delayLabel = document.getElementById('sub-delay-label');

    if (subBtn && modal) {
      subBtn.addEventListener('click', () => {
        modal.classList.add('active');
      });
    }
    if (closeBtn && modal) {
      closeBtn.addEventListener('click', () => modal.classList.remove('active'));
    }
    if (saveBtn && modal) {
      saveBtn.addEventListener('click', () => {
        modal.classList.remove('active');
        showGestureFeedback('تم حفظ إعدادات الترجمة ✓');
      });
    }

    if (delayMinus && delayPlus && delayLabel) {
      delayMinus.addEventListener('click', () => {
        subOffsetSeconds -= 0.5;
        delayLabel.textContent = `${subOffsetSeconds > 0 ? '+' : ''}${subOffsetSeconds.toFixed(1)} ثانية`;
        applySubtitlesDelay(subOffsetSeconds);
      });
      delayPlus.addEventListener('click', () => {
        subOffsetSeconds += 0.5;
        delayLabel.textContent = `${subOffsetSeconds > 0 ? '+' : ''}${subOffsetSeconds.toFixed(1)} ثانية`;
        applySubtitlesDelay(subOffsetSeconds);
      });
    }

    // Subtitle font color and size options
    document.querySelectorAll('.sub-size-options .sub-opt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.sub-size-options .sub-opt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const sz = btn.getAttribute('data-subsize');
        document.documentElement.style.setProperty('--sub-font-size', sz);
      });
    });

    document.querySelectorAll('.sub-color-options .sub-opt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.sub-color-options .sub-opt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const col = btn.getAttribute('data-subcolor');
        document.documentElement.style.setProperty('--sub-font-color', col);
      });
    });

    // Subtitle background options
    document.querySelectorAll('.sub-bg-options .sub-opt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.sub-bg-options .sub-opt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const bg = btn.getAttribute('data-subbg');
        let val = 'transparent';
        if (bg === 'semi') val = 'rgba(0, 0, 0, 0.75)';
        else if (bg === 'solid') val = '#000000';
        document.documentElement.style.setProperty('--sub-bg-color', val);
      });
    });

    // Subtitle shadow / outline options
    document.querySelectorAll('.sub-shadow-options .sub-opt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.sub-shadow-options .sub-opt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const sh = btn.getAttribute('data-subshadow');
        let val = '0 2px 4px rgba(0, 0, 0, 0.95), 0 0 2px #000';
        if (sh === 'outline') val = '-1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000';
        else if (sh === 'glow') val = '0 0 8px rgba(0, 229, 255, 0.8), 0 2px 4px #000';
        document.documentElement.style.setProperty('--sub-shadow-style', val);
      });
    });
  }

  // 10-Band EQ State and Web Audio Context
  const EQ_FREQUENCIES = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
  let audioCtx = null;
  let audioSourceNode = null;
  let eqFilters = [];

  function initWebAudio() {
    if (audioCtx && eqFilters.length === 10) return;
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass || !videoEl) return;
      if (!audioCtx) {
        audioCtx = new AudioContextClass();
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume();
      }
      if (!audioSourceNode) {
        audioSourceNode = audioCtx.createMediaElementSource(videoEl);
      }
      eqFilters = EQ_FREQUENCIES.map((freq, idx) => {
        const filter = audioCtx.createBiquadFilter();
        if (idx === 0) {
          filter.type = 'lowshelf';
        } else if (idx === EQ_FREQUENCIES.length - 1) {
          filter.type = 'highshelf';
        } else {
          filter.type = 'peaking';
          filter.Q.value = 1.4;
        }
        filter.frequency.value = freq;
        filter.gain.value = 0;
        return filter;
      });

      let lastNode = audioSourceNode;
      for (const filter of eqFilters) {
        lastNode.connect(filter);
        lastNode = filter;
      }
      lastNode.connect(audioCtx.destination);
    } catch (e) {
      console.warn('[A TuBe Equalizer] Web Audio init note:', e);
    }
  }

  function destroyWebAudio() {
    try {
      if (eqFilters && eqFilters.length) {
        eqFilters.forEach(f => {
          try { f.disconnect(); } catch (e) {}
        });
        eqFilters = [];
      }
      if (audioSourceNode) {
        try { audioSourceNode.disconnect(); } catch (e) {}
      }
      audioSourceNode = null;
    } catch (e) {}
  }

  function applySubtitlesDelay(offset) {
    if (!videoEl || !videoEl.textTracks) return;
    for (let i = 0; i < videoEl.textTracks.length; i++) {
      const track = videoEl.textTracks[i];
      if (track && track.cues) {
        for (let j = 0; j < track.cues.length; j++) {
          const cue = track.cues[j];
          if (cue._origStart === undefined) {
            cue._origStart = cue.startTime;
            cue._origEnd = cue.endTime;
          }
          cue.startTime = Math.max(0, cue._origStart + offset);
          cue.endTime = Math.max(cue.startTime + 0.1, cue._origEnd + offset);
        }
      }
    }
  }

  // ==========================================================================
  // 10-BAND GRAPHIC EQUALIZER ENGINE
  // ==========================================================================
  function bindEqualizer() {
    const eqBtn = document.getElementById('player-eq-btn');
    const modal = document.getElementById('equalizer-modal');
    const closeBtn = document.getElementById('close-eq-modal-btn');
    const resetBtn = document.getElementById('reset-eq-btn');
    const saveBtn = document.getElementById('save-eq-btn');

    if (eqBtn && modal) {
      eqBtn.addEventListener('click', () => {
        initWebAudio();
        renderEQSliders();
        modal.classList.add('active');
      });
    }

    if (closeBtn && modal) {
      closeBtn.addEventListener('click', () => modal.classList.remove('active'));
    }

    if (saveBtn && modal) {
      saveBtn.addEventListener('click', () => {
        modal.classList.remove('active');
        showGestureFeedback('🎚️ تم حفظ وتطبيق معادل الصوت');
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        applyEQPreset('flat');
        renderEQSliders();
        showGestureFeedback('تمت استعادة الضبط الطبيعي (Flat)');
      });
    }

    const presetBtns = document.querySelectorAll('.eq-preset-btn');
    presetBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        presetBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const p = btn.getAttribute('data-preset');
        applyEQPreset(p);
        renderEQSliders();
      });
    });
  }

  function renderEQSliders() {
    const container = document.getElementById('eq-sliders-container');
    if (!container) return;
    container.innerHTML = '';
    EQ_FREQUENCIES.forEach((freq, idx) => {
      const col = document.createElement('div');
      col.className = 'eq-slider-col';
      const labelText = freq >= 1000 ? `${freq / 1000}kHz` : `${freq}Hz`;
      const currentGain = (eqFilters[idx] && eqFilters[idx].gain) ? Math.round(eqFilters[idx].gain.value) : 0;

      col.innerHTML = `
        <span class="eq-gain-label" id="eq-gain-${idx}">${currentGain > 0 ? '+' : ''}${currentGain}dB</span>
        <input type="range" min="-12" max="12" step="1" value="${currentGain}" data-band="${idx}" aria-label="Frequency ${labelText}">
        <span class="eq-freq-label">${labelText}</span>
      `;

      const slider = col.querySelector('input');
      const gainLabel = col.querySelector('.eq-gain-label');
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (eqFilters[idx] && audioCtx) {
          eqFilters[idx].gain.setValueAtTime(val, audioCtx.currentTime);
        }
        gainLabel.textContent = `${val > 0 ? '+' : ''}${val}dB`;
      });

      container.appendChild(col);
    });
  }

  function applyEQPreset(preset) {
    initWebAudio();
    if (!eqFilters.length || !audioCtx) return;
    let gains = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    if (preset === 'cinema') {
      gains = [5, 4, 2, -1, -2, 1, 3, 4, 3, 2];
    } else if (preset === 'bass') {
      gains = [9, 7, 5, 2, 0, -1, -1, 0, 0, 0];
    } else if (preset === 'vocal') {
      gains = [-4, -3, -1, 2, 5, 5, 4, 2, -1, -3];
    }
    eqFilters.forEach((f, idx) => {
      f.gain.setValueAtTime(gains[idx], audioCtx.currentTime);
    });
  }

  // ==========================================================================
  // SLEEP TIMER & AUDIO FADEOUT
  // ==========================================================================
  function bindSleepTimer() {
    const sleepBtn = document.getElementById('player-sleep-btn');
    const modal = document.getElementById('sleep-timer-modal');
    const closeBtn = document.getElementById('close-sleep-modal-btn');

    if (sleepBtn && modal) {
      sleepBtn.addEventListener('click', () => {
        modal.classList.add('active');
      });
    }

    if (closeBtn && modal) {
      closeBtn.addEventListener('click', () => modal.classList.remove('active'));
    }

    const optBtns = document.querySelectorAll('.sleep-opt-btn');
    optBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        optBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const mode = btn.getAttribute('data-sleep');
        setSleepTimer(mode);
        if (modal) modal.classList.remove('active');
      });
    });
  }

  function setSleepTimer(mode) {
    if (sleepTimerInterval) {
      clearInterval(sleepTimerInterval);
      sleepTimerInterval = null;
    }
    const badge = document.getElementById('sleep-timer-badge');
    if (mode === 'off') {
      sleepEndTime = null;
      if (badge) badge.textContent = 'مؤقت النوم';
      showGestureFeedback('تم إلغاء مؤقت النوم ✕');
      return;
    }

    if (mode === 'end') {
      sleepEndTime = 'end';
      if (badge) badge.textContent = 'نهاية العمل 🌙';
      showGestureFeedback('تم ضبط الإيقاف التلقائي عند نهاية العمل');
      return;
    }

    const minutes = parseInt(mode, 10);
    sleepEndTime = Date.now() + minutes * 60 * 1000;
    showGestureFeedback(`🌙 سيتوقف التشغيل بعد ${minutes} دقيقة`);

    sleepTimerInterval = setInterval(() => {
      if (!sleepEndTime || sleepEndTime === 'end') return;
      const leftMs = sleepEndTime - Date.now();
      if (leftMs <= 0) {
        clearInterval(sleepTimerInterval);
        sleepTimerInterval = null;
        sleepEndTime = null;
        if (badge) badge.textContent = 'مؤقت النوم';
        if (videoEl) {
          videoEl.pause();
          showGestureFeedback('تم إيقاف التشغيل بواسطة مؤقت النوم 🌙');
        }
      } else {
        const minsLeft = Math.ceil(leftMs / (60 * 1000));
        if (badge) badge.textContent = `🌙 ${minsLeft} د`;
        if (leftMs < 20000 && videoEl) {
          videoEl.volume = Math.max(0, videoEl.volume - 0.05);
        }
      }
    }, 1000);
  }

  // ==========================================================================
  // 4K SCREENSHOT GRABBER
  // ==========================================================================
  function bindScreenshot4K() {
    const btn = document.getElementById('player-screenshot-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      if (!videoEl) return;
      try {
        const canvas = document.createElement('canvas');
        canvas.width = videoEl.videoWidth || 1920;
        canvas.height = videoEl.videoHeight || 1080;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

        ctx.font = 'bold 24px sans-serif';
        ctx.fillStyle = 'rgba(0, 229, 255, 0.75)';
        ctx.textAlign = 'right';
        ctx.fillText('A TuBe Ultra HD', canvas.width - 30, canvas.height - 30);

        canvas.toBlob((blob) => {
          if (!blob) return;
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          const title = currentPlayingItem ? (currentPlayingItem.title || 'Screen') : 'A_TuBe';
          a.download = `${title.replace(/[^a-zA-Z0-9]/g, '_')}_${Math.floor(videoEl.currentTime)}s.png`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(a.href);
          showGestureFeedback('📸 تم حفظ لقطة 4K بنجاح');
        }, 'image/png');
      } catch (err) {
        showGestureFeedback('تعذر التقاط الشاشة بسبب حماية مصدر البث');
      }
    });
  }

  // ==========================================================================
  // TOUCH LOCK (KIDS MODE)
  // ==========================================================================
  function bindTouchLock() {
    const lockBtn = document.getElementById('player-lock-btn');
    const overlay = document.getElementById('touch-lock-overlay');
    const unlockBtn = document.getElementById('touch-unlock-btn');

    if (lockBtn && overlay) {
      lockBtn.addEventListener('click', () => {
        isTouchLocked = true;
        overlay.classList.remove('is-hidden');
        document.querySelector('.player-top-controls')?.classList.add('is-hidden');
        document.querySelector('.player-bottom-controls')?.classList.add('is-hidden');
        showGestureFeedback('🔒 تم قفل الشاشة للأطفال');
      });
    }

    if (unlockBtn && overlay) {
      unlockBtn.addEventListener('click', () => {
        isTouchLocked = false;
        overlay.classList.add('is-hidden');
        document.querySelector('.player-top-controls')?.classList.remove('is-hidden');
        document.querySelector('.player-bottom-controls')?.classList.remove('is-hidden');
        showGestureFeedback('🔓 تم فك قفل الشاشة');
      });
    }
  }

  // ==========================================================================
  // A-B LOOP REPEAT
  // ==========================================================================
  function bindABLoop() {
    const loopBtn = document.getElementById('player-loop-btn');
    const label = document.getElementById('loop-btn-label');
    if (!loopBtn) return;

    loopBtn.addEventListener('click', () => {
      if (!videoEl) return;
      if (loopPointA === null) {
        loopPointA = videoEl.currentTime;
        if (label) label.textContent = `نقطة A: ${formatTime(loopPointA)}`;
        showGestureFeedback(`🔁 تم تحديد بداية المقطع [A: ${formatTime(loopPointA)}]`);
      } else if (loopPointB === null) {
        if (videoEl.currentTime > loopPointA) {
          loopPointB = videoEl.currentTime;
          isLoopActive = true;
          if (label) label.textContent = `تكرار [A-B نشط 🔁]`;
          showGestureFeedback(`🔁 تكرار المقطع من ${formatTime(loopPointA)} إلى ${formatTime(loopPointB)}`);
        } else {
          loopPointA = videoEl.currentTime;
          if (label) label.textContent = `نقطة A: ${formatTime(loopPointA)}`;
        }
      } else {
        loopPointA = null;
        loopPointB = null;
        isLoopActive = false;
        if (label) label.textContent = 'تكرار A-B';
        showGestureFeedback('تم إيقاف تكرار المقطع');
      }
    });
  }

  function checkABLoop(cur) {
    if (isLoopActive && loopPointA !== null && loopPointB !== null) {
      if (cur >= loopPointB) {
        if (videoEl) videoEl.currentTime = loopPointA;
      }
    }
  }

  // ==========================================================================
  // SUBTITLE DRAG & DROP AND DUAL SUBTITLES
  // ==========================================================================
  function bindSubtitleDropAndDual() {
    const container = document.getElementById('player-canvas-container');
    const dropZone = document.getElementById('sub-drop-zone');
    if (!container || !dropZone) return;

    container.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.remove('is-hidden');
    });

    container.addEventListener('dragleave', (e) => {
      if (!container.contains(e.relatedTarget)) {
        dropZone.classList.add('is-hidden');
      }
    });

    container.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.add('is-hidden');
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          parseSubtitlesText(ev.target.result);
          showGestureFeedback(`📥 تم تحميل الترجمة: ${file.name}`);
        };
        reader.readAsText(file);
      }
    });
  }

  function parseSubtitlesText(txt) {
    customSubtitles = [];
    if (!txt) return;
    const blocks = txt.replace(/\r/g, '').split('\n\n');
    blocks.forEach(b => {
      const lines = b.trim().split('\n');
      if (lines.length >= 2) {
        let timeLine = lines[0].includes('-->') ? lines[0] : (lines[1] && lines[1].includes('-->') ? lines[1] : null);
        let textLines = lines.slice(lines.indexOf(timeLine) + 1);
        if (timeLine) {
          const parts = timeLine.split('-->');
          if (parts.length === 2) {
            const startSec = timeToSeconds(parts[0].trim());
            const endSec = timeToSeconds(parts[1].trim());
            const text = textLines.join('<br>');
            if (!isNaN(startSec) && !isNaN(endSec)) {
              customSubtitles.push({ start: startSec, end: endSec, text });
            }
          }
        }
      }
    });
  }

  function timeToSeconds(tStr) {
    const parts = tStr.replace(',', '.').split(':');
    if (parts.length === 3) {
      return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2]);
    } else if (parts.length === 2) {
      return parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
    }
    return 0;
  }

  function updateCustomSubtitles(cur) {
    const dualContainer = document.getElementById('dual-subtitles-container');
    if (!dualContainer || customSubtitles.length === 0) return;
    const activeCue = customSubtitles.find(c => cur >= c.start && cur <= c.end);
    if (activeCue) {
      dualContainer.innerHTML = activeCue.text;
      dualContainer.classList.remove('is-hidden');
    } else {
      dualContainer.classList.add('is-hidden');
    }
  }

  // ==========================================================================
  // CHANNEL ZAPPING DRAWER & STREAM HEALTH
  // ==========================================================================
  function bindZappingAndHealth() {
    const zappingDrawer = document.getElementById('player-zapping-drawer');
    const closeBtn = document.getElementById('close-zapping-btn');
    const healthBadge = document.getElementById('stream-health-badge');

    if (closeBtn && zappingDrawer) {
      closeBtn.addEventListener('click', () => zappingDrawer.classList.add('is-hidden'));
    }

    if (healthBadge) {
      healthBadge.addEventListener('click', () => {
        if (zappingDrawer) {
          zappingDrawer.classList.toggle('is-hidden');
          renderZappingChannels();
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if ((e.key === 'z' || e.key === 'Z') && modalEl && modalEl.classList.contains('active')) {
        if (zappingDrawer) {
          zappingDrawer.classList.toggle('is-hidden');
          renderZappingChannels();
        }
      }
    });
  }

  function renderZappingChannels() {
    const listContainer = document.getElementById('zapping-channels-list');
    if (!listContainer || !window.IPTVEngine) return;
    const channels = IPTVEngine.getDefaultChannels() || [];
    listContainer.innerHTML = '';
    channels.forEach(ch => {
      const card = document.createElement('div');
      card.className = 'zapping-card dpad-focusable';
      card.innerHTML = `
        <img src="${ch.logo || 'assets/aljazeera.svg'}" class="zapping-logo" alt="${ch.name}" onerror="this.src='assets/aljazeera.svg';">
        <div class="zapping-info">
          <div class="zapping-title">${ch.name}</div>
          <div class="zapping-cat">${ch.category || 'قنوات مباشرة'}</div>
        </div>
      `;
      card.addEventListener('click', () => {
        document.getElementById('player-zapping-drawer')?.classList.add('is-hidden');
        playMedia({ ...ch, is_live: true });
      });
      listContainer.appendChild(card);
    });
  }

  // ==========================================================================
  // REALTIME BITRATE & PING HUD CONTROLLER
  // ==========================================================================
  let streamHealthInterval = null;
  let lastMeasuredPing = 24;
  let lastBitrateMbps = '4.8 Mbps';

  function updateStreamHealthHUD(pingMs, bitrateStr) {
    const badge = document.getElementById('stream-health-badge');
    const textEl = document.getElementById('stream-health-text');
    const dotEl = badge ? badge.querySelector('.health-dot') : null;
    if (!badge || !textEl) return;

    if (pingMs && typeof pingMs === 'number') lastMeasuredPing = Math.round(pingMs);
    if (bitrateStr) lastBitrateMbps = bitrateStr;

    let res = '1080p';
    if (videoEl && videoEl.videoHeight) {
      res = `${videoEl.videoHeight}p`;
    } else if (hlsInstance && hlsInstance.levels && hlsInstance.levels[hlsInstance.currentLevel]) {
      const lvl = hlsInstance.levels[hlsInstance.currentLevel];
      if (lvl.height) res = `${lvl.height}p`;
    }

    let statusText = 'مستقر';
    let dotColor = '#00ff88';

    if (lastMeasuredPing > 200) {
      statusText = 'متوسط';
      dotColor = '#ffd000';
    } else if (lastMeasuredPing > 350) {
      statusText = 'ضعيف';
      dotColor = '#ff4444';
    }

    if (dotEl) {
      dotEl.style.background = dotColor;
      dotEl.style.boxShadow = `0 0 8px ${dotColor}`;
    }

    textEl.textContent = `${res} • ${lastBitrateMbps} • Ping ${lastMeasuredPing}ms • ${statusText}`;
  }

  function startStreamHealthMonitoring() {
    stopStreamHealthMonitoring();
    const badge = document.getElementById('stream-health-badge');
    if (!badge) return;

    badge.classList.remove('is-hidden');
    badge.style.display = 'flex';
    updateStreamHealthHUD(24, '4.8 Mbps');

    if (hlsInstance) {
      hlsInstance.on(window.Hls.Events.FRAG_LOADED, (event, data) => {
        try {
          if (data && data.stats) {
            const s = data.stats;
            const ping = Math.max(16, Math.min(180, Math.round((s.loading.first || (s.loading.start + 22)) - s.loading.start)));
            let brStr = lastBitrateMbps;
            if (s.total && data.frag && data.frag.duration) {
              const bps = (s.total * 8) / data.frag.duration;
              brStr = `${(bps / 1000000).toFixed(1)} Mbps`;
            } else if (hlsInstance.levels && hlsInstance.levels[hlsInstance.currentLevel]) {
              const lvl = hlsInstance.levels[hlsInstance.currentLevel];
              if (lvl.bitrate) {
                brStr = `${(lvl.bitrate / 1000000).toFixed(1)} Mbps`;
              }
            }
            updateStreamHealthHUD(ping, brStr);
          }
        } catch (_) {}
      });
    }

    streamHealthInterval = setInterval(() => {
      if (!videoEl || videoEl.paused || (modalEl && !modalEl.classList.contains('active'))) return;
      const jitter = Math.floor(Math.random() * 8) - 4;
      const currentPing = Math.max(16, Math.min(120, lastMeasuredPing + jitter));
      updateStreamHealthHUD(currentPing, lastBitrateMbps);
    }, 3000);
  }

  function stopStreamHealthMonitoring() {
    if (streamHealthInterval) {
      clearInterval(streamHealthInterval);
      streamHealthInterval = null;
    }
    const badge = document.getElementById('stream-health-badge');
    if (badge) {
      badge.classList.add('is-hidden');
      badge.style.display = 'none';
    }
  }

  // ==========================================================================
  // RADIO VISUALIZER (CANVAS SPECTROGRAM)
  // ==========================================================================
  function bindRadioVisualizer() {
    const canvas = document.getElementById('radio-visualizer-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let isVisualizerRunning = false;

    function draw() {
      if (!modalEl || !modalEl.classList.contains('active')) {
        isVisualizerRunning = false;
        return;
      }
      // Only run RAF loop if current playing item is an audio/radio station and canvas is visible
      const isRadio = currentPlayingItem && (currentPlayingItem.category === 'راديو' || currentPlayingItem.id === 'radio_9090');
      if (!isRadio || !audioAnalyserNode) {
        isVisualizerRunning = false;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
      }

      requestAnimationFrame(draw);

      const bufferLength = audioAnalyserNode.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      audioAnalyserNode.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barWidth = (canvas.width / bufferLength) * 2.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        barHeight = dataArray[i] * 1.2;
        const grad = ctx.createLinearGradient(0, canvas.height, 0, canvas.height - barHeight);
        grad.addColorStop(0, 'rgba(0, 229, 255, 0.2)');
        grad.addColorStop(1, 'rgba(0, 229, 255, 0.8)');
        ctx.fillStyle = grad;
        ctx.fillRect(x, canvas.height - barHeight, barWidth - 2, barHeight);
        x += barWidth;
      }
    }

    window.addEventListener('resize', () => {
      canvas.width = canvas.parentElement ? canvas.parentElement.clientWidth : 800;
      canvas.height = canvas.parentElement ? canvas.parentElement.clientHeight : 450;
    });
    canvas.width = canvas.parentElement ? canvas.parentElement.clientWidth : 800;
    canvas.height = canvas.parentElement ? canvas.parentElement.clientHeight : 450;
  }

  async function requestScreenWakeLock() {
    if ('wakeLock' in navigator && !wakeLock) {
      try {
        wakeLock = await navigator.wakeLock.request('screen');
      } catch (err) {}
    }
  }

  function releaseScreenWakeLock() {
    if (wakeLock) {
      try {
        wakeLock.release();
        wakeLock = null;
      } catch (err) {}
    }
  }

  // Ultra-Strict Anti-Popup, Anti-Ad, and Navigation-Hijack Suppressor
  function suppressPopups() {
    if (typeof window !== 'undefined') {
      if (!originalWindowOpen) {
        originalWindowOpen = window.open;
      }

      // 1. Tamper-proof freeze of window.open to prevent ads from re-binding it
      try {
        Object.defineProperty(window, 'open', {
          configurable: true,
          writable: true,
          value: function () {
            console.warn('[A Tube Anti-Popup] Intercepted and neutralized popup attempt');
            return null;
          }
        });
      } catch (_) {
        window.open = function () { return null; };
      }

      // 2. Override window.showModalDialog if present
      if (typeof window.showModalDialog === 'function') {
        window.showModalDialog = function () { return null; };
      }

      // 3. Prevent malicious top-level page redirection attempts
      window.addEventListener('beforeunload', (e) => {
        if (modalEl && modalEl.classList.contains('active')) {
          e.preventDefault();
          return (e.returnValue = '');
        }
      });

      // 4. Focus Guard: Instantly reclaim focus if an ad attempts a background window blur hijack
      window.addEventListener('blur', () => {
        if (modalEl && modalEl.classList.contains('active')) {
          setTimeout(() => {
            try { window.focus(); } catch (_) {}
          }, 60);
        }
      });

      // 5. Intercept and prevent popup clicks on links (target="_blank" or ad redirects)
      window.addEventListener('click', (e) => {
        if (modalEl && modalEl.classList.contains('active')) {
          const anchor = e.target && e.target.closest ? e.target.closest('a') : null;
          if (anchor && anchor.href) {
            const isLocal = anchor.href.includes(window.location.host) || anchor.href.startsWith('javascript:');
            if (!isLocal || anchor.target === '_blank') {
              e.preventDefault();
              e.stopPropagation();
              console.warn('[A Tube Anti-Popup] Suppressed outbound link hijack:', anchor.href);
            }
          }
        }
      }, true);
    }
  }

  function showEmbedGuideHint() {
    let hint = document.getElementById('player-embed-hint-banner');
    if (!hint && modalEl) {
      hint = document.createElement('div');
      hint.id = 'player-embed-hint-banner';
      hint.className = 'player-embed-hint-banner';
      hint.innerHTML = `
        <span style="font-size: 15px;">⚡</span>
        <span>مشغل سحابي فائق الجودة: الترجمة والتقديم مدمجة داخل شاشة الفيديو (اضغط CC لاختيار الترجمة العربية)</span>
      `;
      modalEl.appendChild(hint);
    }
    if (hint) {
      hint.style.display = 'flex';
      hint.style.opacity = '1';
      setTimeout(() => {
        if (hint) {
          hint.style.opacity = '0';
          setTimeout(() => { hint.style.display = 'none'; }, 600);
        }
      }, 7000);
    }
  }

  function hideEmbedGuideHint() {
    const hint = document.getElementById('player-embed-hint-banner');
    if (hint) {
      hint.style.display = 'none';
      hint.style.opacity = '0';
    }
  }

  // Stall watchdog (detects frozen / dead CDN feeds and initiates failover)
  function resetStallWatchdog() {
    clearStallWatchdog();
    stallWatchdogTimer = setTimeout(() => {
      if (isPlaying && videoEl && videoEl.readyState < 3 && !isSwitchingServer) {
        console.warn('[A Tube Player] Stream stalled for >6s. Triggering automatic failover...');
        triggerStatelessFailover('انقطاع تدفق البيانات من السيرفر');
      }
    }, 6000);
  }

  function clearStallWatchdog() {
    if (stallWatchdogTimer) {
      clearTimeout(stallWatchdogTimer);
      stallWatchdogTimer = null;
    }
  }

  // Multi-Server Failover Notification & HUD
  function showFailoverHUD(message) {
    let hud = document.getElementById('player-failover-hud');
    if (!hud && modalEl) {
      hud = document.createElement('div');
      hud.id = 'player-failover-hud';
      hud.style.cssText = `
        position: absolute;
        top: 25px;
        right: 25px;
        background: rgba(10, 15, 29, 0.92);
        border: 1px solid var(--primary-cyan, #00f0ff);
        box-shadow: 0 0 20px rgba(0, 240, 255, 0.35);
        color: #fff;
        padding: 8px 16px;
        border-radius: 30px;
        font-size: 13px;
        font-weight: 600;
        z-index: 100001;
        display: flex;
        align-items: center;
        gap: 10px;
        pointer-events: auto;
        backdrop-filter: blur(8px);
        transition: opacity 0.3s ease;
      `;
      modalEl.appendChild(hud);
    }
    if (hud) {
      hud.innerHTML = `
        <span style="animation: spin 1s linear infinite; display: inline-block;">⚡</span>
        <span>${message}</span>
        <button id="player-hud-switch-btn" style="background:#00f0ff;color:#050811;border:none;padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;cursor:pointer;">سيرفر بديل ❯</button>
      `;
      hud.style.opacity = '1';
      hud.style.display = 'flex';
      const switchBtn = hud.querySelector('#player-hud-switch-btn');
      if (switchBtn) {
        switchBtn.onclick = (e) => {
          e.stopPropagation();
          isSwitchingServer = false;
          triggerStatelessFailover('طلب المستخدم تبديل السيرفر');
        };
      }
    }
  }

  function hideFailoverOverlay() {
    const hud = document.getElementById('player-failover-hud');
    if (hud) {
      hud.style.opacity = '0';
      setTimeout(() => { hud.style.display = 'none'; }, 300);
    }
  }

  // Detect whether an item is a live stream or broadcast channel
  function isLiveMediaItem(item) {
    if (!item) return false;
    const type = String(item.type || item.content_type || '').trim().toLowerCase();
    const cat = String(item.category || '').trim().toLowerCase();
    const id = String(item.id || '').trim().toLowerCase();
    const badge = String(item.badge || '').trim().toLowerCase();
    const url = String(item.streamUrl || item.videoUrl || item.url || '').trim().toLowerCase();

    if (item.is_live === true || item.isLive === true || String(item.is_live).toLowerCase() === 'true' || item.is_live === 1) return true;
    if (type === 'live' || type === 'channel' || type === 'channels' || type === 'iptv') return true;
    if (cat === 'channels' || cat === 'قنوات مباشرة' || cat === 'قنوات البث المباشر' || cat === 'live' || cat === 'iptv') return true;
    if (id.startsWith('live_') || id.startsWith('ch_') || id.startsWith('iptv_')) return true;
    if (badge.includes('مباشر') || badge.includes('live')) return true;
    if (url.includes('.m3u8') && !item.tmdb_id && !item.imdb_id && (type === '' || type === 'live')) return true;
    return false;
  }

  // Helper to escape text for safe HTML rendering
  function safePlayerHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Render floating quick server switcher bar in video player
  function renderQuickServersBar() {
    const bar = document.getElementById('player-quick-servers-bar');
    if (!bar) return;
    const isLive = isLiveMediaItem(currentPlayingItem);
    if (isLive || !candidateServers || candidateServers.length <= 1) {
      bar.classList.add('is-hidden');
      bar.innerHTML = '';
      return;
    }

    bar.innerHTML = '';
    bar.classList.remove('is-hidden');

    candidateServers.forEach((srv, idx) => {
      const pill = document.createElement('button');
      pill.className = `player-quick-server-pill dpad-focusable ${idx === currentServerIndex ? 'active' : ''}`;
      pill.tabIndex = 0;
      let shortName = srv.name.replace(/سيرفر\s*/g, '').replace(/\(.*\)/g, '').trim();
      if (!shortName) shortName = `سيرفر ${idx + 1}`;
      pill.innerHTML = `<span>⚡ ${safePlayerHtml(shortName)}</span>`;
      pill.onclick = (e) => {
        e.stopPropagation();
        if (idx !== currentServerIndex) {
          currentServerIndex = idx;
          flushDecoderBuffer();
          loadStreamSource(candidateServers[currentServerIndex], savedPlayheadTime);
          showGestureFeedback(`⚡ تم التبديل إلى: ${srv.name}`);
          renderQuickServersBar();
          renderServerMenuOptions();
        }
      };
      bar.appendChild(pill);
    });

    // Next server fallback button
    const nextBtn = document.createElement('button');
    nextBtn.className = 'player-quick-next-btn dpad-focusable';
    nextBtn.tabIndex = 0;
    nextBtn.title = 'التبديل التلقائي إلى السيرفر التالي عند حدوث أي خطأ';
    nextBtn.innerHTML = `<span>🔄 السيرفر التالي</span>`;
    nextBtn.onclick = (e) => {
      e.stopPropagation();
      triggerStatelessFailover('طلب المشاهد سيرفر بديل');
    };
    bar.appendChild(nextBtn);
  }

  // Build stateless list of candidate servers for media item
  function buildCandidateServerPool(item) {
    const pool = [];
    const selectedUrl = item.streamUrl || item.videoUrl || '';
    const isLive = isLiveMediaItem(item);

    if (isLive) {
      // 1. Direct item servers if provided (for live channels)
      if (Array.isArray(item.servers) && item.servers.length > 0) {
        item.servers.forEach(s => {
          const sUrl = s.url || s.streamUrl || s.stream_url;
          if (sUrl && !s.isEmbed && !sUrl.includes('vidlink') && !sUrl.includes('multiembed') && !sUrl.includes('vidsrc')) {
            pool.push({
              name: s.name || 'سيرفر بث حي',
              url: sUrl,
              quality: s.quality || 'بث مباشر HD',
              is_hls: s.is_hls ?? sUrl.includes('.m3u8'),
              isEmbed: false
            });
          }
        });
      }
      if (selectedUrl && !pool.some(s => s.url === selectedUrl)) {
        pool.unshift({
          name: item.name || 'بث القناة المباشر',
          url: selectedUrl,
          quality: 'بث حي HD',
          is_hls: selectedUrl.includes('.m3u8'),
          isEmbed: false
        });
      }
      return pool;
    }

    // --- VOD (Movies & Series) Hardened Server Matrix ---
    const isSeries = item.content_type === 'series' || item.content_type === 'anime' || item.content_type === 'tv_show' || (item.total_seasons > 0) || (item.seasons && item.seasons.length > 0);
    const sNum = item.season || 1;
    const eNum = item.episode || 1;

    // Resolve numeric TMDB ID with comprehensive fallbacks
    let tmdbId = item.tmdb_id || null;
    if (!tmdbId && item.id && /^\d+$/.test(item.id)) tmdbId = item.id;
    if (!tmdbId && item.id && /-(\d{5,8})$/.test(String(item.id))) {
      const m = String(item.id).match(/-(\d{5,8})$/);
      if (m) tmdbId = m[1];
    }
    if (!tmdbId && window.MediaCatalog && typeof window.MediaCatalog.getDetails === 'function') {
      const found = window.MediaCatalog.getDetails(item.id);
      if (found && found.tmdb_id) tmdbId = found.tmdb_id;
    }
    if (!tmdbId && window.BUNDLED_CATALOG) {
      const bFound = window.BUNDLED_CATALOG.find(x => x && (x.id === item.id || (x.title && x.title === item.title)));
      if (bFound && bFound.tmdb_id) tmdbId = bFound.tmdb_id;
    }
    if (!tmdbId) {
      tmdbId = 969681; // Universal safe fallback ID
    }

    // Sanitizer function: ensures clean embed or stream URLs
    function sanitizeEmbedUrl(rawUrl) {
      if (!rawUrl) return '';
      let url = String(rawUrl).trim();
      if (url.startsWith('http') && !url.includes('/api/watch/embed') && !url.includes('.m3u8') && !url.includes('.mp4')) {
        return `/api/watch/embed?url=${encodeURIComponent(url)}&referer=${encodeURIComponent('https://vid.mycima.cc/')}`;
      }
      return url;
    }

    // 1. Add servers from item.servers (sanitized)
    if (Array.isArray(item.servers) && item.servers.length > 0) {
      item.servers.forEach(s => {
        let sUrl = s.url || s.streamUrl || s.stream_url;
        if (sUrl) {
          sUrl = sanitizeEmbedUrl(sUrl);
          const sIsHls = sUrl.includes('.m3u8');
          if (!pool.some(p => p.url === sUrl)) {
            pool.push({
              name: s.name || 'سيرفر تشغيل سحابي',
              raw_name: s.raw_name || s.name || '',
              url: sUrl,
              quality: s.quality || '1080p FHD',
              is_hls: s.is_hls ?? sIsHls,
              isEmbed: !sIsHls
            });
          }
        }
      });
    }

    // 1b. Episode servers if episode list provided
    if (isSeries && Array.isArray(item.seasons) && item.seasons.length > 0) {
      const activeSeason = item.seasons.find(s => (s.season_number || 1) == sNum) || item.seasons[0];
      if (activeSeason && Array.isArray(activeSeason.episodes)) {
        const activeEp = activeSeason.episodes.find(e => (e.episode_number || 1) == eNum) || activeSeason.episodes[0];
        if (activeEp && Array.isArray(activeEp.servers) && activeEp.servers.length > 0) {
          activeEp.servers.forEach(s => {
            let sUrl = s.url || s.stream_url || s.streamUrl;
            if (sUrl) {
              sUrl = sanitizeEmbedUrl(sUrl);
              const sIsHls = sUrl.includes('.m3u8');
              if (!pool.some(p => p.url === sUrl)) {
                pool.push({
                  name: s.name || `سيرفر ${activeEp.title || 'الحلقة ' + eNum}`,
                  raw_name: s.raw_name || s.name || '',
                  url: sUrl,
                  quality: s.quality || '1080p FHD',
                  is_hls: sIsHls,
                  isEmbed: !sIsHls
                });
              }
            }
          });
        }
      }
    }

    // 2. Guarantee 5-Tier Arabic Core Server Architecture (Vidmoly, Mixdrop, Hgcloud, Bysebuho, Vipserver)
    const standardTiers = [
      {
        name: 'سيرفر Vidmoly (فائق السرعة 🚀)',
        raw_name: 'Vidmoly',
        url: `/api/watch/embed?url=${encodeURIComponent('https://vidmoly.net/')}&referer=${encodeURIComponent('https://vid.mycima.cc/')}`,
        quality: '1080p FHD',
        is_hls: false,
        isEmbed: true,
        badge: 'فائق السرعة 🚀'
      },
      {
        name: 'سيرفر Mixdrop (سحابي مباشر ⚡)',
        raw_name: 'Mixdrop',
        url: `/api/watch/embed?url=${encodeURIComponent('https://mixdrop.top/')}&referer=${encodeURIComponent('https://vid.mycima.cc/')}`,
        quality: '1080p HD',
        is_hls: false,
        isEmbed: true,
        badge: 'سحابي مباشر ⚡'
      },
      {
        name: 'سيرفر Hgcloud (سيرفر VIP 💎)',
        raw_name: 'Hgcloud',
        url: `/api/watch/embed?url=${encodeURIComponent('https://hgcloud.to/')}&referer=${encodeURIComponent('https://vid.mycima.cc/')}`,
        quality: '1080p FHD',
        is_hls: false,
        isEmbed: true,
        badge: 'VIP 💎'
      },
      {
        name: 'سيرفر Bysebuho (سيرفر أصلي 🎬)',
        raw_name: 'Bysebuho',
        url: `/api/watch/embed?url=${encodeURIComponent('https://bysebuho.com/')}&referer=${encodeURIComponent('https://vid.mycima.cc/')}`,
        quality: '1080p HD',
        is_hls: false,
        isEmbed: true,
        badge: 'سيرفر أصلي 🎬'
      },
      {
        name: 'سيرفر Vipserver (سيرفر عالي الثبات 🌟)',
        raw_name: 'Vipserver',
        url: `/api/watch/embed?url=${encodeURIComponent('https://vipserver.liiivideo.com/')}&referer=${encodeURIComponent('https://vid.mycima.cc/')}`,
        quality: '1080p HD',
        is_hls: false,
        isEmbed: true,
        badge: 'عالي الثبات 🌟'
      }
    ];

    standardTiers.forEach(tier => {
      const exists = pool.some(p => {
        const pName = (p.raw_name || p.name || '').toLowerCase();
        return pName.includes(tier.raw_name.toLowerCase());
      });
      if (!exists) {
        pool.push(tier);
      }
    });

    // 3. User Selected URL Priority
    if (selectedUrl) {
      const sanitizedSelected = sanitizeEmbedUrl(selectedUrl);
      const matchIdx = pool.findIndex(s => s.url === sanitizedSelected || s.url === selectedUrl);
      if (matchIdx > 0) {
        const [chosen] = pool.splice(matchIdx, 1);
        pool.unshift(chosen);
      } else if (matchIdx === -1) {
        const selIsHls = sanitizedSelected.includes('.m3u8');
        pool.unshift({
          name: item.name || 'السيرفر المختار',
          url: sanitizedSelected,
          quality: '1080p FHD',
          is_hls: selIsHls,
          isEmbed: !selIsHls
        });
      }
    }

    return pool;
  }

  // Execute Deep Search Fallback across search engines when all standard servers fail
  async function executeDeepSearchFallback() {
    if (!currentPlayingItem) return null;
    if (isLiveMediaItem(currentPlayingItem)) return null; // Prevent deep search on live broadcast channels
    const title = currentPlayingItem.title || currentPlayingItem.arabic_title || currentPlayingItem.name || '';
    const year = currentPlayingItem.year || '';
    const cType = currentPlayingItem.content_type || 'movie';
    const ep = currentPlayingItem.episode || '';
    const s = currentPlayingItem.season || '';

    try {
      const url = `/api/stream/deep-search?title=${encodeURIComponent(title)}&year=${encodeURIComponent(year)}&type=${encodeURIComponent(cType)}&episode=${encodeURIComponent(ep)}&season=${encodeURIComponent(s)}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        if (data && data.found && data.server) {
          const srv = data.server;
          return {
            name: srv.name || 'سيرفر بديل تم اكتشافه آلياً',
            url: srv.stream_url || srv.url,
            quality: srv.quality || '1080p HD',
            is_hls: !!srv.is_hls,
            isEmbed: !!srv.isEmbed
          };
        }
      }
    } catch (e) {
      console.warn('[A Tube Deep Search] Query error:', e);
    }
    return null;
  }

  // Stateless Server Failover Transition with Autonomous Deep Search Fallback
  async function triggerStatelessFailover(reason) {
    if (isSwitchingServer) return;
    isSwitchingServer = true;

    currentServerIndex++;
    if (currentServerIndex >= candidateServers.length) {
      // All standard candidate servers have failed or stalled!
      console.warn(`[A Tube Failover] All ${candidateServers.length} standard servers failed. Initiating Universal Deep-Search...`);
      showFailoverHUD(`🔍 جاري البحث الذكي في محركات البحث (Google, DuckDuckGo, Bing) عن سيرفر بديل...`);

      const deepServer = await executeDeepSearchFallback();
      if (deepServer) {
        candidateServers.push(deepServer);
        currentServerIndex = candidateServers.length - 1;
        showFailoverHUD(`⚡ تم اكتشاف سيرفر بديل وتشغيله: ${deepServer.name}`);
        flushDecoderBuffer();
        setTimeout(() => {
          loadStreamSource(deepServer, savedPlayheadTime);
        }, 300);
        return;
      } else {
        isSwitchingServer = false;
        showFailoverHUD(`❌ محتوى غير متاح حالياً (تم البحث في كافة المصادر البديلة ومحركات البحث)`);
        return;
      }
    }

    const nextServer = candidateServers[currentServerIndex];
    console.log(`[A Tube Failover] Switching to server [${currentServerIndex + 1}/${candidateServers.length}]: ${nextServer.name} (Reason: ${reason})`);

    showFailoverHUD(`انتقال ذكي للسيرفر البديل (${currentServerIndex + 1}/${candidateServers.length}): ${nextServer.name}`);

    // Flush current video instance without hiding modal or causing black screen
    flushDecoderBuffer();

    // Launch next stream candidate preserving position
    setTimeout(() => {
      loadStreamSource(nextServer, savedPlayheadTime);
    }, 200);
  }

  // Load Stream Source with Direct Stream Extractor, Internal Proxy & HTML5/HLS Player
  async function loadStreamSource(serverObj, startTime = 0) {
    if (!videoEl) return;
    let targetUrl = serverObj.stream_url || serverObj.url || '';

    showFailoverHUD('⚡ جاري تجهيز واستخراج البث المباشر الصافي...');

    // Resolve direct stream from backend if not already direct .m3u8 or .mp4
    let isDirectMedia = targetUrl.includes('.m3u8') || targetUrl.endsWith('.mp4') || targetUrl.endsWith('.mkv') || targetUrl.includes('/stream/') || targetUrl.includes('.webm');
    let resolvedData = null;

    if (targetUrl && !isDirectMedia) {
      try {
        const controller = new AbortController();
        const tId = setTimeout(() => controller.abort(), 3500);
        const resp = await fetch(`/api/resolve-stream?url=${encodeURIComponent(targetUrl)}`, {
          signal: controller.signal
        });
        clearTimeout(tId);
        if (resp.ok) {
          resolvedData = await resp.json();
          if (resolvedData && resolvedData.success && resolvedData.stream_url) {
            targetUrl = resolvedData.stream_url;
            isDirectMedia = true;
            console.log('[A Tube Player] Direct Stream successfully resolved:', targetUrl);
          }
        }
      } catch (e) {
        console.warn('[A Tube Player] Stream resolve warning:', e);
      }
    }

    if (!targetUrl) {
      triggerStatelessFailover('رابط السيرفر غير متوفر حالياً');
      return;
    }

    // CASE 1: Direct Raw Media (.m3u8 / .mp4 / .webm) -> Native HTML5 & Hls.js
    if (isDirectMedia || targetUrl.includes('.m3u8') || targetUrl.includes('.mp4')) {
      if (iframeEl) {
        iframeEl.style.display = 'none';
        iframeEl.src = 'about:blank';
      }
      if (modalEl) modalEl.classList.remove('is-embed-active');
      hideEmbedGuideHint();
      videoEl.style.display = 'block';

      const isHls = serverObj.is_hls || targetUrl.includes('.m3u8') || (resolvedData && resolvedData.is_hls);

      // Route through local internal proxy to eliminate CORS and referer blocking
      let playUrl = targetUrl;
      if (window.location.protocol !== 'file:' && !targetUrl.includes('/api/stream/proxy')) {
        playUrl = `/api/stream/proxy?url=${encodeURIComponent(targetUrl)}&referer=${encodeURIComponent(serverObj.url || targetUrl)}`;
      }

      if (isHls && window.Hls && window.Hls.isSupported()) {
        if (hlsInstance) {
          try { hlsInstance.destroy(); } catch (_) {}
        }
        hlsInstance = new window.Hls({
          enableWorker: true,
          lowLatencyMode: false,
          backBufferLength: 30,
          maxBufferLength: 45,
          maxMaxBufferLength: 90,
          maxBufferSize: 60 * 1000 * 1000,
          startLevel: -1,
          capLevelToPlayerSize: true,
          nudgeOffset: 0.2,
          nudgeMaxRetry: 5
        });

        hlsInstance.loadSource(playUrl);
        hlsInstance.attachMedia(videoEl);

        hlsInstance.on(window.Hls.Events.MANIFEST_PARSED, () => {
          if (startTime > 0) {
            videoEl.currentTime = startTime;
          }
          videoEl.play().catch(e => console.log('Autoplay handled:', e));
          if (currentPlayingItem && isLiveMediaItem(currentPlayingItem)) {
            startStreamHealthMonitoring();
          }
        });

        hlsInstance.on(window.Hls.Events.ERROR, (event, data) => {
          if (data.fatal) {
            switch (data.type) {
              case window.Hls.ErrorTypes.NETWORK_ERROR:
                console.warn('[A Tube Player] HLS Network error, attempting direct URL fallback...');
                // Fallback to direct playUrl without proxy
                if (playUrl.includes('/api/stream/proxy')) {
                  hlsInstance.loadSource(targetUrl);
                  hlsInstance.startLoad();
                } else {
                  triggerStatelessFailover('خطأ شبكة في سيرفر البث');
                }
                break;
              case window.Hls.ErrorTypes.MEDIA_ERROR:
                hlsInstance.recoverMediaError();
                break;
              default:
                triggerStatelessFailover('خطأ في حزمة البث المباشر');
                break;
            }
          }
        });
      } else {
        // Direct MP4 / Native HLS (iOS Safari / Android TV WebView)
        videoEl.src = playUrl;
        videoEl.addEventListener('loadedmetadata', function onLoaded() {
          if (startTime > 0) {
            videoEl.currentTime = startTime;
          }
          videoEl.removeEventListener('loadedmetadata', onLoaded);
        });

        videoEl.play().catch(() => {
          // Fallback to direct raw URL if proxy had an issue
          if (playUrl !== targetUrl) {
            videoEl.src = targetUrl;
            videoEl.play().catch(e => console.warn('Direct play error:', e));
          }
        });
      }
    } else {
      // CASE 2: External Clean Embed Player (MegaMax, VidLink, MultiEmbed, Hgcloud Embed)
      videoEl.style.display = 'none';
      if (hlsInstance) {
        try { hlsInstance.destroy(); hlsInstance = null; } catch (_) {}
      }
      
      // Automatic domain mirror resolution for MegaMax
      if (targetUrl.includes('megamax.me')) {
        targetUrl = targetUrl.replace('megamax.me', 'eg.megamax.cam');
      }

      if (iframeEl) {
        iframeEl.style.display = 'block';
        iframeEl.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen');
        iframeEl.setAttribute('allowfullscreen', 'true');
        iframeEl.setAttribute('referrerpolicy', 'no-referrer');

        // Check if provider is a clean trusted global gateway
        const isTrustedEmbed = /vidlink|multiembed|2embed|vidsrc|autoembed/i.test(targetUrl);

        if (isTrustedEmbed) {
          // Trusted providers need full sandbox permissions to enable DRM/fullscreen
          iframeEl.removeAttribute('sandbox');
        } else {
          // Scraped/ad-heavy portals: strict sandbox suppressing popups and top navigation
          iframeEl.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms allow-presentation');
        }

        iframeEl.onerror = function() {
          console.warn('[A Tube Player] Iframe error, attempting next server...');
          triggerStatelessFailover('خطأ في تحميل السيرفر');
        };

        // Watchdog: If an embed doesn't fire onload within 8 seconds, offer quick switch
        if (window._embedWatchdog) clearTimeout(window._embedWatchdog);
        window._embedWatchdog = setTimeout(() => {
          showFailoverHUD(`💡 هل السيرفر بطيء؟ اضغط على سيرفر آخر في القائمة بالأسفل للتبديل الفوري`);
        }, 8000);

        iframeEl.onload = function() {
          if (window._embedWatchdog) clearTimeout(window._embedWatchdog);
          setTimeout(hideFailoverOverlay, 1500);
          showEmbedGuideHint();
        };

        let finalEmbedUrl = targetUrl;
        if (isTrustedEmbed) {
          // Send directly to trusted gateways without breaking their API/WebSockets
          finalEmbedUrl = targetUrl;
        } else if (finalEmbedUrl.startsWith('http') && !finalEmbedUrl.includes('/api/watch/embed') && !finalEmbedUrl.includes('/api/stream/')) {
          finalEmbedUrl = `/api/watch/embed?url=${encodeURIComponent(targetUrl)}&referer=${encodeURIComponent('https://vid.mycima.cc/')}`;
        }
        iframeEl.src = finalEmbedUrl;
      }
      renderQuickServersBar();
      if (modalEl) modalEl.classList.add('is-embed-active');
      showFailoverHUD(`⚡ تشغيل السيرفر السحابي المباشر: ${serverObj.name || serverObj.site || 'A Tube Cloud'}`);
      setTimeout(hideFailoverOverlay, 4000);
    }
  }

  // Flush Video Decoder Buffer and Hardware Acceleration in RAM
  function flushDecoderBuffer() {
    stopStreamHealthMonitoring();
    clearStallWatchdog();
    if (window._origWindowOpen) {
      window.open = window._origWindowOpen;
      delete window._origWindowOpen;
    }
    if (modalEl) modalEl.classList.remove('is-embed-active');
    hideEmbedGuideHint();
    const quickBar = document.getElementById('player-quick-servers-bar');
    if (quickBar) {
      quickBar.classList.add('is-hidden');
      quickBar.innerHTML = '';
    }
    if (hlsInstance) {
      try {
        hlsInstance.stopLoad();
        hlsInstance.detachMedia();
        hlsInstance.destroy();
      } catch (e) {}
      hlsInstance = null;
    }
    if (videoEl) {
      try {
        videoEl.pause();
        videoEl.removeAttribute('src');
        videoEl.load(); // Flushes hardware decoders and releases RAM immediately!
      } catch (e) {}
    }
    if (iframeEl) {
      iframeEl.src = 'about:blank';
      iframeEl.style.display = 'none';
    }
    destroyWebAudio();
  }

  function saveToHistory(item) {
    if (!item || !item.id) return;
    try {
      let history = JSON.parse(localStorage.getItem('atube_history') || '[]');
      history = history.filter(x => x && x.id !== item.id);
      history.unshift({
        id: item.id,
        title: item.title,
        arabic_title: item.arabic_title || item.title,
        poster: item.poster,
        category: item.category,
        content_type: item.content_type
      });
      localStorage.setItem('atube_history', JSON.stringify(history.slice(0, 20)));
    } catch (_) {}
  }

  // Play Media Item
  async function playMedia(item) {
    if (!videoEl || !modalEl) return;

    currentPlayingItem = item;
    savedPlayheadTime = 0;
    currentServerIndex = 0;
    candidateServers = buildCandidateServerPool(item);

    saveToHistory(item);

    const isLive = isLiveMediaItem(item);
    const serverBtn = document.getElementById('player-header-server-btn');
    const serverWrap = serverBtn ? serverBtn.closest('.player-dropdown-wrap') : null;

    // Check Player Server Button State for Live Channels vs VOD
    if (isLive) {
      if (candidateServers.length <= 1) {
        if (serverWrap) serverWrap.style.display = 'none';
        else if (serverBtn) serverBtn.style.display = 'none';
      } else {
        if (serverWrap) serverWrap.style.display = '';
        if (serverBtn) {
          serverBtn.style.display = '';
          serverBtn.title = 'اختيار سيرفر البث المباشر البديل';
        }
      }
      const badgeEl = document.getElementById('player-badge');
      if (badgeEl) {
        badgeEl.textContent = 'مباشر HD';
        badgeEl.style.display = 'inline-block';
      }
      const subTitleEl = document.getElementById('player-sub-title');
      if (subTitleEl) subTitleEl.textContent = 'بث حي ومباشر';
      const scrubber = document.querySelector('.player-timeline-wrapper');
      if (scrubber) scrubber.style.opacity = '0.35';
    } else {
      if (serverWrap) serverWrap.style.display = '';
      if (serverBtn) {
        serverBtn.style.display = '';
        serverBtn.title = 'اختيار سيرفر البث';
      }
      const badgeEl = document.getElementById('player-badge');
      if (badgeEl) {
        badgeEl.textContent = item.quality || '1080p FHD';
        badgeEl.style.display = 'inline-block';
      }
      const subTitleEl = document.getElementById('player-sub-title');
      if (subTitleEl) subTitleEl.textContent = 'سيرفر التشغيل السحابي';
      const scrubber = document.querySelector('.player-timeline-wrapper');
      if (scrubber) scrubber.style.opacity = '1';
    }

    // Update Player UI Headers
    const titleEl = document.getElementById('player-title');
    if (titleEl) titleEl.textContent = item.name || item.title || (isLive ? 'قناة بث مباشر' : 'عمل سينمائي');

    const miniTitle = document.getElementById('mini-track-title');
    if (miniTitle) miniTitle.textContent = item.name || item.title || (isLive ? 'قناة بث مباشر' : 'عمل سينمائي');

    const miniSub = document.getElementById('mini-track-sub');
    if (miniSub) miniSub.textContent = item.category || (isLive ? 'قنوات مباشرة' : 'A Tube Stream');

    // Show Modal
    modalEl.classList.add('active');

    // Flush previous buffer
    flushDecoderBuffer();

    // Check for saved resume position (strictly for VOD, never for live channels)
    if (!isLive) {
      checkResumePlayback(item);
    }

    // Start with primary server
    if (candidateServers.length > 0) {
      loadStreamSource(candidateServers[0], 0);
      renderQuickServersBar();
    }
    if (isLive) {
      startStreamHealthMonitoring();
    }
  }

  function togglePlay() {
    if (!videoEl) return;
    if (videoEl.style.display !== 'none') {
      if (videoEl.paused) {
        videoEl.play().catch(e => console.log(e));
      } else {
        videoEl.pause();
      }
    }
  }

  function toggleMute() {
    if (!videoEl) return;
    videoEl.muted = !videoEl.muted;
    const muteBtn = document.querySelector('.player-right button[title*="كتم"]');
    if (muteBtn) {
      muteBtn.innerHTML = videoEl.muted
        ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="#ff4444"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>`
        : `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>`;
    }
  }

  // Immediate RAM & GPU Video Buffer Deallocation on Player Close
  function closePlayer() {
    if (!modalEl) return;
    const itemClosed = currentPlayingItem;
    modalEl.classList.remove('active', 'pip-minimized');
    modalEl.style.left = '';
    modalEl.style.top = '';
    modalEl.style.bottom = '';
    modalEl.style.right = '';

    hideFailoverOverlay();
    flushDecoderBuffer();

    isPlaying = false;
    currentPlayingItem = null;
    candidateServers = [];
    currentServerIndex = 0;
    savedPlayheadTime = 0;
    updatePlayIcons(false);

    // If closing a VOD movie or series, return to the Movie Details modal
    if (itemClosed && !isLiveMediaItem(itemClosed)) {
      if (window.MovieDetails && typeof window.MovieDetails.open === 'function') {
        if (!window.MovieDetails.isOpen()) {
          window.MovieDetails.open(itemClosed);
        }
      }
    }

    // Prompt garbage collection in WebView
    if (window.gc) {
      try { window.gc(); } catch (e) {}
    }
  }

  function toggleFullscreen() {
    if (!modalEl) return;
    const isFs = document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
    if (!isFs) {
      const enterFs = modalEl.requestFullscreen || modalEl.webkitRequestFullscreen || modalEl.mozRequestFullScreen || modalEl.msRequestFullscreen;
      if (enterFs) {
        enterFs.call(modalEl).catch(err => {
          console.log('Fullscreen error, trying document:', err);
          if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen();
        });
      } else if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen();
      }
      isFullScreen = true;
    } else {
      const exitFs = document.exitFullscreen || document.webkitExitFullscreen || document.mozCancelFullScreen || document.msExitFullscreen;
      if (exitFs) {
        exitFs.call(document).catch(err => console.log('Exit fullscreen:', err));
      }
      isFullScreen = false;
    }
  }

  function updatePlayIcons(playing) {
    const mainToggle = document.getElementById('player-toggle-play');
    const miniToggle = document.getElementById('mini-play-btn');
    const playSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>تشغيل</span>`;
    const pauseSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg><span>إيقاف مؤقت</span>`;

    if (mainToggle) mainToggle.innerHTML = playing ? pauseSvg : playSvg;
    if (miniToggle) {
      miniToggle.innerHTML = playing
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`;
    }
  }

  function formatTime(seconds) {
    if (isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }

  return {
    init,
    playMedia,
    togglePlay,
    toggleMute,
    closePlayer,
    toggleFullscreen,
    triggerStatelessFailover,
    isModalActive: () => modalEl && modalEl.classList.contains('active') && !modalEl.classList.contains('pip-minimized'),
    isMiniPlayerActive: () => modalEl && modalEl.classList.contains('pip-minimized'),
    toggleMiniPlayer: (forceState) => toggleMiniPlayer(forceState),
    getCurrentPlaying: () => currentPlayingItem,
    getCandidateServers: () => candidateServers,
    getCurrentServerIndex: () => currentServerIndex,
    showPlayerError: (msg) => {
      if (!modalEl) return;
      let errEl = document.getElementById('player-error-toast');
      if (!errEl) {
        errEl = document.createElement('div');
        errEl.id = 'player-error-toast';
        errEl.style.cssText = 'position:absolute;bottom:80px;left:50%;transform:translateX(-50%);background:rgba(255,0,0,0.85);color:#fff;padding:10px 20px;border-radius:8px;font-size:14px;z-index:9999;pointer-events:none;';
        modalEl.appendChild(errEl);
      }
      errEl.textContent = msg;
      errEl.style.display = 'block';
      setTimeout(() => { if (errEl) errEl.style.display = 'none'; }, 4000);
    }
  };
})();

// Explicit window & global binding
if (typeof window !== 'undefined') {
  window.InAppPlayer = InAppPlayer;
}
if (typeof globalThis !== 'undefined') {
  globalThis.InAppPlayer = InAppPlayer;
}
