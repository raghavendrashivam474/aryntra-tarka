"""
Ollama embedding provider for Aryntra Tarka.

Responsibilities:
- Implement the BaseEmbeddingProvider interface
- Communicate with the Ollama embeddings API
- Expose no retrieval, indexing, or vector database logic
"""

import ollama

from backend.providers.embeddings.base import BaseEmbeddingProvider
from backend.config.settings import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """
    Embedding provider backed by a local Ollama instance.
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.ollama_default_embedding_model
        self.client = ollama.AsyncClient(host=settings.ollama_base_url)
        logger.info("OllamaEmbeddingProvider initialised. Model: %s", self.model)

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """
        Generate an embedding vector for the given text using Ollama.

        Args:
            text: The input text to embed.
            model: Optional model override.

        Returns:
            A list of floats representing the embedding vector.
        """
        target_model = model or self.model
        logger.debug("Generating embedding. Model: %s", target_model)

        response = await self.client.embeddings(
            model=target_model,
            prompt=text,
        )

        return response.embedding

    async def ping(self) -> bool:
        """
        Check whether Ollama is reachable by listing available models.

        Returns:
            True if reachable, False otherwise.
        """
        try:
            await self.client.list()
            logger.debug("Ollama embedding ping successful.")
            return True
        except Exception as exc:
            logger.warning("Ollama embedding ping failed: %s", exc)
            return False