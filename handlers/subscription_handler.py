"""
Обработчик подписок на игры:
- Подписка на игру (поиск выбор -> сохранение)
- Список подписок пользователя
- Отписка от игры
- Избранное
"""

import html

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (
    add_subscription, remove_subscription,
    get_user_subscriptions, get_user_favorites,
    add_favorite, remove_favorite, is_favorite,
    get_deal_by_title,
)
from keyboards import (
    main_menu, subscribe_menu_keyboard,
    game_selection_keyboard, subscription_action_keyboard,
    my_subscriptions_keyboard, my_favorites_keyboard,
)
from services.search_service import search_games, search_by_exact_prefix
from services.subscription_service import ensure_subscription


# ─── Временное хранилище результатов поиска ─────

# Хранит результаты поиска для каждого пользователя {user_id: [games]}
_search_cache = {}


# ─── Меню подписки ──────────────────────────────

async def subscribe_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text="🔔 <b>Подписка на игру</b>\n\n"
             "Я буду отслеживать скидки и бесплатные раздачи "
             "для выбранной игры и присылать тебе уведомления.\n\n"
             "Нажми кнопку ниже, чтобы начать.",
        parse_mode=ParseMode.HTML,
        reply_markup=subscribe_menu_keyboard()
    )


async def subscribe_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text="🔍 <b>Введите название игры</b>\n\n"
             "Например:\n"
             "• Cyberpunk 2077\n"
             "• GTA V\n"
             "• Ведьмак 3\n"
             "• rdr2\n\n"
             "Можно писать на русском или английском.",
        parse_mode=ParseMode.HTML
    )

    # Устанавливаем флаг, что ждём текст от пользователя
    context.user_data["awaiting_subscribe_search"] = True


async def handle_subscribe_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовый ввод для поиска игры."""
    if not context.user_data.get("awaiting_subscribe_search"):
        return False

    user_id = update.effective_user.id
    query_text = update.message.text.strip()

    if not query_text:
        await update.message.reply_text("❌ Пожалуйста, введите название игры.")
        return True

    await update.message.reply_text(f"🔍 Ищу <b>{html.escape(query_text)}</b>...",
                                     parse_mode=ParseMode.HTML)

    # Ищем игры
    games = await search_games(query_text)

    if not games:
        await update.message.reply_text(
            f"❌ Не удалось найти игры по запросу «{html.escape(query_text)}».\n\n"
            "Попробуй другое название или напиши на английском.",
            parse_mode=ParseMode.HTML,
            reply_markup=subscribe_menu_keyboard()
        )
        context.user_data["awaiting_subscribe_search"] = False
        return True

    # Сохраняем результаты поиска
    _search_cache[user_id] = games

    await update.message.reply_text(
        f"✅ Найдено <b>{len(games)}</b> игр. Выбери нужную:",
        parse_mode=ParseMode.HTML,
        reply_markup=game_selection_keyboard(games, "sub_choose")
    )

    context.user_data["awaiting_subscribe_search"] = False
    return True


async def subscribe_choose_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор игры из результатов поиска."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data  # sub_choose_0, sub_choose_1, etc.

    try:
        index = int(data.split("_")[-1])
    except (ValueError, IndexError):
        await query.message.reply_text("❌ Ошибка выбора.")
        return

    games = _search_cache.get(user_id, [])
    if index < 0 or index >= len(games):
        await query.message.reply_text("❌ Игра не найдена. Попробуй ещё раз.",
                                        reply_markup=subscribe_menu_keyboard())
        return

    game = games[index]
    game_title = game["title"]
    store = game["store"]

    # Проверяем, не подписан ли уже
    user_subs = await get_user_subscriptions(user_id)
    already_subscribed = any(
        s["game_title"] == game_title and s["store"] == store
        for s in user_subs
    )

    is_fav = await is_favorite(user_id, game_title, store)

    # Показываем информацию и кнопки
    text = _format_game_info(game, already_subscribed, is_fav)

    try:
        await query.message.delete()
    except:
        pass

    if game.get("image"):
        try:
            await context.bot.send_photo(
                chat_id=query.message.chat.id,
                photo=game["image"],
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=subscription_action_keyboard(
                    game_title, store, already_subscribed, is_fav
                )
            )
            return
        except:
            pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=subscription_action_keyboard(
            game_title, store, already_subscribed, is_fav
        )
    )


def _format_game_info(game: dict, is_subscribed: bool, is_fav: bool) -> str:
    title = html.escape(game["title"])
    store = game["store"]
    discount = game.get("discount_percent", 0)
    is_free = game.get("is_free", False)

    text = f"🎮 <b>{title}</b>\n"
    text += f"🏪 {store}\n"

    if is_free:
        text += "🎁 <b>БЕСПЛАТНО!</b>\n"
    elif discount > 0:
        text += f"🔥 Скидка: -{discount}%\n"

    if is_subscribed:
        text += "\n✅ <b>Вы подписаны на эту игру</b>"
    else:
        text += "\n❌ <b>Вы не подписаны</b>"

    if is_fav:
        text += "\n⭐ В избранном"

    if game.get("url"):
        text += f'\n\n🔗 <a href="{game["url"]}">Открыть в магазине</a>'

    return text


# ─── Подтверждение подписки ─────────────────────

async def subscribe_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data  # sub_confirm_GameTitle|Store

    try:
        _, raw = data.split("sub_confirm_", 1)
        game_title, store = raw.rsplit("|", 1)
    except (ValueError, IndexError):
        await query.message.reply_text("❌ Ошибка обработки.")
        return

    # Получаем информацию об игре
    game = await get_deal_by_title(game_title, store)

    success = await add_subscription(
        user_id=user_id,
        game_title=game_title,
        store=store,
        price=game["price"] if game else None,
        discount=game["discount_percent"] if game else 0,
    )

    if success:
        await query.edit_message_caption(
            caption=f"✅ <b>Вы подписались на {html.escape(game_title)}</b>\n\n"
                    f"Теперь вы будете получать уведомления о скидках "
                    f"и бесплатных раздачах в {store}.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )
    else:
        await query.edit_message_caption(
            caption=f"⚠️ Вы уже подписаны на {html.escape(game_title)} в {store}.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )


# ─── Отписка ────────────────────────────────────

async def unsubscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data  # unsub_GameTitle|Store

    try:
        _, raw = data.split("unsub_", 1)
        game_title, store = raw.rsplit("|", 1)
    except (ValueError, IndexError):
        await query.message.reply_text("❌ Ошибка обработки.")
        return

    success = await remove_subscription(user_id, game_title, store)

    if success:
        await query.edit_message_caption(
            caption=f"❌ <b>Вы отписались от {html.escape(game_title)}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )
    else:
        await query.edit_message_caption(
            caption=f"⚠️ Подписка на {html.escape(game_title)} не найдена.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )


# ─── Мои подписки ───────────────────────────────

async def my_subscriptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data

    try:
        page = int(data.split("_")[-1])
    except (ValueError, IndexError):
        page = 0

    subs = await get_user_subscriptions(user_id)

    if not subs:
        try:
            await query.message.delete()
        except:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="📌 <b>У вас нет активных подписок</b>\n\n"
                 "Нажми «🔔 Подписаться на игру» в главном меню, "
                 "чтобы начать отслеживать скидки.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )
        return

    text = "📌 <b>Мои подписки</b>\n\n"
    start = page * 5
    end = start + 5
    page_items = subs[start:end]

    for i, sub in enumerate(page_items, start + 1):
        title = html.escape(sub["game_title"])
        store = sub["store"]
        text += f"{i}. {title} ({store})\n"

        if sub["last_known_discount"] > 0:
            text += f"   💸 Последняя скидка: -{sub['last_known_discount']}%\n"
        elif sub["last_known_price"] is not None:
            text += f"   💰 Цена: {sub['last_known_price']:.2f}\n"
        else:
            text += "   💰 Цена неизвестна\n"

        text += "\n"

    text += f"Всего подписок: {len(subs)}"

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=my_subscriptions_keyboard(subs, page)
    )


# ─── Избранное ──────────────────────────────────

async def favorite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление/удаление из избранного."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data  # fav_GameTitle|Store

    try:
        _, raw = data.split("fav_", 1)
        game_title, store = raw.rsplit("|", 1)
    except (ValueError, IndexError):
        await query.message.reply_text("❌ Ошибка обработки.")
        return

    is_fav = await is_favorite(user_id, game_title, store)

    if is_fav:
        await remove_favorite(user_id, game_title, store)
        new_text = "⭐ Удалено из избранного"
    else:
        game = await get_deal_by_title(game_title, store)
        await add_favorite(
            user_id, game_title, store,
            image=game.get("image", "") if game else "",
            url=game.get("url", "") if game else "",
        )
        new_text = "⭐ Добавлено в избранное"

    # Обновляем клавиатуру
    is_subscribed = any(
        s["game_title"] == game_title and s["store"] == store
        for s in await get_user_subscriptions(user_id)
    )

    await query.edit_message_reply_markup(
        reply_markup=subscription_action_keyboard(
            game_title, store, is_subscribed, not is_fav
        )
    )

    await query.message.reply_text(
        f"{new_text}: {html.escape(game_title)} ({store})",
        parse_mode=ParseMode.HTML
    )


async def my_favorites_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data

    try:
        page = int(data.split("_")[-1])
    except (ValueError, IndexError):
        page = 0

    favs = await get_user_favorites(user_id)

    if not favs:
        try:
            await query.message.delete()
        except:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="⭐ <b>Избранное пусто</b>\n\n"
                 "Добавляй игры в избранное, чтобы не потерять их.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )
        return

    text = "⭐ <b>Избранные игры</b>\n\n"
    start = page * 5
    end = start + 5
    page_items = favs[start:end]

    for i, fav in enumerate(page_items, start + 1):
        title = html.escape(fav["game_title"])
        store = fav["store"]
        text += f"{i}. {title} ({store})\n"

        if fav.get("url"):
            text += f'   🔗 <a href="{fav["url"]}">Открыть</a>\n'

        text += "\n"

    text += f"Всего: {len(favs)}"

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=my_favorites_keyboard(favs, page)
    )


# ─── Информация об игре ─────────────────────────

async def game_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию об игре из избранного."""
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    user_id = query.from_user.id
    data = query.data  # game_info_GameTitle|Store

    try:
        _, raw = data.split("game_info_", 1)
        game_title, store = raw.rsplit("|", 1)
    except (ValueError, IndexError):
        await query.message.reply_text("❌ Ошибка обработки.")
        return

    game = await get_deal_by_title(game_title, store)
    is_fav = await is_favorite(user_id, game_title, store)
    user_subs = await get_user_subscriptions(user_id)
    is_sub = any(
        s["game_title"] == game_title and s["store"] == store
        for s in user_subs
    )

    if game:
        text = _format_game_info(game, is_sub, is_fav)
    else:
        text = f"🎮 <b>{html.escape(game_title)}</b>\n🏪 {store}"

    try:
        await query.message.delete()
    except:
        pass

    if game and game.get("image"):
        try:
            await context.bot.send_photo(
                chat_id=query.message.chat.id,
                photo=game["image"],
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=subscription_action_keyboard(
                    game_title, store, is_sub, is_fav
                )
            )
            return
        except:
            pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=subscription_action_keyboard(
            game_title, store, is_sub, is_fav
        )
    )