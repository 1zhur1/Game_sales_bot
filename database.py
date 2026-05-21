import sqlite3
import asyncio
import os
import time
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


def log(message):
    print(f"DB: {message}", flush=True)


# ─── Инициализация ──────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
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

        CREATE INDEX IF NOT EXISTS idx_price_history_game ON price_history(game_title, store);
    """)

    # ─── Миграции для существующей БД ─────────────
    # Добавляем колонки, которых может не быть в старой схеме
    migrations = [
        "ALTER TABLE users ADD COLUMN notifications_enabled INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN min_discount_percent INTEGER DEFAULT 0",
        "ALTER TABLE subscriptions ADD COLUMN last_known_currency TEXT DEFAULT 'RUB'",
        "ALTER TABLE subscriptions ADD COLUMN notification_sent INTEGER DEFAULT 0",
        "ALTER TABLE subscriptions ADD COLUMN last_check REAL",
    ]
    for migration in migrations:
        try:
            conn.execute(migration)
            log(f"Migration applied: {migration}")
        except sqlite3.OperationalError:
            pass  # Колонка уже существует

    conn.commit()
    conn.close()
    log("Database initialized with all tables")


# ─── Базовые асинхронные операции ───────────────

async def get_conn() -> sqlite3.Connection:
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


async def executemany(sql: str, params_list: list) -> None:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.executemany(sql, params_list)
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


# ─── Пользователи ───────────────────────────────

async def add_user(user_id: int) -> bool:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = cur.fetchone()
            if exists:
                conn.execute("UPDATE users SET is_active = 1 WHERE user_id = ?", (user_id,))
                conn.commit()
                return False
            else:
                conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
                conn.commit()
                return True
        finally:
            conn.close()
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def get_all_active_users() -> list[int]:
    rows = await fetchall("SELECT user_id FROM users WHERE is_active = 1")
    return [row[0] for row in rows]


async def get_users_with_notifications() -> list[int]:
    rows = await fetchall(
        "SELECT user_id FROM users WHERE is_active = 1 AND notifications_enabled = 1"
    )
    return [row[0] for row in rows]


async def deactivate_user(user_id: int) -> None:
    await execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))


async def get_user_settings(user_id: int) -> Optional[dict]:
    row = await fetchone(
        "SELECT notifications_enabled, min_discount_percent FROM users WHERE user_id = ?",
        (user_id,)
    )
    if row:
        return {"notifications_enabled": bool(row[0]), "min_discount_percent": row[1]}
    return None


async def update_user_settings(user_id: int, notifications_enabled: Optional[bool] = None,
                                min_discount_percent: Optional[int] = None) -> None:
    sets = []
    params = []
    if notifications_enabled is not None:
        sets.append("notifications_enabled = ?")
        params.append(1 if notifications_enabled else 0)
    if min_discount_percent is not None:
        sets.append("min_discount_percent = ?")
        params.append(min_discount_percent)
    if not sets:
        return
    params.append(user_id)
    await execute(
        f"UPDATE users SET {', '.join(sets)} WHERE user_id = ?",
        tuple(params)
    )


# ─── Подписки ───────────────────────────────────

async def add_subscription(user_id: int, game_title: str, store: str,
                           price: Optional[float] = None,
                           discount: int = 0,
                           currency: str = 'RUB') -> bool:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(
                "SELECT id FROM subscriptions WHERE user_id = ? AND game_title = ? AND store = ?",
                (user_id, game_title, store)
            )
            exists = cur.fetchone()
            if exists:
                return False
            conn.execute(
                """INSERT INTO subscriptions
                   (user_id, game_title, store, last_known_price, last_known_discount,
                    last_known_currency, notification_sent, last_check)
                   VALUES (?, ?, ?, ?, ?, ?, 0, strftime('%s', 'now'))""",
                (user_id, game_title, store, price, discount, currency)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def remove_subscription(user_id: int, game_title: str, store: str) -> bool:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(
                "DELETE FROM subscriptions WHERE user_id = ? AND game_title = ? AND store = ?",
                (user_id, game_title, store)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def get_user_subscriptions(user_id: int) -> list[dict]:
    rows = await fetchall(
        """SELECT game_title, store, last_known_price, last_known_discount,
                  last_known_currency, notification_sent, last_check, created_at
           FROM subscriptions
           WHERE user_id = ?
           ORDER BY created_at DESC""",
        (user_id,)
    )
    result = []
    for row in rows:
        result.append({
            "game_title": row[0],
            "store": row[1],
            "last_known_price": row[2],
            "last_known_discount": row[3],
            "last_known_currency": row[4],
            "notification_sent": bool(row[5]),
            "last_check": row[6],
            "created_at": row[7],
        })
    return result


async def get_all_subscriptions() -> list[dict]:
    rows = await fetchall(
        """SELECT s.id, s.user_id, s.game_title, s.store, s.last_known_price,
                  s.last_known_discount, s.last_known_currency, s.notification_sent
           FROM subscriptions s
           JOIN users u ON s.user_id = u.user_id
           WHERE u.is_active = 1"""
    )
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "user_id": row[1],
            "game_title": row[2],
            "store": row[3],
            "last_known_price": row[4],
            "last_known_discount": row[5],
            "last_known_currency": row[6],
            "notification_sent": bool(row[7]),
        })
    return result


async def update_subscription_price(sub_id: int, price: Optional[float],
                                     discount: int, currency: str = 'RUB') -> None:
    await execute(
        """UPDATE subscriptions
           SET last_known_price = ?, last_known_discount = ?,
               last_known_currency = ?, last_check = strftime('%s', 'now'),
               notification_sent = 0
           WHERE id = ?""",
        (price, discount, currency, sub_id)
    )


async def mark_subscription_notified(sub_id: int) -> None:
    await execute(
        "UPDATE subscriptions SET notification_sent = 1 WHERE id = ?",
        (sub_id,)
    )


async def reset_notification_flag(sub_id: int) -> None:
    await execute(
        "UPDATE subscriptions SET notification_sent = 0 WHERE id = ?",
        (sub_id,)
    )


# ─── Избранное ──────────────────────────────────

async def add_favorite(user_id: int, game_title: str, store: str,
                       image: str = '', url: str = '') -> bool:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(
                "SELECT id FROM favorites WHERE user_id = ? AND game_title = ? AND store = ?",
                (user_id, game_title, store)
            )
            if cur.fetchone():
                return False
            conn.execute(
                "INSERT INTO favorites (user_id, game_title, store, image, url) VALUES (?, ?, ?, ?, ?)",
                (user_id, game_title, store, image, url)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def remove_favorite(user_id: int, game_title: str, store: str) -> bool:
    def _run():
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND game_title = ? AND store = ?",
                (user_id, game_title, store)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    return await asyncio.get_event_loop().run_in_executor(None, _run)


async def get_user_favorites(user_id: int) -> list[dict]:
    rows = await fetchall(
        """SELECT game_title, store, image, url, added_at
           FROM favorites WHERE user_id = ?
           ORDER BY added_at DESC""",
        (user_id,)
    )
    result = []
    for row in rows:
        result.append({
            "game_title": row[0],
            "store": row[1],
            "image": row[2],
            "url": row[3],
            "added_at": row[4],
        })
    return result


async def is_favorite(user_id: int, game_title: str, store: str) -> bool:
    row = await fetchone(
        "SELECT id FROM favorites WHERE user_id = ? AND game_title = ? AND store = ?",
        (user_id, game_title, store)
    )
    return row is not None


# ─── Кэш скидок ─────────────────────────────────

async def clear_deals_cache() -> None:
    await execute("DELETE FROM deals_cache")


async def add_deal_to_cache(deal_id: str, title: str, store: str,
                            price: float, original_price: float,
                            discount_percent: int, is_free: bool,
                            url: str, image: str, currency: str = 'RUB') -> None:
    await execute(
        """INSERT OR REPLACE INTO deals_cache
           (id, title, store, price, original_price, discount_percent,
            is_free, url, image, currency, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))""",
        (deal_id, title, store, price, original_price,
         discount_percent, 1 if is_free else 0, url, image or '', currency)
    )


async def get_deals_from_cache(store: Optional[str] = None,
                                min_discount: int = 0,
                                limit: int = 100,
                                offset: int = 0) -> list[dict]:
    sql = """SELECT id, title, store, price, original_price, discount_percent,
                    is_free, url, image, currency, updated_at
             FROM deals_cache
             WHERE is_free = 0"""
    params = []
    if store:
        sql += " AND store = ?"
        params.append(store)
    if min_discount > 0:
        sql += " AND discount_percent >= ?"
        params.append(min_discount)
    sql += " ORDER BY discount_percent DESC, updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = await fetchall(sql, tuple(params))
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "title": row[1],
            "store": row[2],
            "price": row[3],
            "original_price": row[4],
            "discount_percent": row[5],
            "is_free": bool(row[6]),
            "url": row[7],
            "image": row[8],
            "currency": row[9],
            "updated_at": row[10],
        })
    return result


async def get_free_from_cache(store: Optional[str] = None,
                               limit: int = 100,
                               offset: int = 0) -> list[dict]:
    sql = """SELECT id, title, store, price, original_price, discount_percent,
                    is_free, url, image, currency, updated_at
             FROM deals_cache
             WHERE is_free = 1"""
    params = []
    if store:
        sql += " AND store = ?"
        params.append(store)
    sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = await fetchall(sql, tuple(params))
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "title": row[1],
            "store": row[2],
            "price": row[3],
            "original_price": row[4],
            "discount_percent": row[5],
            "is_free": bool(row[6]),
            "url": row[7],
            "image": row[8],
            "currency": row[9],
            "updated_at": row[10],
        })
    return result


async def get_deal_count(store: Optional[str] = None, is_free: bool = False,
                          min_discount: int = 0) -> int:
    sql = "SELECT COUNT(*) FROM deals_cache WHERE is_free = ?"
    params = [1 if is_free else 0]
    if store:
        sql += " AND store = ?"
        params.append(store)
    if not is_free and min_discount > 0:
        sql += " AND discount_percent >= ?"
        params.append(min_discount)
    row = await fetchone(sql, tuple(params))
    return row[0] if row else 0


async def search_deals_cache(query: str, limit: int = 20) -> list[dict]:
    """Поиск по названию в кэше (LIKE)."""
    pattern = f"%{query}%"
    rows = await fetchall(
        """SELECT id, title, store, price, original_price, discount_percent,
                  is_free, url, image, currency, updated_at
           FROM deals_cache
           WHERE title LIKE ?
           ORDER BY discount_percent DESC
           LIMIT ?""",
        (pattern, limit)
    )
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "title": row[1],
            "store": row[2],
            "price": row[3],
            "original_price": row[4],
            "discount_percent": row[5],
            "is_free": bool(row[6]),
            "url": row[7],
            "image": row[8],
            "currency": row[9],
            "updated_at": row[10],
        })
    return result


async def get_deal_by_title(title: str, store: str) -> Optional[dict]:
    row = await fetchone(
        """SELECT id, title, store, price, original_price, discount_percent,
                  is_free, url, image, currency, updated_at
           FROM deals_cache
           WHERE title = ? AND store = ?""",
        (title, store)
    )
    if row:
        return {
            "id": row[0],
            "title": row[1],
            "store": row[2],
            "price": row[3],
            "original_price": row[4],
            "discount_percent": row[5],
            "is_free": bool(row[6]),
            "url": row[7],
            "image": row[8],
            "currency": row[9],
            "updated_at": row[10],
        }
    return None


async def get_all_deals_for_search() -> list[dict]:
    rows = await fetchall(
        "SELECT title, store, price, original_price, discount_percent, is_free, url, image FROM deals_cache"
    )
    result = []
    for row in rows:
        result.append({
            "title": row[0],
            "store": row[1],
            "price": row[2],
            "original_price": row[3],
            "discount_percent": row[4],
            "is_free": bool(row[5]),
            "url": row[6],
            "image": row[7],
        })
    return result


# ─── История уведомлений ───────────────────────

async def add_notification_history(user_id: int, game_title: str, store: str,
                                   notification_type: str,
                                   discount_percent: int = 0,
                                   price: Optional[float] = None) -> None:
    await execute(
        """INSERT INTO notifications_history
           (user_id, game_title, store, notification_type, discount_percent, price)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, game_title, store, notification_type, discount_percent, price)
    )


async def has_recent_notification(user_id: int, game_title: str, store: str,
                                   notification_type: str, hours: int = 24) -> bool:
    """Проверяет, было ли отправлено такое уведомление за последние N часов."""
    cutoff = time.time() - (hours * 3600)
    row = await fetchone(
        """SELECT id FROM notifications_history
           WHERE user_id = ? AND game_title = ? AND store = ? AND notification_type = ?
           AND sent_at > ?""",
        (user_id, game_title, store, notification_type, cutoff)
    )
    return row is not None


# ─── История цен ────────────────────────────────

async def add_price_history(game_title: str, store: str, price: Optional[float],
                            discount_percent: int, is_free: bool) -> None:
    await execute(
        """INSERT INTO price_history (game_title, store, price, discount_percent, is_free)
           VALUES (?, ?, ?, ?, ?)""",
        (game_title, store, price, discount_percent, 1 if is_free else 0)
    )


async def get_price_history(game_title: str, store: str, limit: int = 30) -> list[dict]:
    rows = await fetchall(
        """SELECT price, discount_percent, is_free, recorded_at
           FROM price_history
           WHERE game_title = ? AND store = ?
           ORDER BY recorded_at DESC
           LIMIT ?""",
        (game_title, store, limit)
    )
    result = []
    for row in rows:
        result.append({
            "price": row[0],
            "discount_percent": row[1],
            "is_free": bool(row[2]),
            "recorded_at": row[3],
        })
    return result


async def get_min_price(game_title: str, store: str) -> Optional[float]:
    row = await fetchone(
        """SELECT MIN(price) FROM price_history
           WHERE game_title = ? AND store = ? AND is_free = 0""",
        (game_title, store)
    )
    return row[0] if row and row[0] else None


# ─── Совместимость со старым кодом ──────────────

def make_deal_id(store: str, title: str) -> str:
    return f"{store.lower()}:{title.strip().lower()}"


async def deal_exists(deal_id: str) -> bool:
    row = await fetchone(
        "SELECT id FROM deals_cache WHERE id = ?",
        (deal_id,)
    )
    return row is not None


async def add_known_deal(deal_id: str, title: str, store: str,
                         discount_percent: int, is_free: bool,
                         url: str, image: str) -> None:
    await add_deal_to_cache(
        deal_id=deal_id,
        title=title,
        store=store,
        price=0,
        original_price=0,
        discount_percent=discount_percent,
        is_free=is_free,
        url=url,
        image=image,
    )


async def get_user_filters(user_id: int) -> dict:
    """Получить фильтры пользователя. Если нет — создаёт со значениями по умолчанию."""
    row = await fetchone(
        """SELECT selected_genres, min_discount, max_price, platform,
                  filter_type, sort_type, rating_filter, language_filter, multiplayer_filter
           FROM user_filters WHERE user_id = ?""",
        (user_id,)
    )
    if row:
        return {
            "selected_genres": row[0].split(",") if row[0] else [],
            "min_discount": row[1],
            "max_price": row[2],
            "platform": row[3],
            "filter_type": row[4],
            "sort_type": row[5],
            "rating_filter": row[6],
            "language_filter": row[7],
            "multiplayer_filter": row[8],
        }
    # Создаём фильтры по умолчанию
    await execute(
        """INSERT OR IGNORE INTO user_filters (user_id) VALUES (?)""",
        (user_id,)
    )
    return {
        "selected_genres": [],
        "min_discount": 0,
        "max_price": 0,
        "platform": "all",
        "filter_type": "all",
        "sort_type": "discount",
        "rating_filter": 0,
        "language_filter": "",
        "multiplayer_filter": "",
    }


async def update_user_filter(user_id: int, field: str, value) -> None:
    """Обновить одно поле фильтра."""
    allowed_fields = {
        "selected_genres", "min_discount", "max_price", "platform",
        "filter_type", "sort_type", "rating_filter", "language_filter", "multiplayer_filter"
    }
    if field not in allowed_fields:
        return
    # Убедимся, что запись существует
    await execute(
        """INSERT OR IGNORE INTO user_filters (user_id) VALUES (?)""",
        (user_id,)
    )
    if field == "selected_genres" and isinstance(value, list):
        value = ",".join(value)
    await execute(
        f"UPDATE user_filters SET {field} = ?, updated_at = strftime('%s', 'now') WHERE user_id = ?",
        (value, user_id)
    )


async def reset_user_filters(user_id: int) -> None:
    """Сбросить все фильтры пользователя."""
    await execute(
        """INSERT OR REPLACE INTO user_filters
           (user_id, selected_genres, min_discount, max_price, platform,
            filter_type, sort_type, rating_filter, language_filter, multiplayer_filter, updated_at)
           VALUES (?, '', 0, 0, 'all', 'all', 'discount', 0, '', '', strftime('%s', 'now'))""",
        (user_id,)
    )


async def get_latest_new_deals(limit: int = 10) -> list[dict]:
    return await get_deals_from_cache(limit=limit, offset=0)
