from flask import Blueprint, flash, redirect, render_template, request, url_for

from database.db import daily_sent_count
from routes.auth_helpers import generate_csrf_token, get_current_user_id, get_user_cfg, login_required, validate_csrf
from services import campaign_service, scheduler_service
from services.user_settings_service import smtp_configured

dashboard_bp = Blueprint("dashboard", __name__)


def register_dashboard(app, con, cfg):
    @dashboard_bp.route("/")
    @login_required
    def index():
        user_id = get_current_user_id()
        user_cfg = get_user_cfg(con, cfg, user_id)
        campaign_id = request.args.get("campaign_id", type=int)
        campaigns = campaign_service.list_campaigns(con, user_id)
        if campaign_id and not campaign_service.get_campaign(con, campaign_id, user_id):
            campaign_id = None
        stats = scheduler_service.dashboard_stats(con, campaign_id, user_id)
        limit = user_cfg["DAILY_SEND_LIMIT"]
        if campaign_id:
            camp = campaign_service.get_campaign(con, campaign_id, user_id)
            if camp and camp["daily_send_limit"]:
                limit = camp["daily_send_limit"]
        daily = daily_sent_count(con, campaign_id)
        return render_template(
            "dashboard.html",
            stats=stats,
            campaigns=campaigns,
            campaign_id=campaign_id,
            daily=daily,
            limit=limit,
            remaining=max(0, limit - daily),
            dry=user_cfg["DRY_RUN"],
            smtp_ready=smtp_configured(user_cfg),
            csrf_token=generate_csrf_token(),
        )

    @dashboard_bp.post("/send")
    @login_required
    def send_one():
        validate_csrf()
        user_id = get_current_user_id()
        user_cfg = get_user_cfg(con, cfg, user_id)
        if not smtp_configured(user_cfg):
            flash("Connect your email in Settings first.", "error")
            return redirect(url_for("settings.index"))
        scheduler_service.process_inbox(con, user_cfg, user_id=user_id)
        result = scheduler_service.send_batch(con, user_cfg, limit=1, user_id=user_id)
        flash(f"Sent {result['sent']} email(s).", "success" if result["sent"] else "warning")
        return redirect(request.referrer or url_for("dashboard.index"))

    @dashboard_bp.post("/send-batch")
    @login_required
    def send_batch_route():
        validate_csrf()
        user_id = get_current_user_id()
        user_cfg = get_user_cfg(con, cfg, user_id)
        if not smtp_configured(user_cfg):
            flash("Connect your email in Settings first.", "error")
            return redirect(url_for("settings.index"))
        scheduler_service.process_inbox(con, user_cfg, user_id=user_id)
        try:
            count = int(request.form.get("count", "5"))
        except ValueError:
            count = 5
        result = scheduler_service.send_batch(
            con,
            user_cfg,
            limit=max(1, min(count, user_cfg["DAILY_SEND_LIMIT"])),
            user_id=user_id,
        )
        flash(f"Sent {result['sent']} email(s), {result['failed']} failed.", "success" if result["sent"] else "warning")
        return redirect(request.referrer or url_for("dashboard.index"))

    app.register_blueprint(dashboard_bp)
