#!/usr/bin/env bash
# Installs the sketchpad for the current user: systemd user unit, the `sketch` command, data dirs. No sudo.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/.config/systemd/user" "$HOME/.local/bin" "$HOME/tablet-sketches" "$HOME/.config/sketchpad"
# the unit runs the server from the clone: point it at wherever this checkout lives
sed "s|%h/Projects/tablet-input-setup|$SCRIPT_DIR|g" "$SCRIPT_DIR/sketchpad/sketchpad.service" > "$HOME/.config/systemd/user/sketchpad.service"
ln -sf "$SCRIPT_DIR/sketchpad/sketch.sh" "$HOME/.local/bin/sketch"
systemctl --user daemon-reload
echo "Installed. Make sure ~/.local/bin is on your PATH, then:  sketch start"
