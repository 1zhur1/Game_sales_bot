"""
═══════════════════════════════════════════════════════════════
🌐 Database Client — HTTP клиент для Database Server

Бот использует этот клиент вместо прямого sqlite3.connect().
Клиент сам определяет, доступен ли сервер БД, и если нет —
использует прямой доступ к SQLite.
═══════════════════════════════════════════════════════════════
"""

import os
import json
import sqlite3
import time
import logging
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("db_client")


# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")
DB_SERVER_URL = "http://127.0.0.1:5001"
USE_SERVER = True  # попробовать использовать сервер, при ошибке — fallback на прямой SQLite
SERVER_TIMEOUT = 3  # таймаут на подключение к серверу (сек)


# ═══════════════════════════════════════════════════════════════
# HTTP КЛИЕНТ
# ═══════════════════════════════════════════════════════════════

class DatabaseClient:
    """
    Клиент для работы с БД.
    Сначала пробует подключиться к серверу БД (HTTP).
    Если сервер недоступен — работает напрямую с SQLite.
    """

    def __init__(self):
        self._server_available = False
        self._fallback_active = False
        self._http = HTTPClient(DB_SERVER_URL, SERVER_TIMEOUT)
        self._local_conn: Optional[sqlite3.Connection] = None

    def check_server(self) -> bool:
        """Проверяет, доступен ли сервер БД."""
        try:
            resp = self._http.get("/health")
            if resp and resp.get("status") == "ok":
                self._server_available = True
                self._fallback_active = False
                return True
        except Exception:
            pass
        self._server_available = False
        return False

    def _ensure_local(self):
        """Открывает локальное соединение если нужно."""
        if self._local_conn is None:
            self._local_conn = sqlite3.connect(DB_PATH)
            self._local_conn.execute("PRAGMA journal_mode=WAL")
            self._local_conn.execute("PRAGMA synchronous=NORMAL")
            self._local_conn.execute("PRAGMA busy_timeout=5000")
            self._local_conn.row_factory = sqlite3.Row
            logger.warning("Using direct SQLite (no server)")

    def execute(self, sql: str, params: tuple = ()) -> dict:
        """Выполняет SQL запрос (INSERT/UPDATE/DELETE)."""
        # Пробуем через сервер
        if self._server_available:
            try:
                return self._http.post("/execute", {
                    "sql": sql,
                    "params": list(params)
                })
            except Exception:
                self.check_server()  # перепроверяем сервер

        # Fallback на прямой SQLite
        self._ensure_local()
        try:
            cur = self._local_conn.execute(sql, params)
            self._local_conn.commit()
            return {
                "success": True,
                "rowcount": cur.rowcount,
                "lastrowid": cur.lastrowid,
            }
        except Exception as e:
            logger.error(f"Execute error: {e}")
            return {"success": False, "error": str(e)}

    def executemany(self, sql: str, params_list: list) -> dict:
        if self._server_available:
            try:
                return self._http.post("/executemany", {
                    "sql": sql,
                    "params_list": params_list
                })
            except Exception:
                self.check_server()

        self._ensure_local()
        try:
            cur = self._local_conn.executemany(sql, params_list)
            self._local_conn.commit()
            return {"success": True, "rowcount": cur.rowcount}
        except Exception as e:
            logger.error(f"Executemany error: {e}")
            return {"success": False, "error": str(e)}

    def fetchone(self, sql: str, params: tuple = ()) -> dict:
        if self._server_available:
            try:
                return self._http.post("/fetchone", {
                    "sql": sql,
                    "params": list(params)
                })
            except Exception:
                self.check_server()

        self._ensure_local()
        try:
            cur = self._local_conn.execute(sql, params)
            row = cur.fetchone()
            if row:
                return {"success": True, "row": dict(row)}
            return {"success": True, "row": None}
        except Exception as e:
            logger.error(f"Fetchone error: {e}")
            return {"success": False, "error": str(e)}

    def fetchall(self, sql: str, params: tuple = ()) -> dict:
        if self._server_available:
            try:
                return self._http.post("/fetchall", {
                    "sql": sql,
                    "params": list(params)
                })
            except Exception:
                self.check_server()

        self._ensure_local()
        try:
            cur = self._local_conn.execute(sql, params)
            rows = cur.fetchall()
            return {"success": True, "rows": [dict(r) for r in rows]}
        except Exception as e:
            logger.error(f"Fetchall error: {e}")
            return {"success": False, "error": str(e)}

    def executescript(self, script: str) -> dict:
        if self._server_available:
            try:
                return self._http.post("/executescript", {"script": script})
            except Exception:
                self.check_server()

        self._ensure_local()
        try:
            self._local_conn.executescript(script)
            self._local_conn.commit()
            return {"success": True}
        except Exception as e:
            logger.error(f"Executescript error: {e}")
            return {"success": False, "error": str(e)}

    def close(self):
        """Закрывает локальное соединение если было открыто."""
        if self._local_conn:
            try:
                self._local_conn.close()
            except Exception:
                pass
            self._local_conn = None


class HTTPClient:
    """Простой HTTP клиент без зависимостей."""

    def __init__(self, base_url: str, timeout: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def post(self, path: str, data: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        body = json.dumps(data or {}).encode("utf-8")
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = Request(url, method="GET")
        with urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


# Глобальный экземпляр клиента
_client = DatabaseClient()


def get_client() -> DatabaseClient:
    """Возвращает глобальный экземпляр клиента БД."""
    return _client


def init_client():
    """Инициализирует клиент и проверяет сервер."""
    available = _client.check_server()
    if available:
        logger.info("✅ Database server available at", DB_SERVER_URL)
    return available