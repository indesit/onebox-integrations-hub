import yaml
from typing import Any
from src.core.models import HubEvent, AdapterTask
from src.core.logger import get_logger
from src.core.queue import enqueue_task

logger = get_logger(__name__)

class EventDispatcher:
    def __init__(self, rules_path: str = "config/routing_rules.yaml"):
        self.rules_path = rules_path
        self._rules = self._load_rules()

    def _load_rules(self) -> list[dict]:
        try:
            with open(self.rules_path, "r") as f:
                config = yaml.safe_load(f)
                return config.get("rules", [])
        except Exception as e:
            logger.error("failed_to_load_routing_rules", error=str(e))
            return []

    def dispatch(self, event: HubEvent):
        matched_count = 0
        for rule in self._rules:
            match = rule.get("match", {})
            if match.get("source") == event.source and match.get("event_type") == event.event_type:
                for adapter_cfg in rule.get("adapters", []):
                    # В Epic 3 мы вызываем Mapper, чтобы подготовить AdapterTask
                    # Пока подготовим импорт внутри метода, чтобы избежать циклов
                    from src.core.mapper import mapper
                    
                    try:
                        task = mapper.map(event, adapter_cfg)
                        # Ставим в очередь реально через наш helper
                        from src.core.worker import execute_adapter_task
                        enqueue_task(execute_adapter_task, task.model_dump())
                        
                        logger.info("event_dispatched", event_id=event.event_id, adapter=adapter_cfg['name'])
                        matched_count += 1
                    except Exception as e:
                        logger.error("dispatch_failed", event_id=event.event_id, error=str(e))
        
        if matched_count == 0:
            logger.warning("no_routing_rule_matched", event_id=event.event_id, source=event.source, type=event.event_type)

dispatcher = EventDispatcher()
