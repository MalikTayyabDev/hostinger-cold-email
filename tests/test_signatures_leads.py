from services import signature_service
from services.lead_service import add_lead, add_leads_bulk


def test_sample_csv_has_required_columns():
    assert "email" in signature_service.SAMPLE_CSV
    assert "name" in signature_service.SAMPLE_CSV


def test_signature_render():
    html = signature_service.render_html(signature_service.DEFAULT_SIGNATURE)
    assert "Sarah" in html
    assert "LaunchNest" in html
    assert "Engineering-First" in html


def test_compose_email_with_signature():
    text, html = signature_service.compose_email_bodies("Hello there", signature_service.DEFAULT_SIGNATURE)
    assert "Hello there" in text
    assert "Sarah" in text
    assert html is not None
    assert "Sarah" in html


def test_add_lead_manual(db):
    from services import campaign_service

    cid = campaign_service.create_campaign(db, "Manual")
    result = add_lead(db, cid, {"email": "manual@test.com", "first_name": "Ann", "company": "Acme"})
    assert result["status"] == "added"

    dup = add_lead(db, cid, {"email": "manual@test.com"})
    assert dup["status"] == "duplicate"


def test_add_leads_bulk(db):
    from services import campaign_service

    cid = campaign_service.create_campaign(db, "Bulk")
    result = add_leads_bulk(db, cid, "a@test.com, Alice\nb@test.com\nbad-email")
    assert result["added"] == 2
    assert result["invalid"] == 1
