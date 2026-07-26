"""
Ollama LLM provider for Aryntra Tarka.

Responsibilities:
- Implement the BaseLLMProvider interface
- Communicate with the Ollama API
- Expose no reasoning or business logic

Sprint 3.8 - generate_stream() implemented using ollama stream=True.
"""

from typing import AsyncIterator

import ollama

from backend.providers.llm.base import BaseLLMProvider
from backend.config.settings import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaLLMProvider(BaseLLMProvider):
    """
    LLM provider backed by a local Ollama instance.
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.ollama_default_model
        self.client = ollama.AsyncClient(host=settings.ollama_base_url)
        logger.info("OllamaLLMProvider initialised. Model: %s", self.model)

    async def generate(self, prompt: str, model: str | None = None) -> str:
        """
        Send a prompt to Ollama and return the complete text response.

        Args:
            prompt: The input text to send to the model.
            model:  Optional model override.

        Returns:
            The model response as a plain string.
        """
        target_model = model or self.model
        logger.debug("Generating response. Model: %s", target_model)

        response = await self.client.generate(
            model=target_model,
            prompt=prompt,
        )

        return response.response

    async def generate_stream(
        self,
        prompt: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Send a prompt to Ollama and stream response chunks as they arrive.

        Uses the Ollama stream=True parameter which causes the client
        to yield partial response objects. Each object carries a
        response field containing the latest token or token group.

        Args:
            prompt: The input text to send to the model.
            model:  Optional model override.

        Yields:
            String chunks as they arrive from Ollama.
        """
        target_model = model or self.model
        logger.debug("Streaming response. Model: %s", target_model)

        stream = await self.client.generate(
            model=target_model,
            prompt=prompt,
            stream=True,
        )

        async for chunk in stream:
            token = chunk.get("response", "")
            if token:
                yield token

    async def ping(self) -> bool:
        """
        Check whether Ollama is reachable by listing available models.

        Returns:
            True if reachable, False otherwise.
        """
        try:
            await self.client.list()
            logger.debug("Ollama LLM ping successful.")
            return True
        except Exception as exc:
            logger.warning("Ollama LLM ping failed: %s", exc)
            return False