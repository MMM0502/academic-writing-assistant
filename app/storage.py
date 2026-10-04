from __future__ import annotations

from datetime import datetime, timezone, timedelta
from contextlib import closing
import json
import sqlite3
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: Path):
        self.path = path
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(self.connect()) as connection:
                with connection:
                    connection.executescript(self._schema())
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"数据库初始化失败：{exc}。请检查数据目录 {self.path.parent} 是否可写，"
                "或通过环境变量 DATA_DIR 指定其他目录。"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"无法创建数据库目录 {self.path.parent}：{exc}。"
                "可通过环境变量 DATA_DIR 指定一个可写目录。"
            ) from exc

    @staticmethod
    def _schema() -> str:
        return """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL,
            user_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            shared_with_id INTEGER,
            permission TEXT NOT NULL DEFAULT 'view',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS journal_styles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            publisher TEXT,
            rules TEXT NOT NULL,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            created_by INTEGER,
            created_at TEXT NOT NULL
        );
        """

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def add(self, kind: str, title: str, payload: dict[str, Any], user_id: int | None = None) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO jobs(kind, title, created_at, payload, user_id) VALUES (?, ?, ?, ?, ?)",
                    (kind, title, created_at, json.dumps(payload, ensure_ascii=False), user_id),
                )
                return int(cursor.lastrowid)

    def list(self, limit: int = 30, user_id: int | None = None) -> list[dict[str, Any]]:
        with closing(self.connect()) as connection:
            if user_id is not None:
                rows = connection.execute(
                    "SELECT id, kind, title, created_at, payload, user_id FROM jobs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, kind, title, created_at, payload, user_id FROM jobs WHERE user_id IS NULL ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def get(self, job_id: int) -> dict[str, Any] | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT id, kind, title, created_at, payload, user_id FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_job(row)

    def delete(self, job_id: int) -> bool:
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                return cursor.rowcount > 0

    def clear(self, user_id: int | None = None) -> int:
        with closing(self.connect()) as connection:
            with connection:
                if user_id is not None:
                    cursor = connection.execute("DELETE FROM jobs WHERE user_id = ?", (user_id,))
                else:
                    cursor = connection.execute("DELETE FROM jobs WHERE user_id IS NULL")
                return int(cursor.rowcount)

    def _row_to_job(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "kind": row["kind"],
            "title": row["title"],
            "created_at": row["created_at"],
            "payload": json.loads(row["payload"]),
            "user_id": row["user_id"] if "user_id" in row.keys() else None,
        }

    def create_user(self, username: str, password_hash: str, role: str = "student") -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO users(username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                    (username, password_hash, role, created_at),
                )
                return int(cursor.lastrowid)

    def get_user_by_name(self, username: str) -> dict | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?", (username,)
            ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "username": row["username"], "password_hash": row["password_hash"], "role": row["role"], "created_at": row["created_at"]}

    def get_user_by_id(self, user_id: int) -> dict | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT id, username, password_hash, role, created_at FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "username": row["username"], "password_hash": row["password_hash"], "role": row["role"], "created_at": row["created_at"]}

    def list_users(self) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT id, username, role, created_at FROM users ORDER BY id"
            ).fetchall()
        return [{"id": r["id"], "username": r["username"], "role": r["role"], "created_at": r["created_at"]} for r in rows]

    def create_session(self, token: str, user_id: int, hours: int = 24) -> None:
        now = datetime.now(timezone.utc)
        with closing(self.connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (token, user_id, now.isoformat(), (now + timedelta(hours=hours)).isoformat()),
                )

    def get_session(self, token: str) -> dict | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT s.token, s.user_id, s.expires_at, u.username, u.role "
                "FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ?",
                (token,)
            ).fetchone()
        if not row:
            return None
        expires = datetime.fromisoformat(row["expires_at"])
        if expires < datetime.now(timezone.utc):
            return None
        return {"token": row["token"], "user_id": row["user_id"], "username": row["username"], "role": row["role"]}

    def delete_session(self, token: str) -> None:
        with closing(self.connect()) as connection:
            with connection:
                connection.execute("DELETE FROM sessions WHERE token = ?", (token,))

    def add_comment(self, job_id: int, user_id: int, content: str) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO comments(job_id, user_id, content, created_at) VALUES (?, ?, ?, ?)",
                    (job_id, user_id, content, created_at),
                )
                return int(cursor.lastrowid)

    def list_comments(self, job_id: int) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT c.id, c.job_id, c.user_id, c.content, c.created_at, u.username "
                "FROM comments c JOIN users u ON c.user_id = u.id WHERE c.job_id = ? ORDER BY c.id",
                (job_id,),
            ).fetchall()
        return [{"id": r["id"], "job_id": r["job_id"], "user_id": r["user_id"], "content": r["content"], "created_at": r["created_at"], "username": r["username"]} for r in rows]

    def delete_comment(self, comment_id: int) -> bool:
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
                return cursor.rowcount > 0

    def create_share(self, job_id: int, owner_id: int, shared_with_id: int | None, permission: str = "view") -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO shares(job_id, owner_id, shared_with_id, permission, created_at) VALUES (?, ?, ?, ?, ?)",
                    (job_id, owner_id, shared_with_id, permission, created_at),
                )
                return int(cursor.lastrowid)

    def list_shares(self, user_id: int) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT s.id, s.job_id, s.owner_id, s.shared_with_id, s.permission, s.created_at, j.title, j.kind "
                "FROM shares s JOIN jobs j ON s.job_id = j.id "
                "WHERE s.shared_with_id = ? OR s.owner_id = ? ORDER BY s.id DESC",
                (user_id, user_id),
            ).fetchall()
        return [{"id": r["id"], "job_id": r["job_id"], "owner_id": r["owner_id"], "shared_with_id": r["shared_with_id"], "permission": r["permission"], "created_at": r["created_at"], "title": r["title"], "kind": r["kind"]} for r in rows]

    def delete_share(self, share_id: int) -> bool:
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute("DELETE FROM shares WHERE id = ?", (share_id,))
                return cursor.rowcount > 0

    def add_journal_style(self, name: str, rules: dict, publisher: str = "", is_builtin: bool = False, created_by: int | None = None) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO journal_styles(name, publisher, rules, is_builtin, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, publisher, json.dumps(rules, ensure_ascii=False), 1 if is_builtin else 0, created_by, created_at),
                )
                return int(cursor.lastrowid)

    def list_journal_styles(self) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT id, name, publisher, rules, is_builtin, created_by, created_at FROM journal_styles ORDER BY is_builtin DESC, id"
            ).fetchall()
        return [{"id": r["id"], "name": r["name"], "publisher": r["publisher"], "rules": json.loads(r["rules"]), "is_builtin": bool(r["is_builtin"]), "created_by": r["created_by"], "created_at": r["created_at"]} for r in rows]

    def get_journal_style(self, style_id: int) -> dict | None:
        with closing(self.connect()) as connection:
            row = connection.execute(
                "SELECT id, name, publisher, rules, is_builtin, created_by, created_at FROM journal_styles WHERE id = ?", (style_id,)
            ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "name": row["name"], "publisher": row["publisher"], "rules": json.loads(row["rules"]), "is_builtin": bool(row["is_builtin"]), "created_by": row["created_by"], "created_at": row["created_at"]}

    def delete_journal_style(self, style_id: int) -> bool:
        with closing(self.connect()) as connection:
            with connection:
                cursor = connection.execute("DELETE FROM journal_styles WHERE id = ? AND is_builtin = 0", (style_id,))
                return cursor.rowcount > 0

    def get_all_jobs(self, limit: int = 1000) -> list[dict]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT id, kind, title, created_at, payload, user_id FROM jobs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_job(row) for row in rows]
