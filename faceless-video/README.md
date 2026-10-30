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

## Templates

| Template | Format | Bilder nötig |
|---|---|---|
| `wyr` | Würdest du lieber: rot/blau geteilt, Karaoke-Text, Emoji, Countdown, Kombi-Abstimmung in den Kommentaren | nein (optional pro Hälfte) |
| `story` | Was wäre wenn, POV, Entscheidungsserie: Bilder mit Ken-Burns-Bewegung, Wort-für-Wort-Untertitel, Auswahlkarten A/B/C mit Countdown | ja |

Beispiele in `scripts/`. `zombie_e01.json` ist Folge 1 der geplanten Hauptserie und
enthält schon die Bild-Prompts und das Charakterblatt der Figur.

## Bausteine

- `engine/tts.py`: Stimmen. `kokoro` (Englisch, lokal, gut), `piper` (Deutsch, lokal,
  mittelmäßig), `gemini` (Deutsch, gut, braucht `GEMINI_API_KEY`, noch ungetestet)
- `engine/images.py`: Bilder über die Gemini API mit Referenzbildern für eine feste
  Figur. Braucht `GEMINI_API_KEY`, noch ungetestet
- `engine/produce.py`: erzeugt fehlende Bilder (erst Charakterblatt, dann jede Szene mit
  Blatt als Referenz) und rendert danach das Video
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
