from flask import Blueprint, flash, redirect, render_template, request, url_for

from routes.auth_helpers import generate_csrf_token, get_current_user_id, get_user_cfg, login_required, validate_csrf
from services import email_service
from services.user_settings_service import save_user_settings, settings_form_defaults, smtp_configured

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")

FORM_KEYS = (
    "SMTP_HOST", "SMTP_PORT", "SMTP_ENCRYPTION", "SMTP_USER", "SMTP_PASSWORD",
    "FROM_NAME", "FROM_EMAIL", "REPLY_TO",
    "IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD", "IMAP_FOLDER",
    "TEST_EMAIL", "DRY_RUN", "DAILY_SEND_LIMIT",
)


def register_settings(app, con, cfg):
    @settings_bp.route("/", methods=["GET", "POST"])
    @login_required
    def index():
        user_id = get_current_user_id()
        from services.user_settings_service import get_user_settings
        stored = get_user_settings(con, user_id)

        if request.method == "POST":
            validate_csrf()
            data = {key: request.form.get(key, "") for key in FORM_KEYS}
            if request.form.get("DRY_RUN") == "1":
                data["DRY_RUN"] = "true"
            else:
                data["DRY_RUN"] = "false"
            save_user_settings(con, user_id, data)
            flash("Email settings saved.", "success")
            return redirect(url_for("settings.index"))

        user_cfg = get_user_cfg(con, cfg, user_id)
        form = settings_form_defaults(cfg, stored)
        return render_template(
            "settings.html",
            settings=form,
            smtp_ready=smtp_configured(user_cfg),
            csrf_token=generate_csrf_token(),
        )

    @settings_bp.post("/test-smtp")
    @login_required
    def test_smtp():
        validate_csrf()
        user_id = get_current_user_id()
        user_cfg = get_user_cfg(con, cfg, user_id)
        test_email = request.form.get("test_email") or user_cfg.get("TEST_EMAIL") or user_cfg.get("FROM_EMAIL")
        if not smtp_configured(user_cfg):
            flash("Fill in SMTP username, password, and from email first.", "error")
            return redirect(url_for("settings.index"))
        if not test_email:
            flash("Enter a test email address.", "error")
            return redirect(url_for("settings.index"))
        try:
            email_service.smtp_send(
                user_cfg,
                test_email,
                "[Test] Cold Email SMTP connection",
                "Your SMTP settings are working. You can create a campaign and send emails.",
            )
            flash(f"Test email sent to {test_email}.", "success")
        except email_service.SMTPDeliveryError as exc:
            flash(str(exc), "error")
        return redirect(url_for("settings.index"))

    app.register_blueprint(settings_bp)
