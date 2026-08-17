#!/usr/bin/env python3
"""
Sincroniza los picks publicados en los canales de Telegram de TheGreenTipster
con picks.json, para mostrarlos en la web.

MODO CALIBRACION (la primera vez, mientras no existan las variables de entorno
CHAT_ID_FREE / CHAT_ID_VIP): en vez de guardar nada, este script solo IMPRIME
en el log los canales desde los que ha recibido mensajes, con su "chat id" y
su titulo, para que puedas decirme cual es cual. En este modo NO se consume
el offset de Telegram, asi que los mensajes de prueba se pueden volver a leer
mas tarde sin perderlos.

MODO NORMAL (una vez configuradas esas variables): guarda cada foto+pie de
foto nuevo como un pick "pendiente", y cuando editas el pie de foto anadiendo
✅ o ❌ al principio, lo marca como "resuelto" con ese resultado.

Uso: python3 scripts/sync_telegram_picks.py
Requiere: requests  ->  pip install requests

Variables de entorno:
  TELEGRAM_BOT_TOKEN  (obligatoria, secreta)
  CHAT_ID_FREE        (opcional; id numerico del canal gratuito)
  CHAT_ID_VIP         (opcional; id numerico del canal VIP)
"""

import json
import os
import re
import sys
from pathlib import Path

import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID_FREE = os.environ.get("CHAT_ID_FREE", "").strip()
CHAT_ID_VIP = os.environ.get("CHAT_ID_VIP", "").strip()

ROOT = Path(__file__).resolve().parent.parent
PICKS_FILE = ROOT / "picks.json"
STATE_FILE = ROOT / "telegram_state.json"
PHOTOS_DIR = ROOT / "assets" / "picks"

API = f"https://api.telegram.org/bot{TOKEN}"
FILE_API = f"https://api.telegram.org/file/bot{TOKEN}"

RESULT_EMOJI = {"✅": "win", "🟢": "win", "❌": "loss", "🔴": "loss"}


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_updates(offset):
    params = {"timeout": 0, "allowed_updates": json.dumps(["channel_post", "edited_channel_post"])}
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(f"{API}/getUpdates", params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data["result"]


def channel_label(chat_id: str) -> str:
    if chat_id == CHAT_ID_FREE:
        return "free"
    if chat_id == CHAT_ID_VIP:
        return "vip"
    return "desconocido"


def extract_result(caption: str):
    if not caption:
        return None, caption
    first = caption.strip()[:1]
    if first in RESULT_EMOJI:
        return RESULT_EMOJI[first], caption.strip()[1:].strip()
    return None, caption


def download_photo(file_id: str, chat_id: str, message_id: int) -> str | None:
    resp = requests.get(f"{API}/getFile", params={"file_id": file_id}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        return None
    file_path = data["result"]["file_path"]

    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file_path).suffix or ".jpg"
    local_name = f"{chat_id}_{message_id}{ext}"
    local_path = PHOTOS_DIR / local_name

    img_resp = requests.get(f"{FILE_API}/{file_path}", timeout=30)
    img_resp.raise_for_status()
    local_path.write_bytes(img_resp.content)

    return f"assets/picks/{local_name}"


def main() -> int:
    if not TOKEN:
        print("[ERROR] Falta la variable TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1

    calibration_mode = not (CHAT_ID_FREE and CHAT_ID_VIP)
    state = load_json(STATE_FILE, {"offset": None})
    updates = get_updates(state.get("offset"))

    if calibration_mode:
        print("[CALIBRACION] No hay CHAT_ID_FREE / CHAT_ID_VIP configurados todavia.")
        seen = {}
        for upd in updates:
            post = upd.get("channel_post") or upd.get("edited_channel_post")
            if not post:
                continue
            chat = post["chat"]
            seen[chat["id"]] = chat.get("title", "(sin titulo)")
        if not seen:
            print("[CALIBRACION] No se ha recibido ningun mensaje todavia. "
                  "Publica un mensaje de prueba en cada canal y vuelve a lanzar el workflow.")
        else:
            print("[CALIBRACION] Canales detectados:")
            for chat_id, title in seen.items():
                print(f"    chat_id = {chat_id}   ->   \"{title}\"")
            print("[CALIBRACION] Dime cual es el gratuito y cual el VIP para configurarlos.")
        return 0

    picks = load_json(PICKS_FILE, [])
    by_key = {(p["chat_id"], p["message_id"]): p for p in picks}
    last_update_id = state.get("offset", 0) or 0

    for upd in updates:
        last_update_id = max(last_update_id, upd["update_id"] + 1)

        post = upd.get("channel_post")
        edited = upd.get("edited_channel_post")

        if post and post.get("photo"):
            chat_id = str(post["chat"]["id"])
            label = channel_label(chat_id)
            if label == "desconocido":
                continue
            caption = post.get("caption", "")
            result, clean_caption = extract_result(caption)
            photo_file_id = post["photo"][-1]["file_id"]  # la de mayor resolucion
            local_photo = download_photo(photo_file_id, chat_id, post["message_id"])

            entry = {
                "chat_id": chat_id,
                "message_id": post["message_id"],
                "channel": label,
                "caption": clean_caption,
                "photo": local_photo,
                "posted_date": post.get("date"),
                "status": "resuelto" if result else "pendiente",
                "result": result,
            }
            by_key[(chat_id, post["message_id"])] = entry
            print(f"[OK] Nuevo pick guardado ({label}): {clean_caption[:60]}")

        elif edited and edited.get("photo"):
            chat_id = str(edited["chat"]["id"])
            key = (chat_id, edited["message_id"])
            if key not in by_key:
                continue
            caption = edited.get("caption", "")
            result, clean_caption = extract_result(caption)
            by_key[key]["caption"] = clean_caption
            if result:
                by_key[key]["status"] = "resuelto"
                by_key[key]["result"] = result
                print(f"[OK] Pick actualizado a resuelto ({result}): {clean_caption[:60]}")

    all_picks = sorted(by_key.values(), key=lambda p: p["posted_date"], reverse=True)
    save_json(PICKS_FILE, all_picks)
    save_json(STATE_FILE, {"offset": last_update_id})
    print(f"[OK] picks.json actualizado. Total picks guardados: {len(all_picks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
