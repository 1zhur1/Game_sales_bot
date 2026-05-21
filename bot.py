import sys
import logging
import os
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# ═══════════════════════════════════════════════════════════════
# 1. START HEALTH SERVER IMMEDIATELY — before ANY other imports
# ═══════════════════════════════════════════════════════════════

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def _run_health():
    port = int(os.getenv("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    server.serve_forever()

t = Thread(target=_run_health, daemon=True)
t.start()

# ═══════════════════════════════════════════════════════════════
# 2. Now safe to import the rest
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

logger.info("Health server started, now importing modules")

try:

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

    logger.info("All modules imported successfully")

except Exception as e:
    logger.error("Failed to import modules: %s", e)
    while True:
        time.sleep(60)
        logger.info("Alive (import error: %s)", e)


# ═══════════════════════════════════════════════════════════════
# 3. Main bot logic
# ═══════════════════════════════════════════════════════════════

def main():

    try:

        logger.info("Checking BOT_TOKEN")

        if not BOT_TOKEN:
            logger.error("BOT_TOKEN environment variable is not set!")
            logger.error("Go to Render Dashboard → Environment → add BOT_TOKEN")
            while True:
                time.sleep(60)
                logger.info("Still alive, waiting for BOT_TOKEN...")

        logger.info("BOT_TOKEN found, building application")

        app = Application.builder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))

        app.add_handler(
            CallbackQueryHandler(main_menu_callback, pattern="^main_menu$")
        )
        app.add_handler(
            CallbackQueryHandler(deals_menu_callback, pattern="^deals_menu$")
        )
        app.add_handler(
            CallbackQueryHandler(free_menu_callback, pattern="^free_menu$")
        )
        app.add_handler(
            CallbackQueryHandler(steam_deals_callback, pattern="^steam_deals_")
        )
        app.add_handler(
            CallbackQueryHandler(epic_deals_callback, pattern="^epic_deals_")
        )
        app.add_handler(
            CallbackQueryHandler(epic_free_callback, pattern="^epic_free_")
        )
        app.add_handler(
            CallbackQueryHandler(steam_free_callback, pattern="^steam_free_")
        )

        logger.info("Bot is running")
        app.run_polling()

    except Exception as e:
        logger.error("Bot crashed: %s", e)
        while True:
            time.sleep(60)
            logger.info("Alive (bot error: %s)", e)


if __name__ == "__main__":
    main()