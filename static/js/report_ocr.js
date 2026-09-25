/* ‏قراءة ورقة تحليل الجسم -- في متصفح الدكتور نفسه، مش على السيرفر.
 *
 * ليه في المتصفح:
 *
 *   الميزة فضلت مقفولة مرتين: مرة عشان محتاجة مفتاح API مربوط بحساب
 *   وفيزة، ومرة عشان مكتبة القراءة على السيرفر بتاخد ~٢٨٠ ميجا رام
 *   والاستضافة عندها ٥١٢ والتطبيق ماشي فيهم -- فأول صورة كانت تقدر
 *   تنيّم الموقع. الدكتور قال "عايز الخاصيه تشتغل"، ودي الطريقة اللي
 *   بتشتغل من غير مفتاح ولا تركيب ولا إعداد على الاستضافة.
 *
 *   وفيها مكسب تاني أهم: صورة ورقة تحليل العميل مابتخرجش من الموبايل
 *   خالص. اللي بيوصل للسيرفر هو الكلام المقروء، مش الصورة.
 *
 * الملف ده بيعمل حاجة واحدة: صورة -> سطور كلام. تفسير السطور (إيه الوزن
 * وإيه الطول، وإيه الرقم اللي مايتصدّقش) كله في بايثون على السيرفر
 * (ocr_report.py) وعليه اختبارات -- عشان الحواجز اللي بتمنع الرقم الغلط
 * تبقى في مكان واحد مقيس، مش متفرّقة بين جافاسكربت وبايثون.
 */
window.ReportOCR = (function () {
  'use strict';

  var BASE = '/ocr/';

  // ‏حجم الصورة اللي بتتقرا. الرقمين دول مقيسين مش مفترضين:
  //   أقل من ٢٦٠٠ للحرف الطويل -- النقطة العشرية بتضيع. "38.2%" بتتقرا
  //   "382%"، وده الغلط الأكتر تكراراً في كل الصور اللي جرّبتها.
  //   أكتر من ٣٤٠٠ -- ماكسبناش دقة وبنحجز ذاكرة أكتر على الموبايل.
  // ‏صورة موبايل ٤٠٠٠ بكسل بتصغّر لـ٣٤٠٠، وصورة صغيرة بتكبّر لـ٢٦٠٠.
  var MIN_EDGE = 2600, MAX_EDGE = 3400, MAX_SCALE = 4;

  var LIMITS = { lines: 400, words: 40, word: 40 };

  var enginePromise = null, workerPromise = null;

  function loadEngine() {
    if (enginePromise) return enginePromise;
    enginePromise = new Promise(function (resolve, reject) {
      if (window.Tesseract) { resolve(window.Tesseract); return; }
      var el = document.createElement('script');
      el.src = BASE + 'tesseract.min.js';
      el.onload = function () {
        if (window.Tesseract) resolve(window.Tesseract);
        else reject(new Error('engine-missing'));
      };
      el.onerror = function () { reject(new Error('engine-download')); };
      document.head.appendChild(el);
    });
    enginePromise.catch(function () { enginePromise = null; });
    return enginePromise;
  }

  // ‏المحرّك بيتحمّل مرة واحدة ويفضل. أول ورقة بتنزّل ~١.٥ ميجا، واللي
  // بعدها بتقرا على طول -- المكتبة بتحفظ ملف اللغة في IndexedDB بنفسها.
  function getWorker(onStep) {
    if (workerPromise) return workerPromise;
    workerPromise = loadEngine().then(function (T) {
      return T.createWorker('eng', 1, {
        workerPath: BASE + 'worker.min.js',
        corePath: BASE,
        langPath: BASE,
        // ‏الـworker بيتحمّل من نفس الموقع مباشرة، مش من blob -- عشان
        // يمشي مع سياسة الأمان (CSP) بدون ما نوسّعها.
        workerBlobURL: false,
        logger: function (m) { if (onStep) onStep(m); }
      });
    });
    workerPromise.catch(function () { workerPromise = null; });
    return workerPromise;
  }

  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () { URL.revokeObjectURL(url); resolve(img); };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error('bad-image')); };
      img.src = url;
    });
  }

  function drawScaled(img) {
    var iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
    var longest = Math.max(iw, ih);
    if (!longest) throw new Error('bad-image');
    var target = Math.min(MAX_EDGE, Math.max(MIN_EDGE, longest));
    var scale = Math.min(MAX_SCALE, target / longest);
    var w = Math.max(1, Math.round(iw * scale));
    var h = Math.max(1, Math.round(ih * scale));
    var cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    var ctx = cv.getContext('2d', { willReadFrequently: true });
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, w, h);
    ctx.drawImage(img, 0, 0, w, h);
    return cv;
  }

  /** ‏رمادي في المكان، وبيرجّع قناة واحدة للمعالجة التانية. */
  function toGray(cv) {
    var ctx = cv.getContext('2d', { willReadFrequently: true });
    var frame = ctx.getImageData(0, 0, cv.width, cv.height);
    var d = frame.data, n = cv.width * cv.height;
    var one = new Uint8ClampedArray(n);
    for (var p = 0, i = 0; p < n; p++, i += 4) {
      var g = (d[i] * 77 + d[i + 1] * 151 + d[i + 2] * 28) >> 8;
      d[i] = d[i + 1] = d[i + 2] = g; d[i + 3] = 255;
      one[p] = g;
    }
    ctx.putImageData(frame, 0, 0);
    return one;
  }

  /** ‏تنعيم مربّع بنصف قطر r، منفصل أفقي/رأسي عشان يبقى سريع. */
  function boxBlur(src, w, h, r) {
    var tmp = new Float32Array(w * h), out = new Uint8ClampedArray(w * h);
    var span = 2 * r + 1, x, y, i, sum, row;
    for (y = 0; y < h; y++) {
      row = y * w; sum = 0;
      for (i = -r; i <= r; i++) sum += src[row + Math.min(w - 1, Math.max(0, i))];
      for (x = 0; x < w; x++) {
        tmp[row + x] = sum / span;
        sum += src[row + Math.min(w - 1, x + r + 1)] - src[row + Math.max(0, x - r)];
      }
    }
    for (x = 0; x < w; x++) {
      sum = 0;
      for (i = -r; i <= r; i++) sum += tmp[Math.min(h - 1, Math.max(0, i)) * w + x];
      for (y = 0; y < h; y++) {
        out[y * w + x] = sum / span;
        sum += tmp[Math.min(h - 1, y + r + 1) * w + x] - tmp[Math.max(0, y - r) * w + x];
      }
    }
    return out;
  }

  /** ‏تحديد الحدود + شدّ التباين. ده اللي رفع القراءة في الصورة المهزوزة. */
  function sharpenCanvas(gray, w, h) {
    var blur = boxBlur(gray, w, h, 2);
    var n = w * h, out = new Uint8ClampedArray(n), p;
    for (p = 0; p < n; p++) out[p] = gray[p] + 1.8 * (gray[p] - blur[p]);
    var lo = 255, hi = 0;
    for (p = 0; p < n; p++) { if (out[p] < lo) lo = out[p]; if (out[p] > hi) hi = out[p]; }
    if (hi > lo) {
      var k = 255 / (hi - lo);
      for (p = 0; p < n; p++) out[p] = (out[p] - lo) * k;
    }
    var cv = document.createElement('canvas');
    cv.width = w; cv.height = h;
    var ctx = cv.getContext('2d', { willReadFrequently: true });
    var frame = ctx.createImageData(w, h);
    var d = frame.data;
    for (p = 0; p < n; p++) {
      var i = p * 4;
      d[i] = d[i + 1] = d[i + 2] = out[p]; d[i + 3] = 255;
    }
    ctx.putImageData(frame, 0, 0);
    return cv;
  }

  /** ‏كلام المحرّك -> سطور، كل سطر كلماته بترتيبها.
   *
   * ‏الترتيب هو المعلومة كلها: السيرفر بياخد الرقم اللي **بعد** العنوان،
   * فسطر زي "Height 165.0 cm Weight 78.4 kg" مايخليش الوزن ١٦٥.
   */
  function linesOf(data) {
    var lines = [], blocks = data.blocks || [], b, p, l, wd, words;
    for (var bi = 0; bi < blocks.length && lines.length < LIMITS.lines; bi++) {
      b = blocks[bi];
      var paras = b.paragraphs || [];
      for (var pi = 0; pi < paras.length && lines.length < LIMITS.lines; pi++) {
        p = paras[pi];
        var ls = p.lines || [];
        for (var li = 0; li < ls.length && lines.length < LIMITS.lines; li++) {
          l = ls[li];
          words = [];
          var ws = l.words || [];
          for (var wi = 0; wi < ws.length && words.length < LIMITS.words; wi++) {
            wd = ws[wi];
            var text = String(wd.text == null ? '' : wd.text).trim();
            if (!text) continue;
            words.push(text.slice(0, LIMITS.word));
          }
          if (words.length) lines.push(words);
        }
      }
    }
    return lines;
  }

  /** ‏بيرجّع [سطور القراءة الأولى, سطور القراءة التانية].
   *
   * ليه قراءتين: كل معالجة بتنجح في حاجة التانية بتفشل فيها. السيرفر
   * بياخد اللي اتفقوا عليه، واللي اختلفوا فيه بيشيله -- الدكتور يكتبه
   * بإيده، وده أحسن من رقم غلط.
   */
  async function read(file, onStep) {
    var worker = await getWorker(onStep);
    var img = await loadImage(file);
    var first = drawScaled(img);
    var w = first.width, h = first.height;
    var gray = toGray(first);
    var second = sharpenCanvas(gray, w, h);
    gray = null;

    var passes = [], sheets = [first, second];
    for (var i = 0; i < sheets.length; i++) {
      if (onStep) onStep({ status: 'recognizing text', progress: i / 2 });
      var res = await worker.recognize(sheets[i], {}, { blocks: true, text: false });
      passes.push(linesOf(res.data));
      sheets[i].width = sheets[i].height = 1;   // ‏نفضّي الذاكرة على طول
    }
    return passes;
  }

  return { read: read, warm: getWorker };
})();
