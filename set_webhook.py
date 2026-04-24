#!/usr/bin/env python3
"""Скрипт для установки вебхука Telegram бота"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN не установлен")
    sys.exit(1)

if not WEBHOOK_URL:
    print("❌ WEBHOOK_URL не установлен")
    sys.exit(1)

webhook_full_url = f"{WEBHOOK_URL}/webhook"

print(f"Установка вебхука: {webhook_full_url}")

response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    json={"url": webhook_full_url}
)

if response.status_code == 200:
    result = response.json()
    if result.get("ok"):
        print("✅ Вебхук успешно установлен")

        # Проверка информации о вебхуке
        info_response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
        )
        if info_response.status_code == 200:
            info = info_response.json().get("result", {})
            print(f"\nИнформация о вебхуке:")
            print(f"  URL: {info.get('url')}")
            print(f"  Pending updates: {info.get('pending_update_count', 0)}")
            if info.get('last_error_message'):
                print(f"  Последняя ошибка: {info.get('last_error_message')}")
    else:
        print(f"❌ Ошибка: {result}")
else:
    print(f"❌ HTTP ошибка: {response.status_code}")
    print(response.text)
