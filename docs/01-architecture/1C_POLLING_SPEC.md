# INTEGRATION_SPEC: 1C/BAF Polling (Epic 7)

**Version:** 1.1  
**Date:** 2026-03-12  
**Status:** APPROVED  
**Author:** Integrations Hub Architect

---

## 1. Overview
Метод опитування (Polling) через HTTP-сервіс 1С УНФ 1.6. Хаб самостійно ініціює запит до 1С за розкладом, забирає нові чеки та зберігає їх у PostgreSQL. 
**Особливість:** Дані передаються у вигляді "плоского" списку рядків чеків (Receipt Lines).

---

## 2. API Specification (1C Side)

### 2.1 Endpoint (Base URL)
`http://91.202.6.56/SecretShopBAS/hs/reports/receipt_lines`

### 2.2 HTTP Method
**GET**

### 2.3 Query Parameters
- `date_from`: Дата начала (Формат: `YYYY-MM-DD`)
- `date_to`: Дата конца (Формат: `YYYY-MM-DD`)

### 2.4 Response Structure (Flat JSON List)
Сервіс повертає масив об'єктів, де кожен об'єкт — це один рядок чека. Хаб самостійно групує їх за `receipt_uuid`.

```json
[
  {
    "receipt_uuid": "87d63e2c-1631-11f1-abf4-00155dd273c8",
    "receipt_number": "НФНФ-W04517",
    "receipt_datetime": "2026-03-02T14:19:24",
    "receipt_posted": true,
    "receipt_deleted": false,
    "receipt_total_amount": 1496,
    "store_uuid": "59d7e37d-057d-11eb-bddc-f832e4bad26c",
    "customer_uuid": "1603b2d1-eeb1-11ee-abff-00155dd273c8",
    "loyalty_card_uuid": "1603b2d2-eeb1-11ee-abff-00155dd273c8",
    "line_no": 1,
    "product_uuid": "ea72f709-988e-11eb-9a8d-ab685d981f3c",
    "characteristic_uuid": "00000000-0000-0000-0000-000000000000",
    "qty": 1,
    "price": 990,
    "line_amount": 748
  },
  {
    "receipt_uuid": "87d63e2c-1631-11f1-abf4-00155dd273c8",
    "receipt_number": "НФНФ-W04517",
    "receipt_datetime": "2026-03-02T14:19:24",
    "receipt_posted": true,
    "receipt_deleted": false,
    "receipt_total_amount": 1496,
    "store_uuid": "59d7e37d-057d-11eb-bddc-f832e4bad26c",
    "customer_uuid": "1603b2d1-eeb1-11ee-abff-00155dd273c8",
    "loyalty_card_uuid": "1603b2d2-eeb1-11ee-abff-00155dd273c8",
    "line_no": 2,
    "product_uuid": "701c3c24-47a6-11ec-be1d-f832e4bad26c",
    "characteristic_uuid": "00000000-0000-0000-0000-000000000000",
    "qty": 1,
    "price": 990,
    "line_amount": 748
  }
]
```

---

*Source: projects/onebox-integrations-hub/docs/01-architecture/1C_POLLING_SPEC.md*
