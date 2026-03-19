from typing import Any
from src.adapters.base import BaseAdapter
from src.core.logger import get_logger

logger = get_logger(__name__)

class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter):
        self._adapters[adapter.name] = adapter
        logger.info("adapter_registered", name=adapter.name)

    def get(self, name: str) -> BaseAdapter:
        adapter = self._adapters.get(name)
        if not adapter:
            raise ValueError(f"Adapter '{name}' not found")
        return adapter

    def list_all(self) -> list[str]:
        return list(self._adapters.keys())

registry = AdapterRegistry()
