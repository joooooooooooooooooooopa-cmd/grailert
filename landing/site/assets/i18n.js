/* Grailert — тексты лендинга на семи языках.

   Тот же набор, что и в боте: en / fr / de / es / it / pl / ru. Английский —
   эталон и запасной вариант. Язык определяется по браузеру, выбор запоминается
   в localStorage; разметка помечена атрибутами data-i18n. */

const LANGS = {
  en: "English",
  fr: "Français",
  de: "Deutsch",
  es: "Español",
  it: "Italiano",
  pl: "Polski",
  ru: "Русский",
};

const T = {

en: {
  nav_how: "How it works", nav_safe: "Account safety", nav_pricing: "Pricing", nav_faq: "FAQ",
  cta_top: "Open in Telegram",

  hero_eyebrow: "Sourcing alerts for Vinted",
  hero_h1a: "Be first on the", hero_h1em: "listing.",
  hero_sub: "Grailert watches Vinted and messages you the second a match goes live. The good pieces are gone in minutes — you'll be there in seconds.",
  cta_main: "Start free in Telegram", cta_second: "See how it works",
  hero_note_a: "1 search free forever", hero_note_b: "7-day Pro trial", hero_note_c: "no card needed",

  feed_title: "live · what an alert looks like",
  feed_spotted: "spotted {s}s after listing",

  how_eyebrow: "Three steps", how_h2: "Set it once, hunt while you sleep",
  how_p: "No extension to install, no account to connect. Everything happens in a Telegram chat.",
  s1_h: "Tell it what you hunt",
  s1_p: "Send a keyword like <code>stone island</code>, or paste a filtered Vinted link with your exact brand, size and price range.",
  s2_h: "Pick how often to check",
  s2_p: "From every 15 minutes down to every 30 seconds. On Vinted the interval is the whole game — it decides who sees the underpriced piece first.",
  s3_h: "Get the alert, take the deal",
  s3_p: "Photo album, price, size, brand and a direct link land in your chat. One tap and you're on the listing.",

  panel_eyebrow: "Inside Telegram",
  panel_h2: "A control panel, not a chat you have to fight",
  panel_p: "Everything lives in one screen inside Telegram: your searches, what is on sale right now, your plan. No website to log into, no app to install.",
  panel_1h: "Your searches at a glance",
  panel_1p: "Pause, resume, edit filters or run a check right now — one tap each.",
  panel_2h: "A live feed",
  panel_2p: "See what is on sale for any of your searches this second, with photos and prices.",
  panel_3h: "Upgrade without leaving",
  panel_3p: "Pay with Telegram Stars or crypto inside the panel. No card, no redirect.",

  safe_eyebrow: "The part nobody else will tell you",
  safe_h2: "Your Vinted account stays yours",
  safe_p: "Vinted has declared war on third-party tools, and the bans land on people who automate actions on their own account: auto-buying, re-listing, bulk messaging. Grailert does none of that — and that is a deliberate product decision, not a missing feature.",
  them_h: "Tools that risk your account",
  them_1: "Log in as you, with your password or session",
  them_2: "Auto-buy and auto-message from your account",
  them_3: "Re-list your items on a schedule",
  them_4: "Every action is traceable to your account",
  us_h: "What Grailert does",
  us_1: "Reads public listings only — no login, ever",
  us_2: "Never asks for your Vinted password",
  us_3: "Buys nothing, posts nothing, messages nobody",
  us_4: "The only thing it touches is your Telegram chat",
  f1_v: "+340%", f1_k: "growth in bans for automation during the February 2026 wave",
  f2_v: "0", f2_k: "actions Grailert takes on your Vinted account",
  f3_v: "30 sec", f3_k: "fastest check — the interval that decides who gets there first",

  price_eyebrow: "Pricing", price_h2: "You're paying for seconds",
  price_p: "Not for a number of searches — for how early you see the listing. One good find pays for a year.",
  p_free: "Free", p_basic: "Basic", p_pro: "Pro", p_badge: "most popular",
  int_k: "between checks",
  free_1: "1 search", free_2: "Full alerts with photos", free_3: "Free forever",
  basic_1: "3 searches", basic_2: "Include and exclude word filters", basic_3: "Price snapshot per search",
  pro_1: "Unlimited searches", pro_2: "Priority in the queue", pro_3: "12 months for the price of 10",
  per_year: "/ year",
  cta_plan: "Start in Telegram",
  pay_note: "Pay with Telegram Stars or crypto (USDT, TON, BTC) through Crypto Pay. Crypto comes first because Stars lose about a third to app-store fees on mobile — and that is your money, not ours.",

  langs_h2: "Speaks your language", langs_p: "The bot, the alerts and the payment screens are all localised. Pick your language in the chat, or let it follow your Telegram settings.",

  faq_h2: "Questions people actually ask",
  q1: "Can this get my Vinted account banned?",
  a1: "Nothing we do is attached to your account. Grailert reads the public catalogue the same way an anonymous visitor does and writes to your Telegram. It never logs in, never buys, never posts. There is no action on your account for Vinted to flag.",
  q2: "Do you need my Vinted password?",
  a2: "No, and we would refuse it if you offered. There is no login step anywhere in the product.",
  q3: "Which countries does it cover?",
  a3: "Twelve: Poland, Germany, France, Italy, Spain, the Netherlands, the UK, Czechia, Lithuania, Portugal, Belgium and Slovakia. Pick the country when you create a search, or paste a link from any of them.",
  q4: "How fast is it really?",
  a4: "On Pro it checks every 30 seconds, and the alert reaches your phone within a second of that check. In practice you see a new listing before it has scrolled off the first row of the app.",
  q5: "How do I pay, and can I stop?",
  a5: "Telegram Stars or crypto. There is no stored card and no automatic renewal — when the period ends, the plan simply stops. Your searches are paused, never deleted, and come straight back if you renew.",
  q6: "What happens when my trial ends?",
  a6: "You drop to Free: one search, checked every 15 minutes. Everything else is paused and waiting. Nothing is deleted.",

  final_h2: "The next good listing goes live in a minute", final_p: "Be the one who sees it.",

  foot_note: "Grailert is an independent tool. Not affiliated with, endorsed by, or connected to Vinted.",
  foot_faq: "FAQ", foot_safety: "Account safety", foot_terms: "Terms", foot_privacy: "Privacy", foot_support: "Support",
},

fr: {
  nav_how: "Comment ça marche", nav_safe: "Sécurité du compte", nav_pricing: "Tarifs", nav_faq: "FAQ",
  cta_top: "Ouvrir dans Telegram",

  hero_eyebrow: "Alertes de sourcing pour Vinted",
  hero_h1a: "Sois le premier sur", hero_h1em: "l'annonce.",
  hero_sub: "Grailert surveille Vinted et t'écrit à la seconde où une pièce correspond. Les bonnes affaires partent en quelques minutes — toi, tu y seras en quelques secondes.",
  cta_main: "Commencer gratuitement", cta_second: "Voir comment ça marche",
  hero_note_a: "1 recherche gratuite à vie", hero_note_b: "7 jours de Pro offerts", hero_note_c: "sans carte bancaire",

  feed_title: "en direct · à quoi ressemble une alerte",
  feed_spotted: "repérée {s}s après la mise en ligne",

  how_eyebrow: "Trois étapes", how_h2: "Réglé une fois, il chasse pendant que tu dors",
  how_p: "Aucune extension à installer, aucun compte à connecter. Tout se passe dans une conversation Telegram.",
  s1_h: "Dis-lui ce que tu cherches",
  s1_p: "Envoie un mot-clé comme <code>stone island</code>, ou colle un lien Vinted filtré avec ta marque, ta taille et ton budget exacts.",
  s2_h: "Choisis la fréquence",
  s2_p: "De toutes les 15 minutes à toutes les 30 secondes. Sur Vinted, l'intervalle fait tout : c'est lui qui décide qui voit la pièce sous-évaluée en premier.",
  s3_h: "Reçois l'alerte, prends l'affaire",
  s3_p: "Album photo, prix, taille, marque et lien direct arrivent dans ta conversation. Un tap et tu es sur l'annonce.",

  panel_eyebrow: "Dans Telegram",
  panel_h2: "Un vrai tableau de bord, pas un chat à dompter",
  panel_p: "Tout tient sur un écran dans Telegram : tes recherches, ce qui est en vente maintenant, ton abonnement. Aucun site où se connecter, aucune appli à installer.",
  panel_1h: "Tes recherches d'un coup d'œil",
  panel_1p: "Mettre en pause, reprendre, changer les filtres ou vérifier maintenant — un tap chacun.",
  panel_2h: "Un flux en direct",
  panel_2p: "Vois ce qui est en vente pour chaque recherche, à la seconde, avec photos et prix.",
  panel_3h: "Passer au niveau supérieur sur place",
  panel_3p: "Paie en Telegram Stars ou en crypto dans le panneau. Sans carte, sans redirection.",

  safe_eyebrow: "Ce que les autres ne te diront pas",
  safe_h2: "Ton compte Vinted reste le tien",
  safe_p: "Vinted a déclaré la guerre aux outils tiers, et les bannissements tombent sur ceux qui automatisent des actions depuis leur propre compte : achat automatique, remise en ligne, messages en masse. Grailert ne fait rien de tout ça — c'est un choix de conception, pas une fonctionnalité manquante.",
  them_h: "Les outils qui risquent ton compte",
  them_1: "Se connectent à ta place, avec ton mot de passe ou ta session",
  them_2: "Achètent et écrivent automatiquement depuis ton compte",
  them_3: "Republient tes articles selon un planning",
  them_4: "Chaque action est traçable jusqu'à ton compte",
  us_h: "Ce que fait Grailert",
  us_1: "Lit uniquement les annonces publiques — jamais de connexion",
  us_2: "Ne demande jamais ton mot de passe Vinted",
  us_3: "N'achète rien, ne publie rien, n'écrit à personne",
  us_4: "La seule chose qu'il touche, c'est ta conversation Telegram",
  f1_v: "+340 %", f1_k: "de hausse des bannissements pour automatisation lors de la vague de février 2026",
  f2_v: "0", f2_k: "action effectuée par Grailert sur ton compte Vinted",
  f3_v: "30 sec", f3_k: "vérification la plus rapide — l'intervalle qui décide qui arrive en premier",

  price_eyebrow: "Tarifs", price_h2: "Ce que tu paies, ce sont des secondes",
  price_p: "Pas un nombre de recherches, mais l'avance avec laquelle tu vois l'annonce. Une bonne trouvaille paie une année.",
  p_free: "Free", p_basic: "Basic", p_pro: "Pro", p_badge: "le plus choisi",
  int_k: "entre deux vérifications",
  free_1: "1 recherche", free_2: "Alertes complètes avec photos", free_3: "Gratuit à vie",
  basic_1: "3 recherches", basic_2: "Filtres de mots inclus et exclus", basic_3: "Aperçu des prix par recherche",
  pro_1: "Recherches illimitées", pro_2: "Priorité dans la file", pro_3: "12 mois au prix de 10",
  per_year: "/ an",
  cta_plan: "Commencer dans Telegram",
  pay_note: "Paiement par Telegram Stars ou en crypto (USDT, TON, BTC) via Crypto Pay. La crypto est proposée en premier parce que les Stars perdent environ un tiers en commissions de boutique sur mobile — et c'est ton argent, pas le nôtre.",

  langs_h2: "Il parle ta langue", langs_p: "Le bot, les alertes et les écrans de paiement sont traduits. Choisis ta langue dans la conversation, ou laisse-le suivre tes réglages Telegram.",

  faq_h2: "Les vraies questions",
  q1: "Est-ce que ça peut faire bannir mon compte Vinted ?",
  a1: "Rien de ce que nous faisons n'est rattaché à ton compte. Grailert lit le catalogue public comme un visiteur anonyme et écrit dans ton Telegram. Jamais de connexion, jamais d'achat, jamais de publication. Il n'y a aucune action sur ton compte que Vinted pourrait signaler.",
  q2: "Avez-vous besoin de mon mot de passe Vinted ?",
  a2: "Non, et nous le refuserions si tu le proposais. Il n'y a aucune étape de connexion dans le produit.",
  q3: "Quels pays sont couverts ?",
  a3: "Douze : Pologne, Allemagne, France, Italie, Espagne, Pays-Bas, Royaume-Uni, Tchéquie, Lituanie, Portugal, Belgique et Slovaquie. Choisis le pays à la création d'une recherche, ou colle un lien de n'importe lequel.",
  q4: "C'est vraiment si rapide ?",
  a4: "En Pro, il vérifie toutes les 30 secondes, et l'alerte arrive sur ton téléphone dans la seconde qui suit. En pratique, tu vois l'annonce avant qu'elle ne quitte la première ligne de l'appli.",
  q5: "Comment payer, et puis-je arrêter ?",
  a5: "Telegram Stars ou crypto. Aucune carte enregistrée, aucun renouvellement automatique : à la fin de la période, la formule s'arrête, tout simplement. Tes recherches sont mises en pause, jamais supprimées, et repartent si tu renouvelles.",
  q6: "Que se passe-t-il à la fin de l'essai ?",
  a6: "Tu passes en Free : une recherche, vérifiée toutes les 15 minutes. Le reste est en pause et t'attend. Rien n'est supprimé.",

  final_h2: "La prochaine bonne annonce sort dans une minute", final_p: "Sois celui qui la voit.",

  foot_note: "Grailert est un outil indépendant. Sans affiliation ni lien avec Vinted.",
  foot_faq: "FAQ", foot_safety: "Sécurité du compte", foot_terms: "Conditions", foot_privacy: "Confidentialité", foot_support: "Support",
},

de: {
  nav_how: "So funktioniert's", nav_safe: "Kontosicherheit", nav_pricing: "Preise", nav_faq: "FAQ",
  cta_top: "In Telegram öffnen",

  hero_eyebrow: "Sourcing-Alerts für Vinted",
  hero_h1a: "Sei als Erster am", hero_h1em: "Angebot.",
  hero_sub: "Grailert beobachtet Vinted und schreibt dir in der Sekunde, in der ein passendes Teil online geht. Die guten Stücke sind in Minuten weg — du bist in Sekunden da.",
  cta_main: "Kostenlos starten", cta_second: "Ansehen, wie es läuft",
  hero_note_a: "1 Suche dauerhaft gratis", hero_note_b: "7 Tage Pro testen", hero_note_c: "ohne Kreditkarte",

  feed_title: "live · so sieht ein Alert aus",
  feed_spotted: "gefunden {s}s nach dem Einstellen",

  how_eyebrow: "Drei Schritte", how_h2: "Einmal einstellen, jagen lassen",
  how_p: "Keine Erweiterung, kein Konto zu verbinden. Alles passiert in einem Telegram-Chat.",
  s1_h: "Sag ihm, wonach du jagst",
  s1_p: "Schick ein Stichwort wie <code>stone island</code> oder füge einen gefilterten Vinted-Link mit deiner Marke, Größe und Preisspanne ein.",
  s2_h: "Wähle das Prüfintervall",
  s2_p: "Von alle 15 Minuten bis alle 30 Sekunden. Auf Vinted entscheidet das Intervall alles — es bestimmt, wer das unterbewertete Teil zuerst sieht.",
  s3_h: "Alert bekommen, Deal machen",
  s3_p: "Fotoalbum, Preis, Größe, Marke und Direktlink landen in deinem Chat. Ein Tipp und du bist am Angebot.",

  panel_eyebrow: "In Telegram",
  panel_h2: "Ein Steuerpult statt eines Chats, mit dem man kämpft",
  panel_p: "Alles auf einem Bildschirm in Telegram: deine Suchen, was gerade angeboten wird, dein Tarif. Keine Website zum Einloggen, keine App zum Installieren.",
  panel_1h: "Deine Suchen auf einen Blick",
  panel_1p: "Pausieren, fortsetzen, Filter ändern oder jetzt prüfen — je ein Tipp.",
  panel_2h: "Ein Live-Feed",
  panel_2p: "Sieh in Echtzeit, was zu jeder deiner Suchen angeboten wird, mit Fotos und Preisen.",
  panel_3h: "Upgraden ohne rauszugehen",
  panel_3p: "Zahle mit Telegram Stars oder Krypto direkt im Pult. Ohne Karte, ohne Weiterleitung.",

  safe_eyebrow: "Was dir sonst niemand sagt",
  safe_h2: "Dein Vinted-Konto bleibt deins",
  safe_p: "Vinted führt Krieg gegen Drittanbieter-Tools, und die Sperren treffen die, die Aktionen auf dem eigenen Konto automatisieren: Auto-Kauf, Neu-Einstellen, Massennachrichten. Grailert macht nichts davon — das ist eine bewusste Produktentscheidung, keine fehlende Funktion.",
  them_h: "Tools, die dein Konto riskieren",
  them_1: "Melden sich als du an, mit Passwort oder Sitzung",
  them_2: "Kaufen und schreiben automatisch von deinem Konto",
  them_3: "Stellen deine Artikel nach Zeitplan neu ein",
  them_4: "Jede Aktion ist auf dein Konto zurückzuführen",
  us_h: "Was Grailert tut",
  us_1: "Liest nur öffentliche Angebote — niemals ein Login",
  us_2: "Fragt nie nach deinem Vinted-Passwort",
  us_3: "Kauft nichts, postet nichts, schreibt niemandem",
  us_4: "Das Einzige, was er anfasst, ist dein Telegram-Chat",
  f1_v: "+340 %", f1_k: "mehr Sperren wegen Automatisierung in der Welle vom Februar 2026",
  f2_v: "0", f2_k: "Aktionen, die Grailert auf deinem Vinted-Konto ausführt",
  f3_v: "30 Sek", f3_k: "schnellste Prüfung — das Intervall entscheidet, wer zuerst da ist",

  price_eyebrow: "Preise", price_h2: "Du bezahlst für Sekunden",
  price_p: "Nicht für eine Anzahl Suchen, sondern dafür, wie früh du das Angebot siehst. Ein guter Fund zahlt ein Jahr.",
  p_free: "Free", p_basic: "Basic", p_pro: "Pro", p_badge: "am beliebtesten",
  int_k: "zwischen zwei Prüfungen",
  free_1: "1 Suche", free_2: "Volle Alerts mit Fotos", free_3: "Dauerhaft kostenlos",
  basic_1: "3 Suchen", basic_2: "Filter für erwünschte und unerwünschte Wörter", basic_3: "Preisüberblick je Suche",
  pro_1: "Unbegrenzte Suchen", pro_2: "Vorrang in der Warteschlange", pro_3: "12 Monate zum Preis von 10",
  per_year: "/ Jahr",
  cta_plan: "In Telegram starten",
  pay_note: "Zahlung mit Telegram Stars oder Krypto (USDT, TON, BTC) über Crypto Pay. Krypto steht zuerst, weil Stars auf dem Handy rund ein Drittel an App-Store-Gebühren verlieren — und das ist dein Geld, nicht unseres.",

  langs_h2: "Spricht deine Sprache", langs_p: "Bot, Alerts und Zahlungsseiten sind übersetzt. Sprache im Chat wählen oder den Telegram-Einstellungen folgen lassen.",

  faq_h2: "Fragen, die wirklich gestellt werden",
  q1: "Kann mein Vinted-Konto dadurch gesperrt werden?",
  a1: "Nichts, was wir tun, hängt an deinem Konto. Grailert liest den öffentlichen Katalog wie ein anonymer Besucher und schreibt in dein Telegram. Kein Login, kein Kauf, kein Post. Es gibt keine Aktion auf deinem Konto, die Vinted auffallen könnte.",
  q2: "Braucht ihr mein Vinted-Passwort?",
  a2: "Nein — und wir würden es ablehnen. Im ganzen Produkt gibt es keinen Login-Schritt.",
  q3: "Welche Länder sind abgedeckt?",
  a3: "Zwölf: Polen, Deutschland, Frankreich, Italien, Spanien, Niederlande, Großbritannien, Tschechien, Litauen, Portugal, Belgien und Slowakei. Land bei der Suche wählen oder einen Link aus einem davon einfügen.",
  q4: "Wie schnell ist es wirklich?",
  a4: "Mit Pro alle 30 Sekunden, und der Alert ist innerhalb einer Sekunde nach der Prüfung auf deinem Handy. Praktisch siehst du ein Angebot, bevor es aus der ersten Reihe der App gescrollt ist.",
  q5: "Wie zahle ich, und kann ich aufhören?",
  a5: "Telegram Stars oder Krypto. Keine gespeicherte Karte, keine automatische Verlängerung — läuft der Zeitraum ab, endet der Tarif einfach. Deine Suchen werden pausiert, nie gelöscht, und laufen nach der Verlängerung sofort weiter.",
  q6: "Was passiert nach der Testphase?",
  a6: "Du fällst auf Free: eine Suche, Prüfung alle 15 Minuten. Alles andere ist pausiert und wartet. Gelöscht wird nichts.",

  final_h2: "Das nächste gute Angebot geht in einer Minute online", final_p: "Sei der, der es sieht.",

  foot_note: "Grailert ist ein unabhängiges Tool. Keine Verbindung zu Vinted.",
  foot_faq: "FAQ", foot_safety: "Kontosicherheit", foot_terms: "AGB", foot_privacy: "Datenschutz", foot_support: "Support",
},

es: {
  nav_how: "Cómo funciona", nav_safe: "Seguridad de la cuenta", nav_pricing: "Precios", nav_faq: "FAQ",
  cta_top: "Abrir en Telegram",

  hero_eyebrow: "Alertas de sourcing para Vinted",
  hero_h1a: "Llega el primero al", hero_h1em: "anuncio.",
  hero_sub: "Grailert vigila Vinted y te escribe en el segundo en que aparece algo que encaja. Lo bueno vuela en minutos — tú llegarás en segundos.",
  cta_main: "Empezar gratis", cta_second: "Ver cómo funciona",
  hero_note_a: "1 búsqueda gratis para siempre", hero_note_b: "7 días de Pro", hero_note_c: "sin tarjeta",

  feed_title: "en directo · así es una alerta",
  feed_spotted: "detectado {s}s tras publicarse",

  how_eyebrow: "Tres pasos", how_h2: "Configúralo una vez y que cace por ti",
  how_p: "Sin extensiones que instalar ni cuentas que conectar. Todo ocurre en un chat de Telegram.",
  s1_h: "Dile qué buscas",
  s1_p: "Envía una palabra clave como <code>stone island</code>, o pega un enlace de Vinted con tus filtros exactos de marca, talla y precio.",
  s2_h: "Elige cada cuánto revisar",
  s2_p: "Desde cada 15 minutos hasta cada 30 segundos. En Vinted el intervalo lo es todo: decide quién ve antes la prenda infravalorada.",
  s3_h: "Recibe el aviso y cierra el trato",
  s3_p: "Álbum de fotos, precio, talla, marca y enlace directo llegan a tu chat. Un toque y estás en el anuncio.",

  panel_eyebrow: "Dentro de Telegram",
  panel_h2: "Un panel de control, no un chat que hay que pelear",
  panel_p: "Todo en una pantalla dentro de Telegram: tus búsquedas, lo que está en venta ahora, tu plan. Sin web donde entrar, sin app que instalar.",
  panel_1h: "Tus búsquedas de un vistazo",
  panel_1p: "Pausar, reanudar, cambiar filtros o comprobar ahora — un toque cada cosa.",
  panel_2h: "Un feed en vivo",
  panel_2p: "Mira qué hay en venta para cada búsqueda en este segundo, con fotos y precios.",
  panel_3h: "Mejora sin salir",
  panel_3p: "Paga con Telegram Stars o cripto dentro del panel. Sin tarjeta, sin redirección.",

  safe_eyebrow: "Lo que nadie más te va a contar",
  safe_h2: "Tu cuenta de Vinted sigue siendo tuya",
  safe_p: "Vinted ha declarado la guerra a las herramientas de terceros, y los bloqueos caen sobre quienes automatizan acciones desde su propia cuenta: compra automática, republicación, mensajes masivos. Grailert no hace nada de eso, y es una decisión de producto, no una función que falte.",
  them_h: "Herramientas que arriesgan tu cuenta",
  them_1: "Inician sesión por ti, con tu contraseña o sesión",
  them_2: "Compran y escriben automáticamente desde tu cuenta",
  them_3: "Republican tus artículos según un horario",
  them_4: "Cada acción es rastreable hasta tu cuenta",
  us_h: "Lo que hace Grailert",
  us_1: "Solo lee anuncios públicos — nunca inicia sesión",
  us_2: "Jamás pide tu contraseña de Vinted",
  us_3: "No compra, no publica, no escribe a nadie",
  us_4: "Lo único que toca es tu chat de Telegram",
  f1_v: "+340 %", f1_k: "de aumento de bloqueos por automatización en la oleada de febrero de 2026",
  f2_v: "0", f2_k: "acciones que Grailert hace en tu cuenta de Vinted",
  f3_v: "30 seg", f3_k: "revisión más rápida — el intervalo decide quién llega primero",

  price_eyebrow: "Precios", price_h2: "Lo que pagas son segundos",
  price_p: "No un número de búsquedas, sino cuánta ventaja tienes al ver el anuncio. Un buen hallazgo paga un año.",
  p_free: "Free", p_basic: "Basic", p_pro: "Pro", p_badge: "el más elegido",
  int_k: "entre revisiones",
  free_1: "1 búsqueda", free_2: "Alertas completas con fotos", free_3: "Gratis para siempre",
  basic_1: "3 búsquedas", basic_2: "Filtros de palabras incluidas y excluidas", basic_3: "Vistazo de precios por búsqueda",
  pro_1: "Búsquedas ilimitadas", pro_2: "Prioridad en la cola", pro_3: "12 meses al precio de 10",
  per_year: "/ año",
  cta_plan: "Empezar en Telegram",
  pay_note: "Paga con Telegram Stars o cripto (USDT, TON, BTC) mediante Crypto Pay. La cripto va primero porque las Stars pierden cerca de un tercio en comisiones de tienda en el móvil — y ese dinero es tuyo, no nuestro.",

  langs_h2: "Habla tu idioma", langs_p: "El bot, las alertas y las pantallas de pago están traducidos. Elige idioma en el chat o deja que siga tus ajustes de Telegram.",

  faq_h2: "Preguntas que se hacen de verdad",
  q1: "¿Pueden bloquearme la cuenta de Vinted por esto?",
  a1: "Nada de lo que hacemos está ligado a tu cuenta. Grailert lee el catálogo público igual que un visitante anónimo y te escribe a Telegram. Nunca inicia sesión, no compra, no publica. No hay ninguna acción en tu cuenta que Vinted pueda marcar.",
  q2: "¿Necesitáis mi contraseña de Vinted?",
  a2: "No, y la rechazaríamos si nos la dieras. En todo el producto no hay ningún paso de inicio de sesión.",
  q3: "¿Qué países cubre?",
  a3: "Doce: Polonia, Alemania, Francia, Italia, España, Países Bajos, Reino Unido, Chequia, Lituania, Portugal, Bélgica y Eslovaquia. Elige país al crear la búsqueda o pega un enlace de cualquiera de ellos.",
  q4: "¿De verdad es tan rápido?",
  a4: "En Pro revisa cada 30 segundos, y el aviso llega a tu móvil en menos de un segundo tras esa revisión. En la práctica ves el anuncio antes de que salga de la primera fila de la app.",
  q5: "¿Cómo pago y puedo dejarlo?",
  a5: "Telegram Stars o cripto. No hay tarjeta guardada ni renovación automática: cuando acaba el periodo, el plan simplemente termina. Tus búsquedas quedan en pausa, nunca borradas, y vuelven al renovar.",
  q6: "¿Qué pasa cuando acaba la prueba?",
  a6: "Bajas a Free: una búsqueda, revisada cada 15 minutos. El resto queda en pausa esperando. No se borra nada.",

  final_h2: "El próximo buen anuncio sale en un minuto", final_p: "Sé quien lo vea.",

  foot_note: "Grailert es una herramienta independiente. Sin relación con Vinted.",
  foot_faq: "FAQ", foot_safety: "Seguridad de la cuenta", foot_terms: "Términos", foot_privacy: "Privacidad", foot_support: "Soporte",
},

it: {
  nav_how: "Come funziona", nav_safe: "Sicurezza dell'account", nav_pricing: "Prezzi", nav_faq: "FAQ",
  cta_top: "Apri in Telegram",

  hero_eyebrow: "Avvisi di sourcing per Vinted",
  hero_h1a: "Arriva per primo", hero_h1em: "sull'annuncio.",
  hero_sub: "Grailert tiene d'occhio Vinted e ti scrive nel secondo in cui esce qualcosa che corrisponde. I pezzi buoni spariscono in minuti — tu ci sarai in secondi.",
  cta_main: "Inizia gratis", cta_second: "Guarda come funziona",
  hero_note_a: "1 ricerca gratis per sempre", hero_note_b: "7 giorni di Pro", hero_note_c: "senza carta",

  feed_title: "in diretta · ecco com'è un avviso",
  feed_spotted: "trovato {s}s dopo la pubblicazione",

  how_eyebrow: "Tre passi", how_h2: "Imposta una volta, poi caccia da solo",
  how_p: "Nessuna estensione da installare, nessun account da collegare. Tutto accade in una chat Telegram.",
  s1_h: "Digli cosa cerchi",
  s1_p: "Manda una parola chiave come <code>stone island</code>, oppure incolla un link Vinted con i tuoi filtri esatti di marca, taglia e prezzo.",
  s2_h: "Scegli ogni quanto controllare",
  s2_p: "Da ogni 15 minuti fino a ogni 30 secondi. Su Vinted l'intervallo è tutto: decide chi vede per primo il capo sottoprezzo.",
  s3_h: "Ricevi l'avviso, prendi l'affare",
  s3_p: "Album foto, prezzo, taglia, marca e link diretto arrivano in chat. Un tocco e sei sull'annuncio.",

  panel_eyebrow: "Dentro Telegram",
  panel_h2: "Una plancia di comando, non una chat da domare",
  panel_p: "Tutto in una schermata dentro Telegram: le tue ricerche, cosa è in vendita adesso, il tuo piano. Nessun sito dove accedere, nessuna app da installare.",
  panel_1h: "Le tue ricerche a colpo d'occhio",
  panel_1p: "Metti in pausa, riprendi, cambia i filtri o controlla adesso — un tocco ciascuno.",
  panel_2h: "Un flusso dal vivo",
  panel_2p: "Guarda cosa è in vendita per ogni ricerca in questo momento, con foto e prezzi.",
  panel_3h: "Passa di livello senza uscire",
  panel_3p: "Paghi con Telegram Stars o in cripto dentro il pannello. Senza carta, senza redirect.",

  safe_eyebrow: "La parte che nessun altro ti dirà",
  safe_h2: "Il tuo account Vinted resta tuo",
  safe_p: "Vinted ha dichiarato guerra agli strumenti di terze parti, e i blocchi colpiscono chi automatizza azioni dal proprio account: acquisto automatico, ripubblicazione, messaggi di massa. Grailert non fa niente di tutto questo — è una scelta di prodotto, non una funzione mancante.",
  them_h: "Strumenti che rischiano il tuo account",
  them_1: "Accedono al posto tuo, con password o sessione",
  them_2: "Comprano e scrivono in automatico dal tuo account",
  them_3: "Ripubblicano i tuoi articoli a orari fissi",
  them_4: "Ogni azione è riconducibile al tuo account",
  us_h: "Cosa fa Grailert",
  us_1: "Legge solo annunci pubblici — mai un accesso",
  us_2: "Non chiede mai la tua password Vinted",
  us_3: "Non compra, non pubblica, non scrive a nessuno",
  us_4: "L'unica cosa che tocca è la tua chat Telegram",
  f1_v: "+340 %", f1_k: "di aumento dei blocchi per automazione nell'ondata di febbraio 2026",
  f2_v: "0", f2_k: "azioni che Grailert compie sul tuo account Vinted",
  f3_v: "30 sec", f3_k: "controllo più rapido — l'intervallo decide chi arriva prima",

  price_eyebrow: "Prezzi", price_h2: "Quello che paghi sono secondi",
  price_p: "Non un numero di ricerche, ma quanto prima vedi l'annuncio. Un buon affare ripaga un anno.",
  p_free: "Free", p_basic: "Basic", p_pro: "Pro", p_badge: "il più scelto",
  int_k: "tra un controllo e l'altro",
  free_1: "1 ricerca", free_2: "Avvisi completi con foto", free_3: "Gratis per sempre",
  basic_1: "3 ricerche", basic_2: "Filtri di parole incluse ed escluse", basic_3: "Sguardo ai prezzi per ricerca",
  pro_1: "Ricerche illimitate", pro_2: "Priorità in coda", pro_3: "12 mesi al prezzo di 10",
  per_year: "/ anno",
  cta_plan: "Inizia in Telegram",
  pay_note: "Paghi con Telegram Stars o in cripto (USDT, TON, BTC) tramite Crypto Pay. La cripto viene per prima perché le Stars perdono circa un terzo in commissioni degli store su mobile — e quei soldi sono tuoi, non nostri.",

  langs_h2: "Parla la tua lingua", langs_p: "Bot, avvisi e schermate di pagamento sono tradotti. Scegli la lingua in chat o lascia che segua le impostazioni di Telegram.",

  faq_h2: "Le domande che fanno davvero",
  q1: "Rischio il blocco dell'account Vinted?",
  a1: "Niente di ciò che facciamo è collegato al tuo account. Grailert legge il catalogo pubblico come un visitatore anonimo e ti scrive su Telegram. Non accede, non compra, non pubblica. Non c'è nessuna azione sul tuo account che Vinted possa segnalare.",
  q2: "Vi serve la mia password di Vinted?",
  a2: "No, e la rifiuteremmo. Nel prodotto non esiste alcun passaggio di accesso.",
  q3: "Quali paesi copre?",
  a3: "Dodici: Polonia, Germania, Francia, Italia, Spagna, Paesi Bassi, Regno Unito, Cechia, Lituania, Portogallo, Belgio e Slovacchia. Scegli il paese quando crei la ricerca o incolla un link da uno di questi.",
  q4: "Quanto è veloce davvero?",
  a4: "Con Pro controlla ogni 30 secondi, e l'avviso arriva sul telefono entro un secondo da quel controllo. In pratica vedi l'annuncio prima che scorra via dalla prima riga dell'app.",
  q5: "Come pago e posso smettere?",
  a5: "Telegram Stars o cripto. Nessuna carta salvata e nessun rinnovo automatico: finito il periodo, il piano semplicemente si ferma. Le ricerche restano in pausa, mai cancellate, e ripartono al rinnovo.",
  q6: "Cosa succede quando finisce la prova?",
  a6: "Passi a Free: una ricerca, controllata ogni 15 minuti. Tutto il resto è in pausa e ti aspetta. Non si cancella nulla.",

  final_h2: "Il prossimo buon annuncio esce tra un minuto", final_p: "Sii tu a vederlo.",

  foot_note: "Grailert è uno strumento indipendente. Nessun legame con Vinted.",
  foot_faq: "FAQ", foot_safety: "Sicurezza dell'account", foot_terms: "Termini", foot_privacy: "Privacy", foot_support: "Supporto",
},

pl: {
  nav_how: "Jak to działa", nav_safe: "Bezpieczeństwo konta", nav_pricing: "Cennik", nav_faq: "FAQ",
  cta_top: "Otwórz w Telegramie",

  hero_eyebrow: "Alerty do sourcingu na Vinted",
  hero_h1a: "Bądź pierwszy przy", hero_h1em: "ogłoszeniu.",
  hero_sub: "Grailert obserwuje Vinted i pisze do ciebie w sekundzie, w której pojawi się pasująca rzecz. Dobre sztuki znikają w kilka minut — ty będziesz tam w kilka sekund.",
  cta_main: "Zacznij za darmo", cta_second: "Zobacz, jak to działa",
  hero_note_a: "1 wyszukiwanie za darmo na zawsze", hero_note_b: "7 dni Pro", hero_note_c: "bez karty",

  feed_title: "na żywo · tak wygląda alert",
  feed_spotted: "znalezione {s}s po wystawieniu",

  how_eyebrow: "Trzy kroki", how_h2: "Ustaw raz, poluje za ciebie",
  how_p: "Żadnych wtyczek do instalowania, żadnego konta do podłączania. Wszystko dzieje się w czacie Telegrama.",
  s1_h: "Powiedz, czego szukasz",
  s1_p: "Wyślij słowo kluczowe jak <code>stone island</code> albo wklej link z Vinted z twoimi filtrami marki, rozmiaru i ceny.",
  s2_h: "Wybierz częstotliwość",
  s2_p: "Od co 15 minut do co 30 sekund. Na Vinted odstęp decyduje o wszystkim — to on ustala, kto pierwszy zobaczy zaniżoną cenę.",
  s3_h: "Odbierz alert, weź okazję",
  s3_p: "Album zdjęć, cena, rozmiar, marka i bezpośredni link trafiają na czat. Jedno tapnięcie i jesteś przy ogłoszeniu.",

  panel_eyebrow: "W Telegramie",
  panel_h2: "Pulpit, a nie czat, z którym trzeba walczyć",
  panel_p: "Wszystko na jednym ekranie w Telegramie: twoje wyszukiwania, co jest teraz na sprzedaż, twój plan. Żadnej strony do logowania, żadnej aplikacji do instalowania.",
  panel_1h: "Wyszukiwania jak na dłoni",
  panel_1p: "Wstrzymaj, wznów, zmień filtry albo sprawdź teraz — każde jednym tapnięciem.",
  panel_2h: "Podgląd na żywo",
  panel_2p: "Zobacz, co jest na sprzedaż dla każdego wyszukiwania w tej sekundzie, ze zdjęciami i cenami.",
  panel_3h: "Zmień plan bez wychodzenia",
  panel_3p: "Płacisz gwiazdkami Telegrama albo kryptowalutą w pulpicie. Bez karty, bez przekierowań.",

  safe_eyebrow: "To, czego nikt inny ci nie powie",
  safe_h2: "Twoje konto Vinted zostaje twoje",
  safe_p: "Vinted wypowiedział wojnę zewnętrznym narzędziom, a bany spadają na tych, którzy automatyzują działania na własnym koncie: autozakup, przestawianie ogłoszeń, masowe wiadomości. Grailert nie robi nic z tych rzeczy — to świadoma decyzja, a nie brakująca funkcja.",
  them_h: "Narzędzia, które ryzykują twoje konto",
  them_1: "Logują się za ciebie, twoim hasłem lub sesją",
  them_2: "Automatycznie kupują i piszą z twojego konta",
  them_3: "Przestawiają twoje ogłoszenia według harmonogramu",
  them_4: "Każde działanie da się powiązać z twoim kontem",
  us_h: "Co robi Grailert",
  us_1: "Czyta wyłącznie publiczne ogłoszenia — nigdy się nie loguje",
  us_2: "Nigdy nie prosi o hasło do Vinted",
  us_3: "Nic nie kupuje, nic nie publikuje, do nikogo nie pisze",
  us_4: "Jedyne, czego dotyka, to twój czat w Telegramie",
  f1_v: "+340 %", f1_k: "wzrostu banów za automatyzację w fali z lutego 2026",
  f2_v: "0", f2_k: "działań, które Grailert wykonuje na twoim koncie Vinted",
  f3_v: "30 sek", f3_k: "najszybsze sprawdzanie — odstęp decyduje, kto jest pierwszy",

  price_eyebrow: "Cennik", price_h2: "Płacisz za sekundy",
  price_p: "Nie za liczbę wyszukiwań, tylko za to, jak wcześnie widzisz ogłoszenie. Jedna dobra okazja spłaca rok.",
  p_free: "Free", p_basic: "Basic", p_pro: "Pro", p_badge: "najczęściej wybierany",
  int_k: "między sprawdzeniami",
  free_1: "1 wyszukiwanie", free_2: "Pełne alerty ze zdjęciami", free_3: "Za darmo na zawsze",
  basic_1: "3 wyszukiwania", basic_2: "Filtry słów wymaganych i wykluczonych", basic_3: "Podgląd cen dla wyszukiwania",
  pro_1: "Bez limitu wyszukiwań", pro_2: "Priorytet w kolejce", pro_3: "12 miesięcy w cenie 10",
  per_year: "/ rok",
  cta_plan: "Zacznij w Telegramie",
  pay_note: "Płatność przez Telegram Stars albo kryptowalutą (USDT, TON, BTC) w Crypto Pay. Krypto jest pierwsze, bo Stars tracą około jednej trzeciej na prowizjach sklepów na telefonie — a to twoje pieniądze, nie nasze.",

  langs_h2: "Mówi twoim językiem", langs_p: "Bot, alerty i ekrany płatności są przetłumaczone. Wybierz język na czacie albo pozwól mu iść za ustawieniami Telegrama.",

  faq_h2: "Pytania, które naprawdę padają",
  q1: "Czy mogę przez to dostać bana na Vinted?",
  a1: "Nic, co robimy, nie jest powiązane z twoim kontem. Grailert czyta publiczny katalog tak samo jak anonimowy odwiedzający i pisze na twój Telegram. Nigdy się nie loguje, nie kupuje, nie publikuje. Nie ma żadnego działania na twoim koncie, które Vinted mógłby wychwycić.",
  q2: "Potrzebujecie mojego hasła do Vinted?",
  a2: "Nie, a gdybyś je podał, odmówilibyśmy. W całym produkcie nie ma kroku logowania.",
  q3: "Jakie kraje obsługuje?",
  a3: "Dwanaście: Polska, Niemcy, Francja, Włochy, Hiszpania, Holandia, Wielka Brytania, Czechy, Litwa, Portugalia, Belgia i Słowacja. Kraj wybierasz przy tworzeniu wyszukiwania albo wklejasz link z dowolnego z nich.",
  q4: "Czy naprawdę jest tak szybki?",
  a4: "W Pro sprawdza co 30 sekund, a alert trafia na telefon w ciągu sekundy od sprawdzenia. W praktyce widzisz ogłoszenie, zanim zjedzie z pierwszego rzędu w aplikacji.",
  q5: "Jak płacę i czy mogę przestać?",
  a5: "Telegram Stars albo krypto. Żadnej zapisanej karty i żadnego automatycznego odnawiania — po zakończeniu okresu plan po prostu się kończy. Wyszukiwania są wstrzymane, nigdy usunięte, i wracają po przedłużeniu.",
  q6: "Co się dzieje po okresie próbnym?",
  a6: "Spadasz na Free: jedno wyszukiwanie, sprawdzane co 15 minut. Reszta czeka wstrzymana. Nic nie jest usuwane.",

  final_h2: "Następne dobre ogłoszenie pojawi się za minutę", final_p: "Bądź tym, kto je zobaczy.",

  foot_note: "Grailert jest niezależnym narzędziem. Bez powiązań z Vinted.",
  foot_faq: "FAQ", foot_safety: "Bezpieczeństwo konta", foot_terms: "Regulamin", foot_privacy: "Prywatność", foot_support: "Pomoc",
},

ru: {
  nav_how: "Как это работает", nav_safe: "Безопасность аккаунта", nav_pricing: "Тарифы", nav_faq: "Вопросы",
  cta_top: "Открыть в Telegram",

  hero_eyebrow: "Алерты для перекупов Vinted",
  hero_h1a: "Успей первым к", hero_h1em: "объявлению.",
  hero_sub: "Grailert следит за Vinted и пишет в ту же секунду, как выложат подходящую вещь. Хорошее разбирают за минуты — ты будешь там за секунды.",
  cta_main: "Начать бесплатно", cta_second: "Посмотреть, как работает",
  hero_note_a: "1 поиск бесплатно навсегда", hero_note_b: "7 дней Pro", hero_note_c: "без карты",

  feed_title: "вживую · как выглядит алерт",
  feed_spotted: "найдено через {s} с после публикации",

  how_eyebrow: "Три шага", how_h2: "Настроил один раз — охотится, пока ты спишь",
  how_p: "Ничего не устанавливать, никакой аккаунт не подключать. Всё происходит в чате Telegram.",
  s1_h: "Скажи, что ищешь",
  s1_p: "Пришли слово вроде <code>stone island</code> или вставь ссылку с Vinted со своими фильтрами по бренду, размеру и цене.",
  s2_h: "Выбери, как часто проверять",
  s2_p: "От раза в 15 минут до раза в 30 секунд. На Vinted интервал решает всё: он определяет, кто первым увидит недооценённую вещь.",
  s3_h: "Получи алерт и забирай",
  s3_p: "Альбом фото, цена, размер, бренд и прямая ссылка приходят в чат. Одно нажатие — и ты на объявлении.",

  panel_eyebrow: "Внутри Telegram",
  panel_h2: "Пульт, а не переписка, которую надо укрощать",
  panel_p: "Всё на одном экране внутри Telegram: твои поиски, что продаётся прямо сейчас, твой тариф. Никаких сайтов со входом и приложений для установки.",
  panel_1h: "Все поиски перед глазами",
  panel_1p: "Пауза, запуск, правка фильтров или проверка прямо сейчас — по одному нажатию.",
  panel_2h: "Живая лента",
  panel_2p: "Смотри, что продаётся по любому твоему поиску в эту секунду, с фото и ценами.",
  panel_3h: "Поднять тариф не выходя",
  panel_3p: "Оплата звёздами Telegram или криптой прямо в пульте. Без карты и переходов.",

  safe_eyebrow: "То, о чём остальные молчат",
  safe_h2: "Твой аккаунт Vinted остаётся твоим",
  safe_p: "Vinted объявил войну сторонним инструментам, и баны прилетают тем, кто автоматизирует действия на собственном аккаунте: автовыкуп, перезаливы, массовые сообщения. Grailert не делает ничего из этого — и это осознанное решение, а не недоделка.",
  them_h: "Инструменты, которые рискуют твоим аккаунтом",
  them_1: "Входят под тобой — по паролю или сессии",
  them_2: "Сами покупают и пишут с твоего аккаунта",
  them_3: "Перезаливают твои вещи по расписанию",
  them_4: "Любое действие ведёт к твоему аккаунту",
  us_h: "Что делает Grailert",
  us_1: "Читает только публичные объявления — вход не нужен вообще",
  us_2: "Никогда не спрашивает пароль от Vinted",
  us_3: "Ничего не покупает, не публикует и никому не пишет",
  us_4: "Единственное, чего он касается, — твой чат в Telegram",
  f1_v: "+340 %", f1_k: "рост банов за автоматизацию в волне февраля 2026 года",
  f2_v: "0", f2_k: "действий Grailert совершает в твоём аккаунте Vinted",
  f3_v: "30 сек", f3_k: "самая частая проверка — интервал решает, кто успел первым",

  price_eyebrow: "Тарифы", price_h2: "Ты платишь за секунды",
  price_p: "Не за количество поисков, а за то, насколько раньше ты видишь объявление. Одна удачная находка окупает год.",
  p_free: "Free", p_basic: "Basic", p_pro: "Pro", p_badge: "берут чаще всего",
  int_k: "между проверками",
  free_1: "1 поиск", free_2: "Полные алерты с фото", free_3: "Бесплатно навсегда",
  basic_1: "3 поиска", basic_2: "Фильтры по нужным и лишним словам", basic_3: "Срез цен по поиску",
  pro_1: "Поисков без ограничений", pro_2: "Приоритет в очереди", pro_3: "12 месяцев по цене 10",
  per_year: "/ год",
  cta_plan: "Начать в Telegram",
  pay_note: "Оплата через Telegram Stars или криптой (USDT, TON, BTC) в Crypto Pay. Крипта стоит первой, потому что Stars теряют около трети на комиссиях магазинов приложений — и это твои деньги, не наши.",

  langs_h2: "Говорит на твоём языке", langs_p: "Бот, алерты и экраны оплаты переведены. Выбери язык в чате или дай ему подхватить настройки Telegram.",

  faq_h2: "Вопросы, которые задают на самом деле",
  q1: "Меня могут забанить на Vinted из-за этого?",
  a1: "Ничто из того, что мы делаем, не привязано к твоему аккаунту. Grailert читает публичный каталог так же, как анонимный посетитель, и пишет тебе в Telegram. Он не входит в аккаунт, не покупает, не публикует. У Vinted просто нет действия, которое можно было бы тебе предъявить.",
  q2: "Вам нужен мой пароль от Vinted?",
  a2: "Нет, и мы бы отказались, если бы ты его прислал. Во всём продукте нет ни одного шага со входом в аккаунт.",
  q3: "Какие страны поддерживаются?",
  a3: "Двенадцать: Польша, Германия, Франция, Италия, Испания, Нидерланды, Великобритания, Чехия, Литва, Португалия, Бельгия и Словакия. Страну выбираешь при создании поиска или вставляешь ссылку из любой из них.",
  q4: "Насколько он быстрый на самом деле?",
  a4: "На Pro проверка идёт раз в 30 секунд, и алерт долетает до телефона в течение секунды после неё. На практике ты видишь объявление раньше, чем оно уйдёт из первого ряда в приложении.",
  q5: "Как платить и можно ли перестать?",
  a5: "Telegram Stars или крипта. Карта нигде не хранится, автопродления нет: период закончился — тариф просто остановился. Поиски ставятся на паузу, а не удаляются, и возвращаются сразу после продления.",
  q6: "Что будет, когда закончится пробный период?",
  a6: "Ты опустишься на Free: один поиск, проверка раз в 15 минут. Всё остальное на паузе и ждёт. Ничего не удаляется.",

  final_h2: "Следующее хорошее объявление выйдет через минуту", final_p: "Будь тем, кто его увидит.",

  foot_note: "Grailert — независимый инструмент. Не связан с Vinted и не является его продуктом.",
  foot_faq: "Вопросы", foot_safety: "Безопасность аккаунта", foot_terms: "Условия", foot_privacy: "Приватность", foot_support: "Поддержка",
},

};

/* ---------- применение ---------- */

const STORAGE_KEY = "grailert_lang";

function detectLang() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && T[saved]) return saved;
  } catch (e) { /* приватный режим — просто определяем по браузеру */ }
  for (const l of (navigator.languages || [navigator.language || "en"])) {
    const code = String(l).split("-")[0].toLowerCase();
    if (T[code]) return code;
  }
  return "en";
}

function applyLang(lang) {
  const dict = T[lang] || T.en;
  document.documentElement.lang = lang;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const val = dict[key] != null ? dict[key] : T.en[key];
    if (val == null) return;
    // Часть строк содержит <code> — вставляем как разметку только там,
    // где это заложено автором, остальное как текст.
    if (el.hasAttribute("data-i18n-html")) el.innerHTML = val;
    else el.textContent = val;
  });

  document.querySelectorAll("[data-i18n-attr]").forEach((el) => {
    const [attr, key] = el.getAttribute("data-i18n-attr").split(":");
    const val = dict[key] != null ? dict[key] : T.en[key];
    if (val != null) el.setAttribute(attr, val);
  });

  const label = document.getElementById("langLabel");
  if (label) label.textContent = lang.toUpperCase();
  document.querySelectorAll("#langMenu button").forEach((b) => {
    b.setAttribute("aria-current", b.dataset.lang === lang ? "true" : "false");
  });

  try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* не критично */ }
  document.dispatchEvent(new CustomEvent("langchange", { detail: { lang, dict } }));
}
