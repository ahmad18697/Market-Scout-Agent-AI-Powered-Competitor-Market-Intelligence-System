from rest_framework.decorators import api_view
from rest_framework.response import Response
import logging

from google.genai import types

from APIs.gemini_client import MODEL_NAME, client

logger = logging.getLogger(__name__)

# Allowed MIME types for multipart uploads (Django request.FILES)
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
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

def _is_rate_limit_error(exc):
    """Detect quota/rate-limit (429) from Gemini/API layer."""
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
            {"generated_text": "Unsupported image type. Allowed: PNG, JPG, JPEG, WEBP."},
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

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[MARKET_SCOUT_SYSTEM_PROMPT, user_prompt, image_part],
        )

        text = (getattr(response, "text", None) or "").strip()
        if not text:
            return Response(
                {"generated_text": "No response generated from image."},
                status=200,
            )

        return Response({"generated_text": text}, status=200)

    except ValueError as e:
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
