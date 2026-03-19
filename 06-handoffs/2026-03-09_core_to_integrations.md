# Handoff: Core Layer to Integrations (Telegram/SendPulse)

## Status
DONE

## From
Main Agent (Acting as Backend Developer)

## To
Backend Developer (Next Stage: Service Integrations)

## Goal
Реализовать конкретные адаптеры (Telegram, SendPulse, Google Sheets) и подключить их в готовую Core-структуру.

---

## Context
Реализован Epic 3 (Core Layer). У хаба появились "мозги": Dispatcher умеет маршрутизировать события, а GenericMapper — трансформировать их через YAML-конфиги. Настроен Audit Log в SQLite.

---

## Completed
- **CORE-001:** `AdapterRegistry` для управления инстансами адаптеров.
- **CORE-002:** `EventDispatcher` с поддержкой `routing_rules.yaml`.
- **CORE-003:** `GenericMapper` с поддержкой Jinja2 шаблонов и `copy/const`.
- **CORE-006:** `AuditLog` на SQLAlchemy для записи истории обменов в БД.
- **Интеграция:** Подготовлена почва для автоматического маппинга событий из OneBox в любой другой сервис.

---

## Artifacts / Files Created
- `src/core/registry.py` — реестр адаптеров.
- `src/core/dispatcher.py` — маршрутизатор.
- `src/core/mapper.py` — движок трансформации данных.
- `src/core/audit.py` — аудит и работа с БД.

---

## Next Steps
1. Реализовать **Epic 4 (Telegram Integration)**:
   - Создать `src/adapters/telegram/client.py` и `adapter.py`.
   - Зарегистрировать TelegramAdapter в реестре.
2. Проверить цепочку: OneBox Webhook -> Dispatcher -> Mapper -> Telegram.
3. Реализовать Epic 5 (SendPulse) и Epic 6 (Google Sheets) по аналогии.

---
*Created: 2026-03-09*
