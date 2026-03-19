# BACKFILL & RETURNS SPECIFICATION

**Version:** 1.0  
**Date:** 2026-03-14  
**Status:** DRAFT / PENDING 1C UPDATES  
**Author:** Bony (Integrations Hub Assistant)

---

## 1. Overview
This document specifies the requirements for full historical data loading (Backfill) and the logic for handling returns/exchanges in the OneBox Integrations Hub.

---

## 2. Historical Data Backfill (Sales)

### 2.1 Scope
- **Start Date:** 2021-04-30
- **Entity:** All retail receipts (Sales + Returns).
- **Target:** `fact_sales_receipt_items` table in PostgreSQL.

### 2.2 Execution Strategy
- **Batch Size:** 14 days per request.
- **Throttling:** 2-second delay between batches to protect BAF server.
- **Idempotency:** Unique Constraint on `(receipt_uuid, line_no)` to prevent duplicates.

---

## 3. Returns & Exchanges Logic

### 3.1 Data Acquisition (BAF Side)
- **Endpoint:** `/receipt_lines`
- **Requirement:** Must include "Returns from Customer" documents.
- **Format:** Returns must be provided as separate lines with negative values:
  - `qty`: negative (e.g., -1)
  - `line_amount`: negative (e.g., -2500.00)

### 3.2 Storage (Hub Side)
- Returns are stored as independent records in `fact_sales_receipt_items`.
- This preserves the audit trail and P&L accuracy for specific dates.

### 3.3 Analytics Logic
- **Total Sales:** `SUM(qty)` and `SUM(line_amount)`.
- **Customer Holdings:** Group by `product_uuid` and `customer_uuid`, then `HAVING SUM(qty) > 0`.

---

## 4. Gift Cards & Payments Logic (Approved Contract)

### 4.1 Data Acquisition (BAF Side)
- **Endpoint:** `/receipt_lines`
- **Requirement:** Integrate mapping from `РегистрНакопления.ПодарочныеСертификаты`.
- **Field Contract (per line):**
```json
{
 "receipt_uuid": "uuid",
 "is_gift_certificate_sale": false,      // Приход в регистре
 "gift_certificate_sale_amount": 0,      // Сумма Прихода
 "has_certificate_payment": false,       // Расход в регистре
 "certificate_payment_amount": 0         // Сумма Расхода
}
```

### 4.2 Handling Logic in Hub
- **Exclusion Rule:** If `is_gift_certificate_sale == true`, this line amount is excluded from "Product Sales" reports but included in "Cash Flow" reports.
- **Payment Analysis:** If `has_certificate_payment == true`, the `certificate_payment_amount` is treated as a specific payment method (non-cash) for the receipt.

### 4.3 Storage (Hub Side)
- Update `FactSalesReportItem` to include these 4 fields.
- Update `FactStockBalance` to ensure gift card sales don't trigger stock warnings.

---

## 5. Technical Dependencies (1C/BAF Updates)
To proceed with the plan, the following 1C HTTP Service updates are required:
1. **Field Enrichment:** Add `color` field to `/product_catalog` response.
2. **Limit Removal:** Remove the 200-item limit from `/stock_balance_now` and `/receipt_lines`.
3. **Returns Inclusion:** Ensure `/receipt_lines` exports return documents with negative values.
4. **Payment Enrichment:** Add payment types and gift card markers to `/receipt_lines`.

---
*Source of Truth: projects/onebox-integrations-hub/docs/01-architecture/BACKFILL_RETURNS_SPEC.md*
