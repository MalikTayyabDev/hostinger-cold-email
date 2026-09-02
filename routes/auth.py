from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from routes.auth_helpers import generate_csrf_token, login_required, validate_csrf, verify_login

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from flask import current_app
    cfg = current_app.config["CFG"]
    con = current_app.config["DB"]
    if not cfg.get("ADMIN_USERNAME"):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        validate_csrf()
        if verify_login(con, request.form.get("username", ""), request.form.get("password", "")):
            session["logged_in"] = True
            session["username"] = request.form.get("username")
            nxt = request.args.get("next") or url_for("dashboard.index")
            return redirect(nxt)
        flash("Invalid username or password.", "error")

    return render_template("login.html", csrf_token=generate_csrf_token())


@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))


def register_auth(app, con):
    app.register_blueprint(auth_bp)
