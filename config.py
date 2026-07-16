import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

# OpenRouter AI
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Files
FEEDS_FILE = "feeds.txt"

DATA_FOLDER = "data"
POSTED_FILE = f"{DATA_FOLDER}/posted.json"
LOG_FILE = f"{DATA_FOLDER}/logs.txt"

# Telegram
PARSE_MODE = "HTML"
DISABLE_WEB_PREVIEW = False

# Bot
MAX_POSTS_PER_RUN = 3
REQUEST_TIMEOUT = 20

DEFAULT_HASHTAGS = [
    "#AI",
    "#ArtificialIntelligence",
    "#ChatGPT",
    "#Tech",
    "#AITools"
]

# RSS
RSS_TIMEOUT = 15
MAX_FEEDS_PER_RUN = 150

# AI Summary
SUMMARY_LENGTH = 350
