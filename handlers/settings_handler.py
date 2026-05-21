"""
🎮 GameHub — Настройки пользователя.

- Включение/отключение уведомлений
- Фильтр минимального процента скидки
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import get_user_settings, update_user_settings
from keyboards import settings_keyboard, discount_filter_keyboard_v1, main_menu
from utils import settings_menu_text
from services.subscription_service import ensure_subscription


async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    settings = await get_user_settings(user_id)

    if not settings:
        settings = {"notifications_enabled": True, "min_discount_percent": 0}

    try:
        await query.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=settings_menu_text(settings),
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(settings),
    )


async def settings_toggle_notif_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    settings = await get_user_settings(user_id)

    if not settings:
        settings = {"notifications_enabled": True, "min_discount_percent": 0}

    new_status = not settings["notifications_enabled"]
    await update_user_settings(user_id, notifications_enabled=new_status)

    settings["notifications_enabled"] = new_status

    await query.edit_message_text(
        text=settings_menu_text(settings),
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(settings),
    )


async def settings_min_discount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    settings = await get_user_settings(user_id)

    if not settings:
        settings = {"notifications_enabled": True, "min_discount_percent": 0}

    current = settings["min_discount_percent"]

    await query.edit_message_text(
        text=(
            "📉 <b>Минимальная скидка</b>\n\n"
            "Выбери минимальный процент скидки,\n"
            "при котором присылать уведомление.\n\n"
            f"Сейчас: <b>{current}%</b>\n\n"
            "<i>Уведомления приходят, только если\n"
            "скидка >= этого значения.</i>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=discount_filter_keyboard_v1(current),
    )


async def set_min_discount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data  # set_min_discount_10, etc.

    try:
        discount = int(data.split("_")[-1])
    except (ValueError, IndexError):
        return

    await update_user_settings(user_id, min_discount_percent=discount)
    settings = await get_user_settings(user_id)

    if not settings:
        settings = {"notifications_enabled": True, "min_discount_percent": discount}

    await query.edit_message_text(
        text=settings_menu_text(settings),
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(settings),
    )