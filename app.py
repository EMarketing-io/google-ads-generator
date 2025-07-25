import os
import time
import pandas as pd
import bcrypt
import streamlit as st
from io import BytesIO

from langchain.chat_models import ChatOpenAI
from file_utils import (
    download_google_file_as_bytes,
    extract_text_from_pdf_bytes,
    extract_text_from_docx_bytes,
    read_excel_sheet_from_bytes,
)
from summarizer import summarize_text
from ad_generator import generate_ads

# === App Config ===
st.set_page_config(page_title="Google Ads Generator", layout="wide", page_icon="📢")

# === Load environment ===
api_key = st.secrets["OPENAI_API_KEY"]


# === Login Section ===
def check_password(username: str, password: str) -> bool:
    hashed = os.getenv(f"{username.upper()}_HASHED")
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode(), hashed.encode())


def login_ui():
    st.markdown(
        """
    <div class="login-title">🔐 Welcome to Ad Generator Login</div>
    <div class="login-subtitle">Please enter your credentials to access the dashboard.</div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input(
                "🔒 Password", type="password", placeholder="Enter your password"
            )
            submitted = st.form_submit_button("🚀 Login")
            if submitted:
                if check_password(username, password):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.success("✅ Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")


if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login_ui()
    st.stop()

st.markdown("<div class='app-title'>📢 Ads Generator</div>", unsafe_allow_html=True)

if not api_key:
    st.error("❌ Missing OPENAI_API_KEY in .env")
    st.stop()

llm = ChatOpenAI(
    model_name="gpt-4.1-2025-04-14",
    temperature=0.3,
    openai_api_key=api_key,
)

# === Inputs ===
st.subheader("📥 Provide Google File Links")

with st.form("input_form"):
    col1, col2 = st.columns(2)
    with col1:
        website_url = st.text_input("🌐 Website Summary (Google Doc or PDF) [Optional]")
        questionnaire_url = st.text_input(
            "📝 Questionnaire (Google Doc or PDF) [Optional]"
        )
    with col2:
        transcript_url = st.text_input(
            "🎥 Zoom Transcript (Google Doc or PDF) [Optional]"
        )
        offers_url = st.text_input("🎁 Offers (Google Doc or PDF) [Optional]")

    st.markdown("### 🛠️ Required Inputs")
    keyword_url = st.text_input("📊 Keywords (Google Sheet) [Required]")
    sheet_name = st.text_input("📄 Sheet Name (case-sensitive) [Required]")

    submit = st.form_submit_button("🚀 Generate Ads")

if submit:
    try:
        start_total = time.time()

        if not keyword_url or not sheet_name:
            st.error("❌ Keywords and Sheet Name are required.")
            st.stop()

        # === Helper to download and extract ===
        def extract_google_file(url):
            file_bytes = download_google_file_as_bytes(url)
            if url.endswith(".pdf"):
                return extract_text_from_pdf_bytes(file_bytes)
            else:
                return extract_text_from_docx_bytes(file_bytes)

        summaries = {
            "website": "",
            "questionnaire": "",
            "offers": "",
            "transcript": "",
        }

        with st.status("📥 Downloading and summarizing documents...", expanded=True):
            if website_url:
                st.write("🌐 Summarizing Website...")
                website_text = extract_google_file(website_url)
                summaries["website"] = summarize_text(
                    llm, website_text, "Website Summary"
                )

            if questionnaire_url:
                st.write("📝 Summarizing Questionnaire...")
                questionnaire_text = extract_google_file(questionnaire_url)
                summaries["questionnaire"] = summarize_text(
                    llm, questionnaire_text, "Questionnaire"
                )

            if transcript_url:
                st.write("🎥 Summarizing Transcript...")
                transcript_text = extract_google_file(transcript_url)
                summaries["transcript"] = summarize_text(
                    llm, transcript_text, "Zoom Transcript"
                )

            if offers_url:
                st.write("🎁 Summarizing Offers...")
                offers_text = extract_google_file(offers_url)
                summaries["offers"] = summarize_text(llm, offers_text, "Offers")

            if not any(summaries.values()):
                st.error(
                    "❌ Please provide at least one document (Website, Questionnaire, Transcript, or Offers)."
                )
                st.stop()

            # === Load Keywords ===
            excel_bytes = download_google_file_as_bytes(keyword_url)
            df = read_excel_sheet_from_bytes(excel_bytes, sheet_name)
            keyword_groups = {
                col.strip(): df[col].dropna().astype(str).tolist()
                for col in df.columns
                if df[col].dropna().any()
            }

            st.write(f"✅ Found `{len(keyword_groups)}` keyword groups.")

        # === Generate Ads ===
        st.markdown("## 🛠️ Generating Ads")
        with st.spinner("Generating ads using the summarized information..."):
            ads = generate_ads(
                llm,
                keyword_groups,
                website=summaries["website"],
                questionnaire=summaries["questionnaire"],
                offers=summaries["offers"],
                transcript=summaries["transcript"],
            )

        output_df = pd.DataFrame(ads)
        output_buffer = BytesIO()
        output_df.to_excel(output_buffer, index=False)
        output_buffer.seek(0)

        # === Output Download ===
        st.success("🎉 All Ads generated successfully!")
        st.download_button(
            "📥 Download Excel File",
            output_buffer,
            file_name="Generated_Ads_Output.xlsx",
            use_container_width=True,
        )
        st.info(f"⏱️ Total processing time: {round(time.time() - start_total)} seconds")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
