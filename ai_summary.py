import requests

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_URL,
    OPENROUTER_MODEL,
    SUMMARY_LENGTH,
)


def generate_summary(title, summary):
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not found.")
        return summary[:SUMMARY_LENGTH]

    prompt = f"""
Summarize this AI news article in simple English.

Title:
{title}

Article:
{summary}

Rules:
- Maximum {SUMMARY_LENGTH} characters.
- Mention only the important points.
- No markdown.
- No hashtags.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/PESLONALHUB/ai-orbit-bot",
        "X-Title": "AI Orbit Bot",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
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

        print("OpenRouter Status:", response.status_code)

        if response.status_code != 200:
            print("OpenRouter Response:")
            print(response.text)
            return summary[:SUMMARY_LENGTH]

        data = response.json()

        if (
            "choices" in data
            and data["choices"]
            and "message" in data["choices"][0]
        ):
            text = data["choices"][0]["message"]["content"].strip()

            if text:
                return text[:SUMMARY_LENGTH]

        print("Unexpected OpenRouter response:", data)
        return summary[:SUMMARY_LENGTH]

    except Exception as e:
        print("OpenRouter Exception:", str(e))
        return summary[:SUMMARY_LENGTH]
