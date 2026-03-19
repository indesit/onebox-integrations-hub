# Handoff: Architect to Backend

## Status
DONE

## From
Architect Agent

## To
Backend Developer

## Goal
Реализовать v1 OneBox Integrations Hub: Hub Foundation, OneBox Core Adapter, Telegram Integration, Event Dispatcher, Generic Mapper, Retry Engine, Audit Log.

---

## Context
Спроектирована централизованная шина интеграций между CRM OneBox и внешними сервисами.
Ключевые архитектурные решения:
- **FastAPI** — async HTTP-сервер для приёма вебхуков (ADR-001).
- **Redis + rq** — очередь задач с retry (ADR-002).
- **Adapter Pattern + BaseAdapter** — расширяемость без правки Core (ADR-003).
- **YAML-маппинги** — config-driven трансформация полей (ADR-004).
- **Немедленный 200 OK** на вебхуки, обработка асинхронна (ADR-005).
- **SQLite v1 → PostgreSQL v2** через SQLAlchemy (ADR-006).
- **JSON Lines логирование** через structlog (ADR-007).
- **Только outbound в v1** для Telegram/SendPulse/Google Sheets (ADR-008).

---

## Input
- `projects/onebox-integrations-hub/docs/00-brief/PROJECT_BRIEF.md`
- `projects/onebox-integrations-hub/docs/00-brief/TASK.md`
- `projects/onebox-integrations-hub/docs/01-architecture/ARCHITECTURE.md`
- `projects/onebox-integrations-hub/docs/01-architecture/COMPONENTS.md`
- `projects/onebox-integrations-hub/docs/DECISIONS.md`
- `projects/onebox-integrations-hub/docs/BACKLOG_V1.md`

---

## Completed
- Определены границы системы (System Context Diagram).
- Спроектирован Hub Core: Dispatcher, Mapper, Retry Engine, Logger, Audit Log.
- Спроектированы адаптеры: OneBox, Telegram, SendPulse, Google Sheets.
- Описана структура проекта (папки и файлы).
- Описан `.env.example` с полным набором переменных.
- Зафиксированы 8 архитектурных решений в `DECISIONS.md`.
- Сформирован Backlog v1 с приоритетами P0/P1.

---

## Artifacts / Files Created or Updated
- `projects/onebox-integrations-hub/docs/01-architecture/ARCHITECTURE.md`
- `projects/onebox-integrations-hub/docs/01-architecture/COMPONENTS.md`
- `projects/onebox-integrations-hub/docs/DECISIONS.md`
- `projects/onebox-integrations-hub/docs/BACKLOG_V1.md`
- `projects/onebox-integrations-hub/06-handoffs/2026-03-09_architect_to_backend.md`

---

## Source of Truth for Next Step
1. `docs/01-architecture/ARCHITECTURE.md` — главный документ: схемы, потоки, структура проекта.
2. `docs/01-architecture/COMPONENTS.md` — детальные интерфейсы компонентов, env-переменные.
3. `docs/DECISIONS.md` — технологические решения.
4. `docs/BACKLOG_V1.md` — список задач с приоритетами.

---

## Next Steps
1. Создать структуру проекта согласно `ARCHITECTURE.md`.
2. Реализовать Hub Foundation (Epic 1): HUB-001 → HUB-008.
3. Реализовать OneBox Core Adapter (Epic 2): OB-001 → OB-005.
4. Реализовать Core Layer (Epic 3): CORE-001 → CORE-006.
5. Реализовать Telegram Integration (Epic 4): TG-001 → TG-003.

---

## Done Criteria for Next Step
- [ ] `POST /api/v1/webhook/onebox` возвращает 200 немедленно.
- [ ] HMAC-валидация подписи работает (401 на неверную подпись).
- [ ] Webhook OneBox → событие → Telegram `send_message` работает end-to-end.
- [ ] Retry: при ошибке адаптера задача повторяется 5 раз с exponential backoff.
- [ ] Audit Log: каждое выполненное задание записывается в `audit_events`.
- [ ] Логи в JSON Lines формате.

---

## Constraints and Assumptions
- Стек: Python 3.11+, FastAPI, rq, Redis, SQLAlchemy.
- OneBox API v2.
- Docker-контейнеризация.

---

## Next Expected Action
**Backend Developer** читает этот handoff и приступает к Epic 1 (HUB-001): инициализация проекта.

---

*Created: 2026-03-09*  
*Handoff status: DONE*  
*Source of Truth: projects/onebox-integrations-hub/06-handoffs/2026-03-09_architect_to_backend.md*
