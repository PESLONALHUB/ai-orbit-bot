import requests

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_URL,
    OPENROUTER_MODEL,
    SUMMARY_LENGTH,
)


def ai_summary(title, summary):
    if not OPENROUTER_API_KEY:
        return summary[:SUMMARY_LENGTH]

    prompt = f"""
Summarize this AI news article in simple English.

Title:
{title}

Article:
{summary}

Rules:
- Maximum {SUMMARY_LENGTH} characters.
- Keep important facts.
- No hashtags.
- No markdown.
- Easy to read.
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
        "temperature": 0.4,
        "max_tokens": 200
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

        text = data["choices"][0]["message"]["content"].strip()

        return text

    except Exception as e:
        print("AI Error:", e)
        return summary[:SUMMARY_LENGTH]
