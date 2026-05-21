from telegram import Update
from telegram.ext import ContextTypes

from keyboards import main_menu
from services.subscription_service import check_subscription
from database import add_user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ok = await check_subscription(
        update.effective_user.id,
        context.bot
    )

    if not ok:

        await update.message.reply_text(
            "❌ Подпишитесь на канал @WTF_steam"
        )

        return

    # Регистрируем пользователя в БД
    await add_user(update.effective_user.id)

    await update.message.reply_text(
        "🔥 WTF Steam Bot",
        reply_markup=main_menu()
    )
