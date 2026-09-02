from functools import wraps

from flask import flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import auth_enabled


def init_admin_user(con, cfg):
    if not auth_enabled(cfg):
        return
    username = cfg["ADMIN_USERNAME"]
    existing = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        return
    from database.db import utcnow_iso
    con.execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
        (username, generate_password_hash(cfg["ADMIN_PASSWORD"]), utcnow_iso()),
    )
    con.commit()


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        from flask import current_app
        cfg = current_app.config["CFG"]
        if not auth_enabled(cfg):
            return f(*args, **kwargs)
        if session.get("logged_in"):
            return f(*args, **kwargs)
        return redirect(url_for("auth.login", next=request.path))

    return wrapped


def verify_login(con, username, password):
    user = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return True
    return False


def generate_csrf_token():
    import secrets
    from flask import session
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def validate_csrf():
    from flask import abort, session
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token or token != session.get("_csrf"):
        abort(400, "Invalid CSRF token")
