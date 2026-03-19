# HANDOFF: Infrastructure Update (PostgreSQL)

## Status
IN_PROGRESS 🛠️

## From
Main Agent (Acting as Architect)

## To
Backend Developer (Project Implementation)

## Goal
Перехід з SQLite на PostgreSQL для підтримки аналітичного сховища (Data Warehouse) та складної матриці товарів (Victoria's Secret).

---

## Context
За пропозицією Антона (Owner), Хаб тепер не просто транзитна шина, а база даних усіх продажів для подальших P&L звітів та планування закупівель.

---

## Changes
- **Database:** Перехід на PostgreSQL. Оновлено `COMPONENTS.md`.
- **Schema:** Створено `docs/01-architecture/DB_SCHEMA.md` з описом таблиць `receipts`, `receipt_items`, `products`.
- **Logic Change:** Додано шар персистентності. Кожен вхідний чек з 1С спочатку пишеться в БД, а потім синхронізується з OneBox.

---

## Artifacts / Files Updated
- `docs/01-architecture/DB_SCHEMA.md` (NEW)
- `docs/01-architecture/COMPONENTS.md` (Updated DATABASE_URL)

---

## Next Steps
1. **DB Setup:** Налаштування контейнера PostgreSQL.
2. **Models Implementation:** Створення SQLAlchemy/SQLModel моделей на основі `DB_SCHEMA.md`.
3. **Migration:** Перенесення логіки `1c_receipt` у новий потік: `1C Webhook` -> `DB Insert` -> `Async Sync to OneBox`.

---
*Created: 2026-03-11*
