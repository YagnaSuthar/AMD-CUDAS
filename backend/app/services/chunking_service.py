"""
Text Chunking Service.

Splits raw text into semantic chunks using LangChain's
RecursiveCharacterTextSplitter with configurable size and overlap.
"""

import logging
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChunkingService:
    """Splits text into overlapping semantic chunks."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_text(self, text: str) -> list[str]:
        """
        Split *text* into a list of chunk strings.

        Parameters
        ----------
        text : str
            Raw input text (plain text, extracted PDF content, etc.).

        Returns
        -------
        list[str]
            Ordered list of text chunks.
        """
        if not text or not text.strip():
            return []
        chunks = self._splitter.split_text(text)
        logger.info("Chunked text into %d segments (size=%d, overlap=%d)",
                     len(chunks), self.chunk_size, self.chunk_overlap)
        return chunks

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extract text from a PDF file given its raw bytes."""
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
        return "\n\n".join(pages)
