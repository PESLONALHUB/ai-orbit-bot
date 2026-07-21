import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
POSTED_FILE = DATA_DIR / "posted.json"

TITLE_SIMILARITY_THRESHOLD = 0.9


def normalize_url(url):
    try:
        p = urlsplit(url)
        return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", ""))
    except Exception:
        return url


def normalize_title(title):
    """Lowercase, remove punctuation, collapse whitespace."""
    text = title.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _migrate_if_needed(entries):
    """Convert old flat-URL format to object format in-place."""
    if entries and isinstance(entries[0], str):
        return [{"url": normalize_url(u), "title": ""} for u in entries]
    return entries


_entries_cache = None


def load_entries(force_reload=False):
    """
    Load all posted entries as a list of dicts: [{"url": ..., "title": ...}, ...].
    Handles migration from the old flat-URL format automatically.
    Results are cached in memory for the lifetime of the process.
    """
    global _entries_cache
    if _entries_cache is not None and not force_reload:
        return _entries_cache
    if not POSTED_FILE.exists():
        _entries_cache = []
        return _entries_cache
    try:
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        _entries_cache = _migrate_if_needed(raw)
        return _entries_cache
    except Exception:
        _entries_cache = []
        return _entries_cache


def load_posted():
    """Return a set of normalized posted URLs (backward compatible)."""
    return {e["url"] for e in load_entries()}


def save_post(url, title=""):
    """Save a posted article. Accepts old callers that pass only url."""
    url = normalize_url(url)
    entries = load_entries()

    # Remove existing entry with same URL, then append new one
    entries = [e for e in entries if e["url"] != url]
    entries.append({"url": url, "title": normalize_title(title)})

    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    # Bump cache timestamp so subsequent reads see the new entry
    global _entries_cache
    _entries_cache = entries


def is_posted(url):
    """URL-based duplicate check (backward compatible)."""
    return normalize_url(url) in load_posted()


def is_duplicate_title(title):
    """
    Title-based duplicate check using fuzzy matching.

    Compares the normalized incoming title against all stored titles.
    Returns True if any stored title has a similarity ratio >= 0.9.
    Skips entries with empty titles (pre-migration records).
    """
    if not title:
        return False
    incoming = normalize_title(title)
    if not incoming:
        return False

    for entry in load_entries():
        stored = entry.get("title", "")
        if not stored:
            continue
        ratio = SequenceMatcher(None, incoming, stored).ratio()
        if ratio >= TITLE_SIMILARITY_THRESHOLD:
            return True

    return False
