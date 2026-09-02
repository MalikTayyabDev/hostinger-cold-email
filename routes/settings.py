from flask import Blueprint, flash, redirect, render_template, request, url_for

from routes.auth_helpers import generate_csrf_token, get_current_user_id, get_user_cfg, login_required, validate_csrf
from services import email_service
from services.user_settings_service import (
    build_settings_from_form,
    get_user_settings,
    save_user_settings,
    simple_form_view,
    smtp_configured,
)

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


def register_settings(app, con, cfg):
    @settings_bp.route("/", methods=["GET", "POST"])
    @login_required
    def index():
        user_id = get_current_user_id()
        stored = get_user_settings(con, user_id)

        if request.method == "POST":
            validate_csrf()
            data = build_settings_from_form(request.form, cfg, stored)
            try:
                save_user_settings(con, user_id, data)
            except Exception as exc:
                flash(f"Could not save settings: {exc}", "error")
                return redirect(url_for("settings.index"))
            flash("Email connected.", "success")
            return redirect(url_for("settings.index"))

        user_cfg = get_user_cfg(con, cfg, user_id)
        form = simple_form_view(cfg, stored)
        return render_template(
            "settings.html",
            form=form,
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
            flash("Save your email and password first.", "error")
            return redirect(url_for("settings.index"))
        if not test_email:
            flash("Enter where to send the test email.", "error")
            return redirect(url_for("settings.index"))
        try:
            email_service.smtp_send(
                user_cfg,
                test_email,
                "[Test] Your email is connected",
                "Success — your email is connected and ready to send campaigns.",
            )
            flash(f"Test email sent to {test_email}.", "success")
        except email_service.SMTPDeliveryError as exc:
            flash(str(exc), "error")
        return redirect(url_for("settings.index"))

    app.register_blueprint(settings_bp)
