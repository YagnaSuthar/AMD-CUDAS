"""
Embedding Service.

Generates vector embeddings using a local HuggingFace sentence-transformer
model. Supports single-text and batch embedding.
"""

import logging
from functools import lru_cache
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_embedding_model():
    """Lazy-load the HuggingFace embedding model (cached singleton)."""
    from langchain_huggingface import HuggingFaceEmbeddings

    logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


class EmbeddingService:
    """Generate vector embeddings for text content."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL

    @property
    def model(self):
        return _get_embedding_model()

    def embed_text(self, text: str) -> list[float]:
        """Return the embedding vector for a single text string."""
        return self.model.embed_query(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Return embeddings for a list of texts (batch processing).

        Parameters
        ----------
        texts : list[str]
            Texts to embed.

        Returns
        -------
        list[list[float]]
            One embedding vector per input text.
        """
        if not texts:
            return []
        vectors = self.model.embed_documents(texts)
        logger.info("Embedded batch of %d texts", len(texts))
        return vectors
