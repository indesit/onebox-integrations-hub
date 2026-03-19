# receipt_lines v2.0 - Technical Contract (Sales & Returns)

**Version:** 2.0  
**Date:** 2026-03-14  
**Source:** BAF (1C) -> Integrations Hub (DWH)  
**Status:** APPROVED

---

## 1. Endpoint Details
- **Path:** `/hs/reports/receipt_lines`
- **Method:** GET
- **Parameters:**
  - `date_from` (YYYY-MM-DD): Start of the period (inclusive).
  - `date_to` (YYYY-MM-DD): End of the period (inclusive).

---

## 2. Response Structure
The endpoint returns a JSON object with metadata and a `rows` array.

```json
{
 "success": true,
 "generated_at": "2026-03-14T18:00:00",
 "count": 2,
 "rows": [
   {
     "receipt_uuid": "uuid",
     "receipt_number": "string",
     "receipt_datetime": "YYYY-MM-DDTHH:MM:SS",
     "line_no": 1,
     "store_uuid": "uuid",
     "customer_uuid": "uuid",
     "product_uuid": "uuid",
     "characteristic_uuid": "uuid",
     "qty": 1,
     "price": 2500,
     "amount": 2500,
     "is_gift_certificate_sale": false,
     "gift_certificate_sale_amount": 0,
     "has_certificate_payment": false,
     "certificate_payment_amount": 0
   }
 ]
}
```

---

## 3. Data Logic & Source Mapping

### 3.1 Sales (Продажі)
- **Source:** `Документ.ЧекККМ`, tabular part `Запасы`.
- **Values:** `qty` > 0, `amount` > 0.

### 3.2 Returns (Повернення)
- **Source:** `Документ.ЧекККМВозврат`, tabular part `Запасы`.
- **Transformation:** 
  - `qty` = `Value * -1` (negative)
  - `amount` = `Value * -1` (negative)
  - `price` = stays positive.

### 3.3 Gift Certificates (Сертифікати)
- **Source:** `РегистрНакопления.ПодарочныеСертификаты`
- **Mapping:**
  - `is_gift_certificate_sale`: TRUE if `ВидДвижения == Приход`.
  - `gift_certificate_sale_amount`: Total sum of `Приход` movements for this receipt.
  - `has_certificate_payment`: TRUE if `ВидДвижения == Расход`.
  - `certificate_payment_amount`: Total sum of `Расход` movements for this receipt.
- **Note:** These fields are duplicated for every line of the same receipt.

---

## 4. Test Scenarios (Post-Implementation)
1. **Regular Sale:** No certificate flags, positive qty/amount.
2. **Gift Card Sale:** `is_gift_certificate_sale = true`, positive amount.
3. **Gift Card Payment:** `has_certificate_payment = true`, positive product qty, payment amount captured.
4. **Return:** Negative qty/amount, correctly identifying the return document.

---
*Source of Truth: projects/onebox-integrations-hub/docs/01-architecture/RECEIPT_LINES_V2_CONTRACT.md*
