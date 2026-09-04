"""
Document Extractor — plain-text extraction for supplementary reference files.

PDF only for now. Kept as its own small module (matching this project's
one-concern-per-file style — tts_engine.py, spaced_repetition.py, etc.) so a
different format can be added later without touching callers.
"""

import io

MIN_EXTRACTED_CHARS = 20


def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from a PDF's pages, concatenated with blank lines
    between pages. Raises ValueError if nothing usable comes out (e.g. a
    scanned/image-only PDF with no text layer) so the caller can surface a
    real error instead of storing a useless empty entry."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except PdfReadError as e:
        raise ValueError(f"Could not read this PDF: {e}")

    pages = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(text)

    combined = "\n\n".join(pages).strip()
    if len(combined) < MIN_EXTRACTED_CHARS:
        raise ValueError(
            "Couldn't find readable text in this PDF — it may be a scanned "
            "image with no text layer. Image/OCR support isn't available yet."
        )
    return combined
