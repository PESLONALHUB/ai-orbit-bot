from config import DEFAULT_HASHTAGS

def clean_text(text):
    if not text:
        return ""

    text = text.replace("<p>", "")
    text = text.replace("</p>", "")
    text = text.replace("<br>", "")
    text = text.replace("<br/>", "")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")

    return text.strip()


def short_summary(summary, limit=350):
    summary = clean_text(summary)

    if len(summary) <= limit:
        return summary

    return summary[:limit] + "..."


def format_post(post):

    title = clean_text(post["title"])

    summary = short_summary(post["summary"])

    link = post["link"]

    hashtags = " ".join(DEFAULT_HASHTAGS)

    message = f"""
🚀 <b>AI Orbit</b>

📰 <b>{title}</b>

📖 {summary}

🔗 <a href="{link}">Read Full Article</a>

{hashtags}
"""

    return message.strip()
