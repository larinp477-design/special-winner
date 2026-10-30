"""Faceless video engine: script JSON in, finished 1080x1920 TikTok MP4 out.

Templates
  wyr    "Würdest du lieber": split screen, two options, karaoke text, countdown, comment vote
  story  "What if" / POV: image scenes with Ken Burns motion, word-by-word captions, choice cards

Usage: python -m engine.render script.json out.mp4
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import sfx as sfxlib
from . import tts

W, H, FPS = 1080, 1920, 30
SR = tts.SR
ROOT = os.path.join(os.path.dirname(__file__), "..")
FONT_DIR = os.path.join(ROOT, "fonts")
# TikTok overlays: tabs on top, buttons on the right, caption and music at the bottom
SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT = 200, 1640, 930


def font(size, weight=900):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"montserrat-{weight}.woff2"), size)


# ---------------------------------------------------------------- easing

def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    x = min(max(x, 0.0), 1.0)
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


# ---------------------------------------------------------------- text layout

def layout_words(words, max_w, max_h, start=96, min_size=48, weight=900, line_gap=1.12):
    """Fit words into a box. Returns (font, lines) with lines = [[(word, x, width), ...], ...]."""
    size = start
    while size >= min_size:
        f = font(size, weight)
        space = f.getlength(" ")
        lines, cur, cur_w = [], [], 0.0
        for i, w in enumerate(words):
            ww = f.getlength(w)
            if cur and cur_w + space + ww > max_w:
                lines.append(cur)
                cur, cur_w = [], 0.0
            cur.append((i, w, ww))
            cur_w += (space if len(cur) > 1 else 0) + ww
        if cur:
            lines.append(cur)
        if len(lines) * size * line_gap <= max_h and all(ww <= max_w for _, _, ww in sum(lines, [])):
            return f, lines, size * line_gap
        size -= 4
    return f, lines, size * line_gap


def draw_word_block(img, words, box, active, spoken_upto, stroke_rgb, start=96, highlight=(255, 225, 77)):
    """Centered karaoke text. Words <= spoken_upto are white, the active one yellow, the rest dim."""
    x0, y0, x1, y1 = box
    f, lines, lh = layout_words(words, x1 - x0, y1 - y0, start=start)
    space = f.getlength(" ")
    total_h = len(lines) * lh
    d = ImageDraw.Draw(img)
    y = y0 + (y1 - y0 - total_h) / 2
    sw = max(4, int(f.size * 0.09))
    for line in lines:
        lw = sum(ww for _, _, ww in line) + space * (len(line) - 1)
        x = x0 + (x1 - x0 - lw) / 2
        for i, w, ww in line:
            if i == active:
                fill = highlight + (255,)
            elif i <= spoken_upto:
                fill = (255, 255, 255, 255)
            else:
                fill = (255, 255, 255, 95)
            d.text((x + 6, y + 8), w, font=f, fill=(0, 0, 0, 90 if fill[3] == 255 else 30))
            d.text((x, y), w, font=f, fill=fill, stroke_width=sw,
                   stroke_fill=stroke_rgb + ((255,) if fill[3] == 255 else (80,)))
            x += ww + space
        y += lh


def scaled_layer(layer, scale, center):
    """Scale an RGBA layer around a center point, return (image, offset)."""
    if abs(scale - 1) < 1e-3:
        return layer, (0, 0)
    w, h = layer.size
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    s = layer.resize((nw, nh), Image.BILINEAR)
    cx, cy = center
    return s, (int(cx - cx * scale), int(cy - cy * scale))


# ---------------------------------------------------------------- audio timeline

VOICE_CHAIN = ("highpass=f=75,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.4:g=3,"
               "equalizer=f=110:t=q:w=1:g=2,deesser=i=0.4,"
               "acompressor=threshold=0.08:ratio=3.5:attack=8:release=120:makeup=1.6,"
               "aecho=0.9:0.85:28|47:0.12|0.07")


def ffmpeg_filter(x, chain):
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", chain, "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"],
                       input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    y = np.frombuffer(p.stdout, dtype=np.float32)
    out = np.zeros(len(x), np.float32)
    out[: min(len(x), len(y))] = y[: len(x)]
    return out


class Timeline:
    def __init__(self):
        self.audio = []  # (start, samples)
        self.clips = []  # (start, duration, frame_fn)

    def add_audio(self, start, samples, gain=1.0, bus="voice"):
        self.audio.append((start, samples * gain, bus))

    def add_sfx(self, start, name, gain=1.0):
        self.add_audio(start, sfxlib.SFX[name](), gain, "sfx")

    def add_clip(self, start, duration, fn):
        self.clips.append((start, duration, fn))

    @property
    def duration(self):
        return max(s + d for s, d, _ in self.clips)

    def mix(self):
        """Sum per bus. Voice gets EQ, compression and a little room, sfx a little room,
        music is ducked under the voice. Old single-bus timelines still work."""
        n = int(math.ceil(self.duration * SR)) + SR
        buses = {}
        for start, smp, bus in self.audio:
            buf = buses.setdefault(bus, np.zeros(n, dtype=np.float32))
            a = int(start * SR)
            b = min(n, a + len(smp))
            buf[a:b] += smp[: b - a]
        out = np.zeros(n, dtype=np.float32)
        if "voice" in buses:
            v = ffmpeg_filter(buses["voice"], VOICE_CHAIN)
            out += v
            env = np.abs(buses["voice"])
            k = int(0.25 * SR)
            env = np.convolve(env, np.ones(k) / k, mode="same")
            duck = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
        else:
            duck = 1.0
        if "sfx" in buses:
            from .music import reverb
            out += reverb(buses["sfx"], 1.2, 0.18, seed=9)
        if "music" in buses:
            out += buses["music"] * duck
        peak = np.max(np.abs(out)) or 1.0
        if peak > 0.98:
            out *= 0.98 / peak
        return out[: int(self.duration * SR)]

    def frame(self, t):
        """Clips may overlap during transitions; a clip fn gets (t_local) and returns an RGB image or None."""
        active = [(s, d, fn) for s, d, fn in self.clips if s <= t < s + d]
        img = None
        for s, d, fn in active:
            out = fn(t - s, img)
            if out is not None:
                img = out
        return img


def write_video(tl, out_path, preview_dir=None):
    total = tl.duration
    nframes = int(total * FPS)
    wav = out_path + ".wav"
    audio = tl.mix()
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    import wave
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-af", "loudnorm=I=-13:TP=-1.0",
         "-movflags", "+faststart", "-shortest", out_path], stdin=subprocess.PIPE)
    if preview_dir:
        os.makedirs(preview_dir, exist_ok=True)
    for i in range(nframes):
        t = i / FPS
        img = tl.frame(t).convert("RGB")
        if preview_dir and i % (FPS * 2) == 0:
            img.resize((360, 640)).save(os.path.join(preview_dir, f"f{i:05d}.jpg"), quality=80)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    return total


# ---------------------------------------------------------------- template: wyr

PALETTES = {
    "red": ((235, 64, 72), (160, 22, 40)),
    "blue": ((44, 116, 255), (18, 44, 150)),
}


def gradient(size, top, bottom):
    w, h = size
    t = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(top)[None, None, :] * (1 - t) + np.array(bottom)[None, None, :] * t
    arr = np.repeat(arr, w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def wyr_background():
    top = gradient((W, H // 2), *PALETTES["red"])
    bot = gradient((W, H // 2), PALETTES["blue"][1], PALETTES["blue"][0])
    bg = Image.new("RGB", (W, H))
    bg.paste(top, (0, 0))
    bg.paste(bot, (0, H // 2))
    # soft vignette and a light glow per half, so it looks less flat
    glow = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((W * 0.05, H * 0.08, W * 0.95, H * 0.45), fill=70)
    gd.ellipse((W * 0.05, H * 0.55, W * 0.95, H * 0.92), fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    bg = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), bg, glow.point(lambda v: v * 0.35))
    return bg


EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def emoji_img(ch, size):
    f = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new("RGBA", (160, 140))
    ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    s = size / max(im.size)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    shadow.putalpha(im.getchannel("A").point(lambda v: v * 0.35))
    out = Image.new("RGBA", (im.width + 30, im.height + 30))
    out.paste(shadow.filter(ImageFilter.GaussianBlur(8)), (18, 22), shadow.filter(ImageFilter.GaussianBlur(8)))
    out.alpha_composite(im, (0, 0))
    return out


def half_image(path, top):
    """Cover an image into one half and darken it, so white text stays readable."""
    im = cover(Image.open(path).convert("RGB"), W, H // 2)
    shade = Image.new("RGB", im.size, (0, 0, 0))
    return Image.blend(im, shade, 0.32)


def wyr_pair_clip(bg, header, a_words, b_words, a_times, b_times, b_offset, countdown_at, countdown_len,
                  round_label=None, pulse_oder_at=None, badge_text="ODER", ea=None, eb=None, ia=None, ib=None, a_lit=False):
    """Returns frame_fn for one split-screen pair. Option A is visible from t=0, B pops in when spoken."""
    f_head = font(50, 800)
    f_badge = font(46 if len(badge_text) > 2 else 64, 900)
    f_count = font(110, 900)
    base = bg.copy()
    if ia:
        base.paste(half_image(ia, True), (0, 0))
    if ib:
        base.paste(half_image(ib, False), (0, H // 2))
    EM = 190
    em_a = emoji_img(ea, EM) if ea and not ia else None
    em_b = emoji_img(eb, EM) if eb and not ib else None
    A_BOX = (60, 510 if em_a else 300, SAFE_RIGHT, 830)
    B_BOX = (60, 1290 if em_b else 1090, SAFE_RIGHT, 1610)
    stroke_a = (0, 0, 0) if ia else (110, 8, 24)
    stroke_b = (0, 0, 0) if ib else (10, 26, 110)

    def progress(times, t):
        active, spoken = -1, -1
        for i, (_, s, e) in enumerate(times):
            if t >= s:
                spoken = i
                if t < e:
                    active = i
        return active, spoken

    def fn(t, _below):
        img = base.copy().convert("RGBA")
        d = ImageDraw.Draw(img)
        if header:
            label = header + (f"   {round_label}" if round_label else "")
            hw = d.textlength(label, font=f_head)
            d.text(((SAFE_RIGHT + 60 - hw) / 2, 215), label, font=f_head, fill=(255, 255, 255, 235),
                   stroke_width=4, stroke_fill=(110, 8, 24))
        # option A, already there when the round slides in
        if em_a:
            bob = math.sin(t * 2.4) * 8
            img.alpha_composite(em_a, (int((SAFE_RIGHT + 60 - em_a.width) / 2), int(300 + bob)))
        layer = Image.new("RGBA", (W, H))
        act, sp = progress(a_times, t)
        if a_lit:
            sp = len(a_words)
        draw_word_block(layer, a_words, A_BOX, act, sp, stroke_a, start=128)
        img.alpha_composite(layer)
        # option B pops in
        tb = t - b_offset
        if b_times and tb >= b_times[0][1] - 0.08:
            k = (tb - (b_times[0][1] - 0.08)) / 0.28
            sc = 0.55 + 0.45 * ease_out_back(k)
            if em_b:
                e = em_b.resize((max(1, int(em_b.width * sc)), max(1, int(em_b.height * sc))))
                bob = math.sin(t * 2.4 + 1.5) * 8
                img.alpha_composite(e, (int((SAFE_RIGHT + 60 - e.width) / 2), int(1085 + bob + (em_b.height - e.height) / 2)))
            layer = Image.new("RGBA", (W, H))
            act, sp = progress(b_times, tb)
            draw_word_block(layer, b_words, B_BOX, act, sp, stroke_b, start=128)
            lay, off = scaled_layer(layer, sc, ((B_BOX[0] + B_BOX[2]) / 2, (B_BOX[1] + B_BOX[3]) / 2))
            img.paste(lay, off, lay)
        # countdown bar on the seam
        if countdown_at is not None and t >= countdown_at:
            p = min(1.0, (t - countdown_at) / countdown_len)
            bw = int(W * (1 - p))
            d.rectangle(((W - bw) // 2, H // 2 - 9, (W + bw) // 2, H // 2 + 9), fill=(255, 225, 77, 255))
        # badge
        r = 92
        pul = 0.0
        if pulse_oder_at is not None and 0 <= t - pulse_oder_at < 0.35:
            pul = math.sin((t - pulse_oder_at) / 0.35 * math.pi) * 0.18
        if countdown_at is not None and t >= countdown_at:
            k = (t - countdown_at) % 1.0
            pul = max(pul, (1 - k) ** 3 * 0.15)
        rr = int(r * (1 + pul))
        cx, cy = W // 2, H // 2
        d.ellipse((cx - rr - 8, cy - rr - 8, cx + rr + 8, cy + rr + 8), fill=(20, 20, 30, 120))
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 255, 255, 255))
        if countdown_at is not None and t >= countdown_at:
            n = max(1, math.ceil(countdown_len - (t - countdown_at)))
            txt, f = str(n), f_count
        else:
            txt, f = badge_text, f_badge
        bb = d.textbbox((0, 0), txt, font=f)
        d.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), txt, font=f, fill=(25, 25, 35))
        return img.convert("RGB")

    return fn


def slide_transition(dur=0.35):
    """Overlapping clip: takes the previous frame and pushes the next one up from below."""
    def make(prev_fn, prev_t_end, next_fn):
        def fn(t, _below):
            p = ease_in_out(t / dur)
            a = prev_fn(prev_t_end, None)
            b = next_fn(0.0, None)
            img = Image.new("RGB", (W, H))
            img.paste(a, (0, int(-H * p)))
            img.paste(b, (0, int(H * (1 - p))))
            return img
        return fn
    return make


def build_wyr(script):
    v = script["voice"]
    say = lambda text: tts.synth(text, v["backend"], v["voice"], v.get("speed", 1.0))
    lang = script.get("lang", "de")
    prefix = script.get("prefix", "Würdest du lieber" if lang == "de" else "Would you rather")
    joiner = script.get("joiner", "oder" if lang == "de" else "or")
    header = script.get("header", prefix.upper() + " ...")
    bg = wyr_background()
    tl = Timeline()
    t = 0.0
    TR = 0.35
    prev = None  # (fn, start, dur)

    def place(fn, dur):
        nonlocal t, prev
        if prev is not None:
            pfn, ps, pd = prev
            tl.add_clip(t - TR, TR, slide_transition(TR)(pfn, pd - 1e-3, fn))
            tl.add_sfx(t - TR, "whoosh", 0.8)
        tl.add_clip(t, dur, fn)
        prev = (fn, t, dur)
        t += dur

    # hook
    hook = script["hook"]
    ha, hb = say(hook["a"]), say(hook["b"])
    da, db = len(ha) / SR, len(hb) / SR
    at = tts.word_times(hook["a"], da)
    bt = tts.word_times(hook["b"], db)
    lead = 0.05
    a_times = [(w, s + lead, e + lead) for w, s, e in at]
    b_off = lead + da + 0.15
    b_times = [(w, s, e) for w, s, e in bt]
    dur = b_off + db + 0.45
    tl.add_audio(t + lead, ha)
    tl.add_audio(t + b_off, hb)
    tl.add_sfx(t + lead, "boom", 0.6)
    place(wyr_pair_clip(bg, None, hook["a"].split(), hook["b"].split(), a_times, b_times, b_off, None, 0,
                        badge_text=script.get("hook_badge", "?"), ea=hook.get("ea"), eb=hook.get("eb"), a_lit=True), dur)

    rounds = script["rounds"]
    for k, r in enumerate(rounds, 1):
        if isinstance(r, list):
            r = {"a": r[0], "b": r[1]}
        a, b = r["a"], r["b"]
        line_a = f"{prefix} {a}"
        line_b = f"{joiner} {b}?"
        sa, sb = say(line_a), say(line_b)
        da, db = len(sa) / SR, len(sb) / SR
        lead = 0.25
        # word timing for the whole sentence, then keep only the option words
        ta = tts.word_times(line_a, da)
        npre = len(prefix.split())
        a_times = [(w, s + lead, e + lead) for w, s, e in ta[npre:]]
        b_off = lead + da + 0.2
        tb = tts.word_times(line_b, db)
        b_times = [(w, s, e) for w, s, e in tb[1:]]
        oder_at = b_off + tb[0][1]
        cd_at = b_off + db + 0.35
        cd_len = script.get("countdown", 3)
        dur = cd_at + cd_len + 0.15
        tl.add_audio(t + lead, sa)
        tl.add_audio(t + b_off, sb)
        tl.add_sfx(t + b_off + b_times[0][1] - 0.05, "pop", 0.7)
        for i in range(cd_len):
            tl.add_sfx(t + cd_at + i, "tick", 0.9)
        place(wyr_pair_clip(bg, header, a.split(), b.split(), a_times, b_times, b_off, cd_at, cd_len,
                            round_label=f"{k}/{len(rounds)}", pulse_oder_at=oder_at, badge_text=joiner.upper(),
                            ea=r.get("ea"), eb=r.get("eb"), ia=r.get("ia"), ib=r.get("ib")), dur)

    # outro
    out = script["outro"]
    sa, sb = say(out["say_a"]), say(out["say_b"])
    da, db = len(sa) / SR, len(sb) / SR
    lead = 0.2
    a_times = [(w, s + lead, e + lead) for w, s, e in tts.word_times(out["a"], da)]
    b_off = lead + da + 0.2
    b_times = tts.word_times(out["b"], db)
    dur = max(b_off + db + 1.6, script.get("min_duration", 61.5) - t)
    tl.add_audio(t + lead, sa)
    tl.add_audio(t + b_off, sb)
    tl.add_sfx(t + b_off, "ding", 0.7)
    place(wyr_pair_clip(bg, None, out["a"].split(), out["b"].split(), a_times, b_times, b_off, None, 0,
                        badge_text=out.get("badge", "?"), ea=out.get("ea"), eb=out.get("eb")), dur)
    return tl


# ---------------------------------------------------------------- template: story

def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * s + 0.5), int(img.height * s + 0.5)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def kenburns_clip(path, motion, dur, overscan=1.18):
    base = cover(Image.open(path).convert("RGB"), int(W * overscan), int(H * overscan))
    bw, bh = base.size

    def fn(t, _below):
        p = ease_in_out(t / dur) if motion != "shake" else t / dur
        if motion == "zoom_out":
            z = overscan - (overscan - 1) * p
            cx, cy = bw / 2, bh / 2
        elif motion == "pan_left":
            z = overscan * 0.98
            cx, cy = bw / 2 + (bw - W * z) / 2 * (1 - 2 * p) * 0.9, bh / 2
        elif motion == "pan_right":
            z = overscan * 0.98
            cx, cy = bw / 2 - (bw - W * z) / 2 * (1 - 2 * p) * 0.9, bh / 2
        elif motion == "shake":
            z = overscan * 0.9
            cx = bw / 2 + math.sin(t * 37) * 12 + math.sin(t * 23) * 8
            cy = bh / 2 + math.cos(t * 31) * 10
        else:  # zoom_in
            z = 1 + (overscan - 1) * p
            cx, cy = bw / 2, bh / 2
        cw, ch = W * (overscan / z), H * (overscan / z)
        cw, ch = min(cw, bw), min(ch, bh)
        box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
        return base.resize((W, H), Image.BILINEAR, box=box)

    return fn


def caption_overlay(words_times, chunk=3, y=1180):
    """Word-by-word captions, shown in chunks, current word yellow and slightly bigger."""
    chunks, cur = [], []
    for wt in words_times:
        cur.append(wt)
        if len(cur) >= chunk or wt[0][-1] in ".!?,":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    f = font(82, 900)

    def draw(img, t):
        for c in chunks:
            if c[0][1] <= t < (c[-1][2] + 0.05):
                d = ImageDraw.Draw(img)
                words = [w.upper() for w, _, _ in c]
                space = f.getlength(" ")
                widths = [f.getlength(w) for w in words]
                total = sum(widths) + space * (len(words) - 1)
                maxw = SAFE_RIGHT - 60
                scale = min(1.0, maxw / total)
                ff = font(int(82 * scale), 900) if scale < 1 else f
                widths = [ff.getlength(w) for w in words]
                space = ff.getlength(" ")
                total = sum(widths) + space * (len(words) - 1)
                pop = 1 + 0.12 * (1 - ease_out_back(min(1, (t - c[0][1]) / 0.18)))
                x = (SAFE_RIGHT + 30 - total) / 2
                for (w, s, e), word, ww in zip(c, words, widths):
                    on = s <= t < e
                    fill = (255, 225, 77) if on else (255, 255, 255)
                    d.text((x, y - (8 if on else 0) * pop), word, font=ff, fill=fill,
                           stroke_width=10, stroke_fill=(0, 0, 0))
                    x += ww + space
                return

    return draw


def choice_overlay(options, start, cd_len):
    f = font(60, 900)
    fl = font(54, 900)
    colors = [(235, 64, 72), (44, 116, 255), (40, 180, 99), (245, 166, 35)]

    def draw(img, t):
        if t < start:
            return
        d = ImageDraw.Draw(img, "RGBA")
        n = len(options)
        top = 560
        for i, opt in enumerate(options):
            p = ease_out_back((t - start - i * 0.12) / 0.3)
            if p <= 0:
                continue
            y = top + i * 170
            x0 = 70 - (1 - p) * 900
            d.rounded_rectangle((x0, y, x0 + 820, y + 140), 32, fill=colors[i % 4] + (235,),
                                outline=(255, 255, 255, 255), width=6)
            d.text((x0 + 36, y + 38), "ABCD"[i], font=fl, fill=(255, 255, 255))
            fo = f
            while fo.getlength(opt) > 680 and fo.size > 30:
                fo = font(fo.size - 4, 900)
            d.text((x0 + 110, y + 70 - fo.size * 0.55), opt, font=fo, fill=(255, 255, 255))
        cd_at = start + 0.3 + n * 0.12
        if t >= cd_at:
            p = min(1, (t - cd_at) / cd_len)
            bw = int(820 * (1 - p))
            y = top + n * 170 + 10
            d.rounded_rectangle((70, y, 70 + max(bw, 24), y + 24), 12, fill=(255, 225, 77, 255))

    return draw


def build_story(script):
    v = script["voice"]
    say = lambda text: tts.synth(text, v["backend"], v["voice"], v.get("speed", 1.0))
    tl = Timeline()
    t = 0.0
    XF = 0.18
    prev_fn = None
    for sc in script["scenes"]:
        audio = say(sc["text"])
        d = len(audio) / SR
        lead = sc.get("lead", 0.1)
        words = tts.word_times(sc["text"], d)
        words = [(w, s + lead, e + lead) for w, s, e in words]
        choice = sc.get("choice")
        cd_len = sc.get("countdown", 3)
        dur = lead + d + sc.get("tail", 0.25) + ((0.3 + len(choice) * 0.12 + cd_len) if choice else 0)
        bg = kenburns_clip(sc["image"], sc.get("motion", "zoom_in"), dur)
        cap = caption_overlay(words, chunk=sc.get("chunk", 3))
        ch = choice_overlay(choice, lead + d + 0.1, cd_len) if choice else None
        title = sc.get("title")
        ft = font(64, 900)

        def fn(tt, _below, bg=bg, cap=cap, ch=ch, title=title, ft=ft):
            img = bg(tt, None)
            d_ = ImageDraw.Draw(img)
            if title:
                tw = d_.textlength(title, font=ft)
                d_.text(((SAFE_RIGHT + 30 - tw) / 2, 260), title, font=ft, fill=(255, 255, 255),
                        stroke_width=9, stroke_fill=(0, 0, 0))
            if ch:
                ch(img, tt)
            else:
                cap(img, tt)
            return img

        tl.add_audio(t + lead, audio)
        for name, at in sc.get("sfx", []):
            tl.add_sfx(t + at, name)
        if choice:
            base = t + lead + d + 0.1 + 0.3 + len(choice) * 0.12
            for i in range(cd_len):
                tl.add_sfx(base + i, "tick", 0.9)
        if prev_fn is not None:
            pf, pstart, pdur = prev_fn

            def xf(tt, _below, pf=pf, pdur=pdur, nf=fn):
                a = pf(pdur - XF + tt, None)
                b = nf(tt, None)
                return Image.blend(a, b, ease_in_out(tt / XF))

            tl.add_clip(t, XF, xf)
            tl.add_sfx(t, "whoosh", 0.5)
            tl.add_clip(t + XF, dur - XF, lambda tt, _b, fn=fn: fn(tt + XF, None))
        else:
            tl.add_clip(t, dur, fn)
        prev_fn = (fn, t, dur)
        t += dur
    return tl


TEMPLATES = {"wyr": build_wyr, "story": build_story}


def main():
    script_path, out = sys.argv[1], sys.argv[2]
    preview = sys.argv[3] if len(sys.argv) > 3 else None
    with open(script_path) as fh:
        script = json.load(fh)
    base = os.path.dirname(os.path.abspath(script_path))
    for sc in script.get("scenes", []):
        sc["image"] = os.path.join(base, sc["image"])
    tl = TEMPLATES[script["template"]](script)
    dur = write_video(tl, out, preview)
    print(f"{out}: {dur:.1f}s")


if __name__ == "__main__":
    main()
