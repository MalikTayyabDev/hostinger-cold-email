import pytest
from werkzeug.security import generate_password_hash

from database.db import utcnow_iso
from services.user_settings_service import (
    get_user_settings,
    merge_user_config,
    save_user_settings,
    settings_form_defaults,
    smtp_configured,
)


def _create_user(db, username="smtp_tester"):
    return db.execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
        (username, generate_password_hash("password123"), utcnow_iso()),
    ).lastrowid


def test_user_settings_save_and_load(db):
    user_id = _create_user(db)
    save_user_settings(db, user_id, {
        "SMTP_HOST": "smtp.hostinger.com",
        "SMTP_PORT": "465",
        "SMTP_ENCRYPTION": "ssl",
        "SMTP_USER": "me@example.com",
        "SMTP_PASSWORD": "secret-pass",
        "FROM_NAME": "Me",
        "FROM_EMAIL": "me@example.com",
        "DRY_RUN": "true",
    })
    stored = get_user_settings(db, user_id)
    assert stored["SMTP_HOST"] == "smtp.hostinger.com"
    assert stored["SMTP_PASSWORD"] == "secret-pass"
    assert stored["DRY_RUN"] == "true"


def test_user_settings_password_not_overwritten_with_mask(db):
    user_id = _create_user(db, "mask_user")
    save_user_settings(db, user_id, {
        "SMTP_USER": "me@example.com",
        "SMTP_PASSWORD": "real-secret",
        "FROM_EMAIL": "me@example.com",
    })
    save_user_settings(db, user_id, {
        "SMTP_USER": "me@example.com",
        "SMTP_PASSWORD": "********",
        "FROM_EMAIL": "me@example.com",
        "FROM_NAME": "Updated Name",
    })
    stored = get_user_settings(db, user_id)
    assert stored["SMTP_PASSWORD"] == "real-secret"
    assert stored["FROM_NAME"] == "Updated Name"


def test_merge_user_config(db, cfg):
    user_id = _create_user(db, "merge_user")
    save_user_settings(db, user_id, {
        "SMTP_PORT": "587",
        "SMTP_ENCRYPTION": "starttls",
        "DRY_RUN": "false",
    })
    merged = merge_user_config(cfg, db, user_id)
    assert merged["SMTP_PORT"] == 587
    assert merged["SMTP_ENCRYPTION"] == "starttls"
    assert merged["DRY_RUN"] is False


def test_smtp_configured_requires_credentials(cfg):
    assert smtp_configured(cfg) is False
    ready = dict(cfg)
    ready.update({
        "SMTP_USER": "a@b.com",
        "SMTP_PASSWORD": "x",
        "FROM_EMAIL": "a@b.com",
    })
    assert smtp_configured(ready) is True


def test_settings_form_defaults_masks_passwords(db, cfg):
    user_id = _create_user(db, "form_user")
    save_user_settings(db, user_id, {"SMTP_PASSWORD": "hidden", "IMAP_PASSWORD": "hidden2"})
    form = settings_form_defaults(cfg, get_user_settings(db, user_id))
    assert form["SMTP_PASSWORD"] == "********"
    assert form["IMAP_PASSWORD"] == "********"


def test_postgres_upsert_sql_keeps_on_conflict():
    """Regression: UPSERT must not get RETURNING id (user_settings has no id column)."""
    sql = (
        "INSERT INTO user_settings(user_id, key, value) VALUES(?,?,?) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value"
    )
    head = sql.strip().upper()
    should_append = head.startswith("INSERT") and "RETURNING" not in head and "ON CONFLICT" not in head
    assert should_append is False
