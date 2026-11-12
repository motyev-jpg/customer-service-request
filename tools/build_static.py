"""Build the static demo (docs/) from the Flask app's config, translations and demo data.

Run after changing config/*.json, db.DEMO_REQUESTS, or static/css/style.css:
    python tools/build_static.py
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import db  # noqa: E402

# Opens the Airtable settings screen (same default as the Flask app's ADMIN_PHONE).
ADMIN_PHONE = "543210"

# Texts used only by the static demo.
STATIC_TEXTS = {
    "en": {
        "static_banner": "Static demo: your data is saved in this browser only.",
        "airtable_banner": "Connected to Airtable: requests are stored in the Airtable Base.",
        "reset_demo": "Reset demo data",
        "loading": "Loading...",
        "source_static": "Static demo data (this browser only)",
        "static_admin_intro": "Connect this demo to an existing Airtable Base (create it from the Flask admin screen). The token is saved in this browser only.",
        "static_token_hint": "Use a token with data.records:read and data.records:write for the demo Base only.",
        "base_id": "Base ID",
        "base_hint": "Starts with app. Found in the Base URL: airtable.com/appXXXX/...",
        "connect_static": "Connect",
        "invalid_base": "The Base ID must look like appXXXXXXXXXXXXXX.",
        "connect_failed": "Could not connect to Airtable.",
        "static_connected": "Connected to Airtable.",
        "static_disconnected": "Disconnected. The demo uses its built-in data again.",
        "teacher_link": "Create link for the teacher",
        "teacher_link_note": "Anyone with this link can read and change the data in this Base. Share it only with people you trust, and revoke the token afterwards.",
        "copy_link": "Copy link",
        "copied": "Copied",
    },
    "he": {
        "static_banner": "דמו סטטי: הנתונים נשמרים בדפדפן שלך בלבד.",
        "airtable_banner": "מחובר ל-Airtable: הבקשות נשמרות ב-Base ב-Airtable.",
        "reset_demo": "איפוס נתוני דמו",
        "loading": "טוען...",
        "source_static": "נתוני דמו סטטיים (בדפדפן הזה בלבד)",
        "static_admin_intro": "חיבור הדמו ל-Base קיים ב-Airtable (אפשר ליצור אותו ממסך המנהל של Flask). ה-token נשמר בדפדפן הזה בלבד.",
        "static_token_hint": "מומלץ token עם data.records:read ו-data.records:write ל-Base הדמו בלבד.",
        "base_id": "Base ID",
        "base_hint": "מתחיל ב-app. נמצא בכתובת ה-Base: airtable.com/appXXXX/...",
        "connect_static": "חבר",
        "invalid_base": "ה-Base ID צריך להיראות כך: appXXXXXXXXXXXXXX.",
        "connect_failed": "לא ניתן להתחבר ל-Airtable.",
        "static_connected": "החיבור ל-Airtable הצליח.",
        "static_disconnected": "החיבור נותק. הדמו משתמש שוב בנתונים המובנים.",
        "teacher_link": "צור קישור למורה",
        "teacher_link_note": "כל מי שמקבל את הקישור יכול לקרוא ולשנות את הנתונים ב-Base הזה. שתף רק אנשים שאתה סומך עליהם, ובטל את ה-token אחר כך.",
        "copy_link": "העתק קישור",
        "copied": "הועתק",
    },
}


def _dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(out):
    out = Path(out)
    categories = json.loads((ROOT / "config" / "categories.json").read_text(encoding="utf-8"))
    translations = json.loads((ROOT / "config" / "translations.json").read_text(encoding="utf-8"))
    for lang, extra in STATIC_TEXTS.items():
        translations[lang].update(extra)

    demo = {
        "phones": db.DEMO_PHONES,
        "admin_phone": ADMIN_PHONE,
        "requests": [
            {"phone": phone, "category": cat, "subcategory": sub, "description": desc,
             "history": [[status, days] for status, days in history]}
            for phone, cat, sub, desc, history in db.DEMO_REQUESTS
        ],
    }

    _dump(out / "data" / "categories.json", categories)
    _dump(out / "data" / "translations.json", translations)
    _dump(out / "data" / "demo.json", demo)
    (out / "css").mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "static" / "css" / "style.css", out / "css" / "style.css")
    shutil.copyfile(ROOT / "static" / "assets" / "logo.svg", out / "assets" / "logo.svg")


if __name__ == "__main__":
    build(ROOT / "docs")
    print("Static demo data written to docs/")
