"""
Сервис уведомлений:
1. Периодическая проверка новых скидок/халявы (каждый час)
2. Мониторинг подписок пользователей (каждые 30 минут)
3. Отправка персонализированных уведомлений с паузой между сообщениями
4. Фильтрация по интересам пользователя (ключевые слова)
5. Защита от спама (дубликаты уведомлений)
"""

import asyncio
import time
import html
from typing import Optional

from telegram.ext import Application
from telegram.constants import ParseMode

from config import NOTIFICATION_INTERVAL, MONITOR_INTERVAL, MAX_NOTIFICATION_DEALS
from database import (
    add_known_deal, deal_exists, make_deal_id,
    get_all_active_users, get_users_with_notifications,
    get_all_subscriptions, update_subscription_price,
    mark_subscription_notified, add_notification_history,
    has_recent_notification, add_price_history,
    get_deal_by_title, get_deals_from_cache,
    get_free_from_cache, add_deal_to_cache, clear_deals_cache,
    get_user_filters, get_user_notif_filters,
)
from models import GameDeal
from services.filter_service import (
    filter_by_genres, filter_by_discount, filter_by_price,
    filter_by_platform, filter_by_type, filter_by_rating,
    get_game_genres,
)

log = print

FALLBACK_IMAGE = "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/0/header.jpg"

# Пауза между отправкой уведомлений одному пользователю (в секундах)
NOTIFICATION_PAUSE = 90  # 1.5 минуты между сообщениями

# Пауза между отправкой разным пользователям (в секундах)
USER_PAUSE = 30


# ═══════════════════════════════════════════════════════
# Фоновые задачи (вызываются JobQueue)
# ═══════════════════════════════════════════════════════

async def start_background_tasks(app: Application) -> None:
    """Запускает все фоновые задачи (больше не используется, всё через JobQueue)."""
    log("start_background_tasks called - use JobQueue instead")


async def check_new_deals_loop(app: Application) -> None:
    """
    Периодическая проверка новых скидок.
    Вызывается JobQueue по расписанию.
    """
    log("JOB: Starting new deals check...")
    try:
        await _check_new_deals_cycle(app)
    except Exception as e:
        log(f"JOB: New deals check error: {e}")
        import traceback
        log(traceback.format_exc())
    log("JOB: New deals check completed")


async def monitor_subscriptions_loop(app: Application) -> None:
    """
    Периодический мониторинг подписок.
    Вызывается JobQueue по расписанию.
    """
    log("JOB: Starting subscription monitor...")
    try:
        await _monitor_subscriptions_cycle(app)
    except Exception as e:
        log(f"JOB: Subscription monitor error: {e}")
        import traceback
        log(traceback.format_exc())
    log("JOB: Subscription monitor completed")


# ═══════════════════════════════════════════════════════
# Цикл проверки новых скидок
# ═══════════════════════════════════════════════════════

async def _check_new_deals_cycle(app: Application) -> None:
    """Один цикл проверки всех источников. Обновляет кэш в БД."""
    from services.steam_service import get_steam_deals, get_steam_free_games
    from services.epic_service import get_epic_free_games, get_epic_deals

    log("CHECK: Starting new deals check cycle...")

    new_items: list[dict] = []

    # --- Steam deals ---
    try:
        steam_deals = await get_steam_deals()
        for game in steam_deals:
            deal_id = make_deal_id("steam", game.title)
            if not await deal_exists(deal_id):
                log(f"CHECK: New Steam deal: {game.title}")
                await add_known_deal(
                    deal_id, game.title, "Steam",
                    game.discount_percent, False,
                    game.url, game.image
                )
                new_items.append({
                    "title": game.title,
                    "store": "Steam",
                    "discount_percent": game.discount_percent,
                    "is_free": False,
                    "url": game.url,
                    "image": game.image,
                    "price": _extract_price(game.discounted_price),
                    "original_price": _extract_price(game.original_price),
                    "rating_percent": game.rating_percent,
                    "genres": game.genres,
                })

            # Обновляем кэш в БД
            await _update_deals_cache(game, "steam")
    except Exception as e:
        log(f"CHECK: Steam deals error: {e}")

    # --- Steam free ---
    try:
        steam_free = await get_steam_free_games()
        for game in steam_free:
            deal_id = make_deal_id("steam", game.title)
            if not await deal_exists(deal_id):
                log(f"CHECK: New Steam free: {game.title}")
                await add_known_deal(
                    deal_id, game.title, "Steam",
                    100, True, game.url, game.image
                )
                new_items.append({
                    "title": game.title,
                    "store": "Steam",
                    "discount_percent": 100,
                    "is_free": True,
                    "url": game.url,
                    "image": game.image,
                    "price": 0,
                    "original_price": 0,
                    "rating_percent": game.rating_percent,
                    "genres": game.genres,
                })

            await _update_deals_cache(game, "steam")
    except Exception as e:
        log(f"CHECK: Steam free error: {e}")

    # --- Epic free ---
    try:
        epic_free = await get_epic_free_games()
        for game in epic_free:
            deal_id = make_deal_id("epic", game.title)
            if not await deal_exists(deal_id):
                log(f"CHECK: New Epic free: {game.title}")
                await add_known_deal(
                    deal_id, game.title, "Epic Games",
                    100, True, game.url, game.image
                )
                new_items.append({
                    "title": game.title,
                    "store": "Epic Games",
                    "discount_percent": 100,
                    "is_free": True,
                    "url": game.url,
                    "image": game.image,
                    "price": 0,
                    "original_price": 0,
                    "rating_percent": game.rating_percent,
                    "genres": game.genres,
                })

            await _update_deals_cache(game, "epic")
    except Exception as e:
        log(f"CHECK: Epic free error: {e}")

    # --- Epic deals ---
    try:
        epic_deals = await get_epic_deals()
        for game in epic_deals:
            deal_id = make_deal_id("epic", game.title)
            if not await deal_exists(deal_id):
                log(f"CHECK: New Epic deal: {game.title}")
                await add_known_deal(
                    deal_id, game.title, "Epic Games",
                    game.discount_percent, False,
                    game.url, game.image
                )
                new_items.append({
                    "title": game.title,
                    "store": "Epic Games",
                    "discount_percent": game.discount_percent,
                    "is_free": False,
                    "url": game.url,
                    "image": game.image,
                    "price": _extract_price(game.discounted_price),
                    "original_price": _extract_price(game.original_price),
                    "rating_percent": game.rating_percent,
                    "genres": game.genres,
                })

            await _update_deals_cache(game, "epic")
    except Exception as e:
        log(f"CHECK: Epic deals error: {e}")

    if not new_items:
        log("CHECK: No new deals found")
        return

    log(f"CHECK: Found {len(new_items)} new deals!")

    # Отправляем уведомления с учётом фильтров пользователя
    users = await get_users_with_notifications()
    if not users:
        log("CHECK: No users with notifications enabled")
        return

    to_notify = new_items[:MAX_NOTIFICATION_DEALS]

    for user_id in users:
        # Получаем независимые фильтры уведомлений
        notif_filters = await get_user_notif_filters(user_id)

        for item in to_notify:
            try:
                # 1. Проверяем настройки пользователя
                from database import get_user_settings
                settings = await get_user_settings(user_id)
                if settings and not settings.get("notifications_enabled", True):
                    continue

                # 2. Применяем независимые фильтры уведомлений
                genres = item.get("genres", [])
                if not genres:
                    genres = get_game_genres(item["title"])
                item_genres = genres

                # Фильтр по жанрам
                selected_genres = notif_filters.get("selected_genres", [])
                if selected_genres:
                    sg_lower = [g.lower() for g in selected_genres]
                    ig_lower = [g.lower() for g in item_genres]
                    if not any(sg in ig_lower for sg in sg_lower):
                        continue

                # Фильтр по минимальной скидке
                min_discount = notif_filters.get("min_discount", 0)
                if min_discount > 0 and item["discount_percent"] < min_discount:
                    continue

                # Фильтр по платформе
                platform = notif_filters.get("platform", "all")
                if platform != "all":
                    store_lower = item["store"].lower()
                    if platform == "steam" and store_lower not in ("steam",):
                        continue
                    if platform == "epic games" and store_lower != "epic games":
                        continue

                # Фильтр по типу
                filter_type = notif_filters.get("filter_type", "all")
                if filter_type == "free" and not item["is_free"]:
                    continue
                if filter_type == "discounts" and (item["is_free"] or item["discount_percent"] <= 0):
                    continue

                # Фильтр по рейтингу
                rating_filter = notif_filters.get("rating_filter", 0)
                if rating_filter > 0 and item.get("rating_percent", 0) < rating_filter:
                    continue

                # 3. Проверяем дубликаты
                notif_type = "new_free" if item["is_free"] else "new_discount"
                if await has_recent_notification(user_id, item["title"],
                                                  item["store"], notif_type, 24):
                    continue

                # 5. Отправляем уведомление
                caption = _make_new_deal_text(item)
                await _send_notification(app, user_id, caption, item["image"])

                await add_notification_history(
                    user_id, item["title"], item["store"],
                    notif_type, item["discount_percent"], item["price"]
                )

                # ПАУЗА между уведомлениями одному пользователю
                await asyncio.sleep(NOTIFICATION_PAUSE)

            except Exception as e:
                log(f"CHECK: Failed to notify user {user_id}: {e}")

        # ПАУЗА между разными пользователями
        await asyncio.sleep(USER_PAUSE)

    log(f"CHECK: New deal notifications sent to {len(users)} users")


async def _update_deals_cache(game: GameDeal, store_prefix: str) -> None:
    """Обновляет кэш сделок в БД."""
    try:
        store = "Epic Games" if store_prefix == "epic" else "Steam"
        deal_id = make_deal_id(store, game.title)
        price = _extract_price(game.discounted_price)
        original_price = _extract_price(game.original_price)

        await add_deal_to_cache(
            deal_id=deal_id,
            title=game.title,
            store=store,
            price=price if price is not None else 0,
            original_price=original_price if original_price is not None else 0,
            discount_percent=game.discount_percent,
            is_free=game.is_free,
            url=game.url,
            image=game.image or "",
        )

        # Сохраняем историю цен
        await add_price_history(
            game.title, store,
            price if price is not None else 0,
            game.discount_percent,
            game.is_free
        )
    except Exception as e:
        log(f"Cache update error for {game.title}: {e}")


# ═══════════════════════════════════════════════════════
# Мониторинг подписок
# ═══════════════════════════════════════════════════════

async def _monitor_subscriptions_cycle(app: Application) -> None:
    """Проверяет все активные подписки и отправляет уведомления при изменениях."""
    log("MONITOR: Starting subscription check cycle...")

    subscriptions = await get_all_subscriptions()
    if not subscriptions:
        log("MONITOR: No active subscriptions")
        return

    log(f"MONITOR: Checking {len(subscriptions)} subscriptions...")

    for sub in subscriptions:
        try:
            await _check_subscription(app, sub)
        except Exception as e:
            log(f"MONITOR: Error checking sub {sub['id']}: {e}")

    log("MONITOR: Subscription check cycle completed")


async def _check_subscription(app: Application, sub: dict) -> None:
    """Проверяет одну подписку и отправляет уведомление при изменениях."""
    user_id = sub["user_id"]
    game_title = sub["game_title"]
    store = sub["store"]
    sub_id = sub["id"]

    # Получаем текущие данные об игре
    game = await get_deal_by_title(game_title, store)
    if not game:
        from database import search_deals_cache
        results = await search_deals_cache(game_title, limit=1)
        if results:
            game = results[0]
        else:
            log(f"MONITOR: Game not found: {game_title} ({store})")
            return

    # Проверяем настройки пользователя
    from database import get_user_settings
    user_settings = await get_user_settings(user_id)
    if not user_settings or not user_settings.get("notifications_enabled", True):
        return

    current_price = game.get("price")
    current_discount = game.get("discount_percent", 0)
    is_free = game.get("is_free", False)

    last_price = sub["last_known_price"]
    last_discount = sub["last_known_discount"]

    changes_detected = False
    notification_type = ""
    price_change = None
    discount_change = None

    if is_free:
        if not sub.get("notification_sent"):
            changes_detected = True
            notification_type = "became_free"
    else:
        if current_price is not None and last_price is not None:
            if current_price < last_price:
                changes_detected = True
                notification_type = "price_drop"
                price_change = current_price - last_price
        elif last_price is None and current_price is not None:
            changes_detected = True
            notification_type = "new_price"

        if current_discount > last_discount:
            changes_detected = True
            notification_type = "bigger_discount"
            discount_change = current_discount - last_discount

    if not changes_detected:
        await update_subscription_price(sub_id, current_price, current_discount)
        return

    if await has_recent_notification(user_id, game_title, store, notification_type, 24):
        log(f"MONITOR: Skipping duplicate notification for {game_title} to {user_id}")
        await update_subscription_price(sub_id, current_price, current_discount)
        return

    caption = _make_subscription_notification(
        game_title, store, notification_type,
        current_price, current_discount,
        is_free, price_change, discount_change,
        game.get("url", "")
    )

    image = game.get("image", "")
    await _send_notification(app, user_id, caption, image)

    await add_notification_history(
        user_id, game_title, store,
        notification_type, current_discount, current_price
    )

    await update_subscription_price(sub_id, current_price, current_discount)
    await mark_subscription_notified(sub_id)

    await asyncio.sleep(NOTIFICATION_PAUSE)
    log(f"MONITOR: Sent {notification_type} notification for {game_title} to user {user_id}")


# ═══════════════════════════════════════════════════════
# Форматирование уведомлений
# ═══════════════════════════════════════════════════════

def _make_new_deal_text(item: dict) -> str:
    title = html.escape(item["title"])
    store = item["store"]
    discount = item["discount_percent"]
    is_free = item["is_free"]

    if is_free:
        return (
            f"🆓 <b>Игра стала бесплатной!</b>\n\n"
            f"🎮 <b>{title}</b>\n"
            f"🏪 {store}\n\n"
            f"💰 <b>БЕСПЛАТНО</b>\n\n"
            f"Успей забрать, пока раздача активна.\n\n"
            f'🔗 <a href="{item.get("url", "")}">Забрать игру</a>'
        )
    else:
        return (
            f"🔥 <b>Новая скидка!</b>\n\n"
            f"🎮 <b>{title}</b>\n"
            f"💸 Скидка: -{discount}%\n"
            f"🏪 {store}\n\n"
            f'🔗 <a href="{item.get("url", "")}">Открыть магазин</a>'
        )


def _make_subscription_notification(title: str, store: str,
                                     notification_type: str,
                                     current_price: Optional[float],
                                     current_discount: int,
                                     is_free: bool,
                                     price_change: Optional[float],
                                     discount_change: Optional[int],
                                     url: str) -> str:
    safe_title = html.escape(title)

    if is_free or notification_type == "became_free":
        return (
            f"🆓 <b>Игра стала бесплатной!</b>\n\n"
            f"🎮 <b>{safe_title}</b>\n"
            f"🏪 {store}\n\n"
            f"💰 <b>БЕСПЛАТНО</b>\n\n"
            f"Успей забрать, пока раздача активна.\n\n"
            f'🔗 <a href="{url}">Забрать игру</a>'
        )

    if notification_type == "price_drop":
        text = (
            f"📉 <b>Цена снизилась!</b>\n\n"
            f"🎮 <b>{safe_title}</b>\n"
            f"🏪 {store}\n"
        )
        if current_price is not None:
            text += f"💰 Новая цена: <b>{current_price:.0f}₽</b>\n"
        if price_change is not None:
            text += f"📊 Снижение: {abs(price_change):.0f}₽\n"
        if current_discount > 0:
            text += f"🔥 Скидка: -{current_discount}%\n"
        text += f'\n🔗 <a href="{url}">Открыть магазин</a>'
        return text

    if notification_type == "bigger_discount":
        text = (
            f"🔥 <b>Скидка увеличилась!</b>\n\n"
            f"🎮 <b>{safe_title}</b>\n"
            f"🏪 {store}\n"
        )
        if current_discount > 0:
            text += f"💸 Скидка: <b>-{current_discount}%</b>\n"
        if discount_change is not None:
            text += f"📈 Ещё -{discount_change}%\n"
        if current_price is not None:
            text += f"💰 Цена: <b>{current_price:.0f}₽</b>\n"
        text += f'\n🔗 <a href="{url}">Открыть магазин</a>'
        return text

    return (
        f"🔔 <b>Обновление цены</b>\n\n"
        f"🎮 <b>{safe_title}</b>\n"
        f"🏪 {store}\n"
        f"{f'💰 Цена: <b>{current_price:.0f}₽</b>\n' if current_price is not None else ''}"
        f"{f'🔥 Скидка: -{current_discount}%\n' if current_discount > 0 else ''}"
        f'\n🔗 <a href="{url}">Открыть магазин</a>'
    )


async def _send_notification(app: Application, user_id: int,
                              caption: str, image: str = "") -> None:
    if image:
        try:
            await app.bot.send_photo(
                chat_id=user_id,
                photo=image,
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            return
        except Exception as e:
            log(f"Failed to send photo to {user_id}: {e}")
            try:
                await app.bot.send_photo(
                    chat_id=user_id,
                    photo=FALLBACK_IMAGE,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
                return
            except:
                pass

    try:
        await app.bot.send_message(
            chat_id=user_id,
            text=caption,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        log(f"Failed to send message to {user_id}: {e}")


def _extract_price(price_str: str) -> Optional[float]:
    if not price_str or price_str in ("—", "БЕСПЛАТНО", "Со скидкой"):
        return None
    try:
        price = price_str.replace("$", "").replace("₽", "").replace(",", ".").strip()
        return float(price)
    except (ValueError, AttributeError):
        return None


# ─── Совместимость со старым кодом ──────────────

async def check_and_notify(app: Application) -> None:
    """Старая функция для обратной совместимости."""
    await start_background_tasks(app)