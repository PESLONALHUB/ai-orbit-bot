import requests
import feedparser

from config import RSS_TIMEOUT, FEEDS_FILE, MAX_POSTS_PER_RUN
from database import is_posted


def load_feeds():
    with open(FEEDS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def get_latest_post():
    posts = []
    seen = set()
    feeds = load_feeds()

    for feed in feeds:
        try:
            response = requests.get(feed, timeout=RSS_TIMEOUT)

            if response.status_code != 200:
                continue

            rss = feedparser.parse(response.content)

            for item in rss.entries[:10]:

                title = item.get("title", "").strip()
                link = item.get("link", "").strip()
                summary = item.get("summary", "").strip()

                if not link:
                    continue

                # Skip already posted links
                if is_posted(link):
                    continue

                # Unique ID (GUID > ID > LINK)
                uid = (
                    item.get("id")
                    or item.get("guid")
                    or link
                )

                # Skip duplicate items in same run
                if uid in seen:
                    continue

                seen.add(uid)

                posts.append({
                    "title": title,
                    "link": link,
                    "summary": summary
                })

                if len(posts) >= MAX_POSTS_PER_RUN:
                    return posts

        except Exception as e:
            print(f"RSS Error ({feed}): {e}")

    return posts if posts else None
