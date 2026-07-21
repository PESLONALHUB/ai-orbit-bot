import json
import time
from pathlib import Path

import requests

from config import BOT_TOKEN, ADMIN_USER_ID, BOT_VERSION
from log import info, warning, error

DATA_DIR = Path("data")
STATS_FILE = DATA_DIR / "stats.json"
UPDATE_ID_FILE = DATA_DIR / "update_id.txt"

FEATURES = [
    "RSS aggregation (50+ feeds)",
    "AI summaries via OpenRouter",
    "Trending score ranking",
    "Breaking news priority",
    "Feed health monitoring",
    "Image resolution (RSS + og:image)",
    "Title-based duplicate detection",
    "Exponential backoff retry",
    "Telegram admin commands",
]


# ── Stats tracking ──────────────────────────────────────────

DAILY_FIELDS = {"posts_today", "duplicate_urls_skipped", "duplicate_titles_skipped"}
COUNTER_FIELDS = DAILY_FIELDS | {"retry_count", "api_failures", "telegram_failures"}


def _load_stats():
    if not STATS_FILE.exists():
        return {"date": time.strftime("%Y-%m-%d")}
    try:
        with open(STATS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"date": time.strftime("%Y-%m-%d")}


def _save_stats(data):
    DATA_DIR.mkdir(exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _ensure_date(data):
    today = time.strftime("%Y-%m-%d")
    if data.get("date") != today:
        for field in DAILY_FIELDS:
            data[field] = 0
        data["date"] = today
    return data


def increment_stat(field, amount=1):
    data = _load_stats()
    data = _ensure_date(data)
    data[field] = data.get(field, 0) + amount
    _save_stats(data)


def get_all_stats():
    data = _load_stats()
    data = _ensure_date(data)
    return data


# ── Command sending ─────────────────────────────────────────

def send_to_admin(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_USER_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        warning("Failed to send admin message: %s", e)
        return None


# ── Command handlers ────────────────────────────────────────

def cmd_status():
    from feed_health import load_health
    from database import load_entries

    health = load_health()
    total = len(health)
    healthy = sum(1 for e in health.values() if e.get("status") == "healthy")
    disabled = sum(1 for e in health.values() if e.get("status") == "disabled")
    posted = len(load_entries())
    last_run = _load_stats().get("last_run_time", "N/A")

    return (
        f"🤖 <b>AI Orbit Bot — Status</b>\n\n"
        f"Version: {BOT_VERSION}\n"
        f"Last run: {last_run}\n"
        f"Feeds: {total} total, {healthy} healthy, {disabled} disabled\n"
        f"Posted: {posted} articles"
    )


def cmd_stats():
    stats = get_all_stats()

    return (
        f"📊 <b>AI Orbit Bot — Stats</b>\n\n"
        f"Posts today: {stats.get('posts_today', 0)}\n"
        f"Duplicates (URL): {stats.get('duplicate_urls_skipped', 0)}\n"
        f"Duplicates (title): {stats.get('duplicate_titles_skipped', 0)}\n"
        f"Retries: {stats.get('retry_count', 0)}\n"
        f"API failures: {stats.get('api_failures', 0)}\n"
        f"Telegram failures: {stats.get('telegram_failures', 0)}"
    )


def cmd_health():
    from feed_health import load_health

    health = load_health()
    unhealthy = [
        (url, e["consecutive_failures"], e["status"])
        for url, e in health.items()
        if e.get("status") in ("degraded", "disabled")
    ]
    unhealthy.sort(key=lambda x: x[1], reverse=True)

    if not unhealthy:
        return "✅ All feeds are healthy."

    lines = ["⚠️ <b>Unhealthy Feeds (top 10)</b>\n"]
    for url, fails, status in unhealthy[:10]:
        lines.append(f"• <code>{url}</code>")
        lines.append(f"  {status} — {fails} consecutive failures\n")

    return "\n".join(lines).strip()


def cmd_logs():
    log_file = Path("logs") / "app.log"
    if not log_file.exists():
        return "No log file found."

    try:
        with open(log_file) as f:
            lines = f.readlines()
        last_15 = "".join(lines[-15:])
        return f"<b>Last 15 log lines:</b>\n<pre>{last_15}</pre>"
    except Exception as e:
        return f"Error reading log: {e}"


def cmd_retry():
    from feed_health import load_health, save_health

    health = load_health()
    reset = 0
    for entry in health.values():
        if entry.get("status") == "disabled":
            entry["status"] = "healthy"
            entry["consecutive_failures"] = 0
            reset += 1

    if reset:
        save_health(health)
        return f"✅ Reset {reset} disabled feed(s) to healthy."
    return "No disabled feeds to reset."


def cmd_version():
    features = "\n".join(f"• {f}" for f in FEATURES)
    return (
        f"🤖 <b>AI Orbit Bot v{BOT_VERSION}</b>\n\n"
        f"<b>Enabled features:</b>\n{features}"
    )


COMMANDS = {
    "/status": cmd_status,
    "/stats": cmd_stats,
    "/health": cmd_health,
    "/logs": cmd_logs,
    "/retry": cmd_retry,
    "/version": cmd_version,
    "/start": cmd_status,
}


# ── Polling ─────────────────────────────────────────────────

def _read_offset():
    if not UPDATE_ID_FILE.exists():
        return 0
    try:
        return int(UPDATE_ID_FILE.read_text().strip())
    except Exception:
        return 0


def _write_offset(offset):
    UPDATE_ID_FILE.write_text(str(offset))


def process_pending_commands():
    """Poll Telegram for pending admin commands and handle them.

    Call this at the very start of bot.main() before auto-posting.
    """
    if not ADMIN_USER_ID:
        return

    offset = _read_offset()

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        resp = requests.get(url, params={
            "offset": offset + 1,
            "timeout": 5,
        }, timeout=10)
        if resp.status_code != 200:
            return

        updates = resp.json().get("result", [])
        if not updates:
            return

        max_id = offset
        for update in updates:
            max_id = max(max_id, update.get("update_id", 0))
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            user_id = msg.get("from", {}).get("id")
            text = (msg.get("text") or "").strip()

            if user_id != ADMIN_USER_ID:
                continue

            cmd = text.split()[0].lower()
            handler = COMMANDS.get(cmd)
            if handler:
                reply = handler()
                send_to_admin(reply)

        _write_offset(max_id)

    except Exception as e:
        warning("Admin command poll error: %s", e)
