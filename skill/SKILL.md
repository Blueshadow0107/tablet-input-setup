---
name: sketchpad
description: Work with the user's tablet sketchpad: read what they drew ("check my sketch", "look at the latest image"), put a page on the tab for them to annotate or use, see their ink drawn over a page, start the tab app. Use when they mention the tablet, the tab, sketches, drawing something for Claude, or "put this on the tab".
---

# Sketchpad (tablet ↔ laptop)

The user draws on their Galaxy Tab S7 FE (wrapper app or browser); Send saves a PNG + caption on the laptop. Everything is driven by the `sketch` command (`~/Projects/tablet-input-setup/sketchpad/sketch.sh`, on PATH). Repo docs: `~/Projects/tablet-input-setup/README.md` and `AGENTS.md`. The repo is public: **never push without asking**.

## Reading a sketch
- "check my sketch" / "look at the latest image": run `sketch latest`, then Read the PNG it prints and the caption (`~/tablet-sketches/latest.txt`).
- If the sketch was drawn over a page, `sketch latest` also prints `…-over-page.png`: **Read that one**, it is the page with their ink on top. The raw PNG is transparent ink only.
- Handwriting is often sideways (they write with the tab turned): rotate in your head, don't ask.

## Putting something on the tab
1. Write a self-contained page: `~/tablet-sketches/pages/<name>/index.html` (+ css/js/images beside it), or write a file anywhere and run `sketch put <file.html|dir> [name]`.
2. It appears under the **Pages** button (top left of the app). They can Draw on it with the pen, or switch to **Use** (taps and scrolling go to the page, e.g. a quiz or a calculator).
3. Page rules, because ink is positioned in screen pixels:
   - **Fit the screen, no scrolling.** Use `100vw/100vh`, flex/grid, `overflow: hidden`. Landscape is about 1204×731 CSS px, portrait about 731×1204 (the real size is in the sketch's `.json` sidecar as `viewport`).
   - Self-contained: no external network. Plain HTML/CSS/JS; scripts run, but the page is **sandboxed** (no same-origin access, cannot call the sketchpad API or read the token).
   - Big touch targets (≥ 44 px), high contrast, the user's palette if you want to match: bg `#0f0a1a`, panel `#1a1230`, accent `#a78bfa`, paper `#fbfaf6`.
   - Colours and sizes live in variables/constants at the top, nothing hard-coded in the middle; toasts clear themselves.
4. Optionally also publish a copy as a real claude.ai artifact if they want to share it (artifacts need a login, so the tab itself uses the local copy).

## Sketch → page
When they sketch an idea and ask for it "as an artifact/page": read the sketch, build the page (rules above), `sketch put` it, tell them where it is. No other code is needed.

## Starting things
- `sketch app` (tab on a USB cable, plugged **straight into the laptop**, not a hub): installs/launches the wrapper app pointed at the server. `sketch app --rebuild` after changing `app/`.
- `sketch start` / `stop` / `status` / `url` / `usb` / `rotate`. Server binds Tailscale + Wi-Fi + loopback per address; the token is stable.
- The tab is also in the service panel as "Sketchpad".

## S Pen and gotchas
- The side button works **only in the wrapper app**: hold it to erase (the app reads the button natively and tells the page). In plain Chrome it only has a tap-to-toggle fallback.
- Chrome on the tab gets killed for low memory; the app uses about 114 MB instead of ~500 MB.
- Debug pen issues: `adb logcat -s sketchpad` (raw pen events) and `?debug=1` on the URL (page events, `journalctl --user -u sketchpad | grep pen-debug`); debug mode slows drawing, turn it off afterwards.
- Never put the token on shared chat/screens; it is in `~/.config/sketchpad/token` (mode 600).
