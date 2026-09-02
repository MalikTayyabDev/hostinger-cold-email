from flask import Blueprint, flash, redirect, render_template, request, url_for

from database.db import daily_sent_count
from routes.auth_helpers import generate_csrf_token, login_required, validate_csrf
from services import campaign_service, scheduler_service

dashboard_bp = Blueprint("dashboard", __name__)


def register_dashboard(app, con, cfg):
    @dashboard_bp.route("/")
    @login_required
    def index():
        campaign_id = request.args.get("campaign_id", type=int)
        campaigns = campaign_service.list_campaigns(con)
        stats = scheduler_service.dashboard_stats(con, campaign_id)
        limit = cfg["DAILY_SEND_LIMIT"]
        if campaign_id:
            camp = campaign_service.get_campaign(con, campaign_id)
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
            dry=cfg["DRY_RUN"],
            csrf_token=generate_csrf_token(),
        )

    @dashboard_bp.post("/send")
    @login_required
    def send_one():
        validate_csrf()
        scheduler_service.process_inbox(con, cfg)
        result = scheduler_service.send_batch(con, cfg, limit=1)
        flash(f"Sent {result['sent']} email(s).", "success" if result["sent"] else "warning")
        return redirect(request.referrer or url_for("dashboard.index"))

    @dashboard_bp.post("/send-batch")
    @login_required
    def send_batch_route():
        validate_csrf()
        scheduler_service.process_inbox(con, cfg)
        try:
            count = int(request.form.get("count", "5"))
        except ValueError:
            count = 5
        result = scheduler_service.send_batch(con, cfg, limit=max(1, min(count, cfg["DAILY_SEND_LIMIT"])))
        flash(f"Sent {result['sent']} email(s), {result['failed']} failed.", "success" if result["sent"] else "warning")
        return redirect(request.referrer or url_for("dashboard.index"))

    app.register_blueprint(dashboard_bp)
