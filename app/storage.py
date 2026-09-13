from __future__ import annotations

from datetime import datetime, timezone
from contextlib import closing
import json
import sqlite3
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        kind TEXT NOT NULL,
                        title TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        payload TEXT NOT NULL
                    )
                    """
                )

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def add(self, kind: str, title: str, payload: dict[str, Any]) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO jobs(kind, title, created_at, payload) VALUES (?, ?, ?, ?)",
                    (kind, title, created_at, json.dumps(payload, ensure_ascii=False)),
                )
                return int(cursor.lastrowid)

    def list(self, limit: int = 30) -> list[dict[str, Any]]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT id, kind, title, created_at, payload FROM jobs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "title": row["title"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]

    def get(self, job_id: int) -> dict[str, Any] | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT id, kind, title, created_at, payload FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "kind": row["kind"],
            "title": row["title"],
            "created_at": row["created_at"],
            "payload": json.loads(row["payload"]),
        }
