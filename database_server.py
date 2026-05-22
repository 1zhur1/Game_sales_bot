#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  🗄️  Database Server — отдельный процесс для SQLite         ║
║                                                              ║
║  Держит БД открытой постоянно, обрабатывает запросы          ║
║  от бота через HTTP API на порту 5001.                       ║
║  Это решает проблему "database is locked" и ускоряет         ║
║  работу, т.к. не нужно открывать/закрывать соединение        ║
║  на каждый запрос.                                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import sqlite3
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from threading import Lock

# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")
HOST = "127.0.0.1"
PORT = 5001

logging.basicConfig(
    format="%(asctime)s | DBSRV | %(levelname)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("database_server")


# ═══════════════════════════════════════════════════════════════
# ПОДКЛЮЧЕНИЕ К БД (постоянное)
# ═══════════════════════════════════════════════════════════════

class DatabaseConnection:
    """
    Постоянное соединение с БД.
    Открывается один раз и держится всё время работы сервера.
    Использует WAL режим для конкурентного доступа.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: sqlite3.Connection = None
        self.lock = Lock()

    def connect(self):
        """Открывает соединение с БД и настраивает его."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.row_factory = sqlite3.Row
        logger.info(f"✅ Connected to database: {self.db_path} (WAL mode)")

    def execute(self, sql: str, params: tuple = ()) -> dict:
        """Выполняет запрос на запись (INSERT, UPDATE, DELETE)."""
        with self.lock:
            try:
                cur = self.conn.execute(sql, params)
                self.conn.commit()
                return {
                    "success": True,
                    "rowcount": cur.rowcount,
                    "lastrowid": cur.lastrowid,
                }
            except Exception as e:
                logger.error(f"Execute error: {e} | SQL: {sql[:100]}")
                return {"success": False, "error": str(e)}

    def executemany(self, sql: str, params_list: list) -> dict:
        """Выполняет множественный запрос."""
        with self.lock:
            try:
                cur = self.conn.executemany(sql, params_list)
                self.conn.commit()
                return {
                    "success": True,
                    "rowcount": cur.rowcount,
                }
            except Exception as e:
                logger.error(f"Executemany error: {e}")
                return {"success": False, "error": str(e)}

    def fetchone(self, sql: str, params: tuple = ()) -> dict:
        """Возвращает одну строку."""
        with self.lock:
            try:
                cur = self.conn.execute(sql, params)
                row = cur.fetchone()
                if row:
                    return {"success": True, "row": dict(row)}
                return {"success": True, "row": None}
            except Exception as e:
                logger.error(f"Fetchone error: {e}")
                return {"success": False, "error": str(e)}

    def fetchall(self, sql: str, params: tuple = ()) -> dict:
        """Возвращает все строки."""
        with self.lock:
            try:
                cur = self.conn.execute(sql, params)
                rows = cur.fetchall()
                return {"success": True, "rows": [dict(r) for r in rows]}
            except Exception as e:
                logger.error(f"Fetchall error: {e}")
                return {"success": False, "error": str(e)}

    def executescript(self, script: str) -> dict:
        """Выполняет скрипт SQL."""
        with self.lock:
            try:
                self.conn.executescript(script)
                self.conn.commit()
                return {"success": True}
            except Exception as e:
                logger.error(f"Executescript error: {e}")
                return {"success": False, "error": str(e)}

    def close(self):
        """Закрывает соединение."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Глобальный экземпляр БД
db = DatabaseConnection(DB_PATH)


# ═══════════════════════════════════════════════════════════════
# HTTP HANDLER
# ═══════════════════════════════════════════════════════════════

class DatabaseAPIHandler(BaseHTTPRequestHandler):
    """HTTP обработчик запросов к БД."""

    def _send_json(self, data: dict, status: int = 200):
        """Отправляет JSON ответ."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _read_body(self) -> dict:
        """Читает JSON тело запроса."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode("utf-8"))

    def do_POST(self):
        """Обрабатывает POST запросы — все операции с БД."""
        try:
            body = self._read_body()
            path = urlparse(self.path).path

            if path == "/execute":
                result = db.execute(body.get("sql", ""), tuple(body.get("params", [])))
                self._send_json(result)

            elif path == "/executemany":
                result = db.executemany(body.get("sql", ""), body.get("params_list", []))
                self._send_json(result)

            elif path == "/fetchone":
                result = db.fetchone(body.get("sql", ""), tuple(body.get("params", [])))
                self._send_json(result)

            elif path == "/fetchall":
                result = db.fetchall(body.get("sql", ""), tuple(body.get("params", [])))
                self._send_json(result)

            elif path == "/executescript":
                result = db.executescript(body.get("script", ""))
                self._send_json(result)

            elif path == "/health":
                self._send_json({"status": "ok", "db": db.db_path})

            elif path == "/stats":
                stats = {
                    "uptime": time.time() - start_time,
                    "db_path": db.db_path,
                }
                self._send_json(stats)

            else:
                self._send_json({"error": f"Unknown path: {path}"}, 404)

        except Exception as e:
            logger.error(f"Request error: {e}")
            self._send_json({"error": str(e)}, 500)

    def do_GET(self):
        """GET — только health check."""
        path = urlparse(self.path).path
        if path == "/health":
            # Проверяем, что БД отвечает
            result = db.fetchone("SELECT 1 as test")
            if result.get("success"):
                self._send_json({"status": "ok", "test": result.get("row", {}).get("test")})
            else:
                self._send_json({"status": "error", "detail": str(result.get("error"))}, 500)
        elif path == "/stats":
            stats = {
                "uptime": time.time() - start_time,
                "db_path": db.db_path,
            }
            self._send_json(stats)
        else:
            self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        """Логируем только важное."""
        logger.debug(f"{self.command} {self.path} — {args[0]} {args[1]}")


# ═══════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ БД ТОЛЬКО ПЕРВЫЙ РАЗ
# ═══════════════════════════════════════════════════════════════

def init_database():
    """Создаёт таблицы если их нет (только при первом запуске)."""
    logger.info("Initializing database schema...")

    # Сначала подключаемся
    db.connect()

    # Создаём таблицы
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_active INTEGER DEFAULT 1,
            notifications_enabled INTEGER DEFAULT 1,
            min_discount_percent INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_title TEXT NOT NULL,
            store TEXT NOT NULL,
            last_known_price REAL,
            last_known_discount INTEGER DEFAULT 0,
            last_known_currency TEXT DEFAULT 'RUB',
            notification_sent INTEGER DEFAULT 0,
            last_check REAL,
            created_at REAL DEFAULT (strftime('%s', 'now')),
            UNIQUE(user_id, game_title, store)
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_title TEXT NOT NULL,
            store TEXT NOT NULL,
            image TEXT DEFAULT '',
            url TEXT DEFAULT '',
            added_at REAL DEFAULT (strftime('%s', 'now')),
            UNIQUE(user_id, game_title, store)
        );

        CREATE TABLE IF NOT EXISTS deals_cache (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            store TEXT NOT NULL,
            price REAL DEFAULT 0,
            original_price REAL DEFAULT 0,
            discount_percent INTEGER DEFAULT 0,
            is_free INTEGER DEFAULT 0,
            url TEXT DEFAULT '',
            image TEXT DEFAULT '',
            currency TEXT DEFAULT 'RUB',
            updated_at REAL DEFAULT (strftime('%s', 'now'))
        );

        CREATE TABLE IF NOT EXISTS notifications_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            game_title TEXT NOT NULL,
            store TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            discount_percent INTEGER DEFAULT 0,
            price REAL,
            sent_at REAL DEFAULT (strftime('%s', 'now'))
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_title TEXT NOT NULL,
            store TEXT NOT NULL,
            price REAL,
            discount_percent INTEGER DEFAULT 0,
            is_free INTEGER DEFAULT 0,
            recorded_at REAL DEFAULT (strftime('%s', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_game ON subscriptions(game_title, store);
        CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
        CREATE INDEX IF NOT EXISTS idx_deals_cache_store ON deals_cache(store);
        CREATE INDEX IF NOT EXISTS idx_deals_cache_title ON deals_cache(title);
        CREATE INDEX IF NOT EXISTS idx_notifications_history_user ON notifications_history(user_id, game_title, store);
        CREATE INDEX IF NOT EXISTS idx_price_history_game ON price_history(game_title, store);

        CREATE TABLE IF NOT EXISTS user_filters (
            user_id INTEGER PRIMARY KEY,
            selected_genres TEXT DEFAULT '',
            min_discount INTEGER DEFAULT 0,
            max_price REAL DEFAULT 0,
            platform TEXT DEFAULT 'all',
            filter_type TEXT DEFAULT 'all',
            sort_type TEXT DEFAULT 'discount',
            rating_filter INTEGER DEFAULT 0,
            language_filter TEXT DEFAULT '',
            multiplayer_filter TEXT DEFAULT '',
            updated_at REAL DEFAULT (strftime('%s', 'now'))
        );

        CREATE TABLE IF NOT EXISTS user_notif_filters (
            user_id INTEGER PRIMARY KEY,
            selected_genres TEXT DEFAULT '',
            min_discount INTEGER DEFAULT 0,
            max_price REAL DEFAULT 0,
            platform TEXT DEFAULT 'all',
            filter_type TEXT DEFAULT 'all',
            rating_filter INTEGER DEFAULT 0,
            updated_at REAL DEFAULT (strftime('%s', 'now'))
        );
    """)

    # Миграции
    migrations = [
        "ALTER TABLE users ADD COLUMN notifications_enabled INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN min_discount_percent INTEGER DEFAULT 0",
        "ALTER TABLE subscriptions ADD COLUMN last_known_currency TEXT DEFAULT 'RUB'",
        "ALTER TABLE subscriptions ADD COLUMN notification_sent INTEGER DEFAULT 0",
        "ALTER TABLE subscriptions ADD COLUMN last_check REAL",
    ]
    for migration in migrations:
        try:
            db.execute(migration)
            logger.info(f"Migration applied: {migration}")
        except Exception:
            pass  # колонка уже существует

    logger.info("✅ Database schema ready")


# ═══════════════════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════════════════

start_time = time.time()


def run_server():
    """Запускает HTTP сервер для БД."""
    init_database()

    server = HTTPServer((HOST, PORT), DatabaseAPIHandler)
    logger.info(f"🗄️  Database server running on http://{HOST}:{PORT}")
    logger.info(f"   Health check: http://{HOST}:{PORT}/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        db.close()
        server.server_close()


if __name__ == "__main__":
    run_server()