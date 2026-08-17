#!/usr/bin/env python3
"""
Actualiza stats.json y history.json con las estadisticas publicas del perfil
de Blogabet de TheGreenTipster (picks, profit, yield).

- stats.json  -> ultima foto de las 4 cifras mostradas en el "ticket".
- history.json -> serie temporal de "profit" (unidades), un punto por dia,
                   usado para el grafico de evolucion.

El winrate NO esta disponible en la vista principal del perfil (esta en la
pestana "Statistics", que se carga por JS), asi que se mantiene el valor
anterior tal cual estaba en stats.json salvo que lo edites tu a mano.

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
ROOT = Path(__file__).resolve().parent.parent
STATS_FILE = ROOT / "stats.json"
HISTORY_FILE = ROOT / "history.json"

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


def profit_to_number(profit_str: str) -> float:
    """'+117' -> 117.0 ; '-3,5' -> -3.5"""
    cleaned = profit_str.replace(".", "").replace(",", ".") if "," in profit_str else profit_str
    return float(cleaned)


def update_history(profit_value: float, today: str) -> None:
    history = []
    if HISTORY_FILE.exists():
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))

    # Si ya hay un punto de hoy (por ejemplo si se relanza el workflow a mano
    # varias veces el mismo dia), lo actualizamos en vez de duplicarlo.
    existing = next((p for p in history if p["date"] == today), None)
    if existing:
        existing["profit"] = profit_value
    else:
        history.append({"date": today, "profit": profit_value})

    history.sort(key=lambda p: p["date"])
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
    now = datetime.now(timezone.utc)
    current["updated"] = now.isoformat()

    STATS_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] stats.json actualizado: {scraped}")

    if "profit" in scraped:
        try:
            profit_value = profit_to_number(scraped["profit"])
            update_history(profit_value, now.strftime("%Y-%m-%d"))
            print(f"[OK] history.json actualizado con el punto de hoy: {profit_value}")
        except ValueError:
            print(f"[WARN] No se pudo convertir el profit a numero: {scraped['profit']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
