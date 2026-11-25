#!/usr/bin/env python3
"""Sketchpad server: tablet draws, laptop saves a PNG (+ caption) for Claude to read.

Stdlib only. Every request needs the secret token. By default it listens on the
Tailscale address only; --lan opens it on all interfaces (token still required).
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import subprocess
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
TOKEN_FILE = Path(os.environ.get("SKETCHPAD_TOKEN_FILE", "~/.config/sketchpad/token")).expanduser()
DEFAULT_DIR = Path(os.environ.get("SKETCHPAD_DIR", "~/tablet-sketches")).expanduser()
DEFAULT_PORT = 5099
MAX_BYTES = 12 * 1024 * 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_CAPTION = 2000


def load_token() -> str:
    """Read the token, creating a 600-mode one on first run."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(24)
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(token + "\n")
    return token


def tailscale_ip() -> str | None:
    try:
        out = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    ip = out.stdout.strip().splitlines()[0] if out.returncode == 0 and out.stdout.strip() else ""
    return ip or None


def save_sketch(out_dir: Path, png: bytes, caption: str) -> str:
    """Write <stamp>.png (+ .txt), then repoint latest.png / latest.txt atomically."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    name, n = stamp, 1
    while (out_dir / f"{name}.png").exists():
        n += 1
        name = f"{stamp}-{n}"
    png_path, txt_path = out_dir / f"{name}.png", out_dir / f"{name}.txt"
    png_path.write_bytes(png)
    txt_path.write_text(caption)
    for ext in ("png", "txt"):
        link, tmp = out_dir / f"latest.{ext}", out_dir / f".latest.{ext}.tmp"
        tmp.unlink(missing_ok=True)
        tmp.symlink_to(f"{name}.{ext}")
        os.replace(tmp, link)
    return name


class Handler(BaseHTTPRequestHandler):
    server_version = "sketchpad"
    token: str = ""
    out_dir: Path = DEFAULT_DIR

    def log_message(self, fmt: str, *args) -> None:  # keep the token out of logs
        sys.stderr.write("%s %s\n" % (self.address_string(), (fmt % args).split("?")[0]))

    def _authed(self) -> bool:
        q = parse_qs(urlparse(self.path).query)
        given = self.headers.get("X-Token") or (q.get("t") or [""])[0]
        return hmac.compare_digest(given.encode(), self.token.encode())

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, obj: dict) -> None:
        self._send(status, json.dumps(obj).encode(), "application/json")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/favicon.ico":  # browsers ask without the token; nothing to leak
            return self._send(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
        if not self._authed():
            return self._json(HTTPStatus.UNAUTHORIZED, {"error": "bad token"})
        if path == "/":
            return self._send(HTTPStatus.OK, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/health":
            return self._json(HTTPStatus.OK, {"ok": True})
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._authed():
            return self._json(HTTPStatus.UNAUTHORIZED, {"error": "bad token"})
        if urlparse(self.path).path != "/api/sketch":
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BYTES:
            return self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": f"body must be 1..{MAX_BYTES} bytes"})
        png = self.rfile.read(length)
        if not png.startswith(PNG_MAGIC):
            return self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "not a PNG"})
        caption = unquote(self.headers.get("X-Caption", ""))[:MAX_CAPTION]
        name = save_sketch(self.out_dir, png, caption)
        print(f"saved {name} ({len(png)} bytes, caption {len(caption)} chars)", file=sys.stderr, flush=True)
        self._json(HTTPStatus.OK, {"ok": True, "name": name})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lan", action="store_true", help="listen on all interfaces (token still required)")
    ap.add_argument("--host", help="explicit bind address (overrides Tailscale/--lan)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="where sketches are saved")
    args = ap.parse_args()

    if args.host:
        host = args.host
    elif args.lan:
        host = "0.0.0.0"
    else:
        host = tailscale_ip()
        if not host:
            print("Tailscale has no IPv4 address (is it running? `/ts on` over Telegram).\n"
                  "Use --lan for the Wi-Fi address instead.", file=sys.stderr)
            return 2

    Handler.token = load_token()
    Handler.out_dir = args.dir.expanduser()
    httpd = ThreadingHTTPServer((host, args.port), Handler)
    print(f"sketchpad on http://{host}:{args.port}/?t=<token>  ->  {Handler.out_dir}", file=sys.stderr, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
