from __future__ import annotations

import hashlib
import secrets

from .storage import Store


def _hash_password(password: str) -> str:
    salt = "academic-assistant-2024"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return _hash_password(password) == password_hash


def register(store: Store, username: str, password: str, role: str = "student") -> dict:
    if not username or len(username) < 2:
        raise ValueError("用户名至少需要 2 个字符。")
    if len(password) < 4:
        raise ValueError("密码至少需要 4 个字符。")
    if role not in ("student", "teacher"):
        raise ValueError("角色只能是 student 或 teacher。")
    if store.get_user_by_name(username):
        raise ValueError("用户名已存在。")
    user_id = store.create_user(username, _hash_password(password), role)
    token = _create_session(store, user_id)
    return {"user_id": user_id, "username": username, "role": role, "token": token}


def login(store: Store, username: str, password: str) -> dict:
    user = store.get_user_by_name(username)
    if not user or not verify_password(password, user["password_hash"]):
        raise ValueError("用户名或密码错误。")
    token = _create_session(store, user["id"])
    return {"user_id": user["id"], "username": user["username"], "role": user["role"], "token": token}


def logout(store: Store, token: str) -> None:
    store.delete_session(token)


def get_current_user(store: Store, token: str | None) -> dict | None:
    if not token:
        return None
    return store.get_session(token)


def _create_session(store: Store, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    store.create_session(token, user_id, hours=24)
    return token