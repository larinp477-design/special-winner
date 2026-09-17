/* Gadget-Koffer — Gruppe "Ohr"
 * Lärm-Messer, Stimmgerät, Spektrum-Wasserfall.
 * Klassisches Skript, kein Modul. Baut nach CONTRACT.md.
 */
(function () {
  "use strict";

  var NOTES = ["C", "Cis", "D", "Dis", "E", "F", "Fis", "G", "Gis", "A", "Ais", "H"];

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function lerp(a, b, k) { return a + (b - a) * k; }

  /* Frequenz -> { name, oktave, cent, midi } bezogen auf den Kammerton a4 */
  function analyse(freq, a4) {
    var midi = 69 + 12 * Math.log(freq / a4) / Math.log(2);
    var near = Math.round(midi);
    var cent = (midi - near) * 100;
    return {
      name: NOTES[((near % 12) + 12) % 12],
      oktave: Math.floor(near / 12) - 1,
      cent: cent,
      midi: near
    };
  }
  function midiToFreq(m, a4) { return a4 * Math.pow(2, (m - 69) / 12); }

  function micFehler(ctx, e) {
    var n = e && e.name ? e.name : "";
    if (n === "NotAllowedError" || n === "PermissionDeniedError") {
      ctx.status("Kein Zugriff aufs Mikrofon. Im Browser für diese Seite die Mikrofon-Erlaubnis geben und neu laden.", "error");
    } else if (n === "NotFoundError" || n === "DevicesNotFoundError") {
      ctx.status("Kein Mikrofon gefunden.", "error");
    } else if (n === "NotReadableError") {
      ctx.status("Das Mikrofon ist belegt — eine andere App greift gerade darauf zu.", "error");
    } else if (!window.isSecureContext) {
      ctx.status("Über eine unsichere Verbindung gibt der Browser das Mikrofon nicht frei.", "error");
    } else {
      ctx.status("Das Mikrofon lässt sich nicht öffnen.", "error");
    }
  }

  function styleOnce(root, css) {
    var s = document.createElement("style");
    s.textContent = css;
    root.appendChild(s);
  }

  /* ================================================================== */
  /* 1 — Lärm-Messer                                                     */
  /* ================================================================== */

  function mountSpl(root, ctx) {
    styleOnce(root, "#gad-spl .sp-stats{display:flex;gap:22px;flex-wrap:wrap}" +
      "#gad-spl .sp-s{display:flex;flex-direction:column;gap:1px}");

    var cv = ctx.canvas(1.7);
    var read = ctx.readout("dB");
    read.set("–", "wartet aufs Mikrofon");

    var cal = ctx.store("cal", 0);
    var db = 30, shown = 30, peak = 30, minV = 200, maxV = 0;
    var leqBuf = [], leqMax = 100;          // ~10 s bei 10 Werten/s
    var ana = null, buf = null;

    var stats = ctx.el("div", "sp-stats");
    function statBox(label) {
      var b = ctx.el("div", "sp-s");
      b.appendChild(ctx.el("div", "g-label", label));
      var n = ctx.el("div", "g-big", "–");
      b.appendChild(n); stats.appendChild(b);
      return n;
    }
    var nLeq = statBox("Mittel 10 s");
    var nMin = statBox("Leiseste");
    var nMax = statBox("Lauteste");

    var sl = ctx.slider({ min: -30, max: 30, step: 1, value: cal, unit: "dB" });
    sl.onInput(function (v) { cal = v; ctx.save("cal", v); });

    var btnReset = ctx.button("Zurücksetzen", function () {
      peak = db; minV = 200; maxV = 0; leqBuf.length = 0;
    }, "quiet");

    root.appendChild(read.node);
    root.appendChild(cv.node);
    var card = ctx.el("div", "g-card");
    card.appendChild(stats);
    card.appendChild(ctx.field("Abgleich", sl.node));
    card.appendChild(ctx.row(btnReset));
    card.appendChild(ctx.el("div", "g-note",
      "Ein Browser-Mikrofon ist nicht kalibriert — echte dB(A) sind damit nicht messbar. Die Anzeige ist eine Näherung mit festem Bezugspunkt. Wenn du ein richtiges Messgerät danebenlegst, kannst du mit dem Abgleich nachziehen; dann stimmen wenigstens die Unterschiede."));
    root.appendChild(card);

    ctx.mic().then(function (m) {
      ana = m.analyser;
      ana.fftSize = 2048;
      ana.smoothingTimeConstant = 0;
      buf = new Float32Array(ana.fftSize);
      ctx.status("Läuft. Gemessen wird relativ, nicht kalibriert.", "ok");
    }, function (e) { micFehler(ctx, e); });

    function words(v) {
      if (v < 30) return "sehr leise — wie nachts im Schlafzimmer";
      if (v < 45) return "leise — wie ein ruhiges Zimmer";
      if (v < 60) return "normal — wie ein Gespräch";
      if (v < 75) return "laut — wie Straßenverkehr";
      if (v < 90) return "sehr laut — wie ein Staubsauger direkt daneben";
      return "Gehörschutz — so klingt ein Presslufthammer";
    }

    var lastNum = 0;
    ctx.raf(function (dt, t) {
      if (ana && buf) {
        ana.getFloatTimeDomainData(buf);
        var sum = 0;
        for (var i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
        var rms = Math.sqrt(sum / buf.length);
        var raw = 20 * Math.log(Math.max(rms, 1e-8)) / Math.LN10 + 94 + cal;
        db = clamp(raw, 0, 130);
        if (db > peak) peak = db; else peak = Math.max(db, peak - dt * 0.006);
      }
      shown = lerp(shown, db, clamp(dt / 160, 0.03, 0.4));
      draw();

      if (t - lastNum > 100) {
        lastNum = t;
        if (!ana) return;
        leqBuf.push(db);
        if (leqBuf.length > leqMax) leqBuf.shift();
        if (db < minV) minV = db;
        if (db > maxV) maxV = db;
        read.set(ctx.fmt(shown, 1), words(shown));
        var s = 0;
        for (var k = 0; k < leqBuf.length; k++) s += leqBuf[k];
        nLeq.textContent = leqBuf.length ? ctx.fmt(s / leqBuf.length, 1) : "–";
        nMin.textContent = minV < 200 ? ctx.fmt(minV, 1) : "–";
        nMax.textContent = maxV > 0 ? ctx.fmt(maxV, 1) : "–";
      }
    });

    function draw() {
      var g = cv.g, w = cv.w, h = cv.h;
      g.clearRect(0, 0, w, h);
      var cx = w / 2, cy = h * 0.93, R = Math.min(w * 0.46, h * 0.84);
      var A0 = Math.PI * 1.06, A1 = Math.PI * 1.94;   // Zifferblattbogen
      var LO = 20, HI = 120;
      var cLine = ctx.color("line"), cDim = ctx.color("inkDim"), cInk = ctx.color("ink");
      var cAcc = ctx.color("accent"), cWarn = ctx.color("warn"), cGo = ctx.color("go");

      function ang(v) { return A0 + (clamp(v, LO, HI) - LO) / (HI - LO) * (A1 - A0); }

      // Bogen, farblich nach Lautstärke abgestuft
      g.lineWidth = 7; g.lineCap = "butt";
      var segs = [[LO, 60, cGo], [60, 85, cWarn], [85, HI, cAcc]];
      for (var s = 0; s < segs.length; s++) {
        g.strokeStyle = segs[s][2];
        g.globalAlpha = 0.28;
        g.beginPath(); g.arc(cx, cy, R - 4, ang(segs[s][0]), ang(segs[s][1])); g.stroke();
      }
      g.globalAlpha = 1;

      // Striche und Zahlen
      g.font = "400 9.5px ui-monospace, monospace";
      g.textAlign = "center"; g.textBaseline = "middle";
      for (var v = LO; v <= HI; v += 5) {
        var maj = (v % 20 === 0);
        var a = ang(v), r1 = R - (maj ? 20 : 14), r2 = R - 9;
        g.strokeStyle = maj ? cDim : cLine;
        g.lineWidth = maj ? 1.4 : 1;
        g.beginPath();
        g.moveTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
        g.lineTo(cx + Math.cos(a) * r2, cy + Math.sin(a) * r2);
        g.stroke();
        if (maj) {
          g.fillStyle = cDim;
          g.fillText(String(v), cx + Math.cos(a) * (R - 31), cy + Math.sin(a) * (R - 31));
        }
      }

      // Schleppzeiger
      var ap = ang(peak);
      g.strokeStyle = cWarn; g.lineWidth = 2;
      g.beginPath();
      g.moveTo(cx + Math.cos(ap) * (R - 22), cy + Math.sin(ap) * (R - 22));
      g.lineTo(cx + Math.cos(ap) * (R - 6), cy + Math.sin(ap) * (R - 6));
      g.stroke();

      // Zeiger
      var az = ang(shown);
      g.strokeStyle = cInk; g.lineWidth = 2.4; g.lineCap = "round";
      g.beginPath();
      g.moveTo(cx - Math.cos(az) * 10, cy - Math.sin(az) * 10);
      g.lineTo(cx + Math.cos(az) * (R - 14), cy + Math.sin(az) * (R - 14));
      g.stroke();
      g.fillStyle = cInk;
      g.beginPath(); g.arc(cx, cy, 5, 0, Math.PI * 2); g.fill();
    }
  }

  /* ================================================================== */
  /* 2 — Stimmgerät                                                      */
  /* ================================================================== */

  var SAITEN = [[40, "E"], [45, "A"], [50, "D"], [55, "G"], [59, "H"], [64, "E"]]; // MIDI

  function mountTuner(root, ctx) {
    styleOnce(root, "#gad-tuner .tu-head{display:flex;align-items:baseline;gap:11px;flex-wrap:wrap}" +
      "#gad-tuner .tu-note{font-family:var(--f-disp);font-weight:700;font-size:58px;line-height:1;letter-spacing:.01em}" +
      "#gad-tuner .tu-oct{font-family:var(--f-data);font-size:19px;color:var(--ink-dim)}" +
      "#gad-tuner .tu-hz{font-family:var(--f-data);font-size:15px;color:var(--ink-2);font-variant-numeric:tabular-nums}" +
      "#gad-tuner .tu-saiten{display:flex;gap:6px;flex-wrap:wrap}" +
      "#gad-tuner .tu-saite{flex:1;min-width:44px;text-align:center;border:1px solid var(--line);border-radius:2px;padding:7px 4px;font-family:var(--f-data);font-size:13px;color:var(--ink-dim)}" +
      "#gad-tuner .tu-saite.on{border-color:var(--accent);color:var(--accent)}");

    var a4 = ctx.store("a4", 440);
    var showSaiten = ctx.store("saiten", false);

    var head = ctx.el("div", "tu-head");
    var noteEl = ctx.el("div", "tu-note", "–");
    var octEl = ctx.el("div", "tu-oct", "");
    var hzEl = ctx.el("div", "tu-hz", "");
    head.appendChild(noteEl); head.appendChild(octEl); head.appendChild(hzEl);

    var cv = ctx.canvas(3.4);

    var saitenRow = ctx.el("div", "tu-saiten");
    var saitenEls = [];
    for (var i = 0; i < SAITEN.length; i++) {
      var d = analyse(midiToFreq(SAITEN[i][0], a4), a4);
      var s = ctx.el("div", "tu-saite", SAITEN[i][1] + (Math.floor(SAITEN[i][0] / 12) - 1));
      saitenRow.appendChild(s); saitenEls.push(s);
    }
    saitenRow.style.display = showSaiten ? "" : "none";

    var btnSaiten = ctx.button("Gitarre", function () {
      showSaiten = !showSaiten;
      ctx.save("saiten", showSaiten);
      saitenRow.style.display = showSaiten ? "" : "none";
      btnSaiten.setAttribute("aria-pressed", showSaiten ? "true" : "false");
    });
    btnSaiten.setAttribute("aria-pressed", showSaiten ? "true" : "false");

    var sl = ctx.slider({ min: 415, max: 466, step: 1, value: a4, unit: "Hz" });
    sl.onInput(function (v) { a4 = v; ctx.save("a4", v); });

    root.appendChild(head);
    root.appendChild(cv.node);
    var card = ctx.el("div", "g-card");
    card.appendChild(saitenRow);
    card.appendChild(ctx.row(btnSaiten));
    card.appendChild(ctx.field("Kammerton a¹", sl.node));
    card.appendChild(ctx.el("div", "g-note",
      "Deutsche Notennamen: H statt B. Innerhalb von fünf Cent steht die Anzeige auf Grün. Tiefe Saiten brauchen einen Moment, bis der Wert steht — nicht zu früh nachstimmen."));
    root.appendChild(card);

    var ana = null, buf = null, sr = 44100;
    var freq = 0, cent = 0, centSm = 0, hold = 0;

    ctx.mic().then(function (m) {
      ana = m.analyser;
      ana.fftSize = 2048;
      ana.smoothingTimeConstant = 0;
      buf = new Float32Array(ana.fftSize);
      sr = m.actx.sampleRate || 44100;
      ctx.status("Läuft. Spiel einen einzelnen Ton.", "ok");
    }, function (e) { micFehler(ctx, e); });

    /* Autokorrelation — robuster als FFT-Spitzensuche, gerade bei tiefen Tönen. */
    function pitch() {
      if (!ana || !buf) return -1;
      ana.getFloatTimeDomainData(buf);
      var N = 1024;
      var rms = 0, i;
      for (i = 0; i < N; i++) rms += buf[i] * buf[i];
      rms = Math.sqrt(rms / N);
      if (rms < 0.008) return -1;                       // zu leise, gar nicht erst raten

      var loLag = Math.floor(sr / 1400), hiLag = Math.min(Math.floor(sr / 55), N - 2);
      var best = -1, bestVal = 0, c0 = 0;
      for (i = 0; i < N; i++) c0 += buf[i] * buf[i];
      for (var lag = loLag; lag <= hiLag; lag++) {
        var s = 0;
        for (i = 0; i < N - lag; i++) s += buf[i] * buf[i + lag];
        s = s / (N - lag) * N;
        if (s > bestVal) { bestVal = s; best = lag; }
      }
      if (best < 0 || c0 <= 0) return -1;
      if (bestVal / c0 < 0.45) return -1;               // zu unklar

      // parabolische Verfeinerung um das Maximum
      var y1 = corr(best - 1), y2 = bestVal, y3 = corr(best + 1);
      var a = (y1 + y3 - 2 * y2) / 2, b = (y3 - y1) / 2;
      var shift = a ? -b / (2 * a) : 0;
      return sr / (best + clamp(shift, -1, 1));

      function corr(lag) {
        if (lag < 1 || lag >= N - 1) return 0;
        var s2 = 0;
        for (var j = 0; j < N - lag; j++) s2 += buf[j] * buf[j + lag];
        return s2 / (N - lag) * N;
      }
    }

    ctx.every(85, function () {
      var f = pitch();
      if (f > 0 && isFinite(f)) {
        freq = f; hold = 14;
        var info = analyse(f, a4);
        cent = info.cent;
        noteEl.textContent = info.name;
        octEl.textContent = String(info.oktave);
        hzEl.textContent = ctx.fmt(f, 1) + " Hz";
        if (showSaiten) {
          var bestI = 0, bestD = 1e9;
          for (var i = 0; i < SAITEN.length; i++) {
            var d = Math.abs(info.midi - SAITEN[i][0]);
            if (d < bestD) { bestD = d; bestI = i; }
          }
          for (var j = 0; j < saitenEls.length; j++) {
            if (j === bestI && bestD <= 2) saitenEls[j].className = "tu-saite on";
            else saitenEls[j].className = "tu-saite";
          }
        }
      } else if (hold > 0) {
        hold--;
      } else {
        noteEl.textContent = "–"; octEl.textContent = ""; hzEl.textContent = "";
        cent = 0;
        for (var k = 0; k < saitenEls.length; k++) saitenEls[k].className = "tu-saite";
      }
    });

    ctx.raf(function (dt) {
      centSm = lerp(centSm, hold > 0 ? cent : 0, clamp(dt / 130, 0.04, 0.4));
      draw();
    });

    function draw() {
      var g = cv.g, w = cv.w, h = cv.h;
      g.clearRect(0, 0, w, h);
      var cLine = ctx.color("line"), cDim = ctx.color("inkDim");
      var cAcc = ctx.color("accent"), cGo = ctx.color("go"), cInk = ctx.color("ink");

      var pad = 10, y = h * 0.60, half = (w - pad * 2) / 2, cx = w / 2;
      var inTune = hold > 0 && Math.abs(centSm) <= 5;

      g.strokeStyle = cLine; g.lineWidth = 1;
      g.beginPath(); g.moveTo(pad, y); g.lineTo(w - pad, y); g.stroke();

      g.font = "400 9.5px ui-monospace, monospace";
      g.textAlign = "center"; g.textBaseline = "top";
      for (var c = -50; c <= 50; c += 10) {
        var x = cx + (c / 50) * half;
        var maj = (c % 50 === 0 || c === 0);
        g.strokeStyle = c === 0 ? cAcc : (maj ? cDim : cLine);
        g.lineWidth = c === 0 ? 1.6 : 1;
        var len = c === 0 ? 20 : (maj ? 13 : 8);
        g.beginPath(); g.moveTo(x, y - len); g.lineTo(x, y + len); g.stroke();
        if (maj) { g.fillStyle = cDim; g.fillText(c > 0 ? "+" + c : String(c), x, y + len + 3); }
      }

      // Toleranzfenster ±5 Cent
      g.fillStyle = cGo; g.globalAlpha = 0.16;
      g.fillRect(cx - (5 / 50) * half, y - 22, (10 / 50) * half, 44);
      g.globalAlpha = 1;

      if (hold > 0) {
        var px = cx + clamp(centSm / 50, -1.05, 1.05) * half;
        g.fillStyle = inTune ? cGo : cAcc;
        g.beginPath();
        g.moveTo(px, y - 26);
        g.lineTo(px - 7, y - 38);
        g.lineTo(px + 7, y - 38);
        g.closePath(); g.fill();
        g.strokeStyle = inTune ? cGo : cAcc; g.lineWidth = 2.5;
        g.beginPath(); g.moveTo(px, y - 24); g.lineTo(px, y + 24); g.stroke();

        g.fillStyle = inTune ? cGo : cInk;
        g.font = "500 13px ui-monospace, monospace";
        g.textBaseline = "alphabetic";
        g.fillText(inTune ? "stimmt" : (centSm > 0 ? "zu hoch" : "zu tief"), cx, 16);
      } else {
        g.fillStyle = cDim;
        g.font = "400 12px system-ui, sans-serif";
        g.textBaseline = "alphabetic";
        g.fillText("kein Ton erkannt", cx, 16);
      }
    }
  }

  /* ================================================================== */
  /* 3 — Spektrum-Wasserfall                                             */
  /* ================================================================== */

  function mountSpectrum(root, ctx) {
    styleOnce(root, "#gad-spectrum .sw-peak{font-family:var(--f-data);font-size:17px;font-variant-numeric:tabular-nums}");

    var FMIN = 50, FMAX = 16000, LOG = Math.log(FMAX / FMIN);
    var cv = ctx.canvas(1.15);
    var peakEl = ctx.el("div", "sw-peak", "–");
    var frozen = false;

    var gain = ctx.store("gain", 1);
    var sl = ctx.slider({ min: 0.5, max: 3, step: 0.1, value: gain, unit: "×" });
    sl.onInput(function (v) { gain = v; ctx.save("gain", v); });

    var btnFreeze = ctx.button("Halten", function () {
      frozen = !frozen;
      btnFreeze.setAttribute("aria-pressed", frozen ? "true" : "false");
      btnFreeze.textContent = frozen ? "Weiter" : "Halten";
    });

    root.appendChild(cv.node);
    var card = ctx.el("div", "g-card");
    var pr = ctx.el("div", "g-col");
    pr.appendChild(ctx.el("div", "g-label", "Stärkster Ton"));
    pr.appendChild(peakEl);
    card.appendChild(pr);
    card.appendChild(ctx.field("Verstärkung", sl.node));
    card.appendChild(ctx.row(btnFreeze));
    card.appendChild(ctx.el("div", "g-note",
      "Oben das Spektrum im Moment, darunter der Wasserfall: jede Zeile ist ein Augenblick, ältere wandern nach unten. Die Frequenzachse ist logarithmisch, sonst klebt alles Musikalische am linken Rand."));
    root.appendChild(card);

    var ana = null, bins = null, sr = 44100;
    var wf = document.createElement("canvas"), wfg = wf.getContext("2d");
    var wfW = 0, wfH = 0;

    ctx.mic().then(function (m) {
      ana = m.analyser;
      ana.fftSize = 4096;
      ana.smoothingTimeConstant = 0.55;
      bins = new Uint8Array(ana.frequencyBinCount);
      sr = m.actx.sampleRate || 44100;
      ctx.status("Läuft.", "ok");
    }, function (e) { micFehler(ctx, e); });

    function fToX(f, w) { return Math.log(clamp(f, FMIN, FMAX) / FMIN) / LOG * w; }
    function xToF(x, w) { return FMIN * Math.exp(x / w * LOG); }

    /* Farbskala aus den Tokens: leise -> sunk, mittel -> cool, laut -> accent */
    function heat(v) {
      var a = parseHex(ctx.color("sunk")), b = parseHex(ctx.color("cool")), c = parseHex(ctx.color("accent"));
      var t = clamp(v, 0, 1);
      var from, to, k;
      if (t < 0.55) { from = a; to = b; k = t / 0.55; }
      else { from = b; to = c; k = (t - 0.55) / 0.45; }
      return "rgb(" + Math.round(lerp(from[0], to[0], k)) + "," +
        Math.round(lerp(from[1], to[1], k)) + "," + Math.round(lerp(from[2], to[2], k)) + ")";
    }
    function parseHex(s) {
      s = (s || "").trim();
      var m = s.match(/^#?([0-9a-f]{6})$/i);
      if (m) {
        var n = parseInt(m[1], 16);
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
      }
      var m2 = s.match(/rgba?\(([^)]+)\)/);
      if (m2) {
        var p = m2[1].split(",");
        return [parseInt(p[0], 10) || 0, parseInt(p[1], 10) || 0, parseInt(p[2], 10) || 0];
      }
      return [128, 128, 128];
    }

    var lastNum = 0;
    ctx.raf(function (dt, t) {
      var w = cv.w, h = cv.h;
      if (w !== wfW || Math.round(h * 0.55) !== wfH) {
        wfW = w; wfH = Math.max(40, Math.round(h * 0.55));
        wf.width = wfW; wf.height = wfH;
        wfg.fillStyle = ctx.color("sunk");
        wfg.fillRect(0, 0, wfW, wfH);
      }
      if (ana && bins && !frozen) {
        ana.getByteFrequencyData(bins);
        // Wasserfall eine Zeile nach unten schieben, oben die neue Zeile zeichnen
        wfg.drawImage(wf, 0, 1);
        var binHz = sr / 2 / bins.length;
        for (var x = 0; x < wfW; x++) {
          var f0 = xToF(x, wfW), f1 = xToF(x + 1, wfW);
          var i0 = Math.max(0, Math.floor(f0 / binHz)), i1 = Math.min(bins.length - 1, Math.ceil(f1 / binHz));
          var mx = 0;
          for (var i = i0; i <= i1; i++) if (bins[i] > mx) mx = bins[i];
          wfg.fillStyle = heat(mx / 255 * gain);
          wfg.fillRect(x, 0, 1, 1);
        }
      }
      draw();
      if (t - lastNum > 140 && ana && bins && !frozen) {
        lastNum = t;
        var bh = sr / 2 / bins.length, best = 0, bi = 0;
        var lo = Math.floor(FMIN / bh), hi = Math.min(bins.length - 1, Math.floor(FMAX / bh));
        for (var j = lo; j <= hi; j++) if (bins[j] > best) { best = bins[j]; bi = j; }
        if (best > 40) {
          var f = bi * bh;
          var info = analyse(f, 440);
          peakEl.textContent = Math.round(f) + " Hz — nahe " + info.name + info.oktave;
        } else {
          peakEl.textContent = "zu leise";
        }
      }
    });

    function draw() {
      var g = cv.g, w = cv.w, h = cv.h;
      var specH = h - wfH;
      g.clearRect(0, 0, w, h);
      var cLine = ctx.color("line"), cSoft = ctx.color("lineSoft"), cDim = ctx.color("inkDim");
      var cAcc = ctx.color("accent");

      // Momentspektrum
      if (ana && bins) {
        var binHz = sr / 2 / bins.length;
        g.strokeStyle = cAcc; g.lineWidth = 1.5;
        g.beginPath();
        for (var x = 0; x < w; x++) {
          var f0 = xToF(x, w), f1 = xToF(x + 1, w);
          var i0 = Math.max(0, Math.floor(f0 / binHz)), i1 = Math.min(bins.length - 1, Math.ceil(f1 / binHz));
          var mx = 0;
          for (var i = i0; i <= i1; i++) if (bins[i] > mx) mx = bins[i];
          var y = specH - 14 - clamp(mx / 255 * gain, 0, 1) * (specH - 20);
          if (x === 0) g.moveTo(x, y); else g.lineTo(x, y);
        }
        g.stroke();
      }

      // Frequenzlinien mit Beschriftung
      g.font = "400 9px ui-monospace, monospace";
      g.textBaseline = "alphabetic";
      var marks = [[100, "100"], [1000, "1k"], [10000, "10k"]];
      for (var m = 0; m < marks.length; m++) {
        var mx2 = fToX(marks[m][0], w);
        g.strokeStyle = cSoft; g.lineWidth = 1;
        g.beginPath(); g.moveTo(mx2, 0); g.lineTo(mx2, h); g.stroke();
        g.fillStyle = cDim;
        g.textAlign = mx2 < 20 ? "left" : (mx2 > w - 20 ? "right" : "center");
        g.fillText(marks[m][1], mx2, specH - 3);
      }

      // Wasserfall unten anblitten
      g.drawImage(wf, 0, specH, w, wfH);
      g.strokeStyle = cLine; g.lineWidth = 1;
      g.beginPath(); g.moveTo(0, specH); g.lineTo(w, specH); g.stroke();
    }
  }

  /* ================================================================== */

  Gadgets.register({
    id: "spl", name: "Lärm-Messer", group: "Ohr", needs: "mic",
    blurb: "Zeigerinstrument mit Schleppzeiger, Mittelwert und Abgleich.",
    mount: mountSpl
  });

  Gadgets.register({
    id: "tuner", name: "Stimmgerät", group: "Ohr", needs: "mic",
    blurb: "Chromatisch, mit Cent-Skala und Gitarrensaiten.",
    mount: mountTuner
  });

  Gadgets.register({
    id: "spectrum", name: "Spektrum", group: "Ohr", needs: "mic",
    blurb: "Logarithmischer Wasserfall mit dem stärksten Ton als Zahl.",
    mount: mountSpectrum
  });
})();
