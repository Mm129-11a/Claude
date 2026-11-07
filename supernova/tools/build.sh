#!/usr/bin/env bash
# Hace las texturas y las partículas y empaqueta Supernova.mcaddon
# Uso: ./tools/build.sh [destello.jpg]
# (sin la captura usa el destello que ya hay; la vista previa: python3 tools/make_preview.py)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ $# -eq 1 ]; then python3 tools/extract_from_photos.py "$1"; fi
python3 tools/make_vfx.py          # estrella en 3D girando y capas de la explosión
python3 tools/make_particles.py
python3 tools/make_pieces.py       # corta la estrella en sus piezas
python3 tools/make_particles.py    # otra vez: la partícula de las piezas usa el tamaño de piezas.png
rm -rf tools/__pycache__
rm -f Supernova.mcaddon
zip -qr Supernova.mcaddon SupernovaBP SupernovaRP
echo "Creado Supernova.mcaddon"
