import json
import os
from config import POSTED_FILE, DATA_FOLDER

def _ensure():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    if not os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "w") as f:
            json.dump([], f)

def load_posted():
    _ensure()
    with open(POSTED_FILE, "r") as f:
        return json.load(f)

def is_posted(link):
    posts = load_posted()
    return link in posts

def save_post(link):
    posts = load_posted()

    if link not in posts:
        posts.append(link)

    with open(POSTED_FILE, "w") as f:
        json.dump(posts, f, indent=4)
