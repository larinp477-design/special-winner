"""Text-to-speech backends. Every backend returns mono float32 audio at 48 kHz.

kokoro  English, local, Apache 2.0, good quality
piper   German (Thorsten), local, mediocre quality, fallback only
"""
import hashlib
import io
import os
import subprocess
import wave

import numpy as np

SR = 48000
MODELS = os.environ.get("FV_MODELS", os.path.join(os.path.dirname(__file__), "..", "models"))
CACHE = os.environ.get("FV_CACHE", os.path.join(os.path.dirname(__file__), "..", ".cache"))

_kokoro = None
_piper = None


def _resample(audio, sr):
    """Resample through ffmpeg (soxr) to 48 kHz mono float32."""
    if sr == SR:
        return audio.astype(np.float32)
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
         "-af", "aresample=resampler=soxr", "-ar", str(SR), "-f", "f32le", "-"],
        input=audio.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def _trim(audio, thresh=0.01, pad=0.03):
    """Cut leading and trailing silence, keep a short pad."""
    idx = np.where(np.abs(audio) > thresh)[0]
    if len(idx) == 0:
        return audio
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(audio), idx[-1] + int(pad * SR))
    return audio[a:b]


def _kokoro_synth(text, voice, speed):
    global _kokoro
    from kokoro_onnx import Kokoro
    if _kokoro is None:
        _kokoro = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, sr = _kokoro.create(text, voice=voice, speed=speed, lang=lang)
    return _resample(np.asarray(samples), sr)


def _piper_synth(text, voice, speed):
    global _piper
    from piper import PiperVoice, SynthesisConfig
    if _piper is None:
        _piper = PiperVoice.load(os.path.join(MODELS, f"{voice}.onnx"))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        _piper.synthesize_wav(text, w, syn_config=SynthesisConfig(length_scale=1.0 / speed))
    buf.seek(0)
    with wave.open(buf) as w:
        sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return _resample(pcm.astype(np.float32) / 32768.0, sr)


def _gemini_synth(text, voice, speed):
    """Gemini TTS, German capable. Needs GEMINI_API_KEY. Not tested yet (no key)."""
    import base64
    import json
    import urllib.request
    model = os.environ.get("FV_TTS_MODEL", "gemini-2.5-flash-preview-tts")
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    pcm = base64.b64decode(data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    return _resample(audio, 24000)


BACKENDS = {"kokoro": _kokoro_synth, "piper": _piper_synth, "gemini": _gemini_synth}


def synth(text, backend="kokoro", voice="am_michael", speed=1.0):
    """Speak text, cached on disk by content hash."""
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1(f"{backend}|{voice}|{speed}|{text}".encode()).hexdigest()[:16]
    path = os.path.join(CACHE, key + ".f32")
    if os.path.exists(path):
        return np.fromfile(path, dtype=np.float32)
    audio = _trim(BACKENDS[backend](text, voice, speed))
    peak = np.max(np.abs(audio)) or 1.0
    audio = (audio / peak * 0.89).astype(np.float32)
    audio.tofile(path)
    return audio


def word_times(text, duration):
    """Estimate per-word (start, end) by character weight. Punctuation adds a pause."""
    words = text.split()
    weights = []
    for w in words:
        wt = len(w.strip(".,!?;:")) + 1.5
        if w[-1] in ",;:":
            wt += 2.5
        elif w[-1] in ".!?":
            wt += 4
        weights.append(wt)
    total = sum(weights)
    t, out = 0.0, []
    for w, wt in zip(words, weights):
        d = duration * wt / total
        out.append((w, t, t + d))
        t += d
    return out
