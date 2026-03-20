"""
pdf_service.py
--------------
Extracts raw text from PDF bytes using PyMuPDF (fitz).
Handles both machine-readable and (basic) scanned PDFs gracefully.
"""

import fitz  # PyMuPDF


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Open a PDF from raw bytes and extract all text page by page.
    Returns a single cleaned string with page separators.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    pages: list[str] = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            pages.append(f"--- Page {page_num} ---\n{text.strip()}")

    doc.close()

    if not pages:
        raise ValueError("No readable text found in the PDF. It may be a scanned image-only document.")

    return "\n\n".join(pages)


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Dispatcher: currently supports PDF only.
    Extend here for DOCX support later.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)

    # Graceful fallback: try to decode as plain text (TXT uploads)
    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception:
        raise ValueError(f"Unsupported file type: {filename}. Only PDF files are supported at this time.")
