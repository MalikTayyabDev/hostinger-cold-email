"""Smart personalized openers — no site audit required."""
import hashlib
import re
from urllib.parse import urlparse

LAUNCHNEST_URL = "https://launch-nest.com"

OPENER_ANGLES = {
    "auto": "Auto (pick best from lead data)",
    "budget": "Budget & value",
    "portfolio": "Show our work",
    "performance": "Speed & performance",
    "redesign": "Website refresh",
    "ecommerce": "Shopify / e-commerce",
    "wordpress": "WordPress & CMS",
    "local": "Local business",
    "general": "General intro",
}


def _company_label(lead):
    company = (lead.get("company") or "").strip()
    if company:
        return company
    email = (lead.get("email") or "").strip()
    if "@" in email:
        domain = email.split("@", 1)[1].split(".")[0]
        if domain not in ("gmail", "yahoo", "hotmail", "outlook", "icloud", "aol"):
            return domain.replace("-", " ").title()
    return "your business"


def _website_domain(lead):
    raw = (lead.get("website") or "").strip()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    try:
        host = urlparse(raw).netloc or urlparse(raw).path
        return host.lower().removeprefix("www.")
    except Exception:
        return ""


def _pick_variant(key, options):
    if not options:
        return ""
    digest = hashlib.md5(key.encode()).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


def _resolve_angle(lead):
    angle = (lead.get("opener_angle") or "auto").strip().lower()
    if angle and angle != "auto":
        return angle

    industry = (lead.get("industry") or "").lower()
    website = _website_domain(lead)
    tags = (lead.get("tags") or "").lower()

    if any(k in industry for k in ("shop", "retail", "ecommerce", "e-commerce")):
        return "ecommerce"
    if any(k in industry for k in ("restaurant", "dental", "clinic", "law", "real estate", "local")):
        return "local"
    if "wordpress" in industry or "wordpress" in tags:
        return "wordpress"
    if website:
        return "performance"
    return "budget"


def _templates_for_angle(angle, company, domain, industry, location):
    loc = location or "your area"
    ind = industry or "your industry"

    pools = {
        "budget": [
            f"Most businesses in {ind} overpay for web projects — at LaunchNest we deliver agency-quality builds at lean, market-friendly budgets (see {LAUNCHNEST_URL}).",
            f"We help teams like {company} launch modern websites without the usual five-figure agency price tag — full-stack, Shopify, and WordPress under one roof.",
            f"Agencies often quote {company} 2–3× what a project actually needs. We specialize in high-quality delivery at a fraction of typical market rates.",
        ],
        "portfolio": [
            f"I wanted to reach out because LaunchNest has been helping {ind} businesses ship faster, better websites — you can browse our work at {LAUNCHNEST_URL}.",
            f"We recently wrapped projects similar to what {company} might need — engineering-first builds, not bloated retainers. Happy to share relevant examples.",
            f"Our team at LaunchNest ({LAUNCHNEST_URL}) focuses on practical results: better UX, stronger conversion, and clean code — without enterprise-level pricing.",
        ],
        "performance": [
            f"Slow or outdated sites quietly cost {company} leads every week — we help businesses fix performance, mobile UX, and conversion without a full rebuild (unless you want one).",
            f"{f'I noticed {domain}' if domain else f'For {company}'} — speed and clarity on mobile often unlock the fastest ROI on a web project, and that is where we usually start.",
            f"Many {ind} sites look fine but load slow or bury the main call-to-action — we fix that at budgets that make sense for growing teams.",
        ],
        "redesign": [
            f"If {company} is planning a refresh this quarter, LaunchNest handles design, development, and launch end-to-end — usually for less than a traditional agency quote.",
            f"A lot of businesses outgrow their first website — we help teams like {company} modernize the look, messaging, and funnel without months of scope creep.",
            f"We are speaking with a few {ind} companies about Q3/Q4 site upgrades — flexible packages, clear timelines, lean pricing.",
        ],
        "ecommerce": [
            f"If {company} sells online (or wants to), we build and optimize Shopify stores that convert — plus integrations, speed work, and ongoing support at sensible rates.",
            f"E-commerce margins are tight — we help brands improve checkout flow, product pages, and site speed without the overhead of a large dev shop.",
            f"LaunchNest has shipped multiple Shopify projects for {ind}-type businesses — store setup, custom features, and CRO-focused tweaks.",
        ],
        "wordpress": [
            f"WordPress still powers most of the web — we help {company} get a secure, fast, easy-to-manage site without plugin bloat or surprise maintenance bills.",
            f"If {company} is on WordPress (or considering it), we handle custom themes, migrations, and performance — typically well below big-agency quotes.",
            f"We specialize in WordPress builds that marketing teams can actually update themselves — clean, fast, and budget-conscious.",
        ],
        "local": [
            f"Local businesses in {loc} often need a site that ranks, loads fast on phones, and makes booking or calling obvious — that is exactly what we build at LaunchNest.",
            f"We work with a lot of local {ind} teams — modern design, Google-friendly structure, and lead-focused pages without premium-agency pricing.",
            f"{company} probably gets judged on mobile in seconds — we help local businesses look credible and convert visitors into calls and form fills.",
        ],
        "general": [
            f"I came across {company} and thought LaunchNest might be a fit — we build full-stack, Shopify, and WordPress projects at budgets that work for growing businesses.",
            f"We are reaching out to a short list of {ind} companies — LaunchNest ({LAUNCHNEST_URL}) delivers engineering-first web work without the usual agency overhead.",
            f"Quick intro: we help businesses like {company} with websites, e-commerce, and automation — quality work, clear pricing, no fluff.",
        ],
    }
    return pools.get(angle, pools["general"])


def generate_smart_opener(lead):
    """Build a contextual opener from lead fields — no manual site audit needed."""
    company = _company_label(lead)
    domain = _website_domain(lead)
    industry = (lead.get("industry") or "").strip()
    location = (lead.get("location") or "").strip()
    angle = _resolve_angle(lead)

    key = f"{lead.get('email') or company}:{angle}"
    template = _pick_variant(
        key,
        _templates_for_angle(angle, company, domain, industry, location),
    )

    if domain and domain not in template and angle == "performance":
        template = template.replace("your site", domain, 1)

    return template


def resolve_custom_line(lead):
    """Use manual custom_line if set, otherwise smart opener."""
    manual = (lead.get("custom_line") or "").strip()
    if manual:
        return manual
    return generate_smart_opener(lead)


def list_angles_for_ui():
    return [{"id": k, "label": v} for k, v in OPENER_ANGLES.items()]
