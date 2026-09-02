import os

from flask import Flask

from config import BUILD_ID, load_config
from database.db import connect
from logging_config import setup_logging
from routes.auth import register_auth
from routes.auth_helpers import generate_csrf_token, init_admin_user
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
        con = connect(cfg.get("DATABASE") or "campaign.db")
    except Exception as exc:
        log.error("Database connection failed: %s", exc)
        return _error_app(f"{type(exc).__name__}: {exc}")

    app = Flask(__name__)
    app.secret_key = cfg["SECRET_KEY"]
    app.config["CFG"] = cfg
    app.config["DB"] = con

    init_admin_user(con, cfg)
    register_auth(app, con)
    register_dashboard(app, con, cfg)
    register_campaigns(app, con, cfg)
    register_leads(app, con, cfg)
    register_settings(app, con, cfg)
    register_unsubscribe(app, con)
    register_cron(app, con, cfg)

    @app.route("/health")
    def health():
        try:
            con.execute("SELECT 1").fetchone()
            return {"ok": True, "dry_run": cfg["DRY_RUN"], "build": BUILD_ID}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, 500

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


# Local dev entrypoint only — Vercel uses api/index.py
if not os.getenv("VERCEL"):
    app = create_app()

if __name__ == "__main__":
    application = create_app()
    cfg = application.config["CFG"]
    application.run(host=cfg["APP_HOST"], port=cfg["APP_PORT"], debug=False)
