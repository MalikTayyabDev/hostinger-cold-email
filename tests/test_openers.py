from services import campaign_templates, opener_service, template_service


def test_smart_opener_budget():
    lead = {"email": "j@acme.com", "company": "Acme Corp", "opener_angle": "budget"}
    text = opener_service.generate_smart_opener(lead)
    assert "Acme" in text or "LaunchNest" in text
    assert "launch-nest.com" in text or "budget" in text.lower() or "agency" in text.lower()


def test_smart_opener_auto_ecommerce():
    lead = {"email": "s@shop.com", "company": "Shop Co", "industry": "E-commerce"}
    text = opener_service.generate_smart_opener(lead)
    assert "Shopify" in text or "online" in text.lower() or "e-commerce" in text.lower()


def test_custom_line_override(cfg):
    lead = {"first_name": "Ann", "company": "Acme", "custom_line": "My manual opener."}
    out = template_service.render_template("Hi {{first_name}},\n\n{{custom_line}}", lead, cfg)
    assert "My manual opener." in out


def test_smart_opener_in_template(cfg):
    lead = {"first_name": "Bob", "company": "Beta Inc", "industry": "SaaS", "opener_angle": "budget"}
    out = template_service.render_template("Hi {{first_name}},\n\n{{smart_opener}}", lead, cfg)
    assert "Hi Bob" in out
    assert len(out) > 50


def test_launchnest_campaign_templates():
    templates = campaign_templates.list_templates()
    assert len(templates) >= 4
    steps = campaign_templates.get_steps("launchnest_budget")
    assert steps is not None
    assert "launch-nest.com" in steps[0][2] or "LaunchNest" in steps[0][2]
    assert "{{smart_opener}}" in steps[0][2]


def test_apply_template(db):
    from services import campaign_service

    cid = campaign_service.create_campaign(db, "Tpl Test", template_key="launchnest_local")
    steps = campaign_service.get_steps(db, cid)
    assert any("LaunchNest" in s["body"] or "launch-nest" in s["body"] for s in steps)

    ok = campaign_service.apply_template(db, cid, "launchnest_ecommerce")
    assert ok is True
    steps = campaign_service.get_steps(db, cid)
    assert "Shopify" in steps[0]["body"] or "e-commerce" in steps[0]["body"].lower()
