"""SQLite access layer and demo data for the service request dashboard."""
import sqlite3
from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    phone       TEXT NOT NULL,
    category    TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_requests_phone ON requests(phone);

CREATE TABLE IF NOT EXISTS status_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL REFERENCES requests(id),
    status     TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_request ON status_history(request_id);
"""

# Fake numbers only. The last one has no requests (empty history demo).
DEMO_PHONES = ["0500000001", "0500000002", "0500000003", "0500000004"]

# (phone, category, subcategory, description, [(status, days_ago), ...])
# The first history entry is the creation time, the last one is the current status.
DEMO_REQUESTS = [
    ("0500000001", "billing", "invoice_question",
     "The March invoice shows a charge I do not recognize.",
     [("open", 40), ("in_progress", 38), ("resolved", 35), ("closed", 30)]),
    ("0500000001", "technical", "cannot_connect",
     "החיבור לשירות נופל כל כמה דקות מאז אתמול בערב.",
     [("open", 6), ("in_progress", 5), ("waiting_customer", 4)]),
    ("0500000001", "account", "update_details",
     "Please update my address on the account.",
     [("open", 12), ("in_progress", 11), ("resolved", 9)]),
    ("0500000001", "general", "suggestion",
     "הצעה: להוסיף אפשרות לצפות בחשבוניות קודמות.",
     [("open", 2)]),
    ("0500000002", "billing", "refund_request",
     "I was charged twice for the same service. Requesting a refund.",
     [("open", 20), ("in_progress", 18), ("waiting_customer", 15), ("in_progress", 13),
      ("resolved", 10)]),
    ("0500000002", "technical", "slow_performance",
     "הגלישה איטית מאוד בשעות הערב.",
     [("open", 3), ("in_progress", 1)]),
    ("0500000002", "account", "access_problem",
     "I cannot log in to my account after the password reset.",
     [("open", 50), ("in_progress", 49), ("resolved", 48), ("closed", 40)]),
    ("0500000002", "general", "complaint",
     "המתנתי 40 דקות בטלפון ללא מענה.",
     [("open", 8), ("in_progress", 7), ("resolved", 5)]),
    ("0500000003", "technical", "equipment_fault",
     "The router shows a red light and does not restart.",
     [("open", 1)]),
    ("0500000003", "billing", "payment_issue",
     "התשלום בכרטיס האשראי נדחה למרות שיש כיסוי.",
     [("open", 9), ("in_progress", 8), ("waiting_customer", 7)]),
    ("0500000003", "account", "close_account",
     "אני מבקש לסגור את החשבון בסוף החודש.",
     [("open", 30), ("in_progress", 29), ("resolved", 27), ("closed", 25)]),
    ("0500000003", "general", "other",
     "",
     [("open", 4), ("in_progress", 3)]),
    ("0500000003", "technical", "cannot_connect",
     "No internet since this morning, all devices affected.",
     [("open", 14), ("in_progress", 14), ("resolved", 13)]),
]


def demo_requests_oldest_first():
    """Demo requests as (phone, category, subcategory, description, current_status),
    oldest first, so that numbered ids follow creation order."""
    ordered = sorted(DEMO_REQUESTS, key=lambda r: -r[4][0][1])
    return [(phone, cat, sub, desc, history[-1][0])
            for phone, cat, sub, desc, history in ordered]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path, seed=True):
    """Create the schema and, when the database is empty, load the demo data."""
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        empty = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0
        if seed and empty:
            _seed(conn)
        conn.commit()
    finally:
        conn.close()


def _seed(conn):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    for phone, category, sub, desc, history in DEMO_REQUESTS:
        times = [(s, (now - timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ"))
                 for s, d in history]
        cur = conn.execute(
            "INSERT INTO requests (phone, category, subcategory, description, status,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (phone, category, sub, desc, times[-1][0], times[0][1], times[-1][1]))
        conn.executemany(
            "INSERT INTO status_history (request_id, status, changed_at) VALUES (?, ?, ?)",
            [(cur.lastrowid, s, t) for s, t in times])


def list_requests(conn, phone):
    return conn.execute(
        "SELECT * FROM requests WHERE phone = ? ORDER BY created_at DESC, id DESC",
        (phone,)).fetchall()


def get_request(conn, request_id, phone):
    return conn.execute("SELECT * FROM requests WHERE id = ? AND phone = ?",
                        (request_id, phone)).fetchone()


def get_history(conn, request_id):
    return conn.execute(
        "SELECT status, changed_at FROM status_history WHERE request_id = ?"
        " ORDER BY changed_at, id", (request_id,)).fetchall()


def create_request(conn, phone, category, subcategory, description):
    now = now_iso()
    cur = conn.execute(
        "INSERT INTO requests (phone, category, subcategory, description, status,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, 'open', ?, ?)",
        (phone, category, subcategory, description, now, now))
    conn.execute(
        "INSERT INTO status_history (request_id, status, changed_at) VALUES (?, 'open', ?)",
        (cur.lastrowid, now))
    conn.commit()
    return cur.lastrowid
