/* Пульт контента v4: один продукт на экране, переключение табами.
   Слева — «сегодня к выпуску» и очередь, справа — статистика выбранного продукта. */

const TILE_DEFS = {
  grailert: [
    ["bot.users", "пользователей бота"],
    ["bot.paying", "платящих сейчас"],
    ["bot.usdt", "получено USDT", (v) => "$" + fmt(v, 2)],
    ["bot.stars", "получено Stars", (v) => fmt(v) + " ⭐"],
    ["tg.subscribers", "подписчиков TG"],
    ["ig.followers", "подписчиков IG"],
    ["fb.followers", "подписчиков FB"],
  ],
  acme: [
    ["bot.users", "пользователей бота"],
    ["bot.subs", "активных подписок"],
    ["bot.paid_cnt", "оплат всего"],
    ["bot.revenue", "выручка, ₽", (v) => fmt(v) + " ₽"],
    ["tg.subscribers", "подписчиков TG"],
    ["ig.followers", "подписчиков IG"],
  ],
};

const CHART_DEFS = [
  ["bot.users", "Пользователи бота"],
  ["tg.subscribers", "Подписчики Telegram"],
  ["ig.followers", "Подписчики Instagram"],
];

const STATUS_NEXT = { made: "scheduled", scheduled: "published" };
const STATUS_RU = { made: "сделан", scheduled: "запланирован", published: "опубликован" };
const NEXT_RU = { made: "→ в план", scheduled: "→ вышел" };
const PLATFORM_RU = { reels: "Reels", tiktok: "TikTok", tg: "Telegram", fb: "Facebook", reddit: "Reddit" };
const PRODUCT_RU = { grailert: "Grailert", acme: "Acme" };

let PRODUCT = "grailert";
try { PRODUCT = localStorage.getItem("hub_tab") || "grailert"; } catch (e) {}
if (!TILE_DEFS[PRODUCT]) PRODUCT = "grailert";

let DATA = null;      // последний ответ /api/overview
let OPEN_EDIT = null; // id открытого редактора

function fmt(v, digits = 0) {
  if (v == null) return "—";
  return Number(v).toLocaleString("ru-RU", { maximumFractionDigits: digits });
}

function esc(s) {
  return String(s == null ? "" : s)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function ago(ts) {
  if (!ts) return "";
  const d = Math.floor(Date.now() / 1000 - ts);
  if (d < 90) return "только что";
  if (d < 3600) return Math.floor(d / 60) + " мин назад";
  if (d < 86400) return Math.floor(d / 3600) + " ч назад";
  return Math.floor(d / 86400) + " дн назад";
}

async function api(path, body) {
  const r = await fetch(path, body === undefined ? undefined : {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.status === 401) { location.reload(); throw new Error("auth"); }
  return r.json();
}

function todayStr(offset = 0) {
  const d = new Date(Date.now() + offset * 86400000);
  return d.toISOString().slice(0, 10);
}

/* ---------- статистика (правая колонка) ---------- */

function sparkline(points) {
  if (!points || points.length < 2) return null;
  const W = 260, H = 52, P = 4;
  const xs = points.map((p) => p[0]), ys = points.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = Math.min(...ys), y1 = Math.max(...ys);
  const sx = (x) => P + ((x - x0) / Math.max(1, x1 - x0)) * (W - 2 * P);
  const sy = (y) => H - P - ((y - y0) / Math.max(1, y1 - y0)) * (H - 2 * P);
  const line = points.map((p, i) => (i ? "L" : "M") + sx(p[0]).toFixed(1) + " " + sy(p[1]).toFixed(1)).join(" ");
  const area = line + ` L${sx(x1).toFixed(1)} ${H - 1} L${sx(x0).toFixed(1)} ${H - 1} Z`;
  const last = points[points.length - 1];
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img">
    <path class="spark-fill" d="${area}"/><path class="spark" d="${line}"/>
    <circle class="spark-dot" cx="${sx(last[0]).toFixed(1)}" cy="${sy(last[1]).toFixed(1)}" r="3"/></svg>`;
}

function renderStats() {
  const p = DATA.products[PRODUCT];
  document.getElementById("stats-title").textContent = "Статистика · " + PRODUCT_RU[PRODUCT];

  const tiles = document.getElementById("tiles");
  tiles.innerHTML = "";
  for (const [key, label, format] of TILE_DEFS[PRODUCT]) {
    const v = p.tiles[key];
    const el = document.createElement("div");
    if (v == null) {
      el.className = "tile off";
      el.innerHTML = `<div class="v">не подключено</div><div class="k">${esc(label)}</div>`;
    } else {
      el.className = "tile";
      el.innerHTML = `<div class="v num">${format ? format(v) : fmt(v)}</div><div class="k">${esc(label)}</div>`;
    }
    tiles.appendChild(el);
  }

  const charts = document.getElementById("charts");
  charts.innerHTML = "";
  for (const [key, label] of CHART_DEFS) {
    const pts = p.series[key];
    const svg = sparkline(pts);
    if (!svg) continue;
    const el = document.createElement("div");
    el.className = "chart";
    el.innerHTML = `<div class="t"><span>${esc(label)}</span>
      <span class="num">${fmt(pts[pts.length - 1][1])}</span></div>${svg}`;
    charts.appendChild(el);
  }

  document.getElementById("sources-title").textContent =
    PRODUCT === "grailert" ? "Каналы привлечения" : "Источники стартов";
  const tb = document.querySelector("#src tbody");
  tb.innerHTML = "";
  const rows = p.sources || [];
  for (const r of rows.slice(0, 12)) {
    const money = PRODUCT === "grailert"
      ? [r.stars ? fmt(r.stars) + "⭐" : "", r.usdt ? "$" + fmt(r.usdt, 2) : ""].filter(Boolean).join(" + ")
      : r.revenue != null ? fmt(r.revenue) + " ₽" : "";
    tb.insertAdjacentHTML("beforeend",
      `<tr><td>${esc(r.src || r.source || "—")}</td>
       <td class="num">${fmt(r.users ?? r.starts)}</td>
       <td class="num">${fmt(r.paying ?? r.paid)}</td>
       <td class="num">${money || "—"}</td></tr>`);
  }
  if (!rows.length)
    tb.innerHTML = `<tr><td colspan="4" class="empty">Появится с первыми переходами</td></tr>`;

  const media = p.media || [];
  const mtb = document.querySelector("#media tbody");
  mtb.innerHTML = "";
  document.getElementById("media-empty").hidden = media.length > 0;
  document.getElementById("media").hidden = media.length === 0;
  for (const m of media.slice(0, 10)) {
    mtb.insertAdjacentHTML("beforeend",
      `<tr><td>${esc((m.title || "без подписи").slice(0, 46))}</td>
       <td class="num">${fmt(m.views)}</td><td class="num">${fmt(m.likes)}</td>
       <td class="num">${fmt(m.comments)}</td></tr>`);
  }

  const NAMES = { bot: "Бот", tg: "Telegram", ig: "Instagram", fb: "Facebook" };
  const box = document.getElementById("pulls");
  box.innerHTML = "";
  const mine = (DATA.pulls || []).filter((x) => x.source.startsWith(PRODUCT + ":"));
  const seen = new Set(mine.map((x) => x.source.split(":")[1]));
  for (const x of mine) {
    const kind = x.source.split(":")[1];
    box.insertAdjacentHTML("beforeend",
      `<div class="pull"><span class="dot ${x.ok ? "ok" : "bad"}"></span>
       <span class="who">${esc(NAMES[kind] || kind)}</span>
       <span class="when">${ago(x.ts)}</span></div>`);
  }
  const expect = PRODUCT === "grailert" ? ["bot", "tg", "ig", "fb"] : ["bot", "tg", "ig"];
  for (const kind of expect) {
    if (!seen.has(kind))
      box.insertAdjacentHTML("beforeend",
        `<div class="pull"><span class="dot off"></span>
         <span class="who">${esc(NAMES[kind])}</span><span class="when">не подключён</span></div>`);
  }
}

/* ---------- очередь (левая колонка) ---------- */

function dateChip(c) {
  if (c.status === "published" || !c.scheduled_for) return "";
  const t = todayStr(), tm = todayStr(1);
  let cls = "datechip", label = c.scheduled_for.slice(5).split("-").reverse().join(".");
  if (c.scheduled_for === t) { cls += " today"; label = "сегодня"; }
  else if (c.scheduled_for === tm) { label = "завтра"; }
  else if (c.scheduled_for < t) { cls += " overdue"; label = "просрочен · " + label; }
  return `<span class="chip ${cls}">${label}</span>`;
}

function card(c, compact = false) {
  const hasVideo = c.filename && c.filename.endsWith(".mp4");
  const hasFile = Boolean(c.filename);
  const next = STATUS_NEXT[c.status];
  const editing = OPEN_EDIT === c.id;
  return `
  <article class="ccard ${compact ? "compact" : ""}" data-id="${c.id}">
    <div class="cmedia">
      ${hasVideo
        ? `<video src="/file/${esc(c.filename)}?inline=1" controls preload="metadata" playsinline></video>`
        : hasFile
          ? `<img src="/file/${esc(c.filename)}?inline=1" alt="">`
          : (c.caption && !["reels","tiktok"].includes(c.platform)
              ? `<div class="nofile textpost">📝 текстовый пост<span>файл не нужен —\nкопируй подпись</span></div>`
              : `<div class="nofile making">🎬 ролик в производстве<span>файл появится здесь</span></div>`)}
    </div>
    <div class="cbody">
      <div class="crow1">
        <span class="st st-${c.status}">${STATUS_RU[c.status]}</span>
        ${dateChip(c)}
        ${c.hook ? `<span class="chip hookchip">${esc(c.hook)}</span>` : ""}
        <span class="muted">#${c.id} · ${PLATFORM_RU[c.platform] || esc(c.platform)}</span>
        ${c.status === "published" && (c.m_views || c.m_likes)
          ? `<span class="muted num">24ч: ${fmt(c.m_views)} 👁 · ${fmt(c.m_likes)} ❤</span>` : ""}
      </div>
      <div class="ctitle">${esc(c.title)}</div>
      ${c.post_error ? `<div class="cerr">не опубликовано: ${esc(c.post_error)}</div>` : ""}
      ${c.music ? `<div class="cmusic">♪ ${esc(c.music)}</div>` : ""}
      ${c.caption && !compact ? `<div class="ccaption">${esc(c.caption)}</div>` : ""}
      <div class="cactions">
        ${hasFile ? `<a class="btn stbtn" href="/file/${esc(c.filename)}" download>Скачать</a>` : ""}
        ${c.caption ? `<button class="btn stbtn" data-copy="${c.id}">Скопировать подпись</button>` : ""}
        <button class="btn stbtn" data-edit="${c.id}">${editing ? "Свернуть" : "Изменить"}</button>
        ${next ? `<button class="btn stbtn hot" data-status="${next}" data-id="${c.id}">${NEXT_RU[c.status]}</button>` : ""}
        ${c.status !== "published" ? `<button class="btn stbtn" data-postnow="${c.id}">Опубликовать сейчас</button>` : ""}
        ${compact ? "" : `<button class="btn stbtn danger" data-del="${c.id}">Удалить</button>`}
      </div>
      ${editing ? editForm(c) : ""}
    </div>
  </article>`;
}

function editForm(c) {
  return `
  <div class="editbox" data-editbox="${c.id}">
    <label>Название<input name="title" value="${esc(c.title)}"></label>
    <label>Подпись (копируется при публикации)
      <textarea name="caption" rows="5">${esc(c.caption)}</textarea></label>
    <label>Звук — что искать при загрузке
      <input name="music" value="${esc(c.music)}"></label>
    <div class="editrow">
      <label>Дата выхода<input type="date" name="scheduled_for" value="${esc(c.scheduled_for)}"></label>
      <label>Время (МСК)<input type="time" name="post_time" value="${esc(c.post_time || "12:00")}"></label>
    </div>
    <div class="editrow">
      <label>Хук (для A/B)<input name="hook" value="${esc(c.hook)}"></label>
      <label class="chkline"><input type="checkbox" name="auto" ${c.auto === 0 ? "" : "checked"}>
        Публиковать самому в срок</label>
    </div>
    <label>Ссылка на опубликованный пост
      <input name="url" value="${esc(c.url)}" placeholder="https://…"></label>
    <div class="editrow">
      <label>Просмотры за 24ч<input type="number" min="0" name="m_views" value="${c.m_views || ""}"></label>
      <label>Лайки за 24ч<input type="number" min="0" name="m_likes" value="${c.m_likes || ""}"></label>
    </div>
    <label>Файл (mp4 / png / jpg, до 120 МБ)
      <input type="file" name="file" accept="video/mp4,image/png,image/jpeg"></label>
    <div class="editactions">
      <button class="btn hot" data-save="${c.id}">Сохранить</button>
      <span class="muted" data-msg="${c.id}"></span>
    </div>
  </div>`;
}

function groupLabel(c) {
  if (c.status === "published") return "Вышло";
  const t = todayStr(), tm = todayStr(1);
  if (!c.scheduled_for) return "Без даты";
  if (c.scheduled_for <= t) return "Сегодня";
  if (c.scheduled_for === tm) return "Завтра";
  return "Позже";
}

const GROUP_ORDER = ["Сегодня", "Завтра", "Позже", "Без даты", "Вышло"];

function renderQueue() {
  const content = (DATA.content || []).filter((c) => c.product === PRODUCT);
  const sorted = [...content].sort((a, b) =>
    (a.scheduled_for || "9999").localeCompare(b.scheduled_for || "9999") || a.id - b.id);

  // «Сегодня к выпуску» — задачи дня отдельной панелью сверху
  const today = sorted.filter((c) => groupLabel(c) === "Сегодня");
  const tl = document.getElementById("today-list");
  tl.innerHTML = today.length
    ? today.map((c) => card(c, true)).join("")
    : `<p class="empty">На сегодня всё выпущено 🎉</p>`;
  document.getElementById("today-count").textContent =
    today.length ? `${today.length} к выпуску` : "";

  // остальная очередь — сегодняшние не дублируем
  const rest = sorted.filter((c) => groupLabel(c) !== "Сегодня");
  const groups = new Map(GROUP_ORDER.map((g) => [g, []]));
  for (const c of rest) groups.get(groupLabel(c)).push(c);
  const box = document.getElementById("queue-list");
  const html = GROUP_ORDER
    .filter((g) => g !== "Сегодня" && groups.get(g).length)
    .map((g) => `<div class="qgroup"><div class="qgroup-h">${g}
      <span class="muted">${groups.get(g).length}</span></div>
      ${groups.get(g).map((c) => card(c)).join("")}</div>`)
    .join("");
  box.innerHTML = html || `<p class="empty">Дальше очередь пуста — добавь ролик формой выше</p>`;

  const q = DATA.products[PRODUCT].queue || {};
  document.getElementById("queue-summary").textContent =
    `сделано ${q.made || 0} · в плане ${q.scheduled || 0} · вышло ${q.published || 0}`;
}

let OPEN_TASK = null; // id развёрнутой задачи

function taskCard(t) {
  let body = { steps: [], texts: [] };
  try { body = JSON.parse(t.body || "{}"); } catch (e) {}
  const open = OPEN_TASK === t.id;
  return `
  <div class="task ${t.done ? "done" : ""}" data-tid="${t.id}">
    <div class="task-head">
      <label class="task-check"><input type="checkbox" data-act="toggle" ${t.done ? "checked" : ""}></label>
      <button class="task-title" data-act="open">${esc(t.title)}</button>
      <span class="task-arrow">${open ? "▾" : "▸"}</span>
    </div>
    ${open ? `<div class="task-body">
      ${(body.steps || []).length
        ? `<ol class="task-steps">${body.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>` : ""}
      ${(body.texts || []).map((x, i) => `
        <div class="task-text">
          <div class="task-text-h"><span>${esc(x.label)}</span>
            <button class="btn stbtn" data-act="copytext" data-i="${i}">Скопировать</button></div>
          <pre>${esc(x.value)}</pre>
        </div>`).join("")}
    </div>` : ""}
  </div>`;
}

function renderTasks() {
  const all = (DATA.tasks || []).filter((t) => t.product === PRODUCT);
  const doneN = all.filter((t) => t.done).length;
  document.getElementById("tasks-count").textContent =
    all.length ? `готово ${doneN} из ${all.length}` : "";
  document.getElementById("tasks-list").innerHTML = all.length
    ? all.map(taskCard).join("")
    : `<p class="empty">Задач нет — всё запущено.</p>`;
}

document.getElementById("tasks-list").addEventListener("click", async (e) => {
  const box = e.target.closest(".task");
  if (!box) return;
  const id = Number(box.dataset.tid);
  const t = (DATA.tasks || []).find((x) => x.id === id);
  if (!t) return;
  const act = e.target.closest("[data-act]");
  if (act && act.dataset.act === "toggle") {
    t.done = e.target.checked ? 1 : 0;
    await api("/api/task/toggle", { id, done: Boolean(t.done) });
    renderTasks();
    return;
  }
  if (act && act.dataset.act === "copytext") {
    let body = { texts: [] };
    try { body = JSON.parse(t.body || "{}"); } catch (err) {}
    const x = (body.texts || [])[Number(act.dataset.i)];
    if (x) {
      try { await navigator.clipboard.writeText(x.value); act.textContent = "Скопировано ✓";
        setTimeout(() => { act.textContent = "Скопировать"; }, 1500); } catch (err) {}
    }
    return;
  }
  OPEN_TASK = OPEN_TASK === id ? null : id;
  renderTasks();
});

function renderAll() {
  if (!DATA) return;
  document.querySelectorAll(".tab").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === PRODUCT));
  renderStats();
  renderTasks();
  renderQueue();
  document.getElementById("updated").textContent =
    "Данные: " + new Date(DATA.generated * 1000).toLocaleTimeString("ru-RU").slice(0, 5) + ".";
}

async function load() {
  DATA = await api("/api/overview");
  renderAll();
}

/* ---------- события ---------- */

document.getElementById("tabs").addEventListener("click", (e) => {
  const b = e.target.closest(".tab");
  if (!b) return;
  PRODUCT = b.dataset.tab;
  OPEN_EDIT = null;
  try { localStorage.setItem("hub_tab", PRODUCT); } catch (err) {}
  renderAll();
});

document.getElementById("refresh").addEventListener("click", async (e) => {
  e.target.disabled = true; e.target.textContent = "Собираю…";
  await api("/api/refresh", {});
  setTimeout(async () => { await load(); e.target.disabled = false; e.target.textContent = "Обновить"; }, 4000);
});

document.getElementById("addform").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  await api("/api/queue/add", {
    product: PRODUCT, platform: f.get("platform"), title: f.get("title"),
  });
  e.target.reset();
  load();
});

async function handleCardClick(e) {
  const t = e.target;
  if (t.dataset.edit) {
    const id = Number(t.dataset.edit);
    OPEN_EDIT = OPEN_EDIT === id ? null : id;
    renderAll();
    return;
  }
  if (t.dataset.copy) {
    const c = DATA.content.find((x) => x.id === Number(t.dataset.copy));
    if (c) {
      try { await navigator.clipboard.writeText(c.caption); t.textContent = "Скопировано ✓"; }
      catch (err) { t.textContent = "Открой «Изменить» и скопируй"; }
      setTimeout(() => (t.textContent = "Скопировать подпись"), 1800);
    }
    return;
  }
  if (t.dataset.status) {
    await api("/api/queue/status", { id: Number(t.dataset.id), status: t.dataset.status });
    load();
    return;
  }
  if (t.dataset.postnow) {
    const was = t.textContent;
    t.textContent = "Публикую…";
    t.disabled = true;
    const res = await api("/api/queue/post_now", { id: Number(t.dataset.postnow) });
    t.disabled = false;
    if (res && res.ok) { load(); }
    else { t.textContent = (res && res.info) ? res.info.slice(0, 60) : "не вышло";
           setTimeout(() => (t.textContent = was), 4000); }
    return;
  }
  if (t.dataset.del) {
    if (!confirm("Удалить запись вместе с файлом?")) return;
    await api("/api/queue/delete", { id: Number(t.dataset.del) });
    OPEN_EDIT = null;
    load();
    return;
  }
  if (t.dataset.save) {
    const id = Number(t.dataset.save);
    const box = document.querySelector(`[data-editbox="${id}"]`);
    const msg = box.querySelector(`[data-msg="${id}"]`);
    msg.textContent = "Сохраняю…";
    const res0 = await api("/api/queue/edit", {
      id,
      title: box.querySelector('[name="title"]').value,
      caption: box.querySelector('[name="caption"]').value,
      music: box.querySelector('[name="music"]').value,
      url: box.querySelector('[name="url"]').value,
      scheduled_for: box.querySelector('[name="scheduled_for"]').value,
      post_time: box.querySelector('[name="post_time"]').value || "12:00",
      auto: box.querySelector('[name="auto"]').checked ? 1 : 0,
      hook: box.querySelector('[name="hook"]').value,
      m_views: box.querySelector('[name="m_views"]').value,
      m_likes: box.querySelector('[name="m_likes"]').value,
    });
    if (res0 && res0.error) { msg.textContent = res0.error; return; }
    const file = box.querySelector('[name="file"]').files[0];
    if (file) {
      msg.textContent = "Заливаю файл…";
      const r = await fetch(`/api/upload/${id}`, {
        method: "POST", headers: { "Content-Type": file.type }, body: file,
      });
      const res = await r.json();
      if (res.error) { msg.textContent = "Файл: " + res.error; return; }
    }
    msg.textContent = "Сохранено ✓";
    OPEN_EDIT = null;
    setTimeout(load, 400);
  }
}
document.getElementById("queue-list").addEventListener("click", handleCardClick);
document.getElementById("today-list").addEventListener("click", handleCardClick);

load();
setInterval(() => { if (OPEN_EDIT === null) load(); }, 120000);
