import time

from app import create_app
from logging_config import setup_logging
from services import scheduler_service

log = setup_logging("scheduler")
app = create_app()
con = app.config["DB"]
cfg = app.config["CFG"]

log.info("Scheduler started (DRY_RUN=%s)", cfg["DRY_RUN"])
print("Cold email scheduler started. Press Ctrl+C to stop.")

while True:
    try:
        with app.app_context():
            inbox = scheduler_service.process_inbox(con, cfg)
            if inbox["replies"]:
                print(f"Replies detected: {inbox['replies']}")
            if inbox["unsubscribes"]:
                print(f"Unsubscribes detected: {inbox['unsubscribes']}")

            result = scheduler_service.send_batch(con, cfg)
            if result["sent"]:
                print(f"Sent {result['sent']} message(s).")
            else:
                print("Nothing eligible to send.")

        time.sleep(900)
    except KeyboardInterrupt:
        log.info("Scheduler stopped")
        print("Stopped.")
        break
    except Exception as exc:
        log.exception("Scheduler error: %s", exc)
        print("Scheduler error:", repr(exc))
        time.sleep(300)
