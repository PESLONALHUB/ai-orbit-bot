import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
POSTED_FILE = DATA_DIR / "posted.json"

def normalize_url(url):
    try:
        p = urlsplit(url)
        return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip("/"), "", ""))
    except Exception:
        return url

def load_posted():
    if not POSTED_FILE.exists():
        return set()
    try:
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            return {normalize_url(x) for x in json.load(f)}
    except Exception:
        return set()

def save_post(url):
    posts = load_posted()
    posts.add(normalize_url(url))
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(posts), f, indent=2)

def is_posted(url):
    return normalize_url(url) in load_posted()
