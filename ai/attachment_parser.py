import io
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AttachmentParser:
    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extracts plain text content from PDF byte stream using pypdf."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"[AttachmentParser] Error parsing PDF bytes: {e}")
            return ""

    @staticmethod
    def process_attachments(attachments: List[Dict[str, Any]]) -> str:
        """Summarizes and extracts text from attachments list."""
        if not attachments:
            return ""
            
        combined_text = []
        for att in attachments:
            filename = att.get("filename", "unknown")
            content_text = att.get("content_text", "")
            bytes_data = att.get("bytes")
            
            if not content_text and bytes_data and filename.lower().endswith(".pdf"):
                content_text = AttachmentParser.extract_text_from_pdf(bytes_data)
                
            if content_text:
                combined_text.append(f"--- CONTENIDO ADJUNTO: {filename} ---\n{content_text}")
            else:
                combined_text.append(f"--- ADJUNTO DETECTADO: {filename} ---")
                
        return "\n\n".join(combined_text)
