from urllib.parse import urlparse


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

    import re

    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def smart_summary(title, summary):
    summary = clean_text(summary)

    if not summary:
        return title

    sentences = summary.split(". ")

    result = []

    for sentence in sentences:
        sentence = sentence.strip()

        if len(sentence) < 20:
            continue

        result.append(sentence)

        if len(result) == 2:
            break

    if not result:
        return summary[:220]

    text = ". ".join(result)

    if len(text) > 220:
        text = text[:220].rsplit(" ", 1)[0] + "..."

    return text


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
    summary = smart_summary(
        title,
        post.get("summary", ""),
    )

    source = get_source(post.get("link", ""))

    caption = f"""🚀 <b>AI Orbit</b>

📰 <b>{title}</b>

✨ <b>Summary</b>
{summary}

🌐 <b>Source:</b> {source}

🔗 <a href="{post['link']}">Read Full Article</a>

{DEFAULT_HASHTAGS}
"""

    return {
        "caption": caption,
        "image": post.get("image"),
    }
