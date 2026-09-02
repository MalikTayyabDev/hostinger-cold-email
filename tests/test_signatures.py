from services import lead_service, signature_service


def test_sample_csv_has_required_columns():
    header = signature_service.SAMPLE_CSV.splitlines()[0]
    assert "email" in header
    assert "company" in header


def test_signature_render():
    html = signature_service.render_html(signature_service.DEFAULT_SIGNATURE)
    assert "Sarah" in html
    assert "LaunchNest" in html
    assert "Engineering-First" in html

    text = signature_service.render_text(signature_service.DEFAULT_SIGNATURE)
    assert "Sarah" in text
    assert "BUILD" in text


def test_compose_email_with_signature():
    text, html = signature_service.compose_email_bodies("Hello there,\n\nQuick idea.", signature_service.DEFAULT_SIGNATURE)
    assert "Hello there" in text
    assert "Sarah" in text
    assert html is not None
    assert "Sarah" in html


def test_add_lead_manual(db):
    from services import campaign_service

    cid = campaign_service.create_campaign(db, "Manual")
    result = lead_service.add_lead(db, cid, {
        "email": "manual@test.com",
        "first_name": "Ann",
        "company": "Acme",
    })
    assert result["status"] == "added"

    dup = lead_service.add_lead(db, cid, {"email": "manual@test.com"})
    assert dup["status"] == "duplicate"


def test_add_leads_bulk(db):
    from services import campaign_service

    cid = campaign_service.create_campaign(db, "Bulk")
    result = lead_service.add_leads_bulk(
        db,
        cid,
        "a@test.com, Alice\nb@test.com\nbad-email\nc@test.com",
    )
    assert result["added"] == 3
    assert result["invalid"] == 1


def test_create_signature(db):
    from routes.auth_helpers import register_user

    user_id, _ = register_user(db, "siguser", "password123")
    sig_id = signature_service.create_signature(db, user_id, dict(signature_service.DEFAULT_SIGNATURE))
    sig = signature_service.get_signature(db, sig_id, user_id)
    assert sig["display_name"] == "Sarah"

    sig_id2 = signature_service.create_signature(db, user_id, {
        **signature_service.DEFAULT_SIGNATURE,
        "name": "Alt",
        "display_name": "Mike",
    })
    rows = signature_service.list_signatures(db, user_id)
    assert len(rows) == 2

    signature_service.delete_signature(db, sig_id2, user_id)
    assert len(signature_service.list_signatures(db, user_id)) == 1
