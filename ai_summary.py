import os
import requests

API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "anthropic/claude-sonnet-5"

URL = "https://openrouter.ai/api/v1/chat/completions"


def generate_summary(title, summary):

    if not API_KEY:
        return summary

    prompt = f"""
You are an AI news editor.

Summarize the following AI news in simple English.

Rules:
- Maximum 80 words.
- Keep important facts.
- Do not add fake information.
- Return only the summary.

Title:
{title}

Article:
{summary}
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 180
    }

    try:
        response = requests.post(
            URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("AI Error:", e)
        return summary
