#!/usr/bin/env python3
"""
Actualiza stats.json con las estadisticas publicas del perfil de Blogabet
de TheGreenTipster (picks, profit, yield). El winrate NO esta disponible
en la vista principal del perfil (esta en la pestana "Statistics", que se
carga por JS), asi que se mantiene el valor anterior tal cual estaba en
stats.json salvo que lo edites tu a mano.

Uso: python3 scripts/scrape_blogabet.py
Requiere: requests, beautifulsoup4  ->  pip install requests beautifulsoup4
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PROFILE_URL = "https://thegreentipster.blogabet.com/"
STATS_FILE = Path(__file__).resolve().parent.parent / "stats.json"

HEADERS = {
    # User-Agent normal de navegador para evitar bloqueos triviales.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_text(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Texto plano de toda la pagina; el scraping se basa en patrones de texto,
    # no en clases CSS concretas, para que aguante mejor si Blogabet cambia el maquetado.
    return soup.get_text(separator=" ", strip=True)


def extract_stats(page_text: str) -> dict:
    stats = {}

    m_picks = re.search(r"([\d.,]+)\s*Paid picks", page_text, re.IGNORECASE)
    if m_picks:
        stats["picks"] = m_picks.group(1)

    m_profit = re.search(r"([+\-]?\s?[\d.,]+)\s*Profit", page_text, re.IGNORECASE)
    if m_profit:
        stats["profit"] = m_profit.group(1).replace(" ", "")

    m_yield = re.search(r"([+\-]?\s?[\d.,]+%)\s*Yield", page_text, re.IGNORECASE)
    if m_yield:
        stats["yield"] = m_yield.group(1).replace(" ", "")

    return stats


def main() -> int:
    try:
        page_text = fetch_text(PROFILE_URL)
    except requests.RequestException as exc:
        print(f"[ERROR] No se pudo descargar el perfil de Blogabet: {exc}", file=sys.stderr)
        return 1

    scraped = extract_stats(page_text)
    if not scraped:
        print("[ERROR] No se encontro ninguna estadistica en la pagina. "
              "Blogabet puede haber cambiado el formato: revisa scrape_blogabet.py", file=sys.stderr)
        return 1

    current = {}
    if STATS_FILE.exists():
        current = json.loads(STATS_FILE.read_text(encoding="utf-8"))

    current.update(scraped)
    current["updated"] = datetime.now(timezone.utc).isoformat()

    STATS_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] stats.json actualizado: {scraped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
