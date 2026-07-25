"""
Abstract embedding provider interface for Aryntra Tarka.

Responsibilities:
- Define the contract all embedding providers must fulfil
- Allow future providers to be swapped without changing application code
- Expose no retrieval, indexing, or vector database logic
"""

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """
    Abstract base class for all embedding providers.

    Any provider that generates embeddings must implement this interface.
    The application layer communicates only with this contract.
    """

    @abstractmethod
    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The input text to embed.
            model: Optional model override. Uses provider default if not given.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """
        Check whether the embedding provider is reachable.

        Returns:
            True if reachable, False otherwise.
        """
        ...