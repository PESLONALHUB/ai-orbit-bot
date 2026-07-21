"""
AI Orbit Bot — Web Dashboard (Flask)

Reads existing data files to display status, feeds, queue, logs, and stats.
Provides actions: run bot, retry feeds, clear queue, export logs.
"""

import json
import threading
import time as time_module
from pathlib import Path
from urllib.parse import urlsplit

import flask

from config import BOT_VERSION
from log import info

_bot_lock = threading.Lock()

# ── Flask app ────────────────────────────────────────────────

app = flask.Flask(__name__)
app.secret_key = "ai-orbit-dashboard"

BOT_RUNNING = False

# ── Data readers ─────────────────────────────────────────────

DATA_DIR = Path("data")
HEALTH_FILE = DATA_DIR / "health.json"
QUEUE_FILE = DATA_DIR / "queue.json"
STATS_FILE = DATA_DIR / "stats.json"
POSTED_FILE = DATA_DIR / "posted.json"
LOG_FILE = Path("logs") / "app.log"
FEEDS_FILE = Path("feeds.txt")


def _read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _read_lines(path, n=100):
    if not path.exists():
        return "(no file)"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return "(read error)"


def _fmt_ts(ts):
    if not ts:
        return "—"
    return time_module.strftime("%Y-%m-%d %H:%M", time_module.localtime(ts))


# ── Routes ───────────────────────────────────────────────────

@app.route("/")
def home():
    global BOT_RUNNING

    health = _read_json(HEALTH_FILE) or {}
    queue = _read_json(QUEUE_FILE) or []
    stats = _read_json(STATS_FILE) or {}
    posted = _read_json(POSTED_FILE)
    feeds_list = _read_lines(FEEDS_FILE).splitlines() if FEEDS_FILE.exists() else []

    total_feeds = len(health) if health else len(feeds_list)
    healthy = sum(1 for e in health.values() if e.get("status") == "healthy")
    disabled = sum(1 for e in health.values() if e.get("status") == "disabled")
    total_posted = len(posted) if isinstance(posted, list) else 0

    return flask.render_template(
        "index.html",
        status="Running" if BOT_RUNNING else "Idle",
        version=BOT_VERSION,
        last_run=stats.get("last_run_time", "—"),
        queue_size=len(queue),
        total_feeds=total_feeds,
        healthy_feeds=healthy,
        disabled_feeds=disabled,
        total_posted=total_posted,
    )


@app.route("/feeds")
def feeds():
    health = _read_json(HEALTH_FILE) or {}
    feeds_list = _read_lines(FEEDS_FILE).splitlines() if FEEDS_FILE.exists() else []

    rows = []
    for url in feeds_list:
        e = health.get(url, {})
        rows.append({
            "url": url,
            "status": e.get("status", "unknown"),
            "consecutive": e.get("consecutive_failures", 0),
            "last_success": _fmt_ts(e.get("last_success")),
            "last_failure": _fmt_ts(e.get("last_failure")),
        })

    return flask.render_template("feeds.html", feeds=rows)


@app.route("/queue")
def queue():
    articles = _read_json(QUEUE_FILE) or []

    for a in articles:
        link = a.get("link", "")
        try:
            domain = urlsplit(link).netloc.lower()
            a["source"] = domain[4:] if domain.startswith("www.") else domain
        except Exception:
            a["source"] = "?"
        a["published"] = _fmt_ts(a.get("published"))

    articles.reverse()  # newest first

    return flask.render_template("queue.html", articles=articles)


@app.route("/logs")
def logs():
    return flask.render_template("logs.html", logs=_read_lines(LOG_FILE, 100))


@app.route("/stats")
def stats():
    s = _read_json(STATS_FILE) or {}
    health = _read_json(HEALTH_FILE) or {}

    rss_failures = sum(e.get("failure_count", 0) for e in health.values())

    return flask.render_template("stats.html", stats={
        "posts_today": s.get("posts_today", 0),
        "duplicate_urls_skipped": s.get("duplicate_urls_skipped", 0),
        "duplicate_titles_skipped": s.get("duplicate_titles_skipped", 0),
        "api_failures": s.get("api_failures", 0),
        "telegram_failures": s.get("telegram_failures", 0),
        "rss_failures": rss_failures,
        "retry_count": s.get("retry_count", 0),
    })


# ── Actions ──────────────────────────────────────────────────

@app.route("/run", methods=["POST"])
def run_bot():
    global BOT_RUNNING
    with _bot_lock:
        if BOT_RUNNING:
            flask.flash("Bot is already running.", "warning")
            return flask.redirect("/")
        BOT_RUNNING = True

    def _task():
        global BOT_RUNNING
        try:
            info("Dashboard: manual bot run triggered.")
            import bot
            bot.main()
        except Exception as e:
            info("Dashboard: manual run error: %s", e)
        finally:
            with _bot_lock:
                BOT_RUNNING = False

    threading.Thread(target=_task, daemon=True).start()
    flask.flash("Bot run started.", "success")
    return flask.redirect("/")


@app.route("/retry-feeds", methods=["POST"])
def retry_feeds():
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
        flask.flash(f"Reset {reset} disabled feed(s) to healthy.", "success")
    else:
        flask.flash("No disabled feeds to reset.", "info")

    return flask.redirect("/")


@app.route("/clear-queue", methods=["POST"])
def clear_queue():
    QUEUE_FILE.write_text("[]")
    flask.flash("Queue cleared.", "success")
    return flask.redirect("/queue")


@app.route("/export-logs")
def export_logs():
    if not LOG_FILE.exists():
        flask.flash("No log file found.", "warning")
        return flask.redirect("/logs")

    return flask.send_file(
        LOG_FILE,
        mimetype="text/plain",
        as_attachment=True,
        download_name="ai-orbit-bot.log",
    )


# ── Entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    print(f"AI Orbit Dashboard — http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
