# Older notes: Weylus and KDE Connect

These predate the sketchpad and were **never run end to end**; the files live in `legacy/`. Don't treat them as verified.

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
