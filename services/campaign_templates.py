"""Ready-made campaign sequences for LaunchNest outreach."""

LAUNCHNEST_URL = "https://launch-nest.com"

# Each template: id, name, description, steps[(step_num, subject, body, delay_days)]
CAMPAIGN_TEMPLATES = {
    "launchnest_budget": {
        "name": "LaunchNest — Budget & Value",
        "description": "Lead with lean pricing vs agencies. Mentions LaunchNest and our services. Uses smart opener — no site audit needed.",
        "steps": [
            (
                1,
                "Better web work for {{company}} — without the agency price tag",
                f"""Hi {{{{first_name}}}},

{{{{smart_opener}}}}

At LaunchNest ({LAUNCHNEST_URL}) we help businesses with:
• Full-stack development & custom web apps
• Shopify & WordPress builds
• UI/UX, speed optimization, SEO & QA
• AI automation for repetitive workflows

Most clients come to us after quotes that felt 2–3× too high elsewhere. We keep scope tight, communicate clearly, and ship on lean budgets.

Would a 15-minute call this week make sense to see if we are a fit for {{{{company}}}}?

{{{{unsubscribe_footer}}}}""",
                0,
            ),
            (
                2,
                "Re: web project for {{company}}",
                """Hi {{first_name}},

Following up in case my note got buried.

Happy to send 2–3 examples of recent LaunchNest projects similar to what {{company}} might need — plus a rough budget range so you know what to expect before any sales call.

Worth a quick reply?

{{unsubscribe_footer}}""",
                3,
            ),
            (
                3,
                "Last note — {{company}}",
                """Hi {{first_name}},

Last follow-up from me.

If a website refresh, Shopify store, or performance fix is on the roadmap for {{company}}, I would love to share how we do it at LaunchNest without the usual agency overhead.

If timing is off, just say the word and I will close the loop.

{{unsubscribe_footer}}""",
                7,
            ),
            (
                4,
                "Closing the loop — {{company}}",
                """Hi {{first_name}},

I will assume this is not a priority right now — no problem at all.

If {{company}} ever needs engineering-first web work at a sensible budget, we are at launch-nest.com.

All the best,
{{sender_name}}

{{unsubscribe_footer}}""",
                14,
            ),
        ],
    },
    "launchnest_portfolio": {
        "name": "LaunchNest — Showcase Our Work",
        "description": "Lead with portfolio and proof. Great when you have case studies to share.",
        "steps": [
            (
                1,
                "LaunchNest — web work for {{company}}",
                f"""Hi {{{{first_name}}}},

{{{{smart_opener}}}}

LaunchNest ({LAUNCHNEST_URL}) is an engineering-first studio — we have shipped full-stack apps, Shopify stores, WordPress sites, and conversion-focused redesigns for teams that wanted quality without enterprise pricing.

I thought of {{company}} because we are actively taking on a few new projects this quarter.

Open to a quick look at relevant work we have done?

{{{{unsubscribe_footer}}}}""",
                0,
            ),
            (
                2,
                "Examples for {{company}}?",
                """Hi {{first_name}},

Wanted to bump this — I can send a short deck with before/after snapshots and typical timelines/budgets for projects like yours.

No audit needed on our side; we keep discovery lightweight.

{{unsubscribe_footer}}""",
                4,
            ),
            (
                3,
                "Still relevant for {{company}}?",
                """Hi {{first_name}},

If improving {{website}} or launching something new is on your list, LaunchNest can usually scope a first phase in under a week.

Let me know if you would like a ballpark — otherwise I will step back.

{{unsubscribe_footer}}""",
                8,
            ),
            (
                4,
                "Sign-off",
                """Hi {{first_name}},

Closing the loop — reach us anytime at launch-nest.com if {{company}} needs web, Shopify, or WordPress help down the road.

{{sender_name}}

{{unsubscribe_footer}}""",
                14,
            ),
        ],
    },
    "launchnest_ecommerce": {
        "name": "LaunchNest — Shopify & E-commerce",
        "description": "For online stores and retail brands. Shopify-focused pitch.",
        "steps": [
            (
                1,
                "Shopify / e-commerce help for {{company}}",
                f"""Hi {{{{first_name}}}},

{{{{smart_opener}}}}

We build and optimize Shopify stores at LaunchNest ({LAUNCHNEST_URL}) — theme work, custom features, speed, checkout flow, and integrations — at budgets that respect tight margins.

If {{company}} sells online (or wants to), I would be glad to share what a sensible first phase looks like.

{{{{unsubscribe_footer}}}}""",
                0,
            ),
            (
                2,
                "Re: {{company}} store",
                """Hi {{first_name}},

Quick follow-up — many stores we work with start with a focused sprint: fix mobile UX, tighten product pages, or speed up checkout.

Happy to outline options if useful.

{{unsubscribe_footer}}""",
                3,
            ),
            (
                3,
                "Last follow-up",
                """Hi {{first_name}},

Last note — if e-commerce is not a focus right now, totally understood.

LaunchNest is here when {{company}} is ready: launch-nest.com

{{unsubscribe_footer}}""",
                7,
            ),
            (
                4,
                "Final check-in",
                """Hi {{first_name}},

Signing off — feel free to reply anytime if a Shopify or web project comes up.

{{sender_name}}

{{unsubscribe_footer}}""",
                14,
            ),
        ],
    },
    "launchnest_local": {
        "name": "LaunchNest — Local Business",
        "description": "For clinics, agencies, trades, and local services. Mobile + leads focused.",
        "steps": [
            (
                1,
                "Quick idea for {{company}}'s website",
                f"""Hi {{{{first_name}}}},

{{{{smart_opener}}}}

Local businesses lose leads when sites are slow on phones or hide phone/booking buttons. LaunchNest ({LAUNCHNEST_URL}) builds clean, fast sites that turn visitors into calls and form fills — without big-agency fees.

Would you be open to a 10-minute chat about {{company}}?

{{{{unsubscribe_footer}}}}""",
                0,
            ),
            (
                2,
                "Re: {{company}}",
                """Hi {{first_name}},

Bumping this once — we often start local clients with a single high-impact page or mobile speed fix before any full redesign.

Let me know if that would be useful.

{{unsubscribe_footer}}""",
                3,
            ),
            (
                3,
                "Last message",
                """Hi {{first_name}},

I will assume website work is not urgent — no worries.

If {{company}} needs help later, we are at launch-nest.com.

{{unsubscribe_footer}}""",
                7,
            ),
            (
                4,
                "Goodbye note",
                """Hi {{first_name}},

All the best with {{company}} — reply anytime if we can help.

{{sender_name}}

{{unsubscribe_footer}}""",
                14,
            ),
        ],
    },
}


def list_templates():
    return [
        {
            "id": key,
            "name": val["name"],
            "description": val["description"],
            "step_count": len(val["steps"]),
        }
        for key, val in CAMPAIGN_TEMPLATES.items()
    ]


def get_template(template_id):
    return CAMPAIGN_TEMPLATES.get(template_id)


def get_steps(template_id):
    tpl = get_template(template_id)
    if not tpl:
        return None
    return tpl["steps"]
