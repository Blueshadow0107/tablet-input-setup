#!/usr/bin/env bash
# sketch: run the tablet sketchpad server and show the URL(s) to open on the tab.
#   sketch start [--tailscale-only]   start the server (systemd user unit). Default: Tailscale + Wi-Fi/LAN address
#   sketch stop                       stop it
#   sketch url                        print the URL for each network the server can be reached on
#   sketch usb [--open]               tab on a USB cable (adb): forward its localhost:5099 to the laptop, print that URL;
#                                     --open also launches it in the tab's browser. Needs `sketch start` once (loopback listener)
#   sketch app [--rebuild]            the wrapper app on a USB-connected tab: build+install it if missing, forward the port, point it at the
#                                     server (shell-only config channel) and launch it. --rebuild forces a fresh build + install
#   sketch watch                      print one line per new Send, forever (run it under a Monitor so Claude is woken by every Send)
#   sketch note "text"                a short message from Claude shows on the tab (dismissible banner)
#   sketch put <file.html|dir> [name] [--open]   put a page on the tab (--open also tells the tab: dot on Pages + an Open banner) (Pages button): it is shown behind the ink, in a sandboxed iframe
#   sketch compose [sketch-name]      render the page a sketch was drawn over and lay the ink on top -> <name>-over-page.png
#   sketch rotate                     make a NEW token (old bookmarks stop working) and restart
#   sketch latest                     print the newest saved sketch (png path + caption)
#   sketch status                     is it running, and where it listens
# The token is stable: it is created once and kept, so the tab can bookmark the link. Rotate it if it leaks.
# The service panel's Sketchpad tile just starts/stops the unit and reuses whatever `sketch start` last saved.
set -euo pipefail

DIR="${SKETCHPAD_DIR:-$HOME/tablet-sketches}"
TOKEN_FILE="${SKETCHPAD_TOKEN_FILE:-$HOME/.config/sketchpad/token}"
PORT="${SKETCHPAD_PORT:-5099}"
UNIT=sketchpad

ts_ip() { tailscale ip -4 2>/dev/null | head -n1 || true; }
ts_up() { [[ "$(tailscale status --json 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin).get("BackendState",""))' 2>/dev/null)" == "Running" ]]; }
lan_ip() { ip -4 route get 10.255.255.255 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -n1; }

new_token() {
  mkdir -p "$(dirname "$TOKEN_FILE")"
  (umask 077; head -c 24 /dev/urandom | base64 | tr '+/' '-_' | tr -d '=\n' >"$TOKEN_FILE")
}

token() {
  [[ -r "$TOKEN_FILE" ]] || new_token
  tr -d '\n' <"$TOKEN_FILE"
}

print_urls() {
  local t; t="$(token)"
  if ts_up && [[ -n "$(ts_ip)" ]]; then echo "tailscale: http://$(ts_ip):$PORT/?t=$t"; else echo "tailscale: off (turn it on from the service panel or /ts on)" >&2; fi
  if grep -q -- '--also-lan' "$(dirname "$TOKEN_FILE")/env" 2>/dev/null; then
    [[ -n "$(lan_ip)" ]] && echo "lan:       http://$(lan_ip):$PORT/?t=$t  (plain HTTP: trusted Wi-Fi only)"
  fi
}

inbox_add() { # kind name text: append to <dir>/inbox.json, which the tab polls
  python3 - "$DIR" "$1" "$2" "$3" <<'PY'
import fcntl, json, os, re, sys, time
d, kind, name, text = sys.argv[1:5]
os.makedirs(d, exist_ok=True)
lock = open(os.path.join(d, ".inbox.lock"), "w")
fcntl.flock(lock, fcntl.LOCK_EX)
path = os.path.join(d, "inbox.json")
try:
    items = json.load(open(path))
except Exception:
    items = []
item = {"id": (items[-1]["id"] + 1) if items else 1, "kind": kind, "time": int(time.time())}
if kind == "page":
    item["name"] = name
    try:
        m = re.search(r"<title>(.*?)</title>", open(os.path.join(d, "pages", name, "index.html"), errors="replace").read()[:4000], re.I | re.S)
        item["title"] = (m.group(1).strip() if m else name)[:80]
    except OSError:
        item["title"] = name
else:
    item["text"] = text[:600]
items = (items + [item])[-100:]
tmp = path + ".tmp"
json.dump(items, open(tmp, "w"))
os.replace(tmp, path)
PY
}

cmd="${1:-status}"; shift || true
case "$cmd" in
  start)
    case "${1:-}" in ""|--tailscale-only) ;; *) echo "sketch start: unknown option '$1' (only --tailscale-only)" >&2; exit 2 ;; esac
    envfile="$(dirname "$TOKEN_FILE")/env"
    mkdir -p "$(dirname "$envfile")"
    token >/dev/null   # create it on first run only
    if [[ "${1:-}" == "--tailscale-only" ]]; then
      echo "SKETCHPAD_ARGS=--loopback" >"$envfile"
    else
      echo "SKETCHPAD_ARGS=--loopback --also-lan" >"$envfile"
      echo "note: the LAN link is plain HTTP and the token is long-lived; on open/shared Wi-Fi use --tailscale-only." >&2
    fi
    chmod 600 "$envfile"
    systemctl --user restart "$UNIT"
    sleep 1
    systemctl --user is-active --quiet "$UNIT" || { journalctl --user -u "$UNIT" -n 5 --no-pager; exit 1; }
    print_urls
    ;;
  stop)
    systemctl --user stop "$UNIT"; echo stopped
    ;;
  url)
    print_urls
    ;;
  usb)
    case "${1:-}" in ""|--open) ;; *) echo "sketch usb: unknown option '$1' (only --open)" >&2; exit 2 ;; esac
    command -v adb >/dev/null || { echo "adb not found" >&2; exit 1; }
    adb devices | awk 'NR>1 && $2=="device"{f=1} END{exit !f}' || { echo "no authorised device on adb (plug the tab straight into the laptop, USB debugging on, accept the prompt)" >&2; exit 1; }
    systemctl --user is-active --quiet "$UNIT" || { echo "server is not running: sketch start" >&2; exit 1; }
    grep -q -- '--loopback' "$(dirname "$TOKEN_FILE")/env" 2>/dev/null || { echo "server has no loopback listener yet: run sketch start once" >&2; exit 1; }
    adb reverse "tcp:$PORT" "tcp:$PORT" >/dev/null
    url="http://localhost:$PORT/?t=$(token)"
    echo "usb: $url"
    if [[ "${1:-}" == "--open" ]]; then adb shell am start -a android.intent.action.VIEW -d "'$url'" >/dev/null; fi
    ;;
  app)
    case "${1:-}" in ""|--rebuild) ;; *) echo "sketch app: unknown option '$1' (only --rebuild)" >&2; exit 2 ;; esac
    command -v adb >/dev/null || { echo "adb not found" >&2; exit 1; }
    adb devices | awk 'NR>1 && $2=="device"{f=1} END{exit !f}' || { echo "no authorised device on adb (plug the tab straight into the laptop, USB debugging on, accept the prompt)" >&2; exit 1; }
    systemctl --user is-active --quiet "$UNIT" || { echo "server is not running: sketch start" >&2; exit 1; }
    grep -q -- '--loopback' "$(dirname "$TOKEN_FILE")/env" 2>/dev/null || { echo "server has no loopback listener yet: run sketch start once" >&2; exit 1; }
    appdir="$(cd "$(dirname "$(readlink -f "$0")")/../app" && pwd)"
    if [[ "${1:-}" == "--rebuild" ]] || ! adb shell pm list packages 2>/dev/null | grep -q 'package:local.sketchpad'; then
      echo "building and installing the app..." >&2
      "$appdir/build.sh" install >/dev/null
    fi
    adb reverse "tcp:$PORT" "tcp:$PORT" >/dev/null
    adb shell am broadcast -f 32 -n local.sketchpad/.ConfigReceiver --es url "'http://localhost:$PORT/?t=$(token)'" >/dev/null
    adb shell am start -n local.sketchpad/.MainActivity >/dev/null
    echo "app started on the tab (http://localhost:$PORT over the cable)"
    ;;
  watch)
    last="$(readlink -f "$DIR/latest.png" 2>/dev/null || true)"
    while true; do
      cur="$(readlink -f "$DIR/latest.png" 2>/dev/null || true)"
      if [[ -n "$cur" && "$cur" != "$last" ]]; then
        last="$cur"; n="$(basename "$cur" .png)"; sleep 0.6   # the page sidecar is written just after the PNG
        cap=""; [[ -s "$DIR/$n.txt" ]] && cap="$(head -c 200 "$DIR/$n.txt" | tr '\n' ' ')"
        over=""; [[ -f "$DIR/$n.json" ]] && over=" over-page=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["page"])' "$DIR/$n.json" 2>/dev/null)"
        echo "new sketch $n$over caption: $cap"
      fi
      sleep 2
    done
    ;;
  note)
    [[ -n "${1:-}" ]] || { echo "usage: sketch note \"text\"" >&2; exit 2; }
    inbox_add note "" "$*"; echo "note is on its way to the tab"
    ;;
  put)
    open=0; pargs=(); for a in "$@"; do if [[ "$a" == "--open" ]]; then open=1; else pargs+=("$a"); fi; done
    set -- "${pargs[@]+"${pargs[@]}"}"
    src="${1:-}"; name="${2:-}"
    [[ -n "$src" && -e "$src" ]] || { echo "usage: sketch put <file.html|dir> [name]" >&2; exit 2; }
    if [[ -d "$src" ]]; then name="${name:-$(basename "$(cd "$src" && pwd)")}"; else name="${name:-$(basename "${src%.*}")}"; fi
    [[ "$name" =~ ^[A-Za-z0-9_.-]{1,64}$ ]] || { echo "page name must be letters, digits, . _ - (max 64): '$name'" >&2; exit 2; }
    dest="$DIR/pages/$name"; mkdir -p "$dest"
    if [[ -d "$src" ]]; then cp -a "$src"/. "$dest"/; else cp "$src" "$dest/index.html"; fi
    [[ -f "$dest/index.html" ]] || { echo "no index.html in $dest" >&2; exit 1; }
    if [[ "$open" == 1 ]]; then inbox_add page "$name" ""; echo "page '$name' is on the tab and the tab was told (dot on Pages + an Open banner)."
    else echo "page '$name' is on the tab: Pages button (top left). Add --open to also notify. Keep it fit-to-screen, no scrolling, so the ink lines up."; fi
    ;;
  compose)
    cj="${1:-}"
    if [[ -z "$cj" ]]; then cj="$(find "$DIR" -maxdepth 1 -name '2*.json' -printf '%f\n' 2>/dev/null | sort | tail -n1)"; cj="${cj%.json}"; fi
    [[ -n "$cj" && -f "$DIR/$cj.json" ]] || { echo "no sketch drawn over a page yet" >&2; exit 1; }
    read -r page vp < <(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["page"], d["viewport"])' "$DIR/$cj.json")
    [[ -f "$DIR/pages/$page/index.html" ]] || { echo "page '$page' no longer exists in $DIR/pages" >&2; exit 1; }
    CHROME="${CHROME:-$(find "$HOME/.cache/ms-playwright" -maxdepth 3 -path '*chromium-*/chrome-linux64/chrome' -type f 2>/dev/null | sort | tail -n1)}"
    [[ -x "$CHROME" ]] || CHROME="$(command -v chromium google-chrome chrome 2>/dev/null | head -n1 || true)"
    [[ -x "$CHROME" ]] || { echo "no headless Chrome/Chromium found (set CHROME=...)" >&2; exit 1; }
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --screenshot="$tmp/page.png" \
      --window-size="${vp/x/,}" "file://$DIR/pages/$page/index.html" >/dev/null 2>&1
    [[ -s "$tmp/page.png" ]] || { echo "could not render the page" >&2; exit 1; }
    ink_dim="$(magick identify -format '%wx%h' "$DIR/$cj.png")"
    magick "$tmp/page.png" -resize "${ink_dim}!" "$DIR/$cj.png" -compose over -composite "$DIR/$cj-over-page.png"
    echo "$DIR/$cj-over-page.png"
    echo "page: $page ($vp)"
    ;;
  rotate)
    new_token
    systemctl --user restart "$UNIT"
    echo "new token saved; re-bookmark the link on the tab:"
    sleep 1; print_urls
    ;;
  latest)
    [[ -e "$DIR/latest.png" ]] || { echo "no sketches yet in $DIR" >&2; exit 1; }
    readlink -f "$DIR/latest.png"
    lname="$(basename "$(readlink -f "$DIR/latest.png")" .png)"
    if [[ -f "$DIR/$lname.json" ]]; then echo "drawn over a page:"; "$0" compose "$lname" || true; fi
    [[ -s "$DIR/latest.txt" ]] && { echo "caption: $(cat "$DIR/latest.txt")"; } || true
    ;;
  status)
    systemctl --user is-active "$UNIT" || true
    ss -ltn "sport = :$PORT" 2>/dev/null | tail -n +2 | awk '{print "listening on", $4}'
    ;;
  *)
    sed -n '2,20p' "$0"; exit 2
    ;;
esac
