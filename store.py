"""Data sources for service requests: local SQLite (default) or Airtable.

Both return request rows with the keys id, phone, category, subcategory, description,
status, created_at, updated_at (category, subcategory and status are config ids).
"""
import re

import db
from airtable import formula_str


class SqliteStore:
    name = "sqlite"
    supports_history = True

    def __init__(self, path):
        self._path = path

    def _run(self, fn):
        conn = db.connect(self._path)
        try:
            return fn(conn)
        finally:
            conn.close()

    def list_requests(self, phone):
        return self._run(lambda c: db.list_requests(c, phone))

    def get_request(self, request_id, phone):
        return self._run(lambda c: db.get_request(c, request_id, phone))

    def get_history(self, request_id):
        return self._run(lambda c: db.get_history(c, request_id))

    def create_request(self, phone, category, subcategory, description):
        return self._run(lambda c: db.create_request(c, phone, category, subcategory, description))


def _iso(value):
    return re.sub(r"\.\d+Z$", "Z", value) if isinstance(value, str) else ""


class AirtableStore:
    name = "airtable"
    supports_history = False

    def __init__(self, client, base_id, cfg):
        self._client = client
        self._base = base_id
        self._cat_by_name = {c["en"]: c["id"] for c in cfg["categories"]}
        self._sub_by_name = {s["en"]: s["id"] for c in cfg["categories"]
                             for s in c["subcategories"]}
        self._status_by_name = {s["en"]: s["id"] for s in cfg["statuses"]}
        self._name_by_id = {item["id"]: item["en"] for item in
                            cfg["categories"] + cfg["statuses"]
                            + [s for c in cfg["categories"] for s in c["subcategories"]]}

    def _row(self, record):
        f = record.get("fields", {})
        rid = f.get("RequestID")
        if not isinstance(rid, int):
            return None
        created = _iso(record.get("createdTime"))
        cat, sub, status = f.get("Category", ""), f.get("Subcategory", ""), f.get("Status", "")
        return {
            "id": rid, "phone": f.get("Phone", ""),
            "category": self._cat_by_name.get(cat, cat),
            "subcategory": self._sub_by_name.get(sub, sub),
            "description": f.get("Description", ""),
            "status": self._status_by_name.get(status, status),
            "created_at": created, "updated_at": _iso(f.get("Updated")) or created,
        }

    def _rows(self, formula):
        rows = (self._row(r) for r in self._client.list_records(self._base, formula))
        return [r for r in rows if r]

    def list_requests(self, phone):
        return self._rows(f"{{Phone}}={formula_str(phone)}")

    def get_request(self, request_id, phone):
        rows = self._rows(f"AND({{Phone}}={formula_str(phone)},{{RequestID}}={int(request_id)})")
        return rows[0] if rows else None

    def get_history(self, request_id):
        return []

    def create_request(self, phone, category, subcategory, description):
        record = self._client.create_record(self._base, {
            "Phone": phone, "Category": self._name_by_id[category],
            "Subcategory": self._name_by_id[subcategory], "Description": description,
            "Status": self._name_by_id["open"]})
        return record.get("fields", {}).get("RequestID")
