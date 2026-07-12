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

    return response.json()


def main():

    post = get_latest_post()

    if post is None:
        print("No new post found.")
        return

    message = format_post(post)

    result = send_message(message)

    if result.get("ok"):
        save_post(post["link"])
        print("Post Sent Successfully")
    else:
        print(result)


if __name__ == "__main__":
    main()
