# HANDOFF: OneBox Sync Worker & Client (Epic 7)

## Status
DONE ✅ (Core Sync Flow)

## From
Main Agent (Acting as Backend Developer)

## To
Backend Developer (Project Integration)

## Goal
Реалізація фонового воркера для синхронізації чеків з PostgreSQL бази Хабу в CRM OneBox через API v2.

---

## Context
Хаб тепер працює як Data Warehouse. Дані з 1С спочатку потрапляють у Postgres, а потім воркер гарантовано передає їх у OneBox.

---

## Completed
- **OneBox API Client:** Створено `src/adapters/onebox/client.py`. Це обгортка над API v2 для створення замовлень (`order/set/`). Використовує асинхронний HTTP-клієнт `httpx`.
- **Sync Worker:** Створено `src/scheduler/onebox_sync.py`. 
  - **Polling:** Воркер щохвилини вибирає з бази до 10 несинхронізованих чеків.
  - **Payload Builder:** Автоматично формує правильний `productinfo` з ID товарів та характеристиками.
  - **Status Update:** Після успішної синхронізації в базу записується `onebox_id` та ставиться прапорець `synced_to_onebox = True`.
- **Logic Isolation:** Код воркера не залежить від вхідних вебхуків, що дозволяє перезапускати синхронізацію без повторної відправки даних з 1С.

---

## Artifacts / Files Created
- `src/adapters/onebox/client.py` (NEW)
- `src/scheduler/onebox_sync.py` (NEW)

---

## Next Steps
1. **Error Handling:** Додати механізм сповіщень у Telegram (через існуючий TG-адаптер), якщо чек не вдається синхронізувати більше 5 разів (Dead Letter Queue).
2. **Product Sync:** Реалізувати скрипт для періодичного оновлення бази товарів `Products` у Хабі, щоб ми мали актуальні `onebox_id` для мапінгу.
3. **P&L SQL:** Написати перший аналітичний запит для підрахунку маржі на основі реальних даних у Postgres.

---
*Created: 2026-03-11*
