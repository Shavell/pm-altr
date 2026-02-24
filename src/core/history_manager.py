"""SQLite-backed request/response history manager."""
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


DB_DIR = Path.home() / ".pm-altr"
DB_PATH = DB_DIR / "history.db"


@dataclass
class HistoryEntry:
    id: Optional[int] = None
    timestamp: str = ""
    method: str = "GET"
    url: str = ""
    request_headers: str = "{}"
    request_params: str = "{}"
    request_body: str = ""
    request_body_type: str = "none"
    response_status: int = 0
    response_time_ms: float = 0.0
    response_size_bytes: int = 0
    response_headers: str = "{}"
    response_body: str = ""


class HistoryManager:
    def __init__(self):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                method TEXT,
                url TEXT,
                request_headers TEXT,
                request_params TEXT,
                request_body TEXT,
                request_body_type TEXT,
                response_status INTEGER,
                response_time_ms REAL,
                response_size_bytes INTEGER,
                response_headers TEXT,
                response_body TEXT
            )
        """)
        self._conn.commit()

    def save(self, entry: HistoryEntry) -> int:
        entry.timestamp = datetime.utcnow().isoformat()
        cur = self._conn.execute("""
            INSERT INTO history (
                timestamp, method, url,
                request_headers, request_params, request_body, request_body_type,
                response_status, response_time_ms, response_size_bytes,
                response_headers, response_body
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            entry.timestamp, entry.method, entry.url,
            entry.request_headers, entry.request_params,
            entry.request_body, entry.request_body_type,
            entry.response_status, entry.response_time_ms,
            entry.response_size_bytes, entry.response_headers,
            entry.response_body,
        ))
        self._conn.commit()
        return cur.lastrowid

    def get_all(self, limit: int = 200) -> List[HistoryEntry]:
        rows = self._conn.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [HistoryEntry(**dict(r)) for r in rows]

    def search(self, query: str, limit: int = 200) -> List[HistoryEntry]:
        like = f"%{query}%"
        rows = self._conn.execute(
            "SELECT * FROM history WHERE url LIKE ? OR method LIKE ? ORDER BY id DESC LIMIT ?",
            (like, like, limit),
        ).fetchall()
        return [HistoryEntry(**dict(r)) for r in rows]

    def delete(self, entry_id: int):
        self._conn.execute("DELETE FROM history WHERE id=?", (entry_id,))
        self._conn.commit()

    def clear(self):
        self._conn.execute("DELETE FROM history")
        self._conn.commit()
