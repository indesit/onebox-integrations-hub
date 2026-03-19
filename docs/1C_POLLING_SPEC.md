# Специфікація інтеграції 1С/BAF (Polling API)

Хаб інтеграцій опитує 4 HTTP-ендпоінти, підняті на боці 1С/BAF. 

## 1. /receipt_lines (Продажі по рядках чеків)
Повертає продажі з розбиттям по рядках чеків.
**Ключові поля:**
- `receipt_uuid`, `receipt_number`, `receipt_datetime`, `receipt_posted`, `receipt_deleted`, `receipt_total_amount`
- `store_uuid`, `customer_uuid`, `loyalty_card_uuid`
- `line_no`, `product_uuid`, `characteristic_uuid`, `qty`, `price`, `line_amount`

## 2. /product_catalog (Каталог товарів і характеристик)
Повертає довідник товарів та їхніх характеристик (розмірів/кольорів).
**Ключові поля:**
- `product_uuid`, `product_name`, `article`
- `characteristic_uuid`, `characteristic_name`

## 3. /stores (Список бойових магазинів)
Повертає актуальні точки продажу для прив'язки чеків до відповідних воронок/полів у OneBox.
**Формат відповіді:**
```json
{
  "success": true,
  "generated_at": "2026-03-13T00:22:47",
  "count": 6,
  "rows": [
    {
      "store_uuid": "22556c4a-816a-11ef-ac0e-00155dd273c8",
      "store_name": "Corner River"
    }
  ]
}
```

## 4. /customers (Список клієнтів з телефонами)
Повертає довідник контрагентів. Дублікати прибрані через групування по контрагенту.
**Формат відповіді:**
```json
{
  "success": true,
  "generated_at": "2026-03-13T00:22:47",
  "count": 2,
  "rows": [
    {
      "customer_uuid": "f8b70b25-e82b-11ed-abee-00155d79fd88",
      "customer_name": "Довбищенко Алиса",
      "customer_phone": "380502317543"
    }
  ]
}
```
