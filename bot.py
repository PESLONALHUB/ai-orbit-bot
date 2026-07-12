import os
import requests
import feedparser

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = os.getenv("CHANNEL_USERNAME")

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": f"@{CHANNEL}",
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    requests.post(url, data=data)
