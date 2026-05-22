import sys
import os
import time
import asyncio
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
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        server.serve_forever()
    except OSError:
        pass


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

    from config import BOT_TOKEN
    from database import init_db

    init_db()

    from handlers.start_handler import start
    from handlers.menu_handler import (
        main_menu_callback, store_menu_callback, free_menu_callback,
        top_menu_callback, my_menu_callback,
    )
    from handlers.steam_handler import steam_deals_callback
    from handlers.epic_handler import epic_deals_callback
    from handlers.free_handler import epic_free_callback, steam_free_callback
    from handlers.subscription_handler import (
        subscribe_menu_callback, subscribe_search_callback,
        handle_subscribe_text, subscribe_choose_callback,
        subscribe_confirm_callback, unsubscribe_callback,
        my_subscriptions_callback, favorite_callback,
        my_favorites_callback, game_info_callback,
    )
    from handlers.settings_handler import (
        settings_menu_callback, settings_toggle_notif_callback,
        notif_filters_menu_callback, notif_filters_genres_callback,
        notif_filters_genre_toggle_callback, notif_filters_genre_done_callback,
        notif_filters_discount_callback, notif_filters_set_discount_callback,
        notif_filters_platform_callback, notif_filters_set_platform_callback,
        notif_filters_type_callback, notif_filters_set_type_callback,
        notif_filters_rating_callback, notif_filters_set_rating_callback,
        notif_filters_reset_callback,
    )
    from handlers.filter_handler import (
        filters_menu_callback, filters_genres_callback,
        filters_genre_toggle_callback, filters_genres_done_callback,
        filters_discount_callback, filters_set_discount_callback,
        filters_price_callback, filters_set_price_callback,
        filters_platform_callback, filters_set_platform_callback,
        filters_type_callback, filters_set_type_callback,
        filters_sort_callback, filters_set_sort_callback,
        filters_rating_callback, filters_set_rating_callback,
        filters_reset_callback,
    )
    from services.notification_service import (
        check_new_deals_loop, monitor_subscriptions_loop,
    )

    log("All modules imported successfully")

except Exception as e:
    log(f"IMPORT ERROR: {e}")
    import traceback
    log(traceback.format_exc())
    while True:
        time.sleep(60)


# ═══════════════════════════════════════════════════════════════
# REGISTER HANDLERS
# ═══════════════════════════════════════════════════════════════

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(store_menu_callback, pattern="^store_menu$"))
    app.add_handler(CallbackQueryHandler(steam_deals_callback, pattern="^steam_deals_"))
    app.add_handler(CallbackQueryHandler(epic_deals_callback, pattern="^epic_deals_"))
    app.add_handler(CallbackQueryHandler(free_menu_callback, pattern="^free_menu$"))
    app.add_handler(CallbackQueryHandler(epic_free_callback, pattern="^epic_free_"))
    app.add_handler(CallbackQueryHandler(steam_free_callback, pattern="^steam_free_"))
    app.add_handler(CallbackQueryHandler(top_menu_callback, pattern="^top_menu$"))
    app.add_handler(CallbackQueryHandler(top_menu_callback, pattern="^recommendations$"))
    app.add_handler(CallbackQueryHandler(top_menu_callback, pattern="^popular$"))
    app.add_handler(CallbackQueryHandler(top_menu_callback, pattern="^new_releases$"))
    app.add_handler(CallbackQueryHandler(my_menu_callback, pattern="^my_menu$"))
    app.add_handler(CallbackQueryHandler(subscribe_menu_callback, pattern="^subscribe_menu$"))
    app.add_handler(CallbackQueryHandler(subscribe_search_callback, pattern="^subscribe_search$"))
    app.add_handler(CallbackQueryHandler(subscribe_choose_callback, pattern="^sub_choose_"))
    app.add_handler(CallbackQueryHandler(subscribe_confirm_callback, pattern="^sub_confirm_"))
    app.add_handler(CallbackQueryHandler(unsubscribe_callback, pattern="^unsub_"))
    app.add_handler(CallbackQueryHandler(my_subscriptions_callback, pattern="^my_subscriptions_"))
    app.add_handler(CallbackQueryHandler(favorite_callback, pattern="^fav_"))
    app.add_handler(CallbackQueryHandler(my_favorites_callback, pattern="^my_favorites_"))
    app.add_handler(CallbackQueryHandler(game_info_callback, pattern="^game_info_"))
    app.add_handler(CallbackQueryHandler(settings_menu_callback, pattern="^settings_menu$"))
    app.add_handler(CallbackQueryHandler(settings_toggle_notif_callback, pattern="^settings_toggle_notif$"))
    app.add_handler(CallbackQueryHandler(notif_filters_menu_callback, pattern="^settings_notif_filters$"))
    app.add_handler(CallbackQueryHandler(notif_filters_genres_callback, pattern="^nf_genres$"))
    app.add_handler(CallbackQueryHandler(notif_filters_genre_toggle_callback, pattern="^nf_genre_"))
    app.add_handler(CallbackQueryHandler(notif_filters_genre_done_callback, pattern="^nf_genre_done$"))
    app.add_handler(CallbackQueryHandler(notif_filters_discount_callback, pattern="^nf_discount$"))
    app.add_handler(CallbackQueryHandler(notif_filters_set_discount_callback, pattern="^nf_set_discount_"))
    app.add_handler(CallbackQueryHandler(notif_filters_platform_callback, pattern="^nf_platform$"))
    app.add_handler(CallbackQueryHandler(notif_filters_set_platform_callback, pattern="^nf_set_platform_"))
    app.add_handler(CallbackQueryHandler(notif_filters_type_callback, pattern="^nf_type$"))
    app.add_handler(CallbackQueryHandler(notif_filters_set_type_callback, pattern="^nf_set_type_"))
    app.add_handler(CallbackQueryHandler(notif_filters_rating_callback, pattern="^nf_rating$"))
    app.add_handler(CallbackQueryHandler(notif_filters_set_rating_callback, pattern="^nf_set_rating_"))
    app.add_handler(CallbackQueryHandler(notif_filters_reset_callback, pattern="^nf_reset$"))
    app.add_handler(CallbackQueryHandler(filters_menu_callback, pattern="^filters_menu$"))
    app.add_handler(CallbackQueryHandler(filters_genres_callback, pattern="^filters_genres$"))
    app.add_handler(CallbackQueryHandler(filters_genre_toggle_callback, pattern="^fgenre_toggle_"))
    app.add_handler(CallbackQueryHandler(filters_genres_done_callback, pattern="^fgenre_done$"))
    app.add_handler(CallbackQueryHandler(filters_discount_callback, pattern="^filters_discount$"))
    app.add_handler(CallbackQueryHandler(filters_set_discount_callback, pattern="^fset_discount_"))
    app.add_handler(CallbackQueryHandler(filters_price_callback, pattern="^filters_price$"))
    app.add_handler(CallbackQueryHandler(filters_set_price_callback, pattern="^fset_price_"))
    app.add_handler(CallbackQueryHandler(filters_platform_callback, pattern="^filters_platform$"))
    app.add_handler(CallbackQueryHandler(filters_set_platform_callback, pattern="^fset_platform_"))
    app.add_handler(CallbackQueryHandler(filters_type_callback, pattern="^filters_type$"))
    app.add_handler(CallbackQueryHandler(filters_set_type_callback, pattern="^fset_type_"))
    app.add_handler(CallbackQueryHandler(filters_sort_callback, pattern="^filters_sort$"))
    app.add_handler(CallbackQueryHandler(filters_set_sort_callback, pattern="^fset_sort_"))
    app.add_handler(CallbackQueryHandler(filters_rating_callback, pattern="^filters_rating$"))
    app.add_handler(CallbackQueryHandler(filters_set_rating_callback, pattern="^fset_rating_"))
    app.add_handler(CallbackQueryHandler(filters_reset_callback, pattern="^filters_reset$"))
    app.add_handler(
        CallbackQueryHandler(
            lambda update, context: update.callback_query.answer(),
            pattern="^ignore$",
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_subscribe_text,
        )
    )


# ═══════════════════════════════════════════════════════════════
# POST INIT - запуск фоновых задач через JobQueue
# ═══════════════════════════════════════════════════════════════

async def post_init(app):
    """
    Запускает фоновые задачи через job_queue.
    JobQueue гарантированно работает в правильном event loop'е.
    """
    from config import NOTIFICATION_INTERVAL, MONITOR_INTERVAL

    try:
        # JobQueue run_repeating запускает корутину в правильном loop'е
        # Первый запуск через 10 секунд после старта, потом каждый час
        app.job_queue.run_repeating(
            check_new_deals_loop,
            interval=NOTIFICATION_INTERVAL,
            first=10.0,  # первый раз через 10 секунд
            name="check_new_deals",
        )

        # Мониторинг подписок каждые 30 минут, первый раз через 60 секунд
        app.job_queue.run_repeating(
            monitor_subscriptions_loop,
            interval=MONITOR_INTERVAL,
            first=60.0,  # первый раз через 60 секунд
            name="monitor_subscriptions",
        )

        log("Background jobs scheduled via JobQueue")
    except Exception as e:
        log(f"Failed to schedule background jobs: {e}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def run_bot():
    """Запускает бота с собственным event loop."""
    log("Starting bot...")

    if not BOT_TOKEN:
        log("ERROR: BOT_TOKEN missing")
        return

    # Создаём свежий event loop для этого запуска
    # Это критично — run_polling закрывает loop после остановки,
    # и следующий запуск упадёт с "Event loop is closed"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    log("Application created")

    register_handlers(app)
    log("Handlers registered")
    logger.info("Bot started successfully")

    try:
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            log("Event loop was closed (expected after shutdown)")
        else:
            log(f"RuntimeError: {e}")
    except Exception as e:
        log(f"Bot error: {e}")

def main():
    while True:
        try:
            run_bot()
            break  # нормальное завершение
        except KeyboardInterrupt:
            log("Bot stopped by user")
            break
        except Exception as e:
            log(f"Bot crashed: {e}")
            import traceback
            log(traceback.format_exc())
            log("Restarting in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    main()