import re
import secrets

from services import opener_service


VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")

FALLBACKS = {
    "first_name": "there",
    "last_name": "",
    "full_name": "there",
    "company": "your company",
    "website": "your website",
    "website_domain": "your site",
    "industry": "your industry",
    "location": "your area",
    "custom_line": "",
    "smart_opener": "",
    "launchnest_url": opener_service.LAUNCHNEST_URL,
    "sender_name": "",
    "unsubscribe_url": "",
    "unsubscribe_footer": "",
    "email_footer": "",
}


def _lead_values(lead, cfg, unsubscribe_url=""):
    first = (lead.get("first_name") or "").strip()
    last = (lead.get("last_name") or "").strip()
    full = (lead.get("full_name") or "").strip()
    if not full:
        full = f"{first} {last}".strip() or (lead.get("name") or "").strip()
    if not first and full:
        first = full.split()[0]

    sender = cfg.get("FROM_NAME") or "Team"
    footer = cfg.get("EMAIL_FOOTER") or ""
    unsub_footer = f"Unsubscribe: {unsubscribe_url}" if unsubscribe_url else ""
    smart = opener_service.generate_smart_opener(lead)
    custom = opener_service.resolve_custom_line(lead)
    domain = opener_service._website_domain(lead) or "your site"

    raw = {
        "first_name": first,
        "last_name": last,
        "full_name": full,
        "company": (lead.get("company") or "").strip(),
        "website": (lead.get("website") or "").strip(),
        "website_domain": domain,
        "industry": (lead.get("industry") or "").strip(),
        "location": (lead.get("location") or "").strip(),
        "custom_line": custom,
        "smart_opener": smart,
        "launchnest_url": opener_service.LAUNCHNEST_URL,
        "sender_name": sender,
        "unsubscribe_url": unsubscribe_url,
        "unsubscribe_footer": unsub_footer,
        "email_footer": footer,
    }

    out = {}
    for key, val in raw.items():
        out[key] = val if val else FALLBACKS.get(key, "")
    return out


def render_template(text, lead, cfg, unsubscribe_url=""):
    values = _lead_values(lead, cfg, unsubscribe_url)

    def replace(match):
        key = match.group(1)
        return values.get(key, FALLBACKS.get(key, ""))

    return VAR_PATTERN.sub(replace, text)


def ensure_unsubscribe_token(con, lead):
    if isinstance(lead, dict):
        token = lead.get("unsubscribe_token")
        lead_id = lead["id"]
    else:
        token = lead["unsubscribe_token"]
        lead_id = lead["id"]
    if token:
        return token
    token = secrets.token_urlsafe(32)
    con.execute("UPDATE leads SET unsubscribe_token=? WHERE id=?", (token, lead_id))
    con.commit()
    return token


def unsubscribe_url(cfg, lead):
    if not cfg.get("PUBLIC_BASE_URL"):
        return ""
    if isinstance(lead, dict):
        token = lead.get("unsubscribe_token")
    else:
        token = lead["unsubscribe_token"]
    return f'{cfg["PUBLIC_BASE_URL"]}/unsubscribe/{token}'
