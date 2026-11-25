#!/usr/bin/env python3
"""Draw the app icons (192 and 512 px PNG) into sketchpad/icons/ using only the standard library.
Run once after changing the design: python3 sketchpad/make-icons.py"""
import struct
import zlib
from pathlib import Path

BG, PAPER, INK, ACCENT = (26, 18, 48), (251, 250, 246), (22, 18, 31), (167, 139, 250)  # bar, paper, ink, accent from index.html


def inside(poly, x, y):
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def render(size: int) -> bytes:
    s = size
    # a pencil drawn on a rotated 1x1 square: body, tip, ink dot; everything inside the maskable safe zone (centre 80%)
    pencil = [(.30, .66), (.62, .34), (.70, .42), (.38, .74)]           # body
    tip = [(.30, .66), (.38, .74), (.25, .78)]                           # sharpened end
    cap = [(.62, .34), (.70, .42), (.76, .36), (.68, .28)]               # eraser cap
    rows = bytearray()
    for py in range(s):
        rows.append(0)
        for px in range(s):
            acc = [0, 0, 0]
            for sy in (0.25, 0.75):          # 2x2 supersampling
                for sx in (0.25, 0.75):
                    x, y = (px + sx) / s, (py + sy) / s
                    col = BG
                    if (x - .5) ** 2 + (y - .5) ** 2 < .38 ** 2:
                        col = PAPER
                    if inside(pencil, x, y):
                        col = ACCENT
                    if inside(tip, x, y):
                        col = INK
                    if inside(cap, x, y):
                        col = (209, 46, 79)
                    for k in range(3):
                        acc[k] += col[k]
            rows += bytes(v // 4 for v in acc)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", s, s, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "icons"
    out.mkdir(exist_ok=True)
    for n in (192, 512):
        (out / f"icon-{n}.png").write_bytes(render(n))
        print("wrote", out / f"icon-{n}.png")
