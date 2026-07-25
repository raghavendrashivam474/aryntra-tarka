"""
Abstract LLM provider interface for Aryntra Tarka.

Responsibilities:
- Define the contract all LLM providers must fulfil
- Allow future providers to be swapped without changing application code
- Expose no reasoning, prompting, or business logic
"""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    Any provider that wraps an LLM must implement this interface.
    The application layer communicates only with this contract.
    """

    @abstractmethod
    async def generate(self, prompt: str, model: str | None = None) -> str:
        """
        Send a prompt to the LLM and return the response as a string.

        Args:
            prompt: The input text to send to the model.
            model: Optional model override. Uses provider default if not given.

        Returns:
            The model response as a plain string.
        """
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """
        Check whether the LLM provider is reachable.

        Returns:
            True if reachable, False otherwise.
        """
        ...