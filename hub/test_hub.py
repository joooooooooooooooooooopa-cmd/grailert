# -*- coding: utf-8 -*-
"""Тесты пульта: поднимаем сервер на временном порту и бьём по HTTP.

Запуск:  python3 test_hub.py
Проверяется то, что нельзя ловить руками: авторизация, кука, CRUD очереди,
загрузка/скачивание файлов, выход за каталог, чужие типы файлов.
"""
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse

TMP = tempfile.mkdtemp(prefix="hub_test_")
PORT = 8794
PASS, FAIL, FAILS = 0, 0, []


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        FAILS.append(name)
        print(f"  ❌ {name}   {extra}")


def req(method, path, body=None, headers=None, raw=False):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=10)
    hdrs = dict(headers or {})
    data = None
    if body is not None and not raw:
        data = json.dumps(body).encode()
        hdrs.setdefault("Content-Type", "application/json")
    elif raw:
        data = body
    c.request(method, path, data, hdrs)
    r = c.getresponse()
    payload = r.read()
    c.close()
    return r, payload


env = dict(os.environ,
           HUB_PASSWORD="tpass", HUB_SECRET="tsecret",
           DB_PATH=os.path.join(TMP, "hub.db"),
           FILES_DIR=os.path.join(TMP, "files"),
           PORT=str(PORT), COLLECT_EVERY="99999",
           HUB_STATS_TOKEN="",  # сборщики ботов выключены — тестируем сам сервер
           GRAILERT_BOT_TOKEN="", ACME_BOT_TOKEN="", META_TOKEN="")
proc = subprocess.Popen([sys.executable, "server.py"], env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try:
            r, _b = req("GET", "/healthz")
            if r.status == 200:
                break
        except OSError:
            time.sleep(0.2)
    else:
        sys.exit("сервер не поднялся")

    print("\n[A] Авторизация")
    r, b = req("GET", "/")
    check("без куки отдаётся форма входа", "Пульт контента" in b.decode())
    r, b = req("GET", "/api/overview")
    check("API без куки не отдаёт данные", b"tiles" not in b)
    r, _b = req("POST", "/login",
                urllib.parse.urlencode({"password": "wrong"}).encode(),
                {"Content-Type": "application/x-www-form-urlencoded"}, raw=True)
    check("неверный пароль не ставит куку", "Set-Cookie" not in dict(r.getheaders()))
    r, _b = req("POST", "/login",
                urllib.parse.urlencode({"password": "tpass"}).encode(),
                {"Content-Type": "application/x-www-form-urlencoded"}, raw=True)
    cookie = dict(r.getheaders()).get("Set-Cookie", "").split(";")[0]
    check("верный пароль ставит куку", cookie.startswith("hub="))
    AUTH = {"Cookie": cookie}
    r, b = req("GET", "/api/overview", headers=AUTH)
    check("API с кукой работает", r.status == 200 and b"products" in b)
    # кука с подделанной подписью
    r, b = req("GET", "/api/overview", headers={"Cookie": "hub=9999999999.deadbeef"})
    check("поддельная кука отклоняется", b"products" not in b)

    print("\n[B] Очередь")
    r, b = req("POST", "/api/queue/add", {"product": "grailert", "title": "Тестовый ролик",
                                          "platform": "reels"}, AUTH)
    check("запись добавляется", json.loads(b).get("ok"))
    r, b = req("POST", "/api/queue/add", {"product": "чужое", "title": "x"}, AUTH)
    check("неизвестный продукт отклоняется", r.status == 400)
    r, b = req("GET", "/api/overview", headers=AUTH)
    content = json.loads(b)["content"]
    cid = content[0]["id"]
    check("запись видна в обзоре", content[0]["title"] == "Тестовый ролик")

    r, b = req("POST", "/api/queue/edit", {"id": cid, "title": "Новое имя",
               "caption": "подпись #tag", "music": "trending ambient", "url": ""}, AUTH)
    check("правка сохраняется", json.loads(b).get("ok"))
    r, b = req("GET", "/api/overview", headers=AUTH)
    row = json.loads(b)["content"][0]
    check("подпись и звук изменились",
          row["caption"] == "подпись #tag" and row["music"] == "trending ambient", row)
    r, b = req("POST", "/api/queue/edit", {"id": 99999, "title": "x"}, AUTH)
    check("правка несуществующей записи — 404", r.status == 404)

    r, b = req("POST", "/api/queue/status", {"id": cid, "status": "hacked"}, AUTH)
    check("левый статус отклоняется", r.status == 400)
    r, b = req("POST", "/api/queue/status", {"id": cid, "status": "published"}, AUTH)
    check("статус двигается", json.loads(b).get("ok"))

    print("\n[C] Файлы")
    fake_mp4 = b"\x00\x00\x00\x18ftypmp42" + b"x" * 500
    r, b = req("POST", f"/api/upload/{cid}", fake_mp4,
               {"Content-Type": "video/mp4", **AUTH}, raw=True)
    res = json.loads(b)
    check("mp4 загружается", res.get("ok"), res)
    fname = res.get("filename", "")
    check("имя файла построено из id", fname == f"{cid}.mp4", fname)

    r, b = req("GET", f"/file/{fname}", headers=AUTH)
    check("файл скачивается целиком", r.status == 200 and b == fake_mp4)
    check("скачивание отдаёт attachment",
          "attachment" in dict(r.getheaders()).get("Content-Disposition", ""))
    r, b = req("GET", f"/file/{fname}?inline=1", headers=AUTH)
    check("предпросмотр без attachment",
          "attachment" not in dict(r.getheaders()).get("Content-Disposition", ""))

    r, b = req("GET", "/file/" + fname)  # без куки
    check("файл без авторизации не отдаётся", "Пульт контента" in b.decode(errors="ignore"))

    r, b = req("POST", f"/api/upload/{cid}", b"#!/bin/sh evil",
               {"Content-Type": "application/x-sh", **AUTH}, raw=True)
    check("посторонний тип файла отклоняется", r.status == 415)
    r, b = req("POST", "/api/upload/99999", fake_mp4,
               {"Content-Type": "video/mp4", **AUTH}, raw=True)
    check("загрузка в несуществующую запись — 404", r.status == 404)
    r, b = req("GET", "/file/..%2F..%2Fserver.py", headers=AUTH)
    check("выход за каталог файлов закрыт", b"BaseHTTPRequestHandler" not in b)

    print("\n[D] Удаление")
    r, b = req("POST", "/api/queue/delete", {"id": cid}, AUTH)
    check("запись удаляется", json.loads(b).get("ok"))
    files_left = os.listdir(os.path.join(TMP, "files"))
    check("файл удалился вместе с записью", fname not in files_left, files_left)
    r, b = req("GET", "/api/overview", headers=AUTH)
    check("очередь пуста", json.loads(b)["content"] == [])


    print("\n[E] Range для видео (без него iPhone не играет)")
    r, b = req("POST", "/api/queue/add", {"product": "acme", "title": "range-тест"}, AUTH)
    r, b = req("GET", "/api/overview", headers=AUTH)
    rid = json.loads(b)["content"][0]["id"]
    payload = bytes(range(256)) * 4  # 1024 байта с известным содержимым
    r, b = req("POST", f"/api/upload/{rid}", payload,
               {"Content-Type": "video/mp4", **AUTH}, raw=True)
    fname2 = json.loads(b)["filename"]

    r, b = req("GET", f"/file/{fname2}?inline=1", headers={**AUTH, "Range": "bytes=0-99"})
    check("частичный запрос отдаёт 206", r.status == 206, r.status)
    check("вернулись ровно первые 100 байт", b == payload[:100])
    check("Content-Range корректный",
          dict(r.getheaders()).get("Content-Range") == f"bytes 0-99/{len(payload)}")

    r, b = req("GET", f"/file/{fname2}?inline=1", headers={**AUTH, "Range": "bytes=1000-"})
    check("хвостовой диапазон работает", r.status == 206 and b == payload[1000:])
    r, b = req("GET", f"/file/{fname2}?inline=1", headers={**AUTH, "Range": "bytes=-24"})
    check("последние N байт работают", r.status == 206 and b == payload[-24:])
    r, b = req("GET", f"/file/{fname2}?inline=1", headers={**AUTH, "Range": "bytes=9999-"})
    check("диапазон за концом — 416", r.status == 416)
    r, b = req("GET", f"/file/{fname2}", headers=AUTH)
    check("без Range по-прежнему целиком и 200", r.status == 200 and b == payload)
    check("заголовок Accept-Ranges объявлен",
          dict(r.getheaders()).get("Accept-Ranges") == "bytes")
    req("POST", "/api/queue/delete", {"id": rid}, AUTH)


    print("\n[F] Иконка")
    r, b = req("GET", "/favicon.ico")  # без куки!
    check("фавиконка отдаётся без авторизации", r.status == 200 and b[:2] == b"\x00\x00")
    r, b = req("GET", "/apple-touch-icon.png")
    check("touch-иконка отдаётся без авторизации", r.status == 200 and b[:4] == b"\x89PNG")


    print("\n[G] Даты, хук, результаты")
    r, b = req("POST", "/api/queue/add", {"product": "grailert", "title": "с датой"}, AUTH)
    r, b = req("GET", "/api/overview", headers=AUTH)
    did = json.loads(b)["content"][0]["id"]
    r, b = req("POST", "/api/queue/edit",
               {"id": did, "title": "с датой", "caption": "", "music": "", "url": "",
                "scheduled_for": "2026-09-05", "hook": "вопрос",
                "m_views": "1200", "m_likes": "77"}, AUTH)
    check("правка с новыми полями проходит", json.loads(b).get("ok"))
    r, b = req("GET", "/api/overview", headers=AUTH)
    row = [c for c in json.loads(b)["content"] if c["id"] == did][0]
    check("дата сохранилась", row["scheduled_for"] == "2026-09-05")
    check("хук сохранился", row["hook"] == "вопрос")
    check("результаты числа", row["m_views"] == 1200 and row["m_likes"] == 77)
    r, b = req("POST", "/api/queue/edit",
               {"id": did, "title": "x", "scheduled_for": "05.09.2026"}, AUTH)
    check("кривая дата отклоняется", r.status == 400)
    r, b = req("POST", "/api/queue/edit",
               {"id": did, "title": "x", "m_views": "мусор"}, AUTH)
    check("мусор в числах не роняет (становится 0)", json.loads(b).get("ok"))
    req("POST", "/api/queue/delete", {"id": did}, AUTH)

    print("\n[H] Чек-лист запуска")
    r, b = req("POST", "/api/task/add",
               {"product": "grailert", "title": "Тестовая задача",
                "body": '{"steps":["шаг 1"],"texts":[{"label":"Текст","value":"скопируй меня"}]}'},
               AUTH)
    check("задача добавляется", json.loads(b).get("ok"))
    r, b = req("POST", "/api/task/add", {"product": "grailert", "title": ""}, AUTH)
    check("задача без названия — 400", r.status == 400)
    r, b = req("POST", "/api/task/add", {"title": "т"}, None)
    check("задача без куки — 401", r.status == 401)
    r, b = req("GET", "/api/overview", headers=AUTH)
    tasks = json.loads(b)["tasks"]
    tid = [t for t in tasks if t["title"] == "Тестовая задача"][0]["id"]
    check("задача видна в обзоре и не готова",
          [t for t in tasks if t["id"] == tid][0]["done"] == 0)
    r, b = req("POST", "/api/task/toggle", {"id": tid, "done": True}, AUTH)
    check("галочка ставится", json.loads(b).get("ok"))
    r, b = req("GET", "/api/overview", headers=AUTH)
    check("готовность сохранилась",
          [t for t in json.loads(b)["tasks"] if t["id"] == tid][0]["done"] == 1)
    r, b = req("POST", "/api/task/toggle", {"id": tid, "done": False}, AUTH)
    r, b = req("GET", "/api/overview", headers=AUTH)
    check("галочка снимается",
          [t for t in json.loads(b)["tasks"] if t["id"] == tid][0]["done"] == 0)
    r, b = req("POST", "/api/task/toggle", {"id": tid}, None)
    check("toggle без куки — 401", r.status == 401)

finally:
    proc.terminate()
    proc.wait(timeout=5)
    shutil.rmtree(TMP, ignore_errors=True)

print("\n[Z] Сборщик: пустой адрес статистики не опрашивается")
# Адрес второго продукта по умолчанию пуст; раньше уходил запрос на «?token=…»
# без хоста и в пульте висело «нет ответа».
_tmp2 = tempfile.mkdtemp(prefix="hub_unit_")
try:
    os.environ.update(HUB_STATS_TOKEN="t", DB_PATH=os.path.join(_tmp2, "hub.db"),
                      FILES_DIR=os.path.join(_tmp2, "files"))
    import server  # noqa: E402
    _calls = []
    server._get_json = lambda url, timeout=20: _calls.append(url) or None
    server.pull_bot("acme", "")
    check("пустой URL — ни одного запроса", _calls == [], _calls)
    server.pull_bot("acme", "http://stats.local/hub/stats")
    check("заданный URL опрашивается", len(_calls) == 1, _calls)
finally:
    shutil.rmtree(_tmp2, ignore_errors=True)

print("\n" + "=" * 46)
print(f"ИТОГО: ✅ {PASS} прошло   ❌ {FAIL} упало")
for f in FAILS:
    print("  •", f)
print("=" * 46)
sys.exit(1 if FAIL else 0)
