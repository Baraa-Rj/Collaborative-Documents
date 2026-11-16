"""API tests for the core rules: access control, sharing, sanitization, and file import."""
from pathlib import Path

from conftest import ALICE, BOB, CAROL

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def share(client, doc_id, email, headers=ALICE):
    return client.post(f"/api/documents/{doc_id}/shares", json={"email": email}, headers=headers)


# ---- Access control -------------------------------------------------------------------------

def test_bob_gets_404_before_share_and_200_after(client, alice_doc):
    doc_id = alice_doc["id"]

    # Before sharing: Bob can't read, edit, or see it, and 404 (not 403) doesn't reveal it exists.
    assert client.get(f"/api/documents/{doc_id}", headers=BOB).status_code == 404
    assert client.patch(f"/api/documents/{doc_id}", json={"title": "hijack"}, headers=BOB).status_code == 404
    assert client.get("/api/documents", headers=BOB).json() == {"owned": [], "shared": []}

    assert share(client, doc_id, "bob@ajaia.test").status_code == 200

    # After sharing: Bob can read and edit, and it shows under "shared" (not "owned") with Alice as owner.
    res = client.get(f"/api/documents/{doc_id}", headers=BOB)
    assert res.status_code == 200
    assert res.json()["is_owner"] is False
    assert client.patch(f"/api/documents/{doc_id}", json={"content_html": "<p>Bob was here</p>"}, headers=BOB).status_code == 200
    listing = client.get("/api/documents", headers=BOB).json()
    assert listing["owned"] == []
    assert [(d["id"], d["owner"]["name"]) for d in listing["shared"]] == [(doc_id, "Alice")]

    # Bob's edit is persisted and visible to the owner (reopen).
    assert client.get(f"/api/documents/{doc_id}", headers=ALICE).json()["content_html"] == "<p>Bob was here</p>"

    # Sharing with Bob doesn't leak to Carol.
    assert client.get(f"/api/documents/{doc_id}", headers=CAROL).status_code == 404


def test_requests_without_a_known_user_are_rejected(client, alice_doc):
    assert client.get("/api/documents").status_code == 401
    assert client.get(f"/api/documents/{alice_doc['id']}", headers={"X-User-Id": "999"}).status_code == 401


# ---- Sharing rules --------------------------------------------------------------------------

def test_non_owner_cannot_share(client, alice_doc):
    doc_id = alice_doc["id"]
    share(client, doc_id, "bob@ajaia.test")

    res = share(client, doc_id, "carol@ajaia.test", headers=BOB)  # Bob has access but isn't the owner
    assert res.status_code == 403
    assert client.get(f"/api/documents/{doc_id}", headers=CAROL).status_code == 404

    # A user with no access at all gets 404, same as reading.
    assert share(client, doc_id, "bob@ajaia.test", headers=CAROL).status_code == 404


def test_share_validation_and_idempotency(client, alice_doc):
    doc_id = alice_doc["id"]
    assert share(client, doc_id, "nobody@ajaia.test").status_code == 400
    assert share(client, doc_id, "alice@ajaia.test").status_code == 400  # can't share with yourself

    first = share(client, doc_id, "  BOB@ajaia.test ")  # email is trimmed and case-insensitive
    second = share(client, doc_id, "bob@ajaia.test")
    assert first.status_code == second.status_code == 200
    assert [u["email"] for u in second.json()["shared_with"]] == ["bob@ajaia.test"]  # no duplicate


# ---- Sanitization (stored XSS) --------------------------------------------------------------

def test_script_and_event_handlers_are_stripped_on_save(client, alice_doc):
    doc_id = alice_doc["id"]
    dirty = (
        '<h1>Title</h1><p onclick="steal()">Hello <strong>world</strong>'
        '<script>alert("xss")</script><img src=x onerror="alert(1)">'
        '<a href="javascript:alert(1)">link</a></p>'
    )
    saved = client.patch(f"/api/documents/{doc_id}", json={"content_html": dirty}, headers=ALICE).json()["content_html"]

    for bad in ("<script", "alert(", "onclick", "onerror", "<img", "javascript:"):
        assert bad not in saved
    assert "<h1>Title</h1>" in saved and "<strong>world</strong>" in saved  # editor formatting survives

    # Create goes through the same sanitizer.
    created = client.post("/api/documents", json={"content_html": "<p>a<script>x()</script></p>"}, headers=ALICE).json()
    assert created["content_html"] == "<p>a</p>"


def test_title_validation(client, alice_doc):
    doc_id = alice_doc["id"]
    assert client.patch(f"/api/documents/{doc_id}", json={"title": "   "}, headers=ALICE).status_code == 422
    assert client.patch(f"/api/documents/{doc_id}", json={"title": "x" * 201}, headers=ALICE).status_code == 422
    res = client.patch(f"/api/documents/{doc_id}", json={"title": "  Renamed  "}, headers=ALICE)
    assert res.json()["title"] == "Renamed"


# ---- File import ----------------------------------------------------------------------------

def import_file(client, name, data, headers=ALICE):
    return client.post("/api/documents/import", files={"file": (name, data)}, headers=headers)


def test_markdown_import_creates_formatted_doc(client):
    res = import_file(client, "meeting-notes.md", (SAMPLES / "meeting-notes.md").read_bytes())
    assert res.status_code == 201
    doc = res.json()
    assert doc["title"] == "meeting-notes"
    assert doc["owner"]["name"] == "Alice" and doc["is_owner"] is True
    html = doc["content_html"]
    for tag in ("<h1>", "<h2>", "<strong>", "<em>", "<ul>", "<ol>", "<li>"):
        assert tag in html
    assert [d["id"] for d in client.get("/api/documents", headers=ALICE).json()["owned"]] == [doc["id"]]


def test_docx_import_keeps_headings_and_emphasis(client):
    res = import_file(client, "project-brief.docx", (SAMPLES / "project-brief.docx").read_bytes())
    assert res.status_code == 201
    html = res.json()["content_html"]
    assert "<h1>Project brief</h1>" in html and "<strong>" in html and "<em>" in html


def test_txt_import_escapes_html(client):
    html = import_file(client, "notes.txt", b"line one\nline two\n\n<script>alert(1)</script>\n").json()["content_html"]
    assert html == "<p>line one<br>line two</p><p>&lt;script&gt;alert(1)&lt;/script&gt;</p>"


def test_bad_file_types_are_rejected_with_400(client):
    cases = {
        ("report.pdf", b"%PDF-1.4"): "Unsupported file type",
        ("no_extension", b"hello"): "Unsupported file type",
        ("fake.docx", b"not a zip"): "not a valid .docx",
        ("binary.txt", b"abc\x00def"): "binary",
        ("latin1.md", "café".encode("latin-1")): "UTF-8",
        ("empty.txt", b"   "): "empty",
        ("huge.txt", b"a" * (2 * 1024 * 1024 + 1)): "2 MB",
    }
    for (name, data), message in cases.items():
        res = import_file(client, name, data)
        assert res.status_code == 400, name
        assert message in res.json()["detail"], name
    assert client.get("/api/documents", headers=ALICE).json()["owned"] == []  # nothing half-created
