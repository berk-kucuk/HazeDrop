from __future__ import annotations

import os
import sqlite3
import time

_DB_PATH = os.path.expanduser("~/.local/share/hazedrop/history.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        INTEGER NOT NULL,
            direction TEXT NOT NULL,
            filename  TEXT NOT NULL,
            size      INTEGER NOT NULL,
            onion     TEXT NOT NULL,
            status    TEXT NOT NULL,
            delete_at INTEGER
        )
        """
    )
    conn.commit()
    return conn


def _purge_expired(conn: sqlite3.Connection) -> None:
    now = int(time.time())
    conn.execute("DELETE FROM history WHERE delete_at IS NOT NULL AND delete_at < ?", (now,))
    conn.commit()


def add_entry(
    direction: str,
    filename: str,
    size: int,
    onion: str,
    status: str,
    ttl_days: int = 7,
) -> None:
    try:
        conn = _get_conn()
        ts = int(time.time())
        onion_short = onion[:20] + "…" if len(onion) > 20 else onion
        delete_at = ts + ttl_days * 86400 if ttl_days > 0 else None
        conn.execute(
            "INSERT INTO history (ts, direction, filename, size, onion, status, delete_at) VALUES (?,?,?,?,?,?,?)",
            (ts, direction, filename, size, onion_short, status, delete_at),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_entries(limit: int = 100) -> list[dict]:
    try:
        conn = _get_conn()
        _purge_expired(conn)
        rows = conn.execute(
            "SELECT id, ts, direction, filename, size, onion, status, delete_at "
            "FROM history ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "ts": r[1],
                "direction": r[2],
                "filename": r[3],
                "size": r[4],
                "onion": r[5],
                "status": r[6],
                "delete_at": r[7],
            }
            for r in rows
        ]
    except Exception:
        return []


def clear_history() -> None:
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM history")
        conn.commit()
        conn.close()
    except Exception:
        pass
