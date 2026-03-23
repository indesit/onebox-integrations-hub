# onebox-integrations-hub — How to Operate (1-page)

Last updated: 2026-03-23

## Cross-project map

- Integration map (Hub ↔ Dashboard): `docs/INTEGRATION_MAP.md`

## What this service does

Synchronizes **BAF (1C) receipts** to **OneBox CRM deals** with safeguards:
- no duplicate deals (by receipt number)
- no duplicate contacts (by phone)
- no anonymous deals
- no return receipts in CRM
- deal sums match paid amount (discount-aware)

---

## Runtime flow (every 20 minutes)

1. Poll BAF receipt lines
2. Stage + ETL into DB
3. Refresh customers/stores from BAF
4. Sync pending receipts to OneBox

Single cycle is driven by `baf_polling.py` (no extra parallel schedulers required).

---

## Key scripts

- `src/scheduler/baf_polling.py` — polling entrypoint (BAF -> ETL -> customers sync -> onebox sync)
- `src/scheduler/onebox_sync.py` — sends deals to OneBox
- `src/scheduler/stores_customers_sync.py` — refreshes `dim_customers` / `dim_stores`
- `src/core/etl.py` — staging + fact upsert
- `src/adapters/onebox/client.py` — OneBox API v2 client

---

## Key DB tables

- `stg_baf_receipt_lines` — raw staged BAF lines
- `fact_sales_receipt_items` — main sync fact table
- `dim_customers` — customer dictionary
- `dim_stores` — store dictionary
- `stg_baf_customers`, `stg_baf_stores` — staging dictionaries

Important fields in `fact_sales_receipt_items`:
- `onebox_status` (`pending|synced|failed|ignored_return|ignored_anonymous|ignored_backfill`)
- `onebox_order_id`
- `sync_error`
- `onebox_synced_at`

---

## Critical business rules

1. **Deal key:** OneBox deal name = receipt number without `НФНФ-`.
2. **Contact dedup:** by normalized phone (`contact/get` -> `contact/set`).
3. **Price transfer:** use `line_amount / qty` (not base `price`).
4. **Do not sync:**
   - returns (`qty < 0`) -> `ignored_return`
   - receipts without customer -> `ignored_anonymous`
5. If receipt has `customer_uuid` but customer not in `dim_customers` yet:
   - keep `pending`
   - set `sync_error=missing_customer_in_dim`
   - retry next cycle (after customer refresh)

---

## Operations quick commands

### 1) Current status (today)

```bash
cd /root/projects/onebox-integrations-hub && export PYTHONPATH=.
python3 - <<'PY'
from sqlmodel import Session, text
from src.core.database import engine
with Session(engine) as s:
    print('last_synced:', s.execute(text("SELECT max(onebox_synced_at) FROM fact_sales_receipt_items WHERE onebox_status='synced'" )).scalar())
    print('pending:', s.execute(text("SELECT count(DISTINCT receipt_uuid) FROM fact_sales_receipt_items WHERE (receipt_datetime AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Kyiv')::date=current_date AND onebox_status='pending' AND customer_uuid IS NOT NULL")).scalar())
    print('failed:', s.execute(text("SELECT count(DISTINCT receipt_uuid) FROM fact_sales_receipt_items WHERE (receipt_datetime AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Kyiv')::date=current_date AND onebox_status='failed' AND customer_uuid IS NOT NULL")).scalar())
PY
```

### 2) List failed receipt numbers (today)

```bash
cd /root/projects/onebox-integrations-hub && export PYTHONPATH=.
python3 - <<'PY'
from sqlmodel import Session, text
from src.core.database import engine
with Session(engine) as s:
    q=text("""
      SELECT DISTINCT receipt_number
      FROM fact_sales_receipt_items
      WHERE (receipt_datetime AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Kyiv')::date=current_date
        AND onebox_status='failed' AND customer_uuid IS NOT NULL
      ORDER BY receipt_number
    """)
    for (n,) in s.execute(q).all():
        print(n.replace('НФНФ-',''))
PY
```

### 3) Restart app containers (after config/code changes)

```bash
cd /root/projects/onebox-integrations-hub
docker compose restart hub worker
```

### 4) Tail logs

```bash
tail -n 120 /root/projects/onebox-integrations-hub/data/baf_polling.log
```

---

## Troubleshooting map

- `Request URL is missing http/https`
  - check `.env` and `settings.onebox_url` composition
  - restart `hub/worker`

- `Temporary failure in name resolution`
  - transient DNS/network issue
  - retry failed receipts later (dedup-safe)

- `400 Bad Request` on `product/set`
  - malformed or unsupported product payload/SKU
  - inspect failing receipt payload and product fields

---

## Telegram Bot

Бот для оперативного моніторингу та роботи з клієнтами. Запускається як окремий сервіс `bot` в docker-compose.

### Ролі та доступ

| Роль | Команди |
|------|---------|
| `owner` | всі команди + /cash, /sales, /backfill_status, /users |
| `admin` | /status, /failed, /fix_bdate, /digest, /customer |
| `user` | /customer, /help |

Ролі налаштовуються в `config/roles.yml` (live-reload, без рестарту):

```yaml
owner:
  - "+380XXXXXXXXX"
admin:
  - "+380XXXXXXXXX"
user: []
```

### Кнопкове меню (owner)

```
[ 💰 Залишок грошей в касах ]
[ 📈 Продажі ]  [ 👤 Покупець ]
[ ⚙️ Технічний стан ]  [ ℹ️ Допомога ]
```

- **💰 Залишок** — баланс кас з 1С в реальному часі
- **📈 Продажі** → inline-кнопки Вчора / Сьогодні → виторг по магазинах
- **👤 Покупець** → ForceReply запит номера → повна картка клієнта
- **⚙️ Технічний стан** → inline-меню: Статус черги / Failed чеки / Дайджест / Синхронізація ДН / Покупець

### Картка покупця (/customer або кнопка)

Показує:
- ПІБ, дата народження, OneBox id
- Перший / останній візит
- Кількість чеків, сума, середній чек
- Розбивка по магазинах
- Останні 5 покупок з датою та магазином
- Статус в OneBox (live-запит)

### Авторизація

1. `/start` → кнопка "📱 Надіслати номер телефону"
2. Бот нормалізує номер до `+380XXXXXXXXX`
3. Перевіряє `config/roles.yml`
4. Зберігає роль у `data/bot_users.json`

### Ключові файли бота

- `src/bot/bot.py` — aiogram 3 dispatcher, хендлери, FSM
- `src/bot/handlers.py` — синхронні обробники команд (DB queries)
- `src/bot/roles.py` — авторизація, RBAC
- `src/bot/cash.py` — запит балансу кас з 1С
- `config/roles.yml` — whitelist телефонів по ролях
- `data/bot_users.json` — збережені авторизовані юзери

---

## Canonical docs

- Current architecture: `docs/01-architecture/ARCHITECTURE_CURRENT.md`
- Bot & operations: `docs/03-operations/BOT_GUIDE.md`
- Agent runbook: `docs/03-operations/AGENT_RUNBOOK.md`
- Ops cheatsheet: `docs/03-operations/SYNC_CHEATSHEET.md`
- ADR history: `docs/DECISIONS.md`
