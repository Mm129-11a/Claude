#!/usr/bin/env bash
# Regenera las texturas y empaqueta el addon en DeathAnimation.mcaddon
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/generate_textures.py
rm -f DeathAnimation.mcaddon
zip -qr DeathAnimation.mcaddon DeathAnimation_BP DeathAnimation_RP
echo "Creado DeathAnimation.mcaddon"
