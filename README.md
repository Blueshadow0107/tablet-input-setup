# Tablet Input Setup: Galaxy Tab S7 FE → Linux laptop

Hardware: Samsung Galaxy Tab S7 FE (SM-T733, 4 GB RAM, Android 14, S Pen).
Laptop: Linux, Hyprland/Wayland.

Two separate things live here. **Sketchpad is built and tested.** The Weylus and KDE Connect notes further down are older and have never been run end to end.

---

## Sketchpad: draw on the tab, show Claude

Draw on the tablet in its browser, hit Send, and a PNG (plus an optional caption) lands on the laptop where Claude can read it. No app on the tablet, and it's light on its 4 GB of RAM.

```bash
sketch start          # serve over Tailscale (default); prints the URL for the tab
sketch start --lan    # serve on the Wi-Fi address instead (token still required)
sketch url [--lan]    # print the URL again
sketch latest         # path + caption of the newest sketch
sketch stop
```

Then tell Claude "check my latest sketch". It reads `~/tablet-sketches/latest.png` and `latest.txt`.

- **Pen only by default.** Finger and palm touches are ignored; the *Finger* button turns finger drawing on. The pen's eraser end erases.
- **Auth.** Every request needs a random token (`~/.config/sketchpad/token`, mode 600), regenerated on every `sketch start` so old links die. Over Tailscale the link is encrypted and nothing is exposed on the local Wi-Fi.
- **`--lan` is plain HTTP.** It binds to the Wi-Fi address only, but on an open or shared network the token and your sketches can be sniffed. Use it for short sessions on a network you trust; otherwise use Tailscale.
- **Saved files.** `~/tablet-sketches/<timestamp>.png` + `.txt`, and `latest.png` / `latest.txt` symlinks.
- **Not enabled at boot.** `sketchpad.service` starts only when you run `sketch start`.

Code: `sketchpad/server.py` (stdlib only), `sketchpad/index.html`, `sketchpad/sketch.sh`, `sketchpad/sketchpad.service`. Install with `./install.sh`.

---

## Weylus (untested)

Turns the tablet browser into a wireless pen/touch input device and second display. Installed at `/usr/local/bin/weylus`; the unit `weylus.service` is linked but has never been enabled.

Intended use: S Pen as a pointer for CAD (OpenVSP), `http://<laptop-ip>:1701` in the tablet browser. **None of the behaviour below has been measured here**; the README used to claim specific latencies and pen-button mappings, which were taken from Weylus's docs, not tested.

Open questions to check before relying on it:
- Does it get pen pressure on Hyprland/Wayland (screen capture path)?
- Real latency over this Wi-Fi.
- Is the tab fast enough to run the browser stream smoothly (it was RAM-starved).

Note that Weylus listens on port 1701 on all interfaces with no token by default; don't leave it running on shared Wi-Fi.

## KDE Connect (untested)

`kdeconnect-commands.json` has remote-command ideas for the tablet. They were first written with `xdotool`, which does not work on a Wayland session, so they now use `wtype` (also untested). Pair the tablet in the KDE Connect app first.

---

## Tablet state (2026-11-25)

Cleaned up over adb (wireless debugging; USB never enumerated): power saving off, Samsung bloat and unused apps removed, caches cleared. Security patch is June 2025. A custom ROM was considered and parked: S Pen support on the T733 builds is unverified.
