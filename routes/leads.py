import csv
import io

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from routes.auth_helpers import generate_csrf_token, get_current_user_id, login_required, validate_csrf
from services import campaign_service, lead_service, opener_service, signature_service
from services.lead_meta import opener_angle_from_row

leads_bp = Blueprint("leads", __name__, url_prefix="/leads")


def register_leads(app, con, cfg):
    @leads_bp.route("/")
    @login_required
    def index():
        user_id = get_current_user_id()
        campaign_id = request.args.get("campaign_id", type=int)
        status = request.args.get("status")
        search = request.args.get("q")
        page = request.args.get("page", 1, type=int)
        sort = request.args.get("sort", "id")
        order = request.args.get("order", "desc")

        try:
            rows, total = lead_service.list_leads(
                con, campaign_id=campaign_id, status=status,
                search=search, page=page, sort=sort, order=order, user_id=user_id,
            )
            campaigns = campaign_service.list_campaigns(con, user_id)
        except Exception as exc:
            flash(f"Could not load leads: {exc}", "error")
            rows, total, campaigns = [], 0, []
        per_page = 50
        pages = max(1, (total + per_page - 1) // per_page)

        return render_template(
            "leads/index.html",
            rows=rows,
            campaigns=campaigns,
            campaign_id=campaign_id,
            status=status,
            search=search,
            page=page,
            pages=pages,
            total=total,
            sort=sort,
            order=order,
            csrf_token=generate_csrf_token(),
        )

    @leads_bp.route("/<int:lead_id>")
    @login_required
    def detail(lead_id):
        lead = lead_service.get_lead(con, lead_id)
        if not lead:
            flash("Lead not found.", "error")
            return redirect(url_for("leads.index"))

        memberships = con.execute(
            """SELECT cl.*, c.name AS campaign_name FROM campaign_leads cl
               JOIN campaigns c ON c.id=cl.campaign_id
               WHERE cl.lead_id=?""",
            (lead_id,),
        ).fetchall()

        cl_id = request.args.get("cl", type=int)
        if not cl_id and memberships:
            cl_id = memberships[0]["id"]

        timeline = lead_service.lead_timeline(con, lead_id, cl_id)
        steps = []
        if cl_id:
            cl = con.execute("SELECT * FROM campaign_leads WHERE id=?", (cl_id,)).fetchone()
            if cl:
                steps = campaign_service.get_steps(con, cl["campaign_id"])

        return render_template(
            "leads/detail.html",
            lead=lead,
            memberships=memberships,
            cl_id=cl_id,
            timeline=timeline,
            steps=steps,
            csrf_token=generate_csrf_token(),
        )

    @leads_bp.route("/<int:lead_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit(lead_id):
        lead = lead_service.get_lead(con, lead_id)
        if not lead:
            flash("Lead not found.", "error")
            return redirect(url_for("leads.index"))

        if request.method == "POST":
            validate_csrf()
            lead_service.update_lead(con, lead_id, {
                "first_name": request.form.get("first_name", ""),
                "last_name": request.form.get("last_name", ""),
                "full_name": request.form.get("full_name", ""),
                "company": request.form.get("company", ""),
                "email": request.form.get("email", "").strip().lower(),
                "website": request.form.get("website", ""),
                "industry": request.form.get("industry", ""),
                "location": request.form.get("location", ""),
                "opener_angle": request.form.get("opener_angle", "auto"),
                "custom_line": request.form.get("custom_line", ""),
                "tags": request.form.get("tags", ""),
                "notes": request.form.get("notes", ""),
            })
            flash("Lead updated.", "success")
            return redirect(url_for("leads.detail", lead_id=lead_id))

        return render_template(
            "leads/edit.html",
            lead=lead,
            opener_angles=opener_service.list_angles_for_ui(),
            lead_opener_angle=opener_angle_from_row(lead),
            csrf_token=generate_csrf_token(),
        )

    @leads_bp.route("/add", methods=["GET", "POST"])
    @login_required
    def add_lead():
        user_id = get_current_user_id()
        campaigns = campaign_service.list_campaigns(con, user_id)
        campaign_id = request.args.get("campaign_id", type=int) or request.form.get("campaign_id", type=int)

        if request.method == "POST":
            validate_csrf()
            campaign_id = int(request.form.get("campaign_id", 0))
            if not campaign_service.get_campaign(con, campaign_id, user_id):
                flash("Select a valid campaign.", "error")
                return redirect(url_for("leads.add_lead"))

            mode = request.form.get("mode", "single")
            if mode == "bulk":
                result = lead_service.add_leads_bulk(con, campaign_id, request.form.get("emails_text", ""))
                flash(
                    f"Added {result['added']} lead(s). Skipped — invalid: {result['invalid']}, "
                    f"duplicates: {result['duplicates']}, suppressed: {result['suppressed']}.",
                    "success" if result["added"] else "warning",
                )
            else:
                result = lead_service.add_lead(con, campaign_id, {
                    "email": request.form.get("email", ""),
                    "first_name": request.form.get("first_name", ""),
                    "last_name": request.form.get("last_name", ""),
                    "full_name": request.form.get("full_name", ""),
                    "company": request.form.get("company", ""),
                    "website": request.form.get("website", ""),
                    "industry": request.form.get("industry", ""),
                    "location": request.form.get("location", ""),
                    "opener_angle": request.form.get("opener_angle", "auto"),
                    "custom_line": request.form.get("custom_line", ""),
                })
                if result["status"] == "added":
                    flash("Lead added.", "success")
                elif result["status"] == "duplicate":
                    flash("That email is already in this campaign.", "warning")
                elif result["status"] == "suppressed":
                    flash("That email is on the suppression list.", "error")
                else:
                    flash("Invalid email address.", "error")
            return redirect(url_for("campaigns.detail", campaign_id=campaign_id))

        return render_template(
            "leads/add.html",
            campaigns=campaigns,
            campaign_id=campaign_id,
            opener_angles=opener_service.list_angles_for_ui(),
            csrf_token=generate_csrf_token(),
        )

    @leads_bp.post("/suppress/<int:campaign_lead_id>")
    @login_required
    def suppress(campaign_lead_id):
        validate_csrf()
        lead_service.suppress_lead(con, campaign_lead_id)
        flash("Lead suppressed.", "success")
        return redirect(request.referrer or url_for("leads.index"))

    @leads_bp.route("/import", methods=["GET", "POST"])
    @login_required
    def import_csv():
        user_id = get_current_user_id()
        campaigns = campaign_service.list_campaigns(con, user_id)
        campaign_id = request.args.get("campaign_id", type=int)
        if request.method == "POST":
            validate_csrf()
            campaign_id = int(request.form.get("campaign_id", 0))
            if not campaign_service.get_campaign(con, campaign_id, user_id):
                flash("Select a valid campaign.", "error")
                return redirect(url_for("leads.import_csv"))
            f = request.files.get("file")
            if not f or not campaign_id:
                flash("Select a campaign and CSV file.", "error")
                return redirect(url_for("leads.import_csv"))

            if not f.filename.lower().endswith(".csv"):
                flash("Only .csv files allowed.", "error")
                return redirect(url_for("leads.import_csv"))

            data = f.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024:
                flash("File too large (max 5 MB).", "error")
                return redirect(url_for("leads.import_csv"))

            text = data.decode("utf-8-sig")
            rows = list(csv.DictReader(text.splitlines()))

            if request.form.get("confirm") != "1":
                preview = lead_service.preview_import(con, campaign_id, rows)
                return render_template(
                    "leads/import_preview.html",
                    preview=preview,
                    campaign_id=campaign_id,
                    campaigns=campaigns,
                    csrf_token=generate_csrf_token(),
                )

            result = lead_service.import_leads(con, campaign_id, rows)
            flash(
                f"Imported {result['imported']} leads. "
                f"Skipped — invalid: {result['invalid']}, duplicates: {result['duplicates']}.",
                "success",
            )
            return redirect(url_for("leads.index", campaign_id=campaign_id))

        return render_template("leads/import.html", campaigns=campaigns, campaign_id=campaign_id, csrf_token=generate_csrf_token())

    @leads_bp.get("/import/sample")
    @login_required
    def import_sample():
        return send_file(
            io.BytesIO(signature_service.SAMPLE_CSV.encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="sample_leads.csv",
        )

    @leads_bp.get("/export")
    @login_required
    def export_csv():
        campaign_id = request.args.get("campaign_id", type=int)
        status = request.args.get("status")
        suppressed = request.args.get("suppressed") == "1"

        rows = lead_service.export_leads(con, campaign_id, status, suppressed)
        output = io.StringIO()
        if suppressed:
            writer = csv.DictWriter(output, fieldnames=["email", "reason", "source", "created_at"])
            writer.writeheader()
            for r in rows:
                writer.writerow(dict(r))
        else:
            if not rows:
                flash("No leads to export.", "warning")
                return redirect(url_for("leads.index"))
            writer = csv.DictWriter(output, fieldnames=list(dict(rows[0]).keys()))
            writer.writeheader()
            for r in rows:
                writer.writerow(dict(r))

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="leads_export.csv",
        )

    app.register_blueprint(leads_bp)
