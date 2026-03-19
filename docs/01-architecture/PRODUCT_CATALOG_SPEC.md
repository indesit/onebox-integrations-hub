# INTEGRATION_SPEC: Product Catalog (Epic 7)

**Version:** 1.0  
**Date:** 2026-03-12  
**Status:** APPROVED  
**Author:** Integrations Hub Architect

---

## 1. Overview
Метод синхронізації повного каталогу товарів та їх характеристик з 1С (BAF) у PostgreSQL Хабу. Це критичне джерело даних для розшифровки чеків, побудови P&L та матриці продажів.

---

## 2. API Specification (1C Side)

### 2.1 Endpoint
`http://91.202.6.56/SecretShopBAS/hs/reports/product_catalog`

### 2.2 HTTP Method
**GET**

### 2.3 Response Structure (Flat JSON List)
Сервіс повертає масив варіантів товарів. Кожен рядок — це унікальна комбінація Товар + Характеристика.

```json
[
  {
    "product_ref": "ea72f709-988e-11eb-9a8d-ab685d981f3c",
    "product_name": "Атласна піжама з шортами Boxer PJ",
    "article": "406-058-QNF",
    "characteristic_ref": "UUID-CHAR-1",
    "characteristic_name": "L, В полоску"
  },
  {
    "product_ref": "ea72f709-988e-11eb-9a8d-ab685d981f3c",
    "product_name": "Атласна піжама з шортами Boxer PJ",
    "article": "406-058-QSD",
    "characteristic_ref": "UUID-CHAR-2",
    "characteristic_name": "L, цветочный принт"
  }
]
```

---

## 3. Data Processing Logic (Hub Side)

### 3.1 Mapping Rules
- **`product_ref`**: Зберігається як основний `external_id` для зв'язку з чеками.
- **`article` (SKU)**: Використовується для синхронізації з OneBox.
- **`characteristic_name`**: Хаб автоматично парсить це поле для виділення Розміру та Кольору (наприклад, "L" та "В полоску").

---

*Source: projects/onebox-integrations-hub/docs/01-architecture/PRODUCT_CATALOG_SPEC.md*
