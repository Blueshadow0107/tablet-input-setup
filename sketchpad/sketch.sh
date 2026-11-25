#!/usr/bin/env bash
# sketch: run the tablet sketchpad server and show the URL to open on the tab.
#   sketch start [--lan]   start the server (systemd user unit)
#   sketch stop            stop it
#   sketch url [--lan]     print the URL for the tab
#   sketch latest          print the newest saved sketch (png path + caption)
#   sketch status          is it running, and where it listens
set -euo pipefail

DIR="${SKETCHPAD_DIR:-$HOME/tablet-sketches}"
TOKEN_FILE="${SKETCHPAD_TOKEN_FILE:-$HOME/.config/sketchpad/token}"
PORT="${SKETCHPAD_PORT:-5099}"
UNIT=sketchpad

host_for() { # $1 = "--lan" or ""
  if [[ "${1:-}" == "--lan" ]]; then
    ip -4 -o addr show scope global | awk '$2 !~ /^(docker|br-|veth)/ {split($4,a,"/"); print a[1]; exit}'
  else
    tailscale ip -4 2>/dev/null | head -n1
  fi
}

token() {
  if [[ ! -r "$TOKEN_FILE" ]]; then
    echo "no token yet; start the server once to create it" >&2
    return 1
  fi
  tr -d '\n' <"$TOKEN_FILE"
}

cmd="${1:-status}"; shift || true
case "$cmd" in
  start)
    mode="${1:-}"
    envfile="$(dirname "$TOKEN_FILE")/env"
    mkdir -p "$(dirname "$envfile")"
    if [[ "$mode" == "--lan" ]]; then
      lan_ip="$(host_for --lan)"
      [[ -n "$lan_ip" ]] || { echo "no LAN address found" >&2; exit 1; }
      # bind to the one Wi-Fi address, not every interface
      echo "SKETCHPAD_ARGS=--host $lan_ip" >"$envfile"
      echo "WARNING: --lan is plain HTTP. On open/shared Wi-Fi the token and sketches can be sniffed. Prefer Tailscale; keep sessions short." >&2
    else
      : >"$envfile"
    fi
    # fresh token every start, so an old (possibly sniffed) link stops working
    mkdir -p "$(dirname "$TOKEN_FILE")"
    (umask 077; head -c 24 /dev/urandom | base64 | tr '+/' '-_' | tr -d '=\n' >"$TOKEN_FILE")
    systemctl --user restart "$UNIT"
    sleep 1
    systemctl --user is-active --quiet "$UNIT" || { journalctl --user -u "$UNIT" -n 5 --no-pager; exit 1; }
    "$0" url "$mode"
    ;;
  stop)
    systemctl --user stop "$UNIT"; echo stopped
    ;;
  url)
    host="$(host_for "${1:-}")"
    [[ -n "$host" ]] || { echo "no address found (Tailscale off? try: sketch url --lan)" >&2; exit 1; }
    echo "http://$host:$PORT/?t=$(token)"
    ;;
  latest)
    [[ -e "$DIR/latest.png" ]] || { echo "no sketches yet in $DIR" >&2; exit 1; }
    readlink -f "$DIR/latest.png"
    [[ -s "$DIR/latest.txt" ]] && { echo "caption: $(cat "$DIR/latest.txt")"; } || true
    ;;
  status)
    systemctl --user is-active "$UNIT" || true
    ss -ltn "sport = :$PORT" 2>/dev/null | tail -n +2 | awk '{print "listening on", $4}'
    ;;
  *)
    sed -n '2,8p' "$0"; exit 2
    ;;
esac
