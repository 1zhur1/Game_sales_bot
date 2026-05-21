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

        # COMMANDS
        app.add_handler(CommandHandler("start", start))

        # MAIN MENU
        app.add_handler(
            CallbackQueryHandler(
                main_menu_callback,
                pattern="^main_menu$"
            )
        )

        # DEALS MENU
        app.add_handler(
            CallbackQueryHandler(
                deals_menu_callback,
                pattern="^deals_menu$"
            )
        )

        # FREE MENU
        app.add_handler(
            CallbackQueryHandler(
                free_menu_callback,
                pattern="^free_menu$"
            )
        )

        # STEAM DEALS
        app.add_handler(
            CallbackQueryHandler(
                steam_deals_callback,
                pattern="^steam_deals_"
            )
        )

        # EPIC DEALS
        app.add_handler(
            CallbackQueryHandler(
                epic_deals_callback,
                pattern="^epic_deals_"
            )
        )

        # EPIC FREE
        app.add_handler(
            CallbackQueryHandler(
                epic_free_callback,
                pattern="^epic_free_"
            )
        )

        # STEAM FREE
        app.add_handler(
            CallbackQueryHandler(
                steam_free_callback,
                pattern="^steam_free_"
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

        # Запускаем фоновую задачу уведомлений
        loop = asyncio.get_event_loop()
        loop.create_task(check_and_notify(app))

        log("Notification task created")

        app.run_polling()

    except Exception as e:
        log(f"BOT ERROR: {e}")

        import traceback

        log(traceback.format_exc())

        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()