# Sketchpad

**Draw on a tablet. Hit Send. Your AI assistant sees it, answers on the tablet, and you keep going.**

A tiny self-hosted drawing pad built for working with Claude (or any agent that can read a PNG). Sketch a diagram, circle a bug, mark up a page the assistant just built, or play dots & boxes against it, all without leaving the tablet.

```
 tablet (pen)  ──Send──▶  laptop: PNG + caption saved ──▶  Claude reads it
      ▲                                                       │
      └──── note / page / picture shown on the tablet ◀───────┘
```

- **One small server** (`sketchpad/server.py`, Python stdlib only) and **one HTML page**. No framework, no build step, light enough for a 4 GB tablet.
- **Pen-first canvas:** pressure pen, shapes, fill, select/move/resize, cut/copy/paste, colour wheel + eyedropper, undo, pinch-zoom, paper styles, autosave.
- **Claude → tablet:** the assistant can put a note, an HTML page (you draw over it) or a picture (colour it in) on your tablet; a watcher wakes it on every Send.
- **Optional Android wrapper** (`app/`, ~100 lines of Java, no dependencies) adds the S Pen side button as hold-to-erase and uses a fraction of Chrome's memory.
- **Private by default:** random token on every request, binds only to Tailscale / Wi-Fi / loopback addresses you choose (never `0.0.0.0`), sandboxed pages.

## Quickstart

```bash
git clone https://github.com/Blueshadow0107/tablet-input-setup.git ~/Projects/tablet-input-setup
cd ~/Projects/tablet-input-setup && ./install.sh     # user-level, no sudo
sketch start                                        # prints a URL for each network; open one on the tablet
```

Then tell your assistant **"check my sketch"**: it reads `~/tablet-sketches/latest.png` and its caption.

Needs Linux with systemd, Python 3, and a tablet browser (Chrome works). [Tailscale](https://tailscale.com) is recommended so the link is encrypted; on shared Wi-Fi use `sketch start --tailscale-only`. No Tailscale and a USB cable? `sketch usb` forwards the port over adb, so nothing touches the network.

## The loop

| You | The assistant |
|---|---|
| Draw, optionally type a caption, **Send** | `sketch compose` / `sketch latest` to look at it |
| Mark up a page it made, tap **Send** | `sketch put page.html --open`, `sketch note "…"`, `sketch image pic.png` |
| Switch paper, zoom, undo, colour | stays out of the way |

To make a session tab-first, install the skill (`cp -r skill ~/.claude/skills/sketchpad`) and say "use the tab": it runs `sketch watch` in the background, so every Send wakes it, and replies on the tablet instead of in the terminal.

## Docs

- [`docs/FEATURES.md`](docs/FEATURES.md): every tool, gesture, command and security note.
- [`skill/SKILL.md`](skill/SKILL.md): the Claude-side skill.
- [`app/`](app/): the Android wrapper (`app/build.sh install`; needs the Android SDK build tools).
- [`docs/legacy.md`](docs/legacy.md): older, untested Weylus / KDE Connect notes (files in `legacy/`).

## Security in brief

Every request needs a long random token (`~/.config/sketchpad/token`, mode 600); `sketch rotate` replaces it. The server only listens on addresses you opted into and re-checks them every few seconds. Pages you put on the tablet run in a sandboxed iframe behind short-lived per-page links and a strict CSP. The LAN link is plain HTTP: on open Wi-Fi use Tailscale or USB.

## License

[MIT](LICENSE) © 2026 Blueshadow0107
