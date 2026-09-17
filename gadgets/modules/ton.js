/* Gadget-Koffer — Gruppe "Ton"
 * Tongenerator, Hörtest, Metronom.
 * Klassisches Skript, kein Modul. Baut nach CONTRACT.md.
 */
(function () {
  "use strict";

  var NOTES = ["C", "Cis", "D", "Dis", "E", "F", "Fis", "G", "Gis", "A", "Ais", "H"];

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function lerp(a, b, k) { return a + (b - a) * k; }

  function noteOf(freq) {
    var midi = 69 + 12 * Math.log(freq / 440) / Math.log(2);
    var near = Math.round(midi);
    return {
      name: NOTES[((near % 12) + 12) % 12],
      oktave: Math.floor(near / 12) - 1,
      cent: (midi - near) * 100
    };
  }

  function styleOnce(root, css) {
    var s = document.createElement("style");
    s.textContent = css;
    root.appendChild(s);
  }
  function reducedMotion() {
    try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
    catch (e) { return false; }
  }
  function noAudio(ctx) {
    ctx.status("Dieser Browser gibt keinen Ton aus — die Web-Audio-Schnittstelle fehlt.", "error");
  }

  /* ================================================================== */
  /* 1 — Tongenerator                                                    */
  /* ================================================================== */

  var WAVES = [["sine", "Sinus"], ["triangle", "Dreieck"], ["sawtooth", "Sägezahn"], ["square", "Rechteck"]];

  function mountTone(root, ctx) {
    styleOnce(root, "#gad-tone .to-hz{font-family:var(--f-data);font-size:38px;font-variant-numeric:tabular-nums;letter-spacing:-.03em;line-height:1}" +
      "#gad-tone .to-note{font-size:13px;color:var(--ink-dim);margin-top:3px}" +
      "#gad-tone .to-waves{display:flex;gap:6px;flex-wrap:wrap}" +
      "#gad-tone .to-w{flex:1;min-width:66px}" +
      "#gad-tone .to-in{width:100%}");

    var actx = ctx.audio();
    if (!actx) { noAudio(ctx); return; }

    var freq = ctx.store("freq", 440);
    var wave = ctx.store("wave", "sine");
    var vol = ctx.store("vol", 0.25);
    var running = false, osc = null;

    var out = ctx.owned(actx.createGain());
    out.gain.value = 0;
    var ana = ctx.owned(actx.createAnalyser());
    ana.fftSize = 2048;
    out.connect(ana);
    ana.connect(actx.destination);
    var wbuf = new Float32Array(ana.fftSize);

    var hzEl = ctx.el("div", "to-hz", "440");
    var noteEl = ctx.el("div", "to-note", "");
    var headBox = ctx.el("div");
    headBox.appendChild(hzEl);
    headBox.appendChild(noteEl);

    var cv = ctx.canvas(2.4);

    /* Logarithmischer Frequenzregler: 0..1000 -> 20..20000 Hz */
    function posOf(f) { return Math.log(f / 20) / Math.log(1000) * 1000; }
    function freqOf(p) { return 20 * Math.pow(1000, p / 1000); }

    var sl = ctx.slider({ min: 0, max: 1000, step: 1, value: Math.round(posOf(freq)) });
    sl.onInput(function (p) { setFreq(freqOf(p), false); });

    var numIn = document.createElement("input");
    numIn.type = "number";
    numIn.className = "g-input to-in";
    numIn.min = "20"; numIn.max = "20000"; numIn.step = "1";
    numIn.value = String(Math.round(freq));
    numIn.setAttribute("aria-label", "Frequenz in Hertz");
    ctx.on(numIn, "change", function () {
      var v = parseFloat(numIn.value);
      if (isFinite(v)) setFreq(clamp(v, 20, 20000), true);
    });

    function step(mult) { return function () { setFreq(clamp(freq * mult, 20, 20000), true); }; }
    var btnOctD = ctx.button("−8ve", step(0.5), "quiet");
    var btnHalbD = ctx.button("−½", step(Math.pow(2, -1 / 12)), "quiet");
    var btnHalbU = ctx.button("+½", step(Math.pow(2, 1 / 12)), "quiet");
    var btnOctU = ctx.button("+8ve", step(2), "quiet");

    var waveRow = ctx.el("div", "to-waves");
    var waveBtns = [];
    WAVES.forEach(function (wv) {
      var b = ctx.button(wv[1], function () {
        wave = wv[0]; ctx.save("wave", wave);
        if (osc) osc.type = wave;
        paintWaves();
      });
      b.className += " to-w";
      waveRow.appendChild(b);
      waveBtns.push({ el: b, id: wv[0] });
    });
    function paintWaves() {
      waveBtns.forEach(function (b) { b.el.setAttribute("aria-pressed", b.id === wave ? "true" : "false"); });
    }
    paintWaves();

    var slVol = ctx.slider({ min: 0, max: 100, step: 1, value: Math.round(vol * 100), unit: "%" });
    slVol.onInput(function (v) {
      vol = v / 100; ctx.save("vol", vol);
      if (running) out.gain.setTargetAtTime(vol, actx.currentTime, 0.02);
    });

    var btnRun = ctx.button("Ton an", function () { running ? stop() : start(); }, "go");

    /* Sweep */
    var sweepTo = ctx.store("sweepTo", 2000);
    var sweepSec = ctx.store("sweepSec", 8);
    var slTo = ctx.slider({ min: 0, max: 1000, step: 1, value: Math.round(posOf(sweepTo)) });
    slTo.onInput(function (p) { sweepTo = freqOf(p); ctx.save("sweepTo", sweepTo); slTo.label(Math.round(sweepTo) + " Hz"); });
    slTo.label(Math.round(sweepTo) + " Hz");
    var slSec = ctx.slider({ min: 1, max: 60, step: 1, value: sweepSec, unit: "s" });
    slSec.onInput(function (v) { sweepSec = v; ctx.save("sweepSec", v); });

    var sweep = null;
    var btnSweep = ctx.button("Sweep starten", function () {
      if (sweep) { endSweep(); return; }
      if (!running) start();
      var t0 = actx.currentTime;
      osc.frequency.cancelScheduledValues(t0);
      osc.frequency.setValueAtTime(freq, t0);
      osc.frequency.exponentialRampToValueAtTime(Math.max(20, sweepTo), t0 + sweepSec);
      sweep = { t0: t0, from: freq, to: sweepTo, dur: sweepSec };
      btnSweep.textContent = "Sweep abbrechen";
    });
    function endSweep() {
      if (osc) {
        var t = actx.currentTime;
        osc.frequency.cancelScheduledValues(t);
        osc.frequency.setValueAtTime(osc.frequency.value, t);
        setFreq(osc.frequency.value, true);
      }
      sweep = null;
      btnSweep.textContent = "Sweep starten";
    }

    function setFreq(f, syncSlider) {
      freq = clamp(f, 20, 20000);
      ctx.save("freq", freq);
      hzEl.textContent = (freq < 100 ? ctx.fmt(freq, 1) : String(Math.round(freq)));
      var n = noteOf(freq);
      noteEl.textContent = "nahe " + n.name + n.oktave + " (" + (n.cent >= 0 ? "+" : "") + ctx.fmt(n.cent, 0) + " Cent)";
      if (syncSlider) { sl.set(Math.round(posOf(freq))); numIn.value = String(Math.round(freq)); }
      else numIn.value = String(Math.round(freq));
      if (osc && !sweep) osc.frequency.setTargetAtTime(freq, actx.currentTime, 0.01);
    }

    function start() {
      if (running) return;
      osc = actx.createOscillator();
      osc.type = wave;
      osc.frequency.value = freq;
      osc.connect(out);
      osc.start();
      out.gain.cancelScheduledValues(actx.currentTime);
      out.gain.setTargetAtTime(vol, actx.currentTime, 0.02);
      running = true;
      btnRun.textContent = "Ton aus";
      ctx.status("Vorsicht mit Kopfhörern — hohe Frequenzen wirken leiser, als sie sind.", "warn");
    }
    function stop() {
      if (!running) return;
      out.gain.cancelScheduledValues(actx.currentTime);
      out.gain.setTargetAtTime(0, actx.currentTime, 0.02);
      var o = osc; osc = null; running = false;
      setTimeout(function () { try { o.stop(); o.disconnect(); } catch (e) {} }, 120);
      btnRun.textContent = "Ton an";
      if (sweep) endSweep();
      ctx.clearStatus();
    }

    root.appendChild(headBox);
    root.appendChild(cv.node);
    var c1 = ctx.el("div", "g-card");
    c1.appendChild(ctx.field("Frequenz", sl.node));
    c1.appendChild(ctx.row(numIn));
    c1.appendChild(ctx.row(btnOctD, btnHalbD, btnHalbU, btnOctU));
    c1.appendChild(ctx.field("Wellenform", waveRow));
    c1.appendChild(ctx.field("Lautstärke", slVol.node));
    c1.appendChild(ctx.row(btnRun));
    root.appendChild(c1);

    var c2 = ctx.el("div", "g-card");
    c2.appendChild(ctx.el("div", "g-label", "Sweep"));
    c2.appendChild(ctx.el("div", "g-note", "Fährt die Frequenz logarithmisch hoch oder runter. Damit findet man Resonanzen — im Zimmer, im Gehäuse, im Lautsprecher."));
    c2.appendChild(ctx.field("Zielfrequenz", slTo.node));
    c2.appendChild(ctx.field("Dauer", slSec.node));
    c2.appendChild(ctx.row(btnSweep));
    root.appendChild(c2);

    setFreq(freq, true);

    ctx.raf(function () {
      if (sweep && osc) {
        var el2 = actx.currentTime - sweep.t0;
        if (el2 >= sweep.dur) { endSweep(); }
        else {
          var f = sweep.from * Math.pow(sweep.to / sweep.from, el2 / sweep.dur);
          hzEl.textContent = String(Math.round(f));
          var n2 = noteOf(f);
          noteEl.textContent = "Sweep — " + Math.round(el2) + " von " + sweep.dur + " s, nahe " + n2.name + n2.oktave;
        }
      }
      draw();
    });

    function draw() {
      var g = cv.g, w = cv.w, h = cv.h;
      g.clearRect(0, 0, w, h);
      var cSoft = ctx.color("lineSoft"), cDim = ctx.color("inkDim"), cAcc = ctx.color("accent");
      var mid = h / 2;

      g.strokeStyle = cSoft; g.lineWidth = 1;
      g.beginPath(); g.moveTo(0, mid); g.lineTo(w, mid); g.stroke();

      if (!running) {
        g.fillStyle = cDim;
        g.font = "400 12px system-ui, sans-serif";
        g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText("Ton ist aus", w / 2, mid);
        return;
      }

      ana.getFloatTimeDomainData(wbuf);
      var sr = actx.sampleRate || 44100;
      var fNow = sweep && osc ? osc.frequency.value : freq;
      var want = Math.round(3 * sr / Math.max(fNow, 20));
      var n = clamp(want, 32, wbuf.length);

      g.strokeStyle = cAcc; g.lineWidth = 1.6;
      g.beginPath();
      for (var i = 0; i < n; i++) {
        var x = i / (n - 1) * w;
        var y = mid - clamp(wbuf[i], -1, 1) * (h * 0.42);
        if (i === 0) g.moveTo(x, y); else g.lineTo(x, y);
      }
      g.stroke();

      g.fillStyle = cDim;
      g.font = "400 9px ui-monospace, monospace";
      g.textAlign = "right"; g.textBaseline = "bottom";
      g.fillText(ctx.fmt(n / sr * 1000, 1) + " ms", w - 3, h - 3);
    }

    return {
      unmount: function () { try { stop(); } catch (e) {} }
    };
  }

  /* ================================================================== */
  /* 2 — Hörtest                                                         */
  /* ================================================================== */

  var STUFEN = [8000, 10000, 12000, 14000, 15000, 16000, 17000, 18000, 19000, 20000];

  function altersHinweis(f) {
    if (f >= 19000) return "Das schaffen sonst fast nur Kinder und Jugendliche.";
    if (f >= 17000) return "Typisch für etwa bis Mitte zwanzig.";
    if (f >= 15000) return "Typisch für etwa dreißig bis vierzig.";
    if (f >= 12000) return "Typisch für etwa fünfzig.";
    if (f >= 10000) return "Typisch für etwa sechzig und älter.";
    return "Unter 10 kHz — hier liegt es sehr oft am Lautsprecher, nicht am Ohr.";
  }

  function mountHearing(root, ctx) {
    styleOnce(root, "#gad-hearing .he-freq{font-family:var(--f-data);font-size:44px;font-variant-numeric:tabular-nums;letter-spacing:-.03em;line-height:1}" +
      "#gad-hearing .he-hist{display:flex;flex-direction:column;gap:3px}" +
      "#gad-hearing .he-h{display:flex;justify-content:space-between;font-family:var(--f-data);font-size:12px;color:var(--ink-dim)}");

    var actx = ctx.audio();
    if (!actx) { noAudio(ctx); return; }

    var out = ctx.owned(actx.createGain());
    out.gain.value = 0;
    out.connect(actx.destination);
    var osc = null;

    var idx = -1;                 // -1 = noch nicht gestartet
    var results = [];             // true = gehört
    var grenze = null;
    var hist = ctx.store("hist", []) || [];

    var freqEl = ctx.el("div", "he-freq", "–");
    var subEl = ctx.el("div", "g-note", "Kopfhörer aufsetzen, mittlere Lautstärke, ruhig sitzen. Dann starten.");
    var cv = ctx.canvas(2.2);

    var btnStart = ctx.button("Test starten", function () { begin(); }, "go");
    var btnJa = ctx.button("Gehört", function () { answer(true); }, "go");
    var btnNein = ctx.button("Nichts", function () { answer(false); });
    var btnStop = ctx.button("Abbrechen", function () { finishAbort(); }, "quiet");
    var runRow = ctx.row(btnJa, btnNein, btnStop);
    runRow.style.display = "none";

    var histBox = ctx.el("div", "he-hist");
    function paintHist() {
      histBox.textContent = "";
      if (!hist.length) { histBox.appendChild(ctx.el("div", "g-note", "Noch kein Durchlauf gespeichert.")); return; }
      hist.slice(0, 6).forEach(function (h) {
        var r = ctx.el("div", "he-h");
        r.appendChild(ctx.el("span", null, h.datum));
        r.appendChild(ctx.el("span", null, (h.hz / 1000).toFixed(0) + " kHz"));
        histBox.appendChild(r);
      });
    }
    paintHist();

    root.appendChild(freqEl);
    root.appendChild(subEl);
    root.appendChild(cv.node);
    var c1 = ctx.el("div", "g-card");
    c1.appendChild(ctx.row(btnStart));
    c1.appendChild(runRow);
    c1.appendChild(ctx.el("div", "g-note",
      "Das ist ein Spaß-Test, keine Untersuchung. Tagesform, Kopfhörer und Umgebung verschieben das Ergebnis stark — und der eingebaute Lautsprecher eines Telefons gibt oberhalb von etwa 15 kHz oft gar nichts mehr her. Wenn du echte Sorgen hast: zum Arzt, nicht zu dieser Seite."));
    root.appendChild(c1);

    var c2 = ctx.el("div", "g-card");
    c2.appendChild(ctx.el("div", "g-label", "Frühere Durchläufe"));
    c2.appendChild(histBox);
    root.appendChild(c2);

    function play(f) {
      silence();
      osc = actx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = f;
      osc.connect(out);
      osc.start();
      out.gain.cancelScheduledValues(actx.currentTime);
      out.gain.setTargetAtTime(0.16, actx.currentTime, 0.03);
    }
    function silence() {
      if (!osc) return;
      out.gain.cancelScheduledValues(actx.currentTime);
      out.gain.setTargetAtTime(0, actx.currentTime, 0.02);
      var o = osc; osc = null;
      setTimeout(function () { try { o.stop(); o.disconnect(); } catch (e) {} }, 120);
    }

    function begin() {
      idx = 0; results = []; grenze = null;
      btnStart.style.display = "none";
      runRow.style.display = "";
      stufe();
    }
    function stufe() {
      var f = STUFEN[idx];
      freqEl.textContent = (f / 1000).toFixed(0) + " kHz";
      subEl.textContent = "Stufe " + (idx + 1) + " von " + STUFEN.length + " — hörst du einen Ton?";
      play(f);
      draw();
    }
    function answer(gehoert) {
      results[idx] = gehoert;
      if (!gehoert) { finish(idx > 0 ? STUFEN[idx - 1] : null); return; }
      idx++;
      if (idx >= STUFEN.length) { finish(STUFEN[STUFEN.length - 1]); return; }
      stufe();
    }
    function finishAbort() {
      silence();
      idx = -1; results = [];
      btnStart.style.display = ""; runRow.style.display = "none";
      freqEl.textContent = "–";
      subEl.textContent = "Abgebrochen. Jederzeit neu starten.";
      draw();
    }
    function finish(f) {
      silence();
      grenze = f;
      btnStart.style.display = ""; btnStart.textContent = "Nochmal";
      runRow.style.display = "none";
      if (f == null) {
        freqEl.textContent = "–";
        subEl.textContent = "Schon die erste Stufe bei 8 kHz war nicht zu hören. Das liegt fast sicher an der Wiedergabe: lauter stellen und mit Kopfhörern nochmal.";
      } else {
        freqEl.textContent = (f / 1000).toFixed(0) + " kHz";
        subEl.textContent = "Deine obere Grenze in diesem Durchlauf. " + altersHinweis(f);
        var d = new Date();
        hist.unshift({
          datum: ("0" + d.getDate()).slice(-2) + "." + ("0" + (d.getMonth() + 1)).slice(-2) + "." + d.getFullYear(),
          hz: f
        });
        hist = hist.slice(0, 12);
        ctx.save("hist", hist);
        paintHist();
      }
      draw();
    }

    draw();

    function draw() {
      var g = cv.g, w = cv.w, h = cv.h;
      g.clearRect(0, 0, w, h);
      var cLine = ctx.color("line"), cSoft = ctx.color("lineSoft"), cDim = ctx.color("inkDim");
      var cAcc = ctx.color("accent"), cGo = ctx.color("go");

      var padL = 8, padR = 8, top = 10, bot = h - 20;
      var n = STUFEN.length, cw = (w - padL - padR) / n;

      g.font = "400 9px ui-monospace, monospace";
      g.textAlign = "center"; g.textBaseline = "top";
      for (var i = 0; i < n; i++) {
        var x = padL + cw * i, cxm = x + cw / 2;
        var state = results[i];
        var isNow = (idx === i);

        g.strokeStyle = cSoft; g.lineWidth = 1;
        g.beginPath(); g.moveTo(cxm, top); g.lineTo(cxm, bot); g.stroke();

        var hgt = (i + 1) / n * (bot - top - 8);
        var y = bot - hgt;
        if (state === true) { g.fillStyle = cGo; g.globalAlpha = 0.85; }
        else if (state === false) { g.fillStyle = cAcc; g.globalAlpha = 0.5; }
        else { g.fillStyle = cLine; g.globalAlpha = 0.5; }
        g.fillRect(x + 3, y, cw - 6, hgt);
        g.globalAlpha = 1;

        if (isNow) {
          g.strokeStyle = cAcc; g.lineWidth = 1.6;
          g.strokeRect(x + 3, y, cw - 6, hgt);
        }
        g.fillStyle = cDim;
        g.fillText(String(STUFEN[i] / 1000), cxm, bot + 4);
      }
      if (grenze) {
        var gi = STUFEN.indexOf(grenze);
        if (gi >= 0) {
          var gx = padL + cw * gi + cw / 2;
          g.strokeStyle = cAcc; g.lineWidth = 2;
          g.beginPath(); g.moveTo(gx, top); g.lineTo(gx, bot); g.stroke();
        }
      }
      g.fillStyle = cDim;
      g.textAlign = "right";
      g.fillText("kHz", w - 3, bot + 4);
    }

    return { unmount: function () { try { silence(); } catch (e) {} } };
  }

  /* ================================================================== */
  /* 3 — Metronom                                                        */
  /* ================================================================== */

  var TAKTE = [["2/4", 2], ["3/4", 3], ["4/4", 4], ["6/8", 6]];

  function mountMetronome(root, ctx) {
    styleOnce(root, "#gad-metronome .me-bpm{font-family:var(--f-data);font-size:52px;font-variant-numeric:tabular-nums;letter-spacing:-.03em;line-height:1}" +
      "#gad-metronome .me-takte{display:flex;gap:6px;flex-wrap:wrap}" +
      "#gad-metronome .me-t{flex:1;min-width:58px}" +
      "#gad-metronome .me-sub{font-size:13px;color:var(--ink-dim)}");

    var actx = ctx.audio();
    if (!actx) { noAudio(ctx); return; }

    var out = ctx.owned(actx.createGain());
    out.gain.value = 0.5;
    out.connect(actx.destination);

    var bpm = ctx.store("bpm", 100);
    var sigIdx = ctx.store("sig", 2);
    var beatsPerBar = TAKTE[sigIdx][1];
    var running = false;
    var nextTime = 0, beat = 0, bar = 0;
    var queue = [];
    var curBeat = -1, lastBeatTime = 0, beatDur = 0.6;
    var reduce = reducedMotion();

    // Übe-Werkzeuge
    var stepOn = ctx.store("stepOn", false);
    var stepBars = ctx.store("stepBars", 4);
    var stepBpm = ctx.store("stepBpm", 5);
    var stepZiel = ctx.store("stepZiel", 160);
    var muteOn = ctx.store("muteOn", false);
    var muteEvery = ctx.store("muteEvery", 4);

    var bpmEl = ctx.el("div", "me-bpm", String(bpm));
    var subEl = ctx.el("div", "me-sub", "Schläge pro Minute");
    var head = ctx.el("div");
    head.appendChild(bpmEl); head.appendChild(subEl);

    var cv = ctx.canvas(1.9);

    var sl = ctx.slider({ min: 30, max: 300, step: 1, value: bpm, unit: "bpm" });
    sl.onInput(function (v) { setBpm(v); });

    var taps = [];
    var btnTap = ctx.button("Tippen", function () {
      var now = (window.performance || Date).now();
      taps = taps.filter(function (t) { return now - t < 2500; });
      taps.push(now);
      if (taps.length >= 3) {
        var gaps = [];
        for (var i = 1; i < taps.length; i++) gaps.push(taps[i] - taps[i - 1]);
        gaps.sort(function (a, b) { return a - b; });
        var mid = gaps[Math.floor(gaps.length / 2)];
        var keep = gaps.filter(function (g2) { return Math.abs(g2 - mid) < mid * 0.35; });
        var s = 0;
        for (var j = 0; j < keep.length; j++) s += keep[j];
        if (keep.length) setBpm(clamp(Math.round(60000 / (s / keep.length)), 30, 300));
      }
      subEl.textContent = taps.length < 3 ? "weiter tippen …" : "Schläge pro Minute";
    });

    var taktRow = ctx.el("div", "me-takte");
    var taktBtns = [];
    TAKTE.forEach(function (t, i) {
      var b = ctx.button(t[0], function () {
        sigIdx = i; ctx.save("sig", i);
        beatsPerBar = t[1]; beat = 0; bar = 0;
        paintTakte();
      });
      b.className += " me-t";
      taktRow.appendChild(b);
      taktBtns.push(b);
    });
    function paintTakte() {
      taktBtns.forEach(function (b, i) { b.setAttribute("aria-pressed", i === sigIdx ? "true" : "false"); });
    }
    paintTakte();

    var btnRun = ctx.button("Start", function () { running ? stop() : start(); }, "go");

    var slStepBars = ctx.slider({ min: 1, max: 16, step: 1, value: stepBars, unit: "Takte" });
    slStepBars.onInput(function (v) { stepBars = v; ctx.save("stepBars", v); });
    var slStepBpm = ctx.slider({ min: 1, max: 20, step: 1, value: stepBpm, unit: "bpm" });
    slStepBpm.onInput(function (v) { stepBpm = v; ctx.save("stepBpm", v); });
    var slStepZiel = ctx.slider({ min: 40, max: 300, step: 1, value: stepZiel, unit: "bpm" });
    slStepZiel.onInput(function (v) { stepZiel = v; ctx.save("stepZiel", v); });
    var btnStep = ctx.button("Steigerung", function () {
      stepOn = !stepOn; ctx.save("stepOn", stepOn);
      btnStep.setAttribute("aria-pressed", stepOn ? "true" : "false");
    });
    btnStep.setAttribute("aria-pressed", stepOn ? "true" : "false");

    var slMute = ctx.slider({ min: 2, max: 8, step: 1, value: muteEvery, unit: "Takte" });
    slMute.onInput(function (v) { muteEvery = v; ctx.save("muteEvery", v); });
    var btnMute = ctx.button("Stille üben", function () {
      muteOn = !muteOn; ctx.save("muteOn", muteOn);
      btnMute.setAttribute("aria-pressed", muteOn ? "true" : "false");
    });
    btnMute.setAttribute("aria-pressed", muteOn ? "true" : "false");

    root.appendChild(head);
    root.appendChild(cv.node);
    var c1 = ctx.el("div", "g-card");
    c1.appendChild(ctx.field("Tempo", sl.node));
    c1.appendChild(ctx.row(btnTap, btnRun));
    c1.appendChild(ctx.field("Taktart", taktRow));
    root.appendChild(c1);

    var c2 = ctx.el("div", "g-card");
    c2.appendChild(ctx.el("div", "g-label", "Üben"));
    c2.appendChild(ctx.el("div", "g-note", "Steigerung zieht das Tempo schrittweise an, bis das Ziel erreicht ist. Stille üben lässt jeden x-ten Takt aus — dann musst du den Takt selbst halten und merkst sofort, ob du schleppst."));
    c2.appendChild(ctx.row(btnStep));
    c2.appendChild(ctx.field("Schneller werden alle", slStepBars.node));
    c2.appendChild(ctx.field("Und zwar um", slStepBpm.node));
    c2.appendChild(ctx.field("Zieltempo", slStepZiel.node));
    c2.appendChild(ctx.row(btnMute));
    c2.appendChild(ctx.field("jeden x-ten Takt aussetzen", slMute.node));
    root.appendChild(c2);

    function setBpm(v) {
      bpm = clamp(Math.round(v), 30, 300);
      ctx.save("bpm", bpm);
      bpmEl.textContent = String(bpm);
      sl.set(bpm);
    }

    function schedule(b, time, silent) {
      if (!silent) {
        var o = actx.createOscillator(), g2 = actx.createGain();
        o.type = "square";
        o.frequency.value = (b === 0) ? 1750 : 1100;
        g2.gain.setValueAtTime(0.0001, time);
        g2.gain.exponentialRampToValueAtTime(b === 0 ? 0.9 : 0.5, time + 0.003);
        g2.gain.exponentialRampToValueAtTime(0.0001, time + 0.055);
        o.connect(g2); g2.connect(out);
        o.start(time); o.stop(time + 0.07);
        o.onended = function () { try { o.disconnect(); g2.disconnect(); } catch (e) {} };
      }
      queue.push({ beat: b, time: time, silent: silent });
    }

    function tick() {
      if (!running) return;
      var horizon = actx.currentTime + 0.12;
      while (nextTime < horizon) {
        var silent = muteOn && (bar % muteEvery === muteEvery - 1);
        schedule(beat, nextTime, silent);
        var spb = 60 / bpm;
        nextTime += spb;
        beat++;
        if (beat >= beatsPerBar) {
          beat = 0; bar++;
          if (stepOn && bar > 0 && bar % stepBars === 0 && bpm < stepZiel) {
            setBpm(Math.min(stepZiel, bpm + stepBpm));
          }
        }
      }
    }

    function start() {
      if (running) return;
      if (actx.state === "suspended" && actx.resume) { try { actx.resume(); } catch (e) {} }
      running = true;
      beat = 0; bar = 0; queue.length = 0;
      nextTime = actx.currentTime + 0.08;
      btnRun.textContent = "Stopp";
      tick();
    }
    function stop() {
      running = false;
      queue.length = 0;
      curBeat = -1;
      btnRun.textContent = "Start";
    }

    ctx.every(25, tick);

    ctx.raf(function () {
      var now = actx.currentTime;
      while (queue.length && queue[0].time <= now) {
        var q = queue.shift();
        curBeat = q.beat;
        lastBeatTime = q.time;
        beatDur = 60 / bpm;
      }
      draw(now);
    });

    function draw(now) {
      var g = cv.g, w = cv.w, h = cv.h;
      g.clearRect(0, 0, w, h);
      var cLine = ctx.color("line"), cDim = ctx.color("inkDim");
      var cAcc = ctx.color("accent"), cCool = ctx.color("cool"), cPanel = ctx.color("panel");

      var phase = running ? clamp((now - lastBeatTime) / Math.max(beatDur, 0.05), 0, 1) : 0;

      // Pendel
      var pivotY = h * 0.14, len = h * 0.60, cx = w / 2;
      if (!reduce) {
        var swing = running ? Math.sin((curBeat + phase) * Math.PI) : 0;
        var ang = swing * 0.42;
        var bx = cx + Math.sin(ang) * len, by = pivotY + Math.cos(ang) * len;
        g.strokeStyle = cLine; g.lineWidth = 2;
        g.beginPath(); g.moveTo(cx, pivotY); g.lineTo(bx, by); g.stroke();
        g.fillStyle = running ? cAcc : cLine;
        g.beginPath(); g.arc(bx, by, 9, 0, Math.PI * 2); g.fill();
        g.fillStyle = cDim;
        g.beginPath(); g.arc(cx, pivotY, 4, 0, Math.PI * 2); g.fill();
      }

      // Schlagpunkte
      var n = beatsPerBar, r = 9, gap = Math.min(30, (w - 40) / n);
      var totalW = gap * (n - 1);
      var y = h - 20;
      for (var i = 0; i < n; i++) {
        var x = cx - totalW / 2 + gap * i;
        var on = running && curBeat === i;
        var accentB = (i === 0);
        g.beginPath(); g.arc(x, y, accentB ? r + 2 : r, 0, Math.PI * 2);
        if (on) { g.fillStyle = accentB ? cAcc : cCool; g.fill(); }
        else { g.fillStyle = cPanel; g.fill(); g.strokeStyle = accentB ? cDim : cLine; g.lineWidth = 1.4; g.stroke(); }
      }

      if (running && (stepOn || muteOn)) {
        g.fillStyle = cDim;
        g.font = "400 10px ui-monospace, monospace";
        g.textAlign = "center"; g.textBaseline = "top";
        var bits = ["Takt " + (bar + 1)];
        if (muteOn && bar % muteEvery === muteEvery - 1) bits.push("stumm");
        if (stepOn) bits.push("Ziel " + stepZiel);
        g.fillText(bits.join(" · "), cx, 4);
      }
    }

    return { unmount: function () { try { stop(); } catch (e) {} } };
  }

  /* ================================================================== */

  Gadgets.register({
    id: "tone", name: "Tongenerator", group: "Ton", needs: null,
    blurb: "20 Hz bis 20 kHz, vier Wellenformen, Sweep für Resonanzen.",
    mount: mountTone
  });

  Gadgets.register({
    id: "hearing", name: "Hörtest", group: "Ton", needs: null,
    blurb: "Findet deine obere Hörgrenze. Ergebnisse bleiben gespeichert.",
    mount: mountHearing
  });

  Gadgets.register({
    id: "metronome", name: "Metronom", group: "Ton", needs: null,
    blurb: "Taktfest geplant, mit Tap-Tempo, Steigerung und Stille-Übung.",
    mount: mountMetronome
  });
})();
