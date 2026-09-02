from services import lead_service


def test_list_leads_count_with_user_filter(db):
    from routes.auth_helpers import register_user
    from services import campaign_service

    user_id, _ = register_user(db, "leadlistuser", "password123")
    cid = campaign_service.create_campaign(db, "L", user_id=user_id)
    lead_service.add_lead(db, cid, {"email": "x@test.com", "company": "Acme"})

    rows, total = lead_service.list_leads(db, user_id=user_id)
    assert total == 1
    assert len(rows) == 1


def test_opener_angle_in_tags_without_column(db):
    from services.lead_meta import encode_angle_in_tags, lead_has_opener_angle_column, opener_angle_from_row

    tags = encode_angle_in_tags("budget", "vip")
    row = {"tags": tags}
    assert opener_angle_from_row(row) == "budget"
    assert opener_angle_from_row({"tags": "angle:local"}) == "local"
