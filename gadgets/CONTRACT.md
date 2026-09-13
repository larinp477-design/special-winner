# Gadget-Koffer — Modul-Vertrag

Verbindlich. Die Shell (`shell.html`) wird exakt nach diesem Vertrag gebaut.
Wer davon abweicht, bricht die Integration.

## Was du schreibst

Genau **eine** klassische JS-Datei (kein ES-Modul, kein `export`, kein `import`).
Sie wird per `<script src="…">` nach der Shell geladen. `window.Gadgets` existiert
zu diesem Zeitpunkt bereits.

Kein Build-Schritt. Keine externen Bibliotheken — die CSP der Seite blockiert sie
ohnehin. Kein `innerHTML`, nirgends. Baue DOM mit `ctx.el(...)` und setze Text
über `textContent`.

## Registrierung

```js
(function () {
  "use strict";
  Gadgets.register({
    id: "level",                  // eindeutig, klein, ascii
    name: "Wasserwaage",          // deutsch, kurz
    group: "Lage",                // genau einer von: Lage | Ohr | Ton | Welt
    blurb: "Zeigt, ob etwas gerade ist.",   // eine kurze deutsche Zeile
    needs: "motion",              // "motion" | "mic" | "geo" | "camera" | null
    mount: function (root, ctx) {
      // root ist ein leeres <div>. Alles reinhängen.
      return { unmount: function () { /* nur eigene Sonderfälle */ } };
    }
  });
})();
```

`unmount` ist optional. Alles was du über `ctx` anlegst (Schleifen, Timer,
Listener, Mikrofon, Kamera, Standort) räumt die Shell selbst ab. `unmount`
brauchst du nur für Dinge, die du an `ctx` vorbei angelegt hast.

## ctx — was dir zur Verfügung steht

```
ctx.el(tag, cls?, text?)        -> HTMLElement. Kurzform für createElement.
ctx.frag()                      -> DocumentFragment
ctx.readout(unit?)              -> { node, set(value, sub?) }
                                   Die große Hauptanzeige. value: String|Number.
                                   sub: kleine Zeile darunter, optional.
ctx.status(text, kind?)         -> setzt die Statuszeile unter dem Instrument.
                                   kind: "info" (Standard) | "warn" | "error" | "ok"
ctx.clearStatus()
ctx.canvas(aspect?)             -> { node, g, w, h } DPR-korrekt, aspect Standard 1.6
                                   g ist der 2D-Kontext. w/h sind CSS-Pixel und
                                   werden bei Größenänderung aktualisiert.
                                   Lies w/h IN der Zeichenschleife, nicht davor.
ctx.color(name)                 -> aktueller Token-Wert, z.B. ctx.color("accent")
                                   Gültig: ground panel panel2 sunk line lineSoft
                                           ink ink2 inkDim accent cool go warn
ctx.raf(fn)                     -> Dauerschleife. fn(dtMs, tMs). Läuft nur solange
                                   das Instrument offen und die Seite sichtbar ist.
                                   Gibt stop() zurück.
ctx.every(ms, fn)               -> Intervall, automatisch aufgeräumt. gibt stop().
ctx.on(target, type, fn, opts?) -> Listener, automatisch abgemeldet. gibt off().
ctx.store(key, fallback)        -> Einstellung lesen (pro Gadget getrennt)
ctx.save(key, value)            -> Einstellung schreiben
ctx.fmt(n, digits)              -> Zahl mit fester Nachkommastelle, deutsches Komma
ctx.button(label, onClick, variant?) -> <button>. variant: "go" | "quiet" | undefined
ctx.row(...children)            -> <div class="g-row"> mit den Kindern
ctx.field(labelText, controlEl)  -> beschriftete Zeile für einen Regler
ctx.slider(opts)                -> { node, value(), set(v), onInput(fn) }
                                   opts: {min, max, step, value, unit}
```

### Sensor-Zugriff

```
ctx.motion()   -> Promise<true|false>   Fragt ggf. iOS-Erlaubnis ab. Danach
                  hörst du selbst auf window per ctx.on(window,"deviceorientation",…)
                  bzw. "devicemotion".
ctx.mic()      -> Promise<{ actx, analyser, source, stream }>
                  Geteilt und referenzgezählt. Der Analyser gehört DIR nicht —
                  setze fftSize/smoothingTimeConstant beim Mount, das ist erlaubt.
                  Nicht schließen, die Shell macht das.
ctx.audio()    -> AudioContext für Ausgabe (geteilt, bereits resumed).
                  Eigene Nodes anlegen und in unmount trennen ist deine Sache —
                  ODER du nutzt ctx.owned(node), dann trennt die Shell.
ctx.owned(node)-> registriert einen AudioNode zum automatischen disconnect()
ctx.geo(fn)    -> watchPosition, automatisch beendet. fn(position|null, error|null)
ctx.camera(opts)-> Promise<{ stream, video }>  video ist bereits playing,
                  muted, playsinline. Automatisch gestoppt.
                  opts: { facingMode: "environment"|"user", torch: true|false }
                  torch ist ein Wunsch, kein Versprechen — prüfe
                  stream.getVideoTracks()[0].getCapabilities().torch
```

Jede Sensor-Zusage kann fehlschlagen. `ctx.motion()` liefert `false`,
`ctx.mic()` / `ctx.camera()` werfen, `ctx.geo` ruft mit `(null, error)`.
**Fange das ab und sage auf Deutsch, was los ist und was zu tun wäre** —
über `ctx.status(...)`, nicht über `alert`. Ein Gerät ohne Sensor ist kein
Fehlerfall, sondern ein erklärter Zustand.

## CSS-Klassen der Shell, die du benutzen sollst

```
.g-row        Zeile, flex, gap, umbruchfähig
.g-col        Spalte, flex, gap
.g-card       abgesetzter Block auf dem Panel
.g-note       kleiner, gedämpfter Text
.g-num        monospace, tabular-nums — für alles Zählbare
.g-label      kleine Großbuchstaben-Beschriftung, gesperrt
.g-grid2      zweispaltiges Raster, bricht bei schmal auf eine Spalte um
.g-big        große Zahl (kleiner als der Readout, für Nebenwerte)
```

Eigenes CSS: erlaubt, aber **nur** über ein `<style>`-Element, das du im `mount`
anlegst und an `root` hängst, und **nur** mit Selektoren, die unter
`#gad-<deine id>` liegen. Beispiel: `#gad-level .bubble { … }`.
Farben ausschließlich über die Tokens: `var(--accent)`, `var(--ink)`, … —
nie ein fester Hex-Wert, sonst bricht eines der beiden Themes.

## Design-Tokens (bereits definiert, nur verwenden)

```
--ground --panel --panel2 --sunk --line --line-soft
--ink --ink-2 --ink-dim
--accent      Signalrot-Orange, das eine laute Farbe. Sparsam.
--cool        Blaugrau, für Hinweise und Sekundäres
--go --warn   semantisch, getrennt vom Akzent
--f-disp      Rajdhani     (Überschriften, Beschriftungen)
--f-body      Barlow       (Fließtext, Bedienelemente)
--f-data      Azeret Mono  (Zahlen, Messwerte)
```

## Regeln

1. **Deutsch.** Jede sichtbare Zeile. Per Du. Keine Emoji.
2. **Handy zuerst.** 400 px breit muss alles lesbar und bedienbar sein.
   Nichts darf seitlich über den Rand laufen. Tippziele mindestens 40 px.
3. **Sofort etwas zu sehen.** Beim Öffnen steht das Instrument da — mit
   Nullwerten, Skala, Zifferblatt. Kein leerer Kasten, der auf einen
   Start-Knopf wartet. Ein Knopf ist in Ordnung, wenn er einen Sensor
   freischaltet, aber das Gerät drumherum ist gezeichnet.
4. **Ehrlich messen.** Wo eine Messung physikalisch nur relativ sein kann
   (Schalldruck ohne kalibriertes Mikrofon), schreib das hin, statt eine
   absolute Zahl zu erfinden. Lieber "relativ, nicht kalibriert" als eine
   Lüge in dB.
5. **`prefers-reduced-motion` beachten** bei allem, was animiert.
6. **Kein Blinken** zwischen 3 und 60 Hz über größere Flächen.
7. Zahlen laufen ruhig: Messwerte glätten, nicht mit 60 Hz Ziffern flackern
   lassen. Anzeige höchstens ~10× pro Sekunde aktualisieren, zeichnen darf
   schneller.
8. Rechne in `ctx.raf` nichts Schweres. Kein `console.log` im Endstand.

## Qualität

Das hier sind keine Demos. Ein Zifferblatt hat Skalenstriche und beschriftete
Werte. Ein Pegel hat eine Spitzenwert-Anzeige. Ein Stimmgerät sagt nicht nur
"A", sondern wie viele Cent daneben. Wenn du zwischen "noch ein Regler" und
"das eine gut machen" wählen musst: das eine gut machen.
