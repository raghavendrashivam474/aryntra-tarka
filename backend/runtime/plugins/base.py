from abc import ABC, abstractmethod
from typing import Any, Dict


class PluginBase(ABC):
    """
    Every plugin must implement this interface.
    Runtime only speaks to this contract.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """What this plugin does."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version string."""
        pass

    @property
    def input_schema(self) -> Dict:
        """
        Optional JSON schema for input validation.
        Override in plugin to enforce strict inputs.
        """
        return {}

    @property
    def output_schema(self) -> Dict:
        """
        Optional JSON schema for output validation.
        """
        return {}

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core execution method.
        Receives input dict.
        Returns output dict.
        """
        pass

    def health_check(self) -> bool:
        """
        Optional health check.
        Return False if plugin cannot operate.
        """
        return True
