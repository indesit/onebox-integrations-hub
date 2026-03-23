"""Telegram bot — aiogram 3.x long-polling with role-based access control.

Roles are defined in config/roles.yml (reloaded on every auth, no restart needed).
Authorized users are persisted to data/bot_users.json.

Start: python -m src.bot.bot
"""

import asyncio

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

from src.bot import roles
from src.bot.cash import get_cash_balance
from src.bot.handlers import (
    cmd_customer,
    cmd_digest,
    cmd_failed,
    cmd_fix_bdate,
    cmd_sales,
    cmd_backfill_status,
    cmd_status,
)
from src.config.settings import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


# ── FSM States ─────────────────────────────────────────────────────────────

class CustomerLookup(StatesGroup):
    waiting_phone = State()


# ── Keyboards ──────────────────────────────────────────────────────────────

auth_kb = types.ReplyKeyboardMarkup(
    keyboard=[[types.KeyboardButton(text="📱 Надіслати номер телефону", request_contact=True)]],
    resize_keyboard=True,
    is_persistent=True,
)

owner_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="💰 Залишок грошей в касах")],
        [types.KeyboardButton(text="📈 Продажі"), types.KeyboardButton(text="👤 Покупець")],
        [types.KeyboardButton(text="⚙️ Технічний стан"), types.KeyboardButton(text="ℹ️ Допомога")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

admin_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="👤 Покупець"), types.KeyboardButton(text="ℹ️ Допомога")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

user_kb = types.ReplyKeyboardMarkup(
    keyboard=[[types.KeyboardButton(text="👤 Покупець"), types.KeyboardButton(text="ℹ️ Допомога")]],
    resize_keyboard=True,
    is_persistent=True,
)


def _kb_for(role: roles.Role | None) -> types.ReplyKeyboardMarkup:
    if role == "owner":
        return owner_kb
    if role == "admin":
        return admin_kb
    return user_kb


# ── Helpers ────────────────────────────────────────────────────────────────

async def _deny(message: types.Message) -> None:
    await message.answer("⛔ Недостатньо прав для цієї команди.")


async def _run_sync(message: types.Message, func, args: str = "") -> None:
    """Run a sync handler in executor and reply with HTML-safe Markdown text."""
    loop = asyncio.get_event_loop()
    try:
        text = await loop.run_in_executor(None, func, args)
    except Exception as e:
        logger.error("bot_handler_error", error=str(e))
        text = f"❌ Помилка: {e}"
    role = roles.get_role(message.from_user.id)
    await message.answer(text, reply_markup=_kb_for(role))


# ── Handlers ───────────────────────────────────────────────────────────────

def setup(dp: Dispatcher) -> None:  # noqa: C901

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message) -> None:
        role = roles.get_role(message.from_user.id)
        if role:
            kb = _kb_for(role)
            await message.answer(
                f"👋 Вітаю! Ваша роль: *{role}*.\nОберіть дію 👇:",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await message.answer(
                "👋 Вітаю!\nДля використання бота потрібна авторизація.\n"
                "Натисніть кнопку нижче, щоб надіслати свій номер телефону 👇",
                reply_markup=auth_kb,
            )

    @dp.message(F.contact)
    async def process_contact(message: types.Message) -> None:
        contact = message.contact
        if not contact or contact.user_id != message.from_user.id:
            await message.answer("❌ Будь ласка, надішліть саме свій контакт через кнопку.")
            return

        phone = contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone

        role = roles.authorize(message.from_user.id, phone)
        if role:
            await message.answer(
                f"✅ Авторизація успішна! Ваша роль: *{role}*.",
                reply_markup=_kb_for(role),
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await message.answer(
                "❌ Доступ заборонено.\nВашого номера немає в списку дозволених.\n"
                "Зверніться до адміністратора."
            )

    # ── /help ──────────────────────────────────────────────────────────────

    @dp.message(Command("help"))
    @dp.message(F.text == "ℹ️ Допомога")
    async def cmd_help(message: types.Message) -> None:
        role = roles.get_role(message.from_user.id)
        lines = ["🤖 *Команди бота*\n"]
        if role in ("owner", "admin", "user"):
            lines += ["/customer 380XX — інфо про клієнта"]
        if role in ("owner", "admin"):
            lines += [
                "/status — стан черги синхронізації",
                "/failed — останні 10 failed чеків",
                "/fix\\_bdate 380XX — передати ДН з BAF в OneBox",
                "/digest — дайджест за вчора",
            ]
        if role == "owner":
            lines += [
                "/cash — залишок грошей в касах",
                "/sales — продажі за вчора по магазинах",
                "/backfill\\_status — статус синхронізації ДН",
                "/users — список авторизованих користувачів",
            ]
        lines.append("/help — це повідомлення")
        await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    # ── /status, /failed, /digest (команди залишаються) ───────────────────

    @dp.message(Command("status"))
    async def handle_status(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/status"):
            await _deny(message)
            return
        await _run_sync(message, cmd_status)

    @dp.message(Command("failed"))
    async def handle_failed(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/failed"):
            await _deny(message)
            return
        await _run_sync(message, cmd_failed)

    @dp.message(Command("digest"))
    async def handle_digest(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/digest"):
            await _deny(message)
            return
        await _run_sync(message, cmd_digest)

    # ── ⚙️ Технічний стан — inline-меню ───────────────────────────────────

    tech_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статус черги", callback_data="tech:status")],
        [InlineKeyboardButton(text="❌ Failed чеки", callback_data="tech:failed")],
        [InlineKeyboardButton(text="📅 Дайджест", callback_data="tech:digest")],
        [InlineKeyboardButton(text="🔄 Синхронізація ДН", callback_data="tech:bfill")],
        [InlineKeyboardButton(text="👤 Покупець", callback_data="tech:customer")],
    ])

    @dp.message(F.text == "⚙️ Технічний стан")
    async def handle_tech_state(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/status"):
            await _deny(message)
            return
        await message.answer("Оберіть розділ:", reply_markup=tech_kb)

    @dp.callback_query(F.data.startswith("tech:"))
    async def tech_callback(callback: types.CallbackQuery, state: FSMContext) -> None:
        if not roles.can(callback.from_user.id, "/status"):
            await callback.answer("⛔ Недостатньо прав.", show_alert=True)
            return
        action = callback.data.split(":")[1]
        await callback.answer()
        if action == "customer":
            await state.set_state(CustomerLookup.waiting_phone)
            await callback.message.answer(
                "📱 Введіть номер телефону покупця:",
                reply_markup=ForceReply(selective=True, input_field_placeholder="380XXXXXXXXX"),
            )
            return
        func_map = {
            "status": cmd_status,
            "failed": cmd_failed,
            "digest": cmd_digest,
            "bfill": cmd_backfill_status,
        }
        func = func_map.get(action)
        if not func:
            return
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, func, "")
        await callback.message.answer(text)

    @dp.message(CustomerLookup.waiting_phone)
    async def customer_phone_received(message: types.Message, state: FSMContext) -> None:
        await state.clear()
        if not roles.can(message.from_user.id, "/customer"):
            await _deny(message)
            return
        phone = message.text.strip() if message.text else ""
        await _run_sync(message, cmd_customer, phone)

    # ── /sales ─────────────────────────────────────────────────────────────────

    sales_date_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📅 Вчора", callback_data="sales:yesterday"),
        InlineKeyboardButton(text="📆 Сьогодні", callback_data="sales:today"),
    ]])

    @dp.message(Command("sales"))
    @dp.message(F.text == "📈 Продажі")
    async def handle_sales(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/sales"):
            await _deny(message)
            return
        await message.answer("Оберіть період:", reply_markup=sales_date_kb)

    @dp.callback_query(F.data.startswith("sales:"))
    async def sales_callback(callback: types.CallbackQuery) -> None:
        if not roles.can(callback.from_user.id, "/sales"):
            await callback.answer("⛔ Недостатньо прав.", show_alert=True)
            return
        period = callback.data.split(":")[1]  # "today" or "yesterday"
        await callback.answer()
        wait = await callback.message.answer("⏳ Зачекайте...")
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, cmd_sales, period)
        await wait.edit_text(text, parse_mode=ParseMode.MARKDOWN)

    # ── /backfill_status ───────────────────────────────────────────────────────

    @dp.message(Command("backfill_status"))
    @dp.message(F.text == "🔄 Синхронізація ДН")
    async def handle_backfill_status(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/backfill_status"):
            await _deny(message)
            return
        await _run_sync(message, cmd_backfill_status)

    # ── /customer ──────────────────────────────────────────────────────────

    @dp.message(Command("customer"))
    @dp.message(F.text == "👤 Покупець")
    async def handle_customer(message: types.Message, state: FSMContext) -> None:
        await state.clear()
        if not roles.can(message.from_user.id, "/customer"):
            await _deny(message)
            return
        # Extract args only for /customer command, not for button press
        parts = message.text.split(None, 1) if message.text.startswith("/") else []
        args = parts[1] if len(parts) > 1 else ""
        if not args:
            await state.set_state(CustomerLookup.waiting_phone)
            await message.answer(
                "📱 Введіть номер телефону покупця:",
                reply_markup=ForceReply(selective=True, input_field_placeholder="380XXXXXXXXX"),
            )
            return
        await _run_sync(message, cmd_customer, args)

    # ── /fix_bdate ─────────────────────────────────────────────────────────

    @dp.message(Command("fix_bdate"))
    async def handle_fix_bdate(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/fix_bdate"):
            await _deny(message)
            return
        args = message.text.split(None, 1)[1] if len(message.text.split(None, 1)) > 1 else ""
        await _run_sync(message, cmd_fix_bdate, args)

    # ── /cash ──────────────────────────────────────────────────────────────

    @dp.message(Command("cash"))
    @dp.message(F.text == "💰 Залишок грошей в касах")
    async def handle_cash(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/cash"):
            await _deny(message)
            return
        wait = await message.answer("⏳ <i>Отримую дані з 1С...</i>", parse_mode=ParseMode.HTML)
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, get_cash_balance)
        await wait.edit_text(text, parse_mode=ParseMode.HTML)

    # ── /users ─────────────────────────────────────────────────────────────

    @dp.message(Command("users"))
    async def handle_users(message: types.Message) -> None:
        if not roles.can(message.from_user.id, "/users"):
            await _deny(message)
            return
        users = roles.list_users()
        if not users:
            await message.answer("Немає авторизованих користувачів.")
            return
        lines = ["👥 *Авторизовані користувачі*\n"]
        for u in users:
            lines.append(f"• `{u['user_id']}` — {u['role']}")
        await message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    # ── Fallback ───────────────────────────────────────────────────────────

    @dp.message()
    async def fallback(message: types.Message) -> None:
        role = roles.get_role(message.from_user.id)
        if role is None:
            await message.answer(
                "Спочатку потрібна авторизація. Натисніть /start",
                reply_markup=auth_kb,
            )
        else:
            await message.answer("Невідома команда. Напишіть /help")


# ── Entry point ────────────────────────────────────────────────────────────

async def main() -> None:
    if not settings.telegram_bot_token:
        logger.error("bot_no_token")
        return

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    setup(dp)

    logger.info("bot_started")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
