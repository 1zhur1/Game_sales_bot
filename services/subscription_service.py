from telegram import InlineKeyboardMarkup
from telegram import InlineKeyboardButton

from config import CHANNEL_USERNAME


async def check_subscription(user_id, bot):

    try:

        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except:
        return False


async def ensure_subscription(query, context):

    ok = await check_subscription(
        query.from_user.id,
        context.bot
    )

    if ok:
        return True

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 Подписаться",
                url="https://t.me/WTF_steam"
            )
        ]
    ])

    await query.message.reply_text(
        "❌ Подпишитесь на канал.",
        reply_markup=keyboard
    )

    return False