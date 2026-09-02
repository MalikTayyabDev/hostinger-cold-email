import os

from flask import Flask

from config import load_config
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


def create_app():
    cfg = load_config()
    log = setup_logging()
    con = connect(cfg.get("DATABASE") or "campaign.db")

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


app = create_app()

if __name__ == "__main__":
    cfg = app.config["CFG"]
    app.run(host=cfg["APP_HOST"], port=cfg["APP_PORT"], debug=False)
