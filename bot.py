import sys
import os
import time
import asyncio  # 👈 Added for the Python 3.14 event loop fix
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ═══════════════════════════════════════════════════════════════
# HEALTH SERVER FOR RENDER
# ═══════════════════════════════════════════════════════════════

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return


def run_health_server():
    port = int(os.getenv("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


Thread(target=run_health_server, daemon=True).start()

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

def log(message):
    print(f"BOT: {message}", flush=True)


log("Health server started")

import logging

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════

try:
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        MessageHandler,
        filters,
    )

    log("telegram.ext imported")

    from config import BOT_TOKEN

    log(f"BOT_TOKEN loaded: {'YES' if BOT_TOKEN else 'NO'}")

    from database import init_db

    init_db()
    log("Database initialized")

    from handlers.start_handler import start

    log("start_handler imported")

    from handlers.menu_handler import (
        main_menu_callback,
        deals_menu_callback,
        free_menu_callback,
    )

    log("menu_handler imported")

    from handlers.steam_handler import steam_deals_callback

    log("steam_handler imported")

    from handlers.epic_handler import epic_deals_callback

    log("epic_handler imported")

    from handlers.free_handler import (
        epic_free_callback,
        steam_free_callback,
    )

    log("free_handler imported")

    from handlers.subscription_handler import (
        subscribe_menu_callback,
        subscribe_search_callback,
        handle_subscribe_text,
        subscribe_choose_callback,
        subscribe_confirm_callback,
        unsubscribe_callback,
        my_subscriptions_callback,
        favorite_callback,
        my_favorites_callback,
        game_info_callback,
    )

    log("subscription_handler imported")

    from handlers.settings_handler import (
        settings_menu_callback,
        settings_toggle_notif_callback,
        settings_min_discount_callback,
        set_min_discount_callback,
    )

    log("settings_handler imported")

    from services.notification_service import check_and_notify

    log("notification_service imported")

except Exception as e:
    log(f"IMPORT ERROR: {e}")

    import traceback

    log(traceback.format_exc())

    while True:
        time.sleep(60)

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():

    log("Starting bot...")

    if not BOT_TOKEN:
        log("ERROR: BOT_TOKEN missing")

        while True:
            time.sleep(60)

    try:
        app = Application.builder().token(BOT_TOKEN).build()

        log("Application created")

        # ─── COMMANDS ───────────────────────────
        app.add_handler(CommandHandler("start", start))

        # ─── MAIN MENU ──────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                main_menu_callback,
                pattern="^main_menu$"
            )
        )

        # ─── DEALS MENU ─────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                deals_menu_callback,
                pattern="^deals_menu$"
            )
        )

        # ─── FREE MENU ──────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                free_menu_callback,
                pattern="^free_menu$"
            )
        )

        # ─── STEAM DEALS ────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                steam_deals_callback,
                pattern="^steam_deals_"
            )
        )

        # ─── EPIC DEALS ─────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                epic_deals_callback,
                pattern="^epic_deals_"
            )
        )

        # ─── EPIC FREE ──────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                epic_free_callback,
                pattern="^epic_free_"
            )
        )

        # ─── STEAM FREE ─────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                steam_free_callback,
                pattern="^steam_free_"
            )
        )

        # ─── SUBSCRIPTION MENU ──────────────────
        app.add_handler(
            CallbackQueryHandler(
                subscribe_menu_callback,
                pattern="^subscribe_menu$"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                subscribe_search_callback,
                pattern="^subscribe_search$"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                subscribe_choose_callback,
                pattern="^sub_choose_"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                subscribe_confirm_callback,
                pattern="^sub_confirm_"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                unsubscribe_callback,
                pattern="^unsub_"
            )
        )

        # ─── MY SUBSCRIPTIONS ───────────────────
        app.add_handler(
            CallbackQueryHandler(
                my_subscriptions_callback,
                pattern="^my_subscriptions_"
            )
        )

        # ─── FAVORITES ──────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                favorite_callback,
                pattern="^fav_"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                my_favorites_callback,
                pattern="^my_favorites_"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                game_info_callback,
                pattern="^game_info_"
            )
        )

        # ─── SETTINGS ───────────────────────────
        app.add_handler(
            CallbackQueryHandler(
                settings_menu_callback,
                pattern="^settings_menu$"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                settings_toggle_notif_callback,
                pattern="^settings_toggle_notif$"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                settings_min_discount_callback,
                pattern="^settings_min_discount$"
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                set_min_discount_callback,
                pattern="^set_min_discount_"
            )
        )

        # ─── IGNORE CALLBACK ────────────────────
        app.add_handler(
            CallbackQueryHandler(
                lambda update, context: update.callback_query.answer(),
                pattern="^ignore$"
            )
        )

        # ─── TEXT HANDLER (для поиска игр) ──────
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                handle_subscribe_text
            )
        )

        log("Handlers registered")
        logger.info("Bot started successfully")

        # 👇 FIX: Ensure an event loop exists for the MainThread in Python 3.14
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Запускаем фоновые задачи
        loop = asyncio.get_event_loop()
        loop.create_task(check_and_notify(app))

        log("Background tasks started")

        app.run_polling()

    except Exception as e:
        log(f"BOT ERROR: {e}")

        import traceback

        log(traceback.format_exc())

        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()