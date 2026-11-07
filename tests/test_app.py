import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def token(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def login(client, phone="0500000001"):
    return client.post("/login", data={"phone": phone, "csrf": token(client)},
                       follow_redirects=True)


def test_login_page_shows_demo_phones_and_header(client):
    html = client.get("/login").get_data(as_text=True)
    assert "0500000001" in html and "0500000004" in html
    assert "logo.svg" in html and "English" in html and "עברית" in html


def test_redirects_to_login_when_anonymous(client):
    assert client.get("/dashboard").status_code == 302


def test_invalid_phone_rejected(client):
    r = login(client, "abc")
    assert "valid phone" in r.get_data(as_text=True)


def test_post_without_csrf_rejected(client):
    assert client.post("/login", data={"phone": "0500000001"}).status_code == 400


def test_dashboard_shows_only_own_requests(client):
    html = login(client, "0500000001").get_data(as_text=True)
    assert "SR-0001" in html
    assert "refund" not in html.lower()  # belongs to 0500000002


def test_empty_history_for_new_number(client):
    html = login(client, "0500000004").get_data(as_text=True)
    assert "No service requests found." in html


def test_dashboard_has_no_filters_or_statistics(client):
    html = login(client).get_data(as_text=True)
    assert 'class="filters' not in html and 'class="counters' not in html


def test_create_request(client):
    login(client, "0500000004")
    r = client.post("/requests/new", follow_redirects=True, data={
        "csrf": token(client, "/requests/new"), "category": "billing",
        "subcategory": "payment_issue", "description": "test"})
    html = r.get_data(as_text=True)
    assert "Your request was created." in html and "Open" in html


def test_invalid_subcategory_rejected(client):
    login(client, "0500000004")
    r = client.post("/requests/new", data={
        "csrf": token(client, "/requests/new"), "category": "billing",
        "subcategory": "complaint", "description": ""})
    assert "valid category" in r.get_data(as_text=True)


def test_cannot_view_other_users_request(client):
    login(client, "0500000001")
    assert client.get("/requests/5").status_code == 404  # belongs to 0500000002
    assert client.get("/requests/1").status_code == 200


def test_language_switch_to_hebrew(client):
    login(client)
    client.get("/lang/he")
    html = client.get("/dashboard").get_data(as_text=True)
    assert 'dir="rtl"' in html and "הבקשות שלי" in html and "בטיפול" in html
