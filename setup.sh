#!/usr/bin/env bash
# Installs everything the reaction-format editor needs. Safe to run more than once.
# Cloud environment: set "bash setup.sh" (run from the repo root) as the environment's Setup script.
set -euo pipefail

pip install -q --root-user-action=ignore faster-whisper onnxruntime opencv-contrib-python-headless pillow fonttools numpy

MODELS="${REACTION_MODELS:-$HOME/.cache/reaction-format/models}"
mkdir -p "$MODELS"
for m in rvm_resnet50_fp32 rvm_mobilenetv3_fp32; do
  [ -s "$MODELS/$m.onnx" ] || curl -fsSL -o "$MODELS/$m.onnx" \
    "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/$m.onnx"
done

# speech-to-text model (needs huggingface.co, *.hf.co allowed in the environment's network settings)
python3 -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')" \
  || echo "WARNING: could not download the speech model; check the Hugging Face domains are allowed"

command -v ffmpeg >/dev/null || echo "WARNING: ffmpeg is not installed"
echo "reaction-format setup done"
