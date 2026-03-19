# INTEGRATION_SPEC: 1C/BAF Stock Balance Polling

**Version:** 1.0  
**Date:** 2026-03-19  
**Status:** APPROVED  

## 1. Overview
Метод опитування (Polling) через HTTP-сервіс 1С для отримання поточних складських залишків. Використовується для синхронізації залишків у DWH та подальшого їх відображення в дашборді асортименту.

## 2. API Specification (1C Side)

### 2.1 Endpoint (Base URL)
`http://91.202.6.56/SecretShopBAS/hs/reports/stock_balance_now`

### 2.2 HTTP Method
**GET**

### 2.3 Query Parameters
Усі параметри є опціональними. Фільтри працюють незалежно та можуть комбінуватись.

- `limit` (int, optional): Обмежує кількість рядків у відповіді. Якщо не переданий - повертається весь масив.
- `warehouse` (string, optional): Фільтр по магазину (частковий збіг, через LIKE / ПОДОБНО). *Приклад: warehouse=River*
- `category` (string, optional): Фільтр по категорії товару (частковий збіг). *Приклад: category=Бюст*

### 2.4 Examples
- Отримати всі залишки: `/stock_balance_now`
- Отримати з лімітом: `/stock_balance_now?limit=100`
- Відфільтрувати по складу: `/stock_balance_now?warehouse=River`
- Відфільтрувати по категорії: `/stock_balance_now?category=Бюст`
- Комбінований запит: `/stock_balance_now?warehouse=River&category=Бюст&limit=100`

### 2.5 Notes
- При відсутності даних по заданим фільтрам повертається порожній масив `[]`.
