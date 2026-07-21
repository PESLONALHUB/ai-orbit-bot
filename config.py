import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Bot
BOT_VERSION = "2.0.0"

# OpenRouter AI
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model (Claude Sonnet 5)
OPENROUTER_MODEL = "anthropic/claude-sonnet-4"

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

# Posting schedule — only post during these local time windows
# Format: (start_hour, start_minute, end_hour, end_minute)
POSTING_WINDOWS = [
    (8, 0, 10, 0),    # morning: 08:00–10:00
    (13, 0, 15, 0),   # afternoon: 13:00–15:00
    (19, 0, 22, 0),   # evening: 19:00–22:00
]
MIN_GAP_MINUTES = 5   # minimum delay between posts in the same run

# RSS
RSS_TIMEOUT = 15
MAX_FEEDS_PER_RUN = 150

# AI
SUMMARY_LENGTH = 350

# Hashtags
DEFAULT_HASHTAGS = [
    "#AI",
    "#ArtificialIntelligence",
    "#ChatGPT",
    "#Tech",
    "#AITools"
]
