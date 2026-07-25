import re
import time
import requests
import feedparser
from urllib.parse import urlsplit, urlunsplit

from config import RSS_TIMEOUT, FEEDS_FILE, MAX_POSTS_PER_RUN
from database import is_posted, is_duplicate_title, normalize_url
from retry import retry_request
from feed_health import should_fetch, record_success, record_failure
from log import info, warning, error

# ============================================================
# Trending Score — scoring constants
# ============================================================

# Source priority: domain -> base score
# Higher score = more authoritative/source for AI news
SOURCE_PRIORITY = {
    "openai.com": 20,
    "anthropic.com": 20,
    "deepmind.google": 20,
    "blog.google": 18,
    "research.google": 18,
    "ai.googleblog.com": 18,
    "blogs.nvidia.com": 18,
    "mistral.ai": 18,
    "huggingface.co": 15,
    "stability.ai": 15,
    "cohere.com": 15,
    "pytorch.org": 12,
    "blog.tensorflow.org": 12,
    "keras.io": 12,
    "aws.amazon.com": 12,
    "blogs.microsoft.com": 12,
    "azure.microsoft.com": 12,
    "news.mit.edu": 12,
    "venturebeat.com": 12,
    "techcrunch.com": 12,
    "theverge.com": 10,
    "replicate.com": 10,
    "modal.com": 10,
    "marktechpost.com": 8,
    "analyticsvidhya.com": 8,
    "machinelearningmastery.com": 8,
    "blog.roboflow.com": 8,
    "fast.ai": 8,
    "infoq.com": 8,
    "zdnet.com": 8,
    "infoworld.com": 8,
    "eetimes.com": 6,
    "techradar.com": 6,
}

# Keywords that signal breaking/important news -> points added per match
# These are matched case-insensitively against the article title
HIGH_PRIORITY_KEYWORDS = {
    "breaking": 8,
    "launch": 5,
    "launches": 5,
    "launched": 5,
    "release": 5,
    "releases": 5,
    "released": 5,
    "announce": 4,
    "announces": 4,
    "announced": 4,
    "gpt": 6,
    "gpt-5": 8,
    "gpt-4": 4,
    "claude": 6,
    "gemini": 6,
    "deepseek": 6,
    "openai": 5,
    "anthropic": 5,
    "google": 3,
    "meta": 3,
    "microsoft": 3,
    "nvidia": 4,
    "funding": 6,
    "acquisition": 6,
    "acquires": 6,
    "research": 3,
    "model": 2,
    "ai": 2,
}

# Breaking news keywords -> added as a separate breaking_bonus (0-20)
# These are checked against the title and contribute to final_score
BREAKING_KEYWORDS = {
    "gpt-5": 10,
    "gemini": 8,
    "claude": 8,
    "llama": 8,
    "deepseek": 8,
    "qwen": 8,
    "released": 7,
    "launches": 7,
    "launch": 5,
    "introduces": 5,
    "announces": 5,
    "breaking": 10,
    "just in": 8,
    "urgent": 8,
    "available now": 5,
    "today": 3,
    "live": 5,
}

# AI relevance keywords (scanned in title + summary for extra boost)
AI_RELEVANCE_TERMS = [
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "large language model", "llm", "natural language processing",
    "nlp", "computer vision", "transformer", "diffusion", "reinforcement learning",
    "generative ai", "foundation model", "frontier model", "reasoning",
    "multimodal", "open source", "open-source", "agi", "alignment",
    "gpu", "inference", "training", "fine-tuning", "finetuning",
]


def _domain_score(link):
    """Extract the domain from a URL and return its source priority score (0-20)."""
    try:
        domain = urlsplit(link).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        # Exact match
        if domain in SOURCE_PRIORITY:
            return SOURCE_PRIORITY[domain]
        # Subdomain match (e.g. blog.example.com -> check example.com)
        parts = domain.split(".")
        for i in range(len(parts) - 1, 0, -1):
            key = ".".join(parts[i - 1:])
            if key in SOURCE_PRIORITY:
                return SOURCE_PRIORITY[key]
    except Exception:
        pass
    return 5  # default for unknown sources


def _freshness_score(published_ts):
    """
    Score based on how recently the article was published (0-40).
    Articles within hours get maximum freshness points.
    """
    if not published_ts:
        return 0
    hours_ago = (time.time() - published_ts) / 3600
    if hours_ago < 6:
        return 40
    if hours_ago < 12:
        return 30
    if hours_ago < 24:
        return 20
    if hours_ago < 48:
        return 10
    if hours_ago < 168:  # 7 days
        return 5
    return 0


def _keyword_score(title):
    """
    Score article title for high-priority keywords (0-30).
    Breaking news, model names, and company names give the biggest boost.
    Caps at 30 to prevent title-stuffing from dominating other signals.
    """
    lower = title.lower()
    score = 0
    for keyword, points in HIGH_PRIORITY_KEYWORDS.items():
        if keyword in lower:
            score += points
    return min(score, 30)


def _length_score(summary):
    """Longer articles tend to have more substance (0-5)."""
    length = len(summary or "")
    if length > 500:
        return 5
    if length > 200:
        return 3
    if length > 50:
        return 1
    return 0


def _ai_relevance_score(title, summary):
    """
    Count AI-related terms in title and summary (0-5).
    Rewards articles deeply related to AI/ML topics.
    """
    text = (title + " " + (summary or "")).lower()
    matches = sum(1 for term in AI_RELEVANCE_TERMS if term in text)
    if matches >= 5:
        return 5
    if matches >= 3:
        return 3
    if matches >= 1:
        return 1
    return 0


def score_article(post):
    """
    Calculate a trending_score (0-100) for a single article post dict.

    Formula:
      trending_score = freshness (0-40) + source (0-20) + keywords (0-30)
                       + length (0-5) + ai_relevance (0-5)

    Higher = more likely to be interesting to an AI news audience.
    """
    freshness = _freshness_score(post.get("published"))
    source = _domain_score(post.get("link", ""))
    keywords = _keyword_score(post.get("title", ""))
    length = _length_score(post.get("summary"))
    ai_relevance = _ai_relevance_score(post.get("title", ""), post.get("summary"))

    total = freshness + source + keywords + length + ai_relevance
    return total


def _breaking_bonus(title):
    """
    Calculate a breaking news bonus (0-20) based on title keywords.

    Detects urgent/releases/model-launch keywords to surface
    time-sensitive articles above routine content.
    Uses word-boundary matching to avoid substring collisions
    (e.g. ``launch`` does not match ``launches``).
    """
    lower = title.lower()
    score = 0
    for keyword, points in BREAKING_KEYWORDS.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', lower):
            score += points
    return min(score, 20)


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


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def get_post_time(item):
    if getattr(item, "published_parsed", None):
        return time.mktime(item.published_parsed)
    if getattr(item, "updated_parsed", None):
        return time.mktime(item.updated_parsed)
    return 0


def get_latest_post():
    posts = []
    seen = set()

    for feed in load_feeds():
        if not should_fetch(feed):
            continue

        try:
            r = retry_request(
                "GET", feed, max_attempts=2,
                timeout=RSS_TIMEOUT,
            )
            if r.status_code != 200:
                record_failure(feed)
                warning("RSS fetch failed (HTTP %d): %s", r.status_code, feed)
                continue

            rss = feedparser.parse(r.content)

            for item in rss.entries:
                title = item.get("title", "").strip()
                link = normalize_url(item.get("link", "").strip())

                if not link:
                    continue

                if is_posted(link):
                    info("Duplicate skipped (URL): %s", title)
                    continue

                if is_duplicate_title(title):
                    info("Duplicate skipped (title match): %s", title)
                    continue

                key = (title.lower(), link)
                if key in seen:
                    continue
                seen.add(key)

                post = {
                    "title": title,
                    "link": link,
                    "summary": item.get("summary", "").strip(),
                    "image": extract_image(item),
                    "published": get_post_time(item),
                }

                # Attach scores for sorting
                post["trending_score"] = score_article(post)
                post["breaking_bonus"] = _breaking_bonus(post["title"])
                post["final_score"] = post["trending_score"] + post["breaking_bonus"]
                posts.append(post)

            record_success(feed)
            info("RSS fetch success: %s", feed)

        except Exception as e:
            record_failure(feed)
            error("RSS Error (%s): %s", feed, e)

    # Sort by final_score descending — breaking news surfaces to the top
    posts.sort(key=lambda x: x.get("final_score", 0), reverse=True)

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
