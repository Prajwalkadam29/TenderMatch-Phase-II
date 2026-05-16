"""
pdf_service.py
--------------
Extracts raw text and complex tabular data from PDF bytes.
Uses PyMuPDF (fitz) for fast text extraction and pdfplumber for high-fidelity table extraction.
Gracefully handles scanned PDFs via OCR (pytesseract) if installed.
"""

import logging
import fitz  # PyMuPDF
import io

logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pytesseract
    from PIL import Image
    # Check if tesseract is installed
    pytesseract.get_tesseract_version()
    HAS_OCR = True
except Exception:
    HAS_OCR = False
    logger.warning("pytesseract not found or not configured. OCR disabled.")


def _extract_tables_with_pdfplumber(file_bytes: bytes) -> str:
    """Extracts tables from PDF and formats them as Markdown for better LLM processing."""
    if not pdfplumber:
        return ""
    
    tables_text = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                if tables:
                    tables_text.append(f"\n--- Tables from Page {i+1} ---")
                    for table in tables:
                        for row in table:
                            # Clean up empty cells and format as a row
                            clean_row = [str(cell).replace("\n", " ").strip() if cell else "" for cell in row]
                            tables_text.append(" | ".join(clean_row))
                        tables_text.append("-" * 40)
    except Exception as e:
        logger.warning(f"Failed to extract tables with pdfplumber: {e}")
        
    return "\n".join(tables_text)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Open a PDF from raw bytes and extract all text and tables page by page.
    Combines fitz text extraction with pdfplumber table extraction,
    and falls back to OCR for scanned pages.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    pages: list[str] = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        
        # If no text found, it might be a scanned PDF. Try OCR.
        if not text.strip() and HAS_OCR:
            try:
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img)
                if text.strip():
                    text = "[OCR Extracted]\n" + text
            except Exception as e:
                logger.warning(f"OCR failed on page {page_num}: {e}")

        if text.strip():
            pages.append(f"--- Page {page_num} ---\n{text.strip()}")

    doc.close()

    if not pages:
        raise ValueError("No readable text found in the PDF. It may be a scanned image-only document, and OCR is either disabled or failed.")

    final_text = "\n\n".join(pages)
    
    # Append structured table data at the end
    tables_content = _extract_tables_with_pdfplumber(file_bytes)
    if tables_content.strip():
        final_text += "\n\n=== EXTRACTED TABULAR DATA ===\n" + tables_content

    return final_text


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
