# Tablet Input Setup — Galaxy Tab S7 FE → Linux Laptop

*Hardware: Samsung Galaxy Tab S7 FE (with S Pen)*  
*Target: Linux (Hyprland/Wayland) laptop — OpenVSP, general CAD control, media*

---

## Weylus

Turns the tablet browser into a wireless input device + secondary display. No Android app needed.

### What it gives you

| Input | Mapped to | Use for OpenVSP |
|-------|-----------|-----------------|
| S Pen | Mouse pointer + left-click | Precise geometry selection |
| S Pen hover | Cursor position | Preview before clicking |
| S Pen button | Right-click | Context menus on geometry |
| Touch (1 finger) | Mouse move + click | General UI interaction |
| Touch (2 finger drag) | Scroll wheel | Zoom 3D view, scroll panels |
| Pinch | Zoom | Quick zoom in/out |
| Video stream | Mirrored or extended display | Tool palettes on tablet |

### Install

```bash
# Download static binary
wget https://github.com/H-M-H/Weylus/releases/latest/download/weylus_linux
chmod +x weylus_linux
sudo mv weylus_linux /usr/local/bin/weylus

# Run
weylus
```

### Connect

1. Laptop: `weylus` (starts server on port 1701)
2. Tablet: open browser → `http://<laptop-ip>:1701`
3. Tablet: fullscreen the page → start using pen/touch

### Tips

- Use **Trackpad mode** in Weylus settings for relative movement (better for reaching UI corners)
- Lower video quality → lower latency if only using as input (not display)
- The S Pen has ~9ms latency on this tablet; Weylus adds ~10-20ms over WiFi
- Wired connection (USB tethering) drops latency noticeably

---

## KDE Connect

Android ↔ Linux integration suite. Free, in repos, good for shortcuts/macros.

### What it gives you

| Feature | Use |
|---------|-----|
| Touchpad | Tablet screen = trackpad (move, click, scroll, 3-finger gestures) |
| Presentation remote | Volume keys → custom shortcuts |
| Remote commands | Run shell scripts from tablet |
| File sharing | Drag/drop files between devices |
| Notification sync | Tablet shows laptop notifications |
| Media control | Play/pause, skip, volume |

### Install

```bash
sudo apt install kdeconnect
```

Tablet: install **KDE Connect** from Galaxy Store.

Pair: both devices on same WiFi → accept pairing request.

### OpenVSP Shortcuts Idea

In KDE Connect → **Remote Commands**, add:

| Name | Command | Bound to |
|------|---------|----------|
| Fit Model | `xdotool key ctrl+f` | Tablet button |
| Wireframe | `xdotool key w` | Tablet button |
| Screenshot | `grim -g "$(slurp)" ~/Pictures/vsp-$(date +%s).png` | Tablet button |
| Export STL | script calling OpenVSP CLI | Tablet button |

---

## Comparison

| | Weylus | KDE Connect | Spacedesk |
|--|--------|-------------|-----------|
| **S Pen pressure** | ✅ Yes | ❌ No | ⚠️ Limited |
| **Video stream** | ✅ Yes | ❌ No | ✅ Yes |
| **Latency** | Low (~20ms) | N/A (input only) | Medium (~40ms) |
| **Needs Android app** | ❌ Browser only | ✅ Yes | ✅ Yes |
| **Linux support** | ✅ Native | ✅ Native | ⚠️ Basic viewer |
| **Best for** | Pen CAD work | Shortcuts/files | Second monitor |

---

## Recommended Stack

- **Primary input:** Weylus (S Pen precision for CAD)
- **Shortcuts/macros:** KDE Connect (custom buttons for common actions)
- **File drops:** KDE Connect (send .vsp3, .stp, screenshots)

---

## Next Steps

- [ ] Test Weylus latency with OpenVSP
- [ ] Map KDE Connect remote commands to frequent OpenVSP actions
- [ ] Try USB tethering vs WiFi for Weylus latency comparison
- [ ] Set up `systemd --user` service for Weylus auto-start

---

*Started: 2026-04-13*
