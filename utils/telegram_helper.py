import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_CHAT_ID   = os.environ.get("ADMIN_CHAT_ID")

def send_telegram_message(message: str):
    try:
        url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": ADMIN_CHAT_ID, "text": message}
        r = requests.post(url, data=payload)
        if r.status_code != 200:
            raise Exception(f"status {r.status_code}")
    except Exception as e:
        print(f"텔레그램 전송 오류: {e}")
