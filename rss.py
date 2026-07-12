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
            rss = feedparser.parse(feed)

            for item in rss.entries:

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
