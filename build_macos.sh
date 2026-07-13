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

echo "==> Bundling first-run setup script"
cp 初回セットアップ.command dist/
chmod +x dist/初回セットアップ.command

echo "==> Creating distribution zip (app + setup script)"
( cd dist && rm -f AutoTelop-mac.zip && zip -r -y -q AutoTelop-mac.zip AutoTelop.app 初回セットアップ.command )

echo ""
echo "Done. App is at: dist/AutoTelop.app"
echo "Distribution zip: dist/AutoTelop-mac.zip (includes 初回セットアップ.command)"
echo ""
echo "Note: unsigned apps trigger a Gatekeeper 'damaged' warning on first launch."
echo "The bundled 初回セットアップ.command runs 'xattr -cr' to clear it."
