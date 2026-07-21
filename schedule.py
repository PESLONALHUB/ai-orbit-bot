"""
Smart Schedule — intelligently spreads posts across configurable windows.

- Outside a window: articles are queued, not posted.
- Inside a window: queued articles + new articles are posted (highest score first).
- Breaking news (breaking_bonus >= 15) bypasses the queue and posts immediately.
"""

import json
import time
from datetime import datetime
from pathlib import Path

from config import POSTING_WINDOWS, MIN_GAP_MINUTES
from log import info, warning

DATA_DIR = Path("data")
QUEUE_FILE = DATA_DIR / "queue.json"
MAX_QUEUED = 100

BREAKING_THRESHOLD = 15


# ── Time helpers ────────────────────────────────────────────

def _now_tuple():
    """Return current local time as (hour, minute)."""
    now = datetime.now()
    return now.hour, now.minute


def _minutes_since_midnight(h, m):
    return h * 60 + m


def is_in_window():
    """Return True if current local time falls inside any posting window."""
    now = _now_tuple()
    now_mins = _minutes_since_midnight(*now)
    for start_h, start_m, end_h, end_m in POSTING_WINDOWS:
        start = _minutes_since_midnight(start_h, start_m)
        end = _minutes_since_midnight(end_h, end_m)
        if start <= now_mins < end:
            return True
    return False


def get_next_window_description():
    """Return a human-readable string describing when the next window opens."""
    now = _now_tuple()
    now_mins = _minutes_since_midnight(*now)
    best_start = None
    best_end = None

    for start_h, start_m, end_h, end_m in POSTING_WINDOWS:
        start = _minutes_since_midnight(start_h, start_m)
        end = _minutes_since_midnight(end_h, end_m)
        if now_mins >= end:
            continue
        if best_start is None or start < best_start:
            best_start = start
            best_end = (end_h, end_m)

    if best_start is None:
        # All windows passed today; next is tomorrow's first window
        sh, sm, eh, em = POSTING_WINDOWS[0]
        return f"tomorrow {sh:02d}:{sm:02d}–{eh:02d}:{em:02d}"

    mins_until = best_start - now_mins
    hours = mins_until // 60
    mins = mins_until % 60
    eh, em = best_end
    sh = best_start // 60
    sm = best_start % 60
    if hours > 0:
        return f"in {hours}h {mins}m (next window: {sh:02d}:{sm:02d}–{eh:02d}:{em:02d})"
    return f"in {mins}m (next window: {sh:02d}:{sm:02d}–{eh:02d}:{em:02d})"


def is_breaking(post):
    """Return True if the post's breaking_bonus meets the immediate-post threshold."""
    return post.get("breaking_bonus", 0) >= BREAKING_THRESHOLD


# ── Queue management ────────────────────────────────────────

def load_queue():
    """Load queued articles from disk. Returns a list of post dicts."""
    if not QUEUE_FILE.exists():
        return []
    try:
        with open(QUEUE_FILE) as f:
            return json.load(f)
    except Exception:
        warning("Failed to load queue, starting fresh.")
        return []


def save_queue(posts):
    """Save queued articles to disk."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(posts, f, indent=2)


def queue_article(post):
    """Add an article to the queue (up to MAX_QUEUED)."""
    queue = load_queue()
    # Avoid queuing the same link twice
    if any(p.get("link") == post.get("link") for p in queue):
        return
    queue.append(post)
    if len(queue) > MAX_QUEUED:
        queue = queue[-MAX_QUEUED:]
    save_queue(queue)


def drain_queue():
    """Retrieve and clear the queue. Returns a list of post dicts."""
    posts = load_queue()
    save_queue([])
    return posts
