---
name: sketchpad
description: Work with the user's tablet sketchpad: read what they drew ("check my sketch", "look at the latest image"), put a page on the tab for them to annotate or use, see their ink drawn over a page, start the tab app. Use when they mention the tablet, the tab, sketches, drawing something for Claude, or "put this on the tab".
---

# Sketchpad (tablet ↔ laptop)

The user draws on their tablet (wrapper app or browser); Send saves a PNG + caption on the laptop. Everything is driven by the `sketch` command (`~/Projects/tablet-input-setup/sketchpad/sketch.sh`, on PATH). Repo docs: `~/Projects/tablet-input-setup/README.md` and `AGENTS.md`. The repo is public: **never push without asking**.

## Reading a sketch
- "check my sketch" / "look at the latest image": run `sketch latest`, then Read the PNG it prints and the caption (`~/tablet-sketches/latest.txt`).
- If the sketch was drawn over a page, `sketch latest` also prints `…-over-page.png`: **Read that one**, it is the page with their ink on top. The raw PNG is transparent ink only.
- Handwriting is often sideways (they write with the tab turned): rotate in your head, don't ask.

## Tab-first rule (the user wants the tablet to be the main place)
They want to switch only between the **sketchpad and chat, and chat only when really needed**. So:
- **Wake on Send.** When a sketchpad session starts, run `sketch watch` under the Monitor tool (persistent). Every Send prints `new sketch <name> [over-page=<page>] caption: ...` and wakes you: no "check my sketch" needed.
- **Answer on the tab.** Respond with `sketch put … --open` and/or `sketch note "…"`. In chat say at most one short line (e.g. "answered on the tab") unless something truly needs the chat: a decision that needs words, a failure, or a question the tab can't carry.
- **If the watcher isn't running** (new session, Monitor not started), start it first, then carry on.
- If a Send arrives that you can't act on, put a `sketch note` saying so (don't leave them waiting on a blank tab).

## The loop (one tab, one workflow)
The user's own flowchart: **idea → they draw → they Send (either a reply over one of my pages, or a fresh idea) → I build → I show it back on the tab → they mark it up / ask questions → Send again.**
1. Read the sketch (`sketch latest`). If it has an `…-over-page.png`, it is a reply to that page: say what you're answering.
2. Build or revise the page, `sketch put <dir|file> <name> --open`: the tab shows a dot on Pages and an **Open** banner (never auto-opens, so a page never lands mid-stroke).
3. Banners stay until dismissed, but a **refresh clears them** (the app reload from `sketch app` counts): send notes/pages after the tab has loaded, not just before relaunching it.
3. Questions or comments for them: `sketch note "short text"` shows as a dismissible banner. Keep notes short (one or two sentences, max 600 chars); put anything long in the page itself.
4. They Send again; repeat. Re-use the same page name to revise in place.

## Ink and pages
Blank paper and every page keep their own ink. A Send over a page is that page's ink only (see `over-page=<page>` in the watcher line). The user writes with the tab in landscape but the text turned a quarter turn (reads bottom-to-top): expect sideways handwriting and rotate it in your head.

## Promoting blank paper into a page
If what they are doing on blank paper is turning into a page (a game, a diagram, a worksheet), don't leave it on blank paper: build a page that **carries the paper it had** (dots: an SVG pattern with dots at multiples of 32 px from the page's top-left, r=1.7, `#b8b0cc`; lines: vertical lines every 32 px) and `sketch put <dir> <name> --adopt`. When they tap Open, their blank-paper ink moves into the new page and blank paper is left empty. Keep the page layout fixed to the viewport (no scrolling) so their ink stays aligned with it when you re-put the page with new state.

## Pictures vs pages
The Fill tool only sees the ink layer. If the user will colour, move or resize something (a picture, a character, a diagram to fill in), send it with `sketch image <file>` (it lands ON the canvas via an *Add to canvas* banner). A page (iframe) is for backgrounds and interactive HTML: its content is invisible to Fill.

## Putting something on the tab
1. Write a self-contained page in a scratch dir, then `sketch put <file.html|dir> [name] --open` (without `--open` it still appears under Pages, but the tab isn't told).
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
