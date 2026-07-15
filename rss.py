import requests
import feedparser
import time

from config import RSS_TIMEOUT, FEEDS_FILE, MAX_POSTS_PER_RUN
from database import is_posted


def load_feeds():
    with open(FEEDS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def get_post_time(item):
    if hasattr(item, "published_parsed") and item.published_parsed:
        return time.mktime(item.published_parsed)

    if hasattr(item, "updated_parsed") and item.updated_parsed:
        return time.mktime(item.updated_parsed)

    return 0


def get_latest_post():
    feeds = load_feeds()

    all_posts = []
    seen = set()

    for feed in feeds:
        try:
            response = requests.get(feed, timeout=RSS_TIMEOUT)

            if response.status_code != 200:
                continue

            rss = feedparser.parse(response.content)

            for item in rss.entries:

                title = item.get("title", "").strip()
                link = item.get("link", "").strip()
                summary = item.get("summary", "").strip()

                if not link:
                    continue

                if is_posted(link):
                    continue

                uid = (
                    item.get("id")
                    or item.get("guid")
                    or link
                )

                if uid in seen:
                    continue

                seen.add(uid)

                all_posts.append({
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": get_post_time(item)
                })

        except Exception as e:
            print(f"RSS Error ({feed}): {e}")

    if not all_posts:
        return None

    all_posts.sort(
        key=lambda x: x["published"],
        reverse=True
    )

    unique_sources = set()
    final_posts = []

    for post in all_posts:

        try:
            domain = post["link"].split("/")[2]
        except:
            domain = post["link"]

        if domain in unique_sources:
            continue

        unique_sources.add(domain)
        final_posts.append(post)

        if len(final_posts) >= MAX_POSTS_PER_RUN:
            break

    return final_posts
