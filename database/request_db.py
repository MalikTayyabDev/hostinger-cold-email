"""Per-request database connections for serverless (Vercel)."""
from flask import g


class RequestDbProxy:
    """Routes keep a reference to this; each call uses the current request connection."""

    def execute(self, sql, params=()):
        return get_db().execute(sql, params)

    def commit(self):
        return get_db().commit()

    def executescript(self, script):
        return get_db().executescript(script)

    def __getattr__(self, name):
        return getattr(get_db(), name)


def close_connection(con):
    if con is None:
        return
    raw = getattr(con, "_raw", con)
    try:
        raw.close()
    except Exception:
        pass


def get_db():
    if "db" not in g:
        raise RuntimeError("Database not initialized for this request.")
    return g.db


def init_app_db(app, cfg):
    from database.db import connect
    from routes.auth_helpers import init_admin_user

    db_path = cfg.get("DATABASE") or "campaign.db"
    app.config["DATABASE_PATH"] = db_path

    @app.before_request
    def open_db():
        if "db" not in g:
            g.db = connect(db_path)
        if not app.config.get("_admin_initialized"):
            init_admin_user(g.db, cfg)
            app.config["_admin_initialized"] = True

    @app.teardown_appcontext
    def close_db(exc):
        con = g.pop("db", None)
        close_connection(con)
