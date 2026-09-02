from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from config import auth_enabled
from routes.auth_helpers import generate_csrf_token, is_authenticated, login_required, register_user, validate_csrf, verify_login

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from flask import current_app
    cfg = current_app.config["CFG"]
    con = current_app.config["DB"]
    if not auth_enabled(cfg):
        return redirect(url_for("dashboard.index"))

    if is_authenticated():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        validate_csrf()
        user = verify_login(con, request.form.get("username", ""), request.form.get("password", ""))
        if user:
            session["logged_in"] = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            nxt = request.args.get("next") or url_for("dashboard.index")
            return redirect(nxt)
        flash("Invalid username or password.", "error")

    return render_template(
        "login.html",
        csrf_token=generate_csrf_token(),
        allow_signup=cfg.get("ALLOW_SIGNUP", True),
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    from flask import current_app
    cfg = current_app.config["CFG"]
    con = current_app.config["DB"]
    if not auth_enabled(cfg):
        return redirect(url_for("dashboard.index"))
    if not cfg.get("ALLOW_SIGNUP", True):
        flash("Registration is disabled.", "error")
        return redirect(url_for("auth.login"))

    if is_authenticated():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        validate_csrf()
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")
        if password != confirm:
            flash("Passwords do not match.", "error")
        else:
            user_id, err = register_user(con, request.form.get("username", ""), password)
            if err:
                flash(err, "error")
            else:
                session["logged_in"] = True
                session["user_id"] = user_id
                session["username"] = request.form.get("username", "").strip()
                flash("Account created. Connect your email in Settings to start sending.", "success")
                return redirect(url_for("settings.index"))

    return render_template("register.html", csrf_token=generate_csrf_token())


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))


def register_auth(app, con):
    app.register_blueprint(auth_bp)
