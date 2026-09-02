from flask import Blueprint, render_template

from config import auth_enabled
from routes.auth_helpers import generate_csrf_token, login_required

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


def register_settings(app, con, cfg):
    @settings_bp.route("/")
    @login_required
    def index():
        masked = {
            "SMTP_HOST": cfg["SMTP_HOST"],
            "SMTP_PORT": cfg["SMTP_PORT"],
            "SMTP_ENCRYPTION": cfg["SMTP_ENCRYPTION"],
            "SMTP_USER": cfg["SMTP_USER"],
            "SMTP_PASSWORD": "********" if cfg["SMTP_PASSWORD"] else "",
            "FROM_NAME": cfg["FROM_NAME"],
            "FROM_EMAIL": cfg["FROM_EMAIL"],
            "IMAP_HOST": cfg["IMAP_HOST"],
            "IMAP_PORT": cfg["IMAP_PORT"],
            "IMAP_FOLDER": cfg["IMAP_FOLDER"],
            "IMAP_USER": cfg["IMAP_USER"],
            "IMAP_PASSWORD": "********" if cfg["IMAP_PASSWORD"] else "",
            "DAILY_SEND_LIMIT": cfg["DAILY_SEND_LIMIT"],
            "SEND_DELAY_MIN_SECONDS": cfg["SEND_DELAY_MIN_SECONDS"],
            "SEND_DELAY_MAX_SECONDS": cfg["SEND_DELAY_MAX_SECONDS"],
            "MAX_FOLLOWUPS": cfg["MAX_FOLLOWUPS"],
            "DRY_RUN": cfg["DRY_RUN"],
            "PUBLIC_BASE_URL": cfg["PUBLIC_BASE_URL"],
            "TEST_EMAIL": cfg.get("TEST_EMAIL", ""),
            "AUTH_ENABLED": auth_enabled(cfg),
        }
        return render_template(
            "settings.html",
            settings=masked,
            csrf_token=generate_csrf_token(),
        )

    app.register_blueprint(settings_bp)
