#!/usr/bin/env python3
"""Собирает внутренние страницы сайта из одного шаблона.

Сайт статический, шаблонизатора нет — а шапка и подвал обязаны быть
одинаковыми на всех страницах. Поэтому они живут здесь в одном месте,
и страницы пересобираются командой:  python3 build_pages.py
"""
from __future__ import annotations

import io
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")

SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Grailert</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="https://grailert.example{path}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#FBFAF7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0F0F11" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="article">
<meta property="og:title" content="{title} — Grailert">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://grailert.example/assets/og.png">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Instrument+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/styles.css?v=1">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="top">
  <div class="top-in">
    <a class="brand" href="/">
      <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
        <path d="M3.4 4h15.2v7.6L11 18.6 3.4 11.6V4Z" fill="none" stroke="currentColor"
              stroke-width="1.6" stroke-linejoin="round"/>
        <circle cx="11" cy="10" r="2.6" fill="none" stroke="#DB3A1B" stroke-width="1.6"/>
      </svg>
      Grailert
    </a>
    <nav class="nav">
      <a href="/#how">How it works</a>
      <a href="/safety">Account safety</a>
      <a href="/#pricing">Pricing</a>
      <a href="/faq">FAQ</a>
      <a href="https://telegram.example/grailert_channel" rel="noopener">Channel</a>
    </nav>
    <div class="top-actions">
      <a class="btn btn-primary btn-sm" href="https://telegram.example/grailert_bot?start=site_{src}">Open in Telegram</a>
    </div>
  </div>
</header>

<main id="main" class="page">
  <div class="wrap">
{body}
  </div>
</main>

<footer>
  <div class="wrap foot">
    <div>
      <a class="brand foot-brand" href="/">
        <svg width="20" height="20" viewBox="0 0 22 22" aria-hidden="true">
          <path d="M3.4 4h15.2v7.6L11 18.6 3.4 11.6V4Z" fill="none" stroke="currentColor"
                stroke-width="1.6" stroke-linejoin="round"/>
          <circle cx="11" cy="10" r="2.6" fill="none" stroke="#DB3A1B" stroke-width="1.6"/>
        </svg>
        Grailert
      </a>
      <p class="foot-note">Grailert is an independent tool. Not affiliated with,
      endorsed by, or connected to Vinted.</p>
    </div>
    <div class="foot-links">
      <a href="/faq">FAQ</a>
      <a href="/safety">Account safety</a>
      <a href="/terms">Terms</a>
      <a href="/privacy">Privacy</a>
      <a href="https://telegram.example/grailert_bot?start=site_footer">Telegram</a>
    </div>
  </div>
</footer>
</body>
</html>
"""

PAGES = [

("faq.html", "/faq", "faq", "FAQ", "Answers about bans, speed, countries, payment and cancelling.", "index,follow", """
    <h1>Frequently asked questions</h1>
    <p class="lede">If something here is unclear, ask the bot — it answers in seven languages.</p>

    <h2>Bans and account safety</h2>
    <p><strong>Can Grailert get my Vinted account banned?</strong><br>
    Nothing we do is attached to your account. Grailert reads the public catalogue the same way
    an anonymous visitor does, and writes to your Telegram. It never logs in, never buys, never
    posts, never messages sellers. There is no action on your account for Vinted to flag.</p>

    <p><strong>Then why do people get banned for using tools?</strong><br>
    Because most tools act <em>as you</em>: auto-buying, re-listing on a schedule, bulk messaging.
    Those actions come from your account and are trivially detectable. The February 2026 wave hit
    exactly that behaviour. Read the longer version on the <a href="/safety">account safety</a> page.</p>

    <p><strong>Do you need my Vinted password?</strong><br>
    No — and we would refuse it if you offered. There is no login step anywhere in the product.</p>

    <h2>How it works</h2>
    <p><strong>Which countries are covered?</strong><br>
    Twelve: Poland, Germany, France, Italy, Spain, the Netherlands, the United Kingdom, Czechia,
    Lithuania, Portugal, Belgium and Slovakia.</p>

    <p><strong>Can I use my own filters?</strong><br>
    Yes, and it is the better way. Set your filters on Vinted — brand, size, condition, price —
    copy the address bar link and send it to the bot. It will watch exactly that query. A plain
    keyword works too if you want the whole site.</p>

    <p><strong>How fast is it really?</strong><br>
    On Pro the check runs every 30 seconds and the alert reaches your phone within a second of
    that check. In practice you see a listing before it scrolls off the first row of the app.</p>

    <p><strong>Will it spam me?</strong><br>
    No. A new search is silently baselined: the bot remembers what is already listed and only
    sends what appears afterwards. If a burst arrives, at most eight alerts are sent and the rest
    come as one summary line.</p>

    <h2>Money</h2>
    <p><strong>How do I pay?</strong><br>
    Telegram Stars or crypto (USDT, TON, BTC and others) through Crypto Pay. Crypto is listed
    first because Stars lose roughly a third to app-store fees on mobile purchases.</p>

    <p><strong>Is there automatic renewal?</strong><br>
    No. No card is stored and nothing renews itself. When the period ends, the plan stops.</p>

    <p><strong>What happens to my searches when a plan ends?</strong><br>
    They are paused, never deleted. Renew and they pick up where they left off.</p>

    <p><strong>Refunds?</strong><br>
    Ask in the bot. There is a free plan and a seven-day Pro trial specifically so that nobody
    has to pay to find out whether the tool works for them.</p>
"""),

("safety.html", "/safety", "safety", "Account safety",
 "Why Grailert cannot get your Vinted account banned: what it reads, what it never does.",
 "index,follow", """
    <h1>Your Vinted account stays yours</h1>
    <p class="lede">This page exists because it is the single most important thing to understand
    before installing any tool around a marketplace that bans people for automation.</p>

    <h2>What Vinted actually punishes</h2>
    <p>Vinted's terms forbid external software tools, bots and scrapers, and the platform enforces
    that with a bot-detection layer. But enforcement lands where it can be proven: on
    <strong>actions performed from a user's own account</strong>.</p>
    <ul>
      <li>automatic buying the moment a listing appears</li>
      <li>re-listing your own items on a schedule to stay on top of the feed</li>
      <li>bulk messaging buyers or sellers</li>
      <li>anything driven by a logged-in session that a human could not physically perform</li>
    </ul>
    <p>The February 2026 wave, reported as a roughly 340% increase in bans, hit that behaviour.
    A further round of restrictions followed in July 2026 aimed at automated re-listing.</p>

    <h2>What Grailert does</h2>
    <div class="tablewrap">
      <table>
        <tr><th>Question</th><th>Answer</th></tr>
        <tr><td>Does it log into my account?</td><td>No. Never, in any circumstance.</td></tr>
        <tr><td>Does it ask for my password?</td><td>No. There is no login screen in the product.</td></tr>
        <tr><td>Does it buy anything?</td><td>No.</td></tr>
        <tr><td>Does it publish or re-list?</td><td>No.</td></tr>
        <tr><td>Does it message anyone on Vinted?</td><td>No.</td></tr>
        <tr><td>What does it read?</td><td>The public catalogue, as an anonymous visitor.</td></tr>
        <tr><td>What does it write to?</td><td>Your Telegram chat, and nothing else.</td></tr>
      </table>
    </div>

    <h2>The honest part</h2>
    <p>We are not going to claim that a marketplace can never change its mind about third-party
    tools in general. What we can say precisely is this: there is no action taken on your account,
    so there is nothing on your account to detect, attribute or punish. If Grailert ever stopped
    working, the failure would be ours — a blocked server address — and not a mark on your profile.</p>

    <p>That is also why the product deliberately lacks auto-buy. It is the most requested feature
    in this category and the one that gets customers banned. We would rather be the tool you can
    keep using.</p>

    <h2>What we store about you</h2>
    <p>Your Telegram id and username, your language, your plan, your saved searches and which
    listings were already sent so you do not get them twice. No Vinted credentials, because we
    never have any. Details on the <a href="/privacy">privacy page</a>.</p>
"""),

("terms.html", "/terms", "terms", "Terms",
 "Plain terms of use for Grailert.", "noindex,follow", """
    <h1>Terms of use</h1>
    <p class="lede">Short, in plain language. Using the bot means you agree with what is below.</p>

    <h2>What the service is</h2>
    <p>Grailert is a notification tool. It monitors public listings on Vinted according to the
    search parameters you provide and sends you a message when something matching appears.
    It is an independent product, not affiliated with, endorsed by, or connected to Vinted.</p>

    <h2>What it is not</h2>
    <p>It is not a guarantee that you will find, win or resell anything. Availability of listings,
    prices and the behaviour of the marketplace are outside our control. The service is provided
    as-is, without a promise of uninterrupted operation.</p>

    <h2>Your account elsewhere</h2>
    <p>Grailert never accesses your Vinted account and never asks for its credentials. You remain
    responsible for how you use the marketplace itself, including its own terms.</p>

    <h2>Payment</h2>
    <p>Paid plans are prepaid for a fixed period through Telegram Stars or Crypto Pay. There is no
    stored payment method and no automatic renewal: when the period ends, the plan simply stops.
    Underpaid invoices are not treated as payment. Questions about a specific payment go to the
    bot, which can show you its status.</p>

    <h2>Fair use</h2>
    <p>Plans are personal. Reselling access, sharing one plan across many people, or using the
    service to overload the marketplace will end the plan without a refund.</p>

    <h2>Ending the service</h2>
    <p>You can stop at any time by not renewing; there is nothing to cancel. We may suspend an
    account that abuses the service, and we may stop offering the product entirely — in which case
    any unused prepaid period is refundable on request.</p>

    <h2>Contact</h2>
    <p>Everything goes through <a href="https://telegram.example/grailert_bot">the Telegram bot</a>.</p>
"""),

("privacy.html", "/privacy", "privacy", "Privacy",
 "What Grailert stores, why, and what it never touches.", "noindex,follow", """
    <h1>Privacy</h1>
    <p class="lede">The short version: we store what is needed to run your searches and your plan,
    and nothing about your Vinted account, because we never have access to it.</p>

    <h2>What we store</h2>
    <ul>
      <li><strong>From Telegram:</strong> your numeric id, your username if you have one, and your
      language setting. We never see your phone number.</li>
      <li><strong>Your searches:</strong> the name you gave them, the search link or keyword, the
      check interval and your word filters.</li>
      <li><strong>Delivery bookkeeping:</strong> identifiers of listings already sent, so the same
      item does not arrive twice.</li>
      <li><strong>Payments:</strong> which plan, which method, amount, currency, status and the
      invoice identifier. Card and wallet details never reach us — they stay with Telegram or
      Crypto Pay.</li>
    </ul>

    <h2>What we never store</h2>
    <p>Vinted credentials, because there is no login. Payment credentials. Your contacts, your
    other chats, or anything outside the conversation with the bot.</p>

    <h2>Where it goes</h2>
    <p>Data stays on our server. The bot talks to Telegram (to deliver messages), to Vinted
    (to read public listings), to Crypto Pay (for invoices) and to a European Central Bank rate
    feed (to convert prices). There are no advertising or analytics trackers.</p>

    <h2>How long</h2>
    <p>For as long as you use the bot. Delete a search and its data goes with it; ask the bot to
    remove your account and everything is deleted, payments aside — those are kept as financial
    records.</p>

    <h2>Your requests</h2>
    <p>Write to <a href="https://telegram.example/grailert_bot">the bot</a> to get a copy of your data or
    to have it deleted.</p>
"""),

("404.html", "/404", "404", "Page not found",
 "This page does not exist.", "noindex,nofollow", """
    <h1>404</h1>
    <p class="lede">This page does not exist — but the listings do.</p>
    <p style="margin-top:28px">
      <a class="btn btn-primary" href="/">Back to the front page</a>
    </p>
"""),
]


def main() -> None:
    for filename, path, src, title, desc, robots, body in PAGES:
        html = SHELL.format(title=title, desc=desc, path=path, robots=robots, src=src, body=body)
        with io.open(os.path.join(OUT, filename), "w", encoding="utf-8") as f:
            f.write(html)
        print("собрано:", filename)


if __name__ == "__main__":
    main()
