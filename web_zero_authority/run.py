"""
run.py

Entry point aplikasi. Untuk pengembangan lokal:
    python run.py

Untuk Gunicorn:
    gunicorn --workers 2 --bind 127.0.0.1:8000 run:app
"""

from pathlib import Path

from app import create_app
from app.database import DB_PATH
from init_db import init_db

app = create_app()

if __name__ == "__main__":
    # Jika database belum ada, buat otomatis saat dev server dijalankan.
    if not Path(DB_PATH).exists():
        init_db()
    app.run(debug=True)
