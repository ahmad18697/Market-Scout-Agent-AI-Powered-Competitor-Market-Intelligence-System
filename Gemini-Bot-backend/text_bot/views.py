from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.sessions.backends.db import SessionStore
from rest_framework.decorators import api_view
import google.generativeai as genai
from rest_framework.response import Response
from decouple import config
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

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

# keyVaultName = os.environ["GEMINIKEY"]
# vault_url = f"https://{keyVaultName}.vault.azure.net"
# credential = DefaultAzureCredential()
# client = SecretClient(vault_url=vault_url, credential=credential)
# api_key = client.get_secret("$GEMINI_API_KEY").value

API_KEY = config("GEMINI_API_KEY", default=None)
# API_KEY = os.environ["GEMINI_API_KEY"]

_gemini_model = None


def _get_api_key():
    return config("GEMINI_API_KEY", default=None)


def _get_text_model_name():
    return config("GEMINI_TEXT_MODEL", default="models/gemini-flash-latest")


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        api_key = _get_api_key()
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel(_get_text_model_name())
    return _gemini_model

hist_dict = {}
dialogue_dict = {}

@api_view(['POST'])
def generate_text(request):
    if request.method == 'POST':
        try:
            gemini_model = _get_gemini_model()
            session_id = request.data.get('session_id')
            # Enforce Market Scout role for every request (ignore user-provided system prompts).
            system_prompt = MARKET_SCOUT_SYSTEM_PROMPT
            prompt = request.data.get('prompt')

            if session_id not in hist_dict:
                hist_dict[session_id] = []
            
            chat = gemini_model.start_chat(history=hist_dict[session_id])
            response = chat.send_message([system_prompt,
                                          prompt],
                                          stream=True)
            response.resolve()

            hist_dict[session_id] = chat.history
            
            return Response({"generated_text": response.text})
        except ValueError as e:
            print(e)
            return Response({"generated_text": str(e)}, status=500)
        except Exception as e:
            print(e)
            return Response({"generated_text": "Something went wrong. Please try again later."})
