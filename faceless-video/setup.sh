#!/usr/bin/env bash
# Installs the Python packages and downloads the voice models (from GitHub releases,
# because huggingface.co is blocked in the cloud environment).
set -euo pipefail
cd "$(dirname "$0")"
pip install -q piper-tts kokoro-onnx soundfile pillow numpy
mkdir -p models
get() { [ -f "models/$2" ] || curl -sSL --retry 4 -C - -o "models/$2" "$1"; }
get https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx kokoro-v1.0.onnx
get https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin voices-v1.0.bin
if [ ! -f models/de-thorsten-low.onnx ]; then
  curl -sSL --retry 4 https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-de-thorsten-low.tar.gz | tar xz -C models
fi
echo "ok"
