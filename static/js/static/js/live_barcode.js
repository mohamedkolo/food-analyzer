/* Camera frames stay on the device. ZXing is bundled locally for Safari,
   which cannot rely on the BarcodeDetector API. */
(function () {
  'use strict';
  let decoderReady;
  function loadDecoder(url) {
    if (window.ZXingBrowser) return Promise.resolve(window.ZXingBrowser);
    if (!decoderReady) decoderReady = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = url;
      script.onload = () => resolve(window.ZXingBrowser);
      script.onerror = () => { script.remove(); decoderReady = null; reject(new Error('decoder')); };
      document.head.appendChild(script);
    });
    return decoderReady;
  }
  window.NutraXLiveBarcode = function (options) {
    const { button, panel, video, close, status, strings, onCode } = options;
    let session = 0, active = false, stream = null, timer, deadline;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    function stop(restoreFocus) {
      active = false;
      session += 1;
      clearTimeout(timer);
      clearTimeout(deadline);
      if (stream) stream.getTracks().forEach(track => track.stop());
      stream = null;
      video.pause();
      video.srcObject = null;
      panel.hidden = true;
      button.disabled = false;
      button.setAttribute('aria-expanded', 'false');
      if (restoreFocus) button.focus();
    }
    function fail(message) {
      stop(true);
      status.textContent = message;
      status.className = 'wy-status err';
    }
    async function start() {
      if (active) return;
      if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.textContent = strings.unsupported;
        status.className = 'wy-status err';
        return;
      }
      active = true;
      const id = ++session;
      button.disabled = true;
      button.setAttribute('aria-expanded', 'true');
      panel.hidden = false;
      close.focus();
      status.className = 'wy-status';
      status.textContent = strings.starting;
      deadline = setTimeout(() => { if (id === session) fail(strings.timeout); }, 30000);
      try {
        const library = await loadDecoder(options.decoderUrl);
        if (id !== session) return;
        const camera = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } }
        });
        // A permission prompt can finish after the user closes the scanner.
        if (id !== session) { camera.getTracks().forEach(track => track.stop()); return; }
        stream = camera;
        stream.getVideoTracks().forEach(track => track.addEventListener('ended', () => {
          if (id === session) fail(strings.cameraError);
        }));
        video.srcObject = stream;
        video.muted = true;
        await video.play();
        if (id !== session) return;
        status.textContent = strings.aim;
        const reader = new library.BrowserMultiFormatOneDReader();
        function scan() {
          if (id !== session) return;
          if (video.readyState >= 2 && video.videoWidth && video.videoHeight) {
            const scale = Math.min(1, 1280 / video.videoWidth);
            canvas.width = Math.round(video.videoWidth * scale);
            canvas.height = Math.round(video.videoHeight * scale);
            try {
              ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
              const code = reader.decodeFromCanvas(canvas).getText();
              if (/^(?:\d{8}|\d{12,14})$/.test(code)) {
                stop(true);
                status.textContent = strings.found;
                onCode(code);
                return;
              }
            } catch (error) { /* No barcode in this frame is normal. */ }
          }
          timer = setTimeout(scan, 150);
        }
        scan();
      } catch (error) {
        if (id !== session) return;
        fail(error.name === 'NotAllowedError' || error.name === 'SecurityError'
          ? strings.denied : strings.cameraError);
      }
    }
    button.addEventListener('click', start);
    close.addEventListener('click', () => { stop(true); status.textContent = strings.stopped; });
    panel.addEventListener('keydown', event => {
      if (event.key === 'Escape') { stop(true); status.textContent = strings.stopped; }
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && active) { stop(false); status.textContent = strings.stopped; }
    });
    window.addEventListener('pagehide', () => stop(false));
  };
})();
