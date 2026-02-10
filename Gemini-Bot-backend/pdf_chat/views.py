from decouple import config
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", category=FutureWarning)
    import google.generativeai as genai

from rest_framework.decorators import api_view
from rest_framework.response import Response
import pdfplumber
import io
import logging

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    ResourceExhausted = None


# ================================
# MARKET SCOUT SYSTEM PROMPT
# ================================
MARKET_SCOUT_SYSTEM_PROMPT = """
YOU ARE A MARKET SCOUT AGENT.

TIME LOCK (STRICT):
- Current year is 2026.
- Do NOT reference events, launches, or dates from 2024 or earlier.
- Avoid hard dates; use “current cycle” or “recent period (2026)”.

IDENTITY:
- You are NOT a chatbot or assistant.
- You are a professional Market Intelligence Agent.

INTERPRETATION:
- Treat all names as companies/products.
- Never ask clarification questions.

SCOPE:
- Product updates
- Technical changes
- Market & GTM signals
- Competitive intelligence
- Business impact and risks

OUTPUT FORMAT:
Produce a structured MARKET INTELLIGENCE REPORT with:
1) Executive Summary
2) Product Updates
3) Technical Changes
4) Market / GTM Signals
5) Competitive Intelligence
6) Business Impact
7) Risks / Watchlist
"""


logger = logging.getLogger(__name__)


def _get_api_key():
    return config("GEMINI_API_KEY", default=None)


def _get_model_name():
    return config("GEMINI_TEXT_MODEL", default="models/gemini-1.5-flash")


def _is_rate_limit_error(exc):
    if ResourceExhausted and isinstance(exc, ResourceExhausted):
        return True
    msg = str(exc).lower()
    return "429" in msg or "quota" in msg or "rate limit" in msg


# ================================
# PDF CHAT ENDPOINT
# ================================
@api_view(["POST"])
def pdf_chat(request):

    # ---- API KEY CHECK ----
    api_key = _get_api_key()
    if not api_key:
        return Response(
            {"generated_text": "GEMINI_API_KEY not configured"},
            status=500
        )

    # ---- GET PROMPT ----
    prompt = request.data.get("prompt")
    if not prompt:
        prompt = "Analyze this document for recent product, technical, and market intelligence."

    # ---- GET PDF FILE ----
    pdf_file = request.FILES.get("pdf")
    if not pdf_file:
        return Response(
            {"generated_text": "No PDF uploaded"},
            status=400
        )

    # ---- READ PDF ----
    try:
        pdf_bytes = pdf_file.read()
    except Exception:
        return Response(
            {"generated_text": "Could not read uploaded PDF"},
            status=400
        )

    if not pdf_bytes:
        return Response(
            {"generated_text": "Uploaded PDF is empty"},
            status=400
        )

    # ---- EXTRACT TEXT ----
    extracted_pages = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() if page else None
                if text:
                    extracted_pages.append(text)
    except Exception:
        logger.exception("PDF parsing failed")
        return Response(
            {"generated_text": "Failed to parse PDF"},
            status=400
        )

    extracted_text = "\n\n".join(extracted_pages).strip()
    if not extracted_text:
        return Response(
            {"generated_text": "Could not extract text from PDF"},
            status=400
        )

    # ---- LIMIT CONTEXT SIZE (CRITICAL) ----
    MAX_CHARS = 20_000
    if len(extracted_text) > MAX_CHARS:
        extracted_text = extracted_text[:MAX_CHARS] + "\n\n[TRUNCATED]"

    # ---- GEMINI CALL ----
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(_get_model_name())

        user_message = f"""
{MARKET_SCOUT_SYSTEM_PROMPT}

User Request:
{prompt}

Extracted PDF Text:
{extracted_text}
"""

        response = model.generate_content(user_message)

        # ---- ROBUST RESPONSE PARSING ----
        output_text = ""

        if hasattr(response, "text") and response.text:
            output_text = response.text.strip()
        elif hasattr(response, "candidates") and response.candidates:
            try:
                output_text = response.candidates[0].content.parts[0].text.strip()
            except Exception:
                pass

        if not output_text:
            output_text = "No response generated from the PDF."

        return Response(
            {"generated_text": output_text},
            status=200
        )

    except Exception as e:
        if _is_rate_limit_error(e):
            return Response(
                {"generated_text": "Rate limit exceeded. Please try again later."},
                status=429
            )

        logger.exception("Gemini error")
        return Response(
            {"generated_text": "An error occurred while processing the PDF."},
            status=500
        )
