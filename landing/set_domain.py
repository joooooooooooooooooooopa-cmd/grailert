#!/usr/bin/env python3
"""Меняет адрес сайта во всех ссылках (canonical, Open Graph, sitemap, robots).

В исходниках стоит адрес-заглушка https://grailert.example, а канонические
ссылки обязаны указывать на реальный адрес, иначе поисковик просто не сможет
проиндексировать сайт. Перед выкладкой выполнить с настоящим адресом:

    python3 set_domain.py https://your-domain.tld
"""
from __future__ import annotations

import io
import os
import re
import sys

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_pages.py")
CURRENT = re.compile(r"https://grailert\.example")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Укажи адрес: python3 set_domain.py https://example.com")
    new = sys.argv[1].rstrip("/")
    total = 0
    targets = [os.path.join(SITE, n) for n in os.listdir(SITE)
               if n.endswith((".html", ".xml", ".txt"))] + [BUILD]
    for path in targets:
        src = io.open(path, encoding="utf-8").read()
        out, n = CURRENT.subn(new, src)
        if n:
            io.open(path, "w", encoding="utf-8").write(out)
            total += n
            print(f"{os.path.basename(path)}: заменено {n}")
    print(f"итого ссылок обновлено: {total} → {new}")


if __name__ == "__main__":
    main()
