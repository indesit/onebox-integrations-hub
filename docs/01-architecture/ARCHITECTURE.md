# ARCHITECTURE: OneBox Integrations Hub

**Version:** 1.0  
**Date:** 2026-03-09  
**Status:** APPROVED  
**Author:** Architect Agent

---

## 1. Обзор системы

OneBox Integrations Hub — централизованная шина интеграций между CRM OneBox и внешними сервисами (Telegram, SendPulse, Google Sheets и др.).

**Основной принцип:** Hub — единственная точка обмена данными. Ни OneBox, ни внешние сервисы не знают друг о друге напрямую.

---

## 2. Границы системы (System Boundary)

```mermaid
C4Context
    title System Context — OneBox Integrations Hub

    Person(admin, "Admin / Dev", "Настраивает маппинг, мониторит")

    System(hub, "OneBox Integrations Hub", "Центральная шина интеграций. Python/FastAPI.")

    System_Ext(onebox, "CRM OneBox", "Источник и получатель данных. API v2 + Webhooks.")
    System_Ext(telegram, "Telegram Bot API", "Уведомления, чат-боты")
    System_Ext(sendpulse, "SendPulse", "Email/SMS/Push рассылки")
    System_Ext(gsheets, "Google Sheets API", "Экспорт данных, отчёты")

    Rel(onebox, hub, "Webhook events / HTTP push", "HTTPS/JSON")
    Rel(hub, onebox, "API calls (read/write)", "HTTPS/JSON — OneBox API v2")
    Rel(hub, telegram, "Bot API calls", "HTTPS/JSON")
    Rel(hub, sendpulse, "Campaign / contact API", "HTTPS/JSON")
    Rel(hub, gsheets, "Sheets read/write", "HTTPS/JSON — Google API v4")
    Rel(admin, hub, "Config, monitoring dashboard", "HTTPS")
```

**Что входит в систему (in scope):**
- Приём вебхуков от OneBox
- Опрос OneBox API (polling) при необходимости
- Маппинг и трансформация данных
- Вызов внешних сервисов через адаптеры
- Retry-механизм, логирование, audit trail

**Что вне системы (out of scope):**
- UI для конечных пользователей OneBox
- Хранение бизнес-данных CRM
- Разработка самих Telegram-ботов или SendPulse шаблонов

---

## 3. Высокоуровневая архитектура

```mermaid
flowchart TB
    subgraph EXTERNAL_IN["Входящие источники"]
        OB_HOOK["OneBox Webhook\n(HTTP POST)"]
        OB_POLL["OneBox Polling\n(Scheduler)"]
    end

    subgraph HUB["OneBox Integrations Hub"]
        direction TB

        subgraph ENTRYPOINT["Entry Layer"]
            API["FastAPI\nWebhook Receiver\n/api/v1/webhook/{source}"]
            SCHEDULER["APScheduler\nPolling Jobs"]
        end

        subgraph CORE["Hub Core"]
            DISPATCHER["Event Dispatcher"]
            MAPPER["Generic Mapper\n(config-driven)"]
            RETRY["Retry Engine\n(exponential backoff)"]
            LOGGER["Structured Logger\n(JSON)"]
            AUDIT["Audit Log\n(SQLite/Postgres)"]
        end

        subgraph ADAPTERS["Service Adapters"]
            OB_ADAPTER["OneBox\nCore Adapter"]
            TG_ADAPTER["Telegram\nAdapter"]
            SP_ADAPTER["SendPulse\nAdapter"]
            GS_ADAPTER["Google Sheets\nAdapter"]
            FUTURE["... Future\nAdapters"]
        end

        subgraph QUEUE["Queue Layer"]
            REDIS["Redis Queue\n(rq / celery-lite)"]
        end
    end

    subgraph EXTERNAL_OUT["Внешние сервисы"]
        ONEBOX["CRM OneBox\nAPI v2"]
        TELEGRAM["Telegram\nBot API"]
        SENDPULSE["SendPulse\nAPI"]
        GSHEETS["Google Sheets\nAPI v4"]
    end

    OB_HOOK -->|HTTPS POST| API
    OB_POLL --> SCHEDULER

    API --> DISPATCHER
    SCHEDULER --> DISPATCHER

    DISPATCHER --> MAPPER
    MAPPER --> REDIS
    REDIS --> RETRY
    RETRY --> OB_ADAPTER
    RETRY --> TG_ADAPTER
    RETRY --> SP_ADAPTER
    RETRY --> GS_ADAPTER

    OB_ADAPTER <--> ONEBOX
    TG_ADAPTER --> TELEGRAM
    SP_ADAPTER --> SENDPULSE
    GS_ADAPTER --> GSHEETS

    DISPATCHER --> LOGGER
    RETRY --> LOGGER
    LOGGER --> AUDIT
```

---

## 4. Hub Core — детальное описание

### 4.1 Entry Layer

| Компонент | Технология | Назначение |
|---|---|---|
| Webhook Receiver | FastAPI | Принимает HTTP POST от OneBox, валидирует подпись (HMAC), возвращает 200 немедленно |
| Polling Scheduler | APScheduler | Регулярный опрос OneBox API для pull-based интеграций |

**Принцип:** Entry Layer не выполняет бизнес-логику. Только валидация + постановка в очередь.

### 4.2 Event Dispatcher

Принимает нормализованный `HubEvent`, определяет маршрут:
- Какой адаптер (или несколько) должен обработать событие
- Порядок вызова (параллельно или последовательно)
- Конфигурация берётся из `routing_rules.yaml`

```mermaid
flowchart LR
    EVENT["HubEvent\n{source, event_type, payload}"] --> DISPATCHER
    DISPATCHER --> RULE_CHECK{"routing_rules.yaml\nmatches?"}
    RULE_CHECK -- "да" --> ENQUEUE["Enqueue tasks\nfor matching adapters"]
    RULE_CHECK -- "нет" --> DEADLETTER["Dead Letter Log\n+ Alert"]
```

### 4.3 Generic Mapper

Config-driven трансформация полей по схемам.

**Источник конфига:** `config/mappings/{integration_name}.yaml`

**Принцип:** Новый маппинг — новый YAML-файл, без изменения кода.

### 4.4 Retry Engine

- Стратегия: экспоненциальный backoff (1s → 2s → 4s → 8s → max 5 попыток)
- При исчерпании попыток: запись в `dead_letter_queue` + структурированный алерт

### 4.5 Structured Logger + Audit

- Формат: JSON Lines
- Audit Log: таблица `audit_events` в БД — хранит полный payload запроса/ответа

---

## 5. Adapter Layer — паттерн

Все адаптеры реализуют единый интерфейс `BaseAdapter`.

**Принцип Open-Closed:** новый сервис = новый класс-наследник `BaseAdapter`. Ядро Hub не изменяется.

---

## 6. Структура проекта

```
onebox-integrations-hub/
├── src/
│   ├── main.py                    # FastAPI app entry point
│   ├── core/                      # Dispatcher, Mapper, Retry, Logger
│   ├── adapters/                  # OneBox, Telegram, SendPulse, GSheets
│   ├── api/                       # Routes for webhooks & health
│   ├── scheduler/                 # Polling jobs
│   └── config/                    # Settings & loaders
├── config/                        # YAML mappings & routing rules
├── tests/                         # Unit & Integration tests
├── docker/                        # Dockerfile & Compose
└── docs/                          # Architecture, Decisions, Backlog
```

---

*Source of Truth: projects/onebox-integrations-hub/docs/01-architecture/ARCHITECTURE.md*  
*Created: 2026-03-09*
