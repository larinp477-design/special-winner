"""Image generation through the Gemini API, with optional reference images for a fixed character.

Needs GEMINI_API_KEY in the environment (paid tier, the free tier is not allowed for EEA users).
Not tested yet: there was no key when this was written.

Usage: python -m engine.images "prompt" out.png [ref1.png ref2.png ...]
"""
import base64
import json
import mimetypes
import os
import sys
import urllib.request

MODEL = os.environ.get("FV_IMAGE_MODEL", "gemini-2.5-flash-image")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def generate(prompt, out_path, refs=(), aspect="9:16"):
    key = os.environ["GEMINI_API_KEY"]
    parts = [{"text": prompt}]
    for r in refs:
        mime = mimetypes.guess_type(r)[0] or "image/png"
        with open(r, "rb") as fh:
            parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(fh.read()).decode()}})
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}},
    }
    req = urllib.request.Request(URL.format(model=MODEL), data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    for part in data["candidates"][0]["content"]["parts"]:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            with open(out_path, "wb") as fh:
                fh.write(base64.b64decode(inline["data"]))
            return out_path
    raise RuntimeError("no image in response: " + json.dumps(data)[:500])


if __name__ == "__main__":
    generate(sys.argv[1], sys.argv[2], sys.argv[3:])
