import sqlite3
import os
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

VALID_MODES = {"translate", "stress", "examples"}
DEFAULT_MODE = "translate"


def _get_db_path() -> Path:
    db_path = os.getenv("DATABASE_PATH", "data/bot.db")
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _init_db() -> None:
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_modes (
                chat_id TEXT PRIMARY KEY,
                mode TEXT NOT NULL DEFAULT 'translate',
                stress_enabled INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migration: add stress_enabled column if it doesn't exist
        cursor.execute("PRAGMA table_info(user_modes)")
        columns = [row[1] for row in cursor.fetchall()]
        if "stress_enabled" not in columns:
            cursor.execute(
                "ALTER TABLE user_modes ADD COLUMN stress_enabled INTEGER NOT NULL DEFAULT 0"
            )
            logger.info("Added stress_enabled column to user_modes")
        conn.commit()
        conn.close()
        logger.debug("Database initialized at %s", db_path)
    except sqlite3.Error as e:
        logger.error("Failed to initialize database: %s", e)


def _validate_mode(mode: str) -> None:
    if mode not in VALID_MODES:
        raise ValueError(
            f"Invalid mode '{mode}'. Must be one of: {', '.join(sorted(VALID_MODES))}"
        )


def _get_connection() -> sqlite3.Connection:
    return sqlite3.connect(str(_get_db_path()), check_same_thread=False)


@lru_cache(maxsize=1024)
def get_user_mode(chat_id: str) -> str:
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT mode FROM user_modes WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        return DEFAULT_MODE
    except sqlite3.Error as e:
        logger.error("Failed to get user mode for %s: %s", chat_id, e)
        return DEFAULT_MODE


def set_user_mode(chat_id: str, mode: str) -> None:
    _validate_mode(mode)
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_modes (chat_id, mode, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (chat_id, mode),
        )
        conn.commit()
        conn.close()
        get_user_mode.cache_clear()
        logger.debug("Set mode '%s' for user %s", mode, chat_id)
    except sqlite3.Error as e:
        logger.error("Failed to set user mode for %s: %s", chat_id, e)


def delete_user_mode(chat_id: str) -> None:
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_modes WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
        get_user_mode.cache_clear()
        logger.debug("Deleted mode for user %s", chat_id)
    except sqlite3.Error as e:
        logger.error("Failed to delete user mode for %s: %s", chat_id, e)


def clear_all_modes() -> None:
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_modes")
        conn.commit()
        conn.close()
        get_user_mode.cache_clear()
        logger.info("Cleared all user modes")
    except sqlite3.Error as e:
        logger.error("Failed to clear all user modes: %s", e)


@lru_cache(maxsize=1024)
def get_stress_enabled(chat_id: str) -> bool:
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT stress_enabled FROM user_modes WHERE chat_id = ?", (chat_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return bool(row[0])
        return False
    except sqlite3.Error as e:
        logger.error("Failed to get stress setting for %s: %s", chat_id, e)
        return False


def toggle_stress(chat_id: str) -> bool:
    try:
        current = get_stress_enabled(chat_id)
        new_value = not current
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_modes SET stress_enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?",
            (int(new_value), chat_id),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT OR REPLACE INTO user_modes (chat_id, mode, stress_enabled, updated_at) VALUES (?, 'translate', ?, CURRENT_TIMESTAMP)",
                (chat_id, int(new_value)),
            )
        conn.commit()
        conn.close()
        get_stress_enabled.cache_clear()
        logger.debug("Toggled stress to %s for user %s", new_value, chat_id)
        return new_value
    except sqlite3.Error as e:
        logger.error("Failed to toggle stress for %s: %s", chat_id, e)
        return False


_init_db()
