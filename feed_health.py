import json
import time
from pathlib import Path

from log import info, warning

DATA_DIR = Path("data")
HEALTH_FILE = DATA_DIR / "health.json"

DEGRADED_THRESHOLD = 5
DISABLED_THRESHOLD = 10
RETRY_INTERVAL_HOURS = 24
RETRY_INTERVAL_SECONDS = RETRY_INTERVAL_HOURS * 3600


def _default_entry():
    return {
        "success_count": 0,
        "failure_count": 0,
        "consecutive_failures": 0,
        "last_success": 0.0,
        "last_failure": 0.0,
        "status": "healthy",
    }


def load_health():
    if not HEALTH_FILE.exists():
        return {}
    try:
        with open(HEALTH_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_health(health):
    HEALTH_FILE.parent.mkdir(exist_ok=True)
    with open(HEALTH_FILE, "w") as f:
        json.dump(health, f, indent=2)


def record_success(feed_url):
    health = load_health()
    entry = health.setdefault(feed_url, _default_entry())
    entry["success_count"] += 1
    entry["consecutive_failures"] = 0
    entry["last_success"] = time.time()
    entry["status"] = "healthy"
    save_health(health)
    info("Feed healthy (recovered): %s", feed_url)


def record_failure(feed_url):
    health = load_health()
    entry = health.setdefault(feed_url, _default_entry())
    entry["failure_count"] += 1
    entry["consecutive_failures"] += 1
    entry["last_failure"] = time.time()
    if entry["consecutive_failures"] >= DISABLED_THRESHOLD:
        entry["status"] = "disabled"
    elif entry["consecutive_failures"] >= DEGRADED_THRESHOLD:
        entry["status"] = "degraded"
    save_health(health)
    if entry["status"] == "disabled":
        warning("Feed disabled: %s (consecutive failures: %s)",
                feed_url, entry["consecutive_failures"])
    elif entry["status"] == "degraded":
        warning("Feed degraded: %s (consecutive failures: %s)",
                feed_url, entry["consecutive_failures"])


def should_fetch(feed_url):
    """Check whether a feed should be fetched based on its health status.

    - healthy / degraded: always fetch
    - disabled: fetch only if 24h have passed since last attempt (retry probe)
    - unknown (no entry): always fetch
    """
    health = load_health()
    entry = health.get(feed_url)
    if entry is None:
        return True

    if entry.get("status") != "disabled":
        return True

    last_failure = entry.get("last_failure", 0)
    seconds_since = time.time() - last_failure
    if seconds_since >= RETRY_INTERVAL_SECONDS:
        info("Auto-retrying disabled feed (>%sh since last attempt): %s",
             RETRY_INTERVAL_HOURS, feed_url)
        return True

    return False
