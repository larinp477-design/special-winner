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


def render_scenes(module, names, out_dir):
    """SVG scenes from an episode module to PNG via Chromium. Cached on disk."""
    mod = importlib.import_module(module)
    os.makedirs(out_dir, exist_ok=True)
    args = []
    for n in names:
        svgp, pngp = os.path.join(out_dir, n + ".svg"), os.path.join(out_dir, n + ".png")
        svg = mod.SCENES[n]()
        old = open(svgp).read() if os.path.exists(svgp) else None
        if old != svg or not os.path.exists(pngp):
            open(svgp, "w").write(svg)
            args += [svgp, pngp]
    if args:
        subprocess.run(["node", os.path.join(os.path.dirname(__file__), "svg2png.js")] + args, check=True)
    return {n: os.path.join(out_dir, n + ".png") for n in names}


class SceneLayer:
    """One scene: panel with camera motion, static blurred background."""

    def __init__(self, png, motion, dur, fx):
        src = Image.open(png).convert("RGB")
        self.src = src.resize((1620, 1215), Image.LANCZOS)
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

    def panel(self, t):
        p = ease_in_out(t / self.dur)
        bw, bh = self.src.size
        z0, z1 = {"zoom_in": (1.0, 1.12), "zoom_out": (1.12, 1.0), "push": (1.0, 1.2),
                  "pan_left": (1.1, 1.1), "pan_right": (1.1, 1.1), "still": (1.03, 1.05)}.get(self.motion, (1.0, 1.1))
        z = z0 + (z1 - z0) * p
        cw, ch = bw / z, bh / z
        cx, cy = bw / 2, bh / 2
        if self.motion == "pan_left":
            cx = bw / 2 + (bw - cw) / 2 * (1 - 2 * p)
        elif self.motion == "pan_right":
            cx = bw / 2 - (bw - cw) / 2 * (1 - 2 * p)
        for at in self.fx.get("shake_at", []):
            if 0 <= t - at < 0.45:
                k = 1 - (t - at) / 0.45
                cx += math.sin(t * 90) * 22 * k
                cy += math.cos(t * 77) * 16 * k
        if self.fx.get("shake"):
            cx += math.sin(t * 31) * 6 + math.sin(t * 17) * 4
            cy += math.cos(t * 23) * 5
        cw, ch = min(cw, bw / 1.04), min(ch, bh / 1.04)
        cx = min(max(cx, cw / 2), bw - cw / 2)
        cy = min(max(cy, ch / 2), bh - ch / 2)
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        img = self.src.resize((W, PANEL_H), Image.BILINEAR, box=box)
        if self.fx.get("rain"):
            img = self.rain(img, t)
        if self.fx.get("redpulse"):
            a = 0.12 + 0.12 * (0.5 + 0.5 * math.sin(t * 5))
            img = Image.blend(img, Image.new("RGB", img.size, (170, 20, 30)), a)
        if self.fx.get("flash") and t < 0.25:
            img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), (1 - t / 0.25) * 0.85)
        return img

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
    say = lambda text: tts.synth(text, v["backend"], v["voice"], v.get("speed", 1.0))
    names = [s["svg"] for s in script["scenes"]]
    pngs = render_scenes(script["module"], sorted(set(names)), os.path.join(base, "..", "out", "scenes", script["id"]))
    hud = script["hud"]
    tl = Timeline()
    t = 0.0
    all_words = []
    layers = []
    for sc in script["scenes"]:
        # one TTS call per sentence, with a short dramatic pause in between
        lead = sc.get("lead", 0.12 if layers else 0.0)
        gap = sc.get("gap", script.get("gap", 0.3))
        tail = sc.get("tail", 0.3)
        at = t + lead
        for sent in split_sentences(sc["text"]):
            audio = say(sent)
            d = len(audio) / SR
            all_words += [(w, at + s, at + e) for w, s, e in tts.word_times(sent, d)]
            tl.add_audio(at, audio)
            at += d + gap
        dur = at - gap - t + tail
        for name, at in sc.get("sfx", []):
            tl.add_sfx(t + at, name, sc.get("sfx_gain", 1.0))
        layer = SceneLayer(pngs[sc["svg"]], sc.get("motion", "zoom_in"), dur, sc.get("fx", {}))
        layers.append((t, dur, layer, sc.get("clock", ""), sc.get("choice")))
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
    tl.add_sfx(t, "sting", 0.8)
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
    tl.add_audio(0, sfxlib.drone(end), script.get("drone_gain", 1.0))
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
