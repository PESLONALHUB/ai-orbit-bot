import re
import requests

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_URL,
    OPENROUTER_MODEL,
    SUMMARY_LENGTH,
)
from retry import retry_request
from log import info, warning, error

CATEGORIES = [
    "OpenAI", "Google", "Anthropic", "Meta", "Microsoft",
    "NVIDIA", "Research", "Robotics", "Coding", "Security",
    "Startup", "Hardware", "Other",
]


def _parse_response(text):
    result = {}
    current_key = None

    for line in text.strip().split("\n"):
        line = line.strip()
        lower = line.lower()
        if lower.startswith("headline:"):
            current_key = "headline"
            result[current_key] = line.split(":", 1)[1].strip()
        elif lower.startswith("summary:"):
            current_key = "summary"
            result[current_key] = line.split(":", 1)[1].strip()
        elif lower.startswith("why it matters:"):
            current_key = "why_it_matters"
            result[current_key] = line.split(":", 1)[1].strip()
        elif lower.startswith("category:"):
            current_key = "category"
            val = line.split(":", 1)[1].strip()
            result[current_key] = val if val in CATEGORIES else "Other"
        elif lower.startswith("emoji:"):
            current_key = "emoji"
            result[current_key] = line.split(":", 1)[1].strip()
        elif lower.startswith("hashtags:"):
            current_key = "hashtags_str"
            result[current_key] = line.split(":", 1)[1].strip()
        elif current_key and line:
            result[current_key] += " " + line

    required = ["headline", "summary", "why_it_matters", "category", "emoji", "hashtags_str"]
    if all(k in result and result[k] for k in required):
        summary_text = result["summary"]
        if len(summary_text) > SUMMARY_LENGTH:
            summary_text = summary_text[:SUMMARY_LENGTH].rsplit(" ", 1)[0] + "..."
        return {
            "headline": result["headline"],
            "summary": summary_text,
            "why_it_matters": result["why_it_matters"],
            "category": result["category"],
            "emoji": result["emoji"],
            "hashtags_str": result["hashtags_str"],
        }
    return None


def generate_summary(title, summary):
    if not OPENROUTER_API_KEY:
        error("OPENROUTER_API_KEY not found.")
        return None

    prompt = f"""Analyze this AI news article and return structured data.

Title: {title}
Article: {summary}

Return exactly this format:
Headline: <short engaging headline>
Summary: <60-90 word summary>
Why it matters: <one-line significance>
Category: <one from: OpenAI, Google, Anthropic, Meta, Microsoft, NVIDIA, Research, Robotics, Coding, Security, Startup, Hardware, Other>
Emoji: <single relevant emoji>
Hashtags: <3-5 relevant hashtags>

Plain text only, no markdown."""

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
        "max_tokens": 220,
    }

    try:
        response = retry_request(
            "POST", OPENROUTER_URL, max_attempts=2,
            headers=headers, json=payload, timeout=30,
        )

        info("OpenRouter status: %s", response.status_code)

        if response.status_code != 200:
            warning("OpenRouter failure (HTTP %s): %s", response.status_code, response.text)
            return None

        data = response.json()

        if (
            "choices" in data
            and data["choices"]
            and "message" in data["choices"][0]
        ):
            text = data["choices"][0]["message"]["content"].strip()

            if text:
                return _parse_response(text)

        warning("Unexpected OpenRouter response: %s", data)
        return None

    except Exception as e:
        error("OpenRouter Exception: %s", e)
        return None
