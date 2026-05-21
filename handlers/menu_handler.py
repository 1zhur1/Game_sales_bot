"""
🎮 GameHub — Обработчики меню.

Все callback'и навигации по разделам бота.
"""

from telegram.constants import ParseMode

from keyboards import (
    main_menu,
    store_menu_keyboard,
    free_menu_keyboard,
    top_menu_keyboard,
    my_menu_keyboard,
)
from utils import (
    main_menu_text,
    store_menu_text,
    free_menu_text,
    top_menu_text,
    my_menu_text,
)
from services.subscription_service import ensure_subscription


async def _go_to(update, context, text: str, keyboard, delete: bool = True):
    """Универсальная функция перехода в раздел."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    if delete:
        try:
            await query.message.delete()
        except Exception:
            pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


# ═══════════════════════════════════════════════════════════════
# 🏠 Главное меню
# ═══════════════════════════════════════════════════════════════

async def main_menu_callback(update, context):
    await _go_to(update, context, main_menu_text(), main_menu())


# ═══════════════════════════════════════════════════════════════
# 🎮 Магазины
# ═══════════════════════════════════════════════════════════════

async def store_menu_callback(update, context):
    await _go_to(update, context, store_menu_text(), store_menu_keyboard())


# ═══════════════════════════════════════════════════════════════
# 🎁 Халява
# ═══════════════════════════════════════════════════════════════

async def free_menu_callback(update, context):
    await _go_to(update, context, free_menu_text(), free_menu_keyboard())


# ═══════════════════════════════════════════════════════════════
# 🔥 Топ
# ═══════════════════════════════════════════════════════════════

async def top_menu_callback(update, context):
    await _go_to(update, context, top_menu_text(), top_menu_keyboard())


# ═══════════════════════════════════════════════════════════════
# ❤️ Моё
# ═══════════════════════════════════════════════════════════════

async def my_menu_callback(update, context):
    await _go_to(update, context, my_menu_text(), my_menu_keyboard())