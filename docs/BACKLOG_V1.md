# BACKLOG V1: OneBox Integrations Hub

**Version:** 1.0  
**Date:** 2026-03-09  
**Priority:** P0 = must have v1 | P1 = should have v1 | P2 = v2+

---

## Epic 1: Hub Foundation (P0)
- **HUB-001:** Инициализация проекта: структура папок, pyproject.toml, .env.example.
- **HUB-002:** FastAPI приложение: base app, CORS, middleware.
- **HUB-003:** Webhook endpoint `POST /api/v1/webhook/{source}` с HMAC-валидацией.
- **HUB-004:** Health check endpoint `GET /health`.
- **HUB-005:** Pydantic-модели: HubEvent, AdapterTask, AdapterResult.
- **HUB-006:** Structured Logger (structlog, JSON Lines).
- **HUB-007:** Redis Queue интеграция (rq).
- **HUB-008:** Docker + docker-compose (hub, redis, db).

---

## Epic 2: OneBox Core Adapter (P0)
- **OB-001:** OneBox API v2 HTTP client (httpx, async).
- **OB-002:** Webhook normalizer: raw payload → HubEvent.
- **OB-003:** Реализация `OneBoxAdapter.execute()` для outbound-действий.
- **OB-004:** Actions: update_deal, add_comment, change_status.
- **OB-005:** Обработка ошибок OneBox API: 401, 429, 5xx + retry.

---

## Epic 3: Event Dispatcher + Generic Mapper (P0)
- **CORE-001:** Adapter Registry.
- **CORE-002:** Event Dispatcher + `routing_rules.yaml` loader.
- **CORE-003:** Generic Mapper: copy, const, template (Jinja2), lookup.
- **CORE-004:** Retry Engine с exponential backoff.
- **CORE-005:** Dead Letter Queue: таблица + лог алерт.
- **CORE-006:** Audit Log: SQLAlchemy модель + Alembic миграция.

---

## Epic 4: Telegram Integration (P0) [DONE]
- **TG-001:** Telegram Bot API client (httpx). [DONE]
- **TG-002:** TelegramAdapter.execute() — `send_message`. [DONE]
- **TG-003:** Маппинг и routing rule для Telegram. [DONE]

---

## Epic 5: SendPulse & GSheets (P1)
- **SP-001:** SendPulse API client + OAuth2 token refresh.
- **SP-002:** SendPulseAdapter.execute() — `add_contact_to_list`.
- **GS-001:** Google Sheets API client.
- **GS-002:** GoogleSheetsAdapter.execute() — `append_row`.

---

## Epic 7: 1C/BAF Integration (P0)
- **BAF-001:** Проектування контракту Webhook для 1С (JSON structure).
- **BAF-002:** Ендпоінт `POST /api/v1/webhook/1c` з базовою авторизацією.
- **BAF-003:** BafAdapter для нормалізації даних чеків (1C -> HubEvent).
- **BAF-004:** Маппінг `1c_receipt_to_onebox_deal.yaml`.
- **BAF-005:** Логіка "Contact Upsert" (Матчінг по телефону + прізвищу).
- **BAF-006:** Тестування ланцюжка: 1С -> Hub -> OneBox.

---

## Epic 6: Observability (P0-P1)
- **OBS-001:** Лог ротация по размеру (100MB, 5 файлов).
- **OBS-002:** Алерт в Telegram при dead letter event.

---

*Source of Truth: projects/onebox-integrations-hub/docs/BACKLOG_V1.md*  
*Created: 2026-03-09*
