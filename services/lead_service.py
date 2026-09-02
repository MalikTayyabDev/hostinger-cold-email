import re
import secrets
from datetime import datetime, timezone

from database.db import add_event, utcnow_iso
from services.template_service import ensure_unsubscribe_token


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email):
    return (email or "").strip().lower()


def is_valid_email(email):
    return bool(email and EMAIL_RE.match(email))


def parse_name_fields(row):
    first = (row.get("first_name") or "").strip()
    last = (row.get("last_name") or "").strip()
    full = (row.get("full_name") or row.get("name") or "").strip()
    if not first and full:
        parts = full.split(None, 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else last
    if not full:
        full = f"{first} {last}".strip()
    return first, last, full


def get_lead(con, lead_id):
    return con.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()


def list_leads(con, campaign_id=None, status=None, search=None, page=1, per_page=50, sort="id", order="desc"):
    clauses = ["1=1"]
    params = []

    if campaign_id:
        clauses.append("cl.campaign_id=?")
        params.append(campaign_id)
    if status:
        clauses.append("cl.status=?")
        params.append(status)
    if search:
        clauses.append(
            "(l.full_name LIKE ? OR l.email LIKE ? OR l.company LIKE ?)"
        )
        q = f"%{search}%"
        params.extend([q, q, q])

    sort_map = {
        "id": "l.id",
        "full_name": "l.full_name",
        "company": "l.company",
        "email": "l.email",
        "status": "cl.status",
        "next_action_at": "cl.next_action_at",
        "last_contacted_at": "cl.last_contacted_at",
    }
    sort_col = sort_map.get(sort, "l.id")
    order_dir = "ASC" if order.lower() == "asc" else "DESC"
    offset = max(0, (page - 1) * per_page)

    where = " AND ".join(clauses)
    total = con.execute(
        f"""SELECT COUNT(*) c FROM campaign_leads cl
            JOIN leads l ON l.id=cl.lead_id WHERE {where}""",
        params,
    ).fetchone()["c"]

    rows = con.execute(
        f"""SELECT l.id, l.first_name, l.last_name, l.full_name, l.company, l.email,
                   l.website, l.industry, l.location, l.custom_line, l.tags, l.notes,
                   l.unsubscribe_token, l.created_at,
                   cl.id AS campaign_lead_id, cl.campaign_id, cl.status,
                   cl.sequence_step, cl.emails_sent, cl.last_contacted_at,
                   cl.next_action_at, cl.replied_at, cl.bounced_at, cl.unsubscribed_at,
                   c.name AS campaign_name
            FROM campaign_leads cl
            JOIN leads l ON l.id=cl.lead_id
            JOIN campaigns c ON c.id=cl.campaign_id
            WHERE {where}
            ORDER BY {sort_col} {order_dir}
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    ).fetchall()
    return rows, total


def lead_timeline(con, lead_id, campaign_lead_id=None):
    clauses = ["lead_id=?"]
    params = [lead_id]
    if campaign_lead_id:
        clauses.append("campaign_lead_id=?")
        params.append(campaign_lead_id)
    where = " AND ".join(clauses)
    return con.execute(
        f"SELECT * FROM email_events WHERE {where} ORDER BY created_at ASC",
        params,
    ).fetchall()


def preview_import(con, campaign_id, rows):
    valid = invalid = duplicates = suppressed = 0
    preview = []
    seen = set()

    for row in rows:
        email = normalize_email(row.get("email"))
        if not is_valid_email(email):
            invalid += 1
            preview.append({"email": email, "status": "invalid"})
            continue

        if email in seen:
            duplicates += 1
            preview.append({"email": email, "status": "duplicate_in_file"})
            continue
        seen.add(email)

        sup = con.execute(
            "SELECT id FROM suppressions WHERE lower(email)=lower(?)",
            (email,),
        ).fetchone()
        if sup:
            suppressed += 1
            preview.append({"email": email, "status": "suppressed"})
            continue

        dup = con.execute(
            """SELECT cl.id FROM campaign_leads cl
               JOIN leads l ON l.id=cl.lead_id
               WHERE cl.campaign_id=? AND lower(l.email)=lower(?)""",
            (campaign_id, email),
        ).fetchone()
        if dup:
            duplicates += 1
            preview.append({"email": email, "status": "duplicate"})
            continue

        valid += 1
        preview.append({"email": email, "status": "valid"})

    return {
        "valid": valid,
        "invalid": invalid,
        "duplicates": duplicates,
        "suppressed": suppressed,
        "preview": preview[:100],
    }


def import_leads(con, campaign_id, rows):
    result = preview_import(con, campaign_id, rows)
    imported = 0
    now = utcnow_iso()

    for row in rows:
        email = normalize_email(row.get("email"))
        if not is_valid_email(email):
            continue

        dup = con.execute(
            """SELECT cl.id FROM campaign_leads cl
               JOIN leads l ON l.id=cl.lead_id
               WHERE cl.campaign_id=? AND lower(l.email)=lower(?)""",
            (campaign_id, email),
        ).fetchone()
        if dup:
            continue

        sup = con.execute(
            "SELECT id FROM suppressions WHERE lower(email)=lower(?)",
            (email,),
        ).fetchone()
        if sup:
            continue

        first, last, full = parse_name_fields(row)
        token = secrets.token_urlsafe(32)

        existing = con.execute(
            "SELECT id FROM leads WHERE lower(email)=lower(?)",
            (email,),
        ).fetchone()

        if existing:
            lead_id = existing["id"]
        else:
            lead_id = con.execute(
                """INSERT INTO leads(
                    first_name, last_name, full_name, company, email, website,
                    industry, location, custom_line, tags, unsubscribe_token, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    first,
                    last,
                    full,
                    (row.get("company") or "").strip(),
                    email,
                    (row.get("website") or "").strip(),
                    (row.get("industry") or "").strip(),
                    (row.get("location") or "").strip(),
                    (row.get("custom_line") or "").strip(),
                    (row.get("tags") or "").strip(),
                    token,
                    now,
                ),
            ).lastrowid

        cl_id = con.execute(
            """INSERT INTO campaign_leads(campaign_id, lead_id, status, created_at)
               VALUES(?,?,?,?)""",
            (campaign_id, lead_id, "pending", now),
        ).lastrowid
        add_event(con, campaign_id, lead_id, cl_id, "imported", email)
        imported += 1

    con.commit()
    result["imported"] = imported
    return result


def suppress_lead(con, campaign_lead_id, source="manual"):
    row = con.execute(
        """SELECT cl.*, l.email, l.id AS lead_id FROM campaign_leads cl
           JOIN leads l ON l.id=cl.lead_id WHERE cl.id=?""",
        (campaign_lead_id,),
    ).fetchone()
    if not row:
        return False

    now = utcnow_iso()
    con.execute(
        "UPDATE campaign_leads SET status='unsubscribed', unsubscribed_at=? WHERE id=?",
        (now, campaign_lead_id),
    )
    con.execute(
        "INSERT OR IGNORE INTO suppressions(email, reason, source, created_at) VALUES(?,?,?,?)",
        (row["email"], "manual suppress", source, now),
    )
    con.commit()
    add_event(con, row["campaign_id"], row["lead_id"], campaign_lead_id, "unsubscribed", source)
    return True


def update_lead(con, lead_id, data):
    fields = [
        "first_name", "last_name", "full_name", "company", "email",
        "website", "industry", "location", "custom_line", "tags", "notes",
    ]
    sets = []
    params = []
    for f in fields:
        if f in data:
            sets.append(f"{f}=?")
            params.append(data[f])
    if not sets:
        return
    params.append(lead_id)
    con.execute(f"UPDATE leads SET {', '.join(sets)} WHERE id=?", params)
    con.commit()


def export_leads(con, campaign_id=None, status=None, suppressed_only=False):
    if suppressed_only:
        return con.execute(
            """SELECT s.email, s.reason, s.source, s.created_at
               FROM suppressions s ORDER BY s.created_at DESC"""
        ).fetchall()

    clauses = ["1=1"]
    params = []
    if campaign_id:
        clauses.append("cl.campaign_id=?")
        params.append(campaign_id)
    if status:
        clauses.append("cl.status=?")
        params.append(status)

    where = " AND ".join(clauses)
    return con.execute(
        f"""SELECT l.first_name, l.last_name, l.full_name, l.company, l.email,
                   l.website, l.industry, l.location, l.custom_line, l.tags,
                   cl.status, c.name AS campaign_name, cl.last_contacted_at,
                   cl.next_action_at, cl.emails_sent, cl.replies_count
            FROM campaign_leads cl
            JOIN leads l ON l.id=cl.lead_id
            JOIN campaigns c ON c.id=cl.campaign_id
            WHERE {where}
            ORDER BY l.id""",
        params,
    ).fetchall()
