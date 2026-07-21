import time
import requests

from log import warning


def retry_request(method, url, max_attempts=3, **kwargs):
    """
    Make an HTTP request with retry on temporary failures.

    Retries on: timeout, connection error, HTTP 429, HTTP 500-599.
    Does NOT retry on: other HTTP 4xx (bad request, unauthorized, etc.).

    Exponential backoff:
      attempt 1 -> immediate
      attempt 2 -> 2s delay before
      attempt 3 -> 4s delay before
    """
    last_response = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.request(method, url, **kwargs)
            last_response = response

            # Retry on rate limit or server errors if attempts remain
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < max_attempts:
                    delay = 2 ** attempt
                    warning("HTTP %s on attempt %s, retrying in %ss...",
                            response.status_code, attempt, delay)
                    time.sleep(delay)
                    continue
            return response

        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt < max_attempts:
                delay = 2 ** attempt
                warning("%s on attempt %s, retrying in %ss...",
                        type(e).__name__, attempt, delay)
                time.sleep(delay)
            else:
                raise

    return last_response
