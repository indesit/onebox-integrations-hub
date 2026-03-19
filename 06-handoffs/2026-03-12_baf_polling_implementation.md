# HANDOFF: BAF Polling Implementation (Epic 7)

## Status
IMPLEMENTED ✅ (Awaiting 1C Service Config)

## From
Main Agent (Acting as Architect & Backend Developer)

## To
Owner (Anton)

## Goal
Перехід на модель Polling (опитування) для отримання чеків з 1С УНФ 1.6 у Хаб.

---

## Technical Instructions for 1C (BAF)

### 1. HTTP-Service Configuration
У конфігураторі 1С створити HTTP-сервіс (наприклад, `OneBoxIntegrations`) з наступними параметрами:
- **Root URL:** `OneBoxIntegrations/v1/`
- **Resource:** `get_receipts` (Template: `get_receipts`)
- **Method:** `GET`
- **Method Logic:** Повинен приймати параметри `start_date` та `end_date` (Тип: Дата) і повертати JSON згідно з специфікацією в `docs/01-architecture/1C_POLLING_SPEC.md`.

### 2. SQL Query Execution
Використати наданий SQL запит у коді 1С модуля. **Важливо:** Для коректного мапінгу в Хаб, JSON повинен містити не лише посилання (Refs), а й реальні **Артикули (SKU)** та **Найменування характеристик** (Розмір, Чашка, Колір).

---

## Completed in Hub
- **Integration Spec:** Створено `docs/01-architecture/1C_POLLING_SPEC.md` з описом формату JSON та параметрів запиту.
- **Polling Worker:** Реалізовано `src/scheduler/baf_polling.py`. 
  - **Автоматика:** Скрипт сам ініціює запит до 1С, забирає нові чеки та передає їх у наш `BafAdapter`.
  - **Безпека:** Запит виконується з Basic Auth (логин/пароль 1С).
  - **Ідемпотентність:** Навіть якщо часові інтервали опитування перетинаються, Хаб не створить дублікатів у базі завдяки перевірці `external_id`.

---

## Next Steps
1. **1C Service Setup:** Антону необхідно створити HTTP-сервіс у 1С згідно з інструкцією.
2. **Connectivity Test:** Після створення сервісу ми проведемо перший тестовий запит за останню годину.
3. **Cron Setup:** Коли тест пройде успішно, ми додамо цей воркер у розклад (щохвилини).

---
*Created: 2026-03-12*
