"""Flat 2D vector illustration kit. Every function returns an SVG fragment.

Scenes are drawn on a 1600x1200 canvas (4:3, like the reference videos) and later placed
into the 9:16 frame by the episode template. Style rules: flat fills, no outlines, big
round eyes, muted night palette, light only through soft glows.
"""
import math
import random

W, H = 1600, 1200


def svg(body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<defs>{DEFS}{defs}</defs>{body}</svg>')


DEFS = """
<filter id="blur8"><feGaussianBlur stdDeviation="8"/></filter>
<filter id="blur20"><feGaussianBlur stdDeviation="20"/></filter>
<filter id="blur60"><feGaussianBlur stdDeviation="60"/></filter>
<radialGradient id="glowWarm"><stop offset="0" stop-color="#ffd27a" stop-opacity=".85"/><stop offset="1" stop-color="#ffd27a" stop-opacity="0"/></radialGradient>
<radialGradient id="glowCold"><stop offset="0" stop-color="#bfe3ff" stop-opacity=".7"/><stop offset="1" stop-color="#bfe3ff" stop-opacity="0"/></radialGradient>
<radialGradient id="glowRed"><stop offset="0" stop-color="#ff3b3b" stop-opacity=".8"/><stop offset="1" stop-color="#ff3b3b" stop-opacity="0"/></radialGradient>
<radialGradient id="vignette" cx=".5" cy=".5" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".75"/></radialGradient>
<linearGradient id="fogUp" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#9fb0c8" stop-opacity=".35"/><stop offset="1" stop-color="#9fb0c8" stop-opacity="0"/></linearGradient>
"""


def rect(x, y, w, h, fill, rx=0, op=1, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" opacity="{op}" {extra}/>'


def circle(x, y, r, fill, op=1, extra=""):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" opacity="{op}" {extra}/>'


def ellipse(x, y, rx, ry, fill, op=1, extra=""):
    return f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" opacity="{op}" {extra}/>'


def path(d, fill, op=1, extra=""):
    return f'<path d="{d}" fill="{fill}" opacity="{op}" {extra}/>'


def line(x1, y1, x2, y2, color, w, op=1, cap="round"):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
            f'stroke-width="{w:.1f}" stroke-linecap="{cap}" opacity="{op}"/>')


def poly(points, color, w, op=1):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{w:.1f}" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="{op}"/>')


def text(x, y, s, size, fill, weight=800, anchor="middle", family="Montserrat, Arial, sans-serif", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" font-family="{family}" {extra}>{s}</text>')


def glow(x, y, r, kind="Warm", op=1):
    return ellipse(x, y, r, r, f"url(#glow{kind})", op)


def shade(c, k):
    """Darken (k<1) or lighten (k>1) a hex color."""
    c = c.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    f = (lambda v: min(255, int(v * k))) if k <= 1 else (lambda v: min(255, int(v + (255 - v) * (k - 1))))
    return "#%02x%02x%02x" % (f(r), f(g), f(b))


# ---------------------------------------------------------------- characters

SKIN = {"light": "#f2c9a6", "tan": "#d9a27a", "dark": "#8d5a3b", "zombie": "#8fa67c", "pale": "#e9d9c6"}


def person(x, yf, h=440, skin="light", hair="#5a3a22", style="short", shirt="#7a2f4a", pants="#2e3550",
           shoes="#1d1d24", mood="neutral", look=(0, 0), arms="down", zombie=False, tear=False, blood=False,
           flip=False, extra=""):
    """Front-facing character standing with feet at (x, yf). h is total height."""
    u = h / 100
    sk = SKIN.get(skin, skin)
    if zombie:
        sk = SKIN["zombie"]
    hx, hy, hr = x, yf - 88 * u, 12 * u
    out = [ellipse(x, yf, 20 * u, 3.5 * u, "#000000", 0.28)]
    # long hair behind the body
    if style in ("long", "pigtails_long"):
        out.append(path(f"M{hx - 13 * u},{hy - 2 * u} Q{hx - 15 * u},{hy + 22 * u} {hx - 10 * u},{hy + 26 * u} "
                        f"L{hx + 10 * u},{hy + 26 * u} Q{hx + 15 * u},{hy + 22 * u} {hx + 13 * u},{hy - 2 * u} Z", hair))
    # legs and shoes
    for s in (-1, 1):
        lx = x + s * 6.5 * u
        out.append(rect(lx - 4.5 * u, yf - 42 * u, 9 * u, 39 * u, pants, rx=3 * u))
        out.append(ellipse(lx + s * 1.5 * u, yf - 2.5 * u, 6.5 * u, 3.2 * u, shoes))
    # arms (behind torso when down)
    sh_y = yf - 71 * u
    hands = {
        "down": [(-19, -43), (19, -43)],
        "up": [(-25, -104), (25, -104)],
        "reach": [(-27, -66), (27, -66)],
        "cross": [(6, -58), (-6, -58)],
        "wave": [(-19, -43), (27, -100)],
        "phone": [(-19, -43), (6, -82)],
        "hold": [(-12, -50), (12, -50)],
        "point": [(-19, -43), (34, -74)],
    }[arms]
    elbows = {
        "down": [(-18, -57), (18, -57)],
        "up": [(-24, -82), (24, -82)],
        "reach": [(-22, -68), (22, -68)],
        "cross": [(-17, -55), (17, -55)],
        "wave": [(-18, -57), (25, -78)],
        "phone": [(-18, -57), (17, -62)],
        "hold": [(-17, -54), (17, -54)],
        "point": [(-18, -57), (24, -72)],
    }[arms]
    if flip:
        hands = [(-a, b) for a, b in hands][::-1]
        elbows = [(-a, b) for a, b in elbows][::-1]
    arm_col = shade(shirt, 0.85)
    for s, (hxo, hyo), (ex, ey) in zip((-1, 1), hands, elbows):
        sx = x + s * 13 * u
        out.append(poly([(sx, sh_y), (x + ex * u, yf + ey * u), (x + hxo * u, yf + hyo * u)], arm_col, 7.5 * u))
    # torso
    hem = yf - 40 * u
    if zombie:
        jag = " ".join(f"L{x + 14 * u - i * 4 * u},{hem + (3 * u if i % 2 else -1 * u)}" for i in range(8))
        out.append(path(f"M{x - 13 * u},{sh_y - 4 * u} Q{x},{sh_y - 8 * u} {x + 13 * u},{sh_y - 4 * u} "
                        f"L{x + 15 * u},{hem} {jag} L{x - 15 * u},{hem} Z", shirt))
    else:
        out.append(path(f"M{x - 13 * u},{sh_y - 4 * u} Q{x},{sh_y - 8 * u} {x + 13 * u},{sh_y - 4 * u} "
                        f"L{x + 14.5 * u},{hem + 2 * u} Q{x},{hem + 4 * u} {x - 14.5 * u},{hem + 2 * u} Z", shirt))
    out.append(path(f"M{x - 4 * u},{sh_y - 6 * u} Q{x},{sh_y - 1 * u} {x + 4 * u},{sh_y - 6 * u} Z", shade(shirt, 0.7)))
    if blood:
        out.append(ellipse(x + 9 * u, sh_y + 10 * u, 4 * u, 6 * u, "#9b1c22", 0.9))
        out.append(ellipse(x + 11 * u, sh_y + 17 * u, 1.5 * u, 3 * u, "#9b1c22", 0.9))
    # hands on top
    for (hxo, hyo) in hands:
        out.append(circle(x + hxo * u, yf + hyo * u, 3.5 * u, sk))
    if arms == "phone":
        px, py = hands[1]
        out.append(rect(x + px * u - 3 * u, yf + py * u - 8 * u, 6 * u, 11 * u, "#15161c", rx=u))
        out.append(rect(x + px * u - 2.2 * u, yf + py * u - 7 * u, 4.4 * u, 8 * u, "#7fb7ff", rx=0.5 * u, op=0.9))
    # neck and head
    out.append(rect(hx - 3.5 * u, hy + 8 * u, 7 * u, 7 * u, shade(sk, 0.88)))
    tilt = 'transform="rotate(8 %.1f %.1f)"' % (hx, hy) if zombie else ""
    head = [ellipse(hx, hy, hr, hr * 1.05, sk)]
    # ears
    head.append(ellipse(hx - hr, hy + u, 2.2 * u, 3 * u, shade(sk, 0.92)))
    head.append(ellipse(hx + hr, hy + u, 2.2 * u, 3 * u, shade(sk, 0.92)))
    # hair on top
    if style == "short":
        head.append(path(f"M{hx - hr - 0.5 * u},{hy + 1 * u} Q{hx - hr},{hy - hr * 1.25} {hx},{hy - hr * 1.12} "
                         f"Q{hx + hr * 1.1},{hy - hr * 1.2} {hx + hr + 0.5 * u},{hy + 1 * u} "
                         f"Q{hx + 6 * u},{hy - 8 * u} {hx - 2 * u},{hy - 7 * u} Q{hx - 8 * u},{hy - 6 * u} {hx - hr - 0.5 * u},{hy + 1 * u} Z", hair))
    elif style in ("long", "pigtails", "pigtails_long", "bob"):
        head.append(path(f"M{hx - hr - 1 * u},{hy + 4 * u} Q{hx - hr - 1 * u},{hy - hr * 1.25} {hx},{hy - hr * 1.15} "
                         f"Q{hx + hr + 1 * u},{hy - hr * 1.25} {hx + hr + 1 * u},{hy + 4 * u} "
                         f"Q{hx + 7 * u},{hy - 6 * u} {hx},{hy - 7 * u} Q{hx - 7 * u},{hy - 6 * u} {hx - hr - 1 * u},{hy + 4 * u} Z", hair))
        if style == "pigtails":
            for s in (-1, 1):
                head.append(ellipse(hx + s * (hr + 3 * u), hy - 2 * u, 4.5 * u, 6.5 * u, hair))
                head.append(circle(hx + s * (hr + 0.5 * u), hy - 6 * u, 1.6 * u, "#ff6fa8"))
        if style == "bob":
            for s in (-1, 1):
                head.append(path(f"M{hx + s * (hr + 1 * u)},{hy - 2 * u} L{hx + s * (hr + 2 * u)},{hy + 9 * u} "
                                 f"L{hx + s * (hr - 3 * u)},{hy + 9 * u} Z", hair))
    elif style == "cap":
        head.append(path(f"M{hx - hr - 0.5 * u},{hy - 4 * u} Q{hx},{hy - hr * 1.7} {hx + hr + 0.5 * u},{hy - 4 * u} Z", hair))
        head.append(rect(hx - 3 * u, hy - 6 * u, hr + 9 * u, 2.6 * u, shade(hair, 0.8), rx=u))
    elif style == "helmet":
        head.append(path(f"M{hx - hr - 2 * u},{hy + 1 * u} Q{hx},{hy - hr * 1.6} {hx + hr + 2 * u},{hy + 1 * u} Z", hair))
    elif style == "bald":
        head.append(ellipse(hx - 3 * u, hy - 8 * u, 4 * u, 2 * u, "#ffffff", 0.15))
    if zombie:
        head.append(path(f"M{hx - 6 * u},{hy - 6 * u} l3,{4 * u} l-2,{3 * u}", "none", 1,
                         f'stroke="#4d5e44" stroke-width="{0.8 * u}"'))
    # face
    ex = 4.6 * u
    ey = hy + 0.5 * u
    big = mood in ("scared", "shock", "crying")
    rx, ry = (3.8 * u, 4.6 * u) if big else (3.2 * u, 3.9 * u)
    for s in (-1, 1):
        if zombie:
            head.append(ellipse(hx + s * ex, ey, rx, ry * 0.9, "#f4f1d0"))
            head.append(path(f"M{hx + s * ex - rx - 0.3 * u},{ey - ry * 0.2} L{hx + s * ex + rx + 0.3 * u},{ey - ry * 0.2} "
                             f"L{hx + s * ex + rx + 0.3 * u},{ey - ry - u} L{hx + s * ex - rx - 0.3 * u},{ey - ry - u} Z", sk))
            head.append(circle(hx + s * ex, ey + 0.8 * u, 0.9 * u, "#7a1c1c"))
            continue
        head.append(ellipse(hx + s * ex, ey, rx, ry, "#ffffff"))
        pr = 1.4 * u if big else 1.9 * u
        head.append(circle(hx + s * ex + look[0] * u, ey + look[1] * u + 0.3 * u, pr, "#1b1b22"))
        head.append(circle(hx + s * ex + look[0] * u + 0.6 * u, ey + look[1] * u - 0.5 * u, 0.5 * u, "#ffffff"))
        # brows
        by = ey - ry - 1.6 * u
        if mood in ("scared", "shock", "crying", "sad"):
            head.append(line(hx + s * (ex + 3 * u), by + 1.2 * u, hx + s * (ex - 2.5 * u), by - 0.8 * u, shade(hair, 0.8), 1.3 * u))
        elif mood == "angry":
            head.append(line(hx + s * (ex + 3 * u), by - 1 * u, hx + s * (ex - 2.5 * u), by + 1.2 * u, shade(hair, 0.8), 1.3 * u))
        else:
            head.append(line(hx + s * (ex + 2.8 * u), by, hx + s * (ex - 2.5 * u), by, shade(hair, 0.8), 1.1 * u))
    my = hy + 7.5 * u
    if zombie:
        head.append(path(f"M{hx - 4 * u},{my - u} L{hx - 2 * u},{my + 1.5 * u} L{hx},{my - 0.5 * u} L{hx + 2 * u},{my + 1.8 * u} "
                         f"L{hx + 4 * u},{my - u} Q{hx},{my + 4 * u} {hx - 4 * u},{my - u} Z", "#3b1416"))
    elif mood in ("scared", "shock", "shout"):
        o = 3.2 if mood == "shout" else 2.2
        head.append(ellipse(hx, my + 0.5 * u, o * u * 0.9, o * u, "#3b1416"))
    elif mood == "crying":
        head.append(path(f"M{hx - 3 * u},{my + 1.5 * u} Q{hx},{my - 1.5 * u} {hx + 3 * u},{my + 1.5 * u}", "none", 1,
                         f'stroke="#3b1416" stroke-width="{1.1 * u}" stroke-linecap="round"'))
    elif mood == "smile":
        head.append(path(f"M{hx - 3.5 * u},{my - 0.5 * u} Q{hx},{my + 3 * u} {hx + 3.5 * u},{my - 0.5 * u}", "none", 1,
                         f'stroke="#3b1416" stroke-width="{1.1 * u}" stroke-linecap="round"'))
    else:
        head.append(line(hx - 2.5 * u, my, hx + 2.5 * u, my, "#3b1416", 1.1 * u))
    if tear or mood == "crying":
        for s in (-1, 1):
            head.append(path(f"M{hx + s * ex},{ey + ry} q{-0.8 * u},{3 * u} 0,{4 * u} q{0.8 * u},{-1 * u} 0,{-4 * u} Z", "#8fd0ff"))
    out.append(f"<g {tilt}>{''.join(head)}</g>")
    return f"<g {extra}>{''.join(out)}</g>"


def zombie(x, yf, h=430, shirt="#5d6b78", pants="#3a3530", hair="#3b3a33", style="short", **kw):
    return person(x, yf, h, shirt=shirt, pants=pants, hair=hair, style=style, zombie=True, arms=kw.pop("arms", "reach"), **kw)


def silhouette(x, yf, h, color="#0d0f16", op=1, arms="reach"):
    """Dark figure without face, for crowds in the distance."""
    u = h / 100
    s = [ellipse(x, yf - 88 * u, 11 * u, 12 * u, color),
         path(f"M{x - 13 * u},{yf - 75 * u} L{x + 13 * u},{yf - 75 * u} L{x + 14 * u},{yf - 38 * u} L{x - 14 * u},{yf - 38 * u} Z", color),
         rect(x - 11 * u, yf - 40 * u, 9 * u, 40 * u, color, rx=3 * u), rect(x + 2 * u, yf - 40 * u, 9 * u, 40 * u, color, rx=3 * u)]
    if arms == "reach":
        s += [line(x - 13 * u, yf - 70 * u, x - 27 * u, yf - 66 * u, color, 7 * u), line(x + 13 * u, yf - 70 * u, x + 27 * u, yf - 66 * u, color, 7 * u)]
    else:
        s += [line(x - 13 * u, yf - 70 * u, x - 18 * u, yf - 44 * u, color, 7 * u), line(x + 13 * u, yf - 70 * u, x + 18 * u, yf - 44 * u, color, 7 * u)]
    return f'<g opacity="{op}">{"".join(s)}</g>'


# ---------------------------------------------------------------- environments

def sky(top="#141a2b", bottom="#2a3350", stars=60, seed=1):
    r = random.Random(seed)
    g = (f'<linearGradient id="sky{seed}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
         f'<stop offset="1" stop-color="{bottom}"/></linearGradient>')
    s = [f"<defs>{g}</defs>", rect(0, 0, W, H, f"url(#sky{seed})")]
    for _ in range(stars):
        s.append(circle(r.uniform(0, W), r.uniform(0, H * 0.45), r.uniform(1, 2.6), "#ffffff", r.uniform(0.3, 0.8)))
    return "".join(s)


def moon(x, y, r=55):
    return glow(x, y, r * 3.2, "Cold", 0.45) + circle(x, y, r, "#e9edf5") + circle(x - r * 0.3, y - r * 0.2, r * 0.18, "#cdd3df") + circle(x + r * 0.25, y + r * 0.3, r * 0.12, "#cdd3df")


def house(x, yb, w, h, wall="#3b4256", roof="#262b3a", lit=(), seed=0, door=True):
    """Row house with gable roof. lit: indices of lit windows."""
    r = random.Random(seed)
    s = [rect(x, yb - h, w, h, wall),
         path(f"M{x - 12},{yb - h} L{x + w / 2},{yb - h - w * 0.38} L{x + w + 12},{yb - h} Z", roof)]
    cols, rows = 2, 2
    ww, wh = w * 0.22, h * 0.2
    k = 0
    for row in range(rows):
        for c in range(cols):
            wx = x + w * (0.18 + c * 0.42)
            wy = yb - h + h * (0.14 + row * 0.36)
            on = k in lit
            s.append(rect(wx, wy, ww, wh, "#ffd27a" if on else "#1c2130", rx=3))
            if on:
                s.append(glow(wx + ww / 2, wy + wh / 2, ww * 1.4, "Warm", 0.35))
            s.append(rect(wx + ww / 2 - 2, wy, 4, wh, shade(wall, 0.8)))
            k += 1
    if door:
        s.append(rect(x + w * 0.42, yb - h * 0.3, w * 0.16, h * 0.3, shade(wall, 0.6), rx=2))
    return "".join(s)


def street(y_top=820, color="#2b2f3b", side="#3a3f4c"):
    s = [rect(0, y_top, W, H - y_top, side), rect(0, y_top + 40, W, H - y_top - 40, color)]
    for i in range(8):
        s.append(rect(60 + i * 210, y_top + 40 + (H - y_top - 40) / 2 - 6, 110, 12, "#c9c39a", op=0.55))
    return "".join(s)


def streetlamp(x, yb, h=420, on=True):
    s = [rect(x - 6, yb - h, 12, h, "#1c1f28"), path(f"M{x},{yb - h} q60,-30 90,0", "none", 1,
                                                       'stroke="#1c1f28" stroke-width="10" stroke-linecap="round"'),
         rect(x + 70, yb - h - 4, 44, 14, "#2a2e3a", rx=4)]
    if on:
        s.append(path(f"M{x + 76},{yb - h + 10} L{x + 108},{yb - h + 10} L{x + 230},{yb} L{x - 46},{yb} Z", "#ffe6a8", 0.12))
        s.append(glow(x + 92, yb - h + 8, 70, "Warm", 0.9))
    return "".join(s)


def tree(x, yb, h=360, col="#1f3328"):
    return (rect(x - 10, yb - h * 0.4, 20, h * 0.4, "#2a2220") + circle(x, yb - h * 0.6, h * 0.25, col)
            + circle(x - h * 0.15, yb - h * 0.48, h * 0.2, shade(col, 0.9)) + circle(x + h * 0.16, yb - h * 0.5, h * 0.19, shade(col, 1.1)))


def car(x, yb, w=380, col="#3f6fa8", lights=False):
    h = w * 0.36
    s = [path(f"M{x},{yb - h * 0.25} L{x + w * 0.1},{yb - h * 0.55} L{x + w * 0.3},{yb - h * 0.6} L{x + w * 0.42},{yb - h} "
              f"L{x + w * 0.78},{yb - h} L{x + w * 0.9},{yb - h * 0.6} L{x + w},{yb - h * 0.5} L{x + w},{yb - h * 0.15} L{x},{yb - h * 0.15} Z", col),
         path(f"M{x + w * 0.46},{yb - h * 0.92} L{x + w * 0.6},{yb - h * 0.92} L{x + w * 0.6},{yb - h * 0.62} L{x + w * 0.36},{yb - h * 0.62} Z", "#9cc4e8", 0.8),
         path(f"M{x + w * 0.64},{yb - h * 0.92} L{x + w * 0.76},{yb - h * 0.92} L{x + w * 0.86},{yb - h * 0.62} L{x + w * 0.64},{yb - h * 0.62} Z", "#9cc4e8", 0.8),
         circle(x + w * 0.22, yb - h * 0.12, h * 0.2, "#16171c"), circle(x + w * 0.78, yb - h * 0.12, h * 0.2, "#16171c"),
         circle(x + w * 0.22, yb - h * 0.12, h * 0.08, "#6b6e78"), circle(x + w * 0.78, yb - h * 0.12, h * 0.08, "#6b6e78")]
    if lights:
        s.append(glow(x + w, yb - h * 0.38, 90, "Warm", 0.8))
    return "".join(s)


def fog(y=700, h=500, op=1):
    return rect(0, y, W, h, "url(#fogUp)", op=op)


def vignette(op=1):
    return rect(0, 0, W, H, "url(#vignette)", op=op)


def rain(n=140, seed=3, op=0.35):
    r = random.Random(seed)
    s = []
    for _ in range(n):
        x, y = r.uniform(0, W), r.uniform(0, H)
        L = r.uniform(18, 40)
        s.append(line(x, y, x - L * 0.25, y + L, "#cfe0ff", 2, op))
    return "".join(s)


# ---------------------------------------------------------------- interiors

def room(wall="#4a4f63", floor="#2f2a2e", floor_y=900, baseboard=True):
    s = [rect(0, 0, W, floor_y, wall), rect(0, floor_y, W, H - floor_y, floor)]
    if baseboard:
        s.append(rect(0, floor_y - 18, W, 18, shade(wall, 0.75)))
    return "".join(s)


def window(x, y, w, h, view="", frame="#d7d9de", curtains=None):
    s = [f'<clipPath id="win{x}{y}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>',
         rect(x - 14, y - 14, w + 28, h + 28, frame, rx=4),
         f'<g clip-path="url(#win{x}{y})">{view}</g>',
         rect(x + w / 2 - 6, y, 12, h, frame), rect(x, y + h / 2 - 6, w, 12, frame)]
    if curtains:
        s.append(path(f"M{x - 40},{y - 30} L{x + w * 0.22},{y - 30} Q{x + w * 0.12},{y + h / 2} {x + w * 0.2},{y + h + 30} L{x - 40},{y + h + 30} Z", curtains))
        s.append(path(f"M{x + w + 40},{y - 30} L{x + w * 0.78},{y - 30} Q{x + w * 0.88},{y + h / 2} {x + w * 0.8},{y + h + 30} L{x + w + 40},{y + h + 30} Z", curtains))
    return "".join(s)


def door(x, yb, w=230, h=470, col="#6b4a36", knob=True, spy=True):
    s = [rect(x - 16, yb - h - 16, w + 32, h + 16, "#d7d9de"), rect(x, yb - h, w, h, col),
         rect(x + 24, yb - h + 30, w - 48, h * 0.38, shade(col, 0.88), rx=4),
         rect(x + 24, yb - h * 0.52, w - 48, h * 0.42, shade(col, 0.88), rx=4)]
    if knob:
        s.append(circle(x + w - 34, yb - h * 0.48, 11, "#d9b25a"))
    if spy:
        s.append(circle(x + w / 2, yb - h * 0.82, 7, "#1a1a1a"))
    return "".join(s)


def bed(x, yb, w=560, col="#5b7aa6"):
    return (rect(x, yb - 170, 40, 170, "#5a4030", rx=6) + rect(x, yb - 90, w, 70, "#5a4030", rx=6)
            + rect(x + 30, yb - 140, w - 40, 60, col, rx=20) + rect(x + 50, yb - 165, 150, 50, "#e8e6ef", rx=20)
            + rect(x + 200, yb - 150, w - 220, 75, shade(col, 0.85), rx=24))


def phone_closeup(cx, cy, scale=1.0, time="06:12", lines=("Kein Netz",), warn=False):
    w, h = 340 * scale, 640 * scale
    x, y = cx - w / 2, cy - h / 2
    s = [rect(x, y, w, h, "#121318", rx=48 * scale), rect(x + 16 * scale, y + 16 * scale, w - 32 * scale, h - 32 * scale,
                                                           "#1d2740" if not warn else "#3a1214", rx=36 * scale)]
    s.append(text(cx, y + 150 * scale, time, int(92 * scale), "#ffffff", 300, family="Montserrat, Arial"))
    yy = y + 260 * scale
    for ln in lines:
        s.append(rect(x + 40 * scale, yy - 44 * scale, w - 80 * scale, 64 * scale, "#ffffff", rx=18 * scale, op=0.12))
        s.append(text(cx, yy, ln, int(28 * scale), "#ffb4b4" if warn else "#ffffff", 700))
        yy += 88 * scale
    return "".join(s)


def radio(cx, cy, scale=1.0, col="#c7662e"):
    w, h = 420 * scale, 260 * scale
    x, y = cx - w / 2, cy - h / 2
    s = [line(x + w * 0.75, y, x + w * 0.95, y - 160 * scale, "#888c96", 6 * scale),
         rect(x, y, w, h, col, rx=34 * scale), rect(x + 26 * scale, y + 30 * scale, w * 0.5, h - 60 * scale, "#2a1d16", rx=18 * scale)]
    for i in range(6):
        for j in range(4):
            s.append(circle(x + 52 * scale + i * 30 * scale, y + 62 * scale + j * 46 * scale, 8 * scale, "#5b4030"))
    s.append(circle(x + w * 0.78, y + h * 0.36, 34 * scale, "#ece2d0"))
    s.append(rect(x + w * 0.64, y + h * 0.62, w * 0.28, 22 * scale, "#2a1d16", rx=8 * scale))
    return "".join(s)


def peephole(inner, op_black=1):
    """Fisheye view: inner is drawn normally, then masked to a circle with a dark rim."""
    return (f'<clipPath id="peep"><circle cx="{W / 2}" cy="{H / 2}" r="470"/></clipPath>'
            + rect(0, 0, W, H, "#050507")
            + f'<g clip-path="url(#peep)">{inner}'
            + f'<circle cx="{W / 2}" cy="{H / 2}" r="470" fill="url(#vignette)"/></g>'
            + f'<circle cx="{W / 2}" cy="{H / 2}" r="470" fill="none" stroke="#000" stroke-width="40" opacity=".8" filter="url(#blur20)"/>')


def hallway(wall="#5a5560", floor="#3c2b2b"):
    """One-point perspective corridor."""
    vx, vy = W / 2, H * 0.45
    s = [rect(0, 0, W, H, wall),
         path(f"M0,{H} L{vx - 160},{vy + 170} L{vx + 160},{vy + 170} L{W},{H} Z", floor),
         path(f"M0,0 L{vx - 160},{vy - 150} L{vx + 160},{vy - 150} L{W},0 Z", shade(wall, 1.15)),
         path(f"M0,0 L{vx - 160},{vy - 150} L{vx - 160},{vy + 170} L0,{H} Z", shade(wall, 0.85)),
         path(f"M{W},0 L{vx + 160},{vy - 150} L{vx + 160},{vy + 170} L{W},{H} Z", shade(wall, 0.8)),
         rect(vx - 160, vy - 150, 320, 320, shade(wall, 0.55)),
         rect(vx - 40, vy - 140, 80, 22, "#3fd47a", rx=4), glow(vx, vy - 130, 90, "Cold", 0.4)]
    # red carpet runner
    s.append(path(f"M{vx - 60},{vy + 170} L{vx + 60},{vy + 170} L{W * 0.66},{H} L{W * 0.34},{H} Z", "#7a2630"))
    return "".join(s)


def stairs(wall="#4b4752", step="#5e5866"):
    s = [rect(0, 0, W, H, wall)]
    for i in range(9):
        y = H - i * 95
        x0 = 200 + i * 70
        s.append(rect(x0, y - 95, W - x0 - 150 + i * 40, 95, shade(step, 1 - i * 0.05)))
        s.append(rect(x0, y - 95, W - x0 - 150 + i * 40, 14, shade(step, 1.15 - i * 0.05)))
    s.append(poly([(150, H - 120), (850, H - 820)], "#2c2a30", 18))
    for i in range(8):
        s.append(line(150 + i * 88, H - 120 - i * 88, 150 + i * 88, H - 40 - i * 88, "#2c2a30", 8))
    return "".join(s)
