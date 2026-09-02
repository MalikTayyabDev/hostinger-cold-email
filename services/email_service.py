import email
import imaplib
import random
import re
import smtplib
import ssl
import time
from email.message import EmailMessage
from email.utils import formataddr
from datetime import datetime, timezone

from logging_config import setup_logging

log = setup_logging()


class SMTPDeliveryError(Exception):
    def __init__(self, message, temporary=False, bounce=False):
        super().__init__(message)
        self.temporary = temporary
        self.bounce = bounce


BOUNCE_PATTERNS = [
    r"user unknown",
    r"mailbox not found",
    r"mailbox unavailable",
    r"recipient rejected",
    r"address rejected",
    r"does not exist",
    r"550 ",
    r"551 ",
    r"552 ",
    r"553 ",
]

UNSUBSCRIBE_PATTERNS = [
    r"^\s*unsubscribe\s*$",
    r"^\s*remove me\s*$",
    r"^\s*remove\s*$",
    r"^\s*stop emailing\s*$",
    r"^\s*stop\s*$",
    r"^\s*do not contact\s*$",
    r"^\s*don't contact\s*$",
    r"^\s*no more emails\s*$",
    r"^\s*please unsubscribe\s*$",
]


def _safe_smtp_error(exc):
    text = str(exc).lower()
    if "authentication" in text or "535" in text or "534" in text:
        return "SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD in .env."
    if "connect" in text or "timed out" in text or "gaierror" in text:
        return "Could not connect to the SMTP server. Check SMTP_HOST and SMTP_PORT."
    if any(code in text for code in ("550", "551", "552", "553")):
        return f"Recipient rejected by mail server: {exc.args[0] if exc.args else 'delivery failed'}"
    return f"SMTP error: {exc.args[0] if exc.args else type(exc).__name__}"


def is_bounce_error(exc):
    text = str(exc).lower()
    return any(re.search(p, text) for p in BOUNCE_PATTERNS)


def smtp_send(cfg, to_email, subject, text_body, unsubscribe_url=None):
    msg = EmailMessage()
    msg["From"] = formataddr((cfg["FROM_NAME"], cfg["FROM_EMAIL"]))
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = cfg.get("REPLY_TO") or cfg["FROM_EMAIL"]

    if unsubscribe_url:
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        if cfg.get("PUBLIC_BASE_URL"):
            msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    msg.set_content(text_body)

    if cfg["DRY_RUN"]:
        log.info("DRY RUN email to %s — subject: %s", to_email, subject)
        return

    context = ssl.create_default_context()
    port = int(cfg["SMTP_PORT"])
    encryption = (cfg.get("SMTP_ENCRYPTION") or "").lower()

    try:
        if encryption == "starttls" or port == 587:
            with smtplib.SMTP(cfg["SMTP_HOST"], port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(cfg["SMTP_HOST"], port, context=context, timeout=30) as server:
                server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        log.warning("SMTP authentication failed")
        raise SMTPDeliveryError(_safe_smtp_error(exc)) from exc
    except smtplib.SMTPRecipientsRefused as exc:
        bounce = is_bounce_error(exc)
        raise SMTPDeliveryError(_safe_smtp_error(exc), temporary=not bounce, bounce=bounce) from exc
    except smtplib.SMTPException as exc:
        bounce = is_bounce_error(exc)
        raise SMTPDeliveryError(
            _safe_smtp_error(exc), temporary=not bounce, bounce=bounce
        ) from exc
    except OSError as exc:
        raise SMTPDeliveryError(_safe_smtp_error(exc), temporary=True) from exc


def sleep_between(cfg, campaign=None):
    low = int(
        (campaign and campaign["delay_min_seconds"])
        or cfg["SEND_DELAY_MIN_SECONDS"]
    )
    high = int(
        (campaign and campaign["delay_max_seconds"])
        or cfg["SEND_DELAY_MAX_SECONDS"]
    )
    if high > 0:
        time.sleep(random.randint(low, max(low, high)))


def _own_addresses(cfg):
    own = set()
    for key in ("FROM_EMAIL", "SMTP_USER", "IMAP_USER", "REPLY_TO"):
        value = (cfg.get(key) or "").strip().lower()
        if value and "@" in value:
            own.add(value)
    return own


def _extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="ignore")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(errors="ignore") if payload else ""


def is_unsubscribe_reply(body):
    text = (body or "").strip().lower()
    if not text or len(text) > 200:
        return False
    for pattern in UNSUBSCRIBE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def scan_inbox(cfg, since_date):
    """Return list of dicts: sender, subject, message_id, body, is_unsubscribe."""
    results = []
    if cfg["DRY_RUN"]:
        return results

    own = _own_addresses(cfg)
    mail = imaplib.IMAP4_SSL(cfg["IMAP_HOST"], int(cfg["IMAP_PORT"]))
    try:
        mail.login(cfg["IMAP_USER"], cfg["IMAP_PASSWORD"])
        mail.select(cfg.get("IMAP_FOLDER", "INBOX"))
        typ, data = mail.search(None, "SINCE", since_date.strftime("%d-%b-%Y"))
        if typ != "OK":
            return results

        for num in data[0].split():
            typ, msg_data = mail.fetch(num, "(RFC822)")
            if typ != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            sender = email.utils.parseaddr(msg.get("From", ""))[1].lower().strip()
            if not sender or sender in own:
                continue
            body = _extract_body(msg)
            results.append({
                "sender": sender,
                "subject": msg.get("Subject", ""),
                "message_id": msg.get("Message-ID", ""),
                "body": body,
                "is_unsubscribe": is_unsubscribe_reply(body),
            })
    except imaplib.IMAP4.error as exc:
        log.warning("IMAP error: %s", type(exc).__name__)
    except OSError as exc:
        log.warning("IMAP connection error: %s", type(exc).__name__)
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return results
