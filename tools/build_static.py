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

# Texts used only by the static demo.
STATIC_TEXTS = {
    "en": {
        "static_banner": "Static demo: your data is saved in this browser only.",
        "reset_demo": "Reset demo data",
    },
    "he": {
        "static_banner": "דמו סטטי: הנתונים נשמרים בדפדפן שלך בלבד.",
        "reset_demo": "איפוס נתוני דמו",
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
