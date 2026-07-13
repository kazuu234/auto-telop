#!/usr/bin/env bash
# Build the Auto Telop macOS app (.app) with PyInstaller.
#
# Usage:
#   ./build_macos.sh
#
# Output: dist/AutoTelop.app
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "==> Creating virtualenv"
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

echo "==> Installing dependencies"
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q pyinstaller

echo "==> Cleaning previous build"
rm -rf build dist

echo "==> Building AutoTelop.app"
pyinstaller AutoTelop.spec --noconfirm

echo ""
echo "Done. App is at: dist/AutoTelop.app"
echo ""
echo "To distribute, zip it:"
echo "  cd dist && zip -r AutoTelop-mac.zip AutoTelop.app"
echo ""
echo "Note: unsigned apps trigger a Gatekeeper warning on first launch."
echo "Right-click the app > Open, then confirm, to bypass it."
