"""Character drawing, version 2: cel shading, rim light, detailed faces and clothes.

person(x, yf, h, ...) draws a front-facing figure with feet at (x, yf).
Clothes: hoodie, jacket, robe, tshirt, uniform. Moods: neutral, scared, shock, crying, shout,
smile, sad, angry. eyes_closed=True draws the blink frame.
"""
import itertools

from . import illus as I

_uid = itertools.count()

SKIN = {"light": "#f2c9a6", "tan": "#d9a27a", "dark": "#8d5a3b", "zombie": "#94a883", "pale": "#e9d9c6"}


def _c(x):
    return f"{x:.1f}"


def person(x, yf, h=440, skin="light", hair="#5a3a22", style="short", shirt="#7a2f4a", pants="#2e3550",
           shoes="#1d1d24", clothes="tshirt", mood="neutral", look=(0, 0), arms="down", zombie=False,
           tear=False, blood=False, eyes_closed=False, iris="#5b4a3a", rim="#ffffff", rim_op=0.0,
           flip=False, extra="", **_):
    uid = next(_uid)
    u = h / 100
    sk = SKIN["zombie"] if zombie else SKIN.get(skin, skin)
    sk_d = I.shade(sk, 0.82)
    hx, hy, hrx, hry = x, yf - 86 * u, 12.5 * u, 13.2 * u
    o = [I.ellipse(x, yf, 19 * u, 3.2 * u, "#000000", 0.32)]

    # long hair behind everything
    if style in ("long",):
        o.append(I.path(f"M{_c(hx - 13.5 * u)},{_c(hy - 3 * u)} Q{_c(hx - 16 * u)},{_c(hy + 24 * u)} {_c(hx - 10 * u)},{_c(hy + 28 * u)} "
                        f"L{_c(hx + 10 * u)},{_c(hy + 28 * u)} Q{_c(hx + 16 * u)},{_c(hy + 24 * u)} {_c(hx + 13.5 * u)},{_c(hy - 3 * u)} Z",
                        I.shade(hair, 0.85)))

    # legs
    for s in (-1, 1):
        lx = x + s * 5.6 * u
        col = pants if s < 0 else I.shade(pants, 0.86)
        o.append(I.rect(lx - 4.3 * u, yf - 43 * u, 8.6 * u, 40 * u, col, rx=3 * u))
        o.append(I.rect(lx - 4.3 * u, yf - 9 * u, 8.6 * u, 3 * u, I.shade(pants, 0.7), rx=1 * u))
        # shoes with sole
        sx0 = lx - 5 * u + s * 0.8 * u
        o.append(I.rect(sx0, yf - 6.5 * u, 10 * u, 6 * u, shoes, rx=2.6 * u))
        o.append(I.rect(sx0, yf - 1.8 * u, 10 * u, 1.8 * u, "#d9d9de", rx=0.9 * u))
    if zombie:
        o.append(I.path(f"M{_c(x + 3 * u)},{_c(yf - 20 * u)} l{_c(3 * u)},{_c(4 * u)} l{_c(-2 * u)},{_c(4 * u)} l{_c(3 * u)},{_c(3 * u)}",
                        "none", 1, f'stroke="{I.shade(pants, 0.55)}" stroke-width="{_c(1.2 * u)}"'))

    # arms
    sh_y = yf - 70 * u
    poses = {
        "down": ([(-17.5, -44), (17.5, -44)], [(-16.5, -57), (16.5, -57)]),
        "up": ([(-24, -104), (24, -104)], [(-23, -82), (23, -82)]),
        "reach": ([(-14, -64), (14, -64)], [(-19, -62), (19, -62)]),
        "reach_side": ([(-27, -65), (27, -65)], [(-21, -67), (21, -67)]),
        "cross": ([(6, -57), (-6, -57)], [(-16, -55), (16, -55)]),
        "wave": ([(-17.5, -44), (26, -100)], [(-16.5, -57), (24, -78)]),
        "phone": ([(-17.5, -44), (5, -80)], [(-16.5, -57), (16, -62)]),
        "hold": ([(-9, -54), (11, -52)], [(-16, -56), (17, -55)]),
        "point": ([(-17.5, -44), (33, -74)], [(-16.5, -57), (23, -72)]),
        "fists": ([(-12, -63), (12, -63)], [(-17, -56), (17, -56)]),
    }
    hands, elbows = poses[arms]
    if flip:
        hands = [(-a, b) for a, b in hands][::-1]
        elbows = [(-a, b) for a, b in elbows][::-1]
    sleeve = I.shade(shirt, 0.9)
    front_arms = arms in ("reach", "cross", "hold", "fists", "phone")
    arm_svg = []
    for s, (hxo, hyo), (ex, ey) in zip((-1, 1), hands, elbows):
        sx = x + s * 11.5 * u
        pts = [(sx, sh_y + 1 * u), (x + ex * u, yf + ey * u), (x + hxo * u, yf + hyo * u)]
        col = sleeve if s < 0 else I.shade(sleeve, 0.88)
        arm_svg.append(I.poly(pts, col, 6.6 * u))
        # cuff
        cx_, cy_ = x + hxo * u, yf + hyo * u
        bx, by = x + ex * u, yf + ey * u
        dx, dy = cx_ - bx, cy_ - by
        L = max(1e-6, (dx * dx + dy * dy) ** 0.5)
        if clothes in ("hoodie", "jacket", "uniform", "robe"):
            arm_svg.append(I.circle(cx_ - dx / L * 3.6 * u, cy_ - dy / L * 3.6 * u, 3.5 * u, I.shade(shirt, 0.72)))
        arm_svg.append(I.circle(cx_, cy_, 3.4 * u, sk if s < 0 else sk_d))
        arm_svg.append(I.circle(cx_ - s * 2.4 * u, cy_ - 1.6 * u, 1.3 * u, sk))
    if not front_arms:
        o += arm_svg

    # torso
    hem = yf - 40 * u
    cid = f"tor{uid}"
    if zombie:
        jag = " ".join(f"L{_c(x + 12 * u - i * 3 * u)},{_c(hem + (3 * u if i % 2 else -0.5 * u))}" for i in range(9))
        tpath = (f"M{_c(x - 11.5 * u)},{_c(sh_y - 3 * u)} Q{_c(x)},{_c(sh_y - 7 * u)} {_c(x + 11.5 * u)},{_c(sh_y - 3 * u)} "
                 f"Q{_c(x + 13.5 * u)},{_c(sh_y)} {_c(x + 13 * u)},{_c(hem)} {jag} L{_c(x - 13 * u)},{_c(hem)} "
                 f"Q{_c(x - 13.5 * u)},{_c(sh_y)} {_c(x - 11.5 * u)},{_c(sh_y - 3 * u)} Z")
    else:
        tpath = (f"M{_c(x - 11.5 * u)},{_c(sh_y - 3 * u)} Q{_c(x)},{_c(sh_y - 7 * u)} {_c(x + 11.5 * u)},{_c(sh_y - 3 * u)} "
                 f"Q{_c(x + 13.5 * u)},{_c(sh_y)} {_c(x + 13 * u)},{_c(hem + 1.5 * u)} Q{_c(x)},{_c(hem + 3.5 * u)} {_c(x - 13 * u)},{_c(hem + 1.5 * u)} "
                 f"Q{_c(x - 13.5 * u)},{_c(sh_y)} {_c(x - 11.5 * u)},{_c(sh_y - 3 * u)} Z")
    o.append(f'<clipPath id="{cid}"><path d="{tpath}"/></clipPath>')
    o.append(I.path(tpath, shirt))
    t = [I.rect(x + 4.5 * u, sh_y - 10 * u, 12 * u, 40 * u, "#000000", op=0.16),
         I.rect(x - 14 * u, sh_y - 10 * u, 2.2 * u, 40 * u, rim, op=rim_op)]
    if clothes == "hoodie":
        t.append(I.rect(x - 8 * u, hem - 12 * u, 16 * u, 10 * u, I.shade(shirt, 0.82), rx=3 * u))
        t.append(I.rect(x - 13 * u, hem - 1.5 * u, 26 * u, 4 * u, I.shade(shirt, 0.72)))
        for s in (-1, 1):
            t.append(I.line(x + s * 2.5 * u, sh_y - 2 * u, x + s * 3 * u, sh_y + 9 * u, "#e8e4da", 0.9 * u))
            t.append(I.circle(x + s * 3 * u, sh_y + 9.5 * u, 0.9 * u, "#e8e4da"))
    elif clothes == "jacket":
        t.append(I.line(x, sh_y - 4 * u, x, hem + 3 * u, I.shade(shirt, 0.55), 0.8 * u))
        t.append(I.rect(x - 10 * u, hem - 10 * u, 6 * u, 1.2 * u, I.shade(shirt, 0.6)))
        t.append(I.rect(x + 4 * u, hem - 10 * u, 6 * u, 1.2 * u, I.shade(shirt, 0.6)))
        t.append(I.rect(x - 13 * u, hem - 1.5 * u, 26 * u, 4 * u, I.shade(shirt, 0.78)))
    elif clothes == "robe":
        t.append(I.path(f"M{_c(x - 6 * u)},{_c(sh_y - 5 * u)} L{_c(x)},{_c(sh_y + 9 * u)} L{_c(x + 6 * u)},{_c(sh_y - 5 * u)} Z", "#d9d2c4"))
        t.append(I.path(f"M{_c(x - 7 * u)},{_c(sh_y - 5 * u)} L{_c(x + 1 * u)},{_c(sh_y + 12 * u)} L{_c(x + 1 * u)},{_c(hem + 3 * u)}", "none", 1,
                        f'stroke="{I.shade(shirt, 0.65)}" stroke-width="{_c(1.6 * u)}"'))
        t.append(I.rect(x - 13 * u, hem - 12 * u, 26 * u, 3.2 * u, I.shade(shirt, 0.7)))
        t.append(I.path(f"M{_c(x + 2 * u)},{_c(hem - 10 * u)} l{_c(-2 * u)},{_c(9 * u)} l{_c(3 * u)},0 Z", I.shade(shirt, 0.7)))
    elif clothes == "uniform":
        t.append(I.rect(x - 13 * u, hem - 6 * u, 26 * u, 3 * u, "#2a2a22"))
        t.append(I.rect(x - 9 * u, sh_y + 3 * u, 6 * u, 5 * u, I.shade(shirt, 0.8), rx=u))
        t.append(I.rect(x + 3 * u, sh_y + 3 * u, 6 * u, 5 * u, I.shade(shirt, 0.8), rx=u))
    else:
        t.append(I.path(f"M{_c(x - 4.5 * u)},{_c(sh_y - 5.5 * u)} Q{_c(x)},{_c(sh_y - 0.5 * u)} {_c(x + 4.5 * u)},{_c(sh_y - 5.5 * u)}",
                        "none", 1, f'stroke="{I.shade(shirt, 0.7)}" stroke-width="{_c(1.2 * u)}"'))
    if zombie:
        t.append(I.ellipse(x - 5 * u, sh_y + 14 * u, 3 * u, 4 * u, "#1a1215", 0.55))
        t.append(I.ellipse(x + 7 * u, sh_y + 4 * u, 4 * u, 3 * u, "#5a1418", 0.75))
        t.append(I.rect(x + 6.2 * u, sh_y + 6 * u, 1.2 * u, 7 * u, "#5a1418", op=0.75))
    if blood:
        t.append(I.ellipse(x + 10 * u, sh_y + 9 * u, 4 * u, 6.5 * u, "#9b1c22", 0.92))
        t.append(I.rect(x + 9.2 * u, sh_y + 13 * u, 1.4 * u, 8 * u, "#9b1c22", op=0.92))
    o.append(f'<g clip-path="url(#{cid})">{"".join(t)}</g>')
    if clothes == "hoodie":
        o.append(I.path(f"M{_c(x - 9 * u)},{_c(sh_y - 3 * u)} Q{_c(x)},{_c(sh_y + 4 * u)} {_c(x + 9 * u)},{_c(sh_y - 3 * u)} "
                        f"Q{_c(x)},{_c(sh_y - 1 * u)} {_c(x - 9 * u)},{_c(sh_y - 3 * u)} Z", I.shade(shirt, 0.75)))
    if front_arms:
        o += arm_svg
    if arms == "phone":
        px, py = x + hands[1][0] * u, yf + hands[1][1] * u
        o.append(I.rect(px - 3.2 * u, py - 9 * u, 6.4 * u, 11 * u, "#121318", rx=u))
        o.append(I.rect(px - 2.5 * u, py - 8.2 * u, 5 * u, 9 * u, "#8fc3ff", rx=0.6 * u, op=0.95))
        o.append(I.glow(px, py - 4 * u, 14 * u, "Cold", 0.5))
        o.append(I.circle(px + 2 * u, py, 3.4 * u, sk))

    # neck
    o.append(I.rect(hx - 3.6 * u, hy + 9 * u, 7.2 * u, 7 * u, sk_d))
    o.append(I.ellipse(hx, hy + 15.5 * u, 4.5 * u, 1.4 * u, "#000000", 0.18))

    # head with crescent shadow
    hid = f"hd{uid}"
    head = [f'<clipPath id="{hid}"><ellipse cx="{_c(hx)}" cy="{_c(hy)}" rx="{_c(hrx)}" ry="{_c(hry)}"/></clipPath>',
            I.ellipse(hx - hrx, hy + 1.5 * u, 2.4 * u, 3.4 * u, sk_d),
            I.ellipse(hx + hrx, hy + 1.5 * u, 2.4 * u, 3.4 * u, I.shade(sk_d, 0.92)),
            I.ellipse(hx, hy, hrx, hry, sk_d),
            f'<g clip-path="url(#{hid})">' + I.ellipse(hx - 2.2 * u, hy - 1.6 * u, hrx * 0.98, hry * 0.98, sk)
            + I.rect(hx - hrx, hy - hry, 1.6 * u, 2 * hry, rim, op=rim_op * 1.2) + "</g>"]
    if zombie:
        head.append(I.ellipse(hx + 5 * u, hy - 7 * u, 3 * u, 2 * u, I.shade(sk, 0.75), 0.8))
        head.append(I.ellipse(hx - 6 * u, hy + 6 * u, 2.4 * u, 1.6 * u, I.shade(sk, 0.75), 0.7))

    # hair
    hl = I.shade(hair, 1.35)
    if style in ("short", "long", "bob", "pigtails"):
        top = (f"M{_c(hx - hrx - 0.8 * u)},{_c(hy + 2 * u)} Q{_c(hx - hrx - 1 * u)},{_c(hy - hry * 1.25)} {_c(hx)},{_c(hy - hry * 1.16)} "
               f"Q{_c(hx + hrx + 1 * u)},{_c(hy - hry * 1.25)} {_c(hx + hrx + 0.8 * u)},{_c(hy + 2 * u)} "
               f"L{_c(hx + hrx - 1 * u)},{_c(hy - 3 * u)} Q{_c(hx + 6 * u)},{_c(hy - 7 * u)} {_c(hx + 3 * u)},{_c(hy - 8.5 * u)} "
               f"L{_c(hx + 1 * u)},{_c(hy - 5.5 * u)} L{_c(hx - 2 * u)},{_c(hy - 8.5 * u)} Q{_c(hx - 8 * u)},{_c(hy - 7 * u)} "
               f"{_c(hx - hrx + 1 * u)},{_c(hy - 3 * u)} Z")
        head.append(I.path(top, hair))
        head.append(I.path(f"M{_c(hx - 7 * u)},{_c(hy - hry * 0.95)} Q{_c(hx - 2 * u)},{_c(hy - hry * 1.12)} {_c(hx + 5 * u)},{_c(hy - hry * 0.98)}",
                           "none", 0.45, f'stroke="{hl}" stroke-width="{_c(1.6 * u)}" stroke-linecap="round"'))
        if style == "bob":
            for s in (-1, 1):
                head.append(I.path(f"M{_c(hx + s * (hrx + 0.8 * u))},{_c(hy - 2 * u)} Q{_c(hx + s * (hrx + 3 * u))},{_c(hy + 8 * u)} "
                                   f"{_c(hx + s * (hrx + 1 * u))},{_c(hy + 11 * u)} L{_c(hx + s * (hrx - 3 * u))},{_c(hy + 10 * u)} Z", hair))
        if style == "pigtails":
            for s in (-1, 1):
                head.append(I.ellipse(hx + s * (hrx + 3.5 * u), hy - 1 * u, 4.5 * u, 6.5 * u, hair))
                head.append(I.circle(hx + s * (hrx + 0.6 * u), hy - 5 * u, 1.6 * u, "#ff6fa8"))
    elif style == "cap":
        head.append(I.path(f"M{_c(hx - hrx - 0.5 * u)},{_c(hy - 4 * u)} Q{_c(hx)},{_c(hy - hry * 1.75)} {_c(hx + hrx + 0.5 * u)},{_c(hy - 4 * u)} Z", hair))
        head.append(I.rect(hx - 4 * u, hy - 6 * u, hrx + 10 * u, 2.6 * u, I.shade(hair, 0.75), rx=u))
    elif style == "helmet":
        head.append(I.path(f"M{_c(hx - hrx - 2 * u)},{_c(hy + 0 * u)} Q{_c(hx)},{_c(hy - hry * 1.7)} {_c(hx + hrx + 2 * u)},{_c(hy + 0 * u)} Z", hair))
        head.append(I.rect(hx - hrx - 2.5 * u, hy - 1 * u, 2 * hrx + 5 * u, 2.4 * u, I.shade(hair, 0.75), rx=u))
    elif style == "bald":
        head.append(I.path(f"M{_c(hx - hrx - 0.3 * u)},{_c(hy + 1 * u)} Q{_c(hx - hrx - 1 * u)},{_c(hy - 5 * u)} {_c(hx - hrx + 2 * u)},{_c(hy - 4 * u)} Z", hair))
        head.append(I.path(f"M{_c(hx + hrx + 0.3 * u)},{_c(hy + 1 * u)} Q{_c(hx + hrx + 1 * u)},{_c(hy - 5 * u)} {_c(hx + hrx - 2 * u)},{_c(hy - 4 * u)} Z", hair))
        head.append(I.ellipse(hx - 4 * u, hy - 9 * u, 4 * u, 1.8 * u, "#ffffff", 0.22))

    # face
    ex, ey = 4.7 * u, hy + 0.8 * u
    big = mood in ("scared", "shock", "crying")
    rx, ry = (3.6 * u, 4.4 * u) if big else (3.1 * u, 3.7 * u)
    for s in (-1, 1):
        cx_ = hx + s * ex
        if zombie:
            head.append(I.ellipse(cx_, ey, rx + 1.4 * u, ry + 1.2 * u, I.shade(sk, 0.6), 0.6))
            head.append(I.ellipse(cx_, ey + 0.4 * u, rx, ry * 0.8, "#efecd0"))
            head.append(I.circle(cx_ + look[0] * 0.5 * u, ey + 0.8 * u, 0.9 * u, "#8a1c1c"))
            head.append(I.path(f"M{_c(cx_ - rx - 0.5 * u)},{_c(ey - 0.4 * u)} Q{_c(cx_)},{_c(ey - ry - 1.6 * u)} {_c(cx_ + rx + 0.5 * u)},{_c(ey - 0.4 * u)} "
                               f"L{_c(cx_ + rx + 0.5 * u)},{_c(ey - ry - 2 * u)} L{_c(cx_ - rx - 0.5 * u)},{_c(ey - ry - 2 * u)} Z", sk))
            continue
        if eyes_closed:
            head.append(I.path(f"M{_c(cx_ - rx)},{_c(ey)} Q{_c(cx_)},{_c(ey + 1.6 * u)} {_c(cx_ + rx)},{_c(ey)}", "none", 1,
                               f'stroke="#2a1a18" stroke-width="{_c(0.9 * u)}" stroke-linecap="round"'))
        else:
            head.append(I.ellipse(cx_, ey, rx, ry, "#ffffff"))
            pr = 1.35 * u if big else 1.8 * u
            px_, py_ = cx_ + look[0] * u, ey + look[1] * u + 0.3 * u
            head.append(I.circle(px_, py_, pr + 0.7 * u, iris))
            head.append(I.circle(px_, py_, pr * 0.75, "#141418"))
            head.append(I.circle(px_ + 0.6 * u, py_ - 0.7 * u, 0.55 * u, "#ffffff"))
            head.append(I.path(f"M{_c(cx_ - rx - 0.3 * u)},{_c(ey - 0.6 * u)} Q{_c(cx_)},{_c(ey - ry - 0.9 * u)} {_c(cx_ + rx + 0.3 * u)},{_c(ey - 0.6 * u)}",
                               "none", 1, f'stroke="#2a1a18" stroke-width="{_c(0.75 * u)}" stroke-linecap="round"'))
        by = ey - ry - 2.1 * u
        bcol = I.shade(hair, 0.75) if style != "bald" else "#8a8070"
        if mood in ("scared", "shock", "crying", "sad"):
            b = (cx_ + s * 3.2 * u, by + 1.2 * u, cx_ - s * 2.3 * u, by - 1.0 * u)
        elif mood == "angry":
            b = (cx_ + s * 3.2 * u, by - 1.0 * u, cx_ - s * 2.3 * u, by + 1.3 * u)
        else:
            b = (cx_ + s * 3.0 * u, by, cx_ - s * 2.5 * u, by - 0.2 * u)
        head.append(I.line(*b, bcol, 1.4 * u))
    # nose and cheeks
    head.append(I.path(f"M{_c(hx - 0.3 * u)},{_c(hy + 2.5 * u)} Q{_c(hx + 1.6 * u)},{_c(hy + 5.2 * u)} {_c(hx - 0.8 * u)},{_c(hy + 5.4 * u)}",
                       "none", 1, f'stroke="{I.shade(sk, 0.7)}" stroke-width="{_c(0.8 * u)}" stroke-linecap="round"'))
    if not zombie:
        for s in (-1, 1):
            head.append(I.ellipse(hx + s * 7.2 * u, hy + 5.2 * u, 2.2 * u, 1.3 * u, "#ff8a80", 0.28))
    my = hy + 8.4 * u
    if zombie:
        head.append(I.path(f"M{_c(hx - 4 * u)},{_c(my - u)} L{_c(hx - 2 * u)},{_c(my + 1.5 * u)} L{_c(hx)},{_c(my - 0.3 * u)} "
                           f"L{_c(hx + 2 * u)},{_c(my + 1.8 * u)} L{_c(hx + 4 * u)},{_c(my - u)} Q{_c(hx)},{_c(my + 4.2 * u)} {_c(hx - 4 * u)},{_c(my - u)} Z", "#3b1416"))
        head.append(I.rect(hx + 2.4 * u, my + 1.4 * u, 0.9 * u, 3.5 * u, "#7a1418", op=0.9))
    elif mood in ("scared", "shock", "shout"):
        o_ = 3.4 if mood == "shout" else 2.3
        head.append(I.ellipse(hx, my + 0.6 * u, o_ * u * 0.85, o_ * u, "#3b1416"))
        head.append(I.ellipse(hx, my + 0.6 * u + o_ * u * 0.55, o_ * u * 0.5, o_ * u * 0.3, "#c2555a"))
        if mood == "shout":
            head.append(I.rect(hx - 2 * u, my - 2.6 * u, 4 * u, 1.2 * u, "#ffffff"))
    elif mood in ("crying", "sad"):
        head.append(I.path(f"M{_c(hx - 3 * u)},{_c(my + 1.5 * u)} Q{_c(hx)},{_c(my - 1.4 * u)} {_c(hx + 3 * u)},{_c(my + 1.5 * u)}",
                           "none", 1, f'stroke="#3b1416" stroke-width="{_c(1.1 * u)}" stroke-linecap="round"'))
    elif mood == "smile":
        head.append(I.path(f"M{_c(hx - 3.5 * u)},{_c(my - 0.5 * u)} Q{_c(hx)},{_c(my + 3 * u)} {_c(hx + 3.5 * u)},{_c(my - 0.5 * u)}",
                           "none", 1, f'stroke="#3b1416" stroke-width="{_c(1.1 * u)}" stroke-linecap="round"'))
    else:
        head.append(I.path(f"M{_c(hx - 2.4 * u)},{_c(my)} Q{_c(hx)},{_c(my + 0.6 * u)} {_c(hx + 2.4 * u)},{_c(my - 0.2 * u)}",
                           "none", 1, f'stroke="#3b1416" stroke-width="{_c(1.0 * u)}" stroke-linecap="round"'))
    if (tear or mood == "crying") and not eyes_closed:
        for s in (-1, 1):
            head.append(I.path(f"M{_c(hx + s * ex)},{_c(ey + ry)} q{_c(-0.9 * u)},{_c(3 * u)} 0,{_c(4.2 * u)} q{_c(0.9 * u)},{_c(-1.2 * u)} 0,{_c(-4.2 * u)} Z", "#8fd0ff"))
            head.append(I.line(hx + s * ex, ey + ry, hx + s * ex - 0.3 * u, ey + ry + 9 * u, "#8fd0ff", 0.7 * u, 0.55))
    tilt = f'transform="rotate(9 {_c(hx)} {_c(hy + 12 * u)})"' if zombie else ""
    o.append(f"<g {tilt}>{''.join(head)}</g>")
    return f"<g {extra}>{''.join(o)}</g>"


def zombie(x, yf, h=430, shirt="#5d6b78", pants="#3a3530", hair="#3b3a33", style="short", **kw):
    kw.setdefault("arms", "reach")
    return person(x, yf, h, shirt=shirt, pants=pants, hair=hair, style=style, zombie=True, **kw)


# ---------------------------------------------------------------- version 3: realistic proportions, 3/4 view

def _grad(gid, col, k_lit=1.12, k_dark=0.78, facing=1):
    """Horizontal gradient: lit on the facing side, darker on the back side."""
    a, b = (I.shade(col, k_dark), I.shade(col, k_lit)) if facing >= 0 else (I.shade(col, k_lit), I.shade(col, k_dark))
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{a}"/>'
            f'<stop offset="1" stop-color="{b}"/></linearGradient>')


def person3(x, yf, h=600, facing=1, skin="light", hair="#5a3a22", style="short", shirt="#3f7a4f", pants="#2e3550",
            shoes="#1d1d24", clothes="hoodie", mood="neutral", arms="down", legs="stand", zombie=False, blood=False,
            eyes_closed=False, glasses=False, look=0.0, rim="#ffffff", rim_op=0.0, iris="#3a2a22", extra="", **_):
    """Standing figure, about 6.3 heads tall, in 3/4 view (facing=1 right, -1 left, 0 front)."""
    uid = next(_uid)
    u = h / 100
    f = facing if facing else 0
    fs = f if f else 1
    sk = SKIN["zombie"] if zombie else SKIN.get(skin, skin)
    defs = [_grad(f"gs{uid}", shirt, facing=fs), _grad(f"gp{uid}", pants, facing=fs), _grad(f"gk{uid}", sk, 1.06, 0.82, fs),
            _grad(f"gh{uid}", hair, 1.25, 0.8, fs)]
    S, P, K, HR = f"url(#gs{uid})", f"url(#gp{uid})", f"url(#gk{uid})", f"url(#gh{uid})"
    o = [f"<defs>{''.join(defs)}</defs>", I.ellipse(x + 2 * u * fs, yf, 14 * u, 2.2 * u, "#000000", 0.35, 'filter="url(#blur8)"')]

    hip_y, sh_y = yf - 47 * u, yf - 79 * u
    # legs: back leg first, darker
    spread = {"stand": (2.6, 0), "walk": (5.5, 4), "wide": (5, 0)}[legs]
    for i, s in enumerate((-1, 1)):
        back = (s == -fs)
        lx = x + s * spread[0] * u * (0.7 if f else 1)
        kx = lx + (spread[1] * u * s * 0.5)
        col = I.shade(pants, 0.72) if back else P
        o.append(I.poly([(x + s * 2.6 * u, hip_y + 2 * u), (kx, yf - 24 * u), (lx, yf - 5 * u)], col, 6.4 * u))
        shoe_col = I.shade(shoes, 0.75) if back else shoes
        toe = 6.2 * u * (fs if f else 0.25 * s)
        o.append(I.path(f"M{_c(lx - 3.2 * u)},{_c(yf)} L{_c(lx - 3.2 * u)},{_c(yf - 4 * u)} Q{_c(lx)},{_c(yf - 6 * u)} {_c(lx + 2.5 * u)},{_c(yf - 4.5 * u)} "
                        f"Q{_c(lx + toe + 2 * u)},{_c(yf - 3 * u)} {_c(lx + toe + 2.6 * u)},{_c(yf)} Z" if fs > 0 or not f else
                        f"M{_c(lx + 3.2 * u)},{_c(yf)} L{_c(lx + 3.2 * u)},{_c(yf - 4 * u)} Q{_c(lx)},{_c(yf - 6 * u)} {_c(lx - 2.5 * u)},{_c(yf - 4.5 * u)} "
                        f"Q{_c(lx + toe - 2 * u)},{_c(yf - 3 * u)} {_c(lx + toe - 2.6 * u)},{_c(yf)} Z", shoe_col))
        o.append(I.rect(min(lx - 3.2 * u, lx + toe - 2.6 * u), yf - 1.2 * u, abs(toe) + 6 * u, 1.2 * u, "#cfcfd4", rx=0.6 * u, op=0.9))

    # arms: hands relative to shoulder joints; first entry is the back arm
    poses = {
        "down": [((-1, 12), (-2, 30)), ((1, 13), (2, 31))],
        "hold": [((2, 13), (3, 19)), ((3, 13), (4, 18))],
        "phone": [((-1, 12), (-2, 30)), ((5, 12), (10, 2))],
        "scared": [((4, 10), (6, -4)), ((5, 10), (8, -5))],
        "reach": [((7, 2), (17, 1)), ((8, 3), (19, 2))],
        "point": [((-1, 12), (-2, 30)), ((9, 4), (22, 0))],
        "fists": [((3, 13), (5, 19)), ((4, 13), (7, 18))],
        "knock": [((-1, 12), (-2, 30)), ((7, 8), (14, 0))],
    }[arms]
    sleeve = shirt
    arm_parts = []
    for i, ((ex, ey), (hx_, hy_)) in enumerate(poses):
        back = (i == 0)
        side = -fs if f else (-1 if back else 1)
        shx = x + side * 7.2 * u if not f else x + (-5.5 if back else 5.5) * u * fs * (-1 if back else 1) * (-1)
        if f:
            shx = x + (5.5 * u if not back else -5.5 * u) * fs
            jx, jy = shx + ex * u * fs, sh_y + ey * u
            hx2, hy2 = shx + hx_ * u * fs, sh_y + hy_ * u
        else:
            shx = x + (-7.5 if back else 7.5) * u
            sd = -1 if back else 1
            jx, jy = shx + abs(ex) * u * sd * 0.6, sh_y + ey * u
            hx2, hy2 = shx + abs(hx_) * u * sd * 0.5, sh_y + hy_ * u
        col = I.shade(sleeve, 0.7) if back else S
        part = I.poly([(shx, sh_y + 2 * u), (jx, jy), (hx2, hy2)], col, 4.8 * u)
        if clothes in ("hoodie", "jacket", "uniform", "robe"):
            dx, dy = hx2 - jx, hy2 - jy
            L = max(1e-6, (dx * dx + dy * dy) ** 0.5)
            part += I.circle(hx2 - dx / L * 2.2 * u, hy2 - dy / L * 2.2 * u, 2.6 * u, I.shade(sleeve, 0.62 if back else 0.8))
        part += I.ellipse(hx2, hy2, 2.1 * u, 2.4 * u, I.shade(sk, 0.8) if back else sk)
        arm_parts.append((back, part, (hx2, hy2)))
    front_pose = arms in ("hold", "phone", "reach", "point", "fists", "knock", "scared")
    o += [p for b, p, _ in arm_parts if b]

    # torso
    w_sh, w_hip = 8.4 * u, 7.0 * u
    tp = (f"M{_c(x - w_sh)},{_c(sh_y + 2 * u)} Q{_c(x - w_sh)},{_c(sh_y - 1.5 * u)} {_c(x - w_sh + 3 * u)},{_c(sh_y - 1.5 * u)} "
          f"L{_c(x + w_sh - 3 * u)},{_c(sh_y - 1.5 * u)} Q{_c(x + w_sh)},{_c(sh_y - 1.5 * u)} {_c(x + w_sh)},{_c(sh_y + 2 * u)} "
          f"L{_c(x + w_hip + 0.6 * u)},{_c(hip_y + 2 * u)} L{_c(x - w_hip - 0.6 * u)},{_c(hip_y + 2 * u)} Z")
    if zombie:
        jag = " ".join(f"L{_c(x + w_hip - i * 2 * u)},{_c(hip_y + (3.2 * u if i % 2 else 0.8 * u))}" for i in range(8))
        tp = (f"M{_c(x - w_sh)},{_c(sh_y + 2 * u)} Q{_c(x - w_sh)},{_c(sh_y - 1.5 * u)} {_c(x - w_sh + 3 * u)},{_c(sh_y - 1.5 * u)} "
              f"L{_c(x + w_sh - 3 * u)},{_c(sh_y - 1.5 * u)} Q{_c(x + w_sh)},{_c(sh_y - 1.5 * u)} {_c(x + w_sh)},{_c(sh_y + 2 * u)} "
              f"L{_c(x + w_hip + 0.6 * u)},{_c(hip_y + 2 * u)} {jag} L{_c(x - w_hip - 0.6 * u)},{_c(hip_y + 2 * u)} Z")
    cid = f"t3{uid}"
    o.append(f'<clipPath id="{cid}"><path d="{tp}"/></clipPath>')
    o.append(I.path(tp, S))
    t = [I.rect(x - w_sh - 2 * u, hip_y - 4 * u, 2 * w_sh + 4 * u, 6 * u, "#000000", op=0.12),
         I.rect(x - fs * w_sh - (1.2 * u if fs > 0 else 0), sh_y - 2 * u, 1.4 * u, 40 * u, rim, op=rim_op)]
    if clothes == "hoodie":
        t.append(I.rect(x - 4.5 * u + fs * 1.5 * u, hip_y - 8 * u, 9 * u, 6.5 * u, I.shade(shirt, 0.82), rx=1.5 * u))
        for s in (-1, 1):
            t.append(I.line(x + fs * 1.2 * u + s * 1.4 * u, sh_y - 0.5 * u, x + fs * 1.2 * u + s * 1.6 * u, sh_y + 7 * u, "#e8e4da", 0.55 * u))
    elif clothes == "jacket":
        t.append(I.line(x + fs * 1.5 * u, sh_y - 1 * u, x + fs * 1.5 * u, hip_y + 2 * u, I.shade(shirt, 0.55), 0.6 * u))
        t.append(I.rect(x - w_hip, hip_y - 1 * u, 2 * w_hip, 3 * u, I.shade(shirt, 0.75)))
    elif clothes == "robe":
        t.append(I.path(f"M{_c(x - 2.5 * u + fs * u)},{_c(sh_y - 1.5 * u)} L{_c(x + fs * u)},{_c(sh_y + 8 * u)} L{_c(x + 3 * u + fs * u)},{_c(sh_y - 1.5 * u)} Z", "#d9d2c4"))
        t.append(I.rect(x - w_hip - u, hip_y - 9 * u, 2 * w_hip + 2 * u, 2.4 * u, I.shade(shirt, 0.7)))
    elif clothes == "uniform":
        t.append(I.rect(x - w_hip - u, hip_y - 3 * u, 2 * w_hip + 2 * u, 2.4 * u, "#2a2a22"))
    if zombie:
        t.append(I.ellipse(x + 2 * u, sh_y + 10 * u, 2.5 * u, 3 * u, "#1a1215", 0.5))
        t.append(I.ellipse(x - 3 * u, sh_y + 4 * u, 3 * u, 2 * u, "#5a1418", 0.75))
    if blood:
        t.append(I.ellipse(x + fs * 5 * u, sh_y + 8 * u, 2.6 * u, 4.5 * u, "#9b1c22", 0.92))
    o.append(f'<g clip-path="url(#{cid})">{"".join(t)}</g>')
    if clothes == "hoodie":
        o.append(I.path(f"M{_c(x - 5 * u)},{_c(sh_y - 1 * u)} Q{_c(x + fs * u)},{_c(sh_y + 3.5 * u)} {_c(x + 5 * u)},{_c(sh_y - 1 * u)} "
                        f"Q{_c(x)},{_c(sh_y + 0.8 * u)} {_c(x - 5 * u)},{_c(sh_y - 1 * u)} Z", I.shade(shirt, 0.72)))
    o += [p for b, p, _ in arm_parts if not b]
    if arms == "phone":
        px, py = arm_parts[1][2]
        o.append(I.rect(px - 1.8 * u + fs * u, py - 5.5 * u, 3.6 * u, 6.5 * u, "#121318", rx=0.6 * u))
        o.append(I.glow(px + fs * 3 * u, py - 3 * u, 9 * u, "Cold", 0.55))

    # neck and head
    hx, hy = x + fs * (2.0 if zombie else 1.0) * u, yf - (88.5 if zombie else 91) * u
    rx, ry = 6.6 * u, 7.9 * u
    o.append(I.rect(hx - 2.2 * u - fs * 0.6 * u, hy + 5 * u, 4.4 * u, 6 * u, I.shade(sk, 0.78)))
    hd = []
    hid = f"h3{uid}"
    jaw = (f"M{_c(hx - rx)},{_c(hy - 1 * u)} Q{_c(hx - rx)},{_c(hy - ry)} {_c(hx)},{_c(hy - ry)} Q{_c(hx + rx)},{_c(hy - ry)} {_c(hx + rx)},{_c(hy - 1 * u)} "
           f"Q{_c(hx + rx * (0.95 if fs > 0 else 0.85))},{_c(hy + 5.5 * u)} {_c(hx + fs * 2.6 * u)},{_c(hy + ry)} "
           f"Q{_c(hx - fs * 2 * u)},{_c(hy + ry * 0.95)} {_c(hx - rx * (0.95 if fs < 0 else 0.85))},{_c(hy + 4 * u)} Z")
    hd.append(f'<clipPath id="{hid}"><path d="{jaw}"/></clipPath>')
    if style not in ("bald",):
        hd.append(I.ellipse(hx - fs * 1.2 * u, hy - 1.5 * u, rx + 0.8 * u, ry + 0.4 * u, I.shade(hair, 0.85)))
    hd.append(I.path(jaw, K))
    hd.append(f'<g clip-path="url(#{hid})">' + I.rect(hx - rx, hy + 2 * u, 2 * rx, ry, "#000000", op=0.08)
              + I.rect(hx - fs * rx - (1.2 * u if fs > 0 else 0), hy - ry, 1.2 * u, 2 * ry, rim, op=rim_op * 1.3) + "</g>")
    # ear on the back side
    if f:
        hd.append(I.ellipse(hx - fs * 4.6 * u, hy + 0.8 * u, 1.3 * u, 2 * u, I.shade(sk, 0.82)))
    else:
        for s in (-1, 1):
            hd.append(I.ellipse(hx + s * rx, hy + 0.8 * u, 1.2 * u, 1.9 * u, I.shade(sk, 0.85)))
    # hair
    if style == "short":
        hd.append(I.path(f"M{_c(hx - rx - 0.6 * u)},{_c(hy + 0.5 * u)} Q{_c(hx - rx - 0.8 * u)},{_c(hy - ry - 2 * u)} {_c(hx + fs * 1 * u)},{_c(hy - ry - 1.6 * u)} "
                         f"Q{_c(hx + rx + 1 * u)},{_c(hy - ry - 1 * u)} {_c(hx + rx + 0.4 * u)},{_c(hy - 3 * u)} "
                         f"Q{_c(hx + fs * 3 * u)},{_c(hy - 5.8 * u)} {_c(hx - fs * 1 * u)},{_c(hy - 4.4 * u)} "
                         f"Q{_c(hx - fs * 4 * u)},{_c(hy - 3.5 * u)} {_c(hx - fs * 4.2 * u)},{_c(hy + 0.5 * u)} Z", HR))
    elif style == "bob":
        hd.append(I.path(f"M{_c(hx - rx - 1.2 * u)},{_c(hy + 6 * u)} Q{_c(hx - rx - 1.6 * u)},{_c(hy - ry - 2 * u)} {_c(hx)},{_c(hy - ry - 1.6 * u)} "
                         f"Q{_c(hx + rx + 1.6 * u)},{_c(hy - ry - 2 * u)} {_c(hx + rx + 1.2 * u)},{_c(hy + 6 * u)} L{_c(hx + rx - 1 * u)},{_c(hy + 5 * u)} "
                         f"Q{_c(hx + rx - 0.5 * u)},{_c(hy - 3 * u)} {_c(hx + fs * 1 * u)},{_c(hy - 5 * u)} Q{_c(hx - rx + 0.5 * u)},{_c(hy - 3 * u)} {_c(hx - rx + 1 * u)},{_c(hy + 5 * u)} Z", HR))
    elif style == "long":
        hd.append(I.path(f"M{_c(hx - rx - 1.2 * u)},{_c(hy + 12 * u)} Q{_c(hx - rx - 1.8 * u)},{_c(hy - ry - 2 * u)} {_c(hx)},{_c(hy - ry - 1.6 * u)} "
                         f"Q{_c(hx + rx + 1.8 * u)},{_c(hy - ry - 2 * u)} {_c(hx + rx + 1.2 * u)},{_c(hy + 12 * u)} L{_c(hx + rx - 1 * u)},{_c(hy + 8 * u)} "
                         f"Q{_c(hx + rx - 0.5 * u)},{_c(hy - 3 * u)} {_c(hx + fs * 1 * u)},{_c(hy - 5 * u)} Q{_c(hx - rx + 0.5 * u)},{_c(hy - 3 * u)} {_c(hx - rx + 1 * u)},{_c(hy + 8 * u)} Z", HR))
    elif style == "bald":
        hd.append(I.path(f"M{_c(hx - fs * rx - fs * 0.3 * u)},{_c(hy + 2 * u)} Q{_c(hx - fs * (rx + 0.6 * u))},{_c(hy - 3 * u)} {_c(hx - fs * (rx - 2.5 * u))},{_c(hy - 3.6 * u)} Z", hair))
        hd.append(I.ellipse(hx + fs * 1 * u, hy - ry + 2.2 * u, 3 * u, 1.2 * u, "#ffffff", 0.22))
    elif style == "helmet":
        hd.append(I.path(f"M{_c(hx - rx - 1.5 * u)},{_c(hy - 0.5 * u)} Q{_c(hx)},{_c(hy - ry - 4.5 * u)} {_c(hx + rx + 1.5 * u)},{_c(hy - 0.5 * u)} Z", HR))
    # face
    if f:
        eyes = [(hx + fs * 0.6 * u, 0.85), (hx + fs * 4.4 * u, 1.0)]
    else:
        eyes = [(hx - 2.7 * u, 1.0), (hx + 2.7 * u, 1.0)]
    ey = hy + 0.2 * u
    big = mood in ("scared", "shock")
    erx, ery = (1.35 * u, 1.75 * u) if big else (1.15 * u, 1.35 * u)
    for (ex, k) in eyes:
        if zombie:
            hd.append(I.ellipse(ex, ey, erx * k * 1.6, ery * 1.4, I.shade(sk, 0.55), 0.6))
            hd.append(I.ellipse(ex, ey, erx * k, ery * 0.85, "#eeeacb"))
            hd.append(I.circle(ex + fs * 0.2 * u, ey + 0.2 * u, 0.45 * u, "#7a1c1c"))
        elif eyes_closed:
            hd.append(I.line(ex - erx * k, ey + 0.3 * u, ex + erx * k, ey + 0.3 * u, "#2a1a18", 0.45 * u))
        else:
            hd.append(I.ellipse(ex, ey, erx * k, ery, "#f6f3ee"))
            hd.append(I.circle(ex + (fs * 0.35 + look) * u, ey + 0.1 * u, 0.85 * u, iris))
            hd.append(I.circle(ex + (fs * 0.35 + look) * u, ey + 0.1 * u, 0.45 * u, "#121214"))
            hd.append(I.circle(ex + (fs * 0.35 + look) * u + 0.3 * u, ey - 0.35 * u, 0.22 * u, "#ffffff"))
            hd.append(I.path(f"M{_c(ex - erx * k - 0.2 * u)},{_c(ey - 0.3 * u)} Q{_c(ex)},{_c(ey - ery - 0.4 * u)} {_c(ex + erx * k + 0.2 * u)},{_c(ey - 0.3 * u)}",
                             "none", 1, f'stroke="#2a1a18" stroke-width="{_c(0.42 * u)}" stroke-linecap="round"'))
        bcol = I.shade(hair, 0.7) if style != "bald" else "#8a8070"
        by = ey - ery - 1.1 * u
        tilt_in = {"scared": -0.7, "shock": -0.9, "sad": -0.6, "angry": 0.8}.get(mood, 0)
        sgn = 1 if ex > hx else -1
        hd.append(I.line(ex - 1.4 * u * k, by - tilt_in * sgn * 0.5 * u, ex + 1.4 * u * k, by + tilt_in * sgn * 0.5 * u, bcol, 0.5 * u))
    if glasses and not zombie:
        for (ex, k) in eyes:
            hd.append(I.rect(ex - 2 * u * k, ey - 1.7 * u, 4 * u * k, 3.3 * u, "none", rx=0.8 * u,
                             extra=f'stroke="#1e1e24" stroke-width="{_c(0.45 * u)}"'))
        hd.append(I.line(eyes[0][0] + 2 * u * eyes[0][1] * (1 if eyes[1][0] > eyes[0][0] else -1), ey - 0.6 * u,
                         eyes[1][0] - 2 * u * (1 if eyes[1][0] > eyes[0][0] else -1), ey - 0.6 * u, "#1e1e24", 0.45 * u))
    # nose
    if f:
        nx = hx + fs * (rx - 0.2 * u)
        hd.append(I.path(f"M{_c(nx - fs * 1.2 * u)},{_c(hy - 0.5 * u)} Q{_c(nx + fs * 1.4 * u)},{_c(hy + 3.2 * u)} {_c(nx - fs * 0.6 * u)},{_c(hy + 3.6 * u)} Z", I.shade(sk, 0.92)))
    else:
        hd.append(I.path(f"M{_c(hx)},{_c(hy + 0.8 * u)} Q{_c(hx + 1 * u)},{_c(hy + 3.2 * u)} {_c(hx - 0.6 * u)},{_c(hy + 3.4 * u)}", "none", 1,
                         f'stroke="{I.shade(sk, 0.7)}" stroke-width="{_c(0.45 * u)}" stroke-linecap="round"'))
    mx, my = hx + fs * 2.6 * u if f else hx, hy + 5.3 * u
    if zombie:
        hd.append(I.path(f"M{_c(mx - 2 * u)},{_c(my - 0.3 * u)} L{_c(mx - u)},{_c(my + 0.9 * u)} L{_c(mx)},{_c(my)} L{_c(mx + u)},{_c(my + 1 * u)} L{_c(mx + 2 * u)},{_c(my - 0.3 * u)} "
                         f"Q{_c(mx)},{_c(my + 2.4 * u)} {_c(mx - 2 * u)},{_c(my - 0.3 * u)} Z", "#3b1416"))
        hd.append(I.rect(mx + 0.8 * u, my + 0.9 * u, 0.5 * u, 2.2 * u, "#7a1418", op=0.9))
    elif mood in ("scared", "shock", "shout"):
        hd.append(I.ellipse(mx, my + 0.3 * u, 1.1 * u, 1.4 * u if mood != "shout" else 1.9 * u, "#3b1416"))
    elif mood in ("sad", "crying"):
        hd.append(I.path(f"M{_c(mx - 1.6 * u)},{_c(my + 0.8 * u)} Q{_c(mx)},{_c(my - 0.6 * u)} {_c(mx + 1.6 * u)},{_c(my + 0.8 * u)}", "none", 1,
                         f'stroke="#3b1416" stroke-width="{_c(0.5 * u)}" stroke-linecap="round"'))
    else:
        hd.append(I.line(mx - 1.5 * u, my, mx + 1.4 * u, my - 0.1 * u, "#3b1416", 0.5 * u))
    if mood == "crying" and not eyes_closed:
        for (ex, k) in eyes:
            hd.append(I.line(ex, ey + ery, ex - 0.2 * u, ey + ery + 4.5 * u, "#8fd0ff", 0.45 * u, 0.8))
    tilt = f'transform="rotate({8 * fs} {_c(hx)} {_c(hy + 8 * u)})"' if zombie else ""
    o.append(f"<g {tilt}>{''.join(hd)}</g>")
    return f"<g {extra}>{''.join(o)}</g>"


def zombie3(x, yf, h=600, shirt="#5d6b78", pants="#3a3530", hair="#3b3a33", style="short", **kw):
    kw.setdefault("arms", "reach")
    return person3(x, yf, h, shirt=shirt, pants=pants, hair=hair, style=style, zombie=True, **kw)
