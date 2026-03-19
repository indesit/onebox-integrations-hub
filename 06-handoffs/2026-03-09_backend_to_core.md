# Handoff: OneBox Adapter to Core Layer

## Status
DONE

## From
Main Agent (Acting as Backend Developer)

## To
Backend Developer (Next Stage: Core Layer)

## Goal
Интегрировать реализованный OneBox Adapter в общую логику Dispatcher и Mapper.

---

## Context
Реализован Epic 2 (OneBox Core Adapter). Система теперь умеет не только принимать вебхуки, но и полноценно взаимодействовать с OneBox API v2 для выполнения обратных действий.

---

## Completed
- **OB-001:** Реализован асинхронный HTTP клиент `OneBoxClient` (GET, PATCH, POST).
- **OB-002:** Создан `OneBoxNormalizer` для трансформации входящих вебхуков в `HubEvent`.
- **OB-003:** Реализован класс `OneBoxAdapter` согласно контракту `BaseAdapter`.
- **OB-004:** Добавлена поддержка действий: `update_deal`, `add_comment`, `change_status`.
- **OB-005:** Настроена базовая обработка ошибок API с логированием.

---

## Artifacts / Files Created
- `src/adapters/onebox/client.py` — API клиент.
- `src/adapters/onebox/normalizer.py` — нормализация входящих данных.
- `src/adapters/onebox/adapter.py` — основной адаптер.

---

## Next Steps
1. Реализовать **Epic 3 (Core Layer)**:
   - `AdapterRegistry` (регистрация OneBoxAdapter).
   - `EventDispatcher` (маршрутизация событий по `routing_rules.yaml`).
   - `GenericMapper` (трансформация данных через YAML).
2. Подключить `OneBoxNormalizer` в `src/api/routes/webhook.py`.

---
*Created: 2026-03-09*
