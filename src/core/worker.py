from src.core.models import AdapterTask, AdapterResult
from src.core.registry import registry
from src.core.audit import audit_log, init_db
from src.core.logger import get_logger
import asyncio

logger = get_logger(__name__)

# Инициализируем БД при импорте в воркере
init_db()

def execute_adapter_task(task_dict: dict):
    """Фоновая задача для RQ воркера."""
    task = AdapterTask(**task_dict)
    
    # Т.к. наши адаптеры асинхронные, а RQ воркер синхронный
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_execute(task))

async def _execute(task: AdapterTask):
    # Т.к. воркер импортирует этот файл при старте, нужно убедиться,
    # что адаптеры зарегистрированы в реестре.
    # В v1 просто импортируем их здесь для регистрации
    from src.adapters.telegram.adapter import TelegramAdapter
    if "telegram" not in registry.list_all():
        registry.register(TelegramAdapter())

    adapter = registry.get(task.adapter_name)
    
    logger.info("executing_adapter_task", task_id=task.task_id, adapter=task.adapter_name)
    
    result = await adapter.execute(task)
    
    # Записываем в аудит лог
    audit_log.write(
        task_id=task.task_id,
        adapter=task.adapter_name,
        event_type="outbound_action",
        request=task.data,
        result=result
    )
    
    if result.success:
        logger.info("task_completed_successfully", task_id=task.task_id)
    else:
        logger.error("task_failed", task_id=task.task_id, error=result.error_message)
    
    return result.success
