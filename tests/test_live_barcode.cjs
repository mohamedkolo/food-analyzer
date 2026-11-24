const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

test('supplement barcode is a live scan button, not a file capture', () => {
  const html = fs.readFileSync(path.join(root, 'templates/whey.html'), 'utf8');
  assert.match(html, /<button[^>]*id="wyCodeScan"/);
  assert.doesNotMatch(html, /id="wyCode"/);
  assert.match(html, /id="wyScannerVideo"[^>]*playsinline/);
  assert.match(html, /live_barcode\.js/);
  assert.doesNotMatch(html, /fetch\('\/barcode\/read'/);
});

test('scanner decodes locally and never uploads camera frames', () => {
  const js = fs.readFileSync(path.join(root, 'static/js/live_barcode.js'), 'utf8');
  assert.match(js, /getUserMedia/);
  assert.match(js, /decodeFromCanvas/);
  assert.match(js, /facingMode: \{ ideal: 'environment' \}/);
  assert.match(js, /visibilitychange/);
  assert.match(js, /pagehide/);
  assert.doesNotMatch(js, /fetch\(|FormData|toBlob|toDataURL/);
});

const vm = require('node:vm');
function fixture() {
  const handlers = {}, docHandlers = {}, winHandlers = {};
  const element = () => ({ hidden: true, disabled: false, textContent: '', className: '',
    addEventListener(name, cb) { this[name] = cb; }, setAttribute() {}, focus() {}, pause() {},
    async play() {}, readyState: 2, videoWidth: 640, videoHeight: 480 });
  const button = element(), panel = element(), video = element(), close = element(), status = element();
  let stopped = 0, media = async () => camera, result = '6221024240195', calls = [], timeouts = [];
  const track = { stop() { stopped++; }, addEventListener() {} };
  const camera = { getTracks: () => [track], getVideoTracks: () => [track] };
  const document = { hidden: false, createElement: () => ({getContext: () => ({ drawImage() {} })}),
    addEventListener: (name, cb) => { docHandlers[name] = cb; } };
  const window = { isSecureContext: true, addEventListener: (name, cb) => { winHandlers[name] = cb; },
    ZXingBrowser: { BrowserMultiFormatOneDReader: class { decodeFromCanvas() {
      if (!result) throw new Error('no barcode'); return { getText: () => result };
    } } } };
  const context = {window, document, navigator: {mediaDevices: {getUserMedia: (...args) => media(...args)}},
    setTimeout(fn, ms) { const timer = {fn, ms, cleared:false}; timeouts.push(timer); return timer; },
    clearTimeout(timer) { if(timer)timer.cleared=true; }, console};
  vm.runInNewContext(fs.readFileSync(path.join(root,'static/js/live_barcode.js'),'utf8'), context);
  window.NutraXLiveBarcode({button,panel,video,close,status,onCode:code=>calls.push(code),decoderUrl:'local.js',
    strings:{starting:'starting',aim:'aim',found:'found',denied:'denied',unsupported:'unsupported',cameraError:'error',timeout:'timeout',stopped:'stopped'}});
  return {button,panel,video,close,status,document,docHandlers,winHandlers,window,calls,timeouts,
    setMedia(fn) {media=fn;},setResult(value){result=value;},camera,get stopped(){return stopped;}};
}
const tick = () => new Promise(resolve => setImmediate(resolve));

test('successful detection fills once and stops camera', async()=>{
  const f=fixture();await f.button.click();
  assert.deepEqual(f.calls,['6221024240195']);assert.equal(f.stopped,1);assert.equal(f.panel.hidden,true);
});
test('permission denial is recoverable', async()=>{
  const f=fixture();f.setMedia(async()=>{throw {name:'NotAllowedError'};});await f.button.click();
  assert.equal(f.status.textContent,'denied');assert.equal(f.button.disabled,false);assert.equal(f.panel.hidden,true);
});
test('closing before camera permission returns releases the late stream',async()=>{
  const f=fixture();let release;f.setMedia(()=>new Promise(resolve=>{release=resolve;}));
  const started=f.button.click();await tick();f.close.click();release(f.camera);await started;
  assert.equal(f.stopped,1);assert.equal(f.panel.hidden,true);assert.equal(f.calls.length,0);
});
test('backgrounding stops camera',async()=>{
  const f=fixture();f.setResult(null);await f.button.click();f.document.hidden=true;f.docHandlers.visibilitychange();
  assert.equal(f.stopped,1);assert.equal(f.panel.hidden,true);
});
test('navigation stops camera',async()=>{
  const f=fixture();f.setResult(null);await f.button.click();f.winHandlers.pagehide();assert.equal(f.stopped,1);
});
test('no result timeout stops camera but permits another scan',async()=>{
  const f=fixture();f.setResult(null);await f.button.click();f.timeouts.find(t=>t.ms===30000).fn();
  assert.equal(f.stopped,1);assert.equal(f.button.disabled,false);assert.equal(f.status.textContent,'timeout');
});
test('insecure context never asks for a camera',async()=>{
  const f=fixture();f.window.isSecureContext=false;f.setMedia(()=>{throw new Error('must not run');});
  await f.button.click();assert.equal(f.status.textContent,'unsupported');
});
