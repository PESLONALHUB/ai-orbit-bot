import requests
from config import RSS_TIMEOUT,FEEDS_FILE,MAX_POSTS_PER_RUN
import feedparser
from database import is_posted

def load_feeds():
    with open(FEEDS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def get_latest_post():
    posts = []
    feeds = load_feeds()

    for feed in feeds:
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

                posts.append({
    "title": title,
    "link": link,
    "summary": summary
})

if len(posts) >= MAX_POSTS_PER_RUN:
    return posts

        except Exception as e:
            print(f"RSS Error: {e}")

    return posts if posts else None 
