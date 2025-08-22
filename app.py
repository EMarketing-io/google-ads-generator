# Standard Libraries
import os
import time
from io import BytesIO

# Third-Party Libraries
import pandas as pd
import bcrypt
import streamlit as st

# LangChain Libraries
from langchain.chat_models import ChatOpenAI

# Local Modules
from file_utils import (
    download_google_file_as_bytes,
    extract_text_from_pdf_bytes,
    extract_text_auto,
    extract_text_from_docx_bytes,
    read_excel_sheet_from_bytes,
)
from summarizer import summarize_text
from ad_generator import generate_ads

# Chatbot Logic
from chatbot import answer_question

# Streamlit App Configuration
st.set_page_config(page_title="Google Ads Generator", layout="wide", page_icon="📢")

# === Initialize Session State Keys (Download visibility, Chat access) ===
if "ads_ready" not in st.session_state:
    st.session_state["ads_ready"] = False

# Environment Variables
api_key = st.secrets["OPENAI_API_KEY"]
training_url = st.secrets["TRAINING_PDF_URL"]


# Authentication Function
def check_password(username: str, password: str) -> bool:
    hashed = os.getenv(f"{username.upper()}_HASHED")
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode(), hashed.encode())


# Login UI Function
def login_ui():
    st.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form", clear_on_submit=False):
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


# Initialize Session State
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login_ui()
    st.stop()

# If logged in, display the main app
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# === Sidebar Welcome & Logout ===
with st.sidebar:
    st.markdown(f"👋 **Welcome, {st.session_state.get('username', 'User')}!**")
    if st.button("🔓 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# Initialize the LLM
llm = ChatOpenAI(
    model_name="gpt-4.1-2025-04-14",
    temperature=0.3,
    openai_api_key=api_key,
)


# Function to summarize text with progress bar
def summarize_with_progress(title, text):
    st.subheader(f"🧠 Summarizing: {title}")
    placeholder = st.empty()
    bar = st.progress(0.0)
    total_start = time.time()
    chunks = text.split("\n\n")
    summaries = []
    total = len(chunks)

    for i, chunk in enumerate(chunks, 1):
        summary = llm.predict(
            f"""
You are a Google Ads strategist. Summarize this part of the document titled '{title}' into 150 words or fewer.

CONTENT:
{chunk}
"""
        )
        summaries.append(summary)
        elapsed = time.time() - total_start
        avg_time = elapsed / i
        remaining = avg_time * (total - i)
        placeholder.text(f"⏳ ETA: {int(remaining)}s | Elapsed: {int(elapsed)}s")
        bar.progress(i / total)
        time.sleep(0.5)

    final_prompt = f"""
You are a Google Ads strategist. Summarize the following summaries of the document titled '{title}' into 400 words or fewer.

CONTENT:
{"\n\n".join(summaries)}
"""
    combined = llm.predict(final_prompt)
    bar.empty()
    placeholder.empty()
    st.success(f"✅ Summary complete for: {title}")
    return combined


# Main App UI
st.subheader("📝 Provide Google Links (Google Doc or PDF) [Optional]")
col1, col2 = st.columns(2)

with col1:
    website_url = st.text_input(
        "🌐 Website Summary", placeholder="e.g., https://docs.google.com/document"
    )
    questionnaire_url = st.text_input(
        "📋 Questionnaire", placeholder="e.g., https://docs.google.com/document"
    )

with col2:
    transcript_url = st.text_input(
        "🎙️ Zoom Transcript", placeholder="e.g., https://docs.google.com/document"
    )
    offers_url = st.text_input(
        "🎁 Offers", placeholder="e.g., https://drive.google.com/file"
    )

# Required Inputs
st.markdown("### 🛠️ Required Inputs")
keyword_url = st.text_input(
    "📊 Keywords (Google Sheet)",
    placeholder="e.g., https://docs.google.com/spreadsheets",
)
sheet_name = st.text_input("📑 Sheet Name", placeholder="e.g., Sheet1")
generate = st.button("🚀 Generate Ads", use_container_width=True)

# Ad Generation Flow
if generate:
    try:
        # Reset download visibility
        st.session_state["ads_ready"] = False

        start_total = time.time()
        st.success("✅ Inputs received. Starting processing...")

        if not keyword_url or not sheet_name:
            st.error("❌ Please provide both the Keywords sheet and Sheet name.")
            st.stop()

        def extract_google_file(url: str) -> str:
            file_bytes = download_google_file_as_bytes(url)
            return extract_text_auto(file_bytes)

        summaries = {"website": "", "questionnaire": "", "offers": "", "transcript": ""}

        with st.status(
            "📥 Downloading and extracting documents...", expanded=True
        ) as status:
            st.write("📘 Summarizing Training Rules...")
            training_text = extract_text_auto(
                download_google_file_as_bytes(training_url)
            )
            rules_summary = summarize_with_progress("Training Rules", training_text)

            if website_url:
                summaries["website"] = summarize_with_progress(
                    "Website Summary", extract_google_file(website_url)
                )
            if questionnaire_url:
                summaries["questionnaire"] = summarize_with_progress(
                    "Questionnaire", extract_google_file(questionnaire_url)
                )
            if offers_url:
                summaries["offers"] = summarize_with_progress(
                    "Offers", extract_google_file(offers_url)
                )
            if transcript_url:
                summaries["transcript"] = summarize_with_progress(
                    "Zoom Transcript", extract_google_file(transcript_url)
                )

            if not any(summaries.values()):
                st.error("❌ At least one optional document must be provided.")
                st.stop()

            st.session_state["training_text"] = training_text
            st.session_state["summaries"] = summaries

            # Download and process the keywords sheet
            excel_bytes = download_google_file_as_bytes(keyword_url)
            df = read_excel_sheet_from_bytes(excel_bytes, sheet_name)

            # Keyword Groups Extraction
            keyword_groups = {
                col.strip(): df[col].dropna().astype(str).tolist()
                for col in df.columns
                if df[col].dropna().any()
            }
            st.write(f"📊 Found `{len(keyword_groups)}` keyword groups in sheet.")

            # Generate keyword summary text
            keyword_summary_text = ""
            for group, words in keyword_groups.items():
                if words:
                    keyword_summary_text += f"\n🗂️ {group}:\n- " + "\n- ".join(words)

            st.session_state["keyword_summary"] = keyword_summary_text.strip()
            status.update(label="✅ All documents loaded.", state="complete")

        st.markdown("## 🛠️ Generating Ads")
        progress_label = st.empty()
        progress_bar = st.progress(0)
        ads = []

        for idx, (label, keywords) in enumerate(keyword_groups.items()):
            progress_label.markdown(
                f"🔄 Generating ad for **{label}** (`{idx+1}/{len(keyword_groups)}`)"
            )
            ads.extend(generate_ads(llm, {label: keywords}, rules_summary, **summaries))
            progress_bar.progress((idx + 1) / len(keyword_groups))

        # Store output in session state for persistence
        output_df = pd.DataFrame(ads)
        output_buffer = BytesIO()
        output_df.to_excel(output_buffer, index=False)
        output_buffer.seek(0)
        st.session_state["output_df"] = output_df
        st.session_state["output_buffer"] = output_buffer
        st.session_state["ads_ready"] = True
        st.info(f"⏱️ Total processing time: {round(time.time() - start_total)} seconds")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# === Persistent Output Display ===
if st.session_state.get("ads_ready") and "output_buffer" in st.session_state:
    st.markdown("## ✅ Output")
    st.success("🎉 All Ads generated successfully!")
    st.download_button(
        "📥 Download Excel File",
        st.session_state["output_buffer"],
        file_name="Generated_Ads_Output.xlsx",
        use_container_width=True,
        key="download_button_cached",  # ✅ Unique key
    )


# === Sidebar for Chatbot Interaction ===
st.sidebar.markdown("## 💬 Ask the Assistant")
user_question = st.sidebar.text_input("Type your question:")
ask = st.sidebar.button("Ask", use_container_width=True)

if ask and user_question:
    if not st.session_state.get("ads_ready"):
        st.sidebar.warning("Please generate the ads first.")
    else:
        with st.sidebar:
            docs_for_chat = {
                "Website Summary": st.session_state["summaries"]["website"],
                "Questionnaire": st.session_state["summaries"]["questionnaire"],
                "Offers": st.session_state["summaries"]["offers"],
                "Zoom Transcript": st.session_state["summaries"]["transcript"],
                "Target Keywords": st.session_state.get("keyword_summary", ""),
            }
            with st.spinner("Thinking..."):
                response, source = answer_question(llm, user_question, docs_for_chat)
                st.sidebar.markdown(f"**💬 Answer:** {response}")
                st.sidebar.markdown(f"📄 *Reference:* `{source}`")
