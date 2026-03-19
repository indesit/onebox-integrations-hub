"""Base adapter contract for all outbound integrations."""

from abc import ABC, abstractmethod

from src.core.models import AdapterResult, AdapterTask


class BaseAdapter(ABC):
    """Common interface for all adapters."""

    name: str

    @abstractmethod
    async def execute(self, task: AdapterTask) -> AdapterResult:
        """Execute adapter task and return normalized result."""
        raise NotImplementedError
