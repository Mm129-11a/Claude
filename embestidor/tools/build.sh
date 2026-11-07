#!/usr/bin/env bash
# Hace el modelo, la textura, las animaciones y los archivos del addon, y empaqueta Embestidor.mcaddon
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/make_mob.py
python3 tools/make_addon.py
rm -rf tools/__pycache__
rm -f Embestidor.mcaddon
zip -qr Embestidor.mcaddon EmbestidorBP EmbestidorRP
echo "Creado Embestidor.mcaddon"
