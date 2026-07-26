"""
Abstract LLM provider interface for Aryntra Tarka.

Responsibilities:
- Define the contract all LLM providers must fulfil
- Allow future providers to be swapped without changing application code
- Expose no reasoning, prompting, or business logic

Sprint 3.8 - generate_stream() added as a concrete default that raises
             NotImplementedError. Providers that support streaming should
             override it. This keeps existing non-streaming providers and
             all test mocks working without modification.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    Any provider that wraps an LLM must implement generate() and ping().
    Streaming support is optional. Providers that support streaming
    override generate_stream().
    """

    @abstractmethod
    async def generate(self, prompt: str, model: str | None = None) -> str:
        """
        Send a prompt to the LLM and return the response as a string.
        """
        ...

    async def generate_stream(
        self,
        prompt: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Send a prompt to the LLM and stream the response token by token.

        Default implementation raises NotImplementedError. Providers that
        support streaming override this method.

        Yields:
            String chunks as they arrive from the provider.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support streaming. "
            "Override generate_stream() to enable streaming support."
        )
        # The yield below is unreachable but required so Python treats
        # this method as an async generator matching the return type.
        yield ""  # pragma: no cover

    @abstractmethod
    async def ping(self) -> bool:
        """
        Check whether the LLM provider is reachable.
        """
        ...