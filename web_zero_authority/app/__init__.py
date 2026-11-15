"""
app/__init__.py

The Trust Protocol: Zero's Authority
Challenge Web Exploitation — CTF terisolasi.

PERINGATAN:
Aplikasi ini sengaja mengandung kerentanan (secret key lemah +
otorisasi yang hanya mempercayai data sesi). Ini adalah bagian dari
desain challenge dan TIDAK BOLEH dijadikan contoh untuk aplikasi
produksi. Lihat README bagian "Panduan Deployment Aman".
"""

from flask import Flask, abort, redirect, render_template, request, session, url_for

from app.database import close_db, get_db


def create_app() -> Flask:
    app = Flask(__name__)

    # --- Kerentanan yang disengaja (lihat README §7.2) ---
    # Secret key statis & lemah, ditulis langsung di source code.
    # Siapa pun yang mengetahui nilai ini dapat membuat cookie sesi
    # bertanda tangan yang akan diterima aplikasi.
    app.secret_key = "zero-trust-demo-key"

    app.teardown_appcontext(close_db)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    @app.route("/", methods=["GET", "POST"])
    def login():
        # Kalau sudah ada sesi aktif, tidak perlu balik ke form login.
        # Ini murni UX -- tidak memengaruhi jalur exploit, karena
        # pemalsuan cookie session tidak pernah melewati endpoint ini.
        if "username" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")

            db = get_db()
            # Query diparameterisasi -- login sendiri tidak rentan SQLi.
            # Fokus kerentanan challenge ini ada pada kepercayaan
            # terhadap session["role"], bukan pada query database.
            user = db.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, password),
            ).fetchone()

            if user is None:
                return render_template(
                    "login.html", error="Username atau password salah."
                )

            session.clear()
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        return render_template("login.html", error=None)

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    @app.route("/dashboard")
    def dashboard():
        if "username" not in session:
            return redirect(url_for("login"))
        return render_template(
            "dashboard.html", username=session["username"], role=session["role"]
        )

    # ------------------------------------------------------------------
    # Daftar arsip
    # ------------------------------------------------------------------
    @app.route("/archives")
    def archives():
        if "username" not in session:
            return redirect(url_for("login"))

        db = get_db()
        archive_list = db.execute(
            "SELECT id, title, required_role FROM archives ORDER BY id"
        ).fetchall()
        return render_template(
            "archives.html", archives=archive_list, role=session.get("role")
        )

    # ------------------------------------------------------------------
    # Detail arsip
    # ------------------------------------------------------------------
    @app.route("/archive/<int:archive_id>")
    def archive_detail(archive_id):
        if "username" not in session:
            return redirect(url_for("login"))

        db = get_db()
        archive = db.execute(
            "SELECT * FROM archives WHERE id = ?", (archive_id,)
        ).fetchone()

        if archive is None:
            abort(404)

        # --- Kerentanan yang disengaja (lihat README §7.3) ---
        # Pemeriksaan hak akses sepenuhnya mengandalkan session["role"].
        # Tidak ada validasi tambahan bahwa role tersebut diperoleh
        # melalui alur otorisasi yang sah di sisi server.
        if archive["required_role"] != "member":
            if session.get("role") != archive["required_role"]:
                abort(403)

        return render_template("archive.html", archive=archive)

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------
    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    return app
