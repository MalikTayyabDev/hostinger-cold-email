import os

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

from config import BUILD_ID, load_config
from database.db import connect
from database.request_db import RequestDbProxy, close_connection, init_app_db
from logging_config import setup_logging
from routes.auth import register_auth
from routes.auth_helpers import generate_csrf_token
from routes.campaigns import register_campaigns
from routes.cron import register_cron
from routes.dashboard import register_dashboard
from routes.leads import register_leads
from routes.settings import register_settings
from routes.unsubscribe import register_unsubscribe


def _error_app(message):
    app = Flask(__name__)
    app.secret_key = "error"

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def startup_error(path):
        return (
            "<h1>Startup error</h1>"
            f"<pre>{message}</pre>"
            "<p>Check DATABASE_URL in Vercel env vars.</p>"
            "<p>If this is a timeout, run <code>supabase/migration_multi_user.sql</code> in Supabase SQL Editor, then redeploy.</p>"
        ), 500

    @app.route("/health")
    def health():
        return {"ok": False, "error": message, "build": BUILD_ID}, 500

    return app


def create_app():
    log = setup_logging()
    try:
        cfg = load_config()
        test_con = connect(cfg.get("DATABASE") or "campaign.db")
        test_con.execute("SELECT 1").fetchone()
        close_connection(test_con)
    except Exception as exc:
        log.error("Database connection failed: %s", exc)
        return _error_app(f"{type(exc).__name__}: {exc}")

    app = Flask(__name__)
    app.secret_key = cfg["SECRET_KEY"]
    app.config["CFG"] = cfg

    init_app_db(app, cfg)
    db = RequestDbProxy()

    register_auth(app, db)
    register_dashboard(app, db, cfg)
    register_campaigns(app, db, cfg)
    register_leads(app, db, cfg)
    register_settings(app, db, cfg)
    register_unsubscribe(app, db)
    register_cron(app, db, cfg)

    @app.route("/health")
    def health():
        from database.request_db import get_db
        try:
            get_db().execute("SELECT 1").fetchone()
            return {"ok": True, "dry_run": cfg["DRY_RUN"], "build": BUILD_ID}
        except Exception as exc:
            log.error("Health check failed: %s", exc)
            return {"ok": False, "error": str(exc), "build": BUILD_ID}, 500

    @app.errorhandler(500)
    def internal_server_error(e):
        log.exception("Internal server error: %s", e)
        return render_template("error.html", title="Server error", message="Something went wrong. Please try again in a moment."), 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        if isinstance(e, HTTPException):
            return e
        log.exception("Unhandled error: %s", e)
        return render_template("error.html", title="Error", message="An unexpected error occurred. Please try again."), 500

    @app.context_processor
    def inject_globals():
        return {
            "csrf_token": generate_csrf_token,
            "dry_run": cfg["DRY_RUN"],
            "campaign_name": cfg.get("CAMPAIGN_NAME", ""),
        }

    @app.template_filter("event_label")
    def event_label(value):
        labels = {
            "imported": "Lead imported",
            "queued": "Email queued",
            "sent": "Email sent",
            "send_failed": "Send failed",
            "reply_detected": "Reply detected",
            "bounce_detected": "Bounce detected",
            "unsubscribed": "Unsubscribed",
            "followup_scheduled": "Follow-up scheduled",
            "campaign_active": "Campaign started",
            "campaign_paused": "Campaign paused",
        }
        return labels.get(value, value.replace("_", " ").title())

    log.info("Application initialized (DRY_RUN=%s)", cfg["DRY_RUN"])
    return app


def get_app():
    """Factory accessor for serverless / testing."""
    return create_app()


if not os.getenv("VERCEL"):
    app = create_app()

if __name__ == "__main__":
    application = create_app()
    cfg = application.config["CFG"]
    application.run(host=cfg["APP_HOST"], port=cfg["APP_PORT"], debug=False)
