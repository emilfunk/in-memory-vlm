/**
 * Zero-Disk Browser DOM Video Keyframe & Context Extractor
 * 
 * Executed inside an authenticated browser tab (via CDP Runtime.evaluate).
 * Reads the mounted HTML5 <video> element, seeks across intervals,
 * paints to an OffscreenCanvas in memory, and returns Base64 JPEG frames.
 */
(() => {
  return (async (numFrames = 12) => {
    // 1. Locate the primary video element on the page (prefer playing or visible)
    const videos = Array.from(document.querySelectorAll('video'));
    if (!videos.length) {
      return {
        success: false,
        error: 'No HTML5 <video> element found on the active page.'
      };
    }

    const video = videos.find(v => !v.paused && v.currentTime > 0) ||
      videos.find(v => {
        const r = v.getBoundingClientRect();
        return r.top < window.innerHeight && r.bottom > 0 && r.width > 100 && r.height > 100;
      }) ||
      videos.sort((a, b) => (b.videoWidth * b.videoHeight) - (a.videoWidth * a.videoHeight))[0];

    const originalPaused = video.paused;
    const originalTime = video.currentTime;
    video.pause();

    const duration = video.duration && !isNaN(video.duration) && isFinite(video.duration)
      ? video.duration
      : 30.0;

    const interval = duration / (numFrames + 1);

    // 2. Prepare in-memory OffscreenCanvas bounded to 720p max
    const targetWidth = Math.min(video.videoWidth || 640, 1280);
    const targetHeight = Math.min(video.videoHeight || 360, 720);

    const canvas = new OffscreenCanvas(targetWidth, targetHeight);
    const ctx = canvas.getContext('2d');
    const keyframes = [];

    // 3. Fast-seek through timeline and grab frames in RAM
    for (let i = 1; i <= numFrames; i++) {
      const targetSec = i * interval;
      video.currentTime = targetSec;

      await new Promise((resolve) => {
        let resolved = false;
        let timer = null;
        const cleanup = () => {
          video.removeEventListener('seeked', onSeeked);
          if (timer) clearTimeout(timer);
        };

        timer = setTimeout(() => {
          if (!resolved) {
            resolved = true;
            cleanup();
            resolve();
          }
        }, 1500);

        const onSeeked = () => {
          if (!resolved) {
            resolved = true;
            cleanup();
            resolve();
          }
        };
        video.addEventListener('seeked', onSeeked);
      });

      try {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const blob = await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.75 });
        const arrayBuffer = await blob.arrayBuffer();

        // Convert byte array to Base64 in RAM efficiently using chunks
        let binary = '';
        const bytes = new Uint8Array(arrayBuffer);
        const chunkSize = 8192;
        for (let b = 0; b < bytes.length; b += chunkSize) {
          binary += String.fromCharCode.apply(null, bytes.subarray(b, b + chunkSize));
        }

        keyframes.push({
          index: i,
          timestamp_sec: Math.round(targetSec * 10) / 10,
          base64_jpeg: btoa(binary)
        });
      } catch (err) {
        // Continue seeking if a single frame grab fails
      }
    }

    // Restore playback state
    video.currentTime = originalTime;
    if (!originalPaused) {
      video.play().catch(() => {});
    }

    if (keyframes.length === 0) {
      return {
        success: false,
        error: 'Failed to extract any keyframes from video (possibly cross-origin/CORS restricted).'
      };
    }

    // 4. Capture surrounding textual post context
    let postText = '';
    const textSelectors = [
      'article',
      'main',
      '.feed-shared-update-v2', // LinkedIn
      '[data-testid="tweetText"]', // X
      'h1',
      'div[role="main"]'
    ];
    for (const sel of textSelectors) {
      const el = document.querySelector(sel);
      if (el && el.innerText && el.innerText.trim().length > 10) {
        postText = el.innerText.slice(0, 2000);
        break;
      }
    }

    return {
      success: true,
      duration_sec: duration,
      frame_count: keyframes.length,
      keyframes: keyframes,
      post_text: postText || document.title
    };
  })(12);
})();
