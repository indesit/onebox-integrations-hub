# ARCHITECTURE CURRENT (OneBox Integrations Hub)

Last updated: 2026-03-22
Status: ACTIVE SOURCE OF TRUTH

## 1) Purpose
Hub synchronizes **BAF receipts → OneBox deals** with strict guardrails:
- no duplicate deals by receipt number
- no duplicate contacts by phone
- no anonymous deals in CRM
- no returns in CRM
- price in OneBox = **actual paid amount** from BAF (`line_amount`), not list/base price

---

## 2) Active flow (every 20 minutes)

1. `src/scheduler/baf_polling.py`
   - GET BAF receipt lines
   - store + transform via ETL
   - run customer refresh
   - run OneBox sync batch

2. `src/adapters/baf/adapter.py`
   - passes rows to ETL layer

3. `src/core/etl.py`
   - stage rows to `stg_baf_receipt_lines`
   - upsert to `fact_sales_receipt_items` (status=`pending` for new)

4. `src/scheduler/stores_customers_sync.py`
   - refreshes `dim_customers` and `dim_stores` from BAF

5. `src/scheduler/onebox_sync.py`
   - processes `pending` receipts grouped by `receipt_uuid`
   - creates/links contacts in OneBox
   - creates/skips deals in OneBox
   - updates local sync status

---

## 3) External API calls

### BAF (1C)
- `GET /SecretShopBAS/hs/reports/receipt_lines`
- `GET /SecretShopBAS/hs/reports/customers`
- `GET /SecretShopBAS/hs/reports/stores`

### OneBox API v2
- `POST /api/v2/token/get/`
- `POST /api/v2/contact/get/`
- `POST /api/v2/contact/set/`
- `POST /api/v2/product/set/`
- `POST /api/v2/order/get/`
- `POST /api/v2/order/set/`

---

## 4) Core tables and fields

### `stg_baf_receipt_lines`
Raw/staged BAF lines:
- `receipt_uuid`, `receipt_number`, `receipt_datetime`
- `store_uuid`, `customer_uuid`
- `line_no`, `product_uuid`, `characteristic_uuid`
- `qty`, `price`, `line_amount`
- `raw_payload`

### `fact_sales_receipt_items` (main sync table)
- receipt identity: `receipt_uuid`, `line_no`, `receipt_number`, `receipt_datetime`
- actors: `store_uuid`, `customer_uuid`
- values: `qty`, `price`, `line_amount`
- OneBox sync fields:
  - `onebox_status` (`pending|synced|failed|ignored_return|ignored_anonymous|ignored_backfill`)
  - `onebox_order_id`
  - `sync_error`
  - `onebox_synced_at`

### `dim_customers`
- `customer_uuid`, `customer_name`, `customer_phone`

### `dim_stores`
- `store_uuid`, `store_name`

---

## 5) Dedup + validation rules

### Deal dedup
- deal name in OneBox = receipt number without prefix `НФНФ-` (example: `R30721`)
- before send: check `order/get` by name
- if exists: mark local receipt as synced and store found `onebox_order_id`

### Contact dedup
- phone normalized to numeric UA format
- search in OneBox via `contact/get` with `filter.phones`
- if not found: `contact/set` with `findbyArray: ["externalid", "phone"]`

### What is NOT sent
- returns (`qty < 0`) → `ignored_return`
- receipts without customer → `ignored_anonymous`
- legacy backfill blocked by policy date → `ignored_backfill`

### Missing customer race condition
If receipt has `customer_uuid` but customer is not yet in `dim_customers`:
- do NOT create anonymous deal
- keep receipt in `pending`
- set `sync_error = missing_customer_in_dim`
- retry on next cycle after customer refresh

---

## 6) Price/sum logic

Order line price to OneBox is calculated as:
`actual_price = line_amount / qty`

This preserves applied discount and makes total paid amount in OneBox match BAF/1C fiscal payment.

---

## 7) Scheduling

Current schedule is kept intentionally simple:
- `baf_polling.py` runs every 20 minutes (existing cron/RQ schedule)
- polling script itself triggers customer refresh and onebox sync batch
- no extra cron duplication should be added

---

## 8) Known operational edge-cases

1. OneBox `product/set` may return `400` for specific malformed/unsupported product payloads.
2. Temporary DNS/network failures can move receipts to `failed`; rerun must be dedup-safe.
3. Newly created BAF customers can arrive after receipt line; retry handles this.
