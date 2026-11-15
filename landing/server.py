#!/usr/bin/env python3
"""Лендинг Grailert: статика на стандартной библиотеке, без зависимостей.

Почему свой сервер, а не nginx: нужны чистые адреса (/faq вместо /faq.html),
заголовки безопасности и понятный контроль кеша — всё это здесь видно глазами,
в тридцати строках, и не тянет за собой конфиг чужого демона.

Переменные окружения: PORT (по умолчанию 3000).
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import mimetypes
import os
import posixpath
import re
import socketserver
import sys
import urllib.parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
PORT = int(os.environ.get("PORT", "3000"))

# Чистые адреса: то, что видит пользователь → файл на диске.
CLEAN = {
    "/faq": "/faq.html",
    "/safety": "/safety.html",
    "/terms": "/terms.html",
    "/privacy": "/privacy.html",
}

# Ничего служебного наружу не отдаём, даже если файл случайно окажется в site/.
BLOCKED = re.compile(r"(^|/)(\.|_|server\.py|Dockerfile|README|\.env)", re.I)

# Кеш: хешей в именах файлов нет, поэтому страницы не кешируем совсем,
# а статику держим сутки — с параметром ?v= в ссылках этого достаточно.
CACHE_SECONDS = {
    ".css": 86400, ".js": 86400, ".svg": 604800, ".png": 604800,
    ".ico": 604800, ".webmanifest": 86400, ".woff2": 2592000, ".xml": 3600,
}


def inline_script_hashes() -> str:
    """Считает sha256 всех встроенных <script> в html — для строгого CSP.

    Так строгую политику можно держать без 'unsafe-inline': на странице
    остаётся только блок JSON-LD для поисковиков, и его хеш вычисляется сам.
    Меняется разметка — меняется и политика, руками ничего править не нужно.
    """
    hashes = set()
    pattern = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)
    for name in os.listdir(ROOT):
        if not name.endswith(".html"):
            continue
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            for body in pattern.findall(f.read()):
                digest = hashlib.sha256(body.encode("utf-8")).digest()
                hashes.add("'sha256-" + base64.b64encode(digest).decode() + "'")
    return " ".join(sorted(hashes))


CSP = (
    "default-src 'self'; "
    "script-src 'self' " + inline_script_hashes() + "; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "form-action 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'"
)


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = "grailert"
    sys_version = ""

    def translate_path(self, path: str) -> str:
        path = urllib.parse.urlsplit(path).path
        path = urllib.parse.unquote(path)
        path = CLEAN.get(path.rstrip("/") or "/", path)
        if path.endswith("/"):
            path += "index.html"
        # posixpath.normpath режет попытки выйти из каталога через ../
        clean = posixpath.normpath(path).lstrip("/")
        return os.path.join(ROOT, clean)

    def end_headers(self) -> None:
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def do_GET(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        if path == "/healthz":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if BLOCKED.search(path):
            self.send_error(404)
            return
        super().do_GET()

    def send_head(self):
        """Добавляет кеш-заголовки и отдаёт свою страницу 404."""
        target = self.translate_path(self.path)
        if not os.path.isfile(target):
            return self.not_found()

        ext = os.path.splitext(target)[1].lower()
        ttl = CACHE_SECONDS.get(ext)
        try:
            f = open(target, "rb")
        except OSError:
            return self.not_found()
        size = os.fstat(f.fileno()).st_size
        ctype = mimetypes.guess_type(target)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/manifest+json"):
            ctype += "; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", f"public, max-age={ttl}" if ttl else "no-cache")
        self.end_headers()
        return f

    def not_found(self):
        page = os.path.join(ROOT, "404.html")
        if not os.path.isfile(page):
            self.send_error(404)
            return None
        f = open(page, "rb")
        size = os.fstat(f.fileno()).st_size
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        return f

    def log_message(self, fmt: str, *args) -> None:
        sys.stdout.write("%s %s\n" % (self.address_string(), fmt % args))
        sys.stdout.flush()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    mimetypes.add_type("application/manifest+json", ".webmanifest")
    mimetypes.add_type("image/svg+xml", ".svg")
    print(f"Grailert landing на :{PORT}, корень {ROOT}", flush=True)
    with Server(("", PORT), Handler) as httpd:
        httpd.serve_forever()
