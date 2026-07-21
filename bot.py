import time
import requests

from config import (
    BOT_TOKEN,
    CHANNEL_USERNAME,
    PARSE_MODE,
    DISABLE_WEB_PREVIEW,
    REQUEST_TIMEOUT,
    MIN_GAP_MINUTES,
    MAX_POSTS_PER_RUN,
)

from log import info, warning, error
from retry import retry_request
from rss import get_latest_post
from formatter import format_post
from database import save_post
from image_utils import resolve_post_image
from admin_commands import process_pending_commands, increment_stat
from schedule import (
    is_in_window,
    is_breaking,
    queue_article,
    drain_queue,
    get_next_window_description,
)


def send_message(caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": f"@{CHANNEL_USERNAME}",
        "text": caption,
        "parse_mode": PARSE_MODE,
        "disable_web_page_preview": DISABLE_WEB_PREVIEW,
    }

    response = retry_request(
        "POST", url, max_attempts=3,
        data=payload, timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    return response.json()


def send_photo(photo_url, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    payload = {
        "chat_id": f"@{CHANNEL_USERNAME}",
        "photo": photo_url,
        "caption": caption,
        "parse_mode": PARSE_MODE,
    }

    response = retry_request(
        "POST", url, max_attempts=3,
        data=payload, timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    return response.json()


def _publish(post):
    """Send a single post (photo or text) and save it if successful.

    Returns True on success, False on failure.
    """
    resolved = resolve_post_image(post)
    if resolved:
        post["image"] = resolved

    formatted = format_post(post)
    caption = formatted.get("caption", "")
    image = formatted.get("image")

    if image:
        try:
            result = send_photo(image, caption)
        except Exception as e:
            warning("Photo send failed, falling back to text: %s", e)
            result = send_message(caption)
    else:
        result = send_message(caption)

    if result.get("ok"):
        save_post(post["link"], post["title"])
        increment_stat("posts_today")
        info("Telegram send success: %s", post["title"])
        return True

    increment_stat("telegram_failures")
    warning("Telegram send failed (not ok): %s — %s", post["title"], result)
    return False


def main():
    info("Bot started")

    # 1. Process pending admin commands before auto-posting
    process_pending_commands()

    # 2. Fetch new posts from RSS
    new_posts = get_latest_post()

    if not new_posts:
        info("No new posts found.")
    else:
        info("Fetched %d new articles from RSS.", len(new_posts))

    # 3. Separate breaking and normal
    breaking = [p for p in new_posts if is_breaking(p)]
    normal = [p for p in new_posts if not is_breaking(p)]

    posted = 0

    # 4. Publish breaking news immediately (bypasses schedule)
    for post in breaking:
        try:
            if _publish(post):
                posted += 1
        except Exception as e:
            increment_stat("telegram_failures")
            error("Breaking post error: %s", e)

    # 5. Check schedule
    if is_in_window():
        info("Inside posting window — publishing scheduled articles.")

        # Load queued articles and merge with new normal articles
        queued = drain_queue()
        if queued:
            info("Loaded %d queued articles.", len(queued))

        candidates = queued + normal

        # Sort by final_score descending — best content first
        candidates.sort(key=lambda p: p.get("final_score", 0), reverse=True)

        # Apply per-source cap (same logic as rss.py)
        filtered = []
        per_source = {}
        from urllib.parse import urlsplit
        for post in candidates:
            domain = urlsplit(post["link"]).netloc.lower()
            if per_source.get(domain, 0) >= 2:
                continue
            per_source[domain] = per_source.get(domain, 0) + 1
            filtered.append(post)
            if len(filtered) >= MAX_POSTS_PER_RUN:
                break
        candidates = filtered

        if not candidates:
            info("No articles to publish in this window.")
        else:
            info("Publishing up to %d articles.", len(candidates))

        for i, post in enumerate(candidates):
            try:
                if _publish(post):
                    posted += 1
            except Exception as e:
                increment_stat("telegram_failures")
                error("Post error: %s", e)

            # Minimum gap between posts in the same window
            if i < len(candidates) - 1 and MIN_GAP_MINUTES > 0:
                gap_seconds = MIN_GAP_MINUTES * 60
                info("Waiting %d seconds before next post...", gap_seconds)
                time.sleep(gap_seconds)

    else:
        # Outside posting window — queue normal articles for later
        if normal:
            for post in normal:
                queue_article(post)
            info("Queued %d articles for next window.", len(normal))

        next_window = get_next_window_description()
        info("Outside posting window. Next window: %s", next_window)

    # 6. Save last run time
    from admin_commands import get_all_stats, _save_stats
    stats = get_all_stats()
    stats["last_run_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_stats(stats)

    info("Bot finished. Posted %d articles this run.", posted)


if __name__ == "__main__":
    main()
