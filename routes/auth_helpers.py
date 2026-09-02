from functools import wraps

from flask import flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import auth_enabled
from services.user_settings_service import merge_user_config


def init_admin_user(con, cfg):
    if not cfg.get("ADMIN_USERNAME") or not cfg.get("ADMIN_PASSWORD"):
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


def is_authenticated():
    return bool(session.get("logged_in") and session.get("user_id"))


def clear_stale_session():
    if session.get("logged_in") and not session.get("user_id"):
        session.clear()


def get_current_user_id():
    return session.get("user_id")


def get_user_cfg(con, base_cfg, user_id=None):
    uid = user_id or get_current_user_id()
    if not uid:
        return base_cfg
    return merge_user_config(base_cfg, con, uid)


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        from flask import current_app
        cfg = current_app.config["CFG"]
        if not auth_enabled(cfg):
            return f(*args, **kwargs)
        clear_stale_session()
        if is_authenticated():
            return f(*args, **kwargs)
        return redirect(url_for("auth.login", next=request.path))

    return wrapped


def verify_login(con, username, password):
    user = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def register_user(con, username, password):
    username = (username or "").strip()
    if not username or not password:
        return None, "Username and password are required."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    existing = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        return None, "Username already taken."
    from database.db import utcnow_iso
    cur = con.execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
        (username, generate_password_hash(password), utcnow_iso()),
    )
    con.commit()
    return cur.lastrowid, None


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
