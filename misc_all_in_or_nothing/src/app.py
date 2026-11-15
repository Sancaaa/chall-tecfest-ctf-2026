import os
import secrets
from flask import Flask, Response, jsonify, render_template, request, session

import db
import poker
import story

FLAG = os.environ.get("FLAG", "TecFest26{jud1_4d4l4h_j4l4n_n1nj4_ku}")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_db()


def _current_sid() -> str:
    sid = session.get("sid")
    if not sid:
        sid = secrets.token_hex(16)
        session["sid"] = sid
    return sid


def _build_table_payload(state: dict, flag_value: str | None = None) -> dict:
    payload = {
        "chips": state["chips"],
        "win_streak": state["win_streak"],
        "hands_played": state["hands_played"],
        "composure": state["composure"],
        "dealer_mood": state["dealer_mood"],
        "dealer_line": state["dealer_line"],
        "poker": poker.public_poker_view(state),
        "last_result": state["last_result"],
        "won_by": state["won_by"],
        "audit_memo_b64": story.INTERNAL_MEMO_B64,
    }
    if flag_value or state.get("won_by"):
        payload["flag"] = flag_value or FLAG
    return payload


@app.route("/")
def index():
    _current_sid()
    return render_template("index.html")


@app.route("/robots.txt")
def robots_txt():
    body = (
        "User-agent: *\n"
        "Disallow: /staff/shift-receipt\n"
        "Disallow: /api/table/state\n"
    )
    return Response(body, mimetype="text/plain")


@app.route("/staff/shift-receipt")
def shift_receipt():
    return Response(story.SHIFT_RECEIPT_TEXT, mimetype="text/plain")


@app.route("/logs/vault-audit")
def vault_audit():
    return Response(story.VAULT_AUDIT_LOG, mimetype="text/plain")


@app.route("/api/table/state")
def api_table_state():
    sid = _current_sid()
    state = db.get_state(sid)
    return jsonify(_build_table_payload(state))


@app.route("/api/poker/new", methods=["POST"])
def api_poker_new():
    sid = _current_sid()
    state = db.get_state(sid)
    meta = poker.start_hand(state)
    db.save_state(sid, state)
    payload = _build_table_payload(state)
    payload["meta"] = meta
    return jsonify(payload)


@app.route("/api/poker/action", methods=["POST"])
def api_poker_action():
    sid = _current_sid()
    state = db.get_state(sid)
    data = request.get_json(silent=True) or {}
    action = str(data.get("action", "")).strip().lower()

    res, flag = poker.apply_action(state, action, FLAG)
    if "error" in res:
        return jsonify({"error": res["error"], **_build_table_payload(state)}), 400

    db.save_state(sid, state)
    return jsonify(_build_table_payload(state, flag_value=flag))


@app.route("/api/confront/state")
def api_confront_state():
    sid = _current_sid()
    state = db.get_state(sid)
    view = story.public_confront_view(state)
    if state.get("won_by"):
        view["flag"] = FLAG
    return jsonify(view)


@app.route("/api/confront/submit", methods=["POST"])
def api_confront_submit():
    sid = _current_sid()
    state = db.get_state(sid)
    data = request.get_json(silent=True) or {}
    tactic = str(data.get("tactic", ""))
    evidence = str(data.get("evidence", ""))

    result = story.submit_confrontation(state, tactic, evidence, FLAG)
    db.save_state(sid, state)

    return jsonify(
        {
            **result,
            "confront": story.public_confront_view(state),
            "table": _build_table_payload(state, flag_value=result.get("flag")),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
