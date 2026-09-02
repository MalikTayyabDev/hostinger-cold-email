import html
import re

from database.db import utcnow_iso

DEFAULT_SIGNATURE = {
    "name": "LaunchNest Default",
    "display_name": "Sarah",
    "job_title": "Marketing Manager",
    "company": "LaunchNest",
    "tagline": "Engineering-First Digital Solutions",
    "services": "Full Stack Development • Shopify • WordPress • UI/UX • AI Automation • SEO • Quality Assurance",
    "website_url": "https://launchnest.com",
    "instagram_url": "",
    "facebook_url": "",
    "google_url": "",
    "logo_url": "",
    "footer_text": "BUILD • OPTIMIZE • LAUNCH",
}

SIGNATURE_FIELDS = [
    "name", "display_name", "job_title", "company", "tagline", "services",
    "website_url", "instagram_url", "facebook_url", "google_url", "logo_url", "footer_text",
]

SAMPLE_CSV = """name,company,email,website,custom_line
John,Example Company,john@example.com,https://example.com,"I noticed your website could make the main service CTA easier to find on mobile."
Sarah,Another Company,sarah@example.com,https://another.example.com,"I had a quick idea for improving the homepage conversion flow."
Mike,Sample Corp,mike@samplecorp.com,https://samplecorp.com,"Your site loads well on desktop but the contact form could be simplified."
"""


def _row_to_dict(row):
    return dict(row) if row else None


def list_signatures(con, user_id):
    return con.execute(
        "SELECT * FROM email_signatures WHERE user_id=? ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()


def get_signature(con, signature_id, user_id=None):
    if user_id is not None:
        return con.execute(
            "SELECT * FROM email_signatures WHERE id=? AND user_id=?",
            (signature_id, user_id),
        ).fetchone()
    return con.execute("SELECT * FROM email_signatures WHERE id=?", (signature_id,)).fetchone()


def get_campaign_signature(con, campaign):
    if not campaign:
        return None
    sig_id = campaign["signature_id"] if "signature_id" in campaign.keys() else campaign.get("signature_id")
    if not sig_id:
        return None
    user_id = campaign["user_id"] if "user_id" in campaign.keys() else campaign.get("user_id")
    return get_signature(con, sig_id, user_id)


def parse_form(form):
    data = {field: (form.get(field) or "").strip() for field in SIGNATURE_FIELDS}
    if not data["name"]:
        data["name"] = data["display_name"] or "My signature"
    return data


def create_signature(con, user_id, data):
    now = utcnow_iso()
    sig_id = con.execute(
        """INSERT INTO email_signatures(
            user_id, name, display_name, job_title, company, tagline, services,
            website_url, instagram_url, facebook_url, google_url, logo_url, footer_text,
            created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            user_id,
            data["name"],
            data["display_name"],
            data["job_title"],
            data["company"],
            data["tagline"],
            data["services"],
            data["website_url"],
            data["instagram_url"],
            data["facebook_url"],
            data["google_url"],
            data["logo_url"],
            data["footer_text"],
            now,
            now,
        ),
    ).lastrowid
    con.commit()
    return sig_id


def update_signature(con, signature_id, user_id, data):
    now = utcnow_iso()
    con.execute(
        """UPDATE email_signatures SET
            name=?, display_name=?, job_title=?, company=?, tagline=?, services=?,
            website_url=?, instagram_url=?, facebook_url=?, google_url=?, logo_url=?,
            footer_text=?, updated_at=?
           WHERE id=? AND user_id=?""",
        (
            data["name"],
            data["display_name"],
            data["job_title"],
            data["company"],
            data["tagline"],
            data["services"],
            data["website_url"],
            data["instagram_url"],
            data["facebook_url"],
            data["google_url"],
            data["logo_url"],
            data["footer_text"],
            now,
            signature_id,
            user_id,
        ),
    )
    con.commit()


def delete_signature(con, signature_id, user_id):
    con.execute(
        "UPDATE campaigns SET signature_id=NULL WHERE signature_id=? AND user_id=?",
        (signature_id, user_id),
    )
    con.execute(
        "DELETE FROM email_signatures WHERE id=? AND user_id=?",
        (signature_id, user_id),
    )
    con.commit()


def _esc(value):
    return html.escape(value or "")


def _social_link(url, label, color="#1e3a5f"):
    if not url:
        return ""
    return (
        f'<a href="{_esc(url)}" style="display:inline-block;width:28px;height:28px;'
        f'line-height:28px;text-align:center;border-radius:50%;background:{color};'
        f'color:#fff;text-decoration:none;font-size:12px;margin-right:6px">{label}</a>'
    )


def render_html(sig):
    if not sig:
        return ""
    sig = _row_to_dict(sig)
    logo_cell = ""
    if sig.get("logo_url"):
        logo_cell = (
            f'<td style="padding-right:16px;vertical-align:top">'
            f'<img src="{_esc(sig["logo_url"])}" alt="" width="56" height="56" '
            f'style="border-radius:10px;display:block"></td>'
        )
    else:
        initial = _esc((sig.get("display_name") or "N")[:1].upper())
        logo_cell = (
            f'<td style="padding-right:16px;vertical-align:top">'
            f'<div style="width:56px;height:56px;border-radius:10px;background:#1e3a5f;'
            f'color:#fff;font-size:24px;font-weight:700;text-align:center;line-height:56px">'
            f'{initial}</div></td>'
        )

    title_line = _esc(sig.get("job_title") or "")
    if sig.get("company"):
        company = _esc(sig["company"])
        if title_line:
            title_line += f' <span style="color:#c9a227">|</span> {company}'
        else:
            title_line = company

    social = ""
    social += _social_link(sig.get("website_url"), "🌐", "#c9a227")
    social += _social_link(sig.get("instagram_url"), "IG")
    social += _social_link(sig.get("facebook_url"), "f")
    social += _social_link(sig.get("google_url"), "G", "#4285f4")

    footer = ""
    if sig.get("footer_text"):
        footer = (
            f'<tr><td colspan="2" style="padding-top:14px">'
            f'<div style="border-top:1px solid #e2e8f0;padding-top:10px;font-size:11px;'
            f'letter-spacing:1px;color:#c9a227;font-weight:600">{_esc(sig["footer_text"])}</div></td></tr>'
        )

    return f"""<table cellpadding="0" cellspacing="0" style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#334155;max-width:520px;margin-top:20px">
<tr>
{logo_cell}
<td style="vertical-align:top">
<div style="width:48px;height:4px;background:#c9a227;margin-bottom:8px"></div>
<div style="font-size:22px;font-weight:700;color:#1e3a5f;line-height:1.2">{_esc(sig.get("display_name"))}</div>
<div style="font-size:13px;color:#64748b;margin:4px 0 8px">{title_line}</div>
<div style="font-size:13px;font-weight:600;color:#1e3a5f;margin-bottom:6px">{_esc(sig.get("tagline"))}</div>
<div style="font-size:12px;color:#64748b;line-height:1.5">{_esc(sig.get("services"))}</div>
<div style="margin-top:10px">{social}</div>
</td>
</tr>
{footer}
</table>"""


def render_text(sig):
    if not sig:
        return ""
    sig = _row_to_dict(sig)
    lines = []
    if sig.get("display_name"):
        lines.append(sig["display_name"])
    title_parts = [p for p in (sig.get("job_title"), sig.get("company")) if p]
    if title_parts:
        lines.append(" | ".join(title_parts))
    if sig.get("tagline"):
        lines.append(sig["tagline"])
    if sig.get("services"):
        lines.append(sig["services"])
    for key, label in (
        ("website_url", "Web"),
        ("instagram_url", "Instagram"),
        ("facebook_url", "Facebook"),
        ("google_url", "Google"),
    ):
        if sig.get(key):
            lines.append(f"{label}: {sig[key]}")
    if sig.get("footer_text"):
        lines.append(sig["footer_text"])
    return "\n".join(lines)


def plain_body_to_html(text):
    escaped = html.escape(text or "")
    paragraphs = re.split(r"\n\s*\n", escaped)
    parts = []
    for para in paragraphs:
        para = para.replace("\n", "<br>")
        parts.append(f"<p style='margin:0 0 12px;line-height:1.5'>{para}</p>")
    return "".join(parts)


def compose_email_bodies(text_body, signature):
    text = (text_body or "").rstrip()
    html_sig = render_html(signature) if signature else ""
    text_sig = render_text(signature) if signature else ""
    if text_sig:
        text = f"{text}\n\n--\n{text_sig}"
    html_body = plain_body_to_html(text_body or "")
    if html_sig:
        html_body = f"<div>{html_body}{html_sig}</div>"
    return text, html_body if html_sig else None
