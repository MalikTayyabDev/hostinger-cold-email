from flask import Blueprint

from database.db import add_event, utcnow_iso

unsubscribe_bp = Blueprint("unsubscribe", __name__)


def register_unsubscribe(app, con):
    @unsubscribe_bp.route("/unsubscribe/<token>", methods=["GET", "POST"])
    def unsubscribe(token):
        lead = con.execute(
            "SELECT * FROM leads WHERE unsubscribe_token=?",
            (token,),
        ).fetchone()
        if not lead and token.isdigit():
            lead = con.execute("SELECT * FROM leads WHERE id=?", (int(token),)).fetchone()

        if lead:
            now = utcnow_iso()
            rows = con.execute(
                "SELECT * FROM campaign_leads WHERE lead_id=? AND unsubscribed_at IS NULL",
                (lead["id"],),
            ).fetchall()
            for cl in rows:
                con.execute(
                    "UPDATE campaign_leads SET status='unsubscribed', unsubscribed_at=? WHERE id=?",
                    (now, cl["id"]),
                )
                add_event(con, cl["campaign_id"], lead["id"], cl["id"], "unsubscribed", "public_link")
            con.execute(
                "INSERT OR IGNORE INTO suppressions(email, reason, source, created_at) VALUES(?,?,?,?)",
                (lead["email"], "unsubscribe link", "web", now),
            )
            con.commit()

        return """
        <html><body style="font-family:Arial;max-width:600px;margin:60px auto">
        <h2>Unsubscribed</h2>
        <p>You will not receive further outreach from this sender.</p>
        </body></html>
        """

    app.register_blueprint(unsubscribe_bp)
