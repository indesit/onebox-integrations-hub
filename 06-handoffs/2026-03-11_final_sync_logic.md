# HANDOFF: Final BAF to OneBox Sync Logic (10-min Cron)

## Status
READY FOR PROD ✅

## From
Main Agent (Acting as Architect & Backend Dev)

## To
Owner (Anton)

## Goal
Фіналізація логіки синхронізації чеків з 1С у OneBox CRM за 10-хвилинним графіком (Cron).

---

## Final Logic (Implemented)
- **Sync Mode:** Батчева обробка (Cron). Воркер щоразу забирає до 50 нових чеків з бази PostgreSQL.
- **Product Mapping:** 
  - Кожна позиція чека тепер містить `productcomment` з деталями Victoria's Secret: **Size, Cup, Color**.
  - Це дозволяє бачити специфіку продажу прямо в рядку товару в OneBox.
- **Idempotency:** Використовується `externalid: 1c_{receipt_id}`, що виключає дублікати навіть при збоях зв'язку.
- **Workflow & Status:** Жорстко закріплено `workflowid: 9` та `statusid: 54` (Проведений).

---

## Artifacts / Files Updated
- `src/scheduler/onebox_sync.py`: Оновлено логіку батчів та мапінгу характеристик.

---

## Next Steps (Planned)
1. **Cron Setup:** Налаштування системного планувальника на сервері для виклику `onebox_sync.py` кожні 10 хвилин.
2. **Monitoring Dashboard:** Створення простого SQL-запиту в Postgres для перегляду статистики синхронізації (кількість чеків, помилок, сума).
3. **P&L Preparation:** Коли база наповниться реальними даними за тиждень, ми зможемо витягнути першу матрицю продажів по категоріям.

---
*Created: 2026-03-11*
