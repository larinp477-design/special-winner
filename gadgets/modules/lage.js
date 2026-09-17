/* Gadget-Koffer — Gruppe "Lage"
 * Wasserwaage, Kompass, Erschütterungsmesser.
 * Klassisches Skript, kein Modul. Baut nach CONTRACT.md.
 */
(function () {
  "use strict";

  var D2R = Math.PI / 180, R2D = 180 / Math.PI;

  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function lerp(a, b, k) { return a + (b - a) * k; }

  /* Wacht darüber, ob überhaupt Sensorwerte eintreffen. Auf dem Schreibtisch
   * existiert DeviceOrientationEvent, feuert aber nie — das ist kein Fehler,
   * sondern ein erklärter Zustand. */
  function watchdog(ctx, seenRef, text) {
    var t = setTimeout(function () {
      if (!seenRef.seen) ctx.status(text, "warn");
    }, 2500);
    ctx.on(window, "pagehide", function () { clearTimeout(t); });
    return function () { clearTimeout(t); };
  }

  function styleOnce(root, id, css) {
    var s = document.createElement("style");
    s.textContent = css;
    root.appendChild(s);
  }

  /* ================================================================== */
  /* 1 — Wasserwaage                                                     */
  /* ================================================================== */

  function mountLevel(root, ctx) {
    styleOnce(root, "level", "#gad-level .lv-vals{display:flex;gap:26px;flex-wrap:wrap}" +
      "#gad-level .lv-val{display:flex;flex-direction:column;gap:1px}" +
      "#gad-level .lv-num{font-family:var(--f-data);font-size:27px;font-variant-numeric:tabular-nums;letter-spacing:-.02em}");

    var mode = ctx.store("mode", "dose");          // "dose" | "kante"
    var off = ctx.store("off", { beta: 0, gamma: 0 });
    if (!off || typeof off.beta !== "number") off = { beta: 0, gamma: 0 };

    var cv = ctx.canvas(1);
    var seen = { seen: false };
    var raw = { beta: 0, gamma: 0 };
    var sm = { beta: 0, gamma: 0 };

    var vals = ctx.el("div", "lv-vals");
    function valBox(label) {
      var box = ctx.el("div", "lv-val");
      box.appendChild(ctx.el("div", "g-label", label));
      var n = ctx.el("div", "lv-num", "–");
      box.appendChild(n);
      vals.appendChild(box);
      return n;
    }
    var nLaengs = valBox("Längs");
    var nQuer = valBox("Quer");
    var nExtra = valBox("Gefälle");
    nExtra.parentNode.style.display = "none";

    var btnMode = ctx.button("Kante", function () {
      mode = (mode === "dose") ? "kante" : "dose";
      ctx.save("mode", mode);
      applyMode();
    });
    var btnZero = ctx.button("Nullen", function () {
      off = { beta: raw.beta, gamma: raw.gamma };
      ctx.save("off", off);
      ctx.status("Nullpunkt gesetzt. Diese Lage gilt jetzt als gerade.", "ok");
    });
    var btnReset = ctx.button("Zurücksetzen", function () {
      off = { beta: 0, gamma: 0 };
      ctx.save("off", off);
      ctx.status("Nullpunkt verworfen. Es gilt wieder die Werkseinstellung.");
    }, "quiet");

    function applyMode() {
      var dose = (mode === "dose");
      btnMode.textContent = dose ? "Kante" : "Dose";
      nQuer.parentNode.style.display = dose ? "" : "none";
      nExtra.parentNode.style.display = dose ? "none" : "";
      nLaengs.parentNode.firstChild.textContent = dose ? "Längs" : "Winkel";
    }
    applyMode();

    root.appendChild(cv.node);
    var card = ctx.el("div", "g-card");
    card.appendChild(vals);
    card.appendChild(ctx.row(btnMode, btnZero, btnReset));
    card.appendChild(ctx.el("div", "g-note",
      "Dose: flach hinlegen, die Blase muss in den Ring. Kante: die lange Seite des Telefons auf die Fläche legen, dann steht neben dem Winkel das Gefälle in Prozent. Nullen gleicht eine krumme Hülle aus."));
    root.appendChild(card);

    ctx.motion().then(function (ok) {
      if (!ok) {
        ctx.status("Keine Freigabe für die Lagesensoren. Auf dem iPhone fragt Safari einmalig nach — die Seite neu laden und erlauben.", "error");
        return;
      }
      ctx.on(window, "deviceorientation", function (e) {
        if (e.beta == null && e.gamma == null) return;
        seen.seen = true;
        raw.beta = e.beta || 0;
        raw.gamma = e.gamma || 0;
      });
      watchdog(ctx, seen, "Die Lagesensoren melden nichts. Am Rechner ist das normal — dieses Instrument braucht ein Telefon.");
    });

    var lastNum = 0;
    ctx.raf(function (dt, t) {
      var k = clamp(dt / 120, 0.02, 0.35);
      sm.beta = lerp(sm.beta, raw.beta - off.beta, k);
      sm.gamma = lerp(sm.gamma, raw.gamma - off.gamma, k);
      draw(t);
      if (t - lastNum > 100) { lastNum = t; numbers(); }
    });

    function numbers() {
      if (mode === "dose") {
        nLaengs.textContent = ctx.fmt(sm.beta, 1) + "°";
        nQuer.textContent = ctx.fmt(sm.gamma, 1) + "°";
      } else {
        var a = sm.beta;
        nLaengs.textContent = ctx.fmt(a, 1) + "°";
        var pct = Math.tan(clamp(a, -89, 89) * D2R) * 100;
        nExtra.textContent = ctx.fmt(pct, 1) + " %";
      }
    }

    function draw(t) {
      var g = cv.g, w = cv.w, h = cv.h;
      var cx = w / 2, cy = h / 2;
      var R = Math.min(w, h) / 2 - 12;
      g.clearRect(0, 0, w, h);

      var cLine = ctx.color("line"), cDim = ctx.color("inkDim");
      var cAcc = ctx.color("accent"), cGo = ctx.color("go"), cPanel = ctx.color("panel");

      // Gehäuse
      g.fillStyle = cPanel;
      g.beginPath();
      if (mode === "dose") { g.arc(cx, cy, R, 0, Math.PI * 2); }
      else { roundRect(g, 10, cy - R * 0.30, w - 20, R * 0.60, 6); }
      g.fill();
      g.strokeStyle = cLine; g.lineWidth = 1.2; g.stroke();

      if (mode === "dose") {
        // Skalenstriche alle 15°, lange alle 45°
        g.strokeStyle = cLine;
        for (var a = 0; a < 360; a += 15) {
          var lng = (a % 45 === 0);
          var r1 = R - (lng ? 9 : 5), r2 = R - 1;
          g.lineWidth = lng ? 1.4 : 1;
          g.beginPath();
          g.moveTo(cx + Math.cos(a * D2R) * r1, cy + Math.sin(a * D2R) * r1);
          g.lineTo(cx + Math.cos(a * D2R) * r2, cy + Math.sin(a * D2R) * r2);
          g.stroke();
        }
        // Zielringe: innen 0,5°, außen 2°
        var span = 12;                      // Vollausschlag in Grad
        var rIn = R * (0.5 / span), rMid = R * (2 / span);
        g.strokeStyle = cDim; g.lineWidth = 1;
        ring(g, cx, cy, Math.max(rMid, 14));
        g.strokeStyle = cAcc; g.lineWidth = 1.4;
        ring(g, cx, cy, Math.max(rIn, 7));
        // Fadenkreuz
        g.strokeStyle = cLine; g.lineWidth = 1;
        g.beginPath(); g.moveTo(cx - R, cy); g.lineTo(cx + R, cy);
        g.moveTo(cx, cy - R); g.lineTo(cx, cy + R); g.stroke();

        // Blase
        var level = (Math.abs(sm.beta) < 0.5 && Math.abs(sm.gamma) < 0.5);
        var bx = cx + clamp(sm.gamma / span, -1, 1) * (R - 20);
        var by = cy + clamp(sm.beta / span, -1, 1) * (R - 20);
        bubble(g, bx, by, 15, level ? cGo : cAcc);
        if (level) { g.strokeStyle = cGo; g.lineWidth = 2; ring(g, cx, cy, Math.max(rIn, 7) + 4); }
      } else {
        // Waagerechtes Röhrchen
        var tubeW = w - 20, tubeH = R * 0.60;
        var ty = cy - tubeH / 2;
        var spanK = 10;
        g.strokeStyle = cLine; g.lineWidth = 1;
        for (var i = -5; i <= 5; i++) {
          var x = cx + (i / 5) * (tubeW / 2 - 16);
          var big = (i === 0);
          g.lineWidth = big ? 1.6 : 1;
          g.strokeStyle = big ? cAcc : cLine;
          g.beginPath(); g.moveTo(x, ty + 4); g.lineTo(x, ty + tubeH - 4); g.stroke();
        }
        var lvl2 = Math.abs(sm.beta) < 0.3;
        var px = cx + clamp(sm.beta / spanK, -1, 1) * (tubeW / 2 - 16);
        bubble(g, px, cy, tubeH * 0.32, lvl2 ? cGo : cAcc);
      }
    }

    function ring(g, x, y, r) { g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.stroke(); }
    function bubble(g, x, y, r, col) {
      g.fillStyle = col;
      g.globalAlpha = 0.85;
      g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill();
      g.globalAlpha = 1;
      g.strokeStyle = col; g.lineWidth = 1.5;
      g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.stroke();
    }
    function roundRect(g, x, y, w, h, r) {
      g.beginPath();
      g.moveTo(x + r, y);
      g.arcTo(x + w, y, x + w, y + h, r);
      g.arcTo(x + w, y + h, x, y + h, r);
      g.arcTo(x, y + h, x, y, r);
      g.arcTo(x, y, x + w, y, r);
      g.closePath();
    }
  }

  /* ================================================================== */
  /* 2 — Kompass                                                         */
  /* ================================================================== */

  var DIRS = [
    [0, "Nord"], [45, "Nordost"], [90, "Ost"], [135, "Südost"],
    [180, "Süd"], [225, "Südwest"], [270, "West"], [315, "Nordwest"]
  ];
  function dirName(deg) {
    var i = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
    return DIRS[i][1];
  }

  function mountCompass(root, ctx) {
    styleOnce(root, "compass", "#gad-compass .cp-head{display:flex;align-items:baseline;gap:12px}" +
      "#gad-compass .cp-deg{font-family:var(--f-data);font-size:44px;font-variant-numeric:tabular-nums;letter-spacing:-.03em;line-height:1}" +
      "#gad-compass .cp-dir{font-family:var(--f-disp);font-weight:600;font-size:23px;letter-spacing:.04em}");

    var cv = ctx.canvas(1);
    var seen = { seen: false };
    var absolute = false;
    var heading = 0;                 // Rohwert
    var sx = 1, sy = 0;              // geglättet als Einheitsvektor
    var bearing = ctx.store("bearing", null);

    var head = ctx.el("div", "cp-head");
    var degEl = ctx.el("div", "cp-deg", "–");
    var dirEl = ctx.el("div", "cp-dir", "");
    head.appendChild(degEl); head.appendChild(dirEl);

    var deltaEl = ctx.el("div", "g-note", "");

    var btnMark = ctx.button("Peilung merken", function () {
      bearing = smoothed();
      ctx.save("bearing", bearing);
      btnClear.disabled = false;
      ctx.status("Peilung bei " + Math.round(bearing) + "° gemerkt. Die zweite Marke auf der Rose zeigt dorthin.", "ok");
    }, "go");
    var btnClear = ctx.button("Löschen", function () {
      bearing = null; ctx.save("bearing", null);
      btnClear.disabled = true; deltaEl.textContent = "";
      ctx.clearStatus();
    }, "quiet");
    btnClear.disabled = (bearing == null);

    root.appendChild(cv.node);
    var card = ctx.el("div", "g-card");
    card.appendChild(head);
    card.appendChild(deltaEl);
    card.appendChild(ctx.row(btnMark, btnClear));
    card.appendChild(ctx.el("div", "g-note",
      "Flach halten. Metall, Magnete und Lautsprecher ziehen die Nadel — im Auto oder am Schreibtisch ist der Wert oft mehrere Grad daneben."));
    root.appendChild(card);

    function smoothed() {
      var d = Math.atan2(sy, sx) * R2D;
      return (d % 360 + 360) % 360;
    }

    function onEvt(e) {
      var h = null;
      if (typeof e.webkitCompassHeading === "number" && !isNaN(e.webkitCompassHeading)) {
        h = e.webkitCompassHeading;            // iOS: bereits gegen Norden
        absolute = true;
      } else if (e.alpha != null) {
        h = 360 - e.alpha;                      // Android/Standard
        if (e.absolute === true || e.type === "deviceorientationabsolute") absolute = true;
      }
      if (h == null || isNaN(h)) return;
      seen.seen = true;
      heading = (h % 360 + 360) % 360;
    }

    ctx.motion().then(function (ok) {
      if (!ok) {
        ctx.status("Keine Freigabe für die Lagesensoren. Auf dem iPhone fragt Safari einmalig nach — die Seite neu laden und erlauben.", "error");
        return;
      }
      if ("ondeviceorientationabsolute" in window) ctx.on(window, "deviceorientationabsolute", onEvt);
      ctx.on(window, "deviceorientation", onEvt);
      watchdog(ctx, seen, "Die Lagesensoren melden nichts. Am Rechner ist das normal — dieses Instrument braucht ein Telefon mit Magnetometer.");
      setTimeout(function () {
        if (seen.seen && !absolute) {
          ctx.status("Dieses Gerät liefert nur eine relative Drehung, keinen echten Norden. Die Rose zeigt also, wie weit du dich gedreht hast — nicht, wo Norden liegt.", "warn");
        }
      }, 2600);
    });

    var lastNum = 0;
    ctx.raf(function (dt, t) {
      var k = clamp(dt / 160, 0.02, 0.3);
      var rad = heading * D2R;
      sx = lerp(sx, Math.cos(rad), k);
      sy = lerp(sy, Math.sin(rad), k);
      draw();
      if (t - lastNum > 100) {
        lastNum = t;
        if (seen.seen) {
          var d = smoothed();
          degEl.textContent = Math.round(d) + "°";
          dirEl.textContent = absolute ? dirName(d) : "relativ";
          if (bearing != null) {
            var diff = ((bearing - d + 540) % 360) - 180;
            deltaEl.textContent = "Gemerkte Peilung " + Math.round(bearing) + "° — " +
              (Math.abs(diff) < 2 ? "du stehst darauf."
                : Math.abs(Math.round(diff)) + "° nach " + (diff > 0 ? "rechts" : "links") + " drehen.");
          }
        }
      }
    });

    function draw() {
      var g = cv.g, w = cv.w, h = cv.h;
      var cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - 10;
      g.clearRect(0, 0, w, h);
      var cLine = ctx.color("line"), cDim = ctx.color("inkDim"), cInk = ctx.color("ink");
      var cAcc = ctx.color("accent"), cCool = ctx.color("cool"), cPanel = ctx.color("panel");

      g.fillStyle = cPanel;
      g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.fill();
      g.strokeStyle = cLine; g.lineWidth = 1.2; g.stroke();

      var rot = -smoothed() * D2R;
      g.save();
      g.translate(cx, cy);
      g.rotate(rot);

      for (var a = 0; a < 360; a += 5) {
        var maj = (a % 30 === 0);
        var r1 = R - (maj ? 13 : 6), r2 = R - 2;
        g.strokeStyle = maj ? cDim : cLine;
        g.lineWidth = maj ? 1.3 : 0.9;
        var rad = (a - 90) * D2R;
        g.beginPath();
        g.moveTo(Math.cos(rad) * r1, Math.sin(rad) * r1);
        g.lineTo(Math.cos(rad) * r2, Math.sin(rad) * r2);
        g.stroke();
      }
      g.font = "500 10px " + "ui-monospace, monospace";
      g.fillStyle = cDim;
      g.textAlign = "center"; g.textBaseline = "middle";
      for (var b = 0; b < 360; b += 30) {
        if (b % 90 === 0) continue;
        var rb = (b - 90) * D2R, rr = R - 24;
        g.fillText(String(b), Math.cos(rb) * rr, Math.sin(rb) * rr);
      }
      var CARD = [[0, "N"], [90, "O"], [180, "S"], [270, "W"]];
      for (var i = 0; i < 4; i++) {
        var ang = (CARD[i][0] - 90) * D2R, rr2 = R - 26;
        g.fillStyle = (CARD[i][1] === "N") ? cAcc : cInk;
        g.font = "700 16px " + "system-ui, sans-serif";
        g.fillText(CARD[i][1], Math.cos(ang) * rr2, Math.sin(ang) * rr2);
      }
      if (bearing != null) {
        var rb2 = (bearing - 90) * D2R;
        g.strokeStyle = cCool; g.lineWidth = 2.5;
        g.beginPath();
        g.moveTo(Math.cos(rb2) * (R - 30), Math.sin(rb2) * (R - 30));
        g.lineTo(Math.cos(rb2) * (R - 4), Math.sin(rb2) * (R - 4));
        g.stroke();
      }
      g.restore();

      // feste Nadel oben
      g.fillStyle = cAcc;
      g.beginPath();
      g.moveTo(cx, cy - R + 2);
      g.lineTo(cx - 7, cy - R + 17);
      g.lineTo(cx + 7, cy - R + 17);
      g.closePath(); g.fill();
      g.fillStyle = cLine;
      g.beginPath(); g.arc(cx, cy, 3, 0, Math.PI * 2); g.fill();
    }
  }

  /* ================================================================== */
  /* 3 — Erschütterungsmesser                                            */
  /* ================================================================== */

  function mountShake(root, ctx) {
    styleOnce(root, "shake", "#gad-shake .sk-stats{display:flex;gap:24px;flex-wrap:wrap}" +
      "#gad-shake .sk-s{display:flex;flex-direction:column;gap:1px}");

    var cv = ctx.canvas(2.0);
    var read = ctx.readout("m/s²");
    var seen = { seen: false };

    var grav = { x: 0, y: 0, z: 0 }, haveGrav = false;
    var cur = 0, peak = 0, smoothVal = 0;
    var W = 420, buf = new Float32Array(W), bi = 0, filled = 0;

    var thresh = ctx.store("thresh", 2);
    var hits = 0, armed = true;

    var stats = ctx.el("div", "sk-stats");
    function statBox(label) {
      var b = ctx.el("div", "sk-s");
      b.appendChild(ctx.el("div", "g-label", label));
      var n = ctx.el("div", "g-big", "–");
      b.appendChild(n);
      stats.appendChild(b);
      return n;
    }
    var nPeak = statBox("Spitze");
    var nHits = statBox("Überschritten");

    var sl = ctx.slider({ min: 0.2, max: 12, step: 0.1, value: thresh, unit: "m/s²" });
    sl.onInput(function (v) { thresh = v; ctx.save("thresh", v); });

    var btnReset = ctx.button("Zurücksetzen", function () {
      peak = 0; hits = 0;
      nPeak.textContent = "0,0"; nHits.textContent = "0";
    }, "quiet");

    root.appendChild(read.node);
    root.appendChild(cv.node);
    var card = ctx.el("div", "g-card");
    card.appendChild(stats);
    card.appendChild(ctx.field("Schwelle für den Zähler", sl.node));
    card.appendChild(ctx.row(btnReset));
    card.appendChild(ctx.el("div", "g-note",
      "Misst, was zusätzlich zur Schwerkraft am Gerät zerrt. Aufs Fensterbrett legen und zählen, wie oft der Zug vorbeifährt, oder auf die Waschmaschine im Schleudergang."));
    root.appendChild(card);

    ctx.motion().then(function (ok) {
      if (!ok) {
        ctx.status("Keine Freigabe für die Bewegungssensoren. Auf dem iPhone fragt Safari einmalig nach — die Seite neu laden und erlauben.", "error");
        return;
      }
      ctx.on(window, "devicemotion", function (e) {
        var a = e.accelerationIncludingGravity;
        if (!a || a.x == null) {
          a = e.acceleration;
          if (!a || a.x == null) return;
          seen.seen = true;
          cur = Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
          return;
        }
        seen.seen = true;
        if (!haveGrav) { grav.x = a.x; grav.y = a.y; grav.z = a.z; haveGrav = true; }
        // Hochpass: die Schwerkraft ist der langsam wandernde Anteil
        grav.x = lerp(grav.x, a.x, 0.04);
        grav.y = lerp(grav.y, a.y, 0.04);
        grav.z = lerp(grav.z, a.z, 0.04);
        var dx = a.x - grav.x, dy = a.y - grav.y, dz = a.z - grav.z;
        cur = Math.sqrt(dx * dx + dy * dy + dz * dz);
      });
      watchdog(ctx, seen, "Die Bewegungssensoren melden nichts. Am Rechner ist das normal — dieses Instrument braucht ein Telefon.");
    });

    function words(v) {
      if (v < 0.25) return "ruhig";
      if (v < 1.2) return "leichte Vibration";
      if (v < 4) return "spürbar";
      if (v < 10) return "kräftig";
      return "heftig";
    }

    var lastNum = 0, acc = 0, accN = 0;
    ctx.raf(function (dt, t) {
      smoothVal = lerp(smoothVal, cur, clamp(dt / 90, 0.05, 0.5));
      acc += cur; accN++;

      if (cur > peak) peak = cur;
      if (cur >= thresh && armed) { hits++; armed = false; }
      if (cur < thresh * 0.6) armed = true;

      buf[bi] = smoothVal;
      bi = (bi + 1) % W;
      if (filled < W) filled++;

      draw();

      if (t - lastNum > 100) {
        lastNum = t;
        var mean = accN ? acc / accN : 0; acc = 0; accN = 0;
        read.set(seen.seen ? ctx.fmt(mean, 2) : "–", seen.seen ? words(mean) : "wartet auf den Sensor");
        nPeak.textContent = ctx.fmt(peak, 2);
        nHits.textContent = String(hits);
      }
    });

    function draw() {
      var g = cv.g, w = cv.w, h = cv.h;
      g.clearRect(0, 0, w, h);
      var cLine = ctx.color("line"), cSoft = ctx.color("lineSoft"), cDim = ctx.color("inkDim");
      var cAcc = ctx.color("accent"), cWarn = ctx.color("warn");

      var top = 6, bot = h - 16, hh = bot - top;
      var scale = Math.max(3, Math.min(20, peak * 1.25));

      // Raster mit beschrifteten Werten
      g.font = "400 9px ui-monospace, monospace";
      g.textAlign = "left"; g.textBaseline = "middle";
      var steps = 4;
      for (var i = 0; i <= steps; i++) {
        var v = scale * i / steps;
        var y = bot - (v / scale) * hh;
        g.strokeStyle = (i === 0) ? cLine : cSoft;
        g.lineWidth = 1;
        g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke();
        if (i > 0) { g.fillStyle = cDim; g.fillText(ctx.fmt(v, 1), 3, y - 6); }
      }

      // Schwelle
      if (thresh <= scale) {
        var ty = bot - (thresh / scale) * hh;
        g.strokeStyle = cWarn; g.lineWidth = 1; g.setLineDash([4, 3]);
        g.beginPath(); g.moveTo(0, ty); g.lineTo(w, ty); g.stroke();
        g.setLineDash([]);
      }

      // Kurve, läuft von rechts nach links weg
      if (filled > 1) {
        g.strokeStyle = cAcc; g.lineWidth = 1.6;
        g.beginPath();
        var n = Math.min(filled, W);
        for (var j = 0; j < n; j++) {
          var idx = (bi - n + j + W * 2) % W;
          var x = w - (n - j) * (w / n);
          var yy = bot - clamp(buf[idx] / scale, 0, 1) * hh;
          if (j === 0) g.moveTo(x, yy); else g.lineTo(x, yy);
        }
        g.stroke();
      }

      g.fillStyle = cDim;
      g.textAlign = "right"; g.textBaseline = "bottom";
      g.fillText("jetzt", w - 3, h - 3);
      g.textAlign = "left";
      g.fillText("älter", 3, h - 3);
    }
  }

  /* ================================================================== */

  Gadgets.register({
    id: "level", name: "Wasserwaage", group: "Lage", needs: "motion",
    blurb: "Dosenlibelle und Gefälle in Prozent, mit eigenem Nullpunkt.",
    mount: mountLevel
  });

  Gadgets.register({
    id: "compass", name: "Kompass", group: "Lage", needs: "motion",
    blurb: "Windrose mit Gradskala. Peilung merken und zurückfinden.",
    mount: mountCompass
  });

  Gadgets.register({
    id: "shake", name: "Erschütterung", group: "Lage", needs: "motion",
    blurb: "Seismograf mit Spitzenwert und Zähler für eine Schwelle.",
    mount: mountShake
  });
})();
