#!/usr/bin/env python3
"""Management CLI for cold email system."""
import csv
import sys

from config import load_config
from database.db import connect
from services import campaign_service, email_service, lead_service, scheduler_service
from services import template_service


def cmd_test_email():
    cfg = load_config()
    con = connect(cfg["DATABASE"])
    test_to = cfg.get("TEST_EMAIL") or cfg.get("FROM_EMAIL")
    if not test_to:
        print("Set TEST_EMAIL or FROM_EMAIL in .env")
        return 1
    try:
        email_service.smtp_send(cfg, test_to, "Test Email", "This is a test from manage.py.")
        print(f"Test email sent to {test_to}")
    except email_service.SMTPDeliveryError as exc:
        print(f"Failed: {exc}")
        return 1
    return 0


def cmd_import(path):
    cfg = load_config()
    con = connect(cfg["DATABASE"])
    campaigns = campaign_service.list_campaigns(con)
    if not campaigns:
        print("Create a campaign first.")
        return 1
    cid = campaigns[0]["id"]
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    result = lead_service.import_leads(con, cid, rows)
    print(f"Imported {result['imported']} leads to campaign {cid}")
    return 0


def cmd_stats():
    cfg = load_config()
    con = connect(cfg["DATABASE"])
    stats = scheduler_service.dashboard_stats(con)
    print("Dashboard stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py <test-email|import|stats> [args]")
        return 1
    cmd = sys.argv[1]
    if cmd == "test-email":
        return cmd_test_email()
    if cmd == "import" and len(sys.argv) >= 3:
        return cmd_import(sys.argv[2])
    if cmd == "stats":
        return cmd_stats()
    print("Unknown command.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
