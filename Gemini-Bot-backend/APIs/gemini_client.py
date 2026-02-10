import logging
from decouple import config

from google import genai


logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-3-flash-preview"

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client

    api_key = config("GEMINI_API_KEY", default=None)
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    # New Gemini SDK client
    _client = genai.Client(api_key=api_key)
    return _client
