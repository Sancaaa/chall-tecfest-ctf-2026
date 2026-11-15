"""
database.py

Helper koneksi SQLite untuk aplikasi. Setiap request mendapat satu
koneksi yang disimpan di objek `g` milik Flask, lalu ditutup otomatis
saat request selesai (lihat close_db yang didaftarkan di app/__init__.py).
"""

import sqlite3
from pathlib import Path

from flask import g

DB_PATH = Path(__file__).resolve().parent.parent / "zero_authority.db"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()
