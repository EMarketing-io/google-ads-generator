import os
import time
import pandas as pd
import bcrypt
import streamlit as st
from dotenv import load_dotenv
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
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
training_url = os.getenv("TRAINING_PDF_URL")


# === Login Section ===
def check_password(username: str, password: str) -> bool:
    hashed = os.getenv(f"{username.upper()}_HASHED")
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode(), hashed.encode())


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

    /* Light mode */
    @media (prefers-color-scheme: light) {
        .login-title {
            color: #000000;
        }
        .login-subtitle {
            color: #333333;
        }
    }

    /* Dark mode */
    @media (prefers-color-scheme: dark) {
        .login-title {
            color: #ffffff;
        }
        .login-subtitle {
            color: #cccccc;
        }
    }
    </style>

    <div class="login-title">🔐 Welcome to Ad Generator Login</div>
    <div class="login-subtitle">Please enter your credentials to access the dashboard.</div>
    """,
        unsafe_allow_html=True,
    )

    # Center form using columns
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


# === Authenticate First ===
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login_ui()
    st.stop()

# === Main App ===
st.markdown(
    """
    <style>
    .app-title {
        text-align: center;
        font-size: 40px;
        font-weight: 700;
        margin-top: 20px;
    }

    /* Light mode */
    @media (prefers-color-scheme: light) {
        .app-title {
            color: #000000;
        }
    }

    /* Dark mode */
    @media (prefers-color-scheme: dark) {
        .app-title {
            color: #ffffff;
        }
    }
    </style>

    <div class="app-title">📢 Ads Generator</div>
    """,
    unsafe_allow_html=True,
)


if not api_key or not training_url:
    st.error("❌ Missing OPENAI_API_KEY or TRAINING_PDF_URL in .env")
    st.stop()

# === Setup LLM ===
llm = ChatOpenAI(
    model_name="gpt-4.1-2025-04-14",
    temperature=0.3,
    openai_api_key=api_key,
)

# === Inputs ===
st.subheader("📝 Provide Google Links")
col1, col2 = st.columns(2)
with col1:
    agent_url = st.text_input(
        "🔗 Agent Info (Google Doc)", placeholder="https://docs.google.com/document"
    )
    sheet_url = st.text_input(
        "📊 Keywords (Google Sheet)", placeholder="https://drive.google.com/file"
    )
with col2:
    offers_url = st.text_input(
        "📄 Offers (Google Drive PDF)",
        placeholder="https://docs.google.com/spreadsheets",
    )
    sheet_name = st.text_input("📑 Sheet Name", placeholder="e.g., Sheet1")

generate = st.button("🚀 Generate Ads", use_container_width=True)

if generate:
    try:
        start_total = time.time()
        st.success("✅ Inputs received. Starting processing...")

        # === Step 1: Download & Extract ===
        with st.status(
            "📥 Downloading and extracting documents...", expanded=True
        ) as status:
            training_text = extract_text_from_pdf_bytes(
                download_google_file_as_bytes(training_url)
            )
            agent_text = extract_text_from_docx_bytes(
                download_google_file_as_bytes(agent_url)
            )
            offers_text = extract_text_from_pdf_bytes(
                download_google_file_as_bytes(offers_url)
            )
            excel_bytes = download_google_file_as_bytes(sheet_url)
            df = read_excel_sheet_from_bytes(excel_bytes, sheet_name)
            keyword_groups = {
                col.strip(): df[col].dropna().astype(str).tolist()
                for col in df.columns
                if df[col].dropna().any()
            }
            st.write(f"📊 Found `{len(keyword_groups)}` keyword groups in sheet.")
            status.update(label="✅ All documents loaded.", state="complete")

        # === Step 2: Summarize ===
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
                placeholder.text(
                    f"⏳ ETA: {int(remaining)}s | Elapsed: {int(elapsed)}s"
                )
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

        st.markdown("## 🧠 Summarizing Documents")
        rules_summary = summarize_with_progress("Training", training_text)
        company_summary = summarize_with_progress("Agent Info", agent_text)
        offer_summary = summarize_with_progress("Current Offers", offers_text)

        # === Step 3: Generate Ads ===
        st.markdown("## 🛠️ Generating Ads")
        with st.spinner("Generating ads using the summarized information..."):
            ads = generate_ads(
                llm, keyword_groups, rules_summary, company_summary, offer_summary
            )
        output_df = pd.DataFrame(ads)
        output_buffer = BytesIO()
        output_df.to_excel(output_buffer, index=False)
        output_buffer.seek(0)

        # === Final Output ===
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
