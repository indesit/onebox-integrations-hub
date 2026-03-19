# HANDOFF: BAF Adapter & DB Integration (Epic 7)

## Status
DONE ✅ (Inbound Logic)

## From
Main Agent (Acting as Backend Developer)

## To
Backend Developer (Next: OneBox Sync Worker)

## Goal
Реалізація вхідного адаптера для 1С/BAF з обов'язковим збереженням у PostgreSQL перед синхронізацією.

---

## Context
Ми реалізували стратегію Data Warehouse. Тепер кожен чек з 1С спочатку валідується та зберігається в базу даних Хабу.

---

## Completed
- **DB Connection:** Створено `src/core/database.py` для керування сесіями PostgreSQL через SQLAlchemy/SQLModel.
- **Normalizer Extension:** Оновлено `src/adapters/baf/normalizer.py`. Тепер він вміє мапити складні JSON-дані з 1С (товари з характеристиками: розмір, чашка, колір) у DB-моделі.
- **BAF Adapter:** Створено `src/adapters/baf/adapter.py`. 
  - **Ідемпотентність:** Перевіряє, чи не був цей чек уже записаний (по `external_id` з 1С).
  - **Клієнти:** Автоматично шукає або створює клієнта в базі за номером телефону.
  - **Товари:** Шукає товар за SKU. Якщо товару немає — створює «заглушку» для подальшого оновлення з OneBox.
  - **Транзакційність:** Використовує сесії SQLModel для гарантії цілісності даних (якщо впаде запис товару — відкотиться весь чек).

---

## Artifacts / Files Created/Updated
- `src/core/database.py` (NEW)
- `src/adapters/baf/normalizer.py` (Updated)
- `src/adapters/baf/adapter.py` (NEW)

---

## Next Steps
1. **OneBox Sync Worker:** Створити скрипт, який буде вибирати з бази `Receipts` з прапорцем `synced_to_onebox=False` і створювати їх у OneBox через API v2.
2. **Product Sync:** Додати механізм оновлення кешу товарів у таблиці `Products` з OneBox.
3. **P&L Draft:** Почати проектування першого SQL-запиту для звіту на основі реальних даних у базі.

---
*Created: 2026-03-11*
