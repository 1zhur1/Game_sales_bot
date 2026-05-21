import sqlite3
import asyncio
import os
import time
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


def log(message):
    print(f"DB: {message}", flush=True)


# ─── Синхронные операции (инициализация) ───────────────────────────

def init_db():
    """Создаёт таблицы, если их нет. Вызывается при старте бота."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_active INTEGER DEFAULT 1,
            created_at REAL DEFAULT (strftime('%s', 'now'))
        );

        CREATE TABLE IF NOT EXISTS known_deals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            store TEXT NOT NULL,
            discount_percent INTEGER DEFAULT 0,
            is_free INTEGER DEFAULT 0,
            url TEXT,
            image TEXT,
            first_seen REAL DEFAULT (strftime('%s', 'now')),
            last_seen REAL DEFAULT (strftime('%s', 'now'))
        );

        CREATE INDEX IF NOT EXISTS idx_known_deals_store ON known_deals(store);
        CREATE INDEX IF NOT EXISTS idx_known_deals_first_seen ON known_deals(first_seen);
    """)

    conn.commit()
    conn.close()
    log("Database initialized")


# ─── Асинхронные операции ────────────────────────────────────────

async def get_conn() -> sqlite3.Connection:
    """Получить синхронное соединение (aiosqlite не обязателен, используем sqlite3 в executor)."""
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: sqlite3.connect(DB_PATH)
    )


async def execute(sql: str, params: tuple = ()) -> None:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()
    await asyncio.get_event_loop().run_in_executor(None, _run)


async def fetchone(sql: str, params: tuple = ()) -> Optional[tuple]:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(sql, params)
            return cur.fetchone()
        finally:
            conn.close()
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def fetchall(sql: str, params: tuple = ()) -> list:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(sql, params)
            return cur.fetchall()
        finally:
            conn.close()
    return await asyncio.get_event_loop().run_in_executor(None, _run)


# ─── Пользователи ─────────────────────────────────────────────────

async def add_user(user_id: int) -> bool:
    """Добавить пользователя в БД. Возвращает True, если добавлен новый."""
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(
                "SELECT user_id FROM users WHERE user_id = ?",
                (user_id,)
            )
            exists = cur.fetchone()
            if exists:
                # Обновляем статус на активный
                conn.execute(
                    "UPDATE users SET is_active = 1 WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
                return False
            else:
                conn.execute(
                    "INSERT INTO users (user_id) VALUES (?)",
                    (user_id,)
                )
                conn.commit()
                return True
        finally:
            conn.close()
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def get_all_active_users() -> list[int]:
    rows = await fetchall(
        "SELECT user_id FROM users WHERE is_active = 1"
    )
    return [row[0] for row in rows]


async def deactivate_user(user_id: int) -> None:
    await execute(
        "UPDATE users SET is_active = 0 WHERE user_id = ?",
        (user_id,)
    )


# ─── Известные сделки ─────────────────────────────────────────────

def make_deal_id(store: str, title: str) -> str:
    return f"{store.lower()}:{title.strip().lower()}"


async def deal_exists(deal_id: str) -> bool:
    row = await fetchone(
        "SELECT id FROM known_deals WHERE id = ?",
        (deal_id,)
    )
    return row is not None


async def add_known_deal(deal_id: str, title: str, store: str,
                         discount_percent: int, is_free: bool,
                         url: str, image: str) -> None:
    await execute(
        """INSERT OR IGNORE INTO known_deals
           (id, title, store, discount_percent, is_free, url, image)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (deal_id, title, store, discount_percent,
         1 if is_free else 0, url, image or "")
    )


async def get_latest_new_deals(limit: int = 10) -> list[dict]:
    rows = await fetchall(
        """SELECT id, title, store, discount_percent, is_free, url, image
           FROM known_deals
           ORDER BY first_seen DESC
           LIMIT ?""",
        (limit,)
    )
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "title": row[1],
            "store": row[2],
            "discount_percent": row[3],
            "is_free": bool(row[4]),
            "url": row[5],
            "image": row[6],
        })
    return result