from datetime import datetime, timezone

from database.db import DEFAULT_STEPS, add_event, utcnow_iso


def get_campaign(con, campaign_id, user_id=None):
    if user_id is not None:
        return con.execute(
            "SELECT * FROM campaigns WHERE id=? AND user_id=?",
            (campaign_id, user_id),
        ).fetchone()
    return con.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()


def list_campaigns(con, user_id=None):
    if user_id is not None:
        return con.execute(
            """SELECT c.*,
                (SELECT COUNT(*) FROM campaign_leads cl WHERE cl.campaign_id=c.id) AS total_leads,
                (SELECT COUNT(*) FROM campaign_leads cl WHERE cl.campaign_id=c.id AND cl.status='replied') AS replies,
                (SELECT COUNT(*) FROM campaign_leads cl WHERE cl.campaign_id=c.id AND cl.status='bounced') AS bounces,
                (SELECT COUNT(*) FROM campaign_leads cl WHERE cl.campaign_id=c.id AND cl.status='unsubscribed') AS unsubscribes,
                (SELECT COALESCE(SUM(cl.emails_sent),0) FROM campaign_leads cl WHERE cl.campaign_id=c.id) AS emails_sent
               FROM campaigns c WHERE c.user_id=? ORDER BY c.updated_at DESC""",
            (user_id,),
        ).fetchall()
    return con.execute(
        """SELECT c.*,
            (SELECT COUNT(*) FROM campaign_leads cl WHERE cl.campaign_id=c.id) AS total_leads,
            (SELECT COUNT(*) FROM campaign_leads cl WHERE cl.campaign_id=c.id AND cl.status='replied') AS replies,
            (SELECT COUNT(*) FROM campaign_leads cl WHERE cl.campaign_id=c.id AND cl.status='bounced') AS bounces,
            (SELECT COUNT(*) FROM campaign_leads cl WHERE cl.campaign_id=c.id AND cl.status='unsubscribed') AS unsubscribes,
            (SELECT COALESCE(SUM(cl.emails_sent),0) FROM campaign_leads cl WHERE cl.campaign_id=c.id) AS emails_sent
           FROM campaigns c ORDER BY c.updated_at DESC"""
    ).fetchall()


def campaign_stats(con, campaign_id):
    rows = con.execute(
        "SELECT status, COUNT(*) c FROM campaign_leads WHERE campaign_id=? GROUP BY status",
        (campaign_id,),
    ).fetchall()
    stats = {r["status"]: r["c"] for r in rows}
    sent = con.execute(
        "SELECT COALESCE(SUM(emails_sent),0) s FROM campaign_leads WHERE campaign_id=?",
        (campaign_id,),
    ).fetchone()["s"]
    replies = stats.get("replied", 0)
    stats["emails_sent"] = sent
    stats["reply_rate"] = round(replies / sent * 100, 1) if sent else 0
    return stats


def get_steps(con, campaign_id):
    return con.execute(
        """SELECT * FROM campaign_steps WHERE campaign_id=?
           ORDER BY step_number ASC""",
        (campaign_id,),
    ).fetchall()


def create_campaign(con, name, description="", user_id=None):
    now = utcnow_iso()
    cid = con.execute(
        """INSERT INTO campaigns(name, description, status, user_id, created_at, updated_at)
           VALUES(?,?,?,?,?,?)""",
        (name, description, "draft", user_id, now, now),
    ).lastrowid
    for step_num, subject, body, delay in DEFAULT_STEPS:
        enabled = 1 if step_num <= 3 else 0
        con.execute(
            """INSERT INTO campaign_steps(campaign_id, step_number, subject, body, delay_days, enabled)
               VALUES(?,?,?,?,?,?)""",
            (cid, step_num, subject, body, delay, enabled),
        )
    con.commit()
    return cid


def update_campaign(con, campaign_id, data):
    fields = [
        "name", "description", "status", "daily_send_limit",
        "delay_min_seconds", "delay_max_seconds",
    ]
    sets = ["updated_at=?"]
    params = [utcnow_iso()]
    for f in fields:
        if f in data:
            sets.append(f"{f}=?")
            params.append(data[f])
    params.append(campaign_id)
    con.execute(f"UPDATE campaigns SET {', '.join(sets)} WHERE id=?", params)
    con.commit()


def delete_campaign(con, campaign_id):
    con.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
    con.commit()


def set_campaign_status(con, campaign_id, status):
    con.execute(
        "UPDATE campaigns SET status=?, updated_at=? WHERE id=?",
        (status, utcnow_iso(), campaign_id),
    )
    con.commit()
    add_event(con, campaign_id, None, None, f"campaign_{status}", "")


def save_steps(con, campaign_id, steps):
    con.execute("DELETE FROM campaign_steps WHERE campaign_id=?", (campaign_id,))
    for step in steps:
        con.execute(
            """INSERT INTO campaign_steps(
                campaign_id, step_number, subject, body, delay_days, enabled
            ) VALUES(?,?,?,?,?,?)""",
            (
                campaign_id,
                step["step_number"],
                step["subject"],
                step["body"],
                step.get("delay_days", 0),
                1 if step.get("enabled", True) else 0,
            ),
        )
    con.execute("UPDATE campaigns SET updated_at=? WHERE id=?", (utcnow_iso(), campaign_id))
    con.commit()


def get_next_step(con, campaign_id, current_step):
    """Return next enabled step after current_step (0 = before first send)."""
    steps = get_steps(con, campaign_id)
    enabled = [s for s in steps if s["enabled"]]
    if not enabled:
        return None
    if current_step == 0:
        return enabled[0]
    for s in enabled:
        if s["step_number"] > current_step:
            return s
    return None


def get_step_by_number(con, campaign_id, step_number):
    return con.execute(
        "SELECT * FROM campaign_steps WHERE campaign_id=? AND step_number=?",
        (campaign_id, step_number),
    ).fetchone()
