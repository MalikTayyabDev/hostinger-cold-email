import os
import secrets

from dotenv import load_dotenv

load_dotenv()

BUILD_ID = "2026-09-02p"


def _env(name, default=""):
    val = os.getenv(name)
    if val is None or str(val).strip() == "":
        return default
    return val


def _bool(name, default="false"):
    return _env(name, default).lower() in ("1", "true", "yes")


def _int(name, default):
    raw = _env(name, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return int(default)


def load_config():
    return {
        "SMTP_HOST": _env("SMTP_HOST", "smtp.hostinger.com"),
        "SMTP_PORT": _int("SMTP_PORT", 465),
        "SMTP_ENCRYPTION": _env("SMTP_ENCRYPTION", "ssl"),
        "SMTP_USER": _env("SMTP_USER", ""),
        "SMTP_PASSWORD": _env("SMTP_PASSWORD", ""),
        "FROM_NAME": _env("FROM_NAME", ""),
        "FROM_EMAIL": _env("FROM_EMAIL", ""),
        "REPLY_TO": _env("REPLY_TO", ""),
        "IMAP_HOST": _env("IMAP_HOST", "imap.hostinger.com"),
        "IMAP_PORT": _int("IMAP_PORT", 993),
        "IMAP_USER": _env("IMAP_USER", ""),
        "IMAP_PASSWORD": _env("IMAP_PASSWORD", ""),
        "IMAP_FOLDER": _env("IMAP_FOLDER", "INBOX"),
        "DRY_RUN": _bool("DRY_RUN", "true"),
        "DAILY_SEND_LIMIT": _int("DAILY_SEND_LIMIT", 20),
        "SEND_DELAY_MIN_SECONDS": _int("SEND_DELAY_MIN_SECONDS", 45),
        "SEND_DELAY_MAX_SECONDS": _int("SEND_DELAY_MAX_SECONDS", 120),
        "MAX_FOLLOWUPS": _int("MAX_FOLLOWUPS", 3),
        "FOLLOWUP_1_DAYS": _int("FOLLOWUP_1_DAYS", 3),
        "FOLLOWUP_2_DAYS": _int("FOLLOWUP_2_DAYS", 7),
        "PUBLIC_BASE_URL": _env("PUBLIC_BASE_URL", "").rstrip("/"),
        "CAMPAIGN_NAME": _env("CAMPAIGN_NAME", "Website Outreach"),
        "DATABASE": _env("DATABASE", "campaign.db"),
        "APP_HOST": _env("APP_HOST", "127.0.0.1"),
        "APP_PORT": _int("APP_PORT", 5000),
        "SECRET_KEY": _env("SECRET_KEY") or secrets.token_hex(32),
        "ADMIN_USERNAME": _env("ADMIN_USERNAME", ""),
        "ADMIN_PASSWORD": _env("ADMIN_PASSWORD", ""),
        "ALLOW_SIGNUP": _bool("ALLOW_SIGNUP", "true"),
        "AUTH_DISABLED": _bool("AUTH_DISABLED", "false"),
        "TEST_EMAIL": _env("TEST_EMAIL", ""),
        "EMAIL_FOOTER": _env(
            "EMAIL_FOOTER",
            "If you'd rather not receive messages from me, you can reply \"unsubscribe\".",
        ),
        "DATABASE_URL": _env("DATABASE_URL", ""),
        "SUPABASE_URL": _env("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_KEY": _env("SUPABASE_SERVICE_KEY", ""),
        "CRON_SECRET": _env("CRON_SECRET", ""),
        "VERCEL": _bool("VERCEL", "false"),
    }


def auth_enabled(cfg):
    if cfg.get("AUTH_DISABLED"):
        return False
    return True
