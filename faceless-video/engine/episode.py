"""Episode template, modelled on the reference videos (flat 2D story, decision at the end).

Frame: 9:16. Scene panel 4:3 across the full width, behind it the same scene blurred and dark
with a red vignette. HUD on top (story clock left, zone and alarm right). Captions 2 to 3 words,
upper case, spoken word orange. End card: "WAS MACHST DU?" with numbered option cards.

Usage: python -m engine.episode scripts/zombie_e01_ep.json out/zombie_e01.mp4 [preview_dir]
"""
import importlib
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from . import sfx as sfxlib
from . import tts
from .render import FPS, H, SR, W, Timeline, ease_in_out, ease_out_back, emoji_img, font, write_video

ROOT = os.path.join(os.path.dirname(__file__), "..")
FONTS = os.path.join(ROOT, "fonts")
PANEL_Y, PANEL_H = 390, 810
CAP_Y = 1415
ORANGE = (246, 163, 58)
YELLOW = (246, 195, 67)
COLORS = {"blue": (76, 195, 240), "red": (232, 68, 79), "green": (72, 199, 116), "yellow": (246, 195, 67)}


def mono(size):
    return ImageFont.truetype(os.path.join(FONTS, "JetBrainsMono-ExtraBold.ttf"), size)


def inter(size, bold=False):
    return ImageFont.truetype(os.path.join(FONTS, "Inter-Bold.otf" if bold else "Inter-SemiBold.otf"), size)


def spaced(d, xy, s, f, fill, spacing, anchor_right=False):
    """Letter-spaced small caps label."""
    widths = [f.getlength(c) for c in s]
    total = sum(widths) + spacing * (len(s) - 1)
    x, y = xy
    if anchor_right:
        x -= total
    for c, w in zip(s, widths):
        d.text((x, y), c, font=f, fill=fill)
        x += w + spacing
    return total


def _layers_of(result):
    """A scene function returns an SVG string (one opaque layer) or {"layers": [...]}.
    Layer keys: svg, depth (parallax, 1 = background), pivot (x, y) in scene coords,
    breathe (bool), blink (svg of the same layer with closed eyes)."""
    if isinstance(result, str):
        return [{"svg": result, "depth": 1.0}]
    return result["layers"]


def render_scenes(module, names, out_dir):
    """SVG scenes (and their layers) from an episode module to PNG via Chromium. Cached on disk."""
    mod = importlib.import_module(module)
    os.makedirs(out_dir, exist_ok=True)
    args, out = [], {}
    for n in names:
        specs = []
        for i, lay in enumerate(_layers_of(mod.SCENES[n]())):
            spec = dict(lay)
            for key in ("svg", "blink"):
                if key not in lay:
                    continue
                stem = os.path.join(out_dir, f"{n}_{i}{'_b' if key == 'blink' else ''}")
                old = open(stem + ".svg").read() if os.path.exists(stem + ".svg") else None
                if old != lay[key] or not os.path.exists(stem + ".png"):
                    open(stem + ".svg", "w").write(lay[key])
                    args += [stem + ".svg", stem + ".png"]
                spec["png" if key == "svg" else "blink_png"] = stem + ".png"
            specs.append(spec)
        out[n] = specs
    if args:
        subprocess.run(["node", os.path.join(os.path.dirname(__file__), "svg2png.js")] + args, check=True)
    return out


GRAIN = None


def grain_frames():
    global GRAIN
    if GRAIN is None:
        rng = np.random.default_rng(3)
        GRAIN = [rng.normal(0, 7, (PANEL_H, W, 1)).astype(np.float32) for _ in range(6)]
    return GRAIN


class SceneLayer:
    """One scene: layered panel with parallax camera, breathing and blinking characters,
    bloom and film grain. Background: the scene blurred, dark, with a red vignette."""

    SRC = (1620, 1215)

    def __init__(self, specs, motion, dur, fx):
        if isinstance(specs, str):
            specs = [{"png": specs, "depth": 1.0}]
        self.layers = []
        comp = None
        for i, sp in enumerate(specs):
            im = Image.open(sp["png"]).convert("RGBA").resize(self.SRC, Image.LANCZOS)
            blink = Image.open(sp["blink_png"]).convert("RGBA").resize(self.SRC, Image.LANCZOS) if sp.get("blink_png") else None
            k = self.SRC[0] / 1600
            pivot = tuple(v * k for v in sp.get("pivot", (800, 1200)))
            self.layers.append(dict(img=im, blink=blink, depth=sp.get("depth", 1.0), pivot=pivot,
                                    breathe=sp.get("breathe", False), phase=(i * 1.37) % 3.6))
            comp = im if comp is None else Image.alpha_composite(comp, im)
        src = comp.convert("RGB")
        self.motion, self.dur, self.fx = motion, dur, fx
        bg = src.resize((W, int(W * src.height / src.width)), Image.BILINEAR)
        s = H / bg.height
        bg = bg.resize((int(bg.width * s) + 2, H), Image.BILINEAR)
        x0 = (bg.width - W) // 2
        bg = bg.crop((x0, 0, x0 + W, H)).filter(ImageFilter.GaussianBlur(45))
        bg = ImageEnhance.Brightness(bg).enhance(0.32)
        # red vignette, like the reference
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.42) / (H * 0.55)) ** 2)
        k = np.clip((r - 0.35) / 0.75, 0, 1)[..., None]
        arr = np.asarray(bg).astype(np.float32)
        tint = np.array([58, 12, 22], np.float32)
        arr = arr * (1 - k * 0.75) + tint * k * 0.75 * 0.6
        self.bg = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
        # feather mask for the panel edges
        m = np.ones((PANEL_H, W), np.float32)
        f = 40
        ramp = np.linspace(0, 1, f)
        m[:f] *= ramp[:, None]
        m[-f:] *= ramp[::-1][:, None]
        self.mask = Image.fromarray((m * 255).astype(np.uint8))

    def camera(self, t):
        p = ease_in_out(t / self.dur)
        bw, bh = self.SRC
        z0, z1 = {"zoom_in": (1.04, 1.14), "zoom_out": (1.14, 1.04), "push": (1.04, 1.22),
                  "pan_left": (1.12, 1.12), "pan_right": (1.12, 1.12), "still": (1.05, 1.07)}.get(self.motion, (1.04, 1.12))
        z = z0 + (z1 - z0) * p
        cx, cy = bw / 2, bh / 2
        span = bw - bw / z
        if self.motion == "pan_left":
            cx = bw / 2 + span / 2 * (1 - 2 * p)
        elif self.motion == "pan_right":
            cx = bw / 2 - span / 2 * (1 - 2 * p)
        for at in self.fx.get("shake_at", []):
            if 0 <= t - at < 0.45:
                k = 1 - (t - at) / 0.45
                cx += math.sin(t * 90) * 22 * k
                cy += math.cos(t * 77) * 16 * k
        if self.fx.get("shake"):
            cx += math.sin(t * 31) * 6 + math.sin(t * 17) * 4
            cy += math.cos(t * 23) * 5
        # slow handheld drift so nothing is ever completely static
        cx += math.sin(t * 0.7) * 6
        cy += math.sin(t * 0.53 + 1) * 4
        return z, cx, cy

    def panel(self, t):
        z, cx, cy = self.camera(t)
        bw, bh = self.SRC
        out = None
        for L in self.layers:
            k = L["depth"]
            zl = 1 + (z - 1) * k
            cw, ch = bw / zl, bh / zl
            lx = bw / 2 + (cx - bw / 2) * k
            ly = bh / 2 + (cy - bh / 2) * k
            if k == 1.0 and out is None:
                cw, ch = min(cw, bw / 1.02), min(ch, bh / 1.02)
                lx = min(max(lx, cw / 2), bw - cw / 2)
                ly = min(max(ly, ch / 2), bh - ch / 2)
            x0, y0 = lx - cw / 2, ly - ch / 2
            sx, sy = cw / W, ch / PANEL_H
            if L["breathe"]:
                s = 1 + 0.011 * math.sin(2 * math.pi * (t + L["phase"]) / 3.3)
                px, py = L["pivot"]
                # scale content around the pivot: shrink the sampling box around it
                x0 = px + (x0 - px) / s
                y0 = py + (y0 - py) / s
                sx, sy = sx / s, sy / s
            src = L["img"]
            if L["blink"] is not None and ((t + L["phase"]) % 3.6) < 0.13:
                src = L["blink"]
            im = src.transform((W, PANEL_H), Image.AFFINE, (sx, 0, x0, 0, sy, y0), Image.BILINEAR)
            out = im if out is None else Image.alpha_composite(out, im)
        img = out.convert("RGB")
        if self.fx.get("rain"):
            img = self.rain(img, t)
        if self.fx.get("redpulse"):
            a = 0.10 + 0.10 * (0.5 + 0.5 * math.sin(t * 5))
            img = Image.blend(img, Image.new("RGB", img.size, (170, 20, 30)), a)
        if self.fx.get("flash") and t < 0.25:
            img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), (1 - t / 0.25) * 0.85)
        return self.finish(img, t)

    def finish(self, img, t):
        """Bloom on bright areas plus moving film grain."""
        small = img.resize((W // 2, PANEL_H // 2), Image.BILINEAR)
        bright = small.point(lambda v: max(0, v - 165) * 2).filter(ImageFilter.GaussianBlur(14))
        arr = np.asarray(img).astype(np.float32)
        b = np.asarray(bright.resize((W, PANEL_H), Image.BILINEAR)).astype(np.float32)
        arr = 255 - (255 - arr) * (255 - b * 0.55) / 255
        arr += grain_frames()[int(t * 24) % 6]
        return Image.fromarray(arr.clip(0, 255).astype(np.uint8))

    def rain(self, img, t):
        d = ImageDraw.Draw(img, "RGBA")
        rng = np.random.default_rng(9)
        xs = rng.uniform(0, W, 110)
        ys = rng.uniform(0, PANEL_H, 110)
        sp = rng.uniform(900, 1400, 110)
        for x, y, v in zip(xs, ys, sp):
            yy = (y + t * v) % PANEL_H
            xx = (x - t * v * 0.2) % W
            d.line((xx, yy, xx - 6, yy + 28), fill=(210, 225, 255, 70), width=2)
        return img


def split_sentences(text):
    import re
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def caption_chunks(words, max_words=3, max_chars=18):
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(x[0] for x in cur + [w])) > max_chars):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w[0][-1] in ".!?:":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def draw_caption(img, chunks, t):
    f = font(76, 800)
    for c in chunks:
        if c[0][1] - 0.02 <= t < c[-1][2] + 0.08:
            words = [w.upper() for w, _, _ in c]
            space = f.getlength(" ")
            widths = [f.getlength(w) for w in words]
            total = sum(widths) + space * (len(words) - 1)
            ff = f
            if total > 960:
                ff = font(int(76 * 960 / total), 800)
                widths = [ff.getlength(w) for w in words]
                space = ff.getlength(" ")
                total = sum(widths) + space * (len(words) - 1)
            layer = Image.new("RGBA", (W, 200))
            d = ImageDraw.Draw(layer)
            x = (W - total) / 2
            for (w, s, e), word, ww in zip(c, words, widths):
                on = s <= t < e or (t >= e and (w, s, e) == c[-1])
                d.text((x, 60), word, font=ff, fill=ORANGE if on else (255, 255, 255),
                       stroke_width=3, stroke_fill=(20, 14, 18))
                x += ww + space
            sh = layer.split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 0.7)
            shadow = Image.new("RGBA", (W, 200), (0, 0, 0, 255))
            shadow.putalpha(sh)
            pop = min(1.0, (t - c[0][1] + 0.02) / 0.12)
            sc = 1.06 - 0.06 * pop
            if sc > 1.001:
                layer = layer.resize((int(W * sc), int(200 * sc)), Image.BILINEAR)
                ox, oy = int((W - layer.width) / 2), int(CAP_Y - 100 - (layer.height - 200) / 2)
            else:
                ox, oy = 0, CAP_Y - 100
            img.alpha_composite(shadow, (0, CAP_Y - 92))
            img.alpha_composite(layer, (ox, oy))
            return


def draw_hud(img, hud, clock, t):
    d = ImageDraw.Draw(img)
    d.text((70, 196), clock, font=mono(74), fill=(240, 240, 244))
    spaced(d, (72, 292), hud.get("left", ""), inter(22), (140, 144, 154), 4)
    R = 1010
    spaced(d, (R, 206), hud.get("right_top", ""), inter(20), (140, 144, 154), 4, anchor_right=True)
    spaced(d, (R, 238), hud.get("right_mid", ""), inter(26, True), (236, 236, 240), 2, anchor_right=True)
    if hud.get("alarm"):
        on = (t % 1.0) < 0.62
        col = (232, 68, 79) if on else (120, 40, 46)
        f = inter(22, True)
        wdt = spaced(d, (R, 278), hud["alarm"], f, col, 3, anchor_right=True)
        d.ellipse((R - wdt - 26, 286, R - wdt - 12, 300), fill=col)


def draw_choice(img, choice, t, say_times):
    """End card on top of the panel. say_times: (start, mid, end) of the question audio."""
    d = ImageDraw.Draw(img, "RGBA")
    k = min(1, t / 0.3)
    d.rectangle((0, PANEL_Y, W, PANEL_Y + PANEL_H), fill=(10, 10, 16, int(135 * k)))
    fh = font(80, 900)
    head = choice.get("heading", "WAS MACHST DU?")
    hw = d.textlength(head, font=fh)
    a = int(255 * min(1, t / 0.25))
    d.text(((W - hw) / 2, 470), head, font=fh, fill=(255, 255, 255, a), stroke_width=3, stroke_fill=(10, 10, 16, a))
    s0, mid, e0 = say_times
    for i, opt in enumerate(choice["options"]):
        p = ease_out_back((t - 0.25 - i * 0.18) / 0.35)
        if p <= 0:
            continue
        col = COLORS[opt.get("color", "blue" if i == 0 else "red")]
        y0 = 620 + i * 250 + (1 - min(p, 1)) * 140
        x0, x1 = 70, 1010
        hi = (s0 <= t < mid and i == 0) or (mid <= t < e0 and i == 1) or t >= e0 or t < s0
        alpha = 255 if hi else 110
        layer = Image.new("RGBA", (W, 230))
        ld = ImageDraw.Draw(layer)
        ld.rounded_rectangle((x0, 10, x1, 220), 30, fill=(16, 20, 30, 235), outline=col + (255,), width=6)
        ld.ellipse((x0 + 40, 65, x0 + 140, 165), fill=col + (255,))
        num = str(i + 1)
        fn = font(58, 900)
        bb = ld.textbbox((0, 0), num, font=fn)
        ld.text((x0 + 90 - (bb[0] + bb[2]) / 2, 115 - (bb[1] + bb[3]) / 2), num, font=fn, fill=(255, 255, 255))
        ld.text((x0 + 170, 62), opt["title"].upper(), font=font(54, 900), fill=(255, 255, 255))
        ld.text((x0 + 172, 130), opt["sub"], font=font(32, 800), fill=col + (255,))
        if opt.get("icon"):
            em = emoji_img(opt["icon"], 88)
            layer.alpha_composite(em, (x1 - 130, 70))
        if alpha < 255:
            layer.putalpha(layer.split()[3].point(lambda v: v * alpha // 255))
        img.alpha_composite(layer, (0, int(y0) - 10))
    if t > 0.25 + len(choice["options"]) * 0.18 + 0.3:
        cta = choice.get("cta", "SCHREIB 1 ODER 2")
        fc = font(44, 800)
        pulse = 0.75 + 0.25 * math.sin(t * 5)
        col = tuple(int(c * pulse + 255 * (1 - pulse) * 0.0) for c in YELLOW)
        cw = d.textlength(cta, font=fc)
        x = (W - cw - 70) / 2
        d.text((x, 1128), cta, font=fc, fill=col + (255,))
        em = emoji_img("👇", 54)
        img.alpha_composite(em, (int(x + cw + 14), 1120))


def build(script, base):
    v = script["voice"]
    styles = script.get("voice_styles", {})

    def say(text):
        """A sentence may start with [style], e.g. [whisper]. Styles map to other voices."""
        style = None
        if text.startswith("["):
            style, text = text[1:].split("]", 1)
            text = text.strip()
        vv = dict(v, **styles.get(style, {})) if style else v
        return tts.synth(text, vv["backend"], vv["voice"], vv.get("speed", 1.0))

    def clean(text):
        return text.split("]", 1)[1].strip() if text.startswith("[") else text
    names = [s["svg"] for s in script["scenes"]]
    pngs = render_scenes(script["module"], sorted(set(names)), os.path.join(base, "..", "out", "scenes", script["id"]))
    hud = script["hud"]
    tl = Timeline()
    t = 0.0
    all_words = []
    layers = []
    curve, hits = [], []
    for sc in script["scenes"]:
        # one TTS call per sentence, with a short dramatic pause in between
        lead = sc.get("lead", 0.12 if layers else 0.0)
        gap = sc.get("gap", script.get("gap", 0.3))
        tail = sc.get("tail", 0.3)
        at = t + lead
        for sent in split_sentences(sc["text"]):
            audio = say(sent)
            d = len(audio) / SR
            all_words += [(w, at + s, at + e) for w, s, e in tts.word_times(clean(sent), d)]
            tl.add_audio(at, audio)
            at += d + gap
        dur = at - gap - t + tail
        for name, at in sc.get("sfx", []):
            tl.add_sfx(t + at, name, sc.get("sfx_gain", 1.0))
        layer = SceneLayer(pngs[sc["svg"]], sc.get("motion", "zoom_in"), dur, sc.get("fx", {}))
        layers.append((t, dur, layer, sc.get("clock", ""), sc.get("choice")))
        curve.append((t + 0.01, sc.get("music", 0.4)))
        curve.append((t + dur - 0.01, sc.get("music_end", sc.get("music", 0.4))))
        if sc.get("hit"):
            hits.append(t + sc.get("hit_at", 0.0))
        if sc.get("ambience") == "rain":
            tl.add_audio(t, sfxlib.rain_amb(dur), 0.8, "sfx")
        t += dur
    # end card with the question
    ch = script["choice"]
    q = say(ch["say"])
    dq = len(q) / SR
    qwords = tts.word_times(ch["say"], dq)
    split_word = ch.get("split_word", len(qwords) // 2)
    lead = 0.35
    q_start = t + lead
    mid = q_start + qwords[split_word][1]
    q_end = q_start + dq
    all_words += [(w, q_start + s, q_start + e) for w, s, e in qwords]
    tl.add_audio(q_start, q)
    tl.add_sfx(t, "sting", 0.5)
    outro = script.get("outro_say")
    end = q_end + 0.4
    if outro:
        o = say(outro)
        do = len(o) / SR
        tl.add_audio(end, o)
        all_words += [(w, end + s, end + e) for w, s, e in tts.word_times(outro, do)]
        end += do
    end = max(end + 2.5, script.get("min_duration", 61.5))
    last = script["scenes"][-1]
    end_layer = SceneLayer(pngs[ch.get("svg", last["svg"])], "still", end - t, {})
    layers.append((t, end - t, end_layer, ch.get("clock", last.get("clock", "")), ("CHOICE", t)))
    curve.append((t + 0.01, 0.5))
    curve.append((end, 0.45))
    hits.append(t)
    from . import music
    tl.add_audio(0, music.score(end, curve, hits), script.get("music_gain", 0.55), "music")
    tl.add_audio(0, sfxlib.drone(end), script.get("drone_gain", 0.6), "music")
    chunks = caption_chunks(all_words)
    choice_times = (q_start, mid, q_end)

    for start, dur, layer, clock, choice in layers:
        def fn(tt, _below, start=start, layer=layer, clock=clock, choice=choice):
            img = layer.bg.copy().convert("RGBA")
            panel = layer.panel(tt)
            img.paste(panel, (0, PANEL_Y), layer.mask)
            # punch-in on every cut
            if tt < 0.18:
                k = 1 + 0.035 * (1 - tt / 0.18)
                img = img.resize((int(W * k), int(H * k)), Image.BILINEAR).crop(
                    (int((W * k - W) / 2), int((H * k - H) / 2), int((W * k - W) / 2) + W, int((H * k - H) / 2) + H))
            draw_hud(img, hud, clock, start + tt)
            if isinstance(choice, tuple):
                draw_choice(img, ch, start + tt - choice[1], tuple(x - choice[1] for x in choice_times))
            draw_caption(img, chunks, start + tt)
            if script.get("ai_label", False):
                ImageDraw.Draw(img).text((26, 1872), "KI-generiert", font=inter(22), fill=(150, 150, 158))
            return img.convert("RGB")
        tl.add_clip(start, dur, fn)
    return tl


def main():
    script_path, out = sys.argv[1], sys.argv[2]
    preview = sys.argv[3] if len(sys.argv) > 3 else None
    with open(script_path) as fh:
        script = json.load(fh)
    base = os.path.dirname(os.path.abspath(script_path))
    sys.path.insert(0, os.path.abspath(os.path.join(base, "..")))
    tl = build(script, base)
    dur = write_video(tl, out, preview)
    print(f"{out}: {dur:.1f}s")


if __name__ == "__main__":
    main()
