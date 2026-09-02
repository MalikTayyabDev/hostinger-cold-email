from flask import Blueprint, flash, redirect, render_template, request, url_for

from routes.auth_helpers import generate_csrf_token, get_current_user_id, login_required, validate_csrf
from services import signature_service

signatures_bp = Blueprint("signatures", __name__, url_prefix="/signatures")


def register_signatures(app, con):
    @signatures_bp.route("/")
    @login_required
    def index():
        user_id = get_current_user_id()
        signatures = signature_service.list_signatures(con, user_id)
        return render_template(
            "signatures/index.html",
            signatures=signatures,
            csrf_token=generate_csrf_token(),
        )

    @signatures_bp.route("/new", methods=["GET", "POST"])
    @login_required
    def create():
        user_id = get_current_user_id()
        form = dict(signature_service.DEFAULT_SIGNATURE)

        if request.method == "POST":
            validate_csrf()
            data = signature_service.parse_form(request.form)
            sig_id = signature_service.create_signature(con, user_id, data)
            flash("Signature created.", "success")
            return redirect(url_for("signatures.edit", signature_id=sig_id))

        return render_template(
            "signatures/form.html",
            signature=None,
            form=form,
            preview_html=signature_service.render_html(form),
            csrf_token=generate_csrf_token(),
        )

    @signatures_bp.route("/<int:signature_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit(signature_id):
        user_id = get_current_user_id()
        signature = signature_service.get_signature(con, signature_id, user_id)
        if not signature:
            flash("Signature not found.", "error")
            return redirect(url_for("signatures.index"))

        form = {k: signature[k] for k in signature_service.SIGNATURE_FIELDS if k in signature.keys()}

        if request.method == "POST":
            validate_csrf()
            data = signature_service.parse_form(request.form)
            signature_service.update_signature(con, signature_id, user_id, data)
            flash("Signature saved.", "success")
            return redirect(url_for("signatures.edit", signature_id=signature_id))

        return render_template(
            "signatures/form.html",
            signature=signature,
            form=form,
            preview_html=signature_service.render_html(form),
            csrf_token=generate_csrf_token(),
        )

    @signatures_bp.post("/<int:signature_id>/delete")
    @login_required
    def delete(signature_id):
        validate_csrf()
        user_id = get_current_user_id()
        if not signature_service.get_signature(con, signature_id, user_id):
            flash("Signature not found.", "error")
            return redirect(url_for("signatures.index"))
        signature_service.delete_signature(con, signature_id, user_id)
        flash("Signature deleted.", "success")
        return redirect(url_for("signatures.index"))

    app.register_blueprint(signatures_bp)
