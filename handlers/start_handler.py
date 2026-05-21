from telegram import Update
from telegram.ext import ContextTypes

from keyboards import main_menu
from services.subscription_service import check_subscription


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

    await update.message.reply_text(
        "🔥 WTF Steam Bot",
        reply_markup=main_menu()
    )