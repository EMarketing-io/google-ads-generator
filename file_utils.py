# Standard libs
import io
import re
import requests

# Third-party libs
import fitz  # PyMuPDF
import pandas as pd
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


# Initialize text splitter for processing documents
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


# Download Google file as bytes based on its URL
# file_utils.py

def download_google_file_as_bytes(url, export_type=None):
    """
    Download Google file as bytes.
    Auto-detects format from URL if export_type not provided.
    """
    # Handle Google Docs
    if "docs.google.com/document" in url:
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if not match:
            raise ValueError("Invalid Google Docs link")
        file_id = match.group(1)

        # default export type: docx unless explicitly pdf
        fmt = export_type if export_type else "docx"
        export_url = f"https://docs.google.com/document/d/{file_id}/export?format={fmt}"

    # Handle Google Sheets
    elif "docs.google.com/spreadsheets" in url:
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if not match:
            raise ValueError("Invalid Google Sheets link")
        fmt = export_type if export_type else "xlsx"
        export_url = f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format={fmt}"

    # Handle Google Drive files (auto-detect from env/pdf/docx)
    elif "drive.google.com/file" in url:
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if not match:
            raise ValueError("Invalid Google Drive file link")
        file_id = match.group(1)
        export_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    else:
        export_url = url

    response = requests.get(export_url)
    if response.status_code != 200 or "text/html" in response.headers.get("Content-Type", ""):
        raise Exception(f"❌ Could not download file from: {url}")

    return io.BytesIO(response.content)



# Extract text from DOCX bytes
def extract_text_from_docx_bytes(docx_bytes):
    docx_bytes.seek(0)
    doc = Document(docx_bytes)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(splitter.split_text("\n".join(paragraphs)))


# Extract text from PDF bytes
def extract_text_from_pdf_bytes(pdf_bytes):
    pdf_bytes.seek(0)
    doc = fitz.open(stream=pdf_bytes.read(), filetype="pdf")
    return "\n\n".join(splitter.split_text("\n\n".join([page.get_text() for page in doc])))


# Read an Excel sheet from bytes
def read_excel_sheet_from_bytes(excel_bytes, sheet_name):
    excel_bytes.seek(0)
    xls = pd.ExcelFile(excel_bytes)
    if sheet_name not in xls.sheet_names:
        raise ValueError(f"❌ Sheet '{sheet_name}' not found. Available: {xls.sheet_names}")
    return pd.read_excel(xls, sheet_name=sheet_name)