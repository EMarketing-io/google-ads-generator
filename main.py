import os
import time
import pandas as pd
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from file_utils import (
    download_google_file_as_bytes,
    extract_text_from_pdf_bytes,
    extract_text_from_docx_bytes,
    read_excel_sheet_from_bytes,
)
from summarizer import summarize_text
from ad_generator import generate_ads


def main():
    start_total = time.time()

    # === Load environment variables ===
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    training_url = os.getenv("TRAINING_PDF_URL")
    if not api_key or not training_url:
        raise ValueError("❌ Missing OPENAI_API_KEY or TRAINING_PDF_URL in .env")

    llm = ChatOpenAI(
        model_name="gpt-4.1-2025-04-14",
        temperature=0.3,
        openai_api_key=api_key,
    )

    # === Prompt for links ===
    print("📥 Paste Google file links below")
    agent_url = input("🔗 Agent Info (Google Doc): ").strip()
    offers_url = input("🔗 Offers PDF (Google Drive): ").strip()
    excel_url = input("🔗 Keywords (Google Sheet): ").strip()
    sheet_name = input("📄 Enter Sheet Name (case sensitive): ").strip()

    # === Download and extract content ===
    print("\n📄 Extracting and processing text...")

    training_text = extract_text_from_pdf_bytes(
        download_google_file_as_bytes(training_url)
    )

    agent_text = extract_text_from_docx_bytes(
        download_google_file_as_bytes(agent_url, export_type="docx")
    )

    offers_text = extract_text_from_pdf_bytes(download_google_file_as_bytes(offers_url))

    # === Summarize ===
    print("\n🧠 Summarizing documents...")
    rules_summary = summarize_text(llm, training_text, "Training")
    company_summary = summarize_text(llm, agent_text, "Agent Info")
    offer_summary = summarize_text(llm, offers_text, "Current Offers")

    # === Load keyword groups from Excel ===
    print("\n📊 Reading keyword groups from Excel sheet...")
    excel_bytes = download_google_file_as_bytes(excel_url)
    df = read_excel_sheet_from_bytes(excel_bytes, sheet_name)
    keyword_groups = {
        col.strip(): df[col].dropna().astype(str).tolist()
        for col in df.columns
        if df[col].dropna().any()
    }

    print(f"✅ Loaded {len(keyword_groups)} keyword groups.")

    # === Generate Ads ===
    print("⚙️ Generating ads...")
    ads = generate_ads(
        llm, keyword_groups, rules_summary, company_summary, offer_summary
    )

    # === Export to Excel ===
    output_path = "Generated_Ads_Output_Final.xlsx"
    pd.DataFrame(ads).to_excel(output_path, index=False)
    print(f"\n✅ Ads saved to: {output_path}")
    print(f"⏱️ Total time: {round(time.time() - start_total, 2)} seconds")


if __name__ == "__main__":
    main()
