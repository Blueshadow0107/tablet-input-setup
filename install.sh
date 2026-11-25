#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEYLUS_BIN="/usr/local/bin/weylus"

echo "=== Tablet Input Setup ==="
echo ""

# --- Weylus ---
if [ ! -f "$WEYLUS_BIN" ]; then
    echo "[1/3] Installing Weylus..."
    
    # Download linux.zip from latest release (weylus_linux no longer exists as direct binary)
    TMP_ZIP="/tmp/weylus_linux.zip"
    curl -sL -o "$TMP_ZIP" "https://github.com/H-M-H/Weylus/releases/latest/download/linux.zip"
    
    # Extract just the 'weylus' binary
    unzip -o "$TMP_ZIP" -d /tmp weylus
    chmod +x /tmp/weylus
    sudo mv /tmp/weylus "$WEYLUS_BIN"
    rm -f "$TMP_ZIP"
    
    echo "      Weylus installed to $WEYLUS_BIN"
else
    echo "[1/3] Weylus already installed at $WEYLUS_BIN"
fi

# --- KDE Connect ---
if ! command -v kdeconnect-cli &> /dev/null; then
    echo "[2/3] Installing KDE Connect..."
    sudo apt update && sudo apt install -y kdeconnect
else
    echo "[2/3] KDE Connect already installed"
fi

# --- Systemd user service ---
echo "[3/3] Installing Weylus systemd user service..."
mkdir -p "$HOME/.config/systemd/user"
cp "$SCRIPT_DIR/weylus.service" "$HOME/.config/systemd/user/"

# --- Sketchpad (draw on the tab, save a PNG for Claude) ---
cp "$SCRIPT_DIR/sketchpad/sketchpad.service" "$HOME/.config/systemd/user/"
mkdir -p "$HOME/.local/bin" "$HOME/tablet-sketches" "$HOME/.config/sketchpad"
ln -sf "$SCRIPT_DIR/sketchpad/sketch.sh" "$HOME/.local/bin/sketch"
systemctl --user daemon-reload

echo ""
echo "=== Done ==="
echo ""
echo "Enable Weylus auto-start:  systemctl --user enable --now weylus"
echo "Start Weylus now:          systemctl --user start weylus"
echo "Check status:              systemctl --user status weylus"
echo ""
echo "Next: Pair KDE Connect on your tablet (Galaxy Store) and laptop."
