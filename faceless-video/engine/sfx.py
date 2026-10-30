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


def knock():
    n = int(1.6 * SR)
    out = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(11)
    for k, at in enumerate((0.0, 0.42, 0.84)):
        m = int(0.18 * SR)
        t = np.arange(m) / SR
        thud = np.sin(2 * np.pi * (95 + 40 * np.exp(-t * 40)) * t) * np.exp(-t * 28)
        click = rng.standard_normal(m) * np.exp(-t * 120) * 0.5
        a = int(at * SR)
        out[a:a + m] += ((thud + click) * 0.8).astype(np.float32)
    return out


def heartbeat():
    n = int(1.0 * SR)
    out = np.zeros(n, dtype=np.float32)
    for at, g in ((0.0, 1.0), (0.22, 0.7)):
        m = int(0.16 * SR)
        t = np.arange(m) / SR
        s = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 30) * g
        a = int(at * SR)
        out[a:a + m] += s.astype(np.float32)
    return out * 0.9


def drone(dur=60.0):
    """Low dark bed under the whole episode: two detuned sines plus slow filtered noise."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 55 * t) * 0.5 + np.sin(2 * np.pi * 55.7 * t) * 0.4 + np.sin(2 * np.pi * 82.4 * t) * 0.15
    rng = np.random.default_rng(5)
    noise = rng.standard_normal(n)
    k = int(SR * 0.004)
    noise = np.convolve(noise, np.ones(k) / k, mode="same") * 3
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)
    out = (s + noise * 0.25) * lfo
    fade = np.minimum(1, np.minimum(t / 2, (dur - t) / 2))
    return (out * fade * 0.09).astype(np.float32)


def alarm():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = np.where((t * 4).astype(int) % 2 == 0, 880, 660)
    s = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.25
    return (s * np.exp(-t * 1.5)).astype(np.float32) * 0.35


def sting():
    """Dark hit for reveals: low boom plus a dissonant high cluster."""
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    low = np.sin(2 * np.pi * (60 * np.exp(-t * 3) + 30) * t) * np.exp(-t * 2.5)
    hi = sum(np.sin(2 * np.pi * f * t) for f in (740, 784, 1046)) * np.exp(-t * 2.2) * 0.12
    return ((low + hi) * 0.6).astype(np.float32)


def steps(n_steps=6, gap=0.55):
    """Slow shuffling steps: short low-passed noise scuffs."""
    rng = np.random.default_rng(21)
    n = int((n_steps * gap + 0.6) * SR)
    out = np.zeros(n, np.float32)
    for k in range(n_steps):
        m = int(0.32 * SR)
        t = np.arange(m) / SR
        x = rng.standard_normal(m)
        y = np.zeros(m)
        acc = 0.0
        for i in range(m):
            acc += 0.08 * (x[i] - acc)
            y[i] = acc
        env = np.minimum(1, t / 0.05) * np.exp(-t * 9)
        a = int((k * gap + rng.uniform(-0.05, 0.05)) * SR)
        a = max(0, a)
        out[a:a + m] += (y * env * 2.2 * rng.uniform(0.6, 1.0)).astype(np.float32)[: n - a]
    return out


def buzz():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * 170 * t) * (np.sin(2 * np.pi * 26 * t) > 0) * ((t % 0.45) < 0.3)
    return (s * 0.35).astype(np.float32)


def rain_amb(dur=10.0):
    rng = np.random.default_rng(31)
    n = int(dur * SR)
    x = rng.standard_normal(n).astype(np.float32)
    k = int(SR * 0.0006)
    x = np.convolve(x, np.ones(k) / k, mode="same")
    fade = np.minimum(1, np.minimum(np.arange(n) / SR / 1.0, (n - np.arange(n)) / SR / 1.0))
    return (x * fade * 0.18).astype(np.float32)


SFX = {"steps": steps, "buzz": buzz, "knock": knock, "heartbeat": heartbeat, "alarm": alarm, "sting": sting, "tick": tick, "pop": pop, "whoosh": whoosh, "boom": boom, "ding": ding}
