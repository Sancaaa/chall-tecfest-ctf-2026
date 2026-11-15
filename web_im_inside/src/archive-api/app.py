import os
import secrets
import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory session registry: token -> user dict
sessions = {}

def get_db():
    conn = sqlite3.connect("/tmp/archive.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    );
    """)
    cursor.execute("DELETE FROM users;")
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES ('admin', 'v3ry_s3cur3_p4ssw0rd_92817412894', 'admin');"
    )
    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES ('staff_auditor', 'auditor_p4ss_random_5129', 'staff');"
    )
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Archive API",
        "version": "1.2",
        "documentation": "/docs",
        "message": "Staff access required for audit records."
    }), 200

@app.route("/docs", methods=["GET"])
def docs():
    return jsonify({
        "service": "Archive API Documentation",
        "version": "1.2",
        "description": "Internal document archive and compliance audit service for RelayDesk cluster.",
        "endpoints": [
            {
                "method": "POST",
                "path": "/staff/session",
                "description": "Authenticate staff member to acquire session access token",
                "headers": {
                    "Content-Type": "application/json"
                },
                "request_body": {
                    "username": "admin",
                    "password": "example-password"
                }
            },
            {
                "method": "GET",
                "path": "/staff/audit",
                "description": "Retrieve internal compliance and audit records",
                "headers": {
                    "Authorization": "Bearer <access_token>"
                }
            }
        ]
    }), 200

@app.route("/staff/session", methods=["POST"])
def create_session():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Malformed JSON payload in request body"}), 400

    username = str(data.get("username", ""))
    password = str(data.get("password", ""))

    # Intentionally vulnerable query: direct interpolation enables SQL injection
    query = f"SELECT id, username, role FROM users WHERE username = '{username}' AND password = '{password}' LIMIT 1;"

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        user = cursor.fetchone()
    except sqlite3.Error as e:
        conn.close()
        return jsonify({"error": f"Database syntax error: {str(e)}"}), 500

    conn.close()

    if user:
        user_id, user_name, role = user
        token = secrets.token_hex(24)
        sessions[token] = {
            "id": user_id,
            "username": user_name,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        return jsonify({
            "access_token": token,
            "token_type": "Bearer",
            "role": role
        }), 200

    return jsonify({"error": "Invalid username or password"}), 401

@app.route("/staff/audit", methods=["GET"])
def get_audit():
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Unauthorized: valid staff bearer token required"}), 401

    token = auth_header[7:].strip()
    session = sessions.get(token)
    if not session:
        return jsonify({"error": "Unauthorized: session token is invalid or expired"}), 401

    if session.get("role") != "admin":
        return jsonify({"error": "Forbidden: administrative privileges required"}), 403

    flag = os.environ.get("FLAG", "TecFest26{wh3n_yhH_b1s4_d1_d4l3m_h4t1_ny4_d14}")
    return jsonify({
        "record_id": "AUDIT-026",
        "classification": "internal",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operator": session.get("username"),
        "note": flag
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)

