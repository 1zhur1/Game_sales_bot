"""
🎮 GameHub — Подписки и избранное.

Обработчик подписок на игры:
- Подписка на игру (поиск → выбор → сохранение)
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
from utils import (
    fmt,
    subscribe_menu_text,
    empty_list_text,
    format_deal_from_cache,
)
from services.search_service import search_games
from services.subscription_service import ensure_subscription


# ─── Временное хранилище результатов поиска ─────
_search_cache = {}


# ─── Меню подписки ──────────────────────────────

async def subscribe_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    try:
        await query.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=subscribe_menu_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=subscribe_menu_keyboard(),
    )


async def subscribe_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await ensure_subscription(query, context):
        return

    try:
        await query.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text="🔍 <b>Введите название игры</b>\n\n"
             "Например:\n"
             "• Cyberpunk 2077\n"
             "• Ведьмак 3\n"
             "• rdr2\n\n"
             "Можно писать на русском или английском.",
        parse_mode=ParseMode.HTML,
    )

    context.user_data["awaiting_subscribe_search"] = True


async def handle_subscribe_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовый ввод для поиска игры."""
    if not context.user_data.get("awaiting_subscribe_search"):
        return False

    user_id = update.effective_user.id
    query_text = update.message.text.strip()

    if not query_text:
        await update.message.reply_text("❌ Пожалуйста, введи название игры.")
        return True

    await update.message.reply_text(
        f"🔍 Ищу <b>{fmt(query_text)}</b>...",
        parse_mode=ParseMode.HTML,
    )

    games = await search_games(query_text)

    if not games:
        await update.message.reply_text(
            f"❌ Ничего не нашлось по запросу «{fmt(query_text)}».\n\n"
            "Попробуй другое название или напиши на английском.",
            parse_mode=ParseMode.HTML,
            reply_markup=subscribe_menu_keyboard(),
        )
        context.user_data["awaiting_subscribe_search"] = False
        return True

    _search_cache[user_id] = games

    await update.message.reply_text(
        f"✅ Нашёл <b>{len(games)}</b> игр. Выбери нужную:",
        parse_mode=ParseMode.HTML,
        reply_markup=game_selection_keyboard(games, "sub_choose"),
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
        await query.message.reply_text(
            "❌ Игра не найдена. Попробуй ещё раз.",
            reply_markup=subscribe_menu_keyboard(),
        )
        return

    game = games[index]
    game_title = game["title"]
    store = game["store"]

    user_subs = await get_user_subscriptions(user_id)
    already_subscribed = any(
        s["game_title"] == game_title and s["store"] == store
        for s in user_subs
    )

    is_fav = await is_favorite(user_id, game_title, store)

    text = _format_game_info(game, already_subscribed, is_fav)

    try:
        await query.message.delete()
    except Exception:
        pass

    if game.get("image"):
        try:
            await context.bot.send_photo(
                chat_id=query.message.chat.id,
                photo=game["image"],
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=subscription_action_keyboard(
                    game_title, store, already_subscribed, is_fav,
                ),
            )
            return
        except Exception:
            pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=subscription_action_keyboard(
            game_title, store, already_subscribed, is_fav,
        ),
    )


def _format_game_info(game: dict, is_subscribed: bool, is_fav: bool) -> str:
    title = fmt(game["title"])
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
        text += "\n✅ <b>Ты подписан на эту игру</b>"
    else:
        text += "\n❌ <b>Не подписан</b>"

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
            caption=(
                f"✅ <b>Ты подписался на {fmt(game_title)}</b>\n\n"
                f"Теперь я пришлю уведомление, когда цена "
                f"на эту игру в {store} упадёт."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )
    else:
        await query.edit_message_caption(
            caption=f"⚠️ Ты уже подписан на {fmt(game_title)} в {store}.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
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
            caption=f"❌ <b>Отписался от {fmt(game_title)}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )
    else:
        await query.edit_message_caption(
            caption=f"⚠️ Подписка на {fmt(game_title)} не найдена.",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
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
        except Exception:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=empty_list_text("subscriptions"),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )
        return

    text = "📌 <b>Мои подписки</b>\n\n"
    start = page * 5
    end = start + 5
    page_items = subs[start:end]

    for i, sub in enumerate(page_items, start + 1):
        title = fmt(sub["game_title"])
        store = sub["store"]
        text += f"{i}. {title}  ·  {store}\n"

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
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=my_subscriptions_keyboard(subs, page),
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
        new_text = "⭐ Убрал из избранного"
    else:
        game = await get_deal_by_title(game_title, store)
        await add_favorite(
            user_id, game_title, store,
            image=game.get("image", "") if game else "",
            url=game.get("url", "") if game else "",
        )
        new_text = "⭐ Добавил в избранное"

    is_subscribed = any(
        s["game_title"] == game_title and s["store"] == store
        for s in await get_user_subscriptions(user_id)
    )

    await query.edit_message_reply_markup(
        reply_markup=subscription_action_keyboard(
            game_title, store, is_subscribed, not is_fav,
        ),
    )

    await query.message.reply_text(
        f"{new_text}: {fmt(game_title)} ({store})",
        parse_mode=ParseMode.HTML,
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
        except Exception:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=empty_list_text("favorites"),
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(),
        )
        return

    text = "⭐ <b>Избранные игры</b>\n\n"
    start = page * 5
    end = start + 5
    page_items = favs[start:end]

    for i, fav in enumerate(page_items, start + 1):
        title = fmt(fav["game_title"])
        store = fav["store"]
        text += f"{i}. {title}  ·  {store}\n"

        if fav.get("url"):
            text += f'   🔗 <a href="{fav["url"]}">Открыть</a>\n'

        text += "\n"

    text += f"Всего: {len(favs)}"

    try:
        await query.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=my_favorites_keyboard(favs, page),
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
        text = f"🎮 <b>{fmt(game_title)}</b>\n🏪 {store}"

    try:
        await query.message.delete()
    except Exception:
        pass

    if game and game.get("image"):
        try:
            await context.bot.send_photo(
                chat_id=query.message.chat.id,
                photo=game["image"],
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=subscription_action_keyboard(
                    game_title, store, is_sub, is_fav,
                ),
            )
            return
        except Exception:
            pass

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=subscription_action_keyboard(
            game_title, store, is_sub, is_fav,
        ),
    )