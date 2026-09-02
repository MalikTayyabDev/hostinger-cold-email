import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _bool(name, default="false"):
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def load_config():
    return {
        "SMTP_HOST": os.getenv("SMTP_HOST", "smtp.hostinger.com"),
        "SMTP_PORT": int(os.getenv("SMTP_PORT", "465")),
        "SMTP_ENCRYPTION": os.getenv("SMTP_ENCRYPTION", "ssl"),
        "SMTP_USER": os.getenv("SMTP_USER", ""),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", ""),
        "FROM_NAME": os.getenv("FROM_NAME", ""),
        "FROM_EMAIL": os.getenv("FROM_EMAIL", ""),
        "REPLY_TO": os.getenv("REPLY_TO", ""),
        "IMAP_HOST": os.getenv("IMAP_HOST", "imap.hostinger.com"),
        "IMAP_PORT": int(os.getenv("IMAP_PORT", "993")),
        "IMAP_USER": os.getenv("IMAP_USER", ""),
        "IMAP_PASSWORD": os.getenv("IMAP_PASSWORD", ""),
        "IMAP_FOLDER": os.getenv("IMAP_FOLDER", "INBOX"),
        "DRY_RUN": _bool("DRY_RUN", "true"),
        "DAILY_SEND_LIMIT": int(os.getenv("DAILY_SEND_LIMIT", "20")),
        "SEND_DELAY_MIN_SECONDS": int(os.getenv("SEND_DELAY_MIN_SECONDS", "45")),
        "SEND_DELAY_MAX_SECONDS": int(os.getenv("SEND_DELAY_MAX_SECONDS", "120")),
        "MAX_FOLLOWUPS": int(os.getenv("MAX_FOLLOWUPS", "3")),
        "FOLLOWUP_1_DAYS": int(os.getenv("FOLLOWUP_1_DAYS", "3")),
        "FOLLOWUP_2_DAYS": int(os.getenv("FOLLOWUP_2_DAYS", "7")),
        "PUBLIC_BASE_URL": os.getenv("PUBLIC_BASE_URL", "").rstrip("/"),
        "CAMPAIGN_NAME": os.getenv("CAMPAIGN_NAME", "Website Outreach"),
        "DATABASE": os.getenv("DATABASE", "campaign.db"),
        "APP_HOST": os.getenv("APP_HOST", "127.0.0.1"),
        "APP_PORT": int(os.getenv("APP_PORT", "5000")),
        "SECRET_KEY": os.getenv("SECRET_KEY") or secrets.token_hex(32),
        "ADMIN_USERNAME": os.getenv("ADMIN_USERNAME", ""),
        "ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD", ""),
        "TEST_EMAIL": os.getenv("TEST_EMAIL", ""),
        "EMAIL_FOOTER": os.getenv(
            "EMAIL_FOOTER",
            "If you'd rather not receive messages from me, you can reply \"unsubscribe\".",
        ),
        # Supabase / Vercel production
        "DATABASE_URL": os.getenv("DATABASE_URL", ""),
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY", ""),
        "CRON_SECRET": os.getenv("CRON_SECRET", ""),
        "VERCEL": _bool("VERCEL", "false"),
    }


def auth_enabled(cfg):
    return bool(cfg.get("ADMIN_USERNAME") and cfg.get("ADMIN_PASSWORD"))
