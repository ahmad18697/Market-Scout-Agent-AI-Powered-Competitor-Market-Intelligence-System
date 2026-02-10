import logging
import os
import time

from decouple import config
from google import genai


MODEL_NAME = "gemini-3-flash-preview"


logger = logging.getLogger(__name__)

_api_key = config("GEMINI_API_KEY", default=None)
if _api_key and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = _api_key

client = genai.Client()


def _is_transient_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "429" in msg
        or "rate limit" in msg
        or "resource exhausted" in msg
        or "quota" in msg
        or "unavailable" in msg
        or "deadline" in msg
        or "timeout" in msg
        or "tls" in msg
        or "handshake" in msg
        or "connection" in msg
    )


def generate_content(contents, *, retries: int = 2):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
            )
        except Exception as e:
            last_exc = e
            if attempt >= retries or not _is_transient_error(e):
                raise
            sleep_s = 0.8 * (2 ** attempt)
            logger.warning("Transient Gemini error; retrying in %ss (attempt %s/%s): %s", sleep_s, attempt + 1, retries + 1, e)
            time.sleep(sleep_s)
    raise last_exc
