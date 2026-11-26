/* NX launch splash: shows once per tab/app launch, about 1.5 s, tap to skip. */
(function () {
  try { if (sessionStorage.getItem('nx_splash')) return; sessionStorage.setItem('nx_splash', '1'); } catch (e) {}
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var st = document.createElement('style');
  st.textContent =
    '#nxSplash{position:fixed;inset:0;z-index:2147483000;background:#040507;display:flex;align-items:center;justify-content:center;opacity:1;transition:opacity .45s ease}' +
    '#nxSplash.out{opacity:0;pointer-events:none}' +
    '#nxSplash .g{position:absolute;width:340px;height:340px;border-radius:50%;background:radial-gradient(circle,rgba(98,223,80,.38),rgba(98,223,80,0) 68%);animation:nxg 1.5s ease-out both}' +
    '#nxSplash img{position:relative;width:128px;height:128px;border-radius:28px;animation:nxl 1.1s cubic-bezier(.2,.8,.2,1) both}' +
    '@keyframes nxl{from{opacity:0;transform:scale(.72)}to{opacity:1;transform:scale(1)}}' +
    '@keyframes nxg{0%{opacity:0;transform:scale(.6)}60%{opacity:1}100%{opacity:.8;transform:scale(1.1)}}' +
    '@media (prefers-reduced-motion:reduce){#nxSplash .g,#nxSplash img{animation:none}}';
  document.head.appendChild(st);
  var o = document.createElement('div');
  o.id = 'nxSplash'; o.setAttribute('aria-hidden', 'true');
  o.innerHTML = '<div class="g"></div><img src="/static/nx-icon-v2-512.png" alt="">';
  (document.body || document.documentElement).appendChild(o);
  var done = false;
  function hide() { if (done) return; done = true; o.classList.add('out'); setTimeout(function () { o.remove(); st.remove(); }, 520); }
  o.addEventListener('click', hide);
  setTimeout(hide, reduce ? 700 : 1500);
})();
