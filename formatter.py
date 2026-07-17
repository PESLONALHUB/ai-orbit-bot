import re

from config import DEFAULT_HASHTAGS

try:
    from ai_summary import generate_summary
except ImportError:
    generate_summary = None


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
    rss_summary = short_summary(post.get("summary", "No summary available."))
    link = post.get("link", "")

    summary = rss_summary

    if generate_summary:
        try:
            ai = generate_summary(title, rss_summary)

            if ai and len(ai.strip()) > 20:
                summary = ai.strip()

        except Exception as e:
            print(f"AI Summary Error: {e}")

    hashtags = " ".join(DEFAULT_HASHTAGS)

    return f"""🚀 <b>AI Orbit</b>

📰 <b>{title}</b>

📝 <b>AI Summary</b>
{summary}

🔗 <a href="{link}">Read Full Article</a>

{hashtags}
""".strip()
