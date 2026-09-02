import pytest

from database.db import daily_sent_count
from services import campaign_service, email_service, lead_service, scheduler_service, template_service


def test_lead_creation_and_duplicate(db):
    cid = campaign_service.create_campaign(db, "Test")
    rows = [{"email": "a@test.com", "first_name": "Ann", "company": "Acme"}]
    r1 = lead_service.import_leads(db, cid, rows)
    r2 = lead_service.import_leads(db, cid, rows)
    assert r1["imported"] == 1
    assert r2["imported"] == 0
    assert r2["duplicates"] >= 1


def test_template_missing_variables(cfg):
    lead = {"first_name": "", "company": "", "custom_line": ""}
    out = template_service.render_template("Hi {{first_name}}, idea for {{company}}.", lead, cfg)
    assert "Hi there" in out
    assert "your company" in out
    assert "  ," not in out


def test_unsubscribe_url(cfg, db):
    db.execute(
        """INSERT INTO leads(first_name, email, unsubscribe_token, created_at)
           VALUES('Bob','bob@test.com','tok123','2026-01-01T00:00:00+00:00')"""
    )
    db.commit()
    lead = db.execute("SELECT * FROM leads WHERE email='bob@test.com'").fetchone()
    url = template_service.unsubscribe_url(cfg, lead)
    assert url == "https://example.com/unsubscribe/tok123"


def test_unsubscribe_reply_detection():
    assert email_service.is_unsubscribe_reply("unsubscribe")
    assert email_service.is_unsubscribe_reply("STOP EMAILING")
    assert not email_service.is_unsubscribe_reply("please stop by the office tomorrow")


def test_daily_limit(db, cfg):
    cid = campaign_service.create_campaign(db, "Limit Test")
    campaign_service.set_campaign_status(db, cid, "active")
    rows = [{"email": f"user{i}@test.com", "first_name": f"U{i}"} for i in range(5)]
    lead_service.import_leads(db, cid, rows)

    sent_total = 0
    for _ in range(3):
        result = scheduler_service.send_batch(db, cfg, limit=2, campaign_id=cid)
        sent_total += result["sent"]
    assert daily_sent_count(db, cid) == sent_total


def test_paused_campaign_not_sent(db, cfg):
    cid = campaign_service.create_campaign(db, "Paused")
    lead_service.import_leads(db, cid, [{"email": "x@test.com", "first_name": "X"}])
    result = scheduler_service.send_batch(db, cfg, campaign_id=cid)
    assert result["sent"] == 0


def test_active_campaign_sends(db, cfg):
    cid = campaign_service.create_campaign(db, "Active")
    campaign_service.set_campaign_status(db, cid, "active")
    lead_service.import_leads(db, cid, [{"email": "y@test.com", "first_name": "Y"}])
    result = scheduler_service.send_batch(db, cfg, campaign_id=cid)
    assert result["sent"] == 1


def test_suppression_blocks_send(db, cfg):
    cid = campaign_service.create_campaign(db, "Supp")
    campaign_service.set_campaign_status(db, cid, "active")
    lead_service.import_leads(db, cid, [{"email": "z@test.com", "first_name": "Z"}])
    db.execute(
        "INSERT INTO suppressions(email, reason, source, created_at) VALUES(?,?,?,?)",
        ("z@test.com", "test", "test", "2026-01-01T00:00:00+00:00"),
    )
    db.commit()
    result = scheduler_service.send_batch(db, cfg, campaign_id=cid)
    assert result["sent"] == 0


def test_health_endpoint():
    from app import create_app

    client = create_app().test_client()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_auth_pages_render(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    from app import create_app

    client = create_app().test_client()
    login = client.get("/login")
    assert login.status_code == 200
    assert b"Sign in" in login.data

    register = client.get("/register")
    assert register.status_code == 200
    assert b"Create" in register.data
