#!/usr/bin/env python3
"""Generate the static GitHub Pages site from data/site.json.

Uruchomienie: python build.py
Wynik trafia do katalogu _site/ (index.html, style.css, script.js, assets/,
favicon.ico, site.webmanifest, robots.txt, sitemap.xml, CNAME, .nojekyll).
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "site.json"
TEMPLATE_FILE = ROOT / "templates" / "index.html"
OUTPUT_DIR = ROOT / "_site"
# Pliki z katalogu głównego repozytorium kopiowane 1:1 do _site/.
ROOT_STATIC_FILES = ("style.css", "script.js", "favicon.ico", "site.webmanifest")


def esc(value: Any) -> str:
    """HTML-escape values coming from the editable JSON file."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def as_list(value: Any, field: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Pole '{field}' musi być listą.")
    return value


def safe_http_url(value: str, fallback: str = "#") -> str:
    value = str(value or "").strip()
    if value.startswith("https://") or value.startswith("http://"):
        return esc(value)
    return fallback


def absolute_url(base: str, path: str) -> str:
    """Zamienia ścieżkę względną (np. assets/og-image.jpg) na pełny adres."""
    path = str(path or "").strip()
    if not path:
        return ""
    if path.startswith("https://") or path.startswith("http://"):
        return path
    return base.rstrip("/") + "/" + path.lstrip("/")


def price_number(value: str) -> str:
    """'250 zł za spotkanie' -> '250'. Zwraca '' gdy brak liczby."""
    match = re.search(r"\d[\d\s]*", str(value or ""))
    return re.sub(r"\s", "", match.group(0)) if match else ""


def phone_digits(phone: str) -> str:
    digits = re.sub(r"\D", "", str(phone or ""))
    if not digits or set(digits) == {"0"}:
        return ""
    return ("+" + digits) if str(phone).lstrip().startswith("+") else digits


def phone_display(phone: str) -> str:
    """'+48 780 602 903' -> '780 602 903' (krótsza forma na przycisku)."""
    return re.sub(r"^\+48\s*", "", str(phone or "").strip())


ICON_PATHS = {
    # Mama z dzieckiem przy piersi: konsultacja laktacyjna.
    "lactation": '<circle cx="9" cy="4.8" r="2.3"/><path d="M4.6 21v-5.6C4.6 11.5 6.7 9 9.8 8.8c1.9-.1 3.3.7 4.1 1.8"/><circle cx="14.6" cy="12.8" r="2.1"/><path d="M16.5 13.9c1.6.4 2.8 1.2 3.3 2.4"/><path d="M7.2 15.4c2.5 3 7.6 3.3 11.4.2"/>',
    # Domek z serduszkiem: wizyta poporodowa w domu.
    "postpartum": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1Z"/><path d="M12 12.8s-2.2-1.3-2.2-2.8a1.4 1.4 0 0 1 2.2-.9 1.4 1.4 0 0 1 2.2.9c0 1.5-2.2 2.8-2.2 2.8Z"/>',
    # Body niemowlęce: opieka nad noworodkiem.
    "newborn": '<path d="M9.3 3.6C10 5 11 5.6 12 5.6s2-.6 2.7-2l3.9 1.7c.7.3 1 1.1.7 1.8l-.7 1.6c-.3.6-1 .9-1.6.6l-1-.5v6.4c0 2.4-1.3 3.8-2.6 5.2h-2.8C9.3 19 8 17.6 8 15.2V8.8l-1 .5c-.6.3-1.3 0-1.6-.6l-.7-1.6c-.3-.7 0-1.5.7-1.8Z"/><path d="M11 18.3h.01M13 18.3h.01"/>',
    # Kropla mleka z serduszkiem: przygotowanie do karmienia.
    "feeding": '<path d="M12 3.2C9.1 7.1 6.3 10.1 6.3 14.1a5.7 5.7 0 0 0 11.4 0c0-4-2.8-7-5.7-10.9Z"/><path d="M12 17.1s-2.7-1.6-2.7-3.6a1.7 1.7 0 0 1 2.7-1.1 1.7 1.7 0 0 1 2.7 1.1c0 2-2.7 3.6-2.7 3.6Z"/>',
    # Serce w dłoniach: towarzyszenie w porodzie.
    "birth": '<path d="M12 20s-7-4.1-7-9.4a3.8 3.8 0 0 1 7-2 3.8 3.8 0 0 1 7 2C19 15.9 12 20 12 20Z"/><path d="M3 18.5c2.1 1.7 4 2.2 6.1 2.1M21 18.5c-2.1 1.7-4 2.2-6.1 2.1"/>',
    # Słońce: dzień z położną.
    "day": '<circle cx="12" cy="12" r="4"/><path d="M12 2.8v2.1M12 19.1v2.1M2.8 12h2.1M19.1 12h2.1M5.5 5.5 7 7M17 17l1.5 1.5M5.5 18.5 7 17M17 7l1.5-1.5"/>',
    # Szal z jednym zwisającym końcem i frędzlami: nauka chustonoszenia.
    "babywearing": '<path d="M4 7.2c2.4-3.4 6.1-3.7 9.1-.8 2.5 2.4 4.6 2.5 6.9.8l-.9 3.1c-2.6 1.5-5.4.8-7.8-1.3-2.4-2.1-4.6-2-6.8.7Z"/><path d="M11.9 9.3 8.7 19.1c-.3.9.2 1.8 1.2 2l2.1.5c1 .2 1.8-.4 2-1.4l1.8-9.2"/><path d="m9.1 21.2-.4 1m2.5-.5-.1 1m2.3-.8.3.9"/>',
    # Miseczka z łyżeczką: rozszerzanie diety.
    "weaning": '<path d="M3.5 12h12a6 6 0 0 1-12 0Z"/><path d="M7.5 20.5h4"/><ellipse cx="19" cy="6.4" rx="1.8" ry="2.6"/><path d="M19 9v11.5"/><path d="M7 9.2c.6-.7.6-1.4 0-2.1M11 9.2c.6-.7.6-1.4 0-2.1"/>',
    # Otwarta książka: domowa szkoła rodzenia.
    "birth-school": '<path d="M3 5.5c3.4-1.2 6.4-.7 9 1.4 2.6-2.1 5.6-2.6 9-1.4v13c-3.4-1.2-6.4-.7-9 1.4-2.6-2.1-5.6-2.6-9-1.4Z"/><path d="M12 7v12.9M6.5 9h2M6.5 12h2M15.5 9h2M15.5 12h2"/>',
    # Liść: relaksacja w ciąży.
    "relaxation": '<path d="M20.3 3.8C10.4 4 4.1 8.1 4.1 14.4c0 3.3 2.1 5.6 5.1 5.6 6.2 0 10.6-6.3 11.1-16.2Z"/><path d="M4.5 19.4c3.5-4.2 7.6-7.6 13-10.7M9.1 15.2l-.4-4.1m4.3 1.1 4.1-.3"/>',
    # Serce z linią tętna: KTG.
    "ktg": '<path d="M12 20.2s-7.8-4.6-7.8-10.3a4.1 4.1 0 0 1 7.8-2.2 4.1 4.1 0 0 1 7.8 2.2c0 5.7-7.8 10.3-7.8 10.3Z"/><path d="M6.6 12.4h2l1.2-2.2 1.8 4.4 1.8-5.4 1.3 3.2h2.7"/>',
    # Dymek rozmowy z serduszkiem: z uważnością i bez oceniania.
    "care": '<path d="M20.5 11.6a8.1 8.1 0 0 1-11.8 7.2L3.5 20.4l1.6-4.8a8.1 8.1 0 1 1 15.4-4Z"/><path d="M12 14.4s-2.4-1.4-2.4-3.1a1.5 1.5 0 0 1 2.4-1 1.5 1.5 0 0 1 2.4 1c0 1.7-2.4 3.1-2.4 3.1Z"/>',
    # Otwarta książka: w oparciu o wiedzę.
    "knowledge": '<path d="M3 5.5c3.4-1.2 6.4-.7 9 1.4 2.6-2.1 5.6-2.6 9-1.4v13c-3.4-1.2-6.4-.7-9 1.4-2.6-2.1-5.6-2.6-9-1.4Z"/><path d="M12 7v12.9"/>',
    # Lista z odhaczonymi punktami: praktycznie.
    "practice": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v2.4H9z"/><path d="m8.4 10.4 1.3 1.3 2.3-2.4M13.8 10.6h2.2M8.4 15.6l1.3 1.3 2.3-2.4M13.8 15.8h2.2"/>',
    # Tarcza z ptaszkiem: z poszanowaniem granic.
    "respect": '<path d="M12 3 19 6v5.2c0 4.4-2.8 7.6-7 9.8-4.2-2.2-7-5.4-7-9.8V6Z"/><path d="m9 12 2 2 4-4"/>',
    # Zegar: bez pośpiechu.
    "calm": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.2 2M5 3 3 5"/>',
    # Nieskończoność: ciągłość opieki.
    "continuity": '<path d="M7 7c-2.2 0-4 1.8-4 4s1.8 4 4 4c3.2 0 6.8-6 10-6 2.2 0 4 1.8 4 4s-1.8 4-4 4c-3.2 0-6.8-6-10-6"/>',
    "heart": '<path d="M12 20s-7-4.2-7-9.5a3.8 3.8 0 0 1 7-2 3.8 3.8 0 0 1 7 2C19 15.8 12 20 12 20Z"/>',
    # Ikony kontaktowe.
    "phone": '<path d="M21.2 16.6v2.8a1.9 1.9 0 0 1-2.1 1.9 18.8 18.8 0 0 1-8.2-2.9 18.5 18.5 0 0 1-5.7-5.7A18.8 18.8 0 0 1 2.3 4.4 1.9 1.9 0 0 1 4.2 2.3H7a1.9 1.9 0 0 1 1.9 1.6c.1.9.4 1.8.7 2.6a1.9 1.9 0 0 1-.4 2L8 9.7a15.2 15.2 0 0 0 5.7 5.7l1.2-1.2a1.9 1.9 0 0 1 2-.4c.8.3 1.7.6 2.6.7a1.9 1.9 0 0 1 1.7 2.1Z"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m3.8 6.8 8.2 6 8.2-6"/>',
    "instagram": '<rect x="3.2" y="3.2" width="17.6" height="17.6" rx="5"/><circle cx="12" cy="12" r="4.1"/><circle cx="17.2" cy="6.8" r=".9" fill="currentColor" stroke="none"/>',
    "pin": '<path d="M12 21.2s-6.6-5.7-6.6-11.1a6.6 6.6 0 0 1 13.2 0c0 5.4-6.6 11.1-6.6 11.1Z"/><circle cx="12" cy="10.1" r="2.4"/>',
    "message": '<path d="M20.5 11.6a8.1 8.1 0 0 1-11.8 7.2L3.5 20.4l1.6-4.8a8.1 8.1 0 1 1 15.4-4Z"/>',
}



# Logo: piktogram mamy tulącej dziecko (głowa, ciało w kształcie serca, główka dziecka).
# Ten sam rysunek jest w assets/logo.svg i (pogrubiony) w faviconach.
LOGO_PATHS = (
    '<circle cx="74.7" cy="40.9" r="33.6"/><circle cx="115.7" cy="113.9" r="26.8"/>'
    '<path d="M104.8 138.4C80.4 127.5 59 86.5 35.5 86.5C20.4 86.5 7.5 99.4 7.5 110.9C7.5 143.9 33 179.4 74 192.8'
    'C106.3 185.6 139.5 152.9 142.4 116.1"/>'
)
LOGO_SVG = (
    '<svg class="brand-pictogram" viewBox="0 0 150 200" aria-hidden="true" focusable="false" fill="none" '
    f'stroke="currentColor" stroke-width="10.1" stroke-linecap="round" stroke-linejoin="round">{LOGO_PATHS}</svg>'
)


def seal_svg(text: str) -> str:
    """Okrągła pieczątka: napis dookoła i piktogram w środku (ozdoba, czytnik ekranu ją pomija)."""
    # Okrąg r=74 ma obwód ok. 465; textLength dopasowuje odstępy między literami do obwodu.
    return f'''<svg class="print-seal" viewBox="0 0 200 200" aria-hidden="true" focusable="false">
          <defs><path id="seal-ring" d="M100,100 m-74,0 a74,74 0 1,1 148,0 a74,74 0 1,1 -148,0"/></defs>
          <circle class="print-seal-disc" cx="100" cy="100" r="97"/>
          <text><textPath href="#seal-ring" textLength="458" lengthAdjust="spacing">{esc(text)}</textPath></text>
          <g class="print-seal-mark" transform="translate(73.75 65) scale(0.35)">{LOGO_PATHS}</g>
        </svg>'''


def icon_svg(name: str) -> str:
    """Return a consistent decorative line pictogram for service/value cards."""
    key = str(name or "heart")
    paths = ICON_PATHS.get(key, ICON_PATHS["heart"])
    return f'<svg class="line-pictogram" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'


# ---------------------------------------------------------------- sekcje

def render_care_path(data: dict) -> str:
    """Nić opieki: falista linia z przystankami-etapami pod hero."""
    path = data.get("care_path", {})
    stages = as_list(data.get("stages", []), "stages")
    if not stages:
        return ""
    count = len(stages)
    # Fala przecina oś (y=20) dokładnie w środku każdej kolumny:
    # odcinki co pół szerokości kolumny, naprzemiennie w górę i w dół.
    step = 1000 / (count * 2)
    d = f"M0,20 Q{step / 2:.2f},2 {step:.2f},20"
    for i in range(2, count * 2 + 1):
        d += f" T{step * i:.2f},20"
    stops = "\n".join(
        f'''<li class="care-stop"><a href="#etap-{esc(stage.get('id', ''))}"><span class="care-stop-label">{esc(stage.get('label', ''))}</span><span class="care-stop-note">{esc(stage.get('path_note', ''))}</span></a></li>'''
        for stage in stages
    )
    band = ""
    if path.get("band"):
        target = esc(path.get("band_target", "wsparcie"))
        band = f'<a class="care-band" href="#{target}">{esc(path["band"])}</a>'
    return f'''<section class="care-path" aria-labelledby="care-path-title">
      <h2 class="care-path-title" id="care-path-title">{esc(path.get('title', ''))}</h2>
      <div class="care-track" style="--stops:{count}">
        <svg class="care-line" viewBox="0 0 1000 40" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path pathLength="1" d="{d}"/></svg>
        <ol class="care-stops">
          {stops}
        </ol>
        {band}
      </div>
    </section>'''


def render_service_card(item: dict) -> str:
    classes = ["service-card"]
    if item.get("featured"):
        classes.append("featured")
    if item.get("soft"):
        classes.append("service-card-soft")
    bullets = "\n".join(f"<li>{esc(text)}</li>" for text in as_list(item.get("bullets", []), "services.bullets"))
    note = f'<p class="service-note">{esc(item["note"])}</p>' if item.get("note") else ""
    summary = f'<p class="service-summary">{esc(item["summary"])}</p>' if item.get("summary") else ""
    topic = f' data-topic="{esc(item["topic"])}"' if item.get("topic") else ""
    return f'''<article class="{' '.join(classes)}" id="{esc(item.get('id', ''))}">
          <div class="service-icon">{icon_svg(item.get('icon', 'heart'))}</div>
          <p class="card-kicker">{esc(item.get('kicker', ''))}</p>
          <h4>{esc(item.get('title', ''))}</h4>
          {summary}
          <details class="service-details">
            <summary>Poznaj szczegóły</summary>
            <div class="service-details-content">
              <p>{esc(item.get('description', ''))}</p>
              <ul>{bullets}</ul>
              {note}
            </div>
          </details>
          <a class="card-link" href="#kontakt"{topic}>{esc(item.get('cta', 'Napisz do mnie'))}</a>
        </article>'''


def render_stages(data: dict) -> str:
    services = as_list(data.get("services", []), "services")
    stages = as_list(data.get("stages", []), "stages")
    known = {stage.get("id") for stage in stages}
    orphans = [s.get("title", "?") for s in services if s.get("stage") not in known]
    if orphans:
        raise ValueError("Usługi bez poprawnego pola 'stage': " + ", ".join(orphans))
    blocks = []
    for stage in stages:
        cards = "\n".join(render_service_card(s) for s in services if s.get("stage") == stage.get("id"))
        if not cards:
            continue
        sid = esc(stage.get("id", ""))
        blocks.append(f'''<section class="stage" id="etap-{sid}" aria-labelledby="etap-{sid}-tytul">
        <div class="stage-head">
          <h3 id="etap-{sid}-tytul">{esc(stage.get('title', ''))}</h3>
          <p>{esc(stage.get('intro', ''))}</p>
        </div>
        <div class="stage-cards">
        {cards}
        </div>
      </section>''')
    return "\n".join(blocks)


def render_prices(data: dict, settings: dict) -> str:
    """Cennik: jedyne miejsce z cenami na stronie (osobna sekcja #cennik)."""
    if not settings.get("show_prices", False):
        return ""
    prices = data.get("prices", {})
    rows = "\n".join(
        # Pojedyncze usługi: tylko nazwa i cena (czas trwania pokazujemy wyłącznie przy pakietach).
        f'''<div class="price-entry"><span>{esc(item.get('name', ''))}</span><strong>{esc(item.get('price', ''))}</strong></div>'''
        for item in as_list(prices.get("items", []), "prices.items")
    )
    packages = "\n".join(
        f'''<article class="price-package"><div><h4>{esc(item.get('name', ''))}</h4><p>{esc(item.get('duration', ''))}</p><small>{esc(item.get('details', ''))}</small></div><strong>{esc(item.get('price', ''))}</strong></article>'''
        for item in as_list(prices.get("packages", []), "prices.packages")
    )
    package_html = f'<div class="price-packages"><h3 class="price-packages-title">Pakiety</h3>{packages}</div>' if packages else ""
    travel_html = f'<p class="price-travel">{esc(prices.get("travel", ""))}</p>' if prices.get("travel") else ""
    subtitle = f'<p class="price-subtitle">{esc(prices.get("title", ""))}</p>' if prices.get("title") else ""
    intro_html = f'<p class="section-intro">{esc(prices.get("intro", ""))}</p>' if prices.get("intro") else ""
    return f'''<section class="section prices" id="cennik">
      <div class="section-heading">
        <h2>Cennik</h2>
        {subtitle}
        {intro_html}
      </div>
      <div class="price-note">
        <div class="price-list">{rows}</div>
        {package_html}{travel_html}
      </div>
    </section>'''


def render_reviews(data: dict, settings: dict) -> str:
    if not settings.get("show_reviews", True):
        return ""
    reviews = data.get("reviews", {})
    cards = "\n".join(
        f'''<figure class="review-card"><blockquote class="review-quote"><p>„{esc(item.get('quote', ''))}”</p></blockquote><figcaption class="review-author">{esc(item.get('author', ''))}</figcaption></figure>'''
        for item in as_list(reviews.get("items", []), "reviews.items")
    )
    source_url = safe_http_url(reviews.get("source_url", ""))
    source_name = esc(reviews.get("source_name", "ZnanyLekarz"))
    return f'''<section class="section reviews" id="opinie">
      <div class="section-heading">
        <h2>{esc(reviews.get('title', ''))}</h2>
        <p class="section-intro">{esc(reviews.get('intro', ''))}</p>
      </div>
      <div class="review-grid">{cards}</div>
      <p class="reviews-source">{esc(reviews.get('source_note', ''))} <a href="{source_url}" target="_blank" rel="noopener noreferrer">Zobacz wszystkie opinie w serwisie {source_name} ↗</a></p>
    </section>'''


def render_quote_band(data: dict, settings: dict) -> str:
    text = data.get("quote_band", "")
    if not text or not settings.get("show_quote_band", True):
        return ""
    return f'''<section class="quote-band" aria-label="Myśl przewodnia">
      <span class="quote-mark" aria-hidden="true">“</span>
      <p>{esc(text)}</p>
    </section>'''


def render_values(data: dict) -> str:
    work = data.get("work_section", {})
    entries = [
        f'''<div class="work-card"><span class="work-icon">{icon_svg(item.get('icon', 'heart'))}</span><h3>{esc(item.get('title', ''))}</h3><p>{esc(item.get('text', ''))}</p></div>'''
        for item in as_list(data.get("values", []), "values")
    ]
    heading = f'''<div class="values-heading"><h2>{esc(work.get('title', ''))}</h2></div>'''
    return heading + "\n" + "\n".join(entries)


def render_faq(data: dict, settings: dict) -> str:
    if not settings.get("show_faq", True):
        return ""
    faq = data.get("faq", {})
    items = "\n".join(
        f'''<details class="faq-item"><summary>{esc(item.get('question', ''))}</summary><p>{esc(item.get('answer', ''))}</p></details>'''
        for item in as_list(faq.get("items", []), "faq.items")
    )
    return f'''<section class="section faq" id="faq">
      <div class="section-heading">
        <h2>{esc(faq.get('title', ''))}</h2>
      </div>
      <div class="faq-list">{items}</div>
    </section>'''


def safe_object_position(value: str, field: str) -> str:
    position = str(value or "50% 30%").strip()
    if not re.fullmatch(r"[0-9a-z.%\s-]{1,40}", position):
        raise ValueError(f"{field}: użyj np. \"50% 30%\" albo \"center top\".")
    return position


def render_hero_art(hero: dict) -> str:
    """Prawa część hero: zdjęcie jak odbitka z instaxa (biały margines, szerszy pusty pasek na dole)
    na kartce w kolorze gliny, obok okrągła pieczątka z napisem hero.seal_text."""
    photo = str(hero.get("photo", "")).strip()
    position = safe_object_position(hero.get("photo_position"), "hero.photo_position")
    image = f'''<img class="hero-photo" src="{esc(photo)}" alt="{esc(hero.get('photo_alt', ''))}" style="object-position: {esc(position)}" fetchpriority="high" decoding="async">'''
    seal_text = str(hero.get("seal_text", "")).strip()
    seal_html = seal_svg(seal_text) if seal_text else ""
    return f'''<div class="hero-art hero-art-print">
        <div class="print-block" aria-hidden="true"></div>
        <figure class="print-card">{image}</figure>
        {seal_html}
      </div>'''


def render_about_aside(about: dict) -> str:
    parts = []
    facts = as_list(about.get("facts", []), "about.facts")
    if facts:
        rows = "".join(f'<div><dt>{esc(f.get("label", ""))}</dt><dd>{esc(f.get("value", ""))}</dd></div>' for f in facts)
        parts.append(f'''<div class="about-facts"><p class="about-facts-title">{esc(about.get('facts_title', 'W skrócie'))}</p><dl>{rows}</dl></div>''')
    return "\n".join(parts)


def render_about_beliefs(about: dict) -> str:
    beliefs = as_list(about.get("beliefs", []), "about.beliefs")
    if not beliefs:
        return ""
    items = "".join(f"<li>{esc(item)}</li>" for item in beliefs)
    return f'''<div class="about-beliefs"><h3>{esc(about.get('beliefs_title', 'Wierzę, że'))}:</h3><ul>{items}</ul></div>'''


def render_about_qualifications(about: dict) -> str:
    qualifications = as_list(about.get("qualifications", []), "about.qualifications")
    if not qualifications:
        return ""
    items = "".join(f"<li>{esc(item)}</li>" for item in qualifications)
    return f'''<details class="about-qualifications"><summary>{esc(about.get('qualifications_title', 'Wykształcenie i kursy'))}</summary><ul>{items}</ul></details>'''


def contact_item(icon: str, label: str, value: str, href: str = "", external: bool = False) -> str:
    """Jedna pozycja kontaktu: okrągła ikona, etykieta i wartość (link lub tekst)."""
    inner = f'<span class="contact-icon">{icon_svg(icon)}</span><span class="contact-text"><span class="contact-label">{esc(label)}</span><span class="contact-value">{value}</span></span>'
    if not href:
        return f'<p class="contact-item">{inner}</p>'
    extra = ' target="_blank" rel="noopener noreferrer"' if external else ""
    return f'<a class="contact-item" href="{href}"{extra}>{inner}</a>'


def render_contact_details(contact: dict, settings: dict) -> str:
    bits: list[str] = []
    phone = str(contact.get("phone", "")).strip()
    tel = phone_digits(phone)
    if phone:
        href = esc(f"tel:{tel}") if tel and len(tel.lstrip("+")) >= 7 else ""
        bits.append(contact_item("phone", "Telefon", esc(phone), href))

    email = str(contact.get("email", "")).strip()
    if email:
        href = esc(f"mailto:{email}") if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) else ""
        bits.append(contact_item("mail", "E-mail", esc(email), href))

    instagram = str(contact.get("instagram", "")).strip()
    instagram_url = safe_http_url(contact.get("instagram_url", ""))
    if instagram and instagram_url != "#":
        bits.append(contact_item("instagram", "Instagram", f"@{esc(instagram)} ↗", instagram_url, external=True))

    # Adres gabinetu: pokazywany dopiero po włączeniu settings.show_address.
    address = str(contact.get("address", "")).strip()
    if settings.get("show_address", False) and address:
        bits.append(contact_item("pin", "Adres", esc(address)))

    service_area = str(contact.get("service_area", "")).strip()
    if settings.get("show_service_area", True) and service_area:
        bits.append(contact_item("pin", "Obszar wizyt", esc(service_area)))
    return "\n".join(bits)


# ---------------------------------------------------------- SEO / dane

def build_json_ld(data: dict, canonical: str, og_image: str) -> str:
    """Dane strukturalne schema.org (JSON-LD): WebSite, MedicalBusiness, Person, FAQPage."""
    site = data.get("site", {})
    brand = data.get("brand", {})
    contact = data.get("contact", {})
    about = data.get("about", {})
    reviews = data.get("reviews", {})
    settings = data.get("settings", {})
    base = canonical.rstrip("/") + "/"
    business_id = base + "#praktyka"
    person_id = base + "#katarzyna"

    same_as = [u for u in (contact.get("instagram_url"), reviews.get("source_url")) if str(u or "").startswith("http")]
    cities = [{"@type": "City", "name": c} for c in as_list(site.get("service_cities", []), "site.service_cities")]

    business: dict[str, Any] = {
        "@type": "MedicalBusiness",
        "@id": business_id,
        "name": brand.get("name", ""),
        "alternateName": f"{brand.get('name', '')} {brand.get('owner', '')}".strip(),
        "description": site.get("meta_description", ""),
        "url": base,
        "image": og_image,
        "logo": absolute_url(base, "assets/icon-512.png"),
        "medicalSpecialty": "Midwifery",
        "areaServed": cities,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": site.get("locality", ""),
            "addressRegion": site.get("region", ""),
            "addressCountry": site.get("country", "PL"),
        },
        "founder": {"@id": person_id},
        "employee": {"@id": person_id},
        "knowsLanguage": "pl",
        "currenciesAccepted": "PLN",
    }
    tel = phone_digits(contact.get("phone", ""))
    if tel:
        business["telephone"] = tel
    if contact.get("email"):
        business["email"] = contact["email"]
    if same_as:
        business["sameAs"] = same_as

    if settings.get("show_prices", False):
        prices = data.get("prices", {})
        entries = as_list(prices.get("items", []), "prices.items") + as_list(prices.get("packages", []), "prices.packages")
        offers = []
        for entry in entries:
            service: dict[str, Any] = {"@type": "Service", "name": entry.get("name", ""), "areaServed": cities}
            if entry.get("details"):
                service["description"] = entry["details"]
            offer: dict[str, Any] = {"@type": "Offer", "itemOffered": service, "url": base + "#cennik"}
            number = price_number(entry.get("price", ""))
            if number:
                offer["price"] = number
                offer["priceCurrency"] = "PLN"
            offers.append(offer)
        if offers:
            business["hasOfferCatalog"] = {"@type": "OfferCatalog", "name": "Wizyty domowe położnej", "itemListElement": offers}
        numbers = [int(price_number(i.get("price", ""))) for i in as_list(prices.get("items", []), "prices.items") if price_number(i.get("price", ""))]
        if numbers:
            business["priceRange"] = f"{min(numbers)}–{max(numbers)} zł"

    person: dict[str, Any] = {
        "@type": "Person",
        "@id": person_id,
        "name": brand.get("owner", ""),
        "jobTitle": "Położna i doradczyni laktacyjna",
        "worksFor": {"@id": business_id},
        "knowsAbout": ["położnictwo", "laktacja", "karmienie piersią", "opieka nad noworodkiem", "połóg", "przygotowanie do porodu"],
    }
    person_photo = str(data.get("hero", {}).get("photo", "")).strip()
    if person_photo:
        person["image"] = absolute_url(base, person_photo)
    alumni = next((q for q in as_list(about.get("qualifications", []), "about.qualifications") if "Uniwersytet" in q), "")
    if alumni:
        person["alumniOf"] = {"@type": "CollegeOrUniversity", "name": alumni.split(",")[-1].strip()}
    if same_as:
        person["sameAs"] = same_as

    graph: list[dict[str, Any]] = [
        {
            "@type": "WebSite",
            "@id": base + "#strona",
            "url": base,
            "name": brand.get("name", ""),
            "inLanguage": "pl-PL",
            "publisher": {"@id": business_id},
        },
        business,
        person,
    ]
    if settings.get("show_faq", True):
        faq_items = as_list(data.get("faq", {}).get("items", []), "faq.items")
        if faq_items:
            graph.append({
                "@type": "FAQPage",
                "@id": base + "#faq",
                "mainEntity": [
                    {"@type": "Question", "name": q.get("question", ""), "acceptedAnswer": {"@type": "Answer", "text": q.get("answer", "")}}
                    for q in faq_items
                ],
            })
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=2)
    # Nie pozwól, by treść zamknęła znacznik <script>.
    return payload.replace("<", "\\u003c")


def build_sitemap(canonical: str, today: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{esc(canonical)}</loc>
    <lastmod>{today}</lastmod>
  </url>
</urlset>
'''


def build_robots(canonical: str) -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {canonical.rstrip('/')}/sitemap.xml\n"


# ---------------------------------------------------------- składanie

def build_replacements(data: dict) -> dict[str, str]:
    site = data.get("site", {})
    brand = data.get("brand", {})
    hero = data.get("hero", {})
    services_section = data.get("services_section", {})
    about = data.get("about", {})
    contact = data.get("contact", {})
    contact_form = data.get("contact_form", {})
    footer = data.get("footer", {})
    settings = data.get("settings", {})

    tagline = " ".join(str(brand.get(k, "")) for k in ("tagline_first", "tagline_highlight", "tagline_last")).strip()
    site_title = site.get("title") or f"{brand.get('name', '')} {tagline} | {brand.get('owner', '')}"
    about_paragraphs = "\n".join(f"<p>{esc(p)}</p>" for p in as_list(about.get("paragraphs", []), "about.paragraphs"))
    canonical_url = str(site.get("canonical_url", "")).strip()
    if not canonical_url.startswith("https://"):
        raise ValueError("site.canonical_url musi zaczynać się od https:// (np. https://czulapolozna.pl/).")
    og_image = absolute_url(canonical_url, site.get("og_image", ""))
    email = str(contact.get("email", "")).strip()
    tel = phone_digits(contact.get("phone", ""))
    price_nav = '<a href="#cennik">Cennik</a>' if settings.get("show_prices", False) else ""
    reviews_nav = '<a href="#opinie">Opinie</a>' if settings.get("show_reviews", True) else ""
    faq_nav = '<a href="#faq">FAQ</a>' if settings.get("show_faq", True) else ""
    keywords = ", ".join(str(k) for k in as_list(site.get("keywords", []), "site.keywords"))

    return {
        "{{SITE_TITLE}}": esc(site_title),
        "{{META_DESCRIPTION}}": esc(site.get("meta_description", "")),
        "{{META_KEYWORDS}}": esc(keywords),
        "{{CANONICAL_URL}}": esc(canonical_url),
        "{{OG_TITLE}}": esc(site.get("og_title") or site_title),
        "{{OG_DESCRIPTION}}": esc(site.get("og_description") or site.get("meta_description", "")),
        "{{OG_IMAGE}}": esc(og_image),
        "{{OG_IMAGE_ALT}}": esc(site.get("og_image_alt", "")),
        "{{JSON_LD}}": build_json_ld(data, canonical_url, og_image),
        "{{BRAND_ARIA}}": esc(f"{brand.get('name', '')}, {tagline}"),
        "{{BRAND_FOOTER_ARIA}}": esc(f"{brand.get('name', '')}, {brand.get('owner', '')}"),
        "{{LOGO_MARK}}": LOGO_SVG,
        "{{BRAND_NAME}}": esc(brand.get("name", "")),
        "{{BRAND_OWNER}}": esc(brand.get("owner", "")),
        "{{TAGLINE_FIRST}}": esc(brand.get("tagline_first", "")),
        "{{TAGLINE_HIGHLIGHT}}": esc(brand.get("tagline_highlight", "")),
        "{{TAGLINE_LAST}}": esc(brand.get("tagline_last", "")),
        "{{HERO_ROLE_LINE}}": esc(hero.get("role_line", "")),
        "{{HERO_HEADING_LINE}}": esc(hero.get("heading_line", "")),
        "{{HERO_HEADING_EMPHASIS}}": esc(hero.get("heading_emphasis", "")),
        "{{HERO_HEADING_END}}": esc(hero.get("heading_end", "")),
        "{{HERO_LOCATION}}": esc(hero.get("location", "")),
        "{{HERO_LEAD}}": esc(hero.get("lead", "")),
        "{{HERO_NOTE}}": esc(hero.get("note", "")),
        "{{HERO_ART_HTML}}": render_hero_art(hero),
        "{{PHONE_HREF}}": esc(f"tel:{tel}") if tel else "#kontakt",
        "{{SMS_HREF}}": esc(f"sms:{tel}") if tel else "#kontakt",
        "{{PHONE_DISPLAY}}": esc(phone_display(contact.get("phone", ""))),
        "{{ICON_PHONE}}": icon_svg("phone"),
        "{{ICON_MESSAGE}}": icon_svg("message"),
        "{{CARE_PATH_HTML}}": render_care_path(data),
        "{{SERVICES_TITLE}}": esc(services_section.get("title", "")),
        "{{SERVICES_INTRO}}": esc(services_section.get("intro", "")),
        "{{STAGES_HTML}}": render_stages(data),
        "{{PRICES_SECTION}}": render_prices(data, settings),
        "{{PRICES_NAV_LINK}}": price_nav,
        "{{REVIEWS_SECTION}}": render_reviews(data, settings),
        "{{REVIEWS_NAV_LINK}}": reviews_nav,
        "{{FAQ_SECTION}}": render_faq(data, settings),
        "{{FAQ_NAV_LINK}}": faq_nav,
        "{{QUOTE_BAND}}": render_quote_band(data, settings),
        "{{ABOUT_TITLE}}": esc(about.get("title", "")),
        "{{ABOUT_FACTS_TITLE}}": esc(about.get("facts_title", "W skrócie")),
        "{{ABOUT_ASIDE_HTML}}": render_about_aside(about),
        "{{ABOUT_LEAD}}": esc(about.get("lead", "")),
        "{{ABOUT_PARAGRAPHS}}": about_paragraphs,
        "{{ABOUT_BELIEFS_HTML}}": render_about_beliefs(about),
        "{{ABOUT_QUALIFICATIONS_HTML}}": render_about_qualifications(about),
        "{{ABOUT_SIGNATURE_FIRST}}": esc(about.get("signature_first", "")),
        "{{ABOUT_SIGNATURE_SECOND}}": esc(about.get("signature_second", "")),
        "{{VALUES_HTML}}": render_values(data),
        "{{CONTACT_TITLE}}": esc(contact.get("title", "")),
        "{{CONTACT_LEAD}}": esc(contact.get("lead", "")),
        "{{CONTACT_DETAILS_HTML}}": render_contact_details(contact, settings),
        "{{CONTACT_EMAIL}}": esc(email),
        "{{CONTACT_FORM_TITLE}}": esc(contact_form.get("title", "")),
        "{{CONTACT_FORM_INTRO}}": esc(contact_form.get("intro", "")),
        "{{CONTACT_TOPICS_HTML}}": "\n".join(f'<option>{esc(t)}</option>' for t in as_list(contact_form.get("topics", []), "contact_form.topics")),
        "{{CONTACT_METHODS_HTML}}": '<option value="" selected>Nie wybrano</option>' + "\n".join(f'<option value="{esc(m)}">{esc(m)}</option>' for m in as_list(contact_form.get("preferred_contact_options", []), "contact_form.preferred_contact_options")),
        "{{CONTACT_FORM_HELPER}}": esc(contact_form.get("helper_note", "")),
        "{{FOOTER_DESCRIPTION}}": esc(brand.get("footer_description", "")),
        "{{FOOTER_DOMAIN}}": esc(site.get("domain", "")),
        "{{FOOTER_COPYRIGHT_SUFFIX}}": esc(footer.get("copyright_suffix", "")),
        "{{YEAR}}": str(dt.date.today().year),
    }


def main() -> int:
    try:
        with DATA_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        template = TEMPLATE_FILE.read_text(encoding="utf-8")
        replacements = build_replacements(data)
        output = template
        for token, value in replacements.items():
            output = output.replace(token, value)

        leftovers = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", output)))
        if leftovers:
            raise ValueError("Nieuzupełnione pola szablonu: " + ", ".join(leftovers))

        if not data.get("brand", {}).get("name"):
            raise ValueError("Uzupełnij brand.name w data/site.json.")
        if not data.get("contact", {}).get("email"):
            raise ValueError("Uzupełnij contact.email w data/site.json - formularz używa tego adresu.")

        hero_photo = str(data.get("hero", {}).get("photo", "")).strip()
        if not hero_photo:
            raise ValueError("Uzupełnij hero.photo w data/site.json (zdjęcie na pierwszej stronie).")
        if not hero_photo.startswith("http") and not (ROOT / hero_photo).exists():
            raise ValueError(f"hero.photo: nie ma pliku {hero_photo} (wgraj go do repozytorium).")
        canonical = data["site"]["canonical_url"]
        today = dt.date.today().isoformat()

        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True)
        (OUTPUT_DIR / "index.html").write_text(output, encoding="utf-8")
        for filename in ROOT_STATIC_FILES:
            source = ROOT / filename
            if source.exists():
                shutil.copy2(source, OUTPUT_DIR / filename)
        shutil.copytree(ROOT / "assets", OUTPUT_DIR / "assets")
        (OUTPUT_DIR / "sitemap.xml").write_text(build_sitemap(canonical, today), encoding="utf-8")
        (OUTPUT_DIR / "robots.txt").write_text(build_robots(canonical), encoding="utf-8")

        domain = str(data.get("site", {}).get("domain", "")).strip()
        if domain:
            if not re.fullmatch(r"[A-Za-z0-9.-]+", domain):
                raise ValueError("site.domain ma nieprawidłowy format domeny.")
            (OUTPUT_DIR / "CNAME").write_text(domain + "\n", encoding="utf-8")
        (OUTPUT_DIR / ".nojekyll").write_text("", encoding="utf-8")

        print(f"Gotowe: wygenerowano {OUTPUT_DIR.relative_to(ROOT)}/index.html")
        print("Dodatkowo: sitemap.xml, robots.txt, dane strukturalne JSON-LD w <head>.")
        print("Dane wczytano z data/site.json. Plik JSON nie jest kopiowany do katalogu publikacyjnego.")
        return 0
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
        print(f"Błąd budowania strony: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
