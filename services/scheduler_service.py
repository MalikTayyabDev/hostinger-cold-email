from datetime import datetime, timedelta, timezone

from database.db import add_event, daily_sent_count, utcnow_iso
from services import campaign_service, email_service, lead_service, template_service


def parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def _daily_limit(cfg, campaign):
    if campaign and campaign["daily_send_limit"]:
        return campaign["daily_send_limit"]
    return cfg["DAILY_SEND_LIMIT"]


def _is_suppressed(con, email):
    return con.execute(
        "SELECT id FROM suppressions WHERE lower(email)=lower(?)",
        (email,),
    ).fetchone()


def acquire_send_lock(con, campaign_lead_id, minutes=5):
    now = utcnow_iso()
    lock_until = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    cur = con.execute(
        """UPDATE campaign_leads SET send_lock_until=?
           WHERE id=? AND status IN ('pending','active')
             AND unsubscribed_at IS NULL AND replied_at IS NULL AND bounced_at IS NULL
             AND (send_lock_until IS NULL OR send_lock_until < ?)""",
        (lock_until, campaign_lead_id, now),
    )
    con.commit()
    return cur.rowcount > 0


def release_send_lock(con, campaign_lead_id):
    con.execute(
        "UPDATE campaign_leads SET send_lock_until=NULL WHERE id=?",
        (campaign_lead_id,),
    )
    con.commit()


def eligible_sends(con, campaign_id=None):
    now = datetime.now(timezone.utc)
    clauses = [
        "cl.unsubscribed_at IS NULL",
        "cl.replied_at IS NULL",
        "cl.bounced_at IS NULL",
        "cl.status IN ('pending','active')",
        "c.status='active'",
        "(cl.send_lock_until IS NULL OR cl.send_lock_until < ?)",
    ]
    params = [utcnow_iso()]

    if campaign_id:
        clauses.append("cl.campaign_id=?")
        params.append(campaign_id)

    where = " AND ".join(clauses)
    rows = con.execute(
        f"""SELECT cl.id, cl.campaign_id, cl.lead_id, cl.status, cl.sequence_step,
                   cl.emails_sent, cl.replied_at, cl.bounced_at, cl.unsubscribed_at,
                   cl.next_action_at, cl.send_lock_until,
                   l.email, l.first_name, l.last_name, l.full_name, l.company,
                   l.website, l.industry, l.location, l.custom_line, l.tags, l.notes,
                   l.unsubscribe_token, l.id AS lead_pk,
                   c.name AS campaign_name, c.daily_send_limit,
                   c.delay_min_seconds, c.delay_max_seconds, c.status AS campaign_status
            FROM campaign_leads cl
            JOIN leads l ON l.id=cl.lead_id
            JOIN campaigns c ON c.id=cl.campaign_id
            WHERE {where}
            ORDER BY cl.id""",
        params,
    ).fetchall()

    out = []
    for row in rows:
        if _is_suppressed(con, row["email"]):
            continue
        step = campaign_service.get_next_step(con, row["campaign_id"], row["sequence_step"])
        if not step:
            if row["status"] in ("pending", "active"):
                con.execute(
                    "UPDATE campaign_leads SET status='completed' WHERE id=?",
                    (row["id"],),
                )
                con.commit()
            continue

        if row["sequence_step"] == 0 and row["status"] == "pending":
            out.append((row, step))
        elif row["sequence_step"] > 0 and row["next_action_at"]:
            if parse_dt(row["next_action_at"]) <= now:
                out.append((row, step))
    return out


def send_one(con, cfg, row, step):
    lead = {
        "id": row["lead_id"],
        "email": row["email"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "full_name": row["full_name"],
        "company": row["company"],
        "website": row["website"],
        "industry": row["industry"],
        "location": row["location"],
        "custom_line": row["custom_line"],
        "tags": row["tags"],
        "notes": row["notes"],
        "unsubscribe_token": row["unsubscribe_token"],
    }
    campaign = {
        "delay_min_seconds": row["delay_min_seconds"],
        "delay_max_seconds": row["delay_max_seconds"],
    }
    cl_id = row["id"]
    campaign_id = row["campaign_id"]
    lead_id = row["lead_id"]

    if not acquire_send_lock(con, cl_id):
        return False

    token = template_service.ensure_unsubscribe_token(con, lead)
    lead["unsubscribe_token"] = token
    unsub_url = template_service.unsubscribe_url(cfg, lead)

    subject = template_service.render_template(step["subject"], lead, cfg, unsub_url)
    body = template_service.render_template(step["body"], lead, cfg, unsub_url)

    add_event(con, campaign_id, lead_id, cl_id, "queued", f"step={step['step_number']}")

    try:
        email_service.smtp_send(cfg, lead["email"], subject, body, unsub_url)
    except email_service.SMTPDeliveryError as exc:
        release_send_lock(con, cl_id)
        add_event(con, campaign_id, lead_id, cl_id, "send_failed", str(exc))
        if exc.bounce:
            now = utcnow_iso()
            con.execute(
                """UPDATE campaign_leads SET status='bounced', bounced_at=?, bounce_reason=?
                   WHERE id=?""",
                (now, str(exc), cl_id),
            )
            con.execute(
                "INSERT OR IGNORE INTO suppressions(email, reason, source, created_at) VALUES(?,?,?,?)",
                (lead["email"], str(exc), "bounce", now),
            )
            con.commit()
            add_event(con, campaign_id, lead_id, cl_id, "bounce_detected", str(exc))
        raise

    now = utcnow_iso()
    next_step = campaign_service.get_next_step(con, campaign_id, step["step_number"])
    if next_step and next_step["step_number"] != step["step_number"]:
        next_at = (
            datetime.now(timezone.utc) + timedelta(days=next_step["delay_days"])
        ).isoformat()
        status = "active"
        add_event(con, campaign_id, lead_id, cl_id, "followup_scheduled", next_at)
    else:
        next_at = None
        status = "completed"

    con.execute(
        """UPDATE campaign_leads SET status=?, sequence_step=?, emails_sent=emails_sent+1,
           last_contacted_at=?, next_action_at=?, send_lock_until=NULL
           WHERE id=?""",
        (status, step["step_number"], now, next_at, cl_id),
    )
    con.commit()
    add_event(con, campaign_id, lead_id, cl_id, "sent", f"step={step['step_number']}")
    return True


def send_batch(con, cfg, limit=None, campaign_id=None):
    campaign = campaign_service.get_campaign(con, campaign_id) if campaign_id else None
    daily_limit = _daily_limit(cfg, campaign)
    remaining = max(0, daily_limit - daily_sent_count(con, campaign_id))

    if limit is not None:
        remaining = min(remaining, limit)

    sent = failed = 0
    for row, step in eligible_sends(con, campaign_id):
        if sent >= remaining:
            break
        try:
            if send_one(con, cfg, row, step):
                sent += 1
                if sent < remaining:
                    email_service.sleep_between(cfg, campaign)
        except email_service.SMTPDeliveryError:
            failed += 1
        except Exception:
            failed += 1

    return {"sent": sent, "failed": failed}


def process_inbox(con, cfg):
    since = datetime.now(timezone.utc) - timedelta(days=30)
    messages = email_service.scan_inbox(cfg, since)
    replies = unsubscribes = 0

    for msg in messages:
        sender = msg["sender"]
        rows = con.execute(
            """SELECT cl.*, l.email, l.id AS lead_id FROM campaign_leads cl
               JOIN leads l ON l.id=cl.lead_id
               WHERE lower(l.email)=lower(?)
                 AND cl.unsubscribed_at IS NULL""",
            (sender,),
        ).fetchall()

        for row in rows:
            now = utcnow_iso()
            if msg["is_unsubscribe"]:
                con.execute(
                    "UPDATE campaign_leads SET status='unsubscribed', unsubscribed_at=? WHERE id=?",
                    (now, row["id"]),
                )
                con.execute(
                    "INSERT OR IGNORE INTO suppressions(email, reason, source, created_at) VALUES(?,?,?,?)",
                    (sender, "reply keyword", "imap", now),
                )
                con.commit()
                add_event(con, row["campaign_id"], row["lead_id"], row["id"], "unsubscribed", "reply keyword")
                unsubscribes += 1
            elif not row["replied_at"]:
                con.execute(
                    """UPDATE campaign_leads SET status='replied', replied_at=?,
                       reply_subject=?, reply_message_id=?, replies_count=replies_count+1
                       WHERE id=?""",
                    (now, msg["subject"], msg["message_id"], row["id"]),
                )
                con.commit()
                add_event(con, row["campaign_id"], row["lead_id"], row["id"], "reply_detected", sender)
                replies += 1

    return {"replies": replies, "unsubscribes": unsubscribes}


def dashboard_stats(con, campaign_id=None):
    clauses = []
    params = []
    if campaign_id:
        clauses.append("cl.campaign_id=?")
        params.append(campaign_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    status_rows = con.execute(
        f"SELECT cl.status, COUNT(*) c FROM campaign_leads cl {where} GROUP BY cl.status",
        params,
    ).fetchall()
    stats = {r["status"]: r["c"] for r in status_rows}
    total = sum(stats.values())
    sent_today = daily_sent_count(con, campaign_id)
    emails_sent = con.execute(
        f"SELECT COALESCE(SUM(cl.emails_sent),0) s FROM campaign_leads cl {where}",
        params,
    ).fetchone()["s"]
    replies = stats.get("replied", 0)
    stats.update({
        "total_leads": total,
        "pending": stats.get("pending", 0),
        "active": stats.get("active", 0),
        "replied": replies,
        "bounced": stats.get("bounced", 0),
        "unsubscribed": stats.get("unsubscribed", 0),
        "completed": stats.get("completed", 0),
        "paused": stats.get("paused", 0),
        "sent_today": sent_today,
        "emails_sent": emails_sent,
        "reply_rate": round(replies / emails_sent * 100, 1) if emails_sent else 0,
    })
    return stats
