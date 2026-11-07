#!/usr/bin/env bash
# Regenera texturas y partículas y empaqueta Supernova.mcaddon
# (la vista previa se hace aparte: python3 tools/make_preview.py)
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/make_textures.py
python3 tools/make_particles.py
rm -f Supernova.mcaddon
zip -qr Supernova.mcaddon SupernovaBP SupernovaRP
echo "Creado Supernova.mcaddon"
