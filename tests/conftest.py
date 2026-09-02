import os
import tempfile

import pytest

from config import load_config
from services import email_service


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(email_service, "sleep_between", lambda *a, **k: None)


@pytest.fixture
def db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    from database.db import connect
    con = connect(path)
    yield con
    con.close()
    os.unlink(path)


@pytest.fixture
def cfg():
    c = load_config()
    c["DRY_RUN"] = True
    c["FROM_NAME"] = "Test Sender"
    c["PUBLIC_BASE_URL"] = "https://example.com"
    c["DAILY_SEND_LIMIT"] = 20
    return c
