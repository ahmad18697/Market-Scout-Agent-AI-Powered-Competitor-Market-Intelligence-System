# Market Scout Agent

Market Scout Agent is a market, product, and competitor intelligence application built for the **Market Scout Agent** use case (Virtusa Jatayu Season 5). It delivers structured, analyst-style market intelligence using a Streamlit frontend, a Django REST Framework backend, and Google Gemini multimodal models (text, image, PDF).

## Source Policy (Judge-Ready)

This build does **not** enable live web browsing or real-time search APIs.

As a result:

- **The agent does not provide exact article links** in its output.
- This is an intentional, professional design choice to **avoid fabricated URLs** and unverifiable citations.
- The backend demonstrates a judge-visible, agentic pipeline (planning → source collection → date verification → synthesis) using **representative source categories** such as:
  - public disclosures
  - developer updates
  - industry reporting

This approach keeps the system **enterprise-safe** and audit-friendly in a hackathon setting: it is explicit about what is and is not verified.

### Extensibility

If live browsing or fresh-data RAG is required later, it can be integrated by swapping the “Browser Agent” implementation (e.g., a search API + HTML fetch + date extraction) **without changing the overall agent architecture**.

## Key Features

### 1) Market Intelligence Chat

- Text-based market and competitor intelligence
- Structured, analyst-style reporting (not a casual chatbot)
- Intended for strategy, product, and leadership workflows

### 2) Visual Competitor Analysis (Image)

- Upload images:
  - `JPG` / `JPEG`
  - `PNG`
  - `WEBP`
- Extracts signals from product screenshots, branding, UI/UX, and positioning cues
- Uses Gemini multimodal reasoning for image understanding

### 3) Analyze Market Reports (PDF)

- Upload PDF market and research reports
- Generates structured analysis and answers grounded in document context
- Sends the raw PDF bytes directly to Gemini for multimodal document understanding (no manual text extraction)

## Architecture

- **Streamlit frontend** collects prompts and uploads, then calls backend REST endpoints.
- **Django REST Framework backend** exposes endpoints for:
  - Text chat intelligence
  - Image-based competitor analysis
  - PDF-based report analysis
- **Google Gemini** provides multimodal reasoning and report generation.
- The backend is structured to support agentic workflows and can later be extended with live browsing or RAG without changing endpoint contracts.

## Project Structure

```text
Bot_Ai/
├── Gemini-Bot-backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── APIs/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── gemini_client.py
│   ├── text_bot/
│   │   ├── urls.py
│   │   └── views.py
│   ├── image_bot/
│   │   ├── urls.py
│   │   └── views.py
│   └── pdf_chat/
│       ├── urls.py
│       └── views.py
│
└── Gemini-Bot-main/
    ├── app.py
    ├── requirements.txt
    └── .env
```

## Prerequisites

- Python 3.10+
- A Google Gemini API key (Google AI Studio)

## Environment Variables

### Backend (`Gemini-Bot-backend/.env`)

Required:

```env
GEMINI_API_KEY=your_api_key_here
```

Optional (if supported by your deployment/config):

```env
# GEMINI_TEXT_MODEL=gemini-3-flash-preview
# GEMINI_VISION_MODEL=gemini-3-flash-preview
```

### Frontend (`Gemini-Bot-main/.env`)

Required:

```env
API_URL=http://localhost:8001
```

## Setup Instructions

### 1) Backend Setup (Django REST)

Create and activate a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r Gemini-Bot-backend/requirements.txt
```

Create `Gemini-Bot-backend/.env` and set `GEMINI_API_KEY`.

Run migrations:

```bash
python3 Gemini-Bot-backend/manage.py migrate
```

Run the backend on port **8001**:

```bash
python3 Gemini-Bot-backend/manage.py runserver 0.0.0.0:8001
```

### 2) Frontend Setup (Streamlit)

Create and activate a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r Gemini-Bot-main/requirements.txt
```

Create `Gemini-Bot-main/.env` and set `API_URL=http://localhost:8001`.

Run Streamlit on port **8501**:

```bash
streamlit run Gemini-Bot-main/app.py --server.port 8501
```

Open:

```text
http://localhost:8501
```

## Usage

### Market Intelligence Chat

1. Open the Streamlit app.
2. Select **Market Intelligence Chat**.
3. Enter a company/product name or intelligence query.
4. Submit to receive a structured market intelligence report.

### Visual Competitor Analysis (Image)

1. Select **Visual Competitor Analysis**.
2. Upload an image (`jpg`, `jpeg`, `png`, `webp`).
3. Optionally add a prompt (e.g., positioning, UI, messaging).
4. Submit to receive structured insights derived from the image.

### Analyze Market Reports (PDF)

1. Select **Analyze Market Reports**.
2. Upload a `.pdf` report.
3. Provide an analysis request.
4. Submit to receive a structured analysis grounded in the document.

## API Endpoints (Backend)

- `POST /chat/`
- `POST /image/`
- `POST /pdf/`

All endpoints return JSON:

```json
{ "generated_text": "..." }
```

## Troubleshooting

### API quota / rate limit

Symptoms:

- HTTP `429`
- Errors containing: `quota`, `rate limit`, `resource exhausted`

Actions:

- Wait and retry
- Verify your API key quota in Google AI Studio

### Model not found / access issues

Symptoms:

- HTTP `400`/`500` mentioning model availability

Actions:

- Confirm the configured model is accessible to your API key

### Image upload rejected

Symptoms:

- HTTP `400` “Unsupported image type”

Actions:

- Ensure the upload is `jpg/jpeg/png/webp`
- Ensure multipart upload includes filename + bytes + correct MIME type
- Keep uploads within backend size limits

## Tech Stack

- Python
- Django
- Django REST Framework
- Streamlit
- Google Gemini API
- (Optional future) Search API / RAG layer (not enabled in this build)
