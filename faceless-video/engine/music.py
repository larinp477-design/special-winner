"""Procedural tension score, synthesized with numpy. No samples, so no licence question.

score(dur, curve, hits) builds a dark cinematic bed:
  pad      detuned saw chords (D minor: i, VI, iv, V), filtered, slow attack
  pulse    low D pulse like a heartbeat, comes in with intensity
  pluck    Karplus-Strong arpeggio, only at high intensity
  risers   noise and pitch sweep into every hit, then a sub impact
All of it through one synthetic hall reverb. curve: [(time, 0..1)] intensity over time.
"""
import numpy as np

SR = 48000
BPM = 72
BEAT = 60 / BPM
CHORDS = [  # D minor: Dm, Bb, Gm, A (midi notes)
    [50, 53, 57, 62], [46, 50, 53, 58], [43, 50, 55, 58], [45, 49, 52, 57],
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass_fft(x, cutoff, slope=2.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** (2 * slope)) ** 0.5
    return np.fft.irfft(X, len(x)).astype(np.float32)


def highpass_fft(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (f / cutoff) ** 2 / (1 + (f / cutoff) ** 2)
    return np.fft.irfft(X, len(x)).astype(np.float32)


def reverb(x, seconds=2.6, wet=0.35, seed=4):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 6.9 / seconds)
    ir = lowpass_fft(ir, 5000)
    ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    m = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return (x * (1 - wet) + y * wet * 1.6).astype(np.float32)


def saw(freq, n, phase=0.0):
    t = np.arange(n) / SR
    return (2 * ((t * freq + phase) % 1.0) - 1).astype(np.float32)


def pluck(freq, dur, decay=0.996, seed=0):
    n = int(dur * SR)
    N = max(2, int(SR / freq))
    rng = np.random.default_rng(seed)
    buf = rng.uniform(-1, 1, N).astype(np.float32)
    out = np.zeros(n, np.float32)
    out[:N] = buf
    i = N
    while i < n:
        k = min(N, n - i)
        prev = out[i - N:i - N + k]
        prev2 = out[i - N - 1:i - N - 1 + k] if i - N - 1 >= 0 else np.concatenate([[0.0], out[i - N:i - N + k - 1]])
        out[i:i + k] = decay * 0.5 * (prev + prev2)
        i += k
    return out


def interp_curve(curve, n):
    t = np.arange(n) / SR
    xs = [c[0] for c in curve]
    ys = [c[1] for c in curve]
    return np.interp(t, xs, ys).astype(np.float32)


def score(dur, curve=((0, 0.4),), hits=(), seed=1):
    n = int(dur * SR)
    inten = interp_curve(list(curve), n)
    out = np.zeros(n, np.float32)
    bar = 4 * BEAT
    # pad, two bars per chord
    seg = int(2 * bar * SR)
    k = 0
    for start in range(0, n, seg):
        m = min(seg + int(1.5 * SR), n - start)
        chord = CHORDS[k % len(CHORDS)]
        s = np.zeros(m, np.float32)
        for note in chord:
            for det in (-0.12, 0.0, 0.11):
                s += saw(hz(note + det), m, phase=np.random.default_rng(note).random()) * 0.06
        s += np.sin(2 * np.pi * hz(chord[0] - 12) * np.arange(m) / SR).astype(np.float32) * 0.18
        s = lowpass_fft(s, 700 + 500 * float(inten[min(start, n - 1)]))
        env = np.minimum(1, np.arange(m) / (1.2 * SR)) * np.minimum(1, (m - np.arange(m)) / (1.5 * SR))
        out[start:start + m] += s * env
        k += 1
    # low pulse on every beat, louder with intensity
    pulse_len = int(0.35 * SR)
    tt = np.arange(pulse_len) / SR
    pulse = (np.sin(2 * np.pi * (hz(38) + 30 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)).astype(np.float32)
    b = 0.0
    while b < dur:
        i = int(b * SR)
        g = max(0.0, float(inten[min(i, n - 1)]) - 0.35) * 1.4
        if g > 0:
            e = min(n, i + pulse_len)
            out[i:e] += pulse[: e - i] * 0.55 * g
        b += BEAT
    # pluck arpeggio in eighths when it gets tense
    arp = [62, 65, 69, 74, 69, 65]
    b, j = 0.0, 0
    while b < dur:
        i = int(b * SR)
        g = max(0.0, float(inten[min(i, n - 1)]) - 0.55) * 2.2
        if g > 0:
            chord = CHORDS[int(b / (2 * bar)) % len(CHORDS)]
            note = arp[j % len(arp)] - 62 + chord[0] + 12
            p = pluck(hz(note), 1.2, seed=j)
            e = min(n, i + len(p))
            out[i:e] += p[: e - i] * 0.16 * g
        b += BEAT / 2
        j += 1
    # risers into hits, then impact
    for h in hits:
        rl = 1.8
        a, e = int(max(0, h - rl) * SR), int(h * SR)
        if e > a:
            m = e - a
            t = np.arange(m) / SR
            rng = np.random.default_rng(int(h * 10))
            noise = rng.standard_normal(m).astype(np.float32)
            noise = highpass_fft(noise, 800) * (t / rl) ** 3 * 0.25
            f = 200 * 2 ** (2 * t / rl)
            tone = np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32) * (t / rl) ** 2 * 0.12
            out[a:e] += noise + tone
        il = int(1.6 * SR)
        t = np.arange(il) / SR
        imp = (np.sin(2 * np.pi * (30 + 70 * np.exp(-t * 8)) * t) * np.exp(-t * 2.5)).astype(np.float32) * 0.9
        e2 = min(n, e + il)
        out[e:e2] += imp[: e2 - e]
    out = reverb(out, 3.0, 0.4, seed)
    out = highpass_fft(out, 28)
    peak = np.max(np.abs(out)) or 1
    return (out / peak * 0.5).astype(np.float32)
