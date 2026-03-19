import yaml
import os
from typing import Any
from jinja2 import Template
from src.core.models import HubEvent, AdapterTask
from src.core.logger import get_logger

logger = get_logger(__name__)

class GenericMapper:
    def __init__(self, mappings_dir: str = "config/mappings"):
        self.mappings_dir = mappings_dir

    def map(self, event: HubEvent, adapter_cfg: dict) -> AdapterTask:
        mapping_name = adapter_cfg.get("mapping")
        if not mapping_name:
            # Если маппинг не указан, передаем payload как есть
            return AdapterTask(
                adapter_name=adapter_cfg["name"],
                action=adapter_cfg.get("action", ""),
                data=event.payload
            )

        mapping_path = os.path.join(self.mappings_dir, f"{mapping_name}.yaml")
        with open(mapping_path, "r") as f:
            mapping_spec = yaml.safe_load(f)

        mapped_data = {}
        for field in mapping_spec.get("fields", []):
            target = field["target"]
            op = field["op"]
            
            if op == "const":
                mapped_data[target] = field["value"]
            elif op == "copy":
                # Упрощенный доступ к полям через точку (например payload.deal_id)
                mapped_data[target] = self._resolve_path(field["from"], event)
            elif op == "template":
                template = Template(field["template"])
                mapped_data[target] = template.render(
                    payload=event.payload,
                    event_type=event.event_type,
                    source=event.source
                )
            # lookup реализуем в v1.1 или по необходимости

        return AdapterTask(
            adapter_name=adapter_cfg["name"],
            action=adapter_cfg.get("action", ""),
            data=mapped_data
        )

    def _resolve_path(self, path: str, event: HubEvent) -> Any:
        parts = path.split('.')
        current = {"payload": event.payload, "event_type": event.event_type, "source": event.source}
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

mapper = GenericMapper()
