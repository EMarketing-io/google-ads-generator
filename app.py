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
    st.markdown("""
    <style>
    .login-title {
        text-align: center;
        font-size: 32px;
        font-weight: 700;
        margin-top: 30px;
        margin-bottom: 10px;
    }

    .login-subtitle {
        text-align: center;
        font-size: 16px;
        margin-bottom: 25px;
    }

    @media (prefers-color-scheme: light) {
        .login-title { color: #000000; }
        .login-subtitle { color: #333333; }
    }
    @media (prefers-color-scheme: dark) {
        .login-title { color: #ffffff; }
        .login-subtitle { color: #cccccc; }
    }
    </style>

    <div class="login-title">🔐 Welcome to Ad Generator Login</div>
    <div class="login-subtitle">Please enter your credentials to access the dashboard.</div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("🚀 Login")

            if submitted:
                if check_password(username, password):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.success("✅ Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

# === Authenticate First ===
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login_ui()
    st.stop()

# === Main App Title ===
st.markdown("""
<style>
.app-title {
    text-align: center;
    font-size: 40px;
    font-weight: 700;
    margin-top: 20px;
}
@media (prefers-color-scheme: light) {
    .app-title { color: #000000; }
}
@media (prefers-color-scheme: dark) {
    .app-title { color: #ffffff; }
}
</style>

<div class="app-title">📢 Ads Generator</div>
""", unsafe_allow_html=True)

# === Check API ===
if not api_key:
    st.error("❌ Missing OPENAI_API_KEY in .env")
    st.stop()

# === LLM Setup ===
llm = ChatOpenAI(
    model_name="gpt-4.1-2025-04-14",
    temperature=0.3,
    openai_api_key=api_key,
)

# === Inputs ===
st.subheader("📝 Provide Google Links")
col1, col2 = st.columns(2)
with col1:
    website_url = st.text_input("🌐 Website Summary (Google Doc or PDF) [Optional]")
    questionnaire_url = st.text_input("📋 Questionnaire (Google Doc or PDF) [Optional]")
with col2:
    transcript_url = st.text_input("🎙️ Zoom Transcript (Google Doc or PDF) [Optional]")
    offers_url = st.text_input("🎁 Offers (Google Doc or PDF) [Optional]")

st.markdown("### 🛠️ Required Inputs")
keyword_url = st.text_input("📊 Keywords (Google Sheet)", placeholder="https://drive.google.com/file")
sheet_name = st.text_input("📑 Sheet Name", placeholder="e.g., Sheet1")
generate = st.button("🚀 Generate Ads", use_container_width=True)

if generate:
    try:
        start_total = time.time()
        st.success("✅ Inputs received. Starting processing...")

        if not keyword_url or not sheet_name:
            st.error("❌ Please provide both the Keywords sheet and Sheet name.")
            st.stop()

        def extract_google_file(url):
            file_bytes = download_google_file_as_bytes(url)
            if url.endswith(".pdf"):
                return extract_text_from_pdf_bytes(file_bytes)
            else:
                return extract_text_from_docx_bytes(file_bytes)

        summaries = {"website": "", "questionnaire": "", "offers": "", "transcript": ""}

        with st.status("📥 Downloading and extracting documents...", expanded=True) as status:
            if website_url:
                st.write("🌐 Summarizing Website...")
                text = extract_google_file(website_url)
                summaries["website"] = summarize_text(llm, text, "Website Summary")

            if questionnaire_url:
                st.write("📋 Summarizing Questionnaire...")
                text = extract_google_file(questionnaire_url)
                summaries["questionnaire"] = summarize_text(llm, text, "Questionnaire")

            if offers_url:
                st.write("🎁 Summarizing Offers...")
                text = extract_google_file(offers_url)
                summaries["offers"] = summarize_text(llm, text, "Offers")

            if transcript_url:
                st.write("🎙️ Summarizing Transcript...")
                text = extract_google_file(transcript_url)
                summaries["transcript"] = summarize_text(llm, text, "Zoom Transcript")

            if not any(summaries.values()):
                st.error("❌ At least one optional document must be provided.")
                st.stop()

            excel_bytes = download_google_file_as_bytes(keyword_url)
            df = read_excel_sheet_from_bytes(excel_bytes, sheet_name)
            keyword_groups = {
                col.strip(): df[col].dropna().astype(str).tolist()
                for col in df.columns
                if df[col].dropna().any()
            }
            st.write(f"📊 Found `{len(keyword_groups)}` keyword groups in sheet.")
            status.update(label="✅ All documents loaded.", state="complete")

        st.markdown("## 🛠️ Generating Ads")
        with st.spinner("Generating ads using the summarized information..."):
            ads = generate_ads(
                llm,
                keyword_groups,
                website=summaries["website"],
                questionnaire=summaries["questionnaire"],
                offers=summaries["offers"],
                transcript=summaries["transcript"]
            )

        output_df = pd.DataFrame(ads)
        output_buffer = BytesIO()
        output_df.to_excel(output_buffer, index=False)
        output_buffer.seek(0)

        st.markdown("## ✅ Output")
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
