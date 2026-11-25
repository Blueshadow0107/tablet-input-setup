# Tablet Input Setup: Galaxy Tab S7 FE → Linux laptop

Hardware: Samsung Galaxy Tab S7 FE (SM-T733, 4 GB RAM, Android 14, S Pen).
Laptop: Linux, Hyprland/Wayland.

Two separate things live here. **Sketchpad is built and tested.** The Weylus and KDE Connect notes further down are older and have never been run end to end.

---

## Sketchpad: draw on the tab, show Claude

Draw on the tablet in its browser, hit Send, and a PNG (plus an optional caption) lands on the laptop where Claude can read it. No app on the tablet, and it's light on its 4 GB of RAM.

```bash
sketch start                    # serve on Tailscale AND the Wi-Fi address (default); prints a URL for each
sketch start --tailscale-only   # no LAN listener (use on open/shared Wi-Fi)
sketch url                      # print the URLs again
sketch rotate                   # new token (old bookmarks die) and restart
sketch usb [--open]              # tab on a USB cable: adb-forwards its localhost:5099 to the laptop (no network at all); --open launches it on the tab
sketch latest         # path + caption of the newest sketch
sketch stop
```

Then tell Claude "check my latest sketch". It reads `~/tablet-sketches/latest.png` and `latest.txt`.

- **Pen only by default.** Finger and palm touches are ignored; the *Finger* button turns finger drawing on.
- **Tools.** Pen (pressure-sensitive), Shapes (line, arrow, rectangle, ellipse), Fill, Eraser (removes a whole stroke or shape per touch, sweeping the path so a fast flick can't skip it) and Select.
- **S Pen side button = tap to toggle Pen ↔ Eraser.** Tap it while hovering (or press it mid-stroke: the ink so far is kept and the rest of the stroke erases) and the tool flips; tap again to go back to the tool you had (Select too). Holding the button while touching can't work: Chromium swallows button-held touches, so no events reach the page. Samsung's Air Command may also pop up on a tap (it's a global setting, not per-site). The pen's eraser end erases directly. Mouse right-click does not.
- **Hold to straighten.** Pause the pen at the end of a stroke that is already nearly straight (within 12% of its length) and it snaps to a line that follows the pen until you lift.
- **Install as an app.** Over the USB route (`sketch usb`, `localhost` counts as a secure context) Chrome offers *Install app* in its menu: a standalone window with no tab strip, lighter on the tab's memory. Over Wi-Fi/Tailscale (plain HTTP) only *Add to Home screen* appears. Icons come from `make-icons.py`; the manifest is served by the server with your token baked in.
- **In the wrapper app (`app/`), the S Pen button works two ways:** a quick press in the air toggles Pen/Eraser; holding it while you touch erases for as long as it is held (a press mid-stroke keeps the ink so far and erases the rest). The app reads the button natively and tells the page, because Chrome hides button-held touches. `app/build.sh install` builds and installs it.
- **Fill.** Pick a colour, tap inside a closed shape (or any area) and it floods up to the nearest lines. A gap in the outline lets it leak out, so close the shape first. A fill is one undo step; the Eraser removes it by touching the spot you tapped; Select ignores it.
- **Cut, copy, paste.** Select something and a small bar appears above it (Cut, Copy, Paste, Delete); the panel also has a Paste button. Pasted copies land 24 px down-right of the last one and are selected so you can drag them at once. Ctrl+C/X/V work with a keyboard. Fills are not selectable, so they are not copied.
- **Select.** Draw a lasso around things, drag inside the box to move them, drag a corner to resize, *Delete* to remove. Tapping outside clears the selection.
- **Undo / redo.** Buttons, plus a two-finger tap (undo) and three-finger tap (redo). *Clear* is undoable. Moves, resizes, erases and deletes are each one undo step.
- **Pen diagnostics.** Add `&debug=1` to the URL to show what the browser reports for the pen (type, button, buttons, pressure) and log changes on the laptop (`journalctl --user -u sketchpad | grep pen-debug`).
- **Auth.** Every request needs a random token (`~/.config/sketchpad/token`, mode 600), created once and kept, so the tab can bookmark the link. `sketch rotate` replaces it if it ever leaks. Over Tailscale the link is encrypted. The service panel's Sketchpad tile only starts/stops the unit and reuses what `sketch start` last saved.
- **`sketch usb --open` leaves the token in a few places:** the `adb shell am start` command line (visible briefly to other processes on the laptop), the tab's Chrome history and its logcat. The token is already bookmarked on the tab, so this adds little; `sketch rotate` replaces it if you ever need to. Plain `sketch usb` (no `--open`) only prints the link.
- **The LAN link is plain HTTP.** The server binds each address separately (Tailscale's, and the Wi-Fi one with `--also-lan`), never every interface, and re-checks every few seconds so Tailscale coming up later just works. On an open or shared network the token and sketches can be sniffed, and the token is now long-lived: use `--tailscale-only` there.
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
