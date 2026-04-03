# -*- coding: utf-8 -*-
import os
from pathlib import Path


def _load_token_from_env_file() -> str | None:
    """
    Fallback: пытаемся прочитать TOKEN из локального .env (без внешних зависимостей).
    """
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return None

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "TOKEN":
                return value.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[config] Не удалось прочитать .env: {e}")
    return None


def load_token() -> str:
    token = os.getenv("TOKEN")
    if token and token.strip():
        return token.strip()

    token_from_file = _load_token_from_env_file()
    if token_from_file and token_from_file.strip():
        return token_from_file.strip()

    raise RuntimeError(
        "TOKEN не задан. Укажи TOKEN=... в переменных окружения или в файле .env рядом с bot.py."
    )


TOKEN = load_token()


# Админы: список Telegram user_id
# Можно задать переменной окружения ADMIN_IDS="123,456"
def _load_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return []
    ids: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            print(f"[config] ADMIN_IDS: некорректное значение {part!r}")
    return ids


ADMIN_IDS: list[int] = _load_admin_ids()


# Курс пересчета из ₽ (RUB) в USD/EUR.
# USD_RUB_RATE = сколько рублей стоит 1 USD (пример: 90.0)
# EUR_RUB_RATE = сколько рублей стоит 1 EUR (пример: 100.0)
USD_RUB_RATE: float = float(os.getenv("USD_RUB_RATE", "90.0"))
EUR_RUB_RATE: float = float(os.getenv("EUR_RUB_RATE", "100.0"))


CURRENCIES: list[str] = ["RUB", "USD", "EUR"]
CURRENCY_SYMBOLS: dict[str, str] = {"RUB": "₽", "USD": "$", "EUR": "€"}


# Google Sheets (для /connect_google):
# 1) Создай проект в Google Cloud.
# 2) Включи Google Sheets API и Google Drive API.
# 3) Создай Service Account.
# 4) Скачай ключ в формате JSON (это и есть `credentials.json`).
# 5) Положи `credentials.json` в корень проекта рядом с bot.py и запускай команду /connect_google.


