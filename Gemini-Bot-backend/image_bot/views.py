# from rest_framework.decorators import api_view
# import google.generativeai as genai
# from rest_framework.response import Response
# from decouple import config
# import os
# import logging

# MARKET_SCOUT_SYSTEM_PROMPT = """---
# You are a Market Scout Agent.

# Your role is to provide structured market and competitor intelligence
# for business and product teams.

# You are not a general-purpose chatbot.
# You must not ask follow-up questions or offer options.

# Analyze companies and return recent technical and product updates
# from the last 7 days in a clear, structured format.
# ---
# """

# API_KEY = config("GEMINI_API_KEY", default=None)
# # API_KEY = os.environ["GEMINI_API_KEY"]

# # Model Initialization
# _vision_model = None


# def _get_api_key():
#     return config("GEMINI_API_KEY", default=None)


# logger = logging.getLogger(__name__)

# def _get_vision_model_name():
#     return config("GEMINI_VISION_MODEL", default="models/gemini-2.5-flash")

# def _get_vision_model():
#     global _vision_model
#     if _vision_model is None:
#         api_key = _get_api_key()
#         if not api_key:
#             raise ValueError("GEMINI_API_KEY not configured")
#         genai.configure(api_key=api_key)
#         _vision_model = genai.GenerativeModel(
#             _get_vision_model_name(),
#             system_instruction=MARKET_SCOUT_SYSTEM_PROMPT,
#         )
#     return _vision_model

# @api_view(['POST'])
# def image_bot(request):
#     if request.method == 'POST':
#         try:
#             session_id = request.data.get('session_id')
#             prompt = request.data.get('prompt')
#             image = request.FILES.get('image')

#             if not prompt:
#                 prompt = "Analyze recent technical and product updates for a major technology company from the last 7 days."

#             if not image:
#                 return Response({"generated_text": "No image uploaded"}, status=400)

#             allowed_mime_types = {"image/png", "image/jpeg", "image/jpg"}
#             content_type = getattr(image, "content_type", None) or ""
#             if content_type not in allowed_mime_types:
#                 return Response({"generated_text": "Unsupported image type. Allowed: PNG, JPG, JPEG."}, status=400)

#             max_bytes = 4 * 1024 * 1024
#             size = getattr(image, "size", None)
#             if isinstance(size, int) and size > max_bytes:
#                 return Response({"generated_text": "Image too large. Max allowed size is 4MB."}, status=400)

#             image_bytes = image.read()
#             if len(image_bytes) > max_bytes:
#                 return Response({"generated_text": "Image too large. Max allowed size is 4MB."}, status=400)

#             model = _get_vision_model()
            
#             content = [
#                 prompt,
#                 {
#                     "inline_data": {
#                         "mime_type": content_type,
#                         "data": image_bytes,
#                     }
#                 },
#             ]
            
#             response = model.generate_content(content)
#             # Check if response was blocked or invalid
#             if not response.parts:
#                 logger.warning("Image analysis response blocked/empty. session_id=%s feedback=%s", session_id, getattr(response, "prompt_feedback", None))
#                 return Response({'generated_text': "The response was blocked by safety filters."}, status=200)
                
#             text = response.text

#             return Response({'generated_text': text})
#         except Exception as e:
#             logger.exception("Error in image_bot. session_id=%s", request.data.get('session_id'))
#             return Response({"generated_text": "An error occurred while processing the image."}, status=500)



from rest_framework.decorators import api_view
from rest_framework.response import Response
from decouple import config
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai
import logging

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    ResourceExhausted = None

logger = logging.getLogger(__name__)

# Allowed MIME types for multipart uploads (Django request.FILES)
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg"}
MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4MB

# -------------------------
# Market Scout System Prompt (global, strict role + time lock)
# -------------------------
MARKET_SCOUT_SYSTEM_PROMPT = """---
YOU ARE A MARKET SCOUT AGENT.

TIME LOCK (STRICT – NON-NEGOTIABLE):
- The current year is 2026.
- You are FORBIDDEN from referencing events, launches, conferences, or timelines from 2024 or earlier.
- Do NOT invent specific past dates (e.g., "May 2024", "Build 2024", "WWDC 2024").
- If real-time verification is unavailable, generate CURRENT or FORWARD-LOOKING market intelligence framed as:
  "current cycle", "recent period", or "ongoing phase (2026)".
- Any violation of this time lock is an error.

IDENTITY LOCK:
- You are NOT a chatbot. You are NOT a general AI assistant. You are NOT a consumer-facing helper.
- You are a professional Market Intelligence / Competitive Analysis Agent used by strategy, product, and leadership teams.
- Your identity MUST NEVER change.

INTERPRETATION RULES:
- Always interpret names as COMPANIES or PRODUCTS.
- Ambiguous inputs (e.g., Apple, Microsoft, Amazon, Meta) MUST be treated as corporations.
- NEVER ask clarification questions such as "company or fruit".
- NEVER ask what the user wants to know.
- Every input is a request for market intelligence.

SCOPE OF ANALYSIS:
Focus ONLY on: product and platform updates; technical or architectural changes; AI, infrastructure, and system evolution; go-to-market and positioning signals; competitive intelligence; business impact and risks.

EXCLUSIONS:
No consumer advice, tutorials, definitions, generic explanations, or historical storytelling.

RECENCY RULE:
- Reporting window defaults to "last 7 days relative to 2026".
- If information is inferred, clearly label it as: "market signal", "industry indicator", or "analyst assessment".
- Avoid absolute claims when verification is uncertain.

OUTPUT FORMAT (MANDATORY):

MARKET INTELLIGENCE REPORT: <COMPANY NAME>

1) Executive Summary
- High-level strategic snapshot of the company's current positioning.

2) Product Updates (Recent Period – 2026)
- Confirmed product or platform changes. No speculation presented as fact.

3) Technical Changes
- Architecture, silicon, AI, platform, or system-level developments.

4) Market / GTM Signals
- Positioning, pricing, partnerships, or narrative shifts.

5) Competitive Intelligence
- Direct implications versus key competitors.

6) Business Impact
- Revenue, margin, ecosystem, or strategic consequences.

7) Risks / Watchlist
- Short-term execution or regulatory risks to monitor.

SOURCE FRAMING:
- Reference insights as derived from: official announcements, developer updates, public disclosures, and industry reporting.
- Do NOT cite exact historical dates unless explicitly verified in 2026 context.

ROLE ENFORCEMENT:
- You must ALWAYS remain in Market Scout Agent mode.
- You must NEVER revert to assistant or chatbot behavior.
---
"""

# Safe default when no prompt is provided (multipart form field optional)
DEFAULT_USER_PROMPT = (
    "Analyze the image and extract any market, product, "
    "technology, or competitor-related insights visible."
)

# -------------------------
# Gemini Vision Model (stable, free-tier friendly)
# -------------------------
_vision_model = None


def _get_vision_model_name():
    # Configurable; default is widely supported and works on free-tier
    return config("GEMINI_VISION_MODEL", default="models/gemini-flash-latest")


def _get_vision_model():
    global _vision_model
    if _vision_model is None:
        api_key = config("GEMINI_API_KEY", default=None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        genai.configure(api_key=api_key)
        _vision_model = genai.GenerativeModel(
            model_name=_get_vision_model_name(),
            system_instruction=MARKET_SCOUT_SYSTEM_PROMPT,
        )
    return _vision_model


def _is_rate_limit_error(exc):
    """Detect quota/rate-limit (429) from Gemini/API layer."""
    if ResourceExhausted is not None and isinstance(exc, ResourceExhausted):
        return True
    msg = (getattr(exc, "message", None) or str(exc)).lower()
    return (
        "429" in str(getattr(exc, "code", None) or "")
        or "resource exhausted" in msg
        or "quota" in msg
        or "rate limit" in msg
    )


# -------------------------
# Image Bot API (POST, multipart/form-data; response: {"generated_text": "<string>"})
# -------------------------
@api_view(["POST"])
def image_bot(request):
    # Use request.FILES only (never request.data for the file).
    image_file = request.FILES.get("image")
    if not image_file:
        return Response({"generated_text": "No image uploaded"}, status=400)

    # Validate MIME type from uploaded file
    content_type = getattr(image_file, "content_type", None) or ""
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        return Response(
            {"generated_text": "Unsupported image type. Allowed: PNG, JPG, JPEG."},
            status=400,
        )

    # Optional prompt from form (multipart); safe default if missing
    data = getattr(request, "data", None)
    post = getattr(request, "POST", None)
    user_prompt = (
        (data.get("prompt") if hasattr(data, "get") else None)
        or (post.get("prompt") if hasattr(post, "get") else None)
        or DEFAULT_USER_PROMPT
    )

    # Size check before reading (Django sets .size for multipart)
    size = getattr(image_file, "size", None)
    if isinstance(size, int) and size > MAX_IMAGE_BYTES:
        return Response(
            {"generated_text": "Image too large. Max allowed size is 4MB."},
            status=400,
        )

    try:
        # Single read: get bytes then validate length (handles streaming uploads)
        image_file.seek(0)
        image_bytes = image_file.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            return Response(
                {"generated_text": "Image too large. Max allowed size is 4MB."},
                status=400,
            )

        model = _get_vision_model()
        # Gemini requires inline_data for raw bytes + mime_type.
        # Include BOTH prompt text and image in the SAME request.
        content = [
            user_prompt,
            {
                "inline_data": {
                    "mime_type": content_type,
                    "data": image_bytes,
                }
            },
        ]
        response = model.generate_content(content)

        # Blocked or empty response: return 200 with message (no 500)
        if not getattr(response, "parts", None) or not response.parts:
            logger.warning(
                "Image analysis response blocked or empty. prompt_feedback=%s",
                getattr(response, "prompt_feedback", None),
            )
            return Response(
                {"generated_text": "The response was blocked by safety filters."},
                status=200,
            )

        text = (getattr(response, "text", None) or "").strip()
        if not text:
            return Response(
                {"generated_text": "No response generated from image."},
                status=200,
            )

        return Response({"generated_text": text}, status=200)

    except ValueError as e:
        if "GEMINI_API_KEY" in str(e):
            return Response(
                {"generated_text": "GEMINI_API_KEY not configured"},
                status=500,
            )
        logger.exception("ValueError in image_bot: %s", e)
        return Response(
            {"generated_text": "Something went wrong while processing the image."},
            status=500,
        )
    except Exception as e:
        if _is_rate_limit_error(e):
            logger.warning("Gemini rate limit (429) in image_bot: %s", e)
            return Response(
                {"generated_text": "Rate limit exceeded. Please try again later."},
                status=429,
            )
        logger.exception("Error in image_bot: %s", e)
        return Response(
            {"generated_text": "Something went wrong while processing the image."},
            status=500,
        )
