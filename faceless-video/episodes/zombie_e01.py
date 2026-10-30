"""Zombie series, episode 1: "Tag 1. Waltrop." Layered SVG scenes (engine.illus + engine.chars).

Cast (keep these exact parameter sets in every episode, that keeps the characters consistent):
  DU       17, green hoodie, dark blond short hair
  MIA      classmate, dark bob, yellow jacket, blood on the right arm
  KRUEGER  neighbour, bald, blue bathrobe, zombie from episode 1 on
"""
from engine import chars as C
from engine import illus as I

DU = dict(skin="light", hair="#8a6a3e", style="short", clothes="hoodie", shirt="#3f7a4f", pants="#2e3550", iris="#4a6a8a")
MIA = dict(skin="tan", hair="#2b1d16", style="bob", clothes="jacket", shirt="#e0a93a", pants="#3a3550", iris="#5b3a2a")
KRUEGER = dict(hair="#6b6458", style="bald", clothes="robe", shirt="#3e5a8c", pants="#3e5a8c", shoes="#5a4a3a")

DAWN = ("#1e1020", "#8a3a34")


def char(depth=1.12, pivot=(800, 1100), breathe=True, **kw):
    """Character as its own parallax layer, with a blink frame."""
    is_z = kw.pop("zombie", False)
    fn = C.zombie if is_z else C.person
    lay = {"svg": I.layer_svg(fn(**kw)), "depth": depth, "pivot": pivot, "breathe": breathe}
    if not is_z:
        lay["blink"] = I.layer_svg(fn(eyes_closed=True, **kw))
    return lay


def dawn_view(seed=2, krueger=False):
    b = I.sky(*DAWN, stars=25, seed=seed)
    b += I.circle(1180, 700, 170, "#e0703e", 0.6) + I.glow(1180, 700, 600, "Red", 0.4)
    b += I.skyline(640, "#2a1a24", seed) + I.headframe(1320, 650, 380, "#1c1420")
    b += I.powerline(230)
    for i, (wall, lit) in enumerate([("#3a3340", ()), ("#43394a", (2,)), ("#3a3340", ()), ("#46393f", (0,)), ("#3a3340", (3,))]):
        b += I.house2(-60 + i * 345, 820, 330, 300 + (i % 2) * 30, wall, "#21182a", lit=lit, seed=i)
    b += I.hedge(-20, 840, 420) + I.hedge(1180, 840, 460)
    b += I.street(820, "#2a2730", "#3a3540")
    b += I.puddle(520, 1010, 260) + I.puddle(1250, 1090, 200)
    b += I.streetlamp(330, 860, 470, on=False)
    b += I.car(1000, 950, 380, "#4b5d78")
    return b


def s_bedroom():
    """06:12. You stand in your room with the phone, no power, red dawn outside."""
    bg = I.room2("#33384c", "#3a2c2a", floor_y=900, seed=1)
    bg += I.window(140, 160, 500, 420, dawn_view(3), frame="#c9ccd6", curtains="#5a3442")
    bg += I.light_shaft([(150, 600), (640, 600), (1100, 1200), (300, 1200)], "#ff7a5a", 0.16)
    bg += I.shelf(980, 300, 380) + I.poster(745, 330, 190, 250, "#2f4a6a", "RUHRPOTT", "#e9c64a")
    bg += I.desk(980, 900, 460) + I.rug(560, 1080, 760, "#5a2f3a")
    bg += I.nightstand(720, 920, "--:--")
    bg += I.plant(1450, 900, 230)
    bg += I.vignette(0.7)
    du = char(pivot=(470, 1100), x=470, yf=1100, h=600, mood="scared", arms="phone", look=(1, 1), rim="#ff8a6a", rim_op=0.35, **DU)
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0}, du, {"svg": I.layer_svg(I.vignette(0.35)), "depth": 1.0}]}


def s_phone():
    """Close-up: emergency warning on the phone."""
    bg = I.rect(0, 0, I.W, I.H, "#140f18") + I.glow(800, 600, 700, "Red", 0.35)
    bg += I.shelf(100, 260, 420, seed=4).replace('opacity="1"', 'opacity=".25"') + I.vignette(1)
    ph = ""
    cx, cy, k = 800, 610, 1.6
    w, h = 340 * k, 640 * k
    x, y = cx - w / 2, cy - h / 2
    ph += I.ellipse(cx - 230, cy + 470, 150, 190, I.shade("#f2c9a6", 0.85)) + I.ellipse(cx + 230, cy + 470, 150, 190, "#f2c9a6")
    ph += I.rect(x - 8, y - 8, w + 16, h + 16, "#2a2b31", rx=60) + I.rect(x, y, w, h, "#0d0e12", rx=54)
    ph += I.rect(x + 18, y + 18, w - 36, h - 36, "#2a0f14", rx=42)
    ph += I.text(x + 70, y + 74, "Kein Netz", 26, "#ffb4b4", 700, anchor="start")
    ph += I.rect(x + w - 130, y + 52, 60, 28, "none", rx=6, extra='stroke="#ffb4b4" stroke-width="3"') + I.rect(x + w - 124, y + 58, 14, 16, "#ff6a6a", rx=2)
    ph += I.text(cx, y + 230, "06:13", 150, "#ffffff", 300)
    ph += I.rect(x + 50, y + 320, w - 100, 380, "#e8443f", rx=36, op=0.95)
    ph += I.path(f"M{cx},{y + 360} L{cx + 50},{y + 450} L{cx - 50},{y + 450} Z", "#ffffff") + I.text(cx, y + 440, "!", 60, "#e8443f", 900)
    ph += I.text(cx, y + 520, "NOTFALLWARNUNG", 40, "#ffffff", 900)
    ph += I.text(cx, y + 580, "Bleiben Sie in Ihren Häusern.", 30, "#ffffff", 700)
    ph += I.text(cx, y + 625, "Öffnen Sie niemandem.", 30, "#ffffff", 700)
    ph += I.ellipse(cx + 180, cy + 300, 70, 110, "#f2c9a6")
    ph += I.glow(cx, cy, 420, "Red", 0.25)
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0}, {"svg": I.layer_svg(ph), "depth": 1.15, "pivot": (800, 1200), "breathe": True}]}


def s_window():
    """Looking out: Krueger stands in the middle of the road."""
    bg = dawn_view(4) + I.fog(600, 600, 0.9)
    kr = char(depth=1.05, pivot=(560, 1000), x=560, yf=1000, h=290, zombie=True, arms="down", **KRUEGER)
    frame = (I.rect(0, 0, I.W, 80, "#c9ccd6") + I.rect(0, I.H - 110, I.W, 110, "#c9ccd6") + I.rect(0, I.H - 110, I.W, 16, "#a9acb6")
             + I.rect(0, 0, 80, I.H, "#c9ccd6") + I.rect(I.W - 80, 0, 80, I.H, "#c9ccd6") + I.rect(I.W / 2 - 20, 0, 40, I.H, "#c9ccd6")
             + I.path("M80,80 L520,80 L80,520 Z", "#ffffff", 0.05) + I.path("M840,80 L1100,80 L840,340 Z", "#ffffff", 0.05)
             + I.path("M-40,0 L220,0 Q160,600 230,1200 L-40,1200 Z", "#4a2a36") + I.path(f"M{I.W + 40},0 L{I.W - 200},0 Q{I.W - 150},600 {I.W - 210},1200 L{I.W + 40},1200 Z", "#4a2a36"))
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0}, kr,
                       {"svg": I.layer_svg(frame + I.vignette(0.6)), "depth": 1.3}]}


def s_krueger():
    """Close up: Krueger turns his head toward you."""
    bg = I.sky(*DAWN, stars=0, seed=5) + I.glow(800, 820, 700, "Red", 0.45)
    bg += I.skyline(900, "#2a1a24", 7) + I.headframe(260, 900, 420, "#1c1420")
    bg += I.house2(-80, 1100, 460, 560, "#2a2430", "#17121c", seed=6, lit=(1,)) + I.house2(1220, 1100, 460, 560, "#2a2430", "#17121c", seed=7)
    bg += I.fog(800, 400, 0.7)
    kr = char(depth=1.12, pivot=(800, 2500), x=800, yf=2500, h=2250, zombie=True, arms="down", look=(0, 0), rim="#ff6a5a", rim_op=0.3, **KRUEGER)
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0}, kr, {"svg": I.layer_svg(I.fog(900, 300, 0.6) + I.vignette(0.8)), "depth": 1.2}]}


def hallway_bg(seed=8, door_x=685):
    b = I.room2("#4a4552", "#3a2a2a", floor_y=960, seed=seed)
    b += I.door(door_x, 960, 230, 520, "#6b4a36")
    b += I.rect(door_x + 5, 952, 220, 8, "#ffd27a", op=0.8) + I.glow(door_x + 115, 965, 220, "Warm", 0.4)
    b += I.light_shaft([(door_x + 5, 960), (door_x + 225, 960), (door_x + 420, 1200), (door_x - 200, 1200)], "#ffd27a", 0.12)
    hook = 230 if door_x > 500 else 1120
    b += I.rect(hook - 20, 400, 300, 16, "#5a4030")
    for i, c in enumerate(("#7a2f4a", "#2e3550", "#3f7a4f")):
        b += I.circle(hook + 20 + i * 90, 408, 8, "#c9a24a")
        b += I.path(f"M{hook - 10 + i * 90},420 L{hook + 50 + i * 90},420 L{hook + 64 + i * 90},650 L{hook - 24 + i * 90},650 Z", c)
        b += I.rect(hook - 24 + i * 90, 630, 88, 20, I.shade(c, 0.75))
    b += I.rect(hook, 880, 280, 80, "#5a4030") + I.ellipse(hook + 60, 875, 45, 14, "#1d1d24") + I.ellipse(hook + 170, 875, 45, 14, "#3f4a6a")
    b += I.rect(1180 if door_x < 900 else 120, 380, 180, 260, "#c9ccd6", rx=90) + I.rect(1190 if door_x < 900 else 130, 390, 160, 240, "#5a6274", rx=80)
    return b


def s_door():
    """It knocks. Three times."""
    return {"layers": [{"svg": I.svg(hallway_bg() + I.vignette(1)), "depth": 1.0}]}


def s_du_door():
    """You sneak to the door."""
    bg = hallway_bg(9, door_x=1080)
    du = char(pivot=(640, 1110), x=640, yf=1110, h=640, mood="scared", arms="fists", look=(2.2, -0.5), rim="#ffd27a", rim_op=0.25, **DU)
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0}, du, {"svg": I.layer_svg(I.vignette(0.9)), "depth": 1.0}]}


def peephole_inner(closed):
    inner = I.hallway("#4f4a57", "#3c2b2b")
    inner += I.silhouette(905, 690, 150, op=0.9) + I.silhouette(955, 700, 135, op=0.75) + I.silhouette(860, 700, 130, op=0.6)
    inner += C.person(600, 1560, 1200, mood="crying", arms="hold", look=(1, -1), blood=True, eyes_closed=closed, **MIA)
    return I.svg(I.peephole(inner))


def s_peephole():
    """Through the peephole: Mia, bleeding arm, figures at the end of the corridor."""
    return {"layers": [{"svg": peephole_inner(False), "blink": peephole_inner(True), "depth": 1.0}]}


def s_stairs():
    """Stairwell: more and more figures coming up, red emergency light, long shadows."""
    b = I.stairs("#3f3b46", "#55505e")
    for i in range(0, 1600, 80):
        b += I.line(i, 0, i, 520, "#ffffff", 1, 0.04)
    b += I.glow(1300, 160, 420, "Red", 0.6) + I.rect(1250, 125, 100, 46, "#ff3b3b", rx=8) + I.text(1300, 158, "EXIT", 26, "#2a0000", 900)
    for x, y, h in [(560, 760, 520), (760, 700, 480), (960, 640, 450)]:
        b += f'<g transform="skewX(-18)">{I.silhouette(x + 260, y, h, "#000000", 0.35)}</g>'
    for x, y, h in [(620, 1110, 330), (820, 1000, 300), (1020, 900, 280), (1180, 830, 250)]:
        b += I.silhouette(x, y, h, "#0b0c12", 0.95)
    b += I.rect(0, 0, I.W, I.H, "#5a0d14", op=0.2) + I.fog(700, 500, 0.5) + I.vignette(1)
    return {"layers": [{"svg": I.svg(b), "depth": 1.0}]}


def s_banging():
    """Your door from inside, shadows of feet under it, red light."""
    b = hallway_bg(10)
    b += I.rect(720, 940, 70, 14, "#000000", op=0.7) + I.rect(830, 940, 60, 14, "#000000", op=0.7)
    b += I.rect(0, 0, I.W, I.H, "#5a0d14", op=0.22) + I.vignette(1)
    return {"layers": [{"svg": I.svg(b), "depth": 1.0}]}


SCENES = {
    "bedroom": s_bedroom, "phone": s_phone, "window": s_window, "krueger": s_krueger,
    "door": s_door, "du_door": s_du_door, "peephole": s_peephole, "stairs": s_stairs, "banging": s_banging,
}
