from telegram.constants import ParseMode

from keyboards import nav_keyboard

from utils import format_game

from services.subscription_service import ensure_subscription
from services.steam_service import get_steam_deals


async def steam_deals_callback(update, context):

    query = update.callback_query

    await query.answer()

    if not await ensure_subscription(query, context):
        return

    index = int(query.data.split("_")[-1])

    games = await get_steam_deals()

    if not games:

        await query.message.reply_text(
            "❌ Steam скидки не найдены"
        )

        return

    index = max(0, min(index, len(games) - 1))

    game = games[index]

    try:
        await query.message.delete()
    except:
        pass

    await context.bot.send_photo(
        chat_id=query.message.chat.id,
        photo=game.image,
        caption=format_game(
            game,
            index,
            len(games)
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=nav_keyboard(
            "steam_deals",
            index,
            len(games)
        )
    )