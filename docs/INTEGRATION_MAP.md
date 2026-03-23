# INTEGRATION_MAP.md

Last updated: 2026-03-22
Scope: Relationship between `onebox-integrations-hub` and `retail-analytics-dashboard`

---

## 1) System roles

### onebox-integrations-hub (upstream / producer)
- Polls BAF/1C APIs
- Performs ETL and data normalization
- Maintains DWH-like operational tables in PostgreSQL (`onebox_hub`)
- Synchronizes eligible receipts to OneBox CRM

### retail-analytics-dashboard (downstream / consumer)
- Reads from PostgreSQL (`onebox_hub`) in read-only mode
- Builds KPI/reporting API + frontend dashboards
- Does **not** own ingestion/ETL logic

---

## 2) Data ownership boundary

- **Hub owns data ingestion + correctness at source level**:
  - dedup receipts/deals
  - customer linkage policy
  - return/anonymous filtering
  - amount calculation (`line_amount` semantics)
- **Dashboard owns analytics presentation**:
  - aggregation windows
  - filters/slices
  - UI/UX and report APIs

---

## 3) Shared database and key tables

Both projects use the same DB: `onebox_hub` (PostgreSQL on localhost:5432)

Primary shared tables:
- `fact_sales_receipt_items` (sales receipt facts)
- `dim_product_variants` (product attributes incl. `material`)
- `dim_stores`
- `dim_customers`

Staging/operational tables mostly owned by Hub:
- `stg_baf_receipt_lines`
- `stg_baf_customers`
- `stg_baf_stores`

---

## 4) End-to-end sequence

1. Hub (`baf_polling.py`) runs every 20 minutes
2. Hub fetches BAF `receipt_lines`
3. Hub stages + ETL upsert into `fact_sales_receipt_items`
4. Hub refreshes customers/stores dimensions
5. Hub syncs pending receipts to OneBox CRM
6. Dashboard backend reads from `onebox_hub` and serves BI endpoints
7. Dashboard frontend renders reports/matrices

---

## 5) Contracts that dashboard depends on

Dashboard logic assumes Hub semantics:
- `fact_sales_receipt_items` contains normalized facts
- `line_amount` reflects actual paid amount (discount-aware)
- returns and anonymous receipts are excluded from CRM sync path by Hub policy
- product attributes (including `material`) are provided through `dim_product_variants`

If these contracts change in Hub, dashboard queries and metrics may break or drift.

---

## 6) Integration risks (cross-project)

1. **Schema drift** in Hub tables -> dashboard SQL/API failures
2. **Semantic drift** (`price` vs `line_amount`) -> KPI mismatch
3. **Backfill without guardrails** -> historical metric corruption
4. **Duplicate sync processes** -> duplicate CRM deals and noisy data states
5. **Customer dictionary lag** -> temporary pending receipts before retry

---

## 7) Change management rules

When changing Hub ETL/sync logic:
1. Update Hub docs first:
   - `docs/01-architecture/ARCHITECTURE_CURRENT.md`
   - `docs/DECISIONS.md`
2. Validate dashboard SQL assumptions against updated fields
3. Smoke-test dashboard endpoints relying on:
   - `fact_sales_receipt_items`
   - `dim_product_variants`
4. Announce contract change in handoff notes

---

## 8) Quick verification checklist

- Hub status:
  - no critical sync errors in `data/baf_polling.log`
  - expected pending/failed counts for current date
- Dashboard status:
  - backend connects to `onebox_hub`
  - key report endpoints return consistent totals with Hub facts

---

## 9) Pointers

### Hub docs
- `README.md`
- `docs/01-architecture/ARCHITECTURE_CURRENT.md`
- `docs/03-operations/AGENT_RUNBOOK.md`
- `docs/03-operations/SYNC_CHEATSHEET.md`
- `docs/DECISIONS.md`

### Dashboard docs
- `docs/01-architecture/ARCHITECTURE.md`
- `docs/01-architecture/API_SPEC.md`
- `docs/01-architecture/ARCHITECTURE_OPTIMIZATION.md`
- `docs/00-brief/PROJECT_BRIEF.md`
