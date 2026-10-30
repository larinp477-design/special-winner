# Faceless Video Engine

Baut fertige TikTok-Videos (1080x1920, 30 fps, H.264, Lautheit -14 LUFS) aus einer
Skript-Datei. Stimme, Untertitel, Animation, Soundeffekte und Schnitt laufen per Code
in der Cloud-Umgebung. Musik bewusst nicht: der Trend-Sound kommt beim Hochladen in
der TikTok-App dazu.

Gehört zum Vault-Projekt "KI-Video-Kanal" (Repo `Standard-`,
`02 Projekte/Geld verdienen im Internet/KI-Video-Kanal/`).

## Start

```bash
./setup.sh                                   # Pakete und Stimmen-Modelle
python -m engine.render scripts/wyr_de_01.json out/wyr_de_01.mp4 out/preview
```

Der dritte Parameter ist optional und speichert alle 2 Sekunden ein Standbild zur
Kontrolle. Ein 60-Sekunden-Video rendert in knapp 2 Minuten.

## Hauptformat: Episode

```bash
python -m engine.episode scripts/zombie_e01_ep.json out/zombie_e01.mp4 out/preview
```

Szenen stehen als Python-Funktionen in `episodes/zombie_e01.py` und nutzen die Zeichen-
Bibliothek `engine/illus.py` (Figuren mit Stimmungen und Posen, Zombies, Häuser, Straße,
Zimmer, Tür, Türspion, Treppenhaus, Handy, Radio, Nebel, Licht). Feste Figuren sind dort als
Parameter-Sets definiert, dadurch sehen sie in jeder Folge gleich aus. SVG wird mit Chromium
gerendert (`engine/svg2png.js`). Vorbild: Analyse von zwei erfolgreichen deutschen
Story-Videos, siehe Vault-Notiz "Stilanalyse Vorbild-Videos".

## Templates

| Template | Format | Bilder nötig |
|---|---|---|
| `wyr` | Würdest du lieber: rot/blau geteilt, Karaoke-Text, Emoji, Countdown, Kombi-Abstimmung in den Kommentaren | nein (optional pro Hälfte) |
| `episode` | Hauptformat: flache 2D-Vektorszenen (selbst gezeichnet, kein Bild-Dienst), 4:3-Panel im 9:16-Bild mit unscharfem Hintergrund, HUD mit Story-Uhr, 2-3-Wort-Untertitel mit orangem Wort, Auswahlkarten "Was machst du?" | nein, Szenen sind Code |
| `story` | Was wäre wenn, POV, Entscheidungsserie: Bilder mit Ken-Burns-Bewegung, Wort-für-Wort-Untertitel, Auswahlkarten A/B/C mit Countdown | ja |

Beispiele in `scripts/`. `zombie_e01.json` ist Folge 1 der geplanten Hauptserie und
enthält schon die Bild-Prompts und das Charakterblatt der Figur.

## Bausteine

- `engine/tts.py`: Stimmen. `kokoro` (Englisch, lokal, gut), `piper` (Deutsch, lokal:
  Thorsten high als Erzähler, Thorsten emotional für [whisper], [surprised], [angry] am
  Satzanfang, beide CC0, geladen vom sherpa-onnx-Spiegel auf GitHub), `gemini` (Deutsch, gut, braucht `GEMINI_API_KEY`, noch ungetestet)
- `engine/images.py`: Bilder über die Gemini API mit Referenzbildern für eine feste
  Figur. Braucht `GEMINI_API_KEY`, noch ungetestet
- `engine/produce.py`: erzeugt fehlende Bilder (erst Charakterblatt, dann jede Szene mit
  Blatt als Referenz) und rendert danach das Video
- `engine/music.py`: erzeugter Spannungs-Soundtrack (Flächen, Puls, Zupf-Motiv, Riser,
  Einschläge, Hall), Intensität pro Szene über `music` und `hit` im Skript
- `engine/chars.py`: Figuren Version 2 mit Schattierung, Lichtkante, Iris, Kleidungsdetails
- `engine/sfx.py`: Soundeffekte (Tick, Pop, Whoosh, Boom, Ding) mit numpy erzeugt, also
  lizenzfrei
- `engine/render.py`: Zeitachse, Layout, Animation, Mischung, ffmpeg-Export

## Sichere Zonen

TikTok legt eigene Bedienelemente über das Video. Text bleibt deshalb unter y=200
(Tabs), links von x=930 (Buttons) und über y=1640 (Caption, Musik).

## Netzwerk in der Cloud-Umgebung

Erreichbar: pypi, npm, GitHub-Release-Downloads, `generativelanguage.googleapis.com`.
Gesperrt (Stand 30.10.2026): Hugging Face, edge-tts, fal, Replicate, OpenAI,
ElevenLabs, Cloudflare, Pollinations, Canva-Downloads. Schlüssel gehören in die
Umgebungs-Einstellungen, nie ins Repo.

## Lizenzen

Montserrat: SIL Open Font License (`fonts/OFL-LICENSE.txt`). Kokoro: Apache 2.0.
Piper-Stimme Thorsten: CC0. Emoji: Noto Color Emoji (OFL, Systemschrift).
