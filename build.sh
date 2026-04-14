#!/usr/bin/env bash
# Build patch_plugins as a single standalone binary using PyInstaller.
# Output: dist/patch_plugins

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Install PyInstaller if needed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip3 install --quiet pyinstaller
fi

echo "Building..."
pyinstaller \
    --onefile \
    --name patch_plugins \
    --distpath "$SCRIPT_DIR/dist" \
    --workpath "$SCRIPT_DIR/build" \
    --specpath "$SCRIPT_DIR/build" \
    --clean \
    "$SCRIPT_DIR/src/patcher.py"

echo ""
echo "Binary: dist/patch_plugins"
echo ""
echo "Distribute together:"
echo "  dist/patch_plugins"
echo "  plugins/"
