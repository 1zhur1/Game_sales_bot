from telegram.constants import ParseMode

from keyboards import filtered_nav_keyboard
from utils import format_game
from services.subscription_service import ensure_subscription
from services.epic_service import get_epic_deals
from services.filter_service import apply_filters
from database import get_user_filters


async def epic_deals_callback(update, context):

    query = update.callback_query

    await query.answer()

    if not await ensure_subscription(query, context):
        return

    index = int(query.data.split("_")[-1])

    games = await get_epic_deals()

    if not games:
        await query.message.reply_text(
            "😕 В Epic Games пока нет активных скидок.\n"
            "Загляни позже!"
        )
        return

    # Применяем фильтры пользователя
    user_id = query.from_user.id
    filters = await get_user_filters(user_id)
    filtered = apply_filters(
        games,
        selected_genres=filters.get("selected_genres"),
        min_discount=filters.get("min_discount", 0),
        max_price=filters.get("max_price", 0),
        platform="epic games",
        filter_type="discounts",
        sort_type=filters.get("sort_type", "discount"),
        rating_filter=filters.get("rating_filter", 0),
    )

    if not filtered:
        await query.message.reply_text(
            "😕 Ничего не нашлось под твои фильтры.\n"
            "Попробуй изменить настройки в разделе 🎯 Фильтры.",
        )
        return

    index = max(0, min(index, len(filtered) - 1))

    game = filtered[index]

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
            len(filtered)
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=filtered_nav_keyboard(
            "epic_deals",
            index,
            len(filtered)
        )
    )