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


def extract_google_file(url):
    file_bytes = download_google_file_as_bytes(url)
    if url.endswith(".pdf"):
        return extract_text_from_pdf_bytes(file_bytes)
    else:
        return extract_text_from_docx_bytes(file_bytes)


def main():
    start_total = time.time()

    # === Load environment variables ===
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    training_url = os.getenv("TRAINING_PDF_URL")

    if not api_key:
        raise ValueError("❌ Missing OPENAI_API_KEY in .env")

    llm = ChatOpenAI(
        model_name="gpt-4.1-2025-04-14",
        temperature=0.3,
        openai_api_key=api_key,
    )

    # === Prompt for inputs ===
    print("📥 Paste your file links below")

    website_url = input("🌐 Website Summary (Google Doc or PDF) [Optional]: ").strip()
    questionnaire_url = input(
        "📝 Questionnaire (Google Doc or PDF) [Optional]: "
    ).strip()
    transcript_url = input(
        "🎥 Zoom Transcript (Google Doc or PDF) [Optional]: "
    ).strip()
    offers_url = input("🎁 Offers (Google Doc or PDF) [Optional]: ").strip()

    excel_url = input("📊 Keywords (Google Sheet) [Required]: ").strip()
    sheet_name = input("📄 Sheet Name (case-sensitive): ").strip()

    if not excel_url or not sheet_name:
        raise ValueError("❌ Keywords Sheet and Sheet Name are required.")

    # === Download and summarize optional documents ===
    print("\n📄 Extracting and summarizing text...")

    summaries = []

    if website_url:
        print("\n🧠 Summarizing: Website Summary")
        website_text = extract_google_file(website_url)
        summaries.append(summarize_text(llm, website_text, "Website Summary"))

    if questionnaire_url:
        print("\n🧠 Summarizing: Questionnaire")
        questionnaire_text = extract_google_file(questionnaire_url)
        summaries.append(summarize_text(llm, questionnaire_text, "Questionnaire"))

    if transcript_url:
        print("\n🧠 Summarizing: Zoom Transcript")
        transcript_text = extract_google_file(transcript_url)
        summaries.append(summarize_text(llm, transcript_text, "Zoom Transcript"))

    if offers_url:
        print("\n🧠 Summarizing: Offers")
        offers_text = extract_google_file(offers_url)
        summaries.append(summarize_text(llm, offers_text, "Offers"))

    if not summaries:
        raise ValueError(
            "❌ Please provide at least one document (Website, Questionnaire, Transcript, or Offers)."
        )

    combined_summary = "\n\n".join(summaries)

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
    ads = generate_ads(llm, keyword_groups, combined_summary)

    # === Export to Excel ===
    output_path = "Generated_Ads_Output_Final.xlsx"
    pd.DataFrame(ads).to_excel(output_path, index=False)
    print(f"\n✅ Ads saved to: {output_path}")
    print(f"⏱️ Total time: {round(time.time() - start_total, 2)} seconds")


if __name__ == "__main__":
    main()
