# COMPONENTS: OneBox Integrations Hub

**Version:** 1.0  
**Date:** 2026-03-09  
**Status:** APPROVED

---

## Обзор компонентов

```mermaid
classDiagram
    class HubEvent {
        +str event_id
        +str source
        +str event_type
        +dict payload
    }

    class AdapterTask {
        +str task_id
        +str adapter_name
        +dict data
    }

    class AdapterResult {
        +str task_id
        +bool success
        +str error_message
    }

    class BaseAdapter {
        <<abstract>>
        +str name
        +execute(task: AdapterTask) AdapterResult
    }

    class OneBoxAdapter {
        +normalize_webhook(raw: dict) HubEvent
        +execute(task: AdapterTask) AdapterResult
    }

    class EventDispatcher {
        +dispatch(event: HubEvent) list~AdapterTask~
    }

    class GenericMapper {
        +map(event: HubEvent, rule: MappingRule) AdapterTask
    }

    class RetryEngine {
        +process(task: AdapterTask) AdapterResult
    }

    BaseAdapter <|-- OneBoxAdapter
    BaseAdapter <|-- TelegramAdapter
    BaseAdapter <|-- SendPulseAdapter
    BaseAdapter <|-- GoogleSheetsAdapter
```

---

## 1. Entry Layer

### 1.1 FastAPI Webhook Receiver
**Endpoint:** `POST /api/v1/webhook/{source}`  
**Responsibility:** HMAC verification, deserialization, dispatch.

### 1.2 Health Check
**Endpoint:** `GET /health`  
**Responsibility:** Connectivity check for all adapters and queue depth.

---

## 2. Core Layer

### 2.1 Event Dispatcher
**Responsibility:** Routing `HubEvent` based on `routing_rules.yaml`.

### 2.2 Generic Mapper
**Responsibility:** Field transformation (`copy`, `template`, `lookup`, `const`).

### 2.3 Retry Engine
**Responsibility:** Exponential backoff (max 5 attempts) + Dead Letter Queue management.

### 2.4 Structured Logger
**Format:** JSON Lines via `structlog`.

### 2.5 Audit Log
**Responsibility:** Storing all inbound/outbound payloads. 90-day retention.

---

## 3. Adapter Layer

### 3.1 OneBox Core Adapter
**Direction:** Inbound (webhook) & Outbound (update_deal, add_comment).

### 3.2 Telegram Adapter
**Outbound (v1):** `send_message`.

### 3.3 SendPulse Adapter
**Outbound (v1):** `add_contact_to_list`, `trigger_automation`.

### 3.4 Google Sheets Adapter
**Outbound (v1):** `append_row`, `update_cell`.

---

## 4. Environment (.env.example)

```env
ONEBOX_DOMAIN=your-company.onebox.ru
ONEBOX_API_KEY=your_api_key_here
ONEBOX_WEBHOOK_SECRET=hmac_secret_here

TELEGRAM_BOT_TOKEN=bot_token_here
SENDPULSE_CLIENT_ID=client_id_here
GOOGLE_SERVICE_ACCOUNT_JSON=/run/secrets/gsa_key.json
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://user:password@localhost:5432/hub_db
```

---

*Source of Truth: projects/onebox-integrations-hub/docs/01-architecture/COMPONENTS.md*  
*Created: 2026-03-09*
