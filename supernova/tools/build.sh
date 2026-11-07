#!/usr/bin/env bash
# Saca las texturas de las imágenes de referencia, escribe las partículas y empaqueta Supernova.mcaddon
# Uso: ./tools/build.sh [bola.jpg explosion.jpg destello.jpg]
# (sin imágenes usa las texturas que ya hay; la vista previa: python3 tools/make_preview.py)
set -euo pipefail
cd "$(dirname "$0")/.."
if [ $# -eq 3 ]; then python3 tools/extract_from_photos.py "$1" "$2" "$3"; fi
python3 tools/make_particles.py
python3 tools/make_pieces.py
python3 tools/make_particles.py   # otra vez: la partícula de las piezas usa el tamaño de piezas.png
rm -rf tools/__pycache__
rm -f Supernova.mcaddon
zip -qr Supernova.mcaddon SupernovaBP SupernovaRP
echo "Creado Supernova.mcaddon"
