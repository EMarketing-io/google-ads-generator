import io
import re
import requests
import fitz  # PyMuPDF
import pandas as pd
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

def download_google_file_as_bytes(url, export_type=None):
    if "docs.google.com/document" in url:
        m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if not m:
            raise ValueError("Invalid Google Docs link")
        file_id = m.group(1)
        fmt = export_type if export_type else "docx"
        export_url = f"https://docs.google.com/document/d/{file_id}/export?format={fmt}"

    elif "docs.google.com/spreadsheets" in url:
        m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if not m:
            raise ValueError("Invalid Google Sheets link")
        fmt = export_type if export_type else "xlsx"
        export_url = f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format={fmt}"

    elif "drive.google.com/file" in url:
        m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if not m:
            raise ValueError("Invalid Google Drive file link")
        file_id = m.group(1)
        export_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    else:
        export_url = url

    resp = requests.get(export_url)
    if resp.status_code != 200 or "text/html" in resp.headers.get("Content-Type", ""):
        raise Exception(f"❌ Could not download file from: {url}")
    return io.BytesIO(resp.content)

# ---- existing extractors stay the same ----
def extract_text_from_docx_bytes(docx_bytes):
    docx_bytes.seek(0)
    doc = Document(docx_bytes)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(splitter.split_text("\n".join(paragraphs)))

def extract_text_from_pdf_bytes(pdf_bytes):
    pdf_bytes.seek(0)
    doc = fitz.open(stream=pdf_bytes.read(), filetype="pdf")
    return "\n\n".join(splitter.split_text("\n\n".join([page.get_text() for page in doc])))

def read_excel_sheet_from_bytes(excel_bytes, sheet_name):
    excel_bytes.seek(0)
    xls = pd.ExcelFile(excel_bytes)
    if sheet_name not in xls.sheet_names:
        raise ValueError(f"❌ Sheet '{sheet_name}' not found. Available: {xls.sheet_names}")
    return pd.read_excel(xls, sheet_name=sheet_name)

# ---- NEW: file-type sniffing and auto extraction ----
def _sniff_file_kind(data: bytes) -> str:
    head = data[:8]
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"PK"):
        return "zip"  # docx/xlsx/pptx/zip
    return "unknown"

def extract_text_auto(file_bytes: io.BytesIO) -> str:
    # normalize to raw bytes
    pos = file_bytes.tell()
    file_bytes.seek(0)
    raw = file_bytes.read()
    file_bytes.seek(pos)

    kind = _sniff_file_kind(raw)

    if kind == "pdf":
        return extract_text_from_pdf_bytes(io.BytesIO(raw))

    if kind == "zip":
        # Could be DOCX/XLSX/PPTX; we only support DOCX for text extraction here.
        try:
            return extract_text_from_docx_bytes(io.BytesIO(raw))
        except Exception as e:
            raise Exception(
                "The downloaded file is a ZIP-based format but not a DOCX "
                "(maybe XLSX/PPTX). Please provide a Google Doc/DOCX or PDF "
                "for text extraction."
            ) from e

    raise Exception(
        "Unsupported file type. Please provide a Google Doc/DOCX or PDF. "
        "If this is a Google Sheet, use it only for keywords (XLSX)."
    )
