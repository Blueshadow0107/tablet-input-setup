#!/bin/bash
set -euo pipefail

# Quick-start Weylus without systemd (for one-off use)
if ! command -v weylus &> /dev/null; then
    echo "Weylus not found. Run ./install.sh first."
    exit 1
fi

echo "Starting Weylus on http://$(hostname -I | awk '{print $1}'):1701"
weylus
