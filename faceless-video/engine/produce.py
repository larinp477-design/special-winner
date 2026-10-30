"""One command per episode: generate missing images (character sheet first, then every scene
with the sheet as reference), then render the video.

Usage: python -m engine.produce scripts/zombie_e01.json out/zombie_e01.mp4
"""
import json
import os
import subprocess
import sys

from . import images


def main():
    script_path, out = sys.argv[1], sys.argv[2]
    base = os.path.dirname(os.path.abspath(script_path))
    with open(script_path) as fh:
        script = json.load(fh)
    style = script.get("style", "")
    refs = []
    ch = script.get("character")
    if ch:
        sheet = os.path.join(base, ch["sheet"])
        os.makedirs(os.path.dirname(sheet), exist_ok=True)
        if not os.path.exists(sheet):
            print("character sheet ...")
            images.generate(ch["sheet_prompt"], sheet, aspect="16:9")
        refs.append(sheet)
    for sc in script.get("scenes", []):
        path = os.path.join(base, sc["image"])
        if os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        prompt = sc["prompt"]
        if ch:
            prompt = f"Use the character from the reference sheet ({ch['name']}) exactly as designed. {prompt}"
        print("scene", sc["image"], "...")
        images.generate(f"{prompt}. {style}", path, refs)
    preview = os.path.splitext(out)[0] + "_preview"
    subprocess.run([sys.executable, "-m", "engine.render", script_path, out, preview], check=True)


if __name__ == "__main__":
    main()
