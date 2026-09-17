/* Gadget-Koffer · Gruppe "Welt"
 *
 *   speed  — GPS-Tacho mit Zifferblatt, Strecke und Höchstwert
 *   ruler  — kalibriertes Lineal auf der langen Bildschirmkante
 *   pulse  — optischer Puls-Messer (Fingerkuppe auf der Kamera)
 *
 * Klassisches Skript nach CONTRACT.md: kein Modul, keine Abhängigkeiten,
 * kein innerHTML, Farben nur über die Tokens.
 */
(function () {
  "use strict";

  if (!window.Gadgets || typeof window.Gadgets.register !== "function") { return; }

  var GROUP = "Welt";

  /* ------------------------------------------------------------------ *
   * Kleine Helfer
   * ------------------------------------------------------------------ */

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }

  function num(v, fallback) {
    var n = (typeof v === "number") ? v : parseFloat(v);
    return (typeof n === "number" && isFinite(n)) ? n : fallback;
  }

  function reducedMotion() {
    try {
      return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (e) { return false; }
  }

  function fData(size, weight) {
    return (weight || 500) + " " + size +
      'px "Azeret Mono", ui-monospace, SFMono-Regular, Menlo, monospace';
  }

  function fDisp(size, weight) {
    return (weight || 600) + " " + size +
      'px "Rajdhani", "Arial Narrow", system-ui, sans-serif';
  }

  function median(list) {
    if (!list || !list.length) { return 0; }
    var a = list.slice().sort(function (x, y) { return x - y; });
    var m = a.length >> 1;
    return (a.length % 2) ? a[m] : (a[m - 1] + a[m]) / 2;
  }

  /* Entfernung zweier Koordinaten in Metern (Haversine, Kugelmodell). */
  function haversine(lat1, lon1, lat2, lon2) {
    var R = 6371008.8;
    var p = Math.PI / 180;
    var dLat = (lat2 - lat1) * p;
    var dLon = (lon2 - lon1) * p;
    var s1 = Math.sin(dLat / 2);
    var s2 = Math.sin(dLon / 2);
    var a = s1 * s1 + Math.cos(lat1 * p) * Math.cos(lat2 * p) * s2 * s2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
  }

  var COMPASS = ["N", "NNO", "NO", "ONO", "O", "OSO", "SO", "SSO",
                 "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];

  function compassName(deg) {
    var d = ((deg % 360) + 360) % 360;
    return COMPASS[Math.round(d / 22.5) % 16];
  }

  /* ctx.el mit mehreren Klassen — classList.add verträgt keine Leerzeichen. */
  function maker(ctx) {
    return function (tag, cls, text) {
      var e = ctx.el(tag);
      if (cls) { e.setAttribute("class", cls); }
      if (text !== undefined && text !== null) { e.textContent = String(text); }
      return e;
    };
  }

  function styleTag(ctx, css) {
    var s = ctx.el("style");
    s.textContent = css;
    return s;
  }

  function roundRectPath(g, x, y, w, h, r) {
    var rr = Math.min(r, w / 2, h / 2);
    g.beginPath();
    g.moveTo(x + rr, y);
    g.lineTo(x + w - rr, y);
    g.quadraticCurveTo(x + w, y, x + w, y + rr);
    g.lineTo(x + w, y + h - rr);
    g.quadraticCurveTo(x + w, y + h, x + w - rr, y + h);
    g.lineTo(x + rr, y + h);
    g.quadraticCurveTo(x, y + h, x, y + h - rr);
    g.lineTo(x, y + rr);
    g.quadraticCurveTo(x, y, x + rr, y);
    g.closePath();
  }

  /* Statuszeile nur schreiben, wenn sich wirklich etwas ändert. */
  function statusGate(ctx) {
    var last = "";
    return function (text, kind) {
      var key = (kind || "info") + "|" + text;
      if (key === last) { return; }
      last = key;
      ctx.status(text, kind);
    };
  }

  /* ================================================================== *
   * 1 — GPS-Tacho
   * ================================================================== */

  var SPEED_CSS =
    "#gad-speed .w-cell{display:flex;flex-direction:column;gap:2px;align-items:flex-start;}" +
    "#gad-speed .w-cell .w-val{white-space:nowrap;line-height:1.15;}" +
    "#gad-speed .w-grid{margin-top:2px;}";

  function mountSpeed(root, ctx) {
    var mk = maker(ctx);
    var say = statusGate(ctx);
    var rm = reducedMotion();

    var RANGES = [
      { max: 20,  major: 5,  minor: 1, art: "zu Fuß" },
      { max: 60,  major: 10, minor: 2, art: "Rad" },
      { max: 200, major: 20, minor: 5, art: "Auto" }
    ];
    var ri = clamp(Math.round(num(ctx.store("range", 0), 0)), 0, RANGES.length - 1);

    var st = {
      have: false,      // je ein Fix angekommen
      speed: 0,         // geglättet, km/h
      peak: 0,          // abklingender Spitzenwert für die Bereichswahl
      max: 0,           // Höchstgeschwindigkeit seit Start
      dist: 0,          // Strecke in Metern
      alt: null, altAcc: null, acc: null, heading: null,
      last: null,       // letzte Position { lat, lon, t }
      fixAt: 0, fixes: 0,
      src: "",          // "doppler" | "rechnung"
      blind: true,      // Genauigkeit zu schlecht für eine ehrliche Zahl
      dead: false       // Fehler, kein Empfang
    };
    var needle = 0, needleV = 0;
    var gen = 0, running = false;

    root.appendChild(styleTag(ctx, SPEED_CSS));

    var readout = ctx.readout("km/h");
    root.appendChild(readout.node);
    readout.set("—", "warte auf den ersten Standort");

    var can = ctx.canvas(1.42);
    root.appendChild(can.node);

    var rangeNote = mk("div", "g-note", "");
    root.appendChild(rangeNote);

    function cell(label) {
      var box = mk("div", "g-card w-cell");
      box.appendChild(mk("div", "g-label", label));
      var v = mk("div", "g-big g-num w-val", "—");
      box.appendChild(v);
      return { node: box, set: function (t) { if (v.textContent !== t) { v.textContent = t; } } };
    }

    var cAlt   = cell("Höhe");
    var cAcc   = cell("Genauigkeit");
    var cHead  = cell("Richtung");
    var cDist  = cell("Strecke");
    var cMax   = cell("Höchstwert");
    var cAge   = cell("Letzte Meldung");

    var grid = mk("div", "g-grid2 w-grid");
    grid.appendChild(cAlt.node);
    grid.appendChild(cAcc.node);
    grid.appendChild(cHead.node);
    grid.appendChild(cDist.node);
    grid.appendChild(cMax.node);
    grid.appendChild(cAge.node);
    root.appendChild(grid);

    var btnReset = ctx.button("Zurücksetzen", function () {
      st.dist = 0; st.max = 0; st.peak = 0; st.last = null;
      paintValues();
      say("Strecke und Höchstwert stehen wieder auf null.", "ok");
    }, "quiet");

    var btnRetry = ctx.button("Nochmal versuchen", function () { startGeo(); }, "go");
    btnRetry.disabled = true;

    root.appendChild(ctx.row(btnReset, btnRetry));

    root.appendChild(mk("div", "g-note",
      "Die Geschwindigkeit kommt vom Empfänger selbst (Doppler) oder wird aus zwei " +
      "aufeinanderfolgenden Positionen gerechnet — dann ist sie träger und braucht " +
      "ein paar Sekunden, bis sie stimmt."));

    /* ---- Standort ---- */

    function startGeo() {
      gen++;
      var myGen = gen;
      running = true;
      st.dead = false;
      btnRetry.disabled = true;
      say("Suche den Standort …", "info");
      ctx.geo(function (pos, err) {
        if (myGen !== gen) { return; }
        if (err) { onGeoError(err); return; }
        if (pos) { onFix(pos); }
      });
    }

    function onGeoError(err) {
      st.dead = true;
      st.blind = true;
      running = false;
      btnRetry.disabled = false;
      readout.set("—", "kein Standort");
      var code = err && typeof err.code === "number" ? err.code : 0;
      if (code === 1) {
        say("Du hast den Zugriff auf den Standort abgelehnt. Ohne Standort kann der " +
            "Tacho nichts messen — gib den Standort in den Browser-Einstellungen für " +
            "diese Seite wieder frei und tippe dann auf Nochmal versuchen.", "error");
      } else if (code === 2) {
        say("Dein Gerät findet gerade keinen Standort. Zwischen hohen Häusern, im Zug " +
            "oder in Innenräumen kommt oft kein Satellitensignal an — geh ans Fenster " +
            "oder nach draußen.", "warn");
      } else if (code === 3) {
        say("Die Standortsuche hat zu lange gedauert. Das passiert beim ersten Fix nach " +
            "dem Einschalten — bleib einen Moment stehen und versuch es noch einmal.", "warn");
      } else {
        say("Der Standort ist nicht verfügbar" +
            (err && err.message ? " (" + err.message + ")" : "") +
            ". Versuch es gleich noch einmal.", "error");
      }
    }

    function onFix(pos) {
      var c = pos && pos.coords;
      if (!c) { return; }
      var wall = Date.now();
      var t = num(pos.timestamp, wall);
      if (Math.abs(wall - t) > 60000) { t = wall; }

      st.fixes++;
      st.fixAt = wall;
      st.acc = num(c.accuracy, null);
      st.alt = num(c.altitude, null);
      st.altAcc = num(c.altitudeAccuracy, null);
      var hd = num(c.heading, null);
      st.heading = (hd === null || hd < 0) ? null : hd;

      var acc = (st.acc === null) ? 15 : st.acc;
      st.blind = (st.acc !== null && st.acc > 50);

      var raw = null, src = "";
      var dopp = num(c.speed, null);
      if (dopp !== null && dopp >= 0 && dopp < 120) {
        raw = dopp * 3.6;
        src = "doppler";
      }

      var moved = null, dt = 0;
      if (st.last) {
        dt = (t - st.last.t) / 1000;
        if (dt > 0.25 && dt < 60) {
          moved = haversine(st.last.lat, st.last.lon, c.latitude, c.longitude);
        }
      }

      if (raw === null && moved !== null) {
        /* Rauschgrenze: unter einer halben Streubreite ist das keine Bewegung. */
        var gate = Math.max(1.5, acc * 0.5);
        var v = (moved < gate) ? 0 : (moved / dt) * 3.6;
        if (v <= 400) { raw = v; src = "rechnung"; }
      }

      if (raw !== null) {
        var a = (src === "doppler") ? 0.6 : 0.4;
        st.speed = st.have ? (st.speed + (raw - st.speed) * a) : raw;
        st.src = src;
        st.have = true;
      }

      /* Strecke nur zählen, wenn die Bewegung größer als das Rauschen ist. */
      if (moved !== null && acc <= 45) {
        var dGate = Math.max(2.5, acc * 0.7);
        if (moved > dGate) { st.dist += moved; }
      }

      if (!st.blind && st.speed > st.max && st.speed < 400 && acc <= 30) {
        st.max = st.speed;
      }
      st.peak = Math.max(st.blind ? 0 : st.speed, st.peak * 0.93);

      st.last = { lat: c.latitude, lon: c.longitude, t: t };
      st.dead = false;

      pickRange();
      paintValues();
      paintStatus();
    }

    function pickRange() {
      var want = ri;
      var s = Math.max(st.speed, st.peak);
      while (want < RANGES.length - 1 && s > RANGES[want].max * 0.92) { want++; }
      while (want > 0 && st.peak < RANGES[want - 1].max * 0.6) { want--; }
      if (want !== ri) {
        ri = want;
        ctx.save("range", ri);
      }
    }

    function paintStatus() {
      if (st.dead) { return; }
      if (st.acc === null) {
        say("Standort empfangen, aber ohne Angabe zur Genauigkeit.", "info");
      } else if (st.acc > 50) {
        say("Der Standort streut um ±" + Math.round(st.acc) + " m. Bei so viel " +
            "Unsicherheit wäre jede Geschwindigkeit Kaffeesatz — darum steht hier " +
            "keine. Geh ins Freie und warte, bis der Wert kleiner wird.", "warn");
      } else if (st.acc > 20) {
        say("Standort auf ±" + Math.round(st.acc) + " m genau — das reicht fürs Grobe, " +
            "kleine Geschwindigkeiten zappeln aber noch.", "info");
      } else {
        say("Standort auf ±" + Math.round(st.acc) + " m genau. " +
            (st.src === "doppler" ? "Geschwindigkeit direkt vom Empfänger."
                                  : "Geschwindigkeit aus den Positionen gerechnet."), "ok");
      }
    }

    function paintValues() {
      if (!st.have || st.blind) {
        readout.set("—", st.blind ? "Signal zu ungenau für eine ehrliche Zahl"
                                  : "warte auf den ersten Standort");
      } else {
        var d = st.speed < 10 ? 1 : 0;
        readout.set(ctx.fmt(st.speed, d),
          st.src === "doppler" ? "vom Empfänger gemessen" : "aus zwei Positionen gerechnet");
      }

      cAlt.set(st.alt === null ? "—" :
        ctx.fmt(st.alt, 0) + " m" + (st.altAcc !== null ? " ±" + ctx.fmt(st.altAcc, 0) : ""));
      cAcc.set(st.acc === null ? "—" : "±" + ctx.fmt(st.acc, st.acc < 10 ? 1 : 0) + " m");
      cHead.set(st.heading === null ? "—" :
        compassName(st.heading) + " " + ctx.fmt(st.heading, 0) + "°");
      cDist.set(st.dist >= 1000 ? ctx.fmt(st.dist / 1000, 2) + " km"
                                : ctx.fmt(st.dist, 0) + " m");
      cMax.set(st.max > 0 ? ctx.fmt(st.max, st.max < 10 ? 1 : 0) + " km/h" : "—");

      var R = RANGES[ri];
      rangeNote.textContent = "Messbereich: 0 bis " + R.max + " km/h (" + R.art +
        ") — schaltet sich selbst um.";
      paintAge();
    }

    function paintAge() {
      if (!st.fixAt) { cAge.set("—"); return; }
      var s = (Date.now() - st.fixAt) / 1000;
      cAge.set(s < 1.5 ? "jetzt" : ctx.fmt(s, 0) + " s her");
      if (s > 12 && !st.dead && st.have) {
        say("Seit " + ctx.fmt(s, 0) + " s kam kein neuer Standort mehr. Der angezeigte " +
            "Wert ist damit alt — such dir freien Himmel.", "warn");
      }
    }

    ctx.every(500, paintAge);

    /* ---- Zifferblatt ---- */

    function drawDial() {
      var g = can.g, w = can.w, h = can.h;
      if (!w || !h) { return; }
      g.clearRect(0, 0, w, h);

      var R = RANGES[ri];
      var pad = clamp(w * 0.04, 8, 18);
      var r = Math.min((w - pad * 2) / 2, (h - pad * 2) / 1.5);
      if (r < 34) { return; }
      var cx = w / 2, cy = pad + r;
      var A0 = Math.PI * 150 / 180;
      var SW = Math.PI * 240 / 180;
      var band = Math.max(5, r * 0.055);
      var rBand = r - band / 2;

      function ang(v) { return A0 + SW * clamp(v / R.max, 0, 1.02); }
      function off(a, rad) { return [cx + Math.cos(a) * rad, cy + Math.sin(a) * rad]; }

      g.lineCap = "butt";
      g.lineWidth = band;
      g.strokeStyle = ctx.color("sunk");
      g.beginPath(); g.arc(cx, cy, rBand, A0, A0 + SW); g.stroke();

      g.strokeStyle = ctx.color("warn");
      g.globalAlpha = 0.3;
      g.beginPath(); g.arc(cx, cy, rBand, ang(R.max * 0.85), A0 + SW); g.stroke();
      g.globalAlpha = 1;

      if (!st.blind && needle > 0.05) {
        g.strokeStyle = ctx.color("accent");
        g.beginPath(); g.arc(cx, cy, rBand, A0, ang(needle)); g.stroke();
      }

      /* Striche und Beschriftung */
      var rTick = rBand - band / 2 - 2;
      var fs = clamp(Math.round(r * 0.115), 9, 17);
      g.lineCap = "round";
      g.textAlign = "center";
      g.textBaseline = "middle";
      var steps = Math.round(R.max / R.minor);
      for (var i = 0; i <= steps; i++) {
        var v = i * R.minor;
        var maj = (Math.round(v / R.major) * R.major === v);
        var a = ang(v);
        var len = maj ? r * 0.125 : r * 0.055;
        var p1 = off(a, rTick), p2 = off(a, rTick - len);
        g.lineWidth = maj ? Math.max(2, r * 0.022) : Math.max(1, r * 0.012);
        g.strokeStyle = maj ? ctx.color("ink2") : ctx.color("line");
        g.beginPath(); g.moveTo(p1[0], p1[1]); g.lineTo(p2[0], p2[1]); g.stroke();
        if (maj) {
          var pl = off(a, rTick - len - fs * 0.85);
          g.font = fData(fs, 600);
          g.fillStyle = ctx.color("ink2");
          g.fillText(String(v), pl[0], pl[1]);
        }
      }

      /* Schleppzeiger: Höchstwert */
      if (st.max > R.max * 0.02) {
        var am = ang(st.max);
        var m1 = off(am, rBand + band / 2 + 3);
        var m2 = off(am, rBand - band / 2 - 3);
        g.strokeStyle = ctx.color("cool");
        g.lineWidth = Math.max(2, r * 0.02);
        g.beginPath(); g.moveTo(m1[0], m1[1]); g.lineTo(m2[0], m2[1]); g.stroke();
      }

      /* Zeiger */
      var an = ang(clamp(needle, 0, R.max * 1.02));
      var hw = Math.max(2.5, r * 0.035);
      var tip = off(an, r * 0.80);
      var tail = off(an + Math.PI, r * 0.14);
      var pa = off(an + Math.PI / 2, hw);
      var pb = off(an - Math.PI / 2, hw);
      g.fillStyle = st.blind ? ctx.color("inkDim") : ctx.color("accent");
      g.beginPath();
      g.moveTo(tip[0], tip[1]);
      g.lineTo(pb[0], pb[1]);
      g.lineTo(tail[0], tail[1]);
      g.lineTo(pa[0], pa[1]);
      g.closePath();
      g.fill();

      var hub = Math.max(6, r * 0.09);
      g.fillStyle = ctx.color("panel2");
      g.strokeStyle = ctx.color("line");
      g.lineWidth = 1.5;
      g.beginPath(); g.arc(cx, cy, hub, 0, Math.PI * 2); g.fill(); g.stroke();
      g.fillStyle = st.blind ? ctx.color("inkDim") : ctx.color("accent");
      g.beginPath(); g.arc(cx, cy, hub * 0.36, 0, Math.PI * 2); g.fill();

      /* Beschriftung in der Mitte */
      g.font = fDisp(clamp(Math.round(r * 0.12), 10, 18), 600);
      g.fillStyle = ctx.color("inkDim");
      g.fillText("km/h", cx, cy - r * 0.32);

      var sub = st.dead ? "kein Signal"
              : (st.blind ? "zu ungenau"
              : (st.have ? RANGES[ri].art : "warte auf Standort"));
      g.font = fData(clamp(Math.round(r * 0.095), 9, 14), 500);
      g.fillStyle = (st.blind || st.dead) ? ctx.color("warn") : ctx.color("inkDim");
      g.fillText(sub, cx, cy + r * 0.30);
    }

    ctx.raf(function (dt) {
      var s = clamp(dt, 0, 50) / 1000;
      var target = (st.blind || !st.have) ? 0 : Math.min(st.speed, RANGES[ri].max * 1.02);
      if (rm) {
        needle += (target - needle) * Math.min(1, s * 10);
        needleV = 0;
      } else {
        needleV += ((target - needle) * 70 - needleV * 12) * s;
        needle += needleV * s;
        if (needle < 0) { needle = 0; needleV = 0; }
      }
      drawDial();
    });

    paintValues();
    drawDial();
    startGeo();
  }

  /* ================================================================== *
   * 2 — Lineal
   * ================================================================== */

  var RULER_CSS =
    "#gad-ruler canvas{touch-action:none;}" +
    "#gad-ruler .r-cal{display:flex;flex-direction:column;gap:10px;}" +
    "#gad-ruler .r-target{overflow:hidden;padding:6px 0;}" +
    "#gad-ruler .r-bar{height:58px;max-width:100%;border:2px solid var(--accent);" +
      "border-radius:5px;background:var(--panel2);position:relative;}" +
    "#gad-ruler .r-bar::before,#gad-ruler .r-bar::after{content:\"\";position:absolute;" +
      "top:-6px;bottom:-6px;width:2px;background:var(--accent);}" +
    "#gad-ruler .r-bar::before{left:-2px;}#gad-ruler .r-bar::after{right:-2px;}" +
    "#gad-ruler .r-coin{max-width:100%;border:2px solid var(--accent);border-radius:50%;" +
      "background:var(--panel2);}" +
    "#gad-ruler .r-refs button.is-on{border-color:var(--accent);color:var(--accent);}" +
    "#gad-ruler .r-off{display:none;}";

  var REFS = [
    { id: "card-s", mm: 53.98, label: "Karte kurz",  hint: "kurze Kante der EC- oder Kreditkarte (53,98 mm)", coin: false },
    { id: "card-l", mm: 85.60, label: "Karte lang",  hint: "lange Kante der EC- oder Kreditkarte (85,60 mm)", coin: false },
    { id: "euro",   mm: 23.25, label: "1-Euro-Stück", hint: "Durchmesser einer Ein-Euro-Münze (23,25 mm)",   coin: true }
  ];

  function mountRuler(root, ctx) {
    var mk = maker(ctx);
    var say = statusGate(ctx);

    /* Schätzung, bis kalibriert wird: Handys rechnen mit rund 160 dpi
       je CSS-Pixel, Rechner mit 96 dpi. Beides ist nur ein Startwert. */
    var coarse = false;
    try {
      coarse = !!(window.matchMedia && window.matchMedia("(pointer: coarse)").matches);
    } catch (e) { coarse = false; }
    var GUESS = coarse ? 160 / 25.4 : 96 / 25.4;

    var ppmm = num(ctx.store("ppmm", 0), 0);
    var calibrated = ppmm >= 1.5 && ppmm <= 30;
    if (!calibrated) { ppmm = GUESS; }

    var inch = String(ctx.store("unit", "mm")) === "in";
    var refIdx = clamp(Math.round(num(ctx.store("ref", 0), 0)), 0, REFS.length - 1);

    var markA = 0, markB = 50;
    var maxMm = 100;
    var drag = 0;          // 0 = nichts, 1 = A, 2 = B
    var lastW = 0, lastH = 0;

    root.appendChild(styleTag(ctx, RULER_CSS));

    var readout = ctx.readout();
    root.appendChild(readout.node);

    /* Hochkant den langen Bildschirmrand nutzen, quer den breiten. */
    var vw = Math.max(240, window.innerWidth || 360);
    var vh = Math.max(320, window.innerHeight || 640);
    var aspect;
    if (vh >= vw) {
      aspect = clamp(Math.min(vw - 48, 520) / clamp(vh * 0.74, 300, 900), 0.3, 1.05);
    } else {
      aspect = 2.6;
    }
    var can = ctx.canvas(aspect);
    root.appendChild(can.node);

    var marksLine = mk("div", "g-note g-num", "");
    root.appendChild(marksLine);

    var btnUnit = ctx.button(inch ? "Auf Millimeter" : "Auf Zoll", function () {
      inch = !inch;
      ctx.save("unit", inch ? "in" : "mm");
      btnUnit.textContent = inch ? "Auf Millimeter" : "Auf Zoll";
      draw();
    }, "quiet");

    var btnMarks = ctx.button("Marken zurück", function () {
      markA = 0;
      markB = Math.min(50, maxMm);
      draw();
    }, "quiet");

    var calOpen = !calibrated;
    var btnCal = ctx.button(calOpen ? "Kalibrierung schließen" : "Kalibrieren", function () {
      calOpen = !calOpen;
      btnCal.textContent = calOpen ? "Kalibrierung schließen" : "Kalibrieren";
      if (calOpen) { cal.classList.remove("r-off"); } else { cal.classList.add("r-off"); }
      syncTarget();
    }, "go");

    root.appendChild(ctx.row(btnUnit, btnMarks, btnCal));

    /* ---- Kalibrier-Karte ---- */

    var cal = mk("div", "g-card r-cal");
    if (!calOpen) { cal.classList.add("r-off"); }
    root.appendChild(cal);

    cal.appendChild(mk("div", "g-label", "Kalibrieren"));
    cal.appendChild(mk("div", "g-note",
      "Leg eine EC- oder Kreditkarte an den Balken und zieh den Regler, bis der " +
      "Balken genau so breit ist wie die Karte. Bankkarten sind nach ISO 7810 " +
      "genormt: 85,60 mm lang, 53,98 mm hoch — überall auf der Welt gleich."));

    var refRow = mk("div", "g-row r-refs");
    var refBtns = [];
    (function () {
      for (var i = 0; i < REFS.length; i++) {
        (function (idx) {
          var b = ctx.button(REFS[idx].label, function () {
            refIdx = idx;
            ctx.save("ref", refIdx);
            syncRefButtons();
            syncTarget();
          }, "quiet");
          refBtns.push(b);
          refRow.appendChild(b);
        })(i);
      }
    })();
    cal.appendChild(refRow);

    var refHint = mk("div", "g-note", "");
    cal.appendChild(refHint);

    var targetWrap = mk("div", "r-target");
    var targetEl = mk("div", "r-bar");
    targetWrap.appendChild(targetEl);
    cal.appendChild(targetWrap);

    var sl = ctx.slider({ min: 2, max: 16, step: 0.02, value: ppmm, unit: "px/mm" });
    sl.onInput(function () {
      ppmm = clamp(num(sl.value(), ppmm), 2, 16);
      calibrated = true;
      ctx.save("ppmm", ppmm);
      syncTarget();
      draw();
    });
    cal.appendChild(ctx.field("Pixel je Millimeter", sl.node));

    function nudge(d) {
      ppmm = clamp(ppmm + d, 2, 16);
      calibrated = true;
      sl.set(ppmm);
      ctx.save("ppmm", ppmm);
      syncTarget();
      draw();
    }
    var btnMinus = ctx.button("−  feiner", function () { nudge(-0.02); }, "quiet");
    var btnPlus  = ctx.button("+  feiner", function () { nudge(0.02); }, "quiet");
    cal.appendChild(ctx.row(btnMinus, btnPlus));

    var calInfo = mk("div", "g-note g-num", "");
    cal.appendChild(calInfo);

    var calWarn = mk("div", "g-note", "");
    cal.appendChild(calWarn);

    var honest = mk("div", "g-note", "");
    root.appendChild(honest);

    function syncRefButtons() {
      for (var i = 0; i < refBtns.length; i++) {
        if (i === refIdx) { refBtns[i].classList.add("is-on"); }
        else { refBtns[i].classList.remove("is-on"); }
      }
    }

    function syncTarget() {
      var ref = REFS[refIdx];
      refHint.textContent = "Angelegt wird: " + ref.hint + ".";

      var wantPx = ref.mm * ppmm;
      var room = targetWrap.clientWidth || (root.clientWidth || 320);

      if (ref.coin) {
        targetEl.setAttribute("class", "r-coin");
        targetEl.style.width = wantPx.toFixed(1) + "px";
        targetEl.style.height = wantPx.toFixed(1) + "px";
      } else {
        targetEl.setAttribute("class", "r-bar");
        targetEl.style.width = wantPx.toFixed(1) + "px";
        targetEl.style.height = "";
      }

      if (room > 20 && wantPx > room) {
        calWarn.textContent = "Der Balken ist breiter als der Platz hier — nimm die " +
          "kurze Kante der Karte oder die Münze, sonst kalibrierst du auf einen " +
          "abgeschnittenen Balken.";
      } else {
        calWarn.textContent = "";
      }

      var sw = num(window.screen && window.screen.width, 0);
      var sh = num(window.screen && window.screen.height, 0);
      var screenTxt = (sw && sh)
        ? "  ·  Bildschirm rechnerisch " + ctx.fmt(sw / ppmm, 0) + " × " +
          ctx.fmt(sh / ppmm, 0) + " mm"
        : "";
      calInfo.textContent = ctx.fmt(ppmm, 2) + " px je mm" + screenTxt;
    }

    /* ---- Zeichnen ---- */

    function inchText(mm) {
      var v = mm / 25.4;
      var whole = Math.floor(v + 1e-9);
      var f = Math.round((v - whole) * 16);
      if (f >= 16) { whole += 1; f = 0; }
      if (f === 0) { return String(whole); }
      var n = f, d = 16;
      while (n % 2 === 0) { n /= 2; d /= 2; }
      return (whole > 0 ? whole + " " : "") + n + "/" + d;
    }

    function draw() {
      var g = can.g, w = can.w, h = can.h;
      if (!w || !h) { return; }
      lastW = w; lastH = h;
      var vert = h >= w;
      var L = vert ? h : w;
      var C = vert ? w : h;

      function P(along, cross) { return vert ? [cross, along] : [along, cross]; }

      var pad0 = 12, pad1 = 8;
      var L0 = pad0, L1 = L - pad1;
      maxMm = Math.max(10, (L1 - L0) / ppmm);
      markA = clamp(markA, 0, maxMm);
      markB = clamp(markB, 0, maxMm);

      g.clearRect(0, 0, w, h);
      g.fillStyle = ctx.color("panel2");
      g.fillRect(0, 0, w, h);

      /* Kante, an der gemessen wird */
      g.strokeStyle = ctx.color("ink2");
      g.lineWidth = 2;
      g.beginPath();
      var e0 = P(L0 - pad0, 1), e1 = P(L1 + pad1, 1);
      g.moveTo(e0[0], e0[1]); g.lineTo(e1[0], e1[1]);
      g.stroke();

      /* Skala */
      var base = 1;
      g.lineCap = "butt";
      g.textAlign = vert ? "left" : "center";
      g.textBaseline = vert ? "middle" : "top";

      var lenS, lenM, lenL, labelFs = clamp(Math.round(C * 0.11), 10, 15);

      if (!inch) {
        lenS = clamp(C * 0.16, 7, 16);
        lenM = clamp(C * 0.26, 12, 26);
        lenL = clamp(C * 0.40, 20, 44);
        var mmMax = Math.floor(maxMm);
        for (var m = 0; m <= mmMax; m++) {
          var pos = L0 + m * ppmm;
          if (pos > L1 + 0.5) { break; }
          var isCm = (m % 10 === 0);
          var isHalf = (m % 5 === 0);
          var len = isCm ? lenL : (isHalf ? lenM : lenS);
          g.lineWidth = isCm ? 2 : 1;
          g.strokeStyle = isCm ? ctx.color("ink") : (isHalf ? ctx.color("ink2") : ctx.color("line"));
          var q = Math.round(pos) + 0.5;
          var a1 = P(q, base), a2 = P(q, base + len);
          g.beginPath(); g.moveTo(a1[0], a1[1]); g.lineTo(a2[0], a2[1]); g.stroke();
          if (isCm && m > 0) {
            g.font = fData(labelFs, 600);
            g.fillStyle = ctx.color("ink");
            var lp = P(q, base + len + 4);
            if (vert) { g.fillText(String(m / 10), lp[0], lp[1]); }
            else { g.fillText(String(m / 10), lp[0], lp[1]); }
          }
        }
        g.font = fDisp(labelFs + 1, 600);
        g.fillStyle = ctx.color("inkDim");
        var up = P(L0 + 2, base + lenL + 4);
        g.textAlign = vert ? "left" : "left";
        g.fillText("cm", up[0], up[1] + (vert ? labelFs * 0.9 : 0));
      } else {
        var sixteenths = Math.floor(maxMm / 25.4 * 16);
        var pxPerSix = ppmm * 25.4 / 16;
        lenS = clamp(C * 0.14, 6, 14);
        for (var s = 0; s <= sixteenths; s++) {
          var posi = L0 + s * pxPerSix;
          if (posi > L1 + 0.5) { break; }
          var lvl = (s % 16 === 0) ? 4 : (s % 8 === 0 ? 3 : (s % 4 === 0 ? 2 : (s % 2 === 0 ? 1 : 0)));
          var leni = clamp(C * (0.13 + lvl * 0.07), 6, C * 0.46);
          g.lineWidth = (lvl === 4) ? 2 : 1;
          g.strokeStyle = lvl === 4 ? ctx.color("ink") : (lvl >= 2 ? ctx.color("ink2") : ctx.color("line"));
          var qi = Math.round(posi) + 0.5;
          var b1 = P(qi, base), b2 = P(qi, base + leni);
          g.beginPath(); g.moveTo(b1[0], b1[1]); g.lineTo(b2[0], b2[1]); g.stroke();
          if (lvl === 4 && s > 0) {
            g.font = fData(labelFs, 600);
            g.fillStyle = ctx.color("ink");
            var li = P(qi, base + leni + 4);
            g.fillText(String(s / 16), li[0], li[1]);
          }
        }
        g.font = fDisp(labelFs + 1, 600);
        g.fillStyle = ctx.color("inkDim");
        var ui = P(L0 + 2, base + clamp(C * 0.41, 6, C * 0.46) + 4);
        g.fillText("Zoll", ui[0], ui[1] + (vert ? -labelFs : 0));
      }

      /* Messschieber */
      var pA = L0 + markA * ppmm;
      var pB = L0 + markB * ppmm;
      var lo = Math.min(pA, pB), hi = Math.max(pA, pB);

      g.fillStyle = ctx.color("accent");
      g.globalAlpha = 0.12;
      var r0 = P(lo, 0), r1 = P(hi, 0);
      if (vert) { g.fillRect(0, lo, w, hi - lo); }
      else { g.fillRect(lo, 0, hi - lo, h); }
      g.globalAlpha = 1;

      drawMark(pA, "A", ctx.color("accent"));
      drawMark(pB, "B", ctx.color("cool"));

      function drawMark(pos, letter, col) {
        var q = Math.round(pos) + 0.5;
        g.strokeStyle = col;
        g.lineWidth = 2;
        g.beginPath();
        var m1 = P(q, 0), m2 = P(q, C);
        g.moveTo(m1[0], m1[1]); g.lineTo(m2[0], m2[1]);
        g.stroke();

        var hwv = 15, hh = 26;
        var cpos = C - hh - 4;
        var box = vert ? [cpos, q - hwv, hh, hwv * 2] : [q - hwv, cpos, hwv * 2, hh];
        g.fillStyle = ctx.color("panel");
        g.strokeStyle = col;
        g.lineWidth = 2;
        roundRectPath(g, box[0], box[1], box[2], box[3], 5);
        g.fill(); g.stroke();
        g.fillStyle = col;
        g.font = fDisp(14, 700);
        g.textAlign = "center";
        g.textBaseline = "middle";
        g.fillText(letter, box[0] + box[2] / 2, box[1] + box[3] / 2 + 0.5);
        g.textAlign = vert ? "left" : "center";
        g.textBaseline = vert ? "middle" : "top";
      }

      paintNumbers();
    }

    function paintNumbers() {
      var d = Math.abs(markB - markA);
      if (inch) {
        readout.set(inchText(d), "Zoll zwischen den Marken  ·  " + ctx.fmt(d / 25.4, 3) + " in");
      } else {
        readout.set(ctx.fmt(d, 1), "Millimeter zwischen den Marken  ·  " + ctx.fmt(d / 10, 2) + " cm");
      }
      marksLine.textContent = "A " + ctx.fmt(markA, 1) + " mm   ·   B " + ctx.fmt(markB, 1) +
        " mm   ·   nutzbare Länge " + ctx.fmt(maxMm, 0) + " mm";
      honest.textContent =
        "Ehrlich gesagt: genauer als die Kalibrierung wird das nie. Liegst du beim " +
        "Anlegen der Karte einen Millimeter daneben, ist jede Messung um rund zwei " +
        "Prozent daneben. Und der Bildschirm misst nur so weit, wie er lang ist — " +
        "hier sind das " + ctx.fmt(maxMm, 0) + " mm." +
        (calibrated ? "" : " Noch nicht kalibriert: der Startwert ist nur geschätzt.");
    }

    /* ---- Ziehen ---- */

    function posToMm(ev) {
      var rect = can.node.getBoundingClientRect();
      var vert = can.h >= can.w;
      var along = vert ? (ev.clientY - rect.top) : (ev.clientX - rect.left);
      return clamp((along - 12) / ppmm, 0, maxMm);
    }

    ctx.on(can.node, "pointerdown", function (ev) {
      var mm = posToMm(ev);
      var dA = Math.abs(mm - markA) * ppmm;
      var dB = Math.abs(mm - markB) * ppmm;
      if (dA <= 44 || dB <= 44) {
        drag = (dA <= dB) ? 1 : 2;
      } else {
        drag = (dA <= dB) ? 1 : 2;
        if (drag === 1) { markA = mm; } else { markB = mm; }
      }
      if (can.node.setPointerCapture && ev.pointerId !== undefined) {
        try { can.node.setPointerCapture(ev.pointerId); } catch (e) { /* egal */ }
      }
      ev.preventDefault();
      draw();
    });

    ctx.on(can.node, "pointermove", function (ev) {
      if (!drag) { return; }
      var mm = posToMm(ev);
      if (drag === 1) { markA = mm; } else { markB = mm; }
      ev.preventDefault();
      draw();
    });

    function endDrag() { drag = 0; }
    ctx.on(can.node, "pointerup", endDrag);
    ctx.on(can.node, "pointercancel", endDrag);
    ctx.on(window, "pointerup", endDrag);

    /* Größe, Thema und Kalibrierung können sich ändern — ruhig nachziehen. */
    ctx.every(250, function () {
      if (can.w !== lastW || can.h !== lastH) { draw(); }
      else { draw(); }
    });

    syncRefButtons();
    syncTarget();
    markB = Math.min(50, Math.max(10, maxMm * 0.5));
    draw();

    if (!calibrated) {
      say("Noch nicht kalibriert — der Startwert ist nur geschätzt. Leg eine Karte an " +
          "den Balken unten, dann stimmt das Lineal.", "warn");
    } else {
      say("Kalibriert auf " + ctx.fmt(ppmm, 2) + " Pixel je Millimeter. Zur Gegenprobe " +
          "das Ein-Euro-Stück auf den Kreis legen.", "ok");
    }
  }

  /* ================================================================== *
   * 3 — Puls-Messer
   * ================================================================== */

  var PULSE_CSS =
    "#gad-pulse .p-warn{border-left:3px solid var(--warn);padding-left:10px;}" +
    "#gad-pulse .p-q{display:flex;flex-direction:column;gap:2px;}";

  function mountPulse(root, ctx) {
    var mk = maker(ctx);
    var say = statusGate(ctx);
    var rm = reducedMotion();

    var MEASURE_MS = 10000;
    var S = 48;

    var off = ctx.el("canvas");
    off.width = S; off.height = S;
    var octx = null;
    try { octx = off.getContext("2d", { willReadFrequently: true }); }
    catch (e) { octx = off.getContext("2d"); }

    var video = null, track = null, torchOn = false, torchCap = false;
    var starting = false, live = false;

    var dc = null, acS = 0, envHi = 0, envLo = 0;
    var lastMr = null, motion = 0;
    var inBeat = false, peakV = 0, peakT = 0, lastBeat = 0;
    var intervals = [], beats = [], trace = [];
    var measureStart = 0, locked = false, bpmShown = 0, lastBpm = 0;
    var lastProc = 0, lastPaint = 0;
    var quality = "warten";

    root.appendChild(styleTag(ctx, PULSE_CSS));

    var readout = ctx.readout("bpm");
    root.appendChild(readout.node);
    readout.set("—", "Kamera ist aus");

    var can = ctx.canvas(2.3);
    root.appendChild(can.node);

    var qCard = mk("div", "g-card p-q");
    qCard.appendChild(mk("div", "g-label", "Signal"));
    var qVal = mk("div", "g-big", "Kamera aus");
    qCard.appendChild(qVal);
    var qSub = mk("div", "g-note", "Leg den Zeigefinger flach auf die Rückkamera — " +
      "sie muss ganz zugedeckt sein — und tippe auf Kamera einschalten.");
    qCard.appendChild(qSub);
    root.appendChild(qCard);

    var btnStart = ctx.button("Kamera einschalten", function () { start(); }, "go");
    var btnTorch = ctx.button("Licht aus", function () { setTorch(!torchOn); }, "quiet");
    btnTorch.disabled = true;
    var btnReset = ctx.button("Neu messen", function () { resetSignal(true); }, "quiet");
    root.appendChild(ctx.row(btnStart, btnTorch, btnReset));

    var warnCard = mk("div", "g-card p-warn");
    warnCard.appendChild(mk("div", "g-label", "Bitte lesen"));
    warnCard.appendChild(mk("div", "g-note",
      "Das hier ist eine Spielerei, kein Medizinprodukt. Die Zahl kann daneben liegen, " +
      "und Herzstolpern oder Rhythmusstörungen erkennt sie grundsätzlich nicht. " +
      "Wenn dir schwindelig ist, dein Herz stolpert oder dir die Brust weh tut: " +
      "geh zum Arzt, nicht zum Handy."));
    root.appendChild(warnCard);

    root.appendChild(mk("div", "g-note",
      "So geht das: Licht scheint durch die Fingerkuppe, bei jedem Herzschlag steht " +
      "kurz mehr Blut darin und schluckt etwas mehr davon. Die Kamera sieht diese " +
      "winzige Helligkeitsschwankung im Rotkanal. Das nennt sich Photoplethysmographie."));

    /* ---- Kamera ---- */

    function start() {
      if (starting || live) { return; }
      starting = true;
      btnStart.disabled = true;
      btnStart.textContent = "Kamera startet …";
      say("Kamera wird angefragt …", "info");

      ctx.camera({ facingMode: "environment", torch: true }).then(function (c) {
        onCamera(c, false);
      })["catch"](function (err) {
        if (err && (err.name === "OverconstrainedError" || err.name === "NotFoundError")) {
          ctx.camera({ facingMode: "user", torch: false }).then(function (c) {
            onCamera(c, true);
          })["catch"](camError);
        } else {
          camError(err);
        }
      });
    }

    function onCamera(c, isFront) {
      starting = false;
      live = true;
      video = c && c.video;
      btnStart.disabled = true;
      btnStart.textContent = "Kamera läuft";
      resetSignal(false);

      var tracks = (c && c.stream && c.stream.getVideoTracks) ? c.stream.getVideoTracks() : [];
      track = tracks.length ? tracks[0] : null;
      var caps = null;
      try { caps = (track && track.getCapabilities) ? track.getCapabilities() : null; }
      catch (e) { caps = null; }
      torchCap = !!(caps && caps.torch);

      if (torchCap) {
        btnTorch.disabled = false;
        setTorch(true);
      } else {
        btnTorch.disabled = true;
        btnTorch.textContent = "Licht nicht schaltbar";
        say("Dein Gerät lässt die Taschenlampe nicht über den Browser einschalten. " +
            "Halte den Finger stattdessen vor eine Lampe oder setz dich ans Fenster — " +
            "ohne Licht kommt nichts durch die Fingerkuppe.", "warn");
      }
      if (isFront) {
        say("Die Rückkamera war nicht zu haben, es läuft die Frontkamera. Ohne Blitz " +
            "brauchst du eine helle Lampe direkt am Finger.", "warn");
      }
    }

    function setTorch(on) {
      if (!track || !torchCap || !track.applyConstraints) { return; }
      track.applyConstraints({ advanced: [{ torch: !!on }] }).then(function () {
        torchOn = !!on;
        btnTorch.textContent = torchOn ? "Licht aus" : "Licht an";
      })["catch"](function () {
        torchCap = false;
        btnTorch.disabled = true;
        btnTorch.textContent = "Licht nicht schaltbar";
        say("Das Licht ließ sich nicht einschalten. Nimm eine Lampe zu Hilfe oder " +
            "halte den Finger ans Fenster.", "warn");
      });
    }

    function camError(err) {
      starting = false;
      live = false;
      btnStart.disabled = false;
      btnStart.textContent = "Nochmal versuchen";
      readout.set("—", "keine Kamera");
      qVal.textContent = "Kamera aus";
      var n = (err && err.name) ? err.name : "";
      if (n === "NotAllowedError" || n === "PermissionDeniedError" || n === "SecurityError") {
        say("Du hast der Seite die Kamera verweigert. Ohne Kamera geht hier nichts — " +
            "gib sie in den Browser-Einstellungen für diese Seite frei und versuch es " +
            "noch einmal.", "error");
      } else if (n === "NotFoundError" || n === "DevicesNotFoundError") {
        say("Dieses Gerät hat keine Kamera, die der Browser ansprechen kann.", "error");
      } else if (n === "NotReadableError" || n === "TrackStartError") {
        say("Die Kamera ist gerade von einer anderen App belegt. Schließ die andere " +
            "App und versuch es noch einmal.", "error");
      } else {
        say("Die Kamera ließ sich nicht starten" +
            (err && err.message ? " (" + err.message + ")" : "") + ".", "error");
      }
    }

    function resetSignal(hard) {
      dc = null; acS = 0; envHi = 0; envLo = 0;
      lastMr = null; motion = 0;
      inBeat = false; peakV = 0; peakT = 0; lastBeat = 0;
      intervals = []; beats = []; trace = [];
      measureStart = 0; locked = false;
      if (hard) {
        bpmShown = 0; lastBpm = 0;
        readout.set("—", live ? "misst …" : "Kamera ist aus");
      }
    }

    /* ---- Signalkette ---- */

    function process(t) {
      if (!live || !video || !octx) { return; }
      if (video.readyState < 2 || !video.videoWidth) { return; }

      var vw = video.videoWidth, vh = video.videoHeight;
      var side = Math.min(vw, vh) * 0.6;
      try {
        octx.drawImage(video, (vw - side) / 2, (vh - side) / 2, side, side, 0, 0, S, S);
      } catch (e) { return; }

      var d;
      try { d = octx.getImageData(0, 0, S, S).data; }
      catch (e) { return; }

      var sr = 0, sg = 0, sb = 0, sr2 = 0, n = 0;
      for (var i = 0; i < d.length; i += 8) {
        var r = d[i];
        sr += r; sg += d[i + 1]; sb += d[i + 2];
        sr2 += r * r;
        n++;
      }
      if (!n) { return; }
      var mr = sr / n, mg = sg / n, mb = sb / n;
      var varR = Math.max(0, sr2 / n - mr * mr);

      var dts = clamp(t - lastProc, 8, 200) / 1000;
      lastProc = t;

      /* Bewegung: sprunghafte Änderung der Grundhelligkeit */
      if (lastMr !== null) {
        var jump = Math.abs(mr - lastMr);
        motion = motion * 0.9 + (jump > 3.5 ? jump : 0) * 0.1;
      }
      lastMr = mr;

      /* Gleichanteil abziehen */
      var aDC = 1 - Math.exp(-dts / 1.1);
      dc = (dc === null) ? mr : dc + (mr - dc) * aDC;
      var ac = mr - dc;
      var aAC = 1 - Math.exp(-dts / 0.09);
      acS = acS + (ac - acS) * aAC;

      /* Hüllkurve */
      var decay = Math.max(0.02, (envHi - envLo)) * dts * 0.45;
      envHi = Math.max(acS, envHi - decay);
      envLo = Math.min(acS, envLo + decay);
      var amp = envHi - envLo;

      /* Zustand beurteilen */
      var dark  = mr < 28;
      var scene = varR > 1600 || (mr - mb) < 6;
      var sat   = mr > 250;
      var moving = motion > 1.6;
      var weak  = amp < 0.28;

      var ok = false;
      if (!live) { quality = "warten"; }
      else if (dark) { quality = "dunkel"; }
      else if (scene) { quality = "kein-finger"; }
      else if (sat) { quality = "hell"; }
      else if (moving) { quality = "bewegt"; }
      else if (weak) { quality = "schwach"; }
      else { quality = "gut"; ok = true; }

      trace.push({ t: t, v: amp > 0.0001 ? clamp((acS - (envLo + amp / 2)) / (amp / 2), -1.4, 1.4) : 0 });
      while (trace.length > 400) { trace.shift(); }

      if (!ok) {
        measureStart = 0;
        if (locked && (quality === "kein-finger" || quality === "dunkel")) { locked = false; }
        inBeat = false;
        return;
      }

      if (!measureStart) { measureStart = t; }

      /* Maxima mit Hysterese */
      var thHi = envLo + amp * 0.60;
      var thLo = envLo + amp * 0.35;
      if (!inBeat && acS > thHi) {
        inBeat = true; peakV = acS; peakT = t;
      } else if (inBeat) {
        if (acS > peakV) { peakV = acS; peakT = t; }
        if (acS < thLo) {
          inBeat = false;
          if (lastBeat && (peakT - lastBeat) > 300 && (peakT - lastBeat) < 1500) {
            intervals.push(peakT - lastBeat);
            while (intervals.length > 10) { intervals.shift(); }
            beats.push(peakT);
            while (beats.length > 40) { beats.shift(); }
          } else if (lastBeat && (peakT - lastBeat) >= 1500) {
            intervals = [];
          }
          if (!lastBeat) { beats.push(peakT); }
          lastBeat = peakT;
        }
      }

      /* Auswertung */
      if (intervals.length >= 4) {
        var med = median(intervals);
        var spread = 0, k;
        for (k = 0; k < intervals.length; k++) {
          spread += Math.abs(intervals[k] - med);
        }
        spread = (spread / intervals.length) / (med || 1);
        var bpm = 60000 / (med || 1);
        var plausible = bpm >= 40 && bpm <= 200 && spread < 0.14;
        if (plausible) {
          lastBpm = bpm;
          if (!locked && (t - measureStart) >= MEASURE_MS) { locked = true; }
          if (locked) {
            bpmShown = bpmShown ? bpmShown + (bpm - bpmShown) * 0.25 : bpm;
          }
        }
      }
    }

    function paint(t) {
      if (t - lastPaint < 250) { return; }
      lastPaint = t;

      var qTxt = {
        "warten": "Kamera aus",
        "dunkel": "Zu wenig Licht",
        "kein-finger": "Kein Finger auf der Linse",
        "hell": "Überstrahlt",
        "bewegt": "Finger bewegt sich",
        "schwach": "Signal noch schwach",
        "gut": "Gutes Signal"
      }[quality] || "—";
      var qHint = {
        "warten": "Tippe auf Kamera einschalten.",
        "dunkel": "Schalte das Licht ein oder halte den Finger an eine Lampe.",
        "kein-finger": "Die Fingerkuppe muss die Linse ganz zudecken.",
        "hell": "Schieb den Finger ein wenig, bis es nicht mehr weiß ausbrennt.",
        "bewegt": "Halt still — schon ein Zittern übertönt den Herzschlag.",
        "schwach": "Leg den Finger sanft auf, nicht fest drücken. Zu viel Druck quetscht das Blut heraus.",
        "gut": "So lassen, gleich steht die Zahl da."
      }[quality] || "";
      if (qVal.textContent !== qTxt) { qVal.textContent = qTxt; }
      if (qSub.textContent !== qHint) { qSub.textContent = qHint; }

      if (!live) {
        readout.set("—", "Kamera ist aus");
      } else if (locked && bpmShown >= 40 && bpmShown <= 200) {
        readout.set(ctx.fmt(bpmShown, 0), "Schläge pro Minute  ·  " +
          ctx.fmt(60000 / bpmShown / 1000, 2) + " s zwischen zwei Schlägen");
      } else if (measureStart) {
        var left = Math.max(0, Math.ceil((MEASURE_MS - (t - measureStart)) / 1000));
        readout.set("—", left > 0 ? ("misst … " + left + " s")
                                  : "misst … Signal noch nicht stabil" +
                                    (lastBpm ? "  ·  zuletzt " + ctx.fmt(lastBpm, 0) : ""));
      } else {
        readout.set("—", lastBpm ? ("warte auf Finger  ·  zuletzt " + ctx.fmt(lastBpm, 0))
                                 : "warte auf Finger");
      }

      if (live && quality === "gut") {
        say("Finger liegt gut auf. Ruhig atmen und still halten.", "ok");
      } else if (live && quality === "kein-finger") {
        say("Die Kamera sieht noch den Raum statt deinen Finger. Leg die Fingerkuppe " +
            "flach auf die Linse, sodass kein Licht daneben vorbeikommt.", "info");
      } else if (live && quality === "dunkel" && !torchOn) {
        say("Zu dunkel. Ohne Licht durchleuchtet nichts die Fingerkuppe — schalte das " +
            "Licht ein oder nimm eine Lampe.", "warn");
      }
    }

    /* ---- Schreiber ---- */

    function drawTrace(t) {
      var g = can.g, w = can.w, h = can.h;
      if (!w || !h) { return; }
      g.clearRect(0, 0, w, h);
      g.fillStyle = ctx.color("sunk");
      g.fillRect(0, 0, w, h);

      var WIN = 6000;
      var mid = h / 2;

      g.strokeStyle = ctx.color("lineSoft");
      g.lineWidth = 1;
      for (var s = 1; s <= 6; s++) {
        var x = Math.round(w - (s * 1000 / WIN) * w) + 0.5;
        g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke();
      }
      g.strokeStyle = ctx.color("line");
      g.beginPath(); g.moveTo(0, Math.round(mid) + 0.5); g.lineTo(w, Math.round(mid) + 0.5); g.stroke();

      var i;
      /* Schläge markieren */
      g.strokeStyle = ctx.color("cool");
      g.lineWidth = 1;
      for (i = 0; i < beats.length; i++) {
        var age = t - beats[i];
        if (age < 0 || age > WIN) { continue; }
        var bx = Math.round(w - (age / WIN) * w) + 0.5;
        g.globalAlpha = 0.55;
        g.beginPath(); g.moveTo(bx, mid - h * 0.38); g.lineTo(bx, mid + h * 0.38); g.stroke();
        g.globalAlpha = 1;
      }

      if (trace.length > 1) {
        g.strokeStyle = ctx.color("accent");
        g.lineWidth = 2;
        g.lineJoin = "round";
        g.beginPath();
        var started = false;
        for (i = 0; i < trace.length; i++) {
          var a = t - trace[i].t;
          if (a < 0 || a > WIN) { continue; }
          var px = w - (a / WIN) * w;
          var py = mid - trace[i].v * (h * 0.36);
          if (!started) { g.moveTo(px, py); started = true; }
          else { g.lineTo(px, py); }
        }
        g.stroke();
      } else {
        g.strokeStyle = ctx.color("inkDim");
        g.lineWidth = 1.5;
        g.globalAlpha = 0.7;
        g.beginPath(); g.moveTo(0, mid); g.lineTo(w, mid); g.stroke();
        g.globalAlpha = 1;
      }

      g.font = fDisp(11, 600);
      g.fillStyle = ctx.color("inkDim");
      g.textAlign = "left";
      g.textBaseline = "top";
      g.fillText(live ? "Pulskurve · letzte 6 Sekunden" : "Pulskurve · wartet auf die Kamera", 8, 6);

      /* Taktpunkt, höchstens 200-mal je Minute — kein Flimmern */
      if (!rm && live && lastBeat && (t - lastBeat) < 220) {
        g.fillStyle = ctx.color("accent");
        g.beginPath();
        g.arc(w - 14, 14, 5 * (1 - (t - lastBeat) / 220) + 3, 0, Math.PI * 2);
        g.fill();
      }
    }

    ctx.raf(function (dt, t) {
      var now = (typeof t === "number" && isFinite(t)) ? t : Date.now();
      if (!lastProc) { lastProc = now - 33; }
      if (now - lastProc >= 30) { process(now); }
      drawTrace(now);
      paint(now);
    });

    drawTrace(0);
    say("Leg den Zeigefinger flach auf die Rückkamera und schalte die Kamera ein. " +
        "Nicht drücken — nur auflegen.", "info");

    return {
      unmount: function () {
        /* Das Licht habe ich an ctx vorbei eingeschaltet, also mache ich es aus. */
        try {
          if (track && torchCap && torchOn && track.applyConstraints) {
            track.applyConstraints({ advanced: [{ torch: false }] })["catch"](function () {});
          }
        } catch (e) { /* Gerät ist schon weg */ }
        track = null;
        video = null;
        live = false;
      }
    };
  }

  /* ================================================================== *
   * Registrierung
   * ================================================================== */

  Gadgets.register({
    id: "speed",
    name: "GPS-Tacho",
    group: GROUP,
    blurb: "Geschwindigkeit, Strecke und Höhe aus dem Satellitensignal.",
    needs: "geo",
    mount: mountSpeed
  });

  Gadgets.register({
    id: "ruler",
    name: "Lineal",
    group: GROUP,
    blurb: "Kalibrierte Skala auf der langen Bildschirmkante.",
    needs: null,
    mount: mountRuler
  });

  Gadgets.register({
    id: "pulse",
    name: "Puls-Messer",
    group: GROUP,
    blurb: "Herzschlag über die Kamera an der Fingerkuppe.",
    needs: "camera",
    mount: mountPulse
  });
})();
