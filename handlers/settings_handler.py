"""
Обработчик настроек пользователя:
- Включение/отключение уведомлений
- Фильтр минимального процента скидки
- Подписка на определённые магазины
"""

import html

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import get_user_settings, update_user_settings
from keyboards import settings_keyboard, discount_filter_keyboard, main_menu
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

    text = (
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь можно настроить уведомления под себя.\n\n"
        f"🔔 Уведомления: {'✅ Включены' if settings['notifications_enabled'] else '❌ Отключены'}\n"
        f"📉 Минимальная скидка: {settings['min_discount_percent']}%\n\n"
        "<i>Уведомления приходят только если скидка больше или равна указанному проценту.</i>"
    )

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(settings)
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
        text=(
            "⚙️ <b>Настройки</b>\n\n"
            f"🔔 Уведомления: {'✅ Включены' if new_status else '❌ Отключены'}\n"
            f"📉 Минимальная скидка: {settings['min_discount_percent']}%\n\n"
            f"{'✅ Уведомления включены' if new_status else '❌ Уведомления отключены'}"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(settings)
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

    await query.edit_message_text(
        text=(
            "📉 <b>Минимальный процент скидки</b>\n\n"
            "Выбери минимальный размер скидки, "
            "при котором ты хочешь получать уведомления.\n\n"
            f"Текущее значение: <b>{settings['min_discount_percent']}%</b>\n\n"
            "<i>Уведомления будут приходить только если скидка больше этого значения.</i>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=discount_filter_keyboard(settings["min_discount_percent"])
    )


async def set_min_discount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data  # set_min_discount_10, set_min_discount_50, etc.

    try:
        discount = int(data.split("_")[-1])
    except (ValueError, IndexError):
        return

    await update_user_settings(user_id, min_discount_percent=discount)
    settings = await get_user_settings(user_id)

    if not settings:
        settings = {"notifications_enabled": True, "min_discount_percent": discount}

    await query.edit_message_text(
        text=(
            "⚙️ <b>Настройки</b>\n\n"
            f"🔔 Уведомления: {'✅ Включены' if settings['notifications_enabled'] else '❌ Отключены'}\n"
            f"📉 Минимальная скидка: <b>{discount}%</b>\n\n"
            f"✅ Сохранено!"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=settings_keyboard(settings)
    )