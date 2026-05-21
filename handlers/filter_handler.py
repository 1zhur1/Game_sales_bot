"""
Handler для системы фильтрации игр.

Предоставляет меню фильтров и callbacks для:
- Выбора жанров (toggle)
- Минимальной скидки
- Максимальной цены
- Платформы
- Типа контента
- Сортировки
- Сброса фильтров
"""
from telegram.constants import ParseMode
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from services.subscription_service import ensure_subscription
from database import get_user_filters, update_user_filter, reset_user_filters
from services.filter_service import format_active_filters, ALL_GENRES
from keyboards import filters_main_menu_keyboard, genres_keyboard, discount_filter_keyboard_v2
from keyboards import price_filter_keyboard, platform_filter_keyboard, filter_type_keyboard
from keyboards import sort_type_keyboard, rating_filter_keyboard


async def filters_menu_callback(update, context):
    """Главное меню фильтров."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    active_text = format_active_filters(filters)

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=f"{active_text}\n\nВыбери, что хочешь настроить:",
        parse_mode=ParseMode.HTML,
        reply_markup=filters_main_menu_keyboard(),
    )


async def filters_genres_callback(update, context):
    """Открыть меню выбора жанров."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    selected = set(filters.get("selected_genres", []))

    text = "🎭 <b>Жанры</b>\n\n"
    if selected:
        text += f"Выбрано: <b>{', '.join(sorted(selected))}</b>"
    else:
        text += "Ничего не выбрано — показываю все жанры."

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=genres_keyboard(selected),
    )


async def filters_genre_toggle_callback(update, context):
    """Переключить выбор жанра."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    genre = query.data.replace("fgenre_toggle_", "")

    filters = await get_user_filters(user_id)
    selected = set(filters.get("selected_genres", []))

    if genre in selected:
        selected.remove(genre)
    else:
        selected.add(genre)

    await update_user_filter(user_id, "selected_genres", list(selected))

    text = "🎭 <b>Жанры</b>\n\n"
    if selected:
        text += f"Выбрано: <b>{', '.join(sorted(selected))}</b>"
    else:
        text += "Ничего не выбрано — показываю все жанры."

    await query.message.edit_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=genres_keyboard(selected),
    )


async def filters_genres_done_callback(update, context):
    """Завершить выбор жанров и вернуться в меню фильтров."""
    await filters_menu_callback(update, context)


async def filters_discount_callback(update, context):
    """Открыть меню выбора минимальной скидки."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    current = filters.get("min_discount", 0)

    text = f"💸 <b>Минимальная скидка</b>\n\n"
    text += f"Сейчас: <b>{current}%</b>\n"
    text += f"Выбери минимальный процент:"

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=discount_filter_keyboard_v2(current),
    )


async def filters_set_discount_callback(update, context):
    """Установить минимальную скидку."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    value = int(query.data.replace("fset_discount_", ""))

    await update_user_filter(user_id, "min_discount", value)

    # Возвращаемся в меню фильтров
    await filters_menu_callback(update, context)


async def filters_price_callback(update, context):
    """Открыть меню выбора максимальной цены."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    current = filters.get("max_price", 0)

    text = f"💰 <b>Максимальная цена</b>\n\n"
    if current > 0:
        text += f"Сейчас: <b>${current}</b>\n"
    else:
        text += f"Сейчас: <b>Любая</b>\n"
    text += f"Выбери максимальную цену:"

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=price_filter_keyboard(current),
    )


async def filters_set_price_callback(update, context):
    """Установить максимальную цену."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    value = float(query.data.replace("fset_price_", ""))

    await update_user_filter(user_id, "max_price", value)

    await filters_menu_callback(update, context)


async def filters_platform_callback(update, context):
    """Открыть меню выбора платформы."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    current = filters.get("platform", "all")

    plat_names = {"all": "Все", "steam": "Steam", "epic games": "Epic Games"}
    current_name = plat_names.get(current, current)

    text = f"🖥 <b>Платформа</b>\n\n"
    text += f"Сейчас: <b>{current_name}</b>\n"
    text += f"Выбери платформу:"

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=platform_filter_keyboard(current),
    )


async def filters_set_platform_callback(update, context):
    """Установить платформу."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    platform = query.data.replace("fset_platform_", "")

    await update_user_filter(user_id, "platform", platform)

    await filters_menu_callback(update, context)


async def filters_type_callback(update, context):
    """Открыть меню выбора типа контента."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    current = filters.get("filter_type", "all")

    ft_names = {"all": "Всё", "discounts": "Только скидки", "free": "Только халява"}
    current_name = ft_names.get(current, current)

    text = f"🎯 <b>Тип игр</b>\n\n"
    text += f"Сейчас: <b>{current_name}</b>\n"
    text += f"Выбери тип:"

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=filter_type_keyboard(current),
    )


async def filters_set_type_callback(update, context):
    """Установить тип контента."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filter_type = query.data.replace("fset_type_", "")

    await update_user_filter(user_id, "filter_type", filter_type)

    await filters_menu_callback(update, context)


async def filters_sort_callback(update, context):
    """Открыть меню выбора сортировки."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    current = filters.get("sort_type", "discount")

    st_names = {
        "discount": "По скидке", "price": "По цене", "rating": "По рейтингу",
        "title": "По алфавиту", "popularity": "По популярности", "newest": "По новизне"
    }
    current_name = st_names.get(current, current)

    text = f"📊 <b>Сортировка</b>\n\n"
    text += f"Сейчас: <b>{current_name}</b>\n"
    text += f"Выбери сортировку:"

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=sort_type_keyboard(current),
    )


async def filters_set_sort_callback(update, context):
    """Установить сортировку."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    sort_type = query.data.replace("fset_sort_", "")

    await update_user_filter(user_id, "sort_type", sort_type)

    await filters_menu_callback(update, context)


async def filters_rating_callback(update, context):
    """Открыть меню выбора минимального рейтинга."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    current = filters.get("rating_filter", 0)

    text = f"⭐ <b>Минимальный рейтинг</b>\n\n"
    if current > 0:
        text += f"Сейчас: <b>{current}%+</b>\n"
    else:
        text += "Сейчас: <b>Любой</b>\n"
    text += f"Выбери минимальный рейтинг:"

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=rating_filter_keyboard(current),
    )


async def filters_set_rating_callback(update, context):
    """Установить минимальный рейтинг."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    value = int(query.data.replace("fset_rating_", ""))

    await update_user_filter(user_id, "rating_filter", value)

    await filters_menu_callback(update, context)


async def filters_reset_callback(update, context):
    """Сбросить все фильтры."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    await reset_user_filters(user_id)

    await filters_menu_callback(update, context)