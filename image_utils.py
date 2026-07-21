import re
import requests

from log import info, warning

IMAGE_TIMEOUT = 5


def resolve_post_image(post):
    """Find the best validated image for a post.

    Priority:
      1. RSS media image — already extracted from the feed entry
      2. Open Graph (og:image) — fetched from the article page

    Returns a validated image URL, or None if no valid image is found.
    """
    # 1. Try RSS image first
    rss_image = post.get("image")
    if rss_image and _validate_image_url(rss_image):
        return rss_image

    # 2. Try og:image from the article page
    link = post.get("link", "")
    if link:
        og_image = _extract_og_image(link)
        if og_image and _validate_image_url(og_image):
            info("og:image resolved: %s", og_image)
            return og_image

    return None


def _extract_og_image(url):
    """Fetch the article HTML and parse the og:image meta tag."""
    try:
        resp = requests.get(
            url,
            timeout=IMAGE_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AIOrbitBot/1.0)"},
        )
        if resp.status_code != 200:
            return None

        html = resp.text

        # <meta property="og:image" content="...">
        match = re.search(
            r'<meta\s+[^>]*property=["\']og:image["\'][^>]*'
            r'content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if not match:
            # property= and content= in reverse order
            match = re.search(
                r'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*'
                r'property=["\']og:image["\']',
                html,
                re.IGNORECASE,
            )

        if match:
            og_url = match.group(1).strip()
            if og_url.startswith("/"):
                from urllib.parse import urlsplit
                parsed = urlsplit(url)
                og_url = f"{parsed.scheme}://{parsed.netloc}{og_url}"
            return og_url

    except Exception as e:
        warning("og:image extraction failed for %s: %s", url, e)

    return None


def _validate_image_url(image_url):
    """Verify that a URL points to a real image.

    Uses a lightweight HEAD request to check:
      - HTTP 200 status
      - Content-Type starts with ``image/``
      - Content-Length > 10 KB (heuristic: real article images are larger)
    """
    try:
        resp = requests.head(
            image_url,
            timeout=IMAGE_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AIOrbitBot/1.0)"},
        )

        if resp.status_code != 200:
            return False

        ct = (resp.headers.get("Content-Type") or "").lower()
        if not ct.startswith("image/"):
            return False

        cl = resp.headers.get("Content-Length")
        if cl and int(cl) < 10 * 1024:
            return False

        return True

    except Exception as e:
        warning("Image validation failed for %s: %s", image_url, e)
        return False
