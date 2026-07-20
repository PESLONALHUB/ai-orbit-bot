from urllib.parse import urlparse
import re
from ai_summary import generate_summary

DEFAULT_HASHTAGS = "#AI #ArtificialIntelligence #ChatGPT #TechNews"


def clean_text(text):
    if not text:
        return ""

    text = (
        text.replace("<p>", "")
        .replace("</p>", "\n")
        .replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<br />", "\n")
    )

    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def smart_summary(title, summary):
    summary = clean_text(summary)

    if not summary:
        return title

    bad_phrases = [
        "read more",
        "continue reading",
        "continue",
        "advertisement",
        "subscribe",
        "sign up",
        "newsletter",
        "privacy policy",
        "cookie",
        "all rights reserved",
        "copyright",
    ]

    sentences = []

    for sentence in summary.replace("\n", " ").split("."):
        sentence = sentence.strip()

        if len(sentence) < 30:
            continue

        lower = sentence.lower()

        if any(word in lower for word in bad_phrases):
            continue

        sentences.append(sentence)

    if not sentences:
        return title

    result = ". ".join(sentences[:2]).strip()

    if len(result) > 240:
        result = result[:240].rsplit(" ", 1)[0] + "..."

    if not result.endswith("."):
        result += "."

    return result


def get_source(link):
    try:
        domain = urlparse(link).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    except Exception:
        return "Unknown"


def format_post(post):
    title = clean_text(post.get("title", ""))
    raw_summary = post.get("summary", "")

    # Try AI summary first
    summary = generate_summary(title, raw_summary)

    # Fallback to smart summary if AI fails
    if not summary:
        summary = smart_summary(title, raw_summary)

    source = get_source(post.get("link", ""))

    caption = f"""🚀 <b>AI Orbit</b>

📰 <b>{title}</b>

🧠 <b>Quick Summary</b>
{summary}

🌐 <b>Source:</b> {source}

🔗 <a href="{post['link']}">Read Full Article →</a>

{DEFAULT_HASHTAGS}
"""

    return {
        "caption": caption,
        "image": post.get("image"),
    }
