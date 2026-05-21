from keyboards import (
    main_menu,
    deals_menu_keyboard,
    free_menu_keyboard,
)

from services.subscription_service import ensure_subscription


async def main_menu_callback(update, context):

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
        text="🏠 Главное меню",
        reply_markup=main_menu()
    )


async def deals_menu_callback(update, context):

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
        text="🔥 Раздел скидок",
        reply_markup=deals_menu_keyboard()
    )


async def free_menu_callback(update, context):

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
        text="🎁 Раздел халявы",
        reply_markup=free_menu_keyboard()
    )
