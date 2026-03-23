# Agent Runbook — onebox-integrations-hub

Last updated: 2026-03-23
Audience: internal agents/operators

## Mandatory principles

1. **No duplicate deals**
   - deal key = receipt number without `НФНФ-`
   - before create: check `order/get` by `name`

2. **No duplicate contacts**
   - dedup by normalized phone
   - use `contact/get` (`filter.phones`) first
   - then `contact/set` with `findbyArray: ["externalid", "phone"]`

3. **No anonymous CRM deals**
   - `customer_uuid = 00000000-0000-0000-0000-000000000000` (null UUID) → `ignored_anonymous`
   - `customer_uuid` exists but customer not in `dim_customers` yet → keep `pending` with `missing_customer_in_dim`, retry next cycle

4. **No returns in CRM**
   - if any line has `qty < 0` → `ignored_return`

5. **Correct amount transfer**
   - send line price as `line_amount / qty`

6. **Products sent as batch to OneBox**
   - `/api/v2/product/set/` accepts full `productsArray` in one request — confirmed with 18-item receipts
   - returns `dataArray` with OneBox product IDs in same order as input

7. **OneBox session token auto-refresh**
   - token is fetched via `token/get/` and cached in `OneBoxClient`
   - on 400 + "token in header not found" → auto-refresh and retry (implemented in `client.py`)

## Runtime sequence (every 20 min)

1. poll receipt lines from BAF
2. ETL stage → fact upsert (`pending`)
3. refresh customers/stores from BAF
4. run onebox sync batch

## Periodic jobs (RQ 2.x scheduler)

### Як це працює

**RQ (Redis Queue)** — черга задач на базі Redis. Worker (`onebox-integrations-hub-worker-1`) постійно слухає чергу і виконує jobs.

**RQ scheduler** (вбудований в RQ 2.x, запускається через `rq worker --with-scheduler`) — окремий thread всередині worker-процесу, який у потрібний момент переміщує заплановані jobs з `ScheduledJobRegistry` → в основну чергу → worker їх виконує.

**Реєстрація jobs** відбувається через `src/scheduler/periodic.py`:
- при старті воркера (docker-compose команда: `python -m src.scheduler.periodic && rq worker --with-scheduler default`)
- або вручну: `docker compose exec hub python -m src.scheduler.periodic`

**Важливо:** jobs зберігаються в Redis. Якщо Redis скинути (`redis-cli FLUSHALL`) або воркер перезапустити без `periodic.py` — jobs зникнуть і синхронізація зупиниться. `periodic.py` при кожному запуску спочатку скасовує старі jobs, потім реєструє нові (ідемпотентно).

**Crontab для OneBox не використовується** — весь розклад через RQ worker. Глобальний crontab містить тільки certbot та інструменти моніторингу.

### Розклад jobs

| Job | Інтервал | Що робить |
|-----|----------|-----------|
| `baf_polling.BafPollingWorker.run_polling` | кожні **20 хв** | Poll BAF → ETL → refresh customers → sync pending → OneBox |
| `catalog_then_stock_sync.run_catalog_then_stock` | кожні **4 год** | Оновлює каталог товарів (33k+ SKU) → залишки на складах |
| `bot.digest.send_daily_digest` | щодня **09:00 Kyiv** | Telegram дайджест: продажі, синхронізація, статус |

### Перевірити стан jobs

```bash
# Активні scheduled jobs
docker compose exec hub python -c "
from rq.job import Job; from src.core.queue import get_queue
from datetime import datetime, timezone
q = get_queue('default'); conn = q.connection
for jid in q.scheduled_job_registry.get_job_ids():
    j = Job.fetch(jid, connection=conn)
    score = conn.zscore(q.scheduled_job_registry.key, jid)
    t = datetime.fromtimestamp(float(score), tz=timezone.utc).strftime('%d.%m %H:%M UTC')
    print(j.func_name.split('.')[-1], '->', t)
"
```

### Примусова перереєстрація (якщо jobs зникли)

```bash
docker compose exec hub python -m src.scheduler.periodic
```

## Status semantics

- `pending` — waiting to sync
- `processing` — currently being synced
- `synced` — sent to OneBox successfully
- `failed` — hard error (API/network/product validation)
- `ignored_anonymous` — null customer UUID (no loyalty card)
- `ignored_return` — return receipt (qty < 0)
- `ignored_backfill` — historical receipt manually skipped

## If sync fails

1. Check worker logs:
   ```bash
   docker logs onebox-integrations-hub-worker-1 --tail=50
   ```
2. Check status in DB (via bot: ⚙️ → 📊 Статус черги)
3. If token expired: worker auto-retries. If persists → `docker compose restart worker`
4. If `failed` receipts: check `sync_error` field, fix root cause, then:
   ```sql
   UPDATE fact_sales_receipt_items SET onebox_status='pending', sync_error=NULL WHERE onebox_status='failed';
   ```
5. Never mass-resend old data ranges without explicit user approval.

## Common failure patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `token in header not found` (400) | Session token expired | Auto-retried by client; if loop — restart worker |
| `400 Bad Request` on `product/set` | Malformed articul or missing field | Check articul value in `dim_product_variants`; batch itself is fine |
| `missing_customer_in_dim` | Customer not yet in dim after receipt | Normal: retried next cycle |
| `Request URL is missing http/https` | Bad `.env` ONEBOX_URL | Fix `.env`, restart hub/worker |
| `Temporary failure in name resolution` | DNS/network issue | Transient, auto-retry |

## Documentation source of truth

- Architecture (current): `docs/01-architecture/ARCHITECTURE_CURRENT.md`
- Bot guide: `docs/03-operations/BOT_GUIDE.md`
- Operations shortcuts: `docs/03-operations/SYNC_CHEATSHEET.md`
- ADR log: `docs/DECISIONS.md`
