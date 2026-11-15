import json
import os
import sqlite3
import tempfile
import threading
import time

DB_PATH = os.environ.get("DB_PATH", os.path.join(tempfile.gettempdir(), "all_in.db"))
_LOCK = threading.Lock()

INITIAL_DEALER_LINE = (
    "Selamat datang di Ruang 777. Aturannya sederhana: sepuluh kemenangan "
    "beruntun tanpa sekali pun kalah atau mundur. Kalau nyalimu cuma "
    "seujung kuku, silakan tinggalkan meja sebelum harga dirimu habis."
)


def default_state() -> dict:
    return {
        "chips": 1000,
        "win_streak": 0,
        "hands_played": 0,
        "poker": None,
        "last_result": None,
        "interrogation_stage": 1,
        "composure": 100,
        "strikes": 0,
        "dealer_mood": "smug",
        "dealer_line": INITIAL_DEALER_LINE,
        "won_by": None,
    }


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            sid TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    return conn


def init_db() -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.commit()
        finally:
            conn.close()


def get_state(sid: str) -> dict:
    with _LOCK:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT state_json FROM sessions WHERE sid = ?", (sid,)
            ).fetchone()
            if row is not None:
                return json.loads(row[0])
            state = default_state()
            conn.execute(
                "INSERT INTO sessions (sid, state_json, updated_at) VALUES (?, ?, ?)",
                (sid, json.dumps(state), time.time()),
            )
            conn.commit()
            return state
        finally:
            conn.close()


def save_state(sid: str, state: dict) -> None:
    with _LOCK:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO sessions (sid, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(sid) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (sid, json.dumps(state), time.time()),
            )
            conn.commit()
        finally:
            conn.close()
