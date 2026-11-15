#!/usr/bin/env python3
"""Проставляет в ссылках на статику версию по содержимому файла.

Зачем: статика отдаётся с кешем на сутки, и если версия в ссылке зашита руками,
после выкатки половина посетителей продолжает видеть старый сайт. Здесь версия
считается из самого файла — поменялся файл, поменялась ссылка, кеш обновился сам.

Запуск:  python3 stamp_assets.py   (делается перед деплоем)
"""
from __future__ import annotations

import hashlib
import io
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BASE, "site")

# Ссылки вида /assets/имя.ext?v=что-угодно
LINK = re.compile(r'(/assets/[A-Za-z0-9_.-]+\.(?:css|js))(\?v=[^"\']*)?')


def digest(rel_path: str) -> str | None:
    full = os.path.join(SITE, rel_path.lstrip("/"))
    if not os.path.isfile(full):
        return None
    with open(full, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def main() -> None:
    changed = 0
    for name in sorted(os.listdir(SITE)):
        if not name.endswith(".html"):
            continue
        path = os.path.join(SITE, name)
        src = io.open(path, encoding="utf-8").read()

        def repl(m: re.Match) -> str:
            d = digest(m.group(1))
            return m.group(1) + (f"?v={d}" if d else "")

        out = LINK.sub(repl, src)
        if out != src:
            io.open(path, "w", encoding="utf-8").write(out)
            changed += 1
            print("обновлены версии в", name)
    print(f"готово, файлов изменено: {changed}")
    for asset in ("assets/styles.css", "assets/i18n.js", "assets/app.js"):
        print(f"  {asset} → v={digest('/' + asset)}")


if __name__ == "__main__":
    main()
