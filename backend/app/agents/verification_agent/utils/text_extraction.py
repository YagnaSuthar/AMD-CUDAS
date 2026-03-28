from __future__ import annotations

import asyncio

from fastapi import UploadFile


async def extract_text_from_certificate(*, file: UploadFile, file_bytes: bytes) -> str:
    ct = (file.content_type or "").lower()

    if "pdf" in ct or ct == "application/pdf":
        text = ""
        try:
            import fitz  # PyMuPDF

            def _read_with_pymupdf() -> str:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                parts: list[str] = []
                for page in doc:
                    t = page.get_text("text")
                    if t:
                        parts.append(t)
                return "\n\n".join(parts)

            text = await asyncio.to_thread(_read_with_pymupdf)
        except Exception:
            text = ""

        if text.strip():
            return text

        try:
            from app.services.chunking_service import ChunkingService

            return ChunkingService.extract_text_from_pdf(file_bytes)
        except Exception:
            return ""

    if "image" in ct:
        return await _ocr_image(file_bytes)

    return ""


async def _ocr_image(image_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes))
        return await asyncio.to_thread(pytesseract.image_to_string, img)
    except Exception:
        return ""
