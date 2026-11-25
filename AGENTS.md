# AGENTS.md: tablet-input-setup

Tablet ↔ laptop sketchpad. Read `README.md` for usage. Workspace rules are in `~/AGENTS.md`.

## What's here

- `sketchpad/`: **the working part.** `server.py` (stdlib only), `index.html` (the drawing page), `sketch.sh` (installed as `sketch`), `sketchpad.service`. Sketches land in `~/tablet-sketches/` with `latest.png` / `latest.txt`.
- `legacy/` + `docs/legacy.md`: older Weylus + KDE Connect notes and configs, **never run end to end**. Don't present them as verified. `docs/FEATURES.md` = full feature reference.

## When the user says "check my sketch"

Run `sketch latest` (or read `~/tablet-sketches/latest.png` and `latest.txt` directly). View the PNG with Read; the `.txt` is the caption they typed.

## Rules for changes

- The server must always require the token, and must never log it. Bind per address, never 0.0.0.0 by default: Tailscale's address always, the Wi-Fi address only with `--also-lan` (what `sketch start` saves by default, by the user's choice; plain HTTP, so `--tailscale-only` on shared Wi-Fi). The token is stable (bookmarked on the tab); `sketch rotate` replaces it. `--loopback` (always set by `sketch start`) adds 127.0.0.1 for `sketch usb` (adb reverse over the cable): reachable only from the laptop itself.
- Keep it stdlib-only and a single small HTML page: the tablet has 4 GB RAM.
- Wayland session: use `wtype`/`grim`/`wl-copy`, not `xdotool`.
- UI: no page scroll, toasts clear themselves, colours/sizes come from the constants at the top of the script.

## Tablet access (adb)

USB never enumerated, so the tab is driven over **wireless debugging**: pairing persists, but the connect port changes after each reboot. Run `adb mdns services`, then `adb connect <ip:port>`. Turn wireless debugging off when done.

## Testing

`python3 sketchpad/server.py --host 127.0.0.1 --port 5199 --dir <tmp>` with `SKETCHPAD_TOKEN_FILE=<tmp>/token`, then curl the API or drive the page headlessly (cached Playwright Chromium in `~/.cache/ms-playwright`).
