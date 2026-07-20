import time
import requests
import feedparser
from urllib.parse import urlsplit, urlunsplit

from config import RSS_TIMEOUT, FEEDS_FILE, MAX_POSTS_PER_RUN
from database import is_posted


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def normalize_url(url):
    try:
        p = urlsplit(url)
        return urlunsplit((p.scheme, p.netloc.lower(), p.path, "", ""))
    except Exception:
        return url


def get_post_time(item):
    if getattr(item, "published_parsed", None):
        return time.mktime(item.published_parsed)
    if getattr(item, "updated_parsed", None):
        return time.mktime(item.updated_parsed)
    return 0


def extract_image(item):
    for m in item.get("media_content", []):
        if m.get("url"):
            return m["url"]
    for m in item.get("media_thumbnail", []):
        if m.get("url"):
            return m["url"]
    for link in item.get("links", []):
        if link.get("type", "").startswith("image") and link.get("href"):
            return link["href"]
    for e in getattr(item, "enclosures", []):
        if e.get("href"):
            return e["href"]
    return None


def get_latest_post():
    posts = []
    seen = set()

    for feed in load_feeds():
        try:
            r = requests.get(feed, timeout=RSS_TIMEOUT)
            if r.status_code != 200:
                continue

            rss = feedparser.parse(r.content)

            for item in rss.entries:
                title = item.get("title", "").strip()
                link = normalize_url(item.get("link", "").strip())

                if not link or is_posted(link):
                    continue

                key = (title.lower(), link)
                if key in seen:
                    continue
                seen.add(key)

                posts.append({
                    "title": title,
                    "link": link,
                    "summary": item.get("summary", "").strip(),
                    "image": extract_image(item),
                    "published": get_post_time(item),
                })

        except Exception as e:
            print(f"RSS Error ({feed}): {e}")

    posts.sort(key=lambda x: x["published"], reverse=True)

    final = []
    per_source = {}

    for post in posts:
        domain = urlsplit(post["link"]).netloc.lower()
        if per_source.get(domain, 0) >= 2:
            continue
        per_source[domain] = per_source.get(domain, 0) + 1
        final.append(post)
        if len(final) >= MAX_POSTS_PER_RUN:
            break

    return final
