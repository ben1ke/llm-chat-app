import base64
import fitz  # PyMuPDF
from pathlib import Path
from google import genai
from google.genai import types
from config.settings import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """PDF szöveg kinyerése PyMuPDF segítségével."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()

def encode_image_to_base64(file_bytes: bytes) -> str:
    """Képet Base64 stringgé alakít."""
    return base64.b64encode(file_bytes).decode("utf-8")

def process_uploaded_file(uploaded_file) -> dict:
    """
    Streamlit UploadedFile feldolgozása.
    Returns: {"type": "pdf"/"image", "content": str, "mime_type": str}
    """
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
        return {
            "type": "pdf",
            "content": text,
            "mime_type": "application/pdf"
        }
    elif file_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        b64 = encode_image_to_base64(file_bytes)
        mime_type = "image/png" if file_name.endswith(".png") else "image/jpeg"
        return {
            "type": "image",
            "content": b64,
            "mime_type": mime_type
        }
    else:
        return {"type": "unsupported", "content": "", "mime_type": ""}