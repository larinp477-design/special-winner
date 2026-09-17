# Tages-Cockpit

Ein persönliches Tages-Dashboard fürs Handy. Eine einzelne Seite, die morgens
aufgemacht wird und den Tag trägt: echte Termine, eine Checkliste, eine
Gewohnheits-Serie, der auf das Wesentliche gefilterte Posteingang, ein von
Claude geschriebener Tagesplan und eine Schnellnotiz, die als Markdown im
Obsidian-Vault landet.

Veröffentlicht als Claude Artifact (privat, nur für den Besitzer sichtbar):
https://claude.ai/code/artifact/36ce9abf-0991-4ba3-8ca8-ebbb13e37cca

## Aufbau

`cockpit.html` ist die komplette Seite — Markup, CSS und JavaScript in einer
Datei, ohne Build-Schritt und ohne externe Abhängigkeiten außer den Schriften
von Google Fonts.

Die Datei beginnt bewusst mit `<title>` statt mit `<!doctype html>`: beim
Veröffentlichen wird sie in ein `<!doctype html>…<head>…</head><body>`-Gerüst
eingesetzt. Wer sie lokal im Browser öffnen will, muss sie also selbst in ein
solches Gerüst einbetten.

## Laufzeit-Fähigkeiten

Die veröffentlichte Seite bekommt vom Viewer fünf Fähigkeiten. Jede wird über
`await claude.use(name)` geholt und jede kann `null` liefern — die Seite
rendert vollständig ohne sie und schaltet einzelne Bereiche frei, sobald sie
verfügbar sind.

| Fähigkeit   | Wofür                                                                |
|-------------|----------------------------------------------------------------------|
| `db`        | Aufgaben, Gewohnheiten und Notizen, geräteübergreifend                |
| `mcp`       | `Google Calendar › list_events`, `Gmail › search_threads`             |
| `sample`    | Das Tagesbriefing, gestreamt                                          |
| `downloads` | Markdown-Export für den Obsidian-Vault                                |

Ohne `db` fällt die Seite auf `localStorage` zurück und sagt das in der Fußzeile
auch. Fehler der Connectors werden nach `code` unterschieden, nicht in ein
Sammelbanner geworfen: eine abgelaufene Google-Verbindung bekommt einen anderen
Hinweis als ein kurz nicht erreichbarer Server, und nur echte
Zugriffsverweigerungen verwerfen bereits geladene Daten.

## Datenformate, die beim Bauen beobachtet wurden

Beides einmal live abgefragt, nicht geraten:

- `list_events` liefert **kein** `events`-Feld, wenn nichts im Zeitraum liegt —
  nicht etwa ein leeres Array.
- Ganztägige Termine kommen als `start.date`, getaktete als `start.dateTime`.
  `start.date` kann ein vollständiger Zeitstempel sein (`2026-10-03T00:00:00Z`),
  weshalb der Tagesabgleich über den Datums-Präfix läuft und nicht über
  `new Date(...)`.
- `search_threads` liefert `{}` bei null Treffern; `resultCountEstimate` kommt
  als String.

## Gestaltung

Nachtdeck und Taghülle: petrolstichige Neutraltöne statt Schwarz, Bernstein als
Instrumentenlicht, Eis-Türkis für Hinweise. Saira Condensed für die
Instrumentenbeschriftung, Archivo für Fließtext, IBM Plex Mono für alles
Zählbare. Beide Themes sind vollständig über Tokens definiert, auch für den
Normalfall, in dem der Viewer gar kein `data-theme` setzt.

Das Band unter dem Datum ist eine Zeitachse von 06:00 bis 24:00 mit den Terminen
des Tages als Balken und einer Nadel, die auf der aktuellen Uhrzeit steht.

---

# Gadget-Koffer

Zwölf Messgeräte auf einer Seite, die die Sensoren des Telefons benutzen —
Wasserwaage, Kompass, Erschütterungsmesser, Lärm-Messer, Stimmgerät,
Spektrum-Wasserfall, Tongenerator, Hörtest, Metronom, GPS-Tacho, Lineal und
Puls-Messer.

Veröffentlicht als Claude Artifact (privat):
https://claude.ai/artifact/3boNxFyYkaRuPvasx13zMn

## Aufbau

Anders als das Cockpit ist das hier bewusst mehrteilig:

```
gadgets/
├── CONTRACT.md        Verbindlicher Vertrag für Instrumentenmodule
├── shell.html         Design-System, Navigation, Sensor-Infrastruktur
└── modules/
    ├── lage.js        Wasserwaage · Kompass · Erschütterung
    ├── ohr.js         Lärm-Messer · Stimmgerät · Spektrum
    ├── ton.js         Tongenerator · Hörtest · Metronom
    └── welt.js        GPS-Tacho · Lineal · Puls-Messer
```

Die Module sind klassische Skripte ohne Build-Schritt. Sie melden sich beim
Laden über `Gadgets.register({ id, name, group, blurb, needs, mount })` an;
die Shell baut daraus die Übersicht. Ein Modul, das fehlt oder einen Fehler
hat, nimmt die anderen nicht mit — die Übersicht zeigt dann eben weniger
Geräte.

## Warum die Shell so viel trägt

Jedes Instrument bekommt beim Öffnen ein `ctx`-Objekt. Alles, was darüber
angelegt wird — Zeichenschleifen, Timer, Listener, AudioNodes, Mikrofon,
Kamera, Standortverfolgung — meldet die Shell beim Verlassen des Instruments
wieder ab. Das ist der Grund für den Vertrag: ohne diese eine Regel läuft
nach zehn Minuten Herumtippen das Mikrofon im Hintergrund weiter und der Akku
ist leer.

Sensorfreigaben werden schon beim Antippen der Kachel angefordert, also noch
innerhalb der Nutzergeste. iOS lehnt die Abfrage sonst ab.

## Was am Gerät hängt

Nicht jedes Telefon kann alles, und die Instrumente sagen das selbst, statt
einen Messwert zu erfinden:

- Die Taschenlampe für den Puls-Messer kann Chrome auf Android, Safari nicht.
- Ein echter Kompass braucht ein Magnetometer; sonst zeigt die Rose nur die
  Drehung, nicht Norden — das steht dann auch so da.
- Der Lärm-Messer misst relativ. Ein Browser-Mikrofon ist nicht kalibriert,
  echte dB(A) sind damit nicht zu haben; es gibt einen Abgleichregler.
- Der eingebaute Lautsprecher gibt oberhalb von etwa 15 kHz kaum noch etwas
  her, der Hörtest braucht also Kopfhörer.
- Mikrofon, Kamera und Standort bleiben über eine unsichere Verbindung
  gesperrt.
