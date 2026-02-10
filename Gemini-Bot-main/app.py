import streamlit as st
from PIL import Image
import requests
import uuid
from decouple import config

# ==============================
# CONFIG
# ==============================
API_URL = config("API_URL")  # e.g. http://localhost:8001

st.set_page_config(
    page_title="Market Scout Agent",
    page_icon="📊",
    layout="wide"
)

# ==============================
# SESSION INIT
# ==============================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==============================
# SIDEBAR
# ==============================
st.sidebar.title("Market Scout Agent")
system_prompt = st.sidebar.text_area(
    "Additional context (optional):",
    placeholder="Optional notes for this session."
)

# ==============================
# MARKET INTELLIGENCE CHAT
# ==============================
def market_chat():
    st.markdown("## Market Intelligence Chat")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Enter your market intelligence query...")

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.messages.append(
            {"role": "user", "content": prompt}
        )

        with st.spinner("Thinking..."):
            response = requests.post(
                f"{API_URL}/chat/",
                data={
                    "session_id": st.session_state.session_id,
                    "system_prompt": system_prompt,
                    "prompt": prompt
                },
                timeout=120
            )

        result = response.json().get("generated_text", "")

        with st.chat_message("assistant"):
            st.markdown(result)

        st.session_state.messages.append(
            {"role": "assistant", "content": result}
        )

# ==============================
# VISUAL COMPETITOR ANALYSIS
# ==============================
def image_analysis():
    st.markdown("## Visual Competitor Analysis")

    uploaded_image = st.file_uploader(
        "Upload an image for analysis",
        type=["jpg", "jpeg", "png", "webp"]
    )

    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="Uploaded image", width=250)

        prompt = st.text_input(
            "Enter analysis request (optional)",
            key="image_prompt"
        )

        if st.button("Analyze Image"):
            with st.spinner("Thinking..."):
                uploaded_image.seek(0)
                files = {
                    "image": uploaded_image.read()
                }

                response = requests.post(
                    f"{API_URL}/image/",
                    data={
                        "session_id": st.session_state.session_id,
                        "system_prompt": system_prompt,
                        "prompt": prompt
                    },
                    files=files,
                    timeout=120
                )

            if response.status_code == 200:
                st.markdown(response.json().get("generated_text", ""))
            else:
                st.error(f"Error {response.status_code}")
                st.error(response.text)

# ==============================
# ANALYZE MARKET REPORTS (PDF)
# ==============================
def pdf_analysis():
    st.markdown("## Analyze Market Reports")

    uploaded_pdf = st.file_uploader(
        "Upload a market report (PDF)",
        type=["pdf"]
    )

    if uploaded_pdf:
        st.success("Report uploaded successfully.")

        prompt = st.text_input(
            "Enter your analysis request for this report",
            key="pdf_prompt"
        )

        if st.button("Analyze PDF"):
            with st.spinner("Thinking..."):
                # 🔥 CRITICAL STREAMLIT FIX
                uploaded_pdf.seek(0)
                pdf_bytes = uploaded_pdf.read()

                files = {
                    "pdf": (
                        uploaded_pdf.name,
                        pdf_bytes,
                        "application/pdf"
                    )
                }

                response = requests.post(
                    f"{API_URL}/pdf/",
                    data={
                        "session_id": st.session_state.session_id,
                        "prompt": prompt
                    },
                    files=files,
                    timeout=120
                )

            if response.status_code == 200:
                st.markdown(response.json().get("generated_text", ""))
            else:
                st.error(f"Failed to send the data. Status: {response.status_code}")
                st.error(response.text)

# ==============================
# NAVIGATION
# ==============================
PAGES = {
    "Market Intelligence Chat": market_chat,
    "Visual Competitor Analysis": image_analysis,
    "Analyze Market Reports": pdf_analysis,
}

selection = st.sidebar.radio("Navigation", list(PAGES.keys()))
PAGES[selection]()
