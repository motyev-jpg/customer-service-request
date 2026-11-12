"""Minimal Airtable REST client (standard library only) and the table schema we create."""
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.airtable.com/v0"
TABLE = "Requests"
BASE_NAME = "Service Requests"
BASE_ID_RE = re.compile(r"^app[A-Za-z0-9]{10,20}$")
WORKSPACE_ID_RE = re.compile(r"^wsp[A-Za-z0-9]{10,20}$")
TOKEN_RE = re.compile(r"^[A-Za-z0-9._\-]{20,300}$")


class AirtableError(Exception):
    """An Airtable call failed. Carries the HTTP status and Airtable's error type only
    (never the token or the request payload)."""

    def __init__(self, status, kind=""):
        super().__init__(f"Airtable error {status} {kind}".strip())
        self.status = status
        self.kind = kind


def formula_str(value):
    """Quote a value as a string literal inside an Airtable formula."""
    text = "".join(ch for ch in str(value) if ch >= " ")
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _error_kind(err):
    try:
        body = json.loads(err.read().decode("utf-8"))
        kind = body.get("error")
        kind = kind.get("type") if isinstance(kind, dict) else kind
    except (ValueError, OSError, AttributeError):
        kind = ""
    return re.sub(r"[^A-Za-z0-9_ ]", "", str(kind or ""))[:60]


def ssl_context():
    """Verified TLS context. Only Python's strict X.509 profile is relaxed: networks or
    antivirus that inspect HTTPS often present a root certificate without an Authority Key
    Identifier, which Python 3.13+ rejects. Certificate chain and host name stay verified."""
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx


class AirtableClient:
    def __init__(self, token, timeout=15):
        self._token = token
        self._timeout = timeout
        self._ssl = ssl_context()

    def _request(self, method, url, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self._timeout,
                                            context=self._ssl) as resp:
                    return json.loads(resp.read().decode("utf-8") or "{}")
            except urllib.error.HTTPError as err:
                if err.code == 429 and attempt < 2:  # rate limit: 5 requests/second/base
                    time.sleep(1 + attempt)
                    continue
                raise AirtableError(err.code, _error_kind(err)) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                raise AirtableError(0, "NETWORK") from None

    # ---- schema ------------------------------------------------------------
    def create_base(self, workspace_id, name, tables):
        return self._request("POST", f"{API}/meta/bases",
                             {"name": name, "workspaceId": workspace_id, "tables": tables})

    def add_field(self, base_id, table_id, field):
        return self._request(
            "POST", f"{API}/meta/bases/{base_id}/tables/{table_id}/fields", field)

    # ---- records -----------------------------------------------------------
    def list_records(self, base_id, formula, sort_field="RequestID", descending=True):
        records, offset = [], None
        for _ in range(20):  # at most 2000 records
            params = [("filterByFormula", formula), ("pageSize", "100"),
                      ("sort[0][field]", sort_field),
                      ("sort[0][direction]", "desc" if descending else "asc")]
            if offset:
                params.append(("offset", offset))
            res = self._request(
                "GET", f"{API}/{base_id}/{TABLE}?{urllib.parse.urlencode(params)}")
            records += res.get("records", [])
            offset = res.get("offset")
            if not offset:
                break
        return records

    def create_record(self, base_id, fields):
        return self._request("POST", f"{API}/{base_id}/{TABLE}", {"fields": fields})


def table_schema(cfg):
    """The Requests table. Select options use the English names from config/categories.json."""
    def choices(items):
        return [{"name": item["en"]} for item in items]

    subs = [s for c in cfg["categories"] for s in c["subcategories"]]
    return {
        "name": TABLE,
        "description": "Customer service requests",
        "fields": [
            {"name": "RequestID", "type": "autoNumber"},
            {"name": "Phone", "type": "singleLineText"},
            {"name": "Category", "type": "singleSelect",
             "options": {"choices": choices(cfg["categories"])}},
            {"name": "Subcategory", "type": "singleSelect", "options": {"choices": choices(subs)}},
            {"name": "Description", "type": "multilineText"},
            {"name": "Status", "type": "singleSelect",
             "options": {"choices": choices(cfg["statuses"])}},
        ],
    }


UPDATED_FIELD = {
    "name": "Updated",
    "type": "lastModifiedTime",
    "options": {
        "referencedFieldIds": [],
        "result": {"type": "dateTime", "options": {
            "dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"},
            "timeZone": "utc"}},
    },
}


def create_requests_base(client, workspace_id, cfg):
    """Create the Base and table. Returns (base_id, updated_field_created)."""
    base = client.create_base(workspace_id, BASE_NAME, [table_schema(cfg)])
    base_id = base["id"]
    table_id = base["tables"][0]["id"]
    try:  # separate call: if it is refused, the app falls back to the record creation time
        client.add_field(base_id, table_id, UPDATED_FIELD)
        return base_id, True
    except AirtableError:
        return base_id, False
