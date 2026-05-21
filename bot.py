from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from config import BOT_TOKEN

from handlers.start_handler import start
from handlers.menu_handler import (
    main_menu_callback,
    deals_menu_callback,
    free_menu_callback,
)

from handlers.steam_handler import steam_deals_callback
from handlers.epic_handler import epic_deals_callback
from handlers.free_handler import (
    epic_free_callback,
    steam_free_callback,
)

import logging

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


def main():

    logger.info("Bot started")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(
            main_menu_callback,
            pattern="^main_menu$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            deals_menu_callback,
            pattern="^deals_menu$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            free_menu_callback,
            pattern="^free_menu$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            steam_deals_callback,
            pattern="^steam_deals_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            epic_deals_callback,
            pattern="^epic_deals_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            epic_free_callback,
            pattern="^epic_free_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            steam_free_callback,
            pattern="^steam_free_"
        )
    )

    logger.info("Bot running")

    app.run_polling()


if __name__ == "__main__":
    main()