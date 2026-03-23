"""Cash balance handler — fetches register balances from BAF."""

from datetime import datetime

import httpx
from src.config.settings import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

BAF_CASH_URL = "http://91.202.6.56/SecretShopBAS/hs/reports/cash_balance_now"


def get_cash_balance() -> str:
    """Fetch cash register balances from BAF and return formatted message."""
    try:
        res = httpx.get(
            BAF_CASH_URL,
            auth=(settings.baf_user, settings.baf_password),
            timeout=20,
        )
        res.raise_for_status()
        data = res.json()
    except httpx.TimeoutException:
        return "⏳ Сервер 1С відповідає занадто довго (таймаут)."
    except Exception as e:
        logger.error("cash_balance_fetch_failed", error=str(e))
        return f"❌ Помилка при отриманні звіту: {e}"

    if isinstance(data, dict):
        if "success" in data and not data.get("success"):
            return "❌ Не вдалося отримати звіт по касах."
        rows = data.get("rows", [])
    else:
        rows = data

    return _format(rows)


def _format(rows: list) -> str:
    if not rows:
        return "📭 По касах зараз немає даних."

    valid = [r for r in rows if r.get("cashdesk")]
    valid.sort(key=lambda x: str(x.get("cashdesk", "")))

    lines = ["🏦 <b>Залишок грошей в касах</b>\n"]
    total = 0.0

    for row in valid:
        cashdesk = str(row.get("cashdesk", "-")).strip()
        amount = float(row.get("amount", 0) or 0)
        if amount == 0:
            continue
        total += amount
        amount_fmt = f"{amount:,.2f}".replace(",", "\u00a0")
        lines.append(f"💵 {cashdesk} — <b>{amount_fmt} грн.</b>")

    if len(lines) == 1:
        return "💨 Всі каси порожні (нульові залишки)."

    total_fmt = f"{total:,.2f}".replace(",", "\u00a0")
    lines.append("")
    lines.append(f"📈 <b>Разом — {total_fmt} грн.</b>")
    lines.append(f"🔄 Оновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    return "\n".join(lines)
