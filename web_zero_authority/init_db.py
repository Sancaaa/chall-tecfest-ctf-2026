"""
init_db.py

Membuat / reset database SQLite (zero_authority.db) dari schema.sql.
Jalankan sekali sebelum menjalankan aplikasi, atau setiap kali ingin
mereset instance ke kondisi bersih (misalnya sebelum kompetisi dimulai).

Penggunaan:
    python init_db.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
DB_PATH = BASE_DIR / "zero_authority.db"


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    connection = sqlite3.connect(DB_PATH)
    try:
        connection.executescript(schema_sql)
        connection.commit()
        print(f"Database berhasil dibuat / direset di: {DB_PATH}")
    finally:
        connection.close()


if __name__ == "__main__":
    init_db()
