"""
tests/test_challenge.py

Jalankan dari root proyek dengan virtual environment aktif:
    PYTHONPATH=. pytest -v

Catatan: setiap test menggunakan database SQLite sementara (fixture
`client`) agar tidak mengganggu instance zero_authority.db yang nyata.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.database import get_db
from init_db import SCHEMA_PATH


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Arahkan DB_PATH ke file sementara agar test terisolasi.
    test_db = tmp_path / "test_zero_authority.db"
    monkeypatch.setattr("app.database.DB_PATH", test_db)

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        import sqlite3

        conn = sqlite3.connect(test_db)
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        conn.close()

    with app.test_client() as test_client:
        yield test_client


def test_login_success(client):
    response = client.post(
        "/", data={"username": "kallen", "password": "imeleven"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_login_failure(client):
    response = client.post(
        "/", data={"username": "kallen", "password": "wrong-password"}
    )
    assert response.status_code == 200
    assert "Username atau password salah".encode() in response.data


def test_protected_page_redirects_without_session(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/" in response.headers["Location"]


def test_public_archive_accessible_after_login(client):
    client.post("/", data={"username": "kallen", "password": "imeleven"})
    response = client.get("/archive/1")
    assert response.status_code == 200
    assert b"Public Operation Report" in response.data


def test_secret_archive_denied_for_member(client):
    client.post("/", data={"username": "kallen", "password": "imeleven"})
    response = client.get("/archive/2")
    assert response.status_code == 403


def test_secret_archive_allowed_with_forged_zero_role(client):
    """
    Mensimulasikan intended vulnerability: jika sebuah sesi berhasil
    ditandatangani dengan role 'zero' (misalnya karena secret key bocor),
    aplikasi akan mempercayainya tanpa validasi tambahan.
    """
    client.post("/", data={"username": "kallen", "password": "imeleven"})

    with client.session_transaction() as sess:
        sess["role"] = "zero"

    response = client.get("/archive/2")
    assert response.status_code == 200
    assert b"TecFest26{" in response.data


def test_backup_config_file_is_exposed(client):
    """
    Memverifikasi jalur penemuan secret key: file backup konfigurasi
    harus dapat diakses tanpa login, mensimulasikan file yang tidak
    sengaja ter-deploy ke direktori static.
    """
    response = client.get("/static/config.bak")
    assert response.status_code == 200
    assert b"zero-trust-demo-key" in response.data


def test_logout_clears_session(client):
    client.post("/", data={"username": "kallen", "password": "imeleven"})
    client.get("/logout")
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
