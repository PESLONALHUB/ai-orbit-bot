import requests
import feedparser
from config import RSS_TIMEOUT
import feedparser
from config import FEEDS_FILE
from database import is_posted

def load_feeds():
    with open(FEEDS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def get_latest_post():
    feeds = load_feeds()

    for feed in feeds:
        try:
            try:
    response = requests.get(feed, timeout=RSS_TIMEOUT)

    if response.status_code != 200:
        continue

    rss = feedparser.parse(response.content)

except Exception:
    continue

            for item in rss.entries[:10]:

                title = item.get("title", "").strip()
                link = item.get("link", "").strip()
                summary = item.get("summary", "").strip()

                if not link:
                    continue

                if is_posted(link):
                    continue

                return {
                    "title": title,
                    "link": link,
                    "summary": summary
                }

        except Exception as e:
            print(f"RSS Error: {e}")

    return None
