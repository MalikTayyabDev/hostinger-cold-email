from services import campaign_service, scheduler_service


def test_diagnose_send_no_leads(db, cfg):
    uid = 1
    db.execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES('u','h','2026-01-01')"
    )
    db.commit()
    cid = campaign_service.create_campaign(db, "Empty", user_id=uid)
    campaign_service.set_campaign_status(db, cid, "active")
    msg = scheduler_service.diagnose_send(db, cid, uid, cfg)
    assert "No leads" in msg


def test_diagnose_send_not_active(db, cfg):
    uid = 1
    db.execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES('u2','h','2026-01-01')"
    )
    db.commit()
    cid = campaign_service.create_campaign(db, "Draft", user_id=uid)
    msg = scheduler_service.diagnose_send(db, cid, uid, cfg)
    assert "not active" in msg.lower()
