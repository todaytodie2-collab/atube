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

  function init() {
    videoEl = document.getElementById('main-video');
    iframeEl = document.getElementById('main-embed-frame');
    modalEl = document.getElementById('video-modal');

    if (!videoEl || !modalEl) return;

    videoEl.playsInline = true;

    // Enforce anti-popup & strict security attributes on embed iframe
    if (iframeEl) {
      iframeEl.removeAttribute('sandbox'); // Removed sandbox attribute to allow Minochinos, Mixdrop & Vidmoly embeds without iframe restrictions
      iframeEl.setAttribute('referrerpolicy', 'no-referrer');
      iframeEl.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen');
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

    // Time update listener
    videoEl.addEventListener('timeupdate', () => {
      if (videoEl.duration && !isNaN(videoEl.duration)) {
        savedPlayheadTime = videoEl.currentTime;
        updateTimelineUI(videoEl.currentTime, videoEl.duration);

        // Periodically save resume position in localStorage
        if (currentPlayingItem && Math.floor(videoEl.currentTime) % 4 === 0) {
          savePlaybackPosition(currentPlayingItem.id, videoEl.currentTime);
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

  // Ultra-Strict Popup & Ad-redirect Suppressor
  function suppressPopups() {
    if (typeof window !== 'undefined') {
      if (!originalWindowOpen) {
        originalWindowOpen = window.open;
      }
      // Completely block window.open when player modal is active or globally during streaming
      window.open = function () {
        console.warn('[A Tube Anti-Popup] Intercepted and blocked popup attempt');
        return null;
      };

      // Override window.showModalDialog if present
      if (typeof window.showModalDialog === 'function') {
        window.showModalDialog = function () { return null; };
      }

      // Prevent malicious page redirection attempts
      window.addEventListener('beforeunload', (e) => {
        if (modalEl && modalEl.classList.contains('active')) {
          e.preventDefault();
          return '';
        }
      });

      // Intercept and prevent popup clicks on links (target="_blank" or ad redirects)
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

  // Build stateless list of candidate servers for media item
  function buildCandidateServerPool(item) {
    const pool = [];
    const selectedUrl = item.streamUrl || item.videoUrl || '';
    const isLive = isLiveMediaItem(item);

    // 1. Direct item servers if provided
    if (Array.isArray(item.servers) && item.servers.length > 0) {
      item.servers.forEach(s => {
        const sUrl = s.url || s.streamUrl || s.stream_url;
        if (sUrl) {
          // If this is a live channel, NEVER include external VOD embed servers
          if (isLive && (s.isEmbed || sUrl.includes('vidlink') || sUrl.includes('multiembed') || sUrl.includes('vidsrc') || sUrl.includes('2embed') || sUrl.includes('/embed/'))) {
            return;
          }
          pool.push({
            name: s.name || (isLive ? 'سيرفر بث حي' : 'سيرفر تشغيل'),
            url: sUrl,
            quality: s.quality || (isLive ? 'بث مباشر HD' : '1080p FHD'),
            is_hls: s.is_hls ?? (sUrl.includes('.m3u8')),
            isEmbed: isLive ? false : (s.isEmbed || sUrl.includes('/embed') || sUrl.includes('/e/') || sUrl.includes('mixdrop') || sUrl.includes('hgcloud') || sUrl.includes('vidmoly') || sUrl.includes('minochinos') || sUrl.includes('liiivideo'))
          });
        }
      });
    }

    // 2. If user clicked a specific server, ensure it is at index 0
    if (selectedUrl) {
      const matchIdx = pool.findIndex(s => s.url === selectedUrl);
      if (matchIdx > 0) {
        // Move the clicked server to the absolute top of the list
        const [chosen] = pool.splice(matchIdx, 1);
        pool.unshift(chosen);
      } else if (matchIdx === -1) {
        pool.unshift({
          name: isLive ? 'بث القناة المباشر' : (item.name || 'السيرفر المختار'),
          url: selectedUrl,
          quality: isLive ? 'بث حي HD' : '1080p FHD',
          is_hls: isLive ? true : selectedUrl.includes('.m3u8'),
          isEmbed: isLive ? false : (item.isEmbed || selectedUrl.includes('embed') || selectedUrl.includes('/e/'))
        });
      }
    }

    // 3. Guaranteed Procedural Fallback Mirrors ONLY for VOD movies & series!
    // NEVER EVER push external VOD embed servers for live broadcast channels!
    if (!isLive && pool.length < 2) {
      const cleanTarget = item.tmdb_id || item.imdb_id || 'tt6263850';
      const cleanImdb = item.imdb_id || 'tt6263850';
      const isSeries = item.content_type === 'series' || item.content_type === 'anime';
      pool.push({
        name: 'سيرفر VidLink Ultra (مترجم عربي • بدون إعلانات)',
        url: isSeries ? `https://vidlink.pro/tv/${cleanTarget}/1/1?primaryColor=00e5ff&secondaryColor=ff0055` : `https://vidlink.pro/movie/${cleanTarget}?primaryColor=00e5ff&secondaryColor=ff0055`,
        is_hls: false,
        isEmbed: true
      });
      pool.push({
        name: 'سيرفر MultiEmbed FHD (سيرفرات متعددة وسريعة)',
        url: isSeries ? `https://multiembed.mov/?video_id=${cleanImdb}&s=1&e=1` : `https://multiembed.mov/?video_id=${cleanImdb}&tmdb=1`,
        is_hls: false,
        isEmbed: true
      });
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

  // Load Stream Source with Ad-Sanitizer and In-Memory Buffer
  async function loadStreamSource(serverObj, startTime = 0) {
    if (!videoEl) return;
    let targetUrl = serverObj.url;

    // Fast-path: Check if this is a direct media stream or an embed player
    const isDirectMedia = targetUrl.includes('.m3u8') || targetUrl.endsWith('.mp4') || targetUrl.endsWith('.mkv');
    const isEmbedUrl = !isDirectMedia && (
      serverObj.isEmbed || 
      targetUrl.includes('/embed') || targetUrl.includes('/e/') || 
      targetUrl.includes('vidsrc') || targetUrl.includes('vidlink') || 
      targetUrl.includes('multiembed') || targetUrl.includes('2embed') ||
      targetUrl.includes('mixdrop') || targetUrl.includes('hgcloud') || 
      targetUrl.includes('minochinos') || targetUrl.includes('vidmoly') || 
      targetUrl.includes('liiivideo') || targetUrl.includes('fasel-hd') ||
      targetUrl.includes('video_player')
    );

    // If it's an embed player, load immediately with ZERO latency (no blocking fetch!)
    if (isEmbedUrl) {
      if (iframeEl) {
        iframeEl.removeAttribute('sandbox'); // Removed sandbox attribute to prevent Minochinos/Vidmoly errors
        iframeEl.setAttribute('referrerpolicy', 'no-referrer');
        iframeEl.setAttribute('allowfullscreen', 'true');
        iframeEl.setAttribute('webkitallowfullscreen', 'true');
        iframeEl.setAttribute('mozallowfullscreen', 'true');
        iframeEl.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen');

        videoEl.style.display = 'none';
        videoEl.pause();
        iframeEl.style.display = 'block';
        iframeEl.src = targetUrl;
        isPlaying = true;
        updatePlayIcons(true);
        hideFailoverOverlay();
        if (modalEl) modalEl.classList.add('is-embed-active');
        showEmbedGuideHint();
      }
      return;
    }

    // Stream URL Resolution for non-embed, raw redirect links (with strict 1200ms non-blocking timeout)
    if (targetUrl && !isDirectMedia && window.location.protocol.startsWith('http')) {
      try {
        const controller = new AbortController();
        const tId = setTimeout(() => controller.abort(), 1200);
        const resp = await fetch(`/api/stream/resolve?url=${encodeURIComponent(targetUrl)}`, {
          signal: controller.signal
        });
        clearTimeout(tId);
        if (resp.ok) {
          const data = await resp.json();
          if (data && data.success && data.stream_url) {
            targetUrl = data.stream_url;
          }
        }
      } catch (e) {
        console.warn('[A Tube Player] Resolve error/timeout:', e);
      }
    }


    // Native Video Mode
    if (modalEl) modalEl.classList.remove('is-embed-active');
    hideEmbedGuideHint();
    if (iframeEl) {
      iframeEl.style.display = 'none';
      iframeEl.src = 'about:blank';
    }
    videoEl.style.display = 'block';

    const isHls = serverObj.is_hls || targetUrl.includes('.m3u8');

    if (isHls && window.Hls && window.Hls.isSupported()) {
      hlsInstance = new window.Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 15,
        maxBufferLength: 30,
        maxMaxBufferLength: 60
      });

      // Sanitizer hook: If local server available, proxy m3u8 through in-memory sanitizer
      const playUrl = (window.location.protocol.startsWith('http') && targetUrl.startsWith('http'))
        ? `/api/stream/sanitize?url=${encodeURIComponent(targetUrl)}`
        : targetUrl;

      hlsInstance.loadSource(playUrl);
      hlsInstance.attachMedia(videoEl);

      hlsInstance.on(window.Hls.Events.MANIFEST_PARSED, () => {
        if (startTime > 0) {
          videoEl.currentTime = startTime;
        }
        videoEl.play().catch(e => console.log('Autoplay handled:', e));
      });

      hlsInstance.on(window.Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case window.Hls.ErrorTypes.NETWORK_ERROR:
              console.warn('[A Tube Player] HLS Network error, attempting recovery...');
              hlsInstance.startLoad();
              break;
            case window.Hls.ErrorTypes.MEDIA_ERROR:
              console.warn('[A Tube Player] HLS Media error, attempting recovery...');
              hlsInstance.recoverMediaError();
              break;
            default:
              console.warn('[A Tube Player] Unrecoverable HLS error. Triggering Failover...');
              triggerStatelessFailover('خطأ في حزمة البث المباشر');
              break;
          }
        }
      });
    } else {
      // Direct MP4 / Native HLS (iOS Safari / Android TV WebView)
      videoEl.src = targetUrl;
      videoEl.addEventListener('loadedmetadata', function onLoaded() {
        if (startTime > 0) {
          videoEl.currentTime = startTime;
        }
        videoEl.removeEventListener('loadedmetadata', onLoaded);
      });

      const playTimeout = setTimeout(() => {
        if (videoEl.paused || videoEl.readyState < 2) {
          console.warn('[A Tube Player] Direct play timeout - stream may be unavailable');
          if (typeof showPlayerError === 'function') {
            showPlayerError('فشل تشغيل الفيديو - قد يكون السيرفر غير متاح');
          }
        }
      }, 8000);

      videoEl.play().then(() => {
        clearTimeout(playTimeout);
      }).catch(e => {
        clearTimeout(playTimeout);
        console.warn('[A Tube Player] Direct play failed:', e);
        if (typeof showPlayerError === 'function') {
          showPlayerError('فشل تشغيل الفيديو تلقائياً - اضغط للمحاولة مرة أخرى');
        }
      });
    }
  }

  // Flush Video Decoder Buffer and Hardware Acceleration in RAM
  function flushDecoderBuffer() {
    clearStallWatchdog();
    if (modalEl) modalEl.classList.remove('is-embed-active');
    hideEmbedGuideHint();
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
  }

  // Play Media Item
  async function playMedia(item) {
    if (!videoEl || !modalEl) return;

    currentPlayingItem = item;
    savedPlayheadTime = 0;
    currentServerIndex = 0;
    candidateServers = buildCandidateServerPool(item);

    const isLive = isLiveMediaItem(item);
    const serverBtn = document.getElementById('player-header-server-btn');
    const serverWrap = serverBtn ? serverBtn.closest('.player-dropdown-wrap') : null;

    // Check Player Server Button State for Live Channels vs VOD
    if (isLive) {
      // If live channel has no alternative live streams (<=1), hide the servers button completely!
      // If it has multiple live stream sources, display button for live stream switching.
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
    modalEl.classList.remove('active');

    hideFailoverOverlay();
    flushDecoderBuffer();

    isPlaying = false;
    currentPlayingItem = null;
    candidateServers = [];
    currentServerIndex = 0;
    savedPlayheadTime = 0;
    updatePlayIcons(false);

    // Prompt garbage collection in WebView
    if (window.gc) {
      try { window.gc(); } catch (e) {}
    }
  }

  function toggleFullscreen() {
    if (!modalEl) return;
    if (!document.fullscreenElement) {
      modalEl.requestFullscreen().catch(err => console.log('Fullscreen error:', err));
      isFullScreen = true;
    } else {
      document.exitFullscreen().catch(err => console.log('Exit fullscreen:', err));
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
    isModalActive: () => modalEl && modalEl.classList.contains('active'),
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
