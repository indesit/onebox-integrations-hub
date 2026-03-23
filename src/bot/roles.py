"""Role-based access control for the Telegram bot.

Roles (config/roles.yml):
  owner — full access: /cash, /users + all admin commands
  admin — operational: /status, /failed, /customer, /fix_bdate, /digest
  user  — basic access (reserved for future commands)

Phones stored as "+380XXXXXXXXX" (E.164 with +).
user_id → role mapping is cached in memory and persisted to data/bot_users.json.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

import yaml
from src.core.logger import get_logger

logger = get_logger(__name__)

Role = Literal["owner", "admin", "user"]

ROLES_CONFIG = Path("/app/config/roles.yml")
USERS_FILE = Path("/app/data/bot_users.json")

# Commands allowed per role (cumulative: owner includes admin includes user)
ROLE_COMMANDS: dict[Role, set[str]] = {
    "user":  {"/start", "/help", "/customer"},
    "admin": {"/start", "/help", "/customer", "/status", "/failed", "/fix_bdate", "/digest"},
    "owner": {"/start", "/help", "/customer", "/status", "/failed", "/fix_bdate", "/digest",
               "/cash", "/users", "/sales", "/backfill_status"},
}


def _load_phone_map() -> dict[str, Role]:
    """Load phone → role mapping from roles.yml. Called on every auth check so
    file edits take effect without restart."""
    if not ROLES_CONFIG.exists():
        logger.warning("roles_config_missing", path=str(ROLES_CONFIG))
        return {}
    try:
        with open(ROLES_CONFIG) as f:
            data = yaml.safe_load(f) or {}
        mapping: dict[str, Role] = {}
        for role in ("owner", "admin", "user"):
            for phone in (data.get(role) or []):
                normalized = _normalize_phone(str(phone))
                if normalized:
                    mapping[normalized] = role  # type: ignore[assignment]
        return mapping
    except Exception as exc:
        logger.error("roles_load_error", error=str(exc))
        return {}


def _normalize_phone(phone: str) -> str | None:
    """Normalize to +380XXXXXXXXX format."""
    import re
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if len(digits) == 12 and digits.startswith("380"):
        return f"+{digits}"
    if len(digits) == 10 and digits.startswith("0"):
        return f"+38{digits}"
    if len(digits) == 11 and digits.startswith("80"):
        return f"+3{digits}"
    if len(digits) == 9:
        return f"+380{digits}"
    return f"+{digits}"


# ── Persistent user store ──────────────────────────────────────────────────

def _load_users() -> dict[int, Role]:
    try:
        if USERS_FILE.exists():
            raw = json.loads(USERS_FILE.read_text())
            return {int(k): v for k, v in raw.items()}
    except Exception as exc:
        logger.error("bot_users_load_error", error=str(exc))
    return {}


def _save_users(users: dict[int, Role]) -> None:
    try:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text(json.dumps({str(k): v for k, v in users.items()}, indent=2))
    except Exception as exc:
        logger.error("bot_users_save_error", error=str(exc))


# In-memory cache: user_id → role
_users: dict[int, Role] = _load_users()


def authorize(user_id: int, phone: str) -> Role | None:
    """Try to authorize a user by phone. Returns granted role or None."""
    phone_map = _load_phone_map()
    normalized = _normalize_phone(phone)
    if not normalized:
        return None
    role = phone_map.get(normalized)
    if role:
        _users[user_id] = role
        _save_users(_users)
        logger.info("bot_user_authorized", user_id=user_id, phone=normalized, role=role)
    return role


def get_role(user_id: int) -> Role | None:
    return _users.get(user_id)


def can(user_id: int, command: str) -> bool:
    """Return True if user has permission to run the command."""
    role = get_role(user_id)
    if role is None:
        return False
    return command in ROLE_COMMANDS.get(role, set())


def list_users() -> list[dict]:
    """Return list of authorized users with roles (for /users command)."""
    return [{"user_id": uid, "role": role} for uid, role in _users.items()]


def remove_user(user_id: int) -> bool:
    if user_id in _users:
        del _users[user_id]
        _save_users(_users)
        return True
    return False
