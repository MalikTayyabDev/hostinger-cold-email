from flask import Blueprint, flash, redirect, render_template, request, url_for

from routes.auth_helpers import generate_csrf_token, get_current_user_id, get_user_cfg, login_required, validate_csrf
from services import campaign_service, email_service, scheduler_service, signature_service, template_service
from services.user_settings_service import smtp_configured

campaigns_bp = Blueprint("campaigns", __name__, url_prefix="/campaigns")


def register_campaigns(app, con, cfg):
    def _campaign(campaign_id):
        return campaign_service.get_campaign(con, campaign_id, get_current_user_id())

    @campaigns_bp.route("/")
    @login_required
    def index():
        campaigns = campaign_service.list_campaigns(con, get_current_user_id())
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
                sig_raw = request.form.get("signature_id")
                signature_id = int(sig_raw) if sig_raw else None
                cid = campaign_service.create_campaign(
                    con,
                    name,
                    request.form.get("description", ""),
                    user_id=get_current_user_id(),
                    signature_id=signature_id,
                )
                flash("Campaign created.", "success")
                return redirect(url_for("campaigns.detail", campaign_id=cid))
        signatures = signature_service.list_signatures(con, get_current_user_id())
        return render_template(
            "campaigns/form.html",
            campaign=None,
            signatures=signatures,
            csrf_token=generate_csrf_token(),
        )

    @campaigns_bp.route("/<int:campaign_id>")
    @login_required
    def detail(campaign_id):
        user_id = get_current_user_id()
        user_cfg = get_user_cfg(con, cfg, user_id)
        campaign = _campaign(campaign_id)
        if not campaign:
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        steps = campaign_service.get_steps(con, campaign_id)
        stats = campaign_service.campaign_stats(con, campaign_id)
        signatures = signature_service.list_signatures(con, user_id)
        selected_sig = None
        signature_preview_html = ""
        if campaign["signature_id"]:
            selected_sig = signature_service.get_signature(con, campaign["signature_id"], user_id)
            if selected_sig:
                signature_preview_html = signature_service.render_html(selected_sig)
        return render_template(
            "campaigns/detail.html",
            campaign=campaign,
            steps=steps,
            stats=stats,
            signatures=signatures,
            selected_sig=selected_sig,
            signature_preview_html=signature_preview_html,
            smtp_ready=smtp_configured(user_cfg),
            dry=user_cfg["DRY_RUN"],
            csrf_token=generate_csrf_token(),
        )

    @campaigns_bp.route("/<int:campaign_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit(campaign_id):
        campaign = _campaign(campaign_id)
        if not campaign:
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))

        if request.method == "POST":
            validate_csrf()
            sig_raw = request.form.get("signature_id")
            campaign_service.update_campaign(con, campaign_id, {
                "name": request.form.get("name", "").strip(),
                "description": request.form.get("description", ""),
                "daily_send_limit": request.form.get("daily_send_limit") or None,
                "delay_min_seconds": request.form.get("delay_min_seconds") or None,
                "delay_max_seconds": request.form.get("delay_max_seconds") or None,
                "signature_id": int(sig_raw) if sig_raw else None,
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
        signatures = signature_service.list_signatures(con, get_current_user_id())
        return render_template(
            "campaigns/edit.html",
            campaign=campaign,
            steps=steps,
            signatures=signatures,
            csrf_token=generate_csrf_token(),
        )

    @campaigns_bp.post("/<int:campaign_id>/signature")
    @login_required
    def set_signature(campaign_id):
        validate_csrf()
        campaign = _campaign(campaign_id)
        if not campaign:
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        sig_raw = request.form.get("signature_id")
        signature_id = int(sig_raw) if sig_raw else None
        if signature_id and not signature_service.get_signature(con, signature_id, get_current_user_id()):
            flash("Invalid signature.", "error")
            return redirect(url_for("campaigns.detail", campaign_id=campaign_id))
        campaign_service.update_campaign(con, campaign_id, {"signature_id": signature_id})
        flash("Email signature updated.", "success")
        return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

    @campaigns_bp.post("/<int:campaign_id>/start")
    @login_required
    def start(campaign_id):
        validate_csrf()
        if not _campaign(campaign_id):
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        user_cfg = get_user_cfg(con, cfg, get_current_user_id())
        if not smtp_configured(user_cfg):
            flash("Connect your email in Settings before starting a campaign.", "error")
            return redirect(url_for("settings.index"))
        campaign_service.set_campaign_status(con, campaign_id, "active")
        flash("Campaign started — click Send Now to email your leads.", "success")
        return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

    @campaigns_bp.post("/<int:campaign_id>/send")
    @login_required
    def send_now(campaign_id):
        validate_csrf()
        user_id = get_current_user_id()
        campaign = _campaign(campaign_id)
        if not campaign:
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        user_cfg = get_user_cfg(con, cfg, user_id)
        if not smtp_configured(user_cfg):
            flash("Connect your email in Settings first.", "error")
            return redirect(url_for("settings.index"))
        if campaign["status"] != "active":
            flash("Start the campaign before sending.", "warning")
            return redirect(url_for("campaigns.detail", campaign_id=campaign_id))
        result = scheduler_service.send_batch(
            con, user_cfg, limit=10, campaign_id=campaign_id, user_id=user_id
        )
        flash(
            f"Sent {result['sent']} email(s), {result['failed']} failed.",
            "success" if result["sent"] else "warning",
        )
        return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

    @campaigns_bp.post("/<int:campaign_id>/pause")
    @login_required
    def pause(campaign_id):
        validate_csrf()
        if not _campaign(campaign_id):
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        campaign_service.set_campaign_status(con, campaign_id, "paused")
        flash("Campaign paused.", "success")
        return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

    @campaigns_bp.post("/<int:campaign_id>/resume")
    @login_required
    def resume(campaign_id):
        validate_csrf()
        if not _campaign(campaign_id):
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        campaign_service.set_campaign_status(con, campaign_id, "active")
        flash("Campaign resumed.", "success")
        return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

    @campaigns_bp.post("/<int:campaign_id>/delete")
    @login_required
    def delete(campaign_id):
        validate_csrf()
        if not _campaign(campaign_id):
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        campaign_service.delete_campaign(con, campaign_id)
        flash("Campaign deleted.", "success")
        return redirect(url_for("campaigns.index"))

    @campaigns_bp.route("/<int:campaign_id>/preview")
    @login_required
    def preview(campaign_id):
        if not _campaign(campaign_id):
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        user_cfg = get_user_cfg(con, cfg, get_current_user_id())
        step_num = request.args.get("step", 1, type=int)
        lead_id = request.args.get("lead_id", type=int)
        step = campaign_service.get_step_by_number(con, campaign_id, step_num)
        lead = con.execute(
            """SELECT l.* FROM leads l
               JOIN campaign_leads cl ON cl.lead_id=l.id
               WHERE cl.campaign_id=? LIMIT 1""",
            (campaign_id,),
        ).fetchone()
        if lead_id:
            lead = con.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
        if not step or not lead:
            flash("Cannot preview — add a lead and sequence step first.", "warning")
            return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

        lead = dict(lead)
        token = template_service.ensure_unsubscribe_token(con, lead)
        lead["unsubscribe_token"] = token
        unsub = template_service.unsubscribe_url(user_cfg, lead)
        subject = template_service.render_template(step["subject"], lead, user_cfg, unsub)
        body = template_service.render_template(step["body"], lead, user_cfg, unsub)
        campaign = _campaign(campaign_id)
        signature = signature_service.get_campaign_signature(con, campaign) if campaign else None
        text_body, html_body = signature_service.compose_email_bodies(body, signature)
        return render_template(
            "campaigns/preview.html",
            campaign_id=campaign_id,
            step=step,
            lead=lead,
            subject=subject,
            body=text_body,
            html_body=html_body,
            signature=signature,
            from_email=user_cfg["FROM_EMAIL"],
            from_name=user_cfg["FROM_NAME"],
            csrf_token=generate_csrf_token(),
        )

    @campaigns_bp.post("/<int:campaign_id>/test-send")
    @login_required
    def test_send(campaign_id):
        validate_csrf()
        if not _campaign(campaign_id):
            flash("Campaign not found.", "error")
            return redirect(url_for("campaigns.index"))
        user_id = get_current_user_id()
        user_cfg = get_user_cfg(con, cfg, user_id)
        step_num = int(request.form.get("step_number", 1))
        test_email = request.form.get("test_email") or user_cfg.get("TEST_EMAIL") or user_cfg.get("FROM_EMAIL")
        if not smtp_configured(user_cfg):
            flash("Connect your email in Settings first.", "error")
            return redirect(url_for("settings.index"))
        if not test_email:
            flash("Set a test email in Settings or on the preview page.", "error")
            return redirect(url_for("campaigns.preview", campaign_id=campaign_id, step=step_num))

        step = campaign_service.get_step_by_number(con, campaign_id, step_num)
        lead = con.execute(
            """SELECT l.* FROM leads l
               JOIN campaign_leads cl ON cl.lead_id=l.id
               WHERE cl.campaign_id=? LIMIT 1""",
            (campaign_id,),
        ).fetchone()
        if not step or not lead:
            flash("Cannot send test — configure steps and import a lead.", "error")
            return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

        lead = dict(lead)
        token = template_service.ensure_unsubscribe_token(con, lead)
        lead["unsubscribe_token"] = token
        unsub = template_service.unsubscribe_url(user_cfg, lead)
        subject = "[TEST] " + template_service.render_template(step["subject"], lead, user_cfg, unsub)
        body = template_service.render_template(step["body"], lead, user_cfg, unsub)
        campaign = _campaign(campaign_id)
        signature = signature_service.get_campaign_signature(con, campaign) if campaign else None
        text_body, html_body = signature_service.compose_email_bodies(body, signature)

        try:
            email_service.smtp_send(user_cfg, test_email, subject, text_body, unsub, html_body)
            flash(f"Test email sent to {test_email}.", "success")
        except email_service.SMTPDeliveryError as exc:
            flash(str(exc), "error")

        return redirect(url_for("campaigns.preview", campaign_id=campaign_id, step=step_num))

    app.register_blueprint(campaigns_bp)
