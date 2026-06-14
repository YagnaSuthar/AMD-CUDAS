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
    """Load the HuggingFace embedding model once and cache it (singleton)."""
    from langchain_huggingface import HuggingFaceEmbeddings

    logger.info("[RAG] Loading embedding model: %s", settings.EMBEDDING_MODEL)
    model = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info("[RAG] Embedding model loaded and cached")
    return model


def warm_up_embedding_model() -> None:
    """Eagerly initialize the embedding model at server startup.

    Call this once from the FastAPI lifespan handler so the model is
    ready in memory before the first interview request arrives.
    Subsequent calls are no-ops because ``_get_embedding_model`` is
    decorated with ``@lru_cache``.
    """
    if _get_embedding_model.cache_info().currsize > 0:
        logger.info("[RAG] Reusing embedding model (already loaded)")
    else:
        _get_embedding_model()  # triggers the actual load + cache


class EmbeddingService:
    """Generate vector embeddings for text content."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL

    @property
    def model(self):
        if _get_embedding_model.cache_info().currsize > 0:
            logger.debug("[RAG] Reusing embedding model")
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
