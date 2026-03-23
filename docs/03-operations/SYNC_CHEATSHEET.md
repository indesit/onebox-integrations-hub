# Sync Cheatsheet (for Anton + agents)

Last updated: 2026-03-22

## Quick status (today)

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

## List failed receipt numbers (today)

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

## Restart services (if config/code changed)

```bash
cd /root/projects/onebox-integrations-hub
docker compose restart hub worker
```

## Tail last sync logs

```bash
tail -n 80 /root/projects/onebox-integrations-hub/data/baf_polling.log
```

## Safe manual retry of FAILED only (dedup-aware)

- Always check deal existence in OneBox by `name` before resend.
- If exists, mark local rows synced with existing `onebox_order_id`.
- Only then sync missing ones.

(Use the operational retry script kept in agent history; do not bulk resend all pending from old periods.)

## Guardrails

- Do not sync receipts without customer.
- Do not sync returns.
- Do not remove `ignored_backfill` policy.
- Keep 20-minute schedule; avoid creating parallel cron/worker duplicates.
