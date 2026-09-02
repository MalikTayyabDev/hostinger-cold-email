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


def get_user_settings(con, user_id):
    rows = con.execute(
        "SELECT key, value FROM user_settings WHERE user_id=?",
        (user_id,),
    ).fetchall()
    return {row["key"]: row["value"] for row in rows}


def save_user_settings(con, user_id, data):
    existing = get_user_settings(con, user_id)
    for key in SETTING_KEYS:
        if key not in data:
            continue
        value = data[key]
        if key.endswith("_PASSWORD") and value in ("", "********"):
            continue
        if value is None:
            continue
        con.execute(
            """INSERT INTO user_settings(user_id, key, value) VALUES(?,?,?)
               ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value""",
            (user_id, key, str(value)),
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
