from flask import Blueprint, flash, redirect, render_template, request, url_for

from routes.auth_helpers import generate_csrf_token, login_required, validate_csrf
from services import campaign_service, scheduler_service, template_service

campaigns_bp = Blueprint("campaigns", __name__, url_prefix="/campaigns")


def register_campaigns(app, con, cfg):
    @campaigns_bp.route("/")
    @login_required
    def index():
        campaigns = campaign_service.list_campaigns(con)
        return render_template("campaigns/index.html", campaigns=campaigns, csrf_token=generate_csrf_token())

    @campaigns_bp.route("/new", methods=["GET", "POST"])
    @login_required
    def create():
        if request.method == "POST":
            validate_csrf()
            name = request.form.get("name", "").strip()
            if not name:
                flash("Campaign name is required.", "error")
            else:
                cid = campaign_service.create_campaign(con, name, request.form.get("description", ""))
                flash("Campaign created.", "success")
                return redirect(url_for("campaigns.detail", campaign_id=cid))
        return render_template("campaigns/form.html", campaign=None, csrf_token=generate_csrf_token())

    @campaigns_bp.route("/<int:campaign_id>")
    @login_required
    def detail(campaign_id):
        campaign = campaign_service.get_campaign(con, campaign_id)
        if not campaign:
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        steps = campaign_service.get_steps(con, campaign_id)
        stats = campaign_service.campaign_stats(con, campaign_id)
        return render_template(
            "campaigns/detail.html",
            campaign=campaign,
            steps=steps,
            stats=stats,
            csrf_token=generate_csrf_token(),
        )

    @campaigns_bp.route("/<int:campaign_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit(campaign_id):
        campaign = campaign_service.get_campaign(con, campaign_id)
        if not campaign:
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))

        if request.method == "POST":
            validate_csrf()
            campaign_service.update_campaign(con, campaign_id, {
                "name": request.form.get("name", "").strip(),
                "description": request.form.get("description", ""),
                "daily_send_limit": request.form.get("daily_send_limit") or None,
                "delay_min_seconds": request.form.get("delay_min_seconds") or None,
                "delay_max_seconds": request.form.get("delay_max_seconds") or None,
            })
            steps = []
            step_nums = request.form.getlist("step_number")
            subjects = request.form.getlist("subject")
            bodies = request.form.getlist("body")
            delays = request.form.getlist("delay_days")
            for i, num in enumerate(step_nums):
                enabled = request.form.get(f"enabled_{num}") == "1"
                steps.append({
                    "step_number": int(num),
                    "subject": subjects[i],
                    "body": bodies[i],
                    "delay_days": int(delays[i] or 0),
                    "enabled": enabled,
                })
            campaign_service.save_steps(con, campaign_id, steps)
            flash("Campaign saved.", "success")
            return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

        steps = campaign_service.get_steps(con, campaign_id)
        return render_template(
            "campaigns/edit.html",
            campaign=campaign,
            steps=steps,
            csrf_token=generate_csrf_token(),
        )

    @campaigns_bp.post("/<int:campaign_id>/start")
    @login_required
    def start(campaign_id):
        validate_csrf()
        campaign_service.set_campaign_status(con, campaign_id, "active")
        flash("Campaign started.", "success")
        return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

    @campaigns_bp.post("/<int:campaign_id>/pause")
    @login_required
    def pause(campaign_id):
        validate_csrf()
        campaign_service.set_campaign_status(con, campaign_id, "paused")
        flash("Campaign paused.", "success")
        return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

    @campaigns_bp.post("/<int:campaign_id>/resume")
    @login_required
    def resume(campaign_id):
        validate_csrf()
        campaign_service.set_campaign_status(con, campaign_id, "active")
        flash("Campaign resumed.", "success")
        return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

    @campaigns_bp.post("/<int:campaign_id>/delete")
    @login_required
    def delete(campaign_id):
        validate_csrf()
        campaign_service.delete_campaign(con, campaign_id)
        flash("Campaign deleted.", "success")
        return redirect(url_for("campaigns.index"))

    @campaigns_bp.route("/<int:campaign_id>/preview")
    @login_required
    def preview(campaign_id):
        step_num = request.args.get("step", 1, type=int)
        lead_id = request.args.get("lead_id", type=int)
        step = campaign_service.get_step_by_number(con, campaign_id, step_num)
        lead = con.execute("SELECT * FROM leads LIMIT 1").fetchone()
        if lead_id:
            lead = con.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not step or not lead:
            flash("Cannot preview — add a lead and sequence step first.", "warning")
            return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

        lead = dict(lead)
        token = template_service.ensure_unsubscribe_token(con, lead)
        lead["unsubscribe_token"] = token
        unsub = template_service.unsubscribe_url(cfg, lead)
        subject = template_service.render_template(step["subject"], lead, cfg, unsub)
        body = template_service.render_template(step["body"], lead, cfg, unsub)
        return render_template(
            "campaigns/preview.html",
            campaign_id=campaign_id,
            step=step,
            lead=lead,
            subject=subject,
            body=body,
            from_email=cfg["FROM_EMAIL"],
            from_name=cfg["FROM_NAME"],
            csrf_token=generate_csrf_token(),
        )

    @campaigns_bp.post("/<int:campaign_id>/test-send")
    @login_required
    def test_send(campaign_id):
        validate_csrf()
        step_num = int(request.form.get("step_number", 1))
        test_email = cfg.get("TEST_EMAIL") or cfg.get("FROM_EMAIL")
        if not test_email:
            flash("Set TEST_EMAIL or FROM_EMAIL in .env for test sends.", "error")
            return redirect(url_for("campaigns.preview", campaign_id=campaign_id, step=step_num))

        step = campaign_service.get_step_by_number(con, campaign_id, step_num)
        lead = con.execute("SELECT * FROM leads LIMIT 1").fetchone()
        if not step or not lead:
            flash("Cannot send test — configure steps and import a lead.", "error")
            return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

        lead = dict(lead)
        token = template_service.ensure_unsubscribe_token(con, lead)
        lead["unsubscribe_token"] = token
        unsub = template_service.unsubscribe_url(cfg, lead)
        subject = "[TEST] " + template_service.render_template(step["subject"], lead, cfg, unsub)
        body = template_service.render_template(step["body"], lead, cfg, unsub)

        from services import email_service
        try:
            email_service.smtp_send(cfg, test_email, subject, body, unsub)
            flash(f"Test email sent to {test_email}.", "success")
        except email_service.SMTPDeliveryError as exc:
            flash(str(exc), "error")

        return redirect(url_for("campaigns.preview", campaign_id=campaign_id, step=step_num))

    app.register_blueprint(campaigns_bp)
