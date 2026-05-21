import sys
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
# 2. Print-based logging (more reliable on Render than logging module)
# ═══════════════════════════════════════════════════════════════

def log(msg):
    print(f"BOT: {msg}", flush=True)

log("Health server started, importing modules...")

import logging

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

try:

    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
    )
    log("telegram.ext imported")

    from config import BOT_TOKEN
    log(f"config imported, BOT_TOKEN={'set' if BOT_TOKEN else 'MISSING!'}")

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

    logger.info("All modules imported successfully")

except Exception as e:
    log(f"IMPORT ERROR: {e}")
    import traceback
    log(traceback.format_exc())
    while True:
        time.sleep(60)
        log("Alive (import error)")


# ═══════════════════════════════════════════════════════════════
# 3. Main bot logic
# ═══════════════════════════════════════════════════════════════

def main():

    log("Entering main()")

    if not BOT_TOKEN:
        log("FATAL: BOT_TOKEN is empty!")
        while True:
            time.sleep(60)

    log("Building Application...")

    try:
        app = Application.builder().token(BOT_TOKEN).build()
        log("Application built")

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
        app.add_handler(CallbackQueryHandler(deals_menu_callback, pattern="^deals_menu$"))
        app.add_handler(CallbackQueryHandler(free_menu_callback, pattern="^free_menu$"))
        app.add_handler(CallbackQueryHandler(steam_deals_callback, pattern="^steam_deals_"))
        app.add_handler(CallbackQueryHandler(epic_deals_callback, pattern="^epic_deals_"))
        app.add_handler(CallbackQueryHandler(epic_free_callback, pattern="^epic_free_"))
        app.add_handler(CallbackQueryHandler(steam_free_callback, pattern="^steam_free_"))
        log("Handlers registered")

        logger.info("Bot is running")
        log("Starting polling...")
        app.run_polling()

    except Exception as e:
        log(f"BOT ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        while True:
            time.sleep(60)
            log("Alive (bot error)")


if __name__ == "__main__":
    main()