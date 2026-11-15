/* ---------- переключатель языка ---------- */
(function () {
  const btn = document.getElementById("langBtn");
  const menu = document.getElementById("langMenu");

  menu.innerHTML = Object.entries(LANGS).map(
    ([code, name]) => `<button data-lang="${code}" type="button">${name}</button>`
  ).join("");

  const close = () => { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); };
  close();

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.hidden = !menu.hidden;
    btn.setAttribute("aria-expanded", String(!menu.hidden));
  });
  menu.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-lang]");
    if (!b) return;
    applyLang(b.dataset.lang);
    close();
  });
  document.addEventListener("click", close);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });

  applyLang(detectLang());
})();

/* ---------- лента алертов ----------
   Главный аргумент продукта — скорость. Её честнее показать, чем описать:
   карточки приходят одна за другой, у каждой отметка, через сколько секунд
   после публикации объявление было замечено. */
(function () {
  const feed = document.getElementById("feed");
  if (!feed) return;

  const ITEMS = [
    { n: "Stone Island",  m: "Overshirt · L · 🇩🇪",  p: "€72",  s: "0.8", img: "stone" },
    { n: "Carhartt WIP",  m: "Detroit jacket · M · 🇫🇷", p: "€58", s: "1.2", img: "carhartt" },
    { n: "Arc'teryx",     m: "Beta LT · S · 🇬🇧",    p: "£95",  s: "0.6", img: "arcteryx" },
    { n: "Levi's 501",    m: "Vintage · W32 · 🇮🇹",  p: "€24",  s: "1.4", img: "levis" },
    { n: "Nike TN",       m: "Air Max Plus · 43 · 🇵🇱", p: "zł 210", s: "0.9", img: "nike" },
    { n: "The North Face", m: "Nuptse 700 · M · 🇪🇸", p: "€88",  s: "1.1", img: "nuptse" },
  ];

  const MAX = 5;
  let i = 0;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  function spottedText(sec) {
    const dict = T[document.documentElement.lang] || T.en;
    return (dict.feed_spotted || T.en.feed_spotted).replace("{s}", sec);
  }

  function card(item) {
    const el = document.createElement("div");
    el.className = "alert";
    el.innerHTML =
      '<div class="thumb"><img alt="" loading="lazy"></div>' +
      '<div><div class="row1"><span class="name"></span>' +
      '<span class="price mono"></span></div>' +
      '<div class="meta"></div><div class="speed mono"></div></div>';
    // Превью - нейтральные заглушки: фото чужих объявлений в публичном репо не держим.
    el.querySelector(".thumb img").src = "assets/img/" + item.img + ".svg";
    el.querySelector(".name").textContent = item.n;
    el.querySelector(".price").textContent = item.p;
    el.querySelector(".meta").textContent = item.m;
    el.querySelector(".speed").textContent = "⚡ " + spottedText(item.s);
    el.dataset.sec = item.s;
    return el;
  }

  function push() {
    const item = ITEMS[i % ITEMS.length];
    i++;
    feed.appendChild(card(item));
    while (feed.children.length > MAX) feed.removeChild(feed.firstChild);
  }

  // Стартовый экран заполняем сразу, чтобы лента не выглядела пустой.
  for (let k = 0; k < MAX; k++) push();

  if (!reduced) {
    let timer = setInterval(push, 2600);
    // На скрытой вкладке анимация не нужна — не жжём батарею.
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) { clearInterval(timer); timer = null; }
      else if (!timer) { timer = setInterval(push, 2600); }
    });
  }

  // При смене языка обновляем подписи уже показанных карточек.
  document.addEventListener("langchange", () => {
    feed.querySelectorAll(".alert").forEach((el) => {
      el.querySelector(".speed").textContent = "⚡ " + spottedText(el.dataset.sec);
    });
  });
})();
