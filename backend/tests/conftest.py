"""Test setup: point the app at a throwaway SQLite file BEFORE app modules are imported
(app/db.py reads DATABASE_URL at import time), and give every test a fresh, re-seeded database."""
import os
import tempfile

_tmpdir = tempfile.mkdtemp(prefix="ajaia-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

# Seed order is fixed, so ids are stable: Alice=1, Bob=2, Carol=3.
ALICE = {"X-User-Id": "1"}
BOB = {"X-User-Id": "2"}
CAROL = {"X-User-Id": "3"}


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)  # clean slate; the app's startup recreates tables and seeds users
    with TestClient(app) as c:
        yield c


@pytest.fixture
def alice_doc(client):
    """A document owned by Alice, returned as the API's JSON."""
    res = client.post("/api/documents", json={"title": "Alice's plan", "content_html": "<p>secret plan</p>"}, headers=ALICE)
    assert res.status_code == 201
    return res.json()
