#!/usr/bin/env python3
"""Sketchpad server: tablet draws, laptop saves a PNG (+ caption) for Claude to read.

Stdlib only. Every request needs the secret token. By default it listens on the
Tailscale address only; --also-lan adds the Wi-Fi/LAN address (plain HTTP). Addresses
are bound one by one (never 0.0.0.0 unless --lan) and re-checked every few seconds, so
Tailscale coming up later, or the Wi-Fi address changing, just works.
"""
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
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
PAGE_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
VIEWPORT = re.compile(r"^\d{2,5}x\d{2,5}$")
# Pages are plain files written by Claude into <sketch dir>/pages/<name>/ (index.html + assets). They run in a sandboxed iframe with NO same-origin
# access (CSP sandbox + the iframe's own sandbox attribute), so a page can run scripts but cannot read the token or call the sketchpad API.
# A page can only load its own files (+ data:/blob:), cannot fetch/XHR/WebSocket anywhere, cannot post forms or change <base>: even a page that
# includes untrusted code has nowhere to send what it can see.
PAGE_CSP = ("sandbox allow-scripts; default-src 'self' data: blob: 'unsafe-inline' 'unsafe-eval'; connect-src 'none'; form-action 'none'; base-uri 'none'")
CAP_TTL = 12 * 3600  # a page capability lives this long (seconds)


def page_cap(token: str, name: str, expiry: int) -> str:
    """Short-lived, read-only capability for ONE page: HMAC(token, page name + expiry). It is accepted only by the /p/ file route, never by /api/*,
    so the long-lived token never appears in a page URL (page scripts can read their own URL)."""
    mac = hmac.new(token.encode(), f"page:{name}:{expiry}".encode(), "sha256").hexdigest()[:32]
    return f"{expiry}.{mac}"


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


def lan_ip() -> str | None:
    """The address of the default route (Wi-Fi/Ethernet). No packet is sent; Tailscale's own range is skipped."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
            sk.connect(("10.255.255.255", 1))
            ip = sk.getsockname()[0]
    except OSError:
        return None
    a = ip.split(".")
    if ip.startswith("127.") or (a[0] == "100" and 64 <= int(a[1]) <= 127):
        return None
    return ip


class Listeners:
    """One ThreadingHTTPServer per wanted address; sync() opens new ones and closes ones no longer wanted."""

    def __init__(self, port: int) -> None:
        self.port, self.servers, self.failed = port, {}, set()

    def sync(self, wanted: set[str]) -> None:
        for host in [h for h in self.servers if h not in wanted]:
            srv = self.servers.pop(host)
            srv.shutdown()
            srv.server_close()
            print(f"sketchpad: stopped listening on {host}", file=sys.stderr, flush=True)
        for host in sorted(wanted - set(self.servers)):
            try:
                srv = ThreadingHTTPServer((host, self.port), Handler)
            except OSError as e:  # e.g. Tailscale is off: its address is known but not assigned yet. Say so once, keep retrying quietly
                if host not in self.failed:
                    self.failed.add(host)
                    print(f"sketchpad: cannot listen on {host}:{self.port} yet ({e.strerror}); will keep retrying", file=sys.stderr, flush=True)
                continue
            self.failed.discard(host)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            self.servers[host] = srv
            print(f"sketchpad on http://{host}:{self.port}/?t=<token>  ->  {Handler.out_dir}", file=sys.stderr, flush=True)


def list_pages(pages_dir: Path, token: str = "") -> list[dict]:
    out = []
    if pages_dir.is_dir():
        for d in sorted(pages_dir.iterdir()):
            idx = d / "index.html"
            if d.is_dir() and PAGE_NAME.match(d.name) and idx.is_file():
                m = re.search(r"<title>(.*?)</title>", idx.read_text(errors="replace")[:4000], re.I | re.S)
                out.append({"name": d.name, "title": (m.group(1).strip() if m else d.name)[:80],
                            "path": f"/p/{page_cap(token, d.name, int(time.time()) + CAP_TTL)}/{d.name}/"})
    return out


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

    def log_message(self, fmt: str, *args) -> None:  # keep the token out of logs, keep the status
        line = re.sub(r"([?&]t=)[^ &\"]*", r"\1<token>", fmt % args)
        line = re.sub(r"(/p/)[^/ \"]+", r"\1<cap>", line)  # page URLs carry a short-lived capability in the path
        sys.stderr.write("%s %s\n" % (self.address_string(), line))

    def _authed(self) -> bool:
        q = parse_qs(urlparse(self.path).query)
        given = self.headers.get("X-Token") or (q.get("t") or [""])[0]
        return hmac.compare_digest(given.encode(), self.token.encode())

    def _send(self, status: int, body: bytes, ctype: str, headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
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
        m = re.match(r"^/p/(\d{1,12})\.([0-9a-f]{32})/([A-Za-z0-9_.-]+)/(.*)$", path)
        if m:  # /p/<expiry>.<mac>/<page>/<file>: the capability is in the path so a page's relative links (css, js, images) keep working
            exp, name = int(m.group(1)), m.group(3)
            if exp < time.time() or not hmac.compare_digest(page_cap(self.token, name, exp).encode(), f"{m.group(1)}.{m.group(2)}".encode()):
                return self._json(HTTPStatus.UNAUTHORIZED, {"error": "bad or expired page link"})
            return self._serve_page(name, unquote(m.group(4)))
        if path.startswith("/p/"):  # anything else under /p/ (e.g. the old token-in-path form) is refused
            return self._json(HTTPStatus.UNAUTHORIZED, {"error": "bad or expired page link"})
        if not self._authed():
            return self._json(HTTPStatus.UNAUTHORIZED, {"error": "bad token"})
        if path == "/api/pages":
            return self._json(HTTPStatus.OK, {"pages": list_pages(self.out_dir / "pages", self.token)})
        if path == "/":
            tok = (parse_qs(urlparse(self.path).query).get("t") or [""])[0] or self.headers.get("X-Token", "")
            page = (HERE / "index.html").read_bytes().replace(b"__TOKEN__", re.sub(r"[^A-Za-z0-9_-]", "", tok).encode())  # the manifest/icon links carry the same token
            return self._send(HTTPStatus.OK, page, "text/html; charset=utf-8")
        if path == "/api/health":
            return self._json(HTTPStatus.OK, {"ok": True})
        if path == "/manifest.webmanifest":  # makes Chrome offer "Install app" (standalone window, no tab strip); needs a secure context = http://localhost over USB
            tok = (parse_qs(urlparse(self.path).query).get("t") or [""])[0]
            icons = [{"src": f"/icon-{n}.png?t={tok}", "sizes": f"{n}x{n}", "type": "image/png", "purpose": "any maskable"} for n in (192, 512)]
            manifest = {"name": "Sketchpad", "short_name": "Sketchpad", "id": "/", "start_url": f"/?t={tok}", "scope": "/",
                        "display": "standalone", "orientation": "any", "background_color": "#0f0a1a", "theme_color": "#1a1230", "icons": icons}
            return self._send(HTTPStatus.OK, json.dumps(manifest).encode(), "application/manifest+json")
        if path in ("/icon-192.png", "/icon-512.png"):
            return self._send(HTTPStatus.OK, (HERE / "icons" / path[1:]).read_bytes(), "image/png")
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _serve_page(self, name: str, rel: str) -> None:
        base = (self.out_dir / "pages" / name).resolve()
        target = (base / (rel or "index.html")).resolve() if not rel.endswith("/") else (base / rel / "index.html").resolve()
        if not base.is_dir() or not target.is_relative_to(base) or not target.is_file():  # no traversal, files only
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send(HTTPStatus.OK, target.read_bytes(), ctype, {"Content-Security-Policy": PAGE_CSP, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})

    def do_POST(self) -> None:
        if not self._authed():
            return self._json(HTTPStatus.UNAUTHORIZED, {"error": "bad token"})
        route = urlparse(self.path).path
        if route == "/api/debug":  # pen-event diagnostics from ?debug=1, logged JSON-escaped
            try:
                n = min(int(self.headers.get("Content-Length", "0")), 2048)
            except ValueError:
                n = 0
            msg = self.rfile.read(n).decode("utf-8", "replace")
            print("pen-debug " + json.dumps(msg), file=sys.stderr, flush=True)
            return self._json(HTTPStatus.OK, {"ok": True})
        if route != "/api/sketch":
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
        page, vp = self.headers.get("X-Page", ""), self.headers.get("X-Viewport", "")
        if page and PAGE_NAME.match(page) and VIEWPORT.match(vp):  # ink drawn over a page: remember which page and at what size, so it can be composited later
            (self.out_dir / f"{name}.json").write_text(json.dumps({"page": page, "viewport": vp, "ink": f"{name}.png"}))
        print(f"saved {name} ({len(png)} bytes, caption {len(caption)} chars)", file=sys.stderr, flush=True)
        self._json(HTTPStatus.OK, {"ok": True, "name": name})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lan", action="store_true", help="listen on ALL interfaces (token still required)")
    ap.add_argument("--also-lan", action="store_true", help="also listen on the Wi-Fi/LAN address (plain HTTP), in addition to Tailscale")
    ap.add_argument("--loopback", action="store_true", help="also listen on 127.0.0.1 (for `adb reverse` over a USB cable: nothing leaves the machine)")
    ap.add_argument("--host", help="explicit bind address(es), comma separated (overrides everything else)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="where sketches are saved")
    args = ap.parse_args()

    Handler.token = load_token()
    Handler.out_dir = args.dir.expanduser()

    def wanted() -> set[str]:
        if args.host:
            return {h.strip() for h in args.host.split(",") if h.strip()}
        if args.lan:
            return {"0.0.0.0"}
        out = {tailscale_ip()}
        if args.also_lan:
            out.add(lan_ip())
        if args.loopback:
            out.add("127.0.0.1")
        return {h for h in out if h}

    listeners = Listeners(args.port)
    waiting = False
    try:
        while True:
            want = wanted()
            listeners.sync(want)
            if not want and not waiting:
                print("sketchpad: no Tailscale/LAN address yet, waiting (Tailscale off? `/ts on` over Telegram)", file=sys.stderr, flush=True)
            waiting = not want
            time.sleep(8)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
