"""Sound effects synthesized with numpy, so there is no licence question at all."""
import numpy as np

SR = 48000


def _env(n, attack=0.005, release=None):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1)
    r = np.exp(-t / release) if release else 1.0
    return a * r


def tick():
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 1800 * t) * 0.6 + np.sin(2 * np.pi * 3600 * t) * 0.2
    return (s * _env(n, 0.001, 0.012)).astype(np.float32) * 0.5


def pop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 25) + 180
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return (s * _env(n, 0.002, 0.04)).astype(np.float32) * 0.45


def whoosh(dur=0.45):
    n = int(dur * SR)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    # band sweep: simple one-pole low-pass with moving cutoff
    cut = np.linspace(0.02, 0.35, n) ** 1.5
    y = 0.0
    for i in range(n):
        y += cut[i] * (noise[i] - y)
        out[i] = y
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    out = out * shape
    return (out / (np.max(np.abs(out)) + 1e-9) * 0.35).astype(np.float32)


def boom():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 110 * np.exp(-t * 6) + 38
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    rng = np.random.default_rng(3)
    click = rng.standard_normal(n) * np.exp(-t * 60) * 0.3
    return ((s + click) * _env(n, 0.002, 0.3)).astype(np.float32) * 0.7


def ding():
    n = int(0.8 * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) * a for f, a in [(1320, 0.5), (2640, 0.2), (1980, 0.15)])
    return (s * _env(n, 0.002, 0.25)).astype(np.float32) * 0.35


SFX = {"tick": tick, "pop": pop, "whoosh": whoosh, "boom": boom, "ding": ding}
