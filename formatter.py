import re

from config import SUMMARY_LENGTH, DEFAULT_HASHTAGS


def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def format_post(post):
    title = clean_text(post["title"])
    summary = clean_text(post["summary"])

    if len(summary) > SUMMARY_LENGTH:
        summary = summary[:SUMMARY_LENGTH].rsplit(" ", 1)[0] + "..."

    hashtags = " ".join(DEFAULT_HASHTAGS)

    return f"""🚀 AI Orbit

📰 {title}

📝 Summary
{summary}

🔗 Read More
{post['link']}

{hashtags}
"""
