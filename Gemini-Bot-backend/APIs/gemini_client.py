import os

from decouple import config
from google import genai


MODEL_NAME = "gemini-3-flash-preview"

_api_key = config("GEMINI_API_KEY", default=None)
if _api_key and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = _api_key

client = genai.Client()
