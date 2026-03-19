# HANDOFF: ETL Layer & Data Warehouse Implementation (Epic 7)

## Status
COMPLETED ✅ (Ready for Integration Testing)

## From
Bony (Main Agent)

## To
Owner (Anton)

## Goal
Повноцінна реалізація ETL-шару та DWH структури для синхронізації 1С -> Hub -> OneBox.

---

## Completed
- **DWH Schema:** Впроваджено структуру Staging -> Dimensions -> Facts.
- **Models:** Оновлено `src/core/models_db.py` з підтримкою OneBox статусів, `ext_data` (JSONB) та технічних полів (`load_id`, `updated_at`).
- **ETL Engine:** Створено `src/core/etl.py` з логікою Upsert для запобігання дублікатів та оновлення існуючих чеків.
- **Adapter Integration:** `BafAdapter` тепер автоматично запускає ETL при кожному отриманні даних.
- **Catalog Worker:** Створено `src/scheduler/catalog_sync.py` для автоматичного оновлення довідника товарів та характеристик з 1С.

---

## Artifacts / Files
- `src/core/models_db.py` (Core Models)
- `src/core/etl.py` (ETL Logic)
- `src/scheduler/catalog_sync.py` (New Catalog Worker)
- `src/adapters/baf/adapter.py` (Updated Adapter)

---

## Next Steps
1. **Database Migration:** Запустити `init_db()` для створення нових таблиць.
2. **OneBox Sync Update:** Переписати `onebox_sync.py` на роботу з `FactSalesReportItem` (читання `pending` записів).
3. **End-to-End Test:** Прогнати повний цикл: оновити каталог -> отримати чеки -> перевірити появу записів у фактах зі статусом `pending`.

---
*Created: 2026-03-12*
