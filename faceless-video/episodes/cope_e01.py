"""Cope to Chad, episode 1 (Day 0): Kevin is introduced, Chat takes over, first quest breakfast.

Cast (keep these exact parameter sets in every episode; Kevin's look changes only through
the explicit progress values below, so the glow-up stays visible and consistent):
  KEVIN  19, grey hoodie, messy brown hair, tired eyes, slouched
  BRAD   neighbour, rival in habits (never bodies), blond, red running shirt, headband
"""
from engine import chars as C
from engine import illus as I

KEVIN = dict(skin="light", hair="#5a4636", style="short", clothes="hoodie", shirt="#6b6f78", pants="#2e3550",
             iris="#5b4a3a", tired=True)
BRAD = dict(skin="light", hair="#d9b25a", style="short", clothes="tshirt", shirt="#c0392b", pants="#2a2d36",
            iris="#3a6a9a", headband="#ffffff", shoes="#e9e9ee")
BG_BLUR = 3.0


def char(depth=1.12, pivot=(800, 1100), breathe=True, **kw):
    lay = {"svg": I.layer_svg(C.person3(**kw)), "depth": depth, "pivot": pivot, "breathe": breathe}
    lay["blink"] = I.layer_svg(C.person3(eyes_closed=True, **kw))
    return lay


def s_scroll():
    """03:12. Dark messy room, Kevin lit only by his phone."""
    bg = I.messy_bedroom() + I.rect(0, 0, I.W, I.H, "#050814", op=0.45)
    kev = char(pivot=(760, 1270), x=760, yf=1270, h=1020, facing=1, mood="neutral", arms="phone",
               rim="#8fc3ff", rim_op=0.45, **KEVIN)
    light = I.layer_svg(I.glow(900, 420, 380, "Cold", 0.35) + I.vignette(0.9))
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0, "blur": BG_BLUR}, kev, {"svg": light, "depth": 1.0}]}


def s_stats():
    """Habit-tracker card over the blurred room."""
    bg = I.messy_bedroom(42) + I.rect(0, 0, I.W, I.H, "#050814", op=0.55)
    card = I.app_card(800, 610, "KEVIN · DAY 0", [
        ("LEVEL", "1", 0.01, "#f2c14e"),
        ("AURA", "3 / 100", 0.03, "#e8444f"),
        ("SLEEP", "3 h", 0.2, "#4cc3f0"),
        ("GYM VISITS THIS YEAR", "0", 0.0, "#48c774"),
        ("SCREEN TIME", "9 h 41 min", 0.95, "#e8444f"),
    ], rank="COPE")
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0, "blur": 8}, {"svg": I.layer_svg(card), "depth": 1.1}]}


def s_mirror():
    """Bathroom mirror: Kevin looks at himself and copes."""
    refl = C.person3(470, 1400, 1150, facing=1, mood="sad", arms="down", **KEVIN)
    bg = I.bathroom() + I.mirror(200, 150, 640, 560, refl)
    kev = char(pivot=(1150, 1320), x=1150, yf=1320, h=1150, facing=-1, mood="sad", arms="down", **KEVIN)
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0, "blur": 2.0}, kev, {"svg": I.layer_svg(I.vignette(0.7)), "depth": 1.0}]}


def s_brad():
    """Through the window at sunrise: Brad is already running."""
    b = I.sky("#7fa8d8", "#f6b97a", stars=0, seed=51) + I.circle(1250, 760, 120, "#ffd9a0", 0.9) + I.glow(1250, 760, 500, "Warm", 0.5)
    for i, wall in enumerate(["#8a7f74", "#9a8e80", "#7f766f", "#958a7c", "#8a7f74"]):
        b += I.house2(-60 + i * 345, 820, 330, 300 + (i % 2) * 30, wall, "#5a4f48", seed=i + 3)
    b += I.hedge(-20, 840, 1700, 80, "#4f6b45") + I.street(820, "#5a5a62", "#8a8a90")
    brad = char(depth=1.08, pivot=(700, 1050), x=700, yf=1050, h=380, facing=1, mood="smile", arms="fists", legs="walk", **BRAD)
    frame = (I.rect(0, 0, I.W, 70, "#efece6") + I.rect(0, I.H - 100, I.W, 100, "#efece6") + I.rect(0, 0, 70, I.H, "#efece6")
             + I.rect(I.W - 70, 0, 70, I.H, "#efece6") + I.rect(I.W / 2 - 18, 0, 36, I.H, "#efece6")
             + I.path("M70,70 L460,70 L70,460 Z", "#ffffff", 0.08))
    return {"layers": [{"svg": I.svg(b), "depth": 1.0}, brad, {"svg": I.layer_svg(frame), "depth": 1.3}]}


def s_notify():
    """Close-up: Kevin's phone gets the challenge notification."""
    bg = I.messy_bedroom(43) + I.rect(0, 0, I.W, I.H, "#050814", op=0.5)
    cx, cy, k = 800, 640, 1.55
    w, h = 340 * k, 640 * k
    x, y = cx - w / 2, cy - h / 2
    ph = I.ellipse(cx - 230, cy + 470, 150, 190, I.shade("#f2c9a6", 0.85)) + I.ellipse(cx + 230, cy + 470, 150, 190, "#f2c9a6")
    ph += I.rect(x - 8, y - 8, w + 16, h + 16, "#2a2b31", rx=60) + I.rect(x, y, w, h, "#0d0e12", rx=54)
    ph += I.rect(x + 18, y + 18, w - 36, h - 36, "#1b2233", rx=42)
    ph += I.text(cx, y + 210, "07:05", 130, "#ffffff", 300)
    ph += I.rect(x + 40, y + 300, w - 80, 250, "#f2c14e", rx=32)
    ph += I.text(x + 70, y + 370, "100-DAY CHALLENGE", 36, "#11151d", 900, anchor="start")
    ph += I.text(x + 70, y + 420, "STARTED", 36, "#11151d", 900, anchor="start")
    ph += I.text(x + 70, y + 480, "Your choices:", 28, "#11151d", 700, anchor="start")
    ph += I.text(x + 70, y + 520, "decided by Chat.", 28, "#11151d", 800, anchor="start")
    ph += I.ellipse(cx + 180, cy + 330, 70, 110, "#f2c9a6") + I.glow(cx, y + 420, 380, "Warm", 0.3)
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0, "blur": 8},
                       {"svg": I.layer_svg(ph), "depth": 1.15, "pivot": (800, 1200), "breathe": True}]}


def s_kitchen():
    """Day one, first quest: open fridge with eggs and kiwi, energy drink on the counter."""
    inside = I.egg_carton(115, 330, n=3) + I.kiwi(150, 520, 30)
    bg = I.kitchen() + I.fridge(80, 930, 360, 760, True, inside) + I.energy_can(1180, 650, 130)
    kev = char(pivot=(820, 1250), x=820, yf=1250, h=1000, facing=-1, mood="neutral", arms="down", **KEVIN)
    return {"layers": [{"svg": I.svg(bg), "depth": 1.0, "blur": BG_BLUR}, kev, {"svg": I.layer_svg(I.vignette(0.5)), "depth": 1.0}]}


SCENES = {"scroll": s_scroll, "stats": s_stats, "mirror": s_mirror, "brad": s_brad, "notify": s_notify, "kitchen": s_kitchen}
