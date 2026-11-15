from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    abort,
    make_response
)

import sqlite3
import os

from functools import wraps


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "scarameow-ctf-secret-key-2026"
)

DATABASE = "/app/data/app.db"


# ============================================================
# DATABASE
# ============================================================

def get_db():
    os.makedirs("/app/data", exist_ok=True)

    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row

    return db


def init_db():
    db = get_db()

    # --------------------------------------------------------
    # CREATE TABLES
    # --------------------------------------------------------

    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT
    );

    CREATE TABLE IF NOT EXISTS api_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        scope TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL,
        assigned_to INTEGER
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT,
        content TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS system_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL
    );
    """)

    # --------------------------------------------------------
    # SYSTEM NOTES
    # --------------------------------------------------------

    system_notes = [
        (
            "Server Maintenance",
            "Monitoring workstation menggunakan Ubuntu XFCE melalui XRDP."
        ),
        (
            "Internal Workstation",
            "RDP internal: sadmin / S3rv3r_N0t3s_2026!"
        ),
        (
            "Security Reminder",
            "Credential workstation internal jangan dibagikan ke user biasa."
        )
    ]

    for note in system_notes:
        exists = db.execute(
            """
            SELECT id
            FROM system_notes
            WHERE title = ? AND content = ?
            """,
            (note[0], note[1])
        ).fetchone()

        if not exists:
            db.execute(
                """
                INSERT INTO system_notes
                (title, content)
                VALUES (?, ?)
                """,
                note
            )

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    users = [
        (
            "admin",
            "Tr0piC4l_Bali_2026!",
            "admin",
            "IT"
        ),
        (
            "budi.ops",
            "budi12345",
            "staff",
            "Operations"
        ),
        (
            "sari.log",
            "sari7890",
            "staff",
            "Logistics"
        )
    ]

    for user in users:
        db.execute(
            """
            INSERT OR IGNORE INTO users
            (username, password, role, department)
            VALUES (?, ?, ?, ?)
            """,
            user
        )

    # --------------------------------------------------------
    # API TOKENS
    # --------------------------------------------------------

    admin = db.execute(
        """
        SELECT id
        FROM users
        WHERE username = 'admin'
        """
    ).fetchone()

    budi = db.execute(
        """
        SELECT id
        FROM users
        WHERE username = 'budi.ops'
        """
    ).fetchone()

    if admin:
        db.execute(
            """
            INSERT OR IGNORE INTO api_tokens
            (user_id, token, scope)
            VALUES (?, ?, ?)
            """,
            (
                admin["id"],
                "SCM-TKN-admin-9a21d4e7",
                "admin,status,user"
            )
        )

    if budi:
        db.execute(
            """
            INSERT OR IGNORE INTO api_tokens
            (user_id, token, scope)
            VALUES (?, ?, ?)
            """,
            (
                budi["id"],
                "SCM-TKN-budi-7f3a9c21",
                "status,user"
            )
        )

    # --------------------------------------------------------
    # TICKETS
    # --------------------------------------------------------

    tickets = [
        (
            "TCK-1001",
            "Server monitoring alert",
            "Monitoring server mengirimkan alert CPU tinggi.",
            "open",
            budi["id"] if budi else None
        ),
        (
            "TCK-1002",
            "VPN access request",
            "Permintaan akses VPN untuk tim Operations.",
            "closed",
            budi["id"] if budi else None
        ),
        (
            "TCK-1003",
            "RDP workstation issue",
            "Workstation internal mengalami masalah koneksi.",
            "open",
            admin["id"] if admin else None
        ),
        (
            "TCK-1004",
            "Warehouse network",
            "Gangguan koneksi pada jaringan warehouse.",
            "pending",
            budi["id"] if budi else None
        )
    ]

    for ticket in tickets:
        db.execute(
            """
            INSERT OR IGNORE INTO tickets
            (
                ticket_code,
                title,
                description,
                status,
                assigned_to
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ticket
        )

    # --------------------------------------------------------
    # NOTES
    # --------------------------------------------------------

    notes = [
        (
            "IT Admin",
            "Monitoring workstation menggunakan Ubuntu XFCE melalui XRDP.",
            "2026-02-10 10:15:00"
        ),
        (
            "Operations",
            "Jangan membagikan credential workstation internal.",
            "2026-02-11 08:45:00"
        )
    ]

    for note in notes:
        exists = db.execute(
            """
            SELECT id
            FROM notes
            WHERE author = ? AND content = ?
            """,
            (note[0], note[1])
        ).fetchone()

        if not exists:
            db.execute(
                """
                INSERT INTO notes
                (author, content, created_at)
                VALUES (?, ?, ?)
                """,
                note
            )

    # --------------------------------------------------------
    # COMMIT
    # --------------------------------------------------------

    db.commit()
    db.close()


# ============================================================
# AUTHENTICATION
# ============================================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            abort(403)

        return function(*args, **kwargs)

    return wrapper


# ============================================================
# LANDING PAGE
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# ABOUT
# ============================================================

@app.route("/about")
def about():
    return render_template("about.html")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":

        if "user_id" in session:
            return redirect(url_for("dashboard"))

        return redirect(url_for("index"))

    username = request.form.get(
        "username",
        ""
    )

    password = request.form.get(
        "password",
        ""
    )

    db = get_db()

    # ========================================================
    # INTENTIONALLY VULNERABLE SQL INJECTION
    # ========================================================

    query = (
        "SELECT * FROM users "
        f"WHERE username = '{username}' "
        f"AND password = '{password}'"
    )

    try:

        user = db.execute(
            query
        ).fetchone()

    except sqlite3.Error:

        db.close()

        return render_template(
            "index.html",
            error="Query error. Kamu mencoba sesuatu?"
        )

    # --------------------------------------------------------
    # USERNAME CHECK
    # --------------------------------------------------------

    username_check = db.execute(
        """
        SELECT *
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    db.close()

    # --------------------------------------------------------
    # LOGIN SUCCESS
    # --------------------------------------------------------

    if user:

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["department"] = user["department"]

        return redirect(
            url_for("dashboard")
        )

    # --------------------------------------------------------
    # WRONG PASSWORD
    # --------------------------------------------------------

    if username_check:

        return render_template(
            "index.html",
            error="Password salah."
        )

    # --------------------------------------------------------
    # UNKNOWN USER
    # --------------------------------------------------------

    return render_template(
        "index.html",
        error="Siapa kamu?"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    db = get_db()

    ticket_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM tickets
        """
    ).fetchone()["total"]

    open_tickets = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM tickets
        WHERE status = 'open'
        """
    ).fetchone()["total"]

    user_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM users
        """
    ).fetchone()["total"]

    notes = []

    if session.get("role") == "admin":

        notes = db.execute(
            """
            SELECT *
            FROM notes
            ORDER BY id DESC
            """
        ).fetchall()

    db.close()

    stats = {
        "tickets": ticket_count,
        "open_tickets": open_tickets,
        "users": user_count
    }

    return render_template(
        "dashboard.html",
        username=session.get("username"),
        role=session.get("role"),
        department=session.get("department"),
        stats=stats,
        notes=notes
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/dashboard/admin")
@admin_required
def admin_dashboard():

    db = get_db()

    users = db.execute(
        """
        SELECT id, username, role, department
        FROM users
        ORDER BY id
        """
    ).fetchall()

    logs = db.execute(
        """
        SELECT *
        FROM audit_logs
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()

    db.close()

    return render_template(
        "dashboard.html",
        username=session.get("username"),
        role="admin",
        department=session.get("department"),
        users=users,
        logs=logs
    )


# ============================================================
# NOTES
# ============================================================

@app.route("/notes")
@admin_required
def notes():

    db = get_db()

    notes_data = db.execute(
        """
        SELECT *
        FROM notes
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return render_template(
        "notes.html",
        notes=notes_data
    )


# ============================================================
# SEARCH
# ============================================================

@app.route("/search")
@login_required
def search():

    search_term = request.args.get(
        "q",
        ""
    )

    results = []

    if search_term:

        db = get_db()

        # ====================================================
        # INTENTIONALLY VULNERABLE SQL INJECTION
        # ====================================================

        query = (
            "SELECT id, ticket_code, title, description, "
            "status, assigned_to "
            "FROM tickets "
            f"WHERE ticket_code LIKE '%{search_term}%' "
            f"OR title LIKE '%{search_term}%'"
        )

        try:

            results = db.execute(
                query
            ).fetchall()

        except sqlite3.Error:

            results = []

        db.close()

    return render_template(
        "search.html",
        query=search_term,
        results=results
    )


# ============================================================
# TICKET PAGE
# ============================================================

@app.route("/ticket")
@login_required
def ticket():

    ticket_id = request.args.get(
        "id",
        ""
    )

    db = get_db()

    try:

        query = (
            "SELECT id, ticket_code, title, description, "
            "status, assigned_to "
            "FROM tickets "
            f"WHERE id = {ticket_id}"
        )

        result = db.execute(
            query
        ).fetchone()

    except sqlite3.Error:

        result = None

    db.close()

    return render_template(
        "ticket.html",
        ticket=result
    )


# ============================================================
# API TOKEN HELPER
# ============================================================

def get_api_token():

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    if authorization.startswith("Bearer "):

        return authorization[
            7:
        ].strip()

    token = request.args.get(
        "token"
    )

    return token


def token_valid(token):

    if not token:
        return None

    db = get_db()

    result = db.execute(
        """
        SELECT
            api_tokens.*,
            users.username,
            users.role
        FROM api_tokens
        JOIN users
            ON users.id = api_tokens.user_id
        WHERE api_tokens.token = ?
        """,
        (token,)
    ).fetchone()

    db.close()

    return result


# ============================================================
# API STATUS
# ============================================================

@app.route("/api/v1/status")
def api_status():

    token = get_api_token()

    api_user = token_valid(
        token
    )

    if not api_user:

        return jsonify({
            "error": "unauthorized",
            "message": "Valid API token required."
        }), 401

    return jsonify({
        "status": "online",
        "application": "SCARAMEOW Internal Portal",
        "version": "2.5.0",
        "environment": "production",
        "server": "admin-desktop",
        "rdp": {
            "enabled": True,
            "port": 3389
        },
        "authenticated_as": api_user["username"],
        "scope": api_user["scope"]
    })


# ============================================================
# API USER
# ============================================================

@app.route("/api/v1/user")
def api_user():

    token = get_api_token()

    api_auth = token_valid(
        token
    )

    if not api_auth:

        return jsonify({
            "error": "unauthorized"
        }), 401

    user_id = request.args.get(
        "id",
        ""
    )

    db = get_db()

    # ========================================================
    # INTENTIONALLY VULNERABLE IDOR / SQL INJECTION
    # ========================================================

    try:

        query = (
            "SELECT id, username, role, department "
            "FROM users "
            f"WHERE id = {user_id}"
        )

        users = db.execute(
            query
        ).fetchall()

    except sqlite3.Error:

        db.close()

        return jsonify({
            "error": "database_error"
        }), 500

    db.close()

    return jsonify({
        "count": len(users),
        "users": [
            dict(user)
            for user in users
        ]
    })


# ============================================================
# API TICKET
# ============================================================

@app.route("/api/v1/ticket")
def api_ticket():

    token = get_api_token()

    api_auth = token_valid(
        token
    )

    if not api_auth:

        return jsonify({
            "error": "unauthorized"
        }), 401

    ticket_id = request.args.get(
        "id",
        ""
    )

    db = get_db()

    # ========================================================
    # INTENTIONALLY VULNERABLE SQL INJECTION
    # ========================================================

    try:

        query = (
            "SELECT id, ticket_code, title, description, "
            "status, assigned_to "
            "FROM tickets "
            f"WHERE id = {ticket_id}"
        )

        tickets = db.execute(
            query
        ).fetchall()

    except sqlite3.Error:

        db.close()

        return jsonify({
            "error": "database_error"
        }), 500

    db.close()

    return jsonify({
        "count": len(tickets),
        "tickets": [
            dict(ticket)
            for ticket in tickets
        ]
    })


# ============================================================
# DEBUG API
# ============================================================

@app.route("/api/v1/debug")
def api_debug():

    return jsonify({
        "debug": True,
        "application": "SCARAMEOW Internal Portal",
        "version": "2.5.0",
        "build": "20260210",
        "database": DATABASE,
        "database_engine": "SQLite",
        "python": "3.x",
        "internal_service": "admin-desktop",
        "internal_rdp_port": 3389,
        "message": "Debug endpoint should not be exposed in production."
    }), 500


# ============================================================
# ROBOTS.TXT
# ============================================================

@app.route("/robots.txt")
def robots():

    content = """User-agent: *
Disallow: /backup/
Disallow: /api/
Disallow: /notes
Disallow: /dashboard/admin
"""

    response = make_response(
        content
    )

    response.headers[
        "Content-Type"
    ] = "text/plain"

    return response


# ============================================================
# BACKUP DIRECTORY
# ============================================================

@app.route("/backup/")
def backup_index():

    return """
<!DOCTYPE html>
<html>
<head>
    <title>Index of /backup/</title>
</head>
<body>
    <h1>Index of /backup/</h1>
    <hr>
    <ul>
        <li>
            <a href="/backup/README.txt">
                README.txt
            </a>
        </li>
        <li>
            <a href="/backup/db.sql.bak">
                db.sql.bak
            </a>
        </li>
    </ul>
    <hr>
</body>
</html>
"""


# ============================================================
# BACKUP FILE
# ============================================================

@app.route("/backup/<path:filename>")
def backup_file(filename):

    backup_directory = os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        "backup"
    )

    requested_file = os.path.join(
        backup_directory,
        filename
    )

    if not os.path.isfile(
        requested_file
    ):
        abort(404)

    with open(
        requested_file,
        "rb"
    ) as file:

        response = make_response(
            file.read()
        )

    response.headers[
        "Content-Type"
    ] = "text/plain"

    return response


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(403)
def forbidden(error):

    return render_template(
        "403.html"
    ), 403


@app.errorhandler(404)
def not_found(error):

    return render_template(
        "404.html"
    ), 404


@app.errorhandler(500)
def server_error(error):

    return render_template(
        "500.html"
    ), 500


# ============================================================
# STARTUP
# ============================================================

with app.app_context():
    init_db()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )