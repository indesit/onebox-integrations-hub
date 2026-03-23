"""Telegram bot command handlers."""

import re
import httpx
from datetime import datetime, date, timedelta
from sqlmodel import Session, text
from src.core.database import engine
from src.adapters.onebox.client import OneBoxClient
from src.config.settings import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

BAF_URL = "http://91.202.6.56/SecretShopBAS/hs/reports"


def normalize_phone(phone: str) -> str | None:
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if len(digits) == 12 and digits.startswith("380"):
        return digits
    if len(digits) == 10 and digits.startswith("0"):
        return f"38{digits}"
    if len(digits) == 11 and digits.startswith("80"):
        return f"3{digits}"
    if len(digits) == 9:
        return f"380{digits}"
    return digits


def get_baf_customer(phone_norm: str) -> dict | None:
    try:
        res = httpx.get(f"{BAF_URL}/customers",
                        auth=(settings.baf_user, settings.baf_password), timeout=30)
        for r in res.json().get("rows", []):
            raw = str(r.get("customer_phone") or "")
            if normalize_phone(raw) == phone_norm:
                return r
    except Exception as e:
        logger.error("baf_lookup_failed", error=str(e))
    return None


def cmd_status(_args: str) -> str:
    with Session(engine) as session:
        rows = session.exec(text("""
            SELECT onebox_status, COUNT(*) as cnt
            FROM fact_sales_receipt_items
            GROUP BY onebox_status
            ORDER BY cnt DESC
        """)).all()

        last_sync = session.exec(text("""
            SELECT MAX(onebox_synced_at) FROM fact_sales_receipt_items
            WHERE onebox_status = 'synced'
        """)).first()

        last_activity = session.exec(text("""
            SELECT MAX(updated_at) FROM fact_sales_receipt_items
        """)).first()

    lines = ["📊 Статус черги синхронізації\n"]
    for status, cnt in rows:
        emoji = {"synced": "✅", "pending": "⏳", "failed": "❌",
                 "processing": "🔄", "ignored_return": "↩️",
                 "ignored_anonymous": "👤"}.get(status, "•")
        lines.append(f"{emoji} {status}: {cnt}")

    if last_sync and last_sync[0]:
        lines.append(f"\n🕐 Останній sync в OneBox: {last_sync[0].strftime('%d.%m %H:%M')}")
    if last_activity and last_activity[0]:
        lines.append(f"🔄 Активність воркера: {last_activity[0].strftime('%d.%m %H:%M')}")

    return "\n".join(lines)


def cmd_failed(_args: str) -> str:
    with Session(engine) as session:
        rows = session.exec(text("""
            SELECT receipt_number, sync_error, updated_at
            FROM fact_sales_receipt_items
            WHERE onebox_status = 'failed'
            ORDER BY updated_at DESC
            LIMIT 10
        """)).all()

    if not rows:
        return "✅ Немає failed записів"

    lines = [f"❌ Останні failed ({len(rows)})\n"]
    for receipt, error, updated in rows:
        # Truncate error, strip URLs and special chars that break Markdown
        err_short = (error or "")[:80].split("'https://")[0].strip(" [\"")
        lines.append(f"• {receipt} — {err_short}")
    return "\n".join(lines)


def cmd_customer(args: str) -> str:
    phone_raw = args.strip()
    if not phone_raw:
        return "Використання: /customer 380XXXXXXXXX"

    phone = normalize_phone(phone_raw)
    if not phone:
        return f"Не вдалось нормалізувати номер: {phone_raw}"

    with Session(engine) as session:
        # Main customer record (pick the one with most purchases)
        dim_rows = session.exec(text(f"""
            SELECT dc.customer_name, dc.birth_date, dc.onebox_contact_id,
                   dc.first_seen_at, dc.last_seen_at, dc.customer_uuid
            FROM dim_customers dc
            WHERE dc.customer_phone_norm = '{phone}'
            ORDER BY (SELECT COUNT(*) FROM fact_sales_receipt_items f
                      WHERE f.customer_uuid = dc.customer_uuid) DESC
            LIMIT 1
        """)).first()

        # Purchase stats (avg_check = total per receipt, averaged)
        stats = session.exec(text(f"""
            WITH per_receipt AS (
                SELECT f.receipt_uuid,
                       MIN(f.receipt_datetime) AS dt,
                       SUM(f.line_amount) AS receipt_sum
                FROM fact_sales_receipt_items f
                JOIN dim_customers dc ON dc.customer_uuid = f.customer_uuid
                WHERE dc.customer_phone_norm = '{phone}'
                  AND f.onebox_status NOT IN ('ignored_return', 'ignored_anonymous')
                GROUP BY f.receipt_uuid
            )
            SELECT
                COUNT(*) AS receipts,
                SUM(receipt_sum) AS total,
                AVG(receipt_sum) AS avg_check,
                MIN(dt) AS first_dt,
                MAX(dt) AS last_dt,
                COUNT(*) FILTER (WHERE dt >= NOW() - INTERVAL '30 days') AS receipts_30d,
                SUM(receipt_sum) FILTER (WHERE dt >= NOW() - INTERVAL '30 days') AS total_30d
            FROM per_receipt
        """)).first()

        # Stores breakdown
        store_rows = session.exec(text(f"""
            SELECT COALESCE(s.store_name, '?') AS store,
                   COUNT(DISTINCT f.receipt_uuid) AS cnt
            FROM fact_sales_receipt_items f
            JOIN dim_customers dc ON dc.customer_uuid = f.customer_uuid
            LEFT JOIN dim_stores s ON s.store_uuid = f.store_uuid
            WHERE dc.customer_phone_norm = '{phone}'
              AND f.onebox_status NOT IN ('ignored_return', 'ignored_anonymous')
            GROUP BY s.store_name ORDER BY cnt DESC LIMIT 5
        """)).all()

        # Last 5 receipts
        last_receipts = session.exec(text(f"""
            SELECT DATE(f.receipt_datetime) AS dt,
                   COALESCE(s.store_name, '?') AS store,
                   SUM(f.line_amount) AS amt
            FROM fact_sales_receipt_items f
            JOIN dim_customers dc ON dc.customer_uuid = f.customer_uuid
            LEFT JOIN dim_stores s ON s.store_uuid = f.store_uuid
            WHERE dc.customer_phone_norm = '{phone}'
              AND f.onebox_status NOT IN ('ignored_return', 'ignored_anonymous')
            GROUP BY DATE(f.receipt_datetime), s.store_name
            ORDER BY dt DESC LIMIT 5
        """)).all()

    lines = [f"🔍 Клієнт {phone}\n"]

    # Identity block
    if dim_rows:
        name, bdate, ob_id, _, _, _ = dim_rows
        bdate_str = bdate.strftime('%d.%m.%Y') if bdate else "—"
        lines.append(f"👤 {name}")
        lines.append(f"   ДН: {bdate_str} | OneBox id: {ob_id or '—'}")
    else:
        lines.append("👤 Клієнта не знайдено в БД")

    # Stats block
    if stats and stats[0]:
        receipts, total, avg_check, first_dt, last_dt, r30, t30 = stats
        total_fmt = f"{float(total or 0):,.0f}".replace(",", "\u00a0")
        avg_fmt = f"{float(avg_check or 0):,.0f}".replace(",", "\u00a0")
        if first_dt:
            lines.append(f"   Перший візит: {first_dt.strftime('%d.%m.%Y')} "
                         f"| Останній: {last_dt.strftime('%d.%m.%Y')}")
        lines.append(f"\n💰 Статистика покупок:")
        lines.append(f"   Чеків: {receipts} | Сума: {total_fmt} грн")
        lines.append(f"   Середній чек: {avg_fmt} грн")
        if r30:
            t30_fmt = f"{float(t30 or 0):,.0f}".replace(",", "\u00a0")
            lines.append(f"   За 30 днів: {r30} чеків / {t30_fmt} грн")
    else:
        lines.append("\n💰 Покупок не знайдено")

    # Stores
    if store_rows:
        stores_str = ", ".join(f"{s} ({c})" for s, c in store_rows)
        lines.append(f"\n🏪 Магазини: {stores_str}")

    # Last receipts
    if last_receipts:
        lines.append("\n🧾 Останні покупки:")
        for dt, store, amt in last_receipts:
            amt_fmt = f"{float(amt or 0):,.0f}".replace(",", "\u00a0")
            lines.append(f"   • {dt.strftime('%d.%m.%y')} — {store} — {amt_fmt} грн")

    # OneBox live check
    try:
        client = OneBoxClient(domain=settings.onebox_url,
                              login=settings.onebox_login,
                              token=settings.onebox_api_key)
        res = client.get_contacts({"filter": {"phones": [phone]},
                                   "fields": ["id", "name", "namelast", "bdate"]})
        contacts = [c for c in (res.get("dataArray") or [])
                    if (c.get("name") or "").strip() != "restapi" and str(c.get("id")) != "1"]
        if contacts:
            c = contacts[0]
            bdate = c.get("bdate") or ""
            bdate_str = bdate if bdate and bdate != "0000-00-00" else "—"
            lines.append(f"\n📱 OneBox: {c.get('namelast')} {c.get('name')}, "
                         f"id={c.get('id')}, bdate={bdate_str}")
        else:
            lines.append("\n📱 OneBox: не знайдено")
    except Exception as e:
        lines.append(f"\n📱 OneBox: помилка ({e})")

    return "\n".join(lines)


def cmd_fix_bdate(args: str) -> str:
    phone_raw = args.strip()
    if not phone_raw:
        return "Використання: /fix_bdate 380XXXXXXXXX"

    phone = normalize_phone(phone_raw)
    if not phone:
        return f"Не вдалось нормалізувати номер: {phone_raw}"

    # Get birth_date from BAF
    baf = get_baf_customer(phone)
    if not baf:
        return f"❌ Клієнт {phone} не знайдений в BAF"

    bdate_str = baf.get("birth_date")
    if not bdate_str:
        return f"❌ В BAF немає дати народження для {baf.get('customer_name')} ({phone})"

    # Find in OneBox
    try:
        client = OneBoxClient(domain=settings.onebox_url,
                              login=settings.onebox_login,
                              token=settings.onebox_api_key)
        res = client.get_contacts({"filter": {"phones": [phone]},
                                   "fields": ["id", "name", "namelast", "bdate"]})
        contacts = [c for c in (res.get("dataArray") or [])
                    if (c.get("name") or "").strip() != "restapi" and str(c.get("id")) != "1"]

        if not contacts:
            return f"❌ Клієнт {phone} не знайдений в OneBox"

        c = contacts[0]
        onebox_id = c.get("id")
        existing = (c.get("bdate") or "").strip()

        if existing and existing != "0000-00-00":
            return (f"⚠️ {c.get('namelast')} {c.get('name')} (id={onebox_id}) "
                    f"вже має bdate={existing}, не оновлюю")

        upd = client._post_with_retry("contact/set/", [{"userid": int(onebox_id), "bdate": bdate_str}])
        if upd.get("status") == 1:
            return (f"✅ {baf.get('customer_name')} (OneBox id={onebox_id}) "
                    f"— bdate={bdate_str} оновлено")
        else:
            return f"❌ Помилка OneBox API: {upd.get('errorArray')}"

    except Exception as e:
        return f"❌ Помилка: {e}"


def cmd_sales(period: str = "yesterday") -> str:
    today = date.today()
    target = today if period == "today" else today - timedelta(days=1)
    label = "сьогодні" if period == "today" else target.strftime('%d.%m.%Y')

    with Session(engine) as session:
        rows = session.exec(text(f"""
            SELECT
                COALESCE(s.store_name, 'Невідомий магазин') AS store_name,
                COUNT(DISTINCT f.receipt_uuid) AS receipts,
                SUM(f.line_amount) AS revenue
            FROM fact_sales_receipt_items f
            LEFT JOIN dim_stores s ON s.store_uuid = f.store_uuid
            WHERE DATE(f.receipt_datetime) = '{target}'
              AND f.onebox_status != 'ignored_return'
            GROUP BY s.store_name
            ORDER BY revenue DESC NULLS LAST
        """)).all()

        total_row = session.exec(text(f"""
            SELECT
                COUNT(DISTINCT receipt_uuid),
                SUM(line_amount)
            FROM fact_sales_receipt_items
            WHERE DATE(receipt_datetime) = '{target}'
              AND onebox_status != 'ignored_return'
        """)).first()

    if not rows:
        return f"📭 Продажів за {label} не знайдено."

    lines = [f"📈 *Продажі за {label}*\n"]
    for store, receipts, revenue in rows:
        rev_fmt = f"{float(revenue or 0):,.0f}".replace(",", "\u00a0")
        lines.append(f"🏪 {store}: {receipts} чеків / *{rev_fmt} грн*")

    if total_row:
        total_receipts, total_rev = total_row
        rev_fmt = f"{float(total_rev or 0):,.0f}".replace(",", "\u00a0")
        lines.append(f"\n📊 Разом: {total_receipts} чеків / *{rev_fmt} грн*")

    return "\n".join(lines)


def cmd_backfill_status(_args: str) -> str:
    with Session(engine) as session:
        total_with_bdate = session.exec(text("""
            SELECT COUNT(*) FROM dim_customers WHERE birth_date IS NOT NULL
        """)).first()

        synced_with_bdate = session.exec(text("""
            SELECT COUNT(DISTINCT dc.customer_uuid)
            FROM dim_customers dc
            JOIN fact_sales_receipt_items f ON f.customer_uuid = dc.customer_uuid
            WHERE dc.birth_date IS NOT NULL
              AND f.onebox_status = 'synced'
        """)).first()

        missing_bdate_in_onebox = session.exec(text("""
            SELECT COUNT(DISTINCT dc.customer_uuid)
            FROM dim_customers dc
            JOIN fact_sales_receipt_items f ON f.customer_uuid = dc.customer_uuid
            WHERE dc.birth_date IS NOT NULL
              AND dc.onebox_contact_id IS NOT NULL
              AND (dc.onebox_synced_at IS NULL OR dc.birth_date IS NOT NULL)
              AND f.onebox_status = 'synced'
        """)).first()

    total = total_with_bdate[0] if total_with_bdate else 0
    synced = synced_with_bdate[0] if synced_with_bdate else 0

    lines = [
        "🔄 *Синхронізація дат народження*\n",
        f"📋 Клієнтів з ДН в БД: {total}",
        f"🔗 З них синхронізованих з OneBox: {synced}",
        f"⏳ Без синхронізації: {total - synced}",
    ]
    return "\n".join(lines)


def cmd_digest(_args: str) -> str:
    today = date.today()
    yesterday = today - timedelta(days=1)

    with Session(engine) as session:
        # Synced yesterday
        synced = session.exec(text(f"""
            SELECT COUNT(DISTINCT receipt_uuid)
            FROM fact_sales_receipt_items
            WHERE onebox_status = 'synced'
              AND onebox_synced_at >= '{yesterday}' AND onebox_synced_at < '{today}'
        """)).first()

        # New customers yesterday
        new_customers = session.exec(text(f"""
            SELECT COUNT(*) FROM dim_customers
            WHERE DATE(first_seen_at) = '{yesterday}'
        """)).first()

        # Pending + failed
        queue = session.exec(text("""
            SELECT onebox_status, COUNT(*)
            FROM fact_sales_receipt_items
            WHERE onebox_status IN ('pending', 'failed')
            GROUP BY onebox_status
        """)).all()

    pending = next((cnt for s, cnt in queue if s == "pending"), 0)
    failed = next((cnt for s, cnt in queue if s == "failed"), 0)

    lines = [
        f"📅 *Дайджест за {yesterday.strftime('%d.%m.%Y')}*\n",
        f"✅ Синхронізовано чеків: {synced[0] if synced else 0}",
        f"👤 Нових покупців: {new_customers[0] if new_customers else 0}",
        f"⏳ В черзі (pending): {pending}",
        f"❌ Помилок (failed): {failed}",
    ]
    return "\n".join(lines)


COMMANDS = {
    "/status": cmd_status,
    "/failed": cmd_failed,
    "/customer": cmd_customer,
    "/fix_bdate": cmd_fix_bdate,
    "/digest": cmd_digest,
    "/help": lambda _: (
        "🤖 *Команди бота*\n\n"
        "/status — стан черги синхронізації\n"
        "/failed — останні 10 failed чеків\n"
        "/customer 380XX — інфо про клієнта\n"
        "/fix\\_bdate 380XX — передати ДН з BAF в OneBox\n"
        "/digest — дайджест за вчора\n"
        "/help — це повідомлення"
    ),
}


def handle_message(text_in: str) -> str:
    text_in = text_in.strip()
    parts = text_in.split(None, 1)
    cmd = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    handler = COMMANDS.get(cmd)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            logger.error("bot_handler_error", cmd=cmd, error=str(e))
            return f"❌ Помилка виконання команди: {e}"

    return "Невідома команда. Напиши /help"
