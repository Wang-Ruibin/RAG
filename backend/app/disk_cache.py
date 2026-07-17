"""SQLite 持久化磁盘缓存 — 替代 fakeredis 的 Redis 兼容层

提供 Redis 风格的 API（get/setex/scan/type/ttl/lrange/rpush/expire/zincrby/zrevrange/info/ping），
数据存储在 ``backend/data/cache.db``，进程重启后不丢失。
"""

import fnmatch
import os
import sqlite3
import threading
import time
from pathlib import Path

# ── 数据库路径 ──────────────────────────────────────────
_db_dir = Path(__file__).resolve().parent.parent / "data"
_db_dir.mkdir(parents=True, exist_ok=True)
_DB_PATH = str(_db_dir / "cache.db")

# ── 建表 SQL ────────────────────────────────────────────
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cache_entries (
    key TEXT NOT NULL,
    value TEXT,
    key_type TEXT DEFAULT 'string',
    expires_at REAL DEFAULT 0,
    score REAL DEFAULT 0,
    list_index INTEGER DEFAULT 0,
    PRIMARY KEY (key, list_index)
);
CREATE INDEX IF NOT EXISTS idx_expires ON cache_entries(expires_at);
"""


class DiskCache:
    """SQLite 持久化缓存，提供 Redis 兼容 API。"""

    def __init__(self, db_path: str = _DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._start_time = time.time()

        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_CREATE_TABLE_SQL)
        self._conn.commit()
        self._cursor = self._conn.cursor()

    # ── 内部工具 ────────────────────────────────────────

    def _clean_expired(self) -> None:
        """删除所有已过期的条目。"""
        now = time.time()
        self._cursor.execute(
            "DELETE FROM cache_entries WHERE expires_at > 0 AND expires_at <= ?",
            (now,),
        )
        if self._cursor.rowcount > 0:
            self._conn.commit()

    @staticmethod
    def _redis_range(items: list, start: int, end: int) -> list:
        """按 Redis 区间语义（含端）切片。"""
        if end == -1:
            return items[start:]
        return items[start : end + 1]

    def _count_keys(self, pattern: str = "*") -> int:
        """返回匹配 pattern 的有效（未过期）key 数。"""
        self._clean_expired()
        now = time.time()
        rows = self._cursor.execute(
            "SELECT DISTINCT key FROM cache_entries "
            "WHERE (expires_at = 0 OR expires_at > ?)",
            (now,),
        ).fetchall()
        return sum(1 for r in rows if fnmatch.fnmatch(r[0], pattern))

    # ── 公共 API ────────────────────────────────────────

    def get(self, key: str) -> str | None:
        """获取 string 类型的值。"""
        with self._lock:
            self._clean_expired()
            row = self._cursor.execute(
                "SELECT value FROM cache_entries "
                "WHERE key=? AND list_index=0 AND key_type='string' "
                "AND (expires_at = 0 OR expires_at > ?)",
                (key, time.time()),
            ).fetchone()
            return row[0] if row else None

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        """设置 string 类型值（含过期时间）。"""
        expires_at = time.time() + ttl_seconds if ttl_seconds > 0 else 0
        with self._lock:
            self._clean_expired()
            self._cursor.execute(
                "DELETE FROM cache_entries WHERE key = ?", (key,)
            )
            self._cursor.execute(
                "INSERT INTO cache_entries "
                "(key, value, key_type, expires_at, list_index) "
                "VALUES (?, ?, 'string', ?, 0)",
                (key, value, expires_at),
            )
            self._conn.commit()

    def delete(self, *keys: str) -> int:
        """删除一个或多个 key，返回被删除的 key 数量。"""
        deleted = 0
        with self._lock:
            for key in keys:
                self._cursor.execute(
                    "SELECT COUNT(DISTINCT key) FROM cache_entries WHERE key=?",
                    (key,),
                )
                before = self._cursor.fetchone()[0]
                if before > 0:
                    self._cursor.execute(
                        "DELETE FROM cache_entries WHERE key=?", (key,)
                    )
                    deleted += 1
            if deleted > 0:
                self._conn.commit()
        return deleted

    def scan(
        self, cursor: int = 0, match: str = "*", count: int = 100
    ) -> tuple[int, list[str]]:
        """迭代返回匹配的 key 列表。cursor 始终返回 0（全量返回）。"""
        with self._lock:
            self._clean_expired()
            now = time.time()
            rows = self._cursor.execute(
                "SELECT DISTINCT key FROM cache_entries "
                "WHERE (expires_at = 0 OR expires_at > ?)",
                (now,),
            ).fetchall()
            keys = [r[0] for r in rows]
            if match and match != "*":
                keys = [k for k in keys if fnmatch.fnmatch(k, match)]
            return (0, keys)

    def type(self, key: str) -> str:
        """返回 key 的类型：string / list / zset / none。"""
        with self._lock:
            self._clean_expired()
            row = self._cursor.execute(
                "SELECT key_type FROM cache_entries "
                "WHERE key=? AND (expires_at = 0 OR expires_at > ?) LIMIT 1",
                (key, time.time()),
            ).fetchone()
            return row[0] if row else "none"

    def ttl(self, key: str) -> int:
        """返回剩余秒数。－1 无过期，－2 不存在/已过期。"""
        with self._lock:
            self._clean_expired()
            row = self._cursor.execute(
                "SELECT expires_at FROM cache_entries WHERE key=? LIMIT 1",
                (key,),
            ).fetchone()
            if not row:
                return -2
            expires_at = row[0]
            if expires_at == 0:
                return -1
            remaining = int(expires_at - time.time())
            return max(-2, remaining)

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        """返回 list 类型指定范围的值。"""
        with self._lock:
            self._clean_expired()
            rows = self._cursor.execute(
                "SELECT value FROM cache_entries "
                "WHERE key=? AND key_type='list' ORDER BY list_index",
                (key,),
            ).fetchall()
            values = [r[0] for r in rows]
            return self._redis_range(values, start, end)

    def rpush(self, key: str, value: str) -> None:
        """向 list 尾部追加一个值。"""
        with self._lock:
            self._clean_expired()
            row = self._cursor.execute(
                "SELECT COALESCE(MAX(list_index), -1) FROM cache_entries WHERE key=?",
                (key,),
            ).fetchone()
            next_index = (row[0] if row[0] is not None else -1) + 1
            self._cursor.execute(
                "INSERT INTO cache_entries "
                "(key, value, key_type, list_index) "
                "VALUES (?, ?, 'list', ?)",
                (key, value, next_index),
            )
            self._conn.commit()

    def expire(self, key: str, seconds: int) -> None:
        """设置 key 的过期时间（秒）。"""
        expires_at = time.time() + seconds
        with self._lock:
            self._cursor.execute(
                "UPDATE cache_entries SET expires_at=? WHERE key=?",
                (expires_at, key),
            )
            self._conn.commit()

    def zincrby(self, key: str, amount: int, value: str) -> None:
        """为 zset 中 member 的 score 增加 amount。"""
        with self._lock:
            self._clean_expired()
            row = self._cursor.execute(
                "SELECT list_index, score FROM cache_entries "
                "WHERE key=? AND value=? AND key_type='zset' LIMIT 1",
                (key, value),
            ).fetchone()
            if row:
                self._cursor.execute(
                    "UPDATE cache_entries SET score = score + ? "
                    "WHERE key=? AND list_index=?",
                    (amount, key, row[0]),
                )
            else:
                max_row = self._cursor.execute(
                    "SELECT COALESCE(MAX(list_index), -1) FROM cache_entries "
                    "WHERE key=? AND key_type='zset'",
                    (key,),
                ).fetchone()
                next_idx = (max_row[0] if max_row[0] is not None else -1) + 1
                self._cursor.execute(
                    "INSERT INTO cache_entries "
                    "(key, value, key_type, score, list_index) "
                    "VALUES (?, ?, 'zset', ?, ?)",
                    (key, value, amount, next_idx),
                )
            self._conn.commit()

    def zrevrange(
        self, key: str, start: int, end: int, withscores: bool = False
    ) -> list:
        """返回 zset 中按 score 降序排列的指定范围成员。"""
        with self._lock:
            self._clean_expired()
            rows = self._cursor.execute(
                "SELECT value, score FROM cache_entries "
                "WHERE key=? AND key_type='zset' ORDER BY score DESC, value ASC",
                (key,),
            ).fetchall()
            if withscores:
                items = [(r[0], r[1]) for r in rows]
            else:
                items = [r[0] for r in rows]
            return self._redis_range(items, start, end)

    def info(self) -> dict:
        """返回缓存统计信息。"""
        with self._lock:
            self._clean_expired()
            total = self._count_keys("*")
            try:
                size = os.path.getsize(self._db_path)
            except OSError:
                size = 0

            if size < 1024:
                size_human = f"{size} B"
            elif size < 1024 * 1024:
                size_human = f"{size / 1024:.1f} KB"
            else:
                size_human = f"{size / (1024 * 1024):.1f} MB"

            return {
                "redis_version": "disk_cache-1.0",
                "used_memory": size,
                "used_memory_human": size_human,
                "keyspace_hits": 0,
                "keyspace_misses": 0,
                "uptime_in_seconds": int(time.time() - self._start_time),
                "total_keys": total,
                "evicted_keys": 0,
            }

    def ping(self) -> bool:
        """健康检查。"""
        try:
            self._cursor.execute("SELECT 1")
            return True
        except Exception:
            return False
