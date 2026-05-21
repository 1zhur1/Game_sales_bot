"""
🎮 WTF_Steam — Настройки пользователя.

- Включение/отключение уведомлений
- Фильтры уведомлений (независимые от магазинных фильтров)
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (
    get_user_settings, update_user_settings,
    get_user_notif_filters, update_user_notif_filter,
    reset_user_notif_filters,
)
from keyboards import (
    settings_keyboard, notif_filters_main_keyboard,
    discount_filter_keyboard_v1, main_menu,
)
from utils import settings_menu_text, fmt
from services.subscription_service import ensure_subscription
from services.filter_service import ALL_GENRES


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


# ═══════════════════════════════════════════════════════════════
# 🎯 ФИЛЬТРЫ УВЕДОМЛЕНИЙ
# ═══════════════════════════════════════════════════════════════

async def notif_filters_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню фильтров уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    notif_filters = await get_user_notif_filters(user_id)

    text = (
        "🎯 <b>Фильтры уведомлений</b>\n\n"
        "Настрой, о каких играх присылать уведомления.\n"
        "Эти фильтры не влияют на просмотр игр в магазинах.\n\n"
        "Текущие настройки:"
    )

    try:
        await query.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=notif_filters_main_keyboard(notif_filters),
    )


async def notif_filters_genres_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор жанров для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_notif_filters(user_id)
    selected = set(filters.get("selected_genres", []))

    # Строим клавиатуру выбора жанров с префиксом nf_genre_
    buttons = []
    row = []
    for genre in ALL_GENRES:
        marker = "✅" if genre in selected else genre
        row.append(
            InlineKeyboardButton(marker, callback_data=f"nf_genre_{genre}")
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("✅ Готово", callback_data="nf_genre_done"),
    ])

    await query.edit_message_text(
        text="🎭 <b>Выбери жанры</b>\n\nЖанры, по которым фильтровать уведомления.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def notif_filters_genre_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить жанр для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    genre = query.data.split("_", 2)[2]  # nf_genre_Action -> Action

    filters = await get_user_notif_filters(user_id)
    selected = set(filters.get("selected_genres", []))

    if genre in selected:
        selected.remove(genre)
    else:
        selected.add(genre)

    await update_user_notif_filter(user_id, "selected_genres", list(selected))

    # Обновляем клавиатуру
    buttons = []
    row = []
    for g in ALL_GENRES:
        marker = "✅" if g in selected else g
        row.append(
            InlineKeyboardButton(marker, callback_data=f"nf_genre_{g}")
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("✅ Готово", callback_data="nf_genre_done"),
    ])

    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))


async def notif_filters_genre_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в меню фильтров уведомлений после выбора жанров."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    notif_filters = await get_user_notif_filters(user_id)

    await query.edit_message_text(
        text="🎯 <b>Фильтры уведомлений</b>\n\nТекущие настройки:",
        parse_mode=ParseMode.HTML,
        reply_markup=notif_filters_main_keyboard(notif_filters),
    )


async def notif_filters_discount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор минимальной скидки для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_notif_filters(user_id)
    current = filters.get("min_discount", 0)

    values = [0, 10, 25, 50, 75, 90]
    buttons = []
    row = []
    for v in values:
        marker = "✅" if v == current else f"{v}%"
        row.append(
            InlineKeyboardButton(marker, callback_data=f"nf_set_discount_{v}")
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="settings_notif_filters"),
    ])

    await query.edit_message_text(
        text="💸 <b>Минимальная скидка</b>\n\nПрисылать уведомления, только если скидка >= этого значения.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def notif_filters_set_discount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить минимальную скидку для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    try:
        discount = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        return

    await update_user_notif_filter(user_id, "min_discount", discount)
    notif_filters = await get_user_notif_filters(user_id)

    await query.edit_message_text(
        text="🎯 <b>Фильтры уведомлений</b>\n\nТекущие настройки:",
        parse_mode=ParseMode.HTML,
        reply_markup=notif_filters_main_keyboard(notif_filters),
    )


async def notif_filters_platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор платформы для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_notif_filters(user_id)
    current = filters.get("platform", "all")

    options = [("all", "Все"), ("steam", "Steam"), ("epic games", "Epic Games")]
    buttons = []
    for key, label in options:
        marker = "✅" if current == key else label
        buttons.append([
            InlineKeyboardButton(marker, callback_data=f"nf_set_platform_{key}"),
        ])
    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="settings_notif_filters"),
    ])

    await query.edit_message_text(
        text="🖥 <b>Платформа</b>\n\nУведомления только с выбранной платформы.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def notif_filters_set_platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить платформу для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    platform = query.data.split("_", 3)[3]  # nf_set_platform_steam -> steam

    await update_user_notif_filter(user_id, "platform", platform)
    notif_filters = await get_user_notif_filters(user_id)

    await query.edit_message_text(
        text="🎯 <b>Фильтры уведомлений</b>\n\nТекущие настройки:",
        parse_mode=ParseMode.HTML,
        reply_markup=notif_filters_main_keyboard(notif_filters),
    )


async def notif_filters_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор типа контента для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_notif_filters(user_id)
    current = filters.get("filter_type", "all")

    options = [("all", "Всё подряд"), ("discounts", "Только скидки"), ("free", "Только халява")]
    buttons = []
    for key, label in options:
        marker = "✅" if current == key else label
        buttons.append([
            InlineKeyboardButton(marker, callback_data=f"nf_set_type_{key}"),
        ])
    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="settings_notif_filters"),
    ])

    await query.edit_message_text(
        text="🎯 <b>Тип уведомлений</b>\n\nЧто именно присылать.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def notif_filters_set_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить тип контента для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filter_type = query.data.split("_", 3)[3]

    await update_user_notif_filter(user_id, "filter_type", filter_type)
    notif_filters = await get_user_notif_filters(user_id)

    await query.edit_message_text(
        text="🎯 <b>Фильтры уведомлений</b>\n\nТекущие настройки:",
        parse_mode=ParseMode.HTML,
        reply_markup=notif_filters_main_keyboard(notif_filters),
    )


async def notif_filters_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор минимального рейтинга для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_notif_filters(user_id)
    current = filters.get("rating_filter", 0)

    values = [0, 50, 70, 80, 90, 95]
    buttons = []
    row = []
    for v in values:
        label = "Любой" if v == 0 else f"{v}%+"
        marker = "✅" if current == v else label
        row.append(
            InlineKeyboardButton(marker, callback_data=f"nf_set_rating_{v}")
        )
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("◀️ Назад", callback_data="settings_notif_filters"),
    ])

    await query.edit_message_text(
        text="⭐ <b>Рейтинг</b>\n\nУведомления только для игр с рейтингом >= выбранного.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def notif_filters_set_rating_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить минимальный рейтинг для уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    try:
        rating = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        return

    await update_user_notif_filter(user_id, "rating_filter", rating)
    notif_filters = await get_user_notif_filters(user_id)

    await query.edit_message_text(
        text="🎯 <b>Фильтры уведомлений</b>\n\nТекущие настройки:",
        parse_mode=ParseMode.HTML,
        reply_markup=notif_filters_main_keyboard(notif_filters),
    )


async def notif_filters_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить фильтры уведомлений."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    await reset_user_notif_filters(user_id)
    notif_filters = await get_user_notif_filters(user_id)

    await query.edit_message_text(
        text="🎯 <b>Фильтры уведомлений</b>\n\n🧹 Фильтры сброшены.\n\nТекущие настройки:",
        parse_mode=ParseMode.HTML,
        reply_markup=notif_filters_main_keyboard(notif_filters),
    )