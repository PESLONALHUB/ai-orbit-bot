import requests

from config import (
    BOT_TOKEN,
    CHANNEL_USERNAME,
    PARSE_MODE,
    DISABLE_WEB_PREVIEW
)

from rss import get_latest_post
from formatter import format_post
from database import save_post


def send_message(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": f"@{CHANNEL_USERNAME}",
        "text": message,
        "parse_mode": PARSE_MODE,
        "disable_web_page_preview": DISABLE_WEB_PREVIEW
    }

    response = requests.post(url, data=payload, timeout=20)
    response.raise_for_status()
    return response.json()


def main():

    posts = get_latest_post()
    if not posts:
       print("No new posts found.")
       return

for post in posts:
    message = format_post(post)

    result = send_message(message)

    if result.get("ok"):
        save_post(post["link"])
        print(f"Posted: {post['title']}")
      else:
        print(result)
if __name__ == "__main":    
    main()
