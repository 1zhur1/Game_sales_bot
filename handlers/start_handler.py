"""
🎮 GameHub — Стартовый экран.

Приветствие нового пользователя.
Премиальный вход в игровой центр.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from keyboards import main_menu
from services.subscription_service import check_subscription
from database import add_user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ok = await check_subscription(
        update.effective_user.id,
        context.bot,
    )

    if not ok:
        await update.message.reply_text(
            "❌ Подпишись на канал @WTF_steam, чтобы пользоваться ботом."
        )
        return

    # Регистрируем пользователя в БД
    await add_user(update.effective_user.id)

    welcome_text = (
        "🎮 <b>Добро пожаловать в GameHub!</b>\n\n"
        "Твой персональный центр игр.\n"
        "🔥 Скидки Steam и Epic\n"
        "🎁 Бесплатные игры\n"
        "🔔 Уведомления о снижении цен\n"
        "❤️ Избранное и подписки\n\n"
        "Всё, чтобы не переплачивать за игры.\n\n"
        "Выбери раздел: 👇"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )