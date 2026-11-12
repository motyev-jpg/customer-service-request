import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import airtable  # noqa: E402
from app import create_app  # noqa: E402

TOKEN = "patABCDEFGHIJKLMNOP.0123456789abcdef"
WORKSPACE = "wspABCDEFGHIJKLMN"
BASE = "appABCDEFGHIJKLMN"


class FakeClient:
    """Stands in for AirtableClient: no network."""

    def __init__(self):
        self.records = []
        self.created = []
        self.formulas = []
        self.fail_add_field = False
        self.fail_list = False

    def create_base(self, workspace_id, name, tables):
        self.workspace = workspace_id
        self.tables = tables
        return {"id": BASE, "tables": [{"id": "tblXXXXXXXXXXXXXX", "name": "Requests"}]}

    def add_field(self, base_id, table_id, field):
        if self.fail_add_field:
            raise airtable.AirtableError(422, "INVALID_REQUEST")
        self.added = field

    def list_records(self, base_id, formula, **_):
        if self.fail_list:
            raise airtable.AirtableError(500, "SERVER")
        self.formulas.append(formula)
        return self.records

    def create_records(self, base_id, fields_list):
        self.created_many = fields_list
        return [{"id": f"rec{i}", "fields": f} for i, f in enumerate(fields_list)]

    def create_record(self, base_id, fields):
        self.created.append(fields)
        return {"id": "recX", "fields": {"RequestID": 42, **fields}}


@pytest.fixture()
def fake():
    return FakeClient()


@pytest.fixture()
def client(tmp_path, fake):
    app = create_app(str(tmp_path / "test.db"), airtable_client_factory=lambda token: fake)
    app.config["TESTING"] = True
    return app.test_client()


def token_of(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def login(client, phone):
    return client.post("/login", data={"phone": phone, "csrf": token_of(client)})


def connect(client, token=TOKEN, workspace=WORKSPACE):
    login(client, "543210")
    return client.post("/admin/airtable/connect", follow_redirects=True, data={
        "csrf": token_of(client, "/admin/airtable"), "token": token, "workspace_id": workspace})


def record(rid, status="In progress", phone="0501112222"):
    return {"id": f"rec{rid}", "createdTime": "2026-11-01T10:00:00.000Z", "fields": {
        "RequestID": rid, "Phone": phone, "Category": "Billing",
        "Subcategory": "Payment issue", "Description": "from airtable", "Status": status,
        "Updated": "2026-11-03T08:30:00.000Z"}}


def test_admin_number_opens_token_screen(client):
    r = login(client, "543210")
    assert r.status_code == 302 and r.headers["Location"].endswith("/admin/airtable")
    html = client.get("/admin/airtable").get_data(as_text=True)
    assert 'name="token"' in html and 'type="password"' in html


def test_customer_cannot_open_admin_screen(client):
    login(client, "0500000001")
    assert client.get("/admin/airtable").status_code == 302
    assert client.get("/admin/airtable").headers["Location"].endswith("/login")


def test_anonymous_cannot_connect(client):
    r = client.post("/admin/airtable/connect", data={
        "csrf": token_of(client), "token": TOKEN, "workspace_id": WORKSPACE})
    assert r.status_code == 302 and "/login" in r.headers["Location"]


@pytest.mark.parametrize("token,workspace", [("short", WORKSPACE), (TOKEN, "bad")])
def test_invalid_input_rejected(client, token, workspace):
    html = connect(client, token, workspace).get_data(as_text=True)
    assert 'class="error"' in html and 'name="token"' in html


def test_connect_creates_base_and_hides_token(client, fake, tmp_path):
    html = connect(client).get_data(as_text=True)
    assert BASE in html and TOKEN not in html and "pat…cdef" in html
    assert fake.workspace == WORKSPACE
    assert fake.tables[0]["name"] == "Requests"
    assert [f["name"] for f in fake.tables[0]["fields"]][:2] == ["RequestID", "Phone"]
    assert fake.added["name"] == "Updated"
    assert TOKEN in (tmp_path / "settings.json").read_text(encoding="utf-8")


def test_updated_field_failure_is_reported(client, fake):
    fake.fail_add_field = True
    html = connect(client).get_data(as_text=True)
    assert BASE in html and "Updated column could not be created" in html


def test_airtable_rejection_shown_without_token(client, fake):
    def boom(*_a, **_k):
        raise airtable.AirtableError(403, "INVALID_PERMISSIONS")
    fake.create_base = boom
    html = connect(client).get_data(as_text=True)
    assert "403 INVALID_PERMISSIONS" in html and TOKEN not in html


def test_dashboard_reads_status_from_airtable(client, fake):
    connect(client)
    client.post("/logout", data={"csrf": token_of(client, "/admin/airtable")})
    fake.records = [record(7, "In progress")]
    login(client, "0501112222")
    html = client.get("/dashboard").get_data(as_text=True)
    assert "SR-0007" in html and "In progress" in html and "from" not in html.split("<tbody>")[0]
    assert fake.formulas[-1] == "{Phone}='0501112222'"
    # a status changed by staff shows up on the next load
    fake.records = [record(7, "Resolved")]
    assert "Resolved" in client.get("/dashboard").get_data(as_text=True)
    # Hebrew names come from config
    client.get("/lang/he")
    assert "נפתרה" in client.get("/dashboard").get_data(as_text=True)


def test_new_request_written_to_airtable(client, fake):
    connect(client)
    client.post("/logout", data={"csrf": token_of(client, "/admin/airtable")})
    login(client, "0501112222")
    client.post("/requests/new", data={
        "csrf": token_of(client, "/requests/new"), "category": "billing",
        "subcategory": "payment_issue", "description": "hello"})
    assert fake.created == [{
        "Phone": "0501112222", "Category": "Billing", "Subcategory": "Payment issue",
        "Description": "hello", "Status": "Open"}]


def test_detail_without_history_and_owner_filter(client, fake):
    connect(client)
    client.post("/logout", data={"csrf": token_of(client, "/admin/airtable")})
    fake.records = [record(7)]
    login(client, "0501112222")
    html = client.get("/requests/7").get_data(as_text=True)
    assert "SR-0007" in html and "Status history" not in html
    assert fake.formulas[-1] == "AND({Phone}='0501112222',{RequestID}=7)"
    fake.records = []
    assert client.get("/requests/8").status_code == 404


def test_airtable_outage_shows_generic_message(client, fake):
    connect(client)
    client.post("/logout", data={"csrf": token_of(client, "/admin/airtable")})
    login(client, "0501112222")
    fake.fail_list = True
    r = client.get("/dashboard")
    html = r.get_data(as_text=True)
    assert r.status_code == 502 and "temporarily unavailable" in html and TOKEN not in html


def post_admin(client, path):
    return client.post(path, follow_redirects=True,
                       data={"csrf": token_of(client, "/admin/airtable")})


def test_load_demo_data_into_airtable(client, fake):
    connect(client)
    html = post_admin(client, "/admin/airtable/load-demo").get_data(as_text=True)
    assert "Demo data was added" in html
    sent = fake.created_many
    assert len(sent) == 13
    assert {r["Phone"] for r in sent} == {"0500000001", "0500000002", "0500000003"}
    assert all(set(r) == {"Phone", "Category", "Subcategory", "Description", "Status"}
               for r in sent)
    first = sent[0]  # the oldest demo request, in its current status
    assert (first["Category"], first["Subcategory"], first["Status"]) == (
        "Account", "Access problem", "Closed")
    assert "OR({Phone}='0500000001'" in fake.formulas[-1]


def test_load_demo_is_not_repeated(client, fake):
    connect(client)
    fake.records = [record(1)]  # demo data already in the table
    html = post_admin(client, "/admin/airtable/load-demo").get_data(as_text=True)
    assert "already in the table" in html and not hasattr(fake, "created_many")


def test_load_demo_needs_admin(client, fake):
    login(client, "0500000001")
    r = client.post("/admin/airtable/load-demo", data={"csrf": token_of(client)})
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert not hasattr(fake, "created_many")


def test_create_records_batches_of_ten(monkeypatch):
    bodies = []
    c = airtable.AirtableClient(TOKEN)
    monkeypatch.setattr(c, "_request", lambda method, url, body=None: (
        bodies.append(body), {"records": body["records"]})[1])
    assert len(c.create_records(BASE, [{"Phone": str(i)} for i in range(13)])) == 13
    assert [len(b["records"]) for b in bodies] == [10, 3]


def test_disconnect_returns_to_local_database(client):
    connect(client)
    client.post("/admin/airtable/disconnect", data={"csrf": token_of(client, "/admin/airtable")})
    client.post("/logout", data={"csrf": token_of(client, "/admin/airtable")})
    login(client, "0500000001")
    assert "SR-0001" in client.get("/dashboard").get_data(as_text=True)


def test_ssl_context_still_verifies_certificates_and_host():
    import ssl
    ctx = airtable.ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    assert not ctx.verify_flags & ssl.VERIFY_X509_STRICT


def test_client_passes_ssl_context_to_urlopen(monkeypatch):
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b'{"records": []}'

    def fake_urlopen(req, timeout=None, context=None):
        seen["context"] = context
        return Resp()

    monkeypatch.setattr(airtable.urllib.request, "urlopen", fake_urlopen)
    assert airtable.AirtableClient(TOKEN).list_records(BASE, "1") == []
    assert seen["context"] is not None


def test_formula_string_is_escaped():
    assert airtable.formula_str("a'b\\c") == "'a\\'b\\\\c'"
    assert airtable.formula_str("x\ny") == "'xy'"
