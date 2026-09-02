"""Per-user email and sending settings stored in the database."""

SETTING_KEYS = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_ENCRYPTION",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "FROM_NAME",
    "FROM_EMAIL",
    "REPLY_TO",
    "IMAP_HOST",
    "IMAP_PORT",
    "IMAP_USER",
    "IMAP_PASSWORD",
    "IMAP_FOLDER",
    "TEST_EMAIL",
    "DRY_RUN",
    "DAILY_SEND_LIMIT",
)

INT_KEYS = {"SMTP_PORT", "IMAP_PORT", "DAILY_SEND_LIMIT"}
BOOL_KEYS = {"DRY_RUN"}


HOSTINGER_DEFAULTS = {
    "SMTP_HOST": "smtp.hostinger.com",
    "SMTP_PORT": "465",
    "SMTP_ENCRYPTION": "ssl",
    "IMAP_HOST": "imap.hostinger.com",
    "IMAP_PORT": "993",
    "IMAP_FOLDER": "INBOX",
}


def simple_form_view(base_cfg, stored):
    email = stored.get("FROM_EMAIL") or stored.get("SMTP_USER") or ""
    dry = stored.get("DRY_RUN", base_cfg.get("DRY_RUN", True))
    if isinstance(dry, str):
        dry = dry.lower() in ("1", "true", "yes")
    return {
        "email": email,
        "from_name": stored.get("FROM_NAME", ""),
        "password": "********" if stored.get("SMTP_PASSWORD") else "",
        "test_email": stored.get("TEST_EMAIL") or email,
        "dry_run": dry,
    }


def build_settings_from_form(form, base_cfg, existing=None):
    """Map the simple connect form to full SMTP/IMAP settings."""
    existing = existing or {}
    email = (form.get("email") or "").strip().lower()
    from_name = (form.get("from_name") or "").strip()
    password = form.get("password") or ""
    test_email = (form.get("test_email") or "").strip() or email

    data = dict(HOSTINGER_DEFAULTS)
    data["FROM_NAME"] = from_name
    data["TEST_EMAIL"] = test_email
    data["DRY_RUN"] = "true" if form.get("dry_run") == "1" else "false"
    data["DAILY_SEND_LIMIT"] = str(
        existing.get("DAILY_SEND_LIMIT") or base_cfg.get("DAILY_SEND_LIMIT", 20)
    )

    if email:
        data["SMTP_USER"] = email
        data["FROM_EMAIL"] = email
        data["IMAP_USER"] = email

    if password and password != "********":
        data["SMTP_PASSWORD"] = password
        data["IMAP_PASSWORD"] = password

    return data


def get_user_settings(con, user_id):
    rows = con.execute(
        "SELECT key, value FROM user_settings WHERE user_id=?",
        (user_id,),
    ).fetchall()
    return {row["key"]: row["value"] for row in rows}


def save_user_settings(con, user_id, data):
    rows = []
    for key in SETTING_KEYS:
        if key not in data:
            continue
        value = data[key]
        if key.endswith("_PASSWORD") and value in ("", "********"):
            continue
        if value is None:
            continue
        rows.append((user_id, key, str(value)))

    if not rows:
        return get_user_settings(con, user_id)

    backend = getattr(con, "backend", "sqlite")
    if backend == "postgres" and hasattr(con, "executemany_upsert_settings"):
        con.executemany_upsert_settings(rows)
    else:
        for row in rows:
            con.execute(
                """INSERT INTO user_settings(user_id, key, value) VALUES(?,?,?)
                   ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value""",
                row,
            )
    con.commit()
    return get_user_settings(con, user_id)


def merge_user_config(base_cfg, con, user_id):
    merged = dict(base_cfg)
    stored = get_user_settings(con, user_id)
    for key, value in stored.items():
        if value == "":
            continue
        if key in INT_KEYS:
            try:
                merged[key] = int(value)
            except (TypeError, ValueError):
                continue
        elif key in BOOL_KEYS:
            merged[key] = str(value).lower() in ("1", "true", "yes")
        else:
            merged[key] = value
    return merged


def smtp_configured(cfg):
    return bool(cfg.get("SMTP_USER") and cfg.get("SMTP_PASSWORD") and cfg.get("FROM_EMAIL"))


def settings_form_defaults(base_cfg, stored):
    out = {}
    for key in SETTING_KEYS:
        out[key] = stored.get(key, base_cfg.get(key, ""))
        if key in INT_KEYS and out[key] != "":
            out[key] = int(out[key])
        if key in BOOL_KEYS:
            val = out[key]
            out[key] = str(val).lower() in ("1", "true", "yes") if val != "" else base_cfg.get(key, False)
    out["SMTP_PASSWORD"] = "********" if stored.get("SMTP_PASSWORD") else ""
    out["IMAP_PASSWORD"] = "********" if stored.get("IMAP_PASSWORD") else ""
    return out
