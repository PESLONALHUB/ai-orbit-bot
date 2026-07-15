import re

from config import DEFAULT_HASHTAGS


def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def short_summary(summary, limit=350):
    summary = clean_text(summary)

    if len(summary) <= limit:
        return summary

    return summary[:limit].rsplit(" ", 1)[0] + "..."


def format_post(post):
    title = clean_text(post.get("title", "Untitled"))
    summary = short_summary(post.get("summary", "No summary available."))
    link = post.get("link", "")

    hashtags = " ".join(DEFAULT_HASHTAGS)

    message = f"""🚀 <b>AI Orbit</b>

📰 <b>{title}</b>

📝 <b>Summary</b>
{summary}

🔗 <a href="{link}">Read Full Article</a>

{hashtags}
"""

    return message.strip()
