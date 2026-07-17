import requests

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_URL,
    OPENROUTER_MODEL,
    SUMMARY_LENGTH,
)


def generate_summary(title, summary):
    """
    Generate an AI summary using OpenRouter.
    Falls back to the RSS summary if anything goes wrong.
    """

    if not OPENROUTER_API_KEY:
        return summary[:SUMMARY_LENGTH]

    prompt = f"""
Summarize this AI news article in simple, natural English.

Title:
{title}

Article:
{summary}

Rules:
- Keep it under {SUMMARY_LENGTH} characters.
- Mention only the important points.
- Do not use markdown.
- Do not use hashtags.
- Write 2-4 short sentences.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 180,
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if "choices" in data and data["choices"]:
            text = data["choices"][0]["message"]["content"].strip()

            if text:
                return text[:SUMMARY_LENGTH]

        return summary[:SUMMARY_LENGTH]

    except Exception as e:
        print("OpenRouter Error:", e)
        return summary[:SUMMARY_LENGTH]
