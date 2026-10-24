from io import BytesIO
from pathlib import Path
from PIL import Image
import fitz
from docx import Document
import pytesseract

ALLOWED = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}

def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}")
    if ext == ".pdf":
        doc = fitz.open(stream=data, filetype="pdf")
        return "\n".join(page.get_text() for page in doc).strip()
    if ext == ".docx":
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    if ext in {".txt", ".md"}:
        return data.decode("utf-8-sig", errors="replace").strip()
    try:
        return pytesseract.image_to_string(Image.open(BytesIO(data))).strip()
    except Exception as exc:
        raise ValueError("Could not OCR image. Install Tesseract OCR and ensure it is on PATH.") from exc
