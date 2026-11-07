#!/usr/bin/env bash
# Saca las texturas y el sonido del video y empaqueta DeathAnimation.mcaddon
# Uso: ./tools/build.sh ruta/al/video.mp4
set -euo pipefail
cd "$(dirname "$0")/.."
if [ $# -eq 1 ]; then python3 tools/extract_from_video.py "$1"; fi
python3 tools/make_ui.py
python3 tools/make_preview.py
rm -f DeathAnimation.mcaddon
zip -qr DeathAnimation.mcaddon DeathAnimation_BP DeathAnimation_RP
echo "Creado DeathAnimation.mcaddon"
