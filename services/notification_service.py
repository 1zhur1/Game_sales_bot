import asyncio
import time
import html

from telegram.ext import Application
from telegram.constants import ParseMode

from config import NOTIFICATION_INTERVAL, MAX_NOTIFICATION_DEALS
from database import (
    add_known_deal,
    deal_exists,
    get_all_active_users,
    make_deal_id,
)
from models import GameDeal
from utils import format_game

log = print

NEW_DEALS: dict[str, GameDeal] = {}


async def check_and_notify(app: Application) -> None:
    """Периодическая проверка — обнаруживает новые скидки/халяву и шлёт уведомления."""
    while True:
        try:
            await _check_cycle(app)
        except Exception as e:
            log(f"NOTIFY ERROR: {e}")
            import traceback
            log(traceback.format_exc())

        await asyncio.sleep(NOTIFICATION_INTERVAL)


async def _check_cycle(app: Application) -> None:
    """Один цикл проверки всех источников."""
    from services.steam_service import get_steam_deals, get_steam_free_games
    from services.epic_service import get_epic_free_games, get_epic_deals

    log("NOTIFY: Starting check cycle...")

    new_items: list[GameDeal] = []

    # --- Steam deals ---
    try:
        steam_deals = await get_steam_deals()
        for game in steam_deals:
            did = make_deal_id("steam", game.title)
            if not await deal_exists(did):
                await add_known_deal(
                    did, game.title, "Steam",
                    game.discount_percent, False,
                    game.url, game.image
                )
                new_items.append(game)
    except Exception as e:
        log(f"NOTIFY: Steam deals error: {e}")

    # --- Steam free ---
    try:
        steam_free = await get_steam_free_games()
        for game in steam_free:
            did = make_deal_id("steam", game.title)
            if not await deal_exists(did):
                await add_known_deal(
                    did, game.title, "Steam",
                    100, True, game.url, game.image
                )
                new_items.append(game)
    except Exception as e:
        log(f"NOTIFY: Steam free error: {e}")

    # --- Epic free ---
    try:
        epic_free = await get_epic_free_games()
        for game in epic_free:
            did = make_deal_id("epic", game.title)
            if not await deal_exists(did):
                await add_known_deal(
                    did, game.title, "Epic Games",
                    100, True, game.url, game.image
                )
                new_items.append(game)
    except Exception as e:
        log(f"NOTIFY: Epic free error: {e}")

    # --- Epic deals ---
    try:
        epic_deals = await get_epic_deals()
        for game in epic_deals:
            did = make_deal_id("epic", game.title)
            if not await deal_exists(did):
                await add_known_deal(
                    did, game.title, "Epic Games",
                    game.discount_percent, False,
                    game.url, game.image
                )
                new_items.append(game)
    except Exception as e:
        log(f"NOTIFY: Epic deals error: {e}")

    if not new_items:
        log("NOTIFY: No new deals found")
        return

    log(f"NOTIFY: Found {len(new_items)} new deals!")

    # Отправляем уведомления всем активным пользователям
    users = await get_all_active_users()
    if not users:
        log("NOTIFY: No active users to notify")
        return

    # Ограничиваем количество уведомлений
    to_notify = new_items[:MAX_NOTIFICATION_DEALS]

    for user_id in users:
        for game in to_notify:
            try:
                caption = _make_notification_text(game)
                if game.image:
                    await app.bot.send_photo(
                        chat_id=user_id,
                        photo=game.image,
                        caption=caption,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=caption,
                        parse_mode=ParseMode.HTML
                    )
                await asyncio.sleep(0.05)  # flood control
            except Exception as e:
                log(f"NOTIFY: Failed to send to {user_id}: {e}")

    log(f"NOTIFY: Notifications sent to {len(users)} users")


def _make_notification_text(game: GameDeal) -> str:
    """Формирует текст уведомления по шаблону."""
    title = html.escape(game.title)

    if game.is_free:
        return (
            f"🎁 <b>НОВАЯ ХАЛЯВА!</b>\n\n"
            f"🎮 <b>{title}</b>\n"
            f"🏪 {game.store}\n\n"
            f"💰 <b>БЕСПЛАТНО</b>\n"
            f"⭐ {game.rating_text}\n\n"
            f'🔗 <a href="{game.url}">Забрать</a>'
        )
    else:
        return (
            f"🔥 <b>НОВАЯ СКИДКА!</b>\n\n"
            f"🎮 <b>{title}</b>\n"
            f"🏪 {game.store}\n\n"
            f"💸 <b>{game.discounted_price}</b>\n"
            f"🏷 <s>{game.original_price}</s>\n"
            f"📉 -{game.discount_percent}%\n"
            f"⭐ {game.rating_percent}%\n\n"
            f'🔗 <a href="{game.url}">Открыть магазин</a>'
        )