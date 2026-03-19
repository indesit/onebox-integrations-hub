# HANDOFF: ETL Layer & Data Warehouse Structure (Epic 7)

## Status
IN_PROGRESS ⚙️

## From
Main Agent (Acting as Data Engineer)

## To
Owner (Anton)

## Goal
Реалізація шару ETL та структури Data Warehouse (DWH) у PostgreSQL для повноцінної аналітики продажів.

---

## Context
Переходимо до Варіанту 1: проектування та впровадження таблиць PostgreSQL для зв'язку продажів з каталогом товарів.

---

## Completed
- **Schema Update:** Оновлено `docs/01-architecture/DB_SCHEMA.md` згідно з моделлю.
- **Models Update:** Переписано `src/core/models_db.py` на нову структуру.
- **ETL Layer Core:** Створено `src/core/etl.py`, який реалізує завантаження в `stg` та перетворення у `fact_sales`.
- **BafAdapter Integrated:** Адаптер 1С тепер автоматично зберігає дані в staging-таблиці та запускає ETL-процес при кожному опитуванні.

---

## Artifacts / Files Updated
- `docs/01-architecture/DB_SCHEMA.md`
- `src/core/models_db.py`
- `src/core/etl.py` (New)
- `src/adapters/baf/adapter.py`
- `src/core/database.py`

---

## Next Steps
1. **Catalog Polling:** Реалізувати окремий воркер для оновлення `dim_product_variants` з API 1С (зараз вони наповнюються лише при синхронізації каталогу).
2. **OneBox Sync Update:** Переключити `onebox_sync.py` на читання з `fact_sales_receipt_items` замість застарілих таблиць `receipts/items`.

---
*Created: 2026-03-12*
