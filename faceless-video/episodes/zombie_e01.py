"""Zombie series, episode 1: "Tag 1. Waltrop." Scenes as SVG, drawn with engine.illus.

Cast (keep these exact values in every episode, that is what keeps the characters consistent):
  DU    17, green hoodie, dark blond short hair
  MIA   classmate, dark bob, yellow jacket, blood on the right arm
  KRUEGER neighbour, bald, blue bathrobe, zombie from episode 1 on
"""
from engine import illus as I

DU = dict(skin="light", hair="#8a6a3e", style="short", shirt="#3f7a4f", pants="#2e3550")
MIA = dict(skin="tan", hair="#2b1d16", style="bob", shirt="#e0a93a", pants="#3a3550")
KRUEGER = dict(hair="#3b3a33", style="bald", shirt="#3e5a8c", pants="#3e5a8c")

DAWN_RED = ("#2a1420", "#8a3a34")


def dawn_street(seed=1, zombie_in_road=False, fog=True):
    b = I.sky(*DAWN_RED, stars=20, seed=seed)
    b += I.circle(1250, 760, 160, "#d9673e", 0.55) + I.glow(1250, 760, 520, "Red", 0.35)
    b += I.house(-40, 820, 330, 300, "#2c2f3c", "#1b1d26", lit=(), seed=1)
    b += I.house(300, 820, 330, 330, "#33303b", "#1d1b24", lit=(2,), seed=2)
    b += I.house(640, 820, 330, 300, "#2c2f3c", "#1b1d26", lit=(), seed=3)
    b += I.house(980, 820, 330, 320, "#352f36", "#1f1a20", lit=(), seed=4)
    b += I.house(1320, 820, 330, 300, "#2c2f3c", "#1b1d26", lit=(1,), seed=5)
    b += I.street(820)
    b += I.streetlamp(250, 860, 470, on=False)
    b += I.car(1080, 935, 360, "#4b5d78")
    if zombie_in_road:
        b += I.zombie(760, 1010, 300, **KRUEGER)
    if fog:
        b += I.fog(650, 550)
    return b


def s1_bedroom():
    """06:12, you stand next to the bed, phone without signal, red dawn outside."""
    b = I.room("#363b4e", "#2a2427", floor_y=930)
    view = dawn_street(seed=2)
    b += I.window(160, 170, 520, 420, view, frame="#c9ccd6", curtains="#5a3442")
    b += I.glow(420, 380, 420, "Red", 0.25)
    b += I.rect(1180, 320, 220, 300, "#2e3344", rx=6) + I.rect(1200, 340, 180, 260, "#7a2f4a", rx=4, op=0.5)
    b += I.text(1290, 480, "BVB", 46, "#e9c64a", 900)
    b += I.bed(820, 1000, 640, "#4a6a96")
    b += I.person(560, 1080, 560, mood="scared", arms="phone", look=(1, 1), **DU)
    b += I.vignette(0.9)
    return I.svg(b)


def s2_phone():
    """Closeup phone, emergency warning."""
    b = I.rect(0, 0, I.W, I.H, "#1a1720")
    b += I.glow(800, 600, 600, "Red", 0.35)
    b += I.circle(560, 1130, 140, "#f2c9a6") + I.circle(1040, 1130, 140, "#f2c9a6")
    b += I.phone_closeup(800, 600, 1.55, "06:13", ("Kein Netz", "NOTFALLWARNUNG", "Bleiben Sie zu Hause"), warn=True)
    b += I.vignette(1)
    return I.svg(b)


def s3_window():
    """Looking out of the window: Krueger stands in the middle of the road."""
    b = dawn_street(seed=3, zombie_in_road=True)
    b += I.rect(0, 0, I.W, 70, "#c9ccd6") + I.rect(0, I.H - 90, I.W, 90, "#c9ccd6")
    b += I.rect(0, 0, 70, I.H, "#c9ccd6") + I.rect(I.W - 70, 0, 70, I.H, "#c9ccd6")
    b += I.rect(I.W / 2 - 18, 0, 36, I.H, "#c9ccd6")
    b += I.vignette(0.8)
    return I.svg(b)


def s4_krueger():
    """Close up: Krueger turns his head toward you."""
    b = I.sky(*DAWN_RED, stars=0, seed=4)
    b += I.glow(800, 900, 700, "Red", 0.4)
    b += I.house(-60, 1000, 420, 520, "#24252f", "#17181f", seed=6) + I.house(1240, 1000, 420, 520, "#24252f", "#17181f", seed=7)
    b += I.zombie(800, 2350, 2150, look=(0, 0), **KRUEGER)
    b += I.fog(700, 500, 0.8)
    b += I.vignette(1)
    return I.svg(b)


def s5_door():
    """Your apartment hallway, someone knocks."""
    b = I.room("#4a4552", "#3a2a2a", floor_y=960)
    b += I.door(685, 960, 230, 520, "#6b4a36")
    b += I.rect(690, 952, 220, 8, "#ffd27a", op=0.7) + I.glow(800, 960, 200, "Warm", 0.35)
    for i, c in enumerate(("#7a2f4a", "#2e3550", "#3f7a4f")):
        b += I.line(300 + i * 70, 420, 300 + i * 70, 440, "#2a2a2a", 8)
        b += I.path(f"M{270 + i * 70},{440} L{330 + i * 70},{440} L{340 + i * 70},{640} L{260 + i * 70},{640} Z", c)
    b += I.rect(1120, 760, 260, 200, "#5a4030", rx=6) + I.rect(1150, 700, 80, 60, "#c7662e", rx=10)
    b += I.ellipse(380, 990, 50, 16, "#1d1d24") + I.ellipse(470, 1000, 50, 16, "#1d1d24")
    b += I.vignette(1)
    return I.svg(b)


def s6_peephole():
    """Through the peephole: Mia, bleeding arm, figures at the end of the corridor."""
    inner = I.hallway("#4f4a57", "#3c2b2b")
    inner += I.silhouette(905, 690, 150, op=0.9) + I.silhouette(955, 700, 135, op=0.75) + I.silhouette(860, 700, 130, op=0.6)
    inner += I.person(610, 1520, 1150, mood="crying", arms="hold", look=(1, -1), blood=True, **MIA)
    return I.svg(I.peephole(inner))


def s7_stairs():
    """Stairwell: more and more figures coming up, red emergency light."""
    b = I.stairs("#3f3b46", "#55505e")
    b += I.glow(1300, 160, 380, "Red", 0.55) + I.rect(1260, 130, 80, 40, "#ff3b3b", rx=6)
    for i, (x, y, h) in enumerate([(620, 1110, 330), (820, 1000, 300), (1020, 900, 280), (1180, 830, 250)]):
        b += I.silhouette(x, y, h, "#0b0c12", 0.95)
    b += I.rect(0, 0, I.W, I.H, "#5a0d14", op=0.18)
    b += I.vignette(1)
    return I.svg(b)


def s5b_du_door():
    """You sneak to the door."""
    b = I.room("#4a4552", "#3a2a2a", floor_y=960)
    b += I.door(1050, 960, 230, 520, "#6b4a36")
    b += I.rect(1055, 952, 220, 8, "#ffd27a", op=0.7) + I.glow(1165, 960, 200, "Warm", 0.35)
    b += I.person(700, 1060, 620, mood="scared", arms="hold", look=(2, -0.5), **DU)
    b += I.vignette(1)
    return I.svg(b)


def s8_banging():
    """Door from your side, Mia's shadow under it."""
    b = s5_door().split("<defs>", 1)[1].split("</defs>", 1)[1].rsplit("</svg>", 1)[0]
    b += I.rect(720, 940, 70, 12, "#000000", op=0.6) + I.rect(830, 940, 60, 12, "#000000", op=0.6)
    b += I.rect(0, 0, I.W, I.H, "#5a0d14", op=0.2)
    return I.svg(b)


SCENES = {
    "du_door": s5b_du_door, "banging": s8_banging,
    "bedroom": s1_bedroom, "phone": s2_phone, "window": s3_window, "krueger": s4_krueger,
    "door": s5_door, "peephole": s6_peephole, "stairs": s7_stairs,
}
