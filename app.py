"""Customer service request dashboard (Flask)."""
import json
import os
import re
import secrets
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from markupsafe import Markup

import db

BASE_DIR = Path(__file__).parent
LANGS = ("en", "he")
DEFAULT_LANG = "en"
MAX_DESCRIPTION = 1000
PHONE_RE = re.compile(r"^\d{9,15}$")


def _load_json(name):
    return json.loads((BASE_DIR / "config" / name).read_text(encoding="utf-8"))


def create_app(db_path=None):
    load_dotenv(BASE_DIR / ".env")
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["DB_PATH"] = db_path or os.environ.get(
        "DB_PATH", str(BASE_DIR / "data" / "csrm.db"))
    Path(app.config["DB_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    db.init_db(app.config["DB_PATH"])

    cfg = _load_json("categories.json")
    translations = _load_json("translations.json")
    categories = {c["id"]: c for c in cfg["categories"]}
    statuses = {s["id"]: s for s in cfg["statuses"]}

    # ---- helpers -----------------------------------------------------------
    def lang():
        value = session.get("lang", DEFAULT_LANG)
        return value if value in LANGS else DEFAULT_LANG

    def conn():
        if "db" not in g:
            g.db = db.connect(app.config["DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        c = g.pop("db", None)
        if c is not None:
            c.close()

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    def safe_next(target):
        if target and target.startswith("/") and not target.startswith("//"):
            return target
        return url_for("index")

    def current_phone():
        return session.get("phone")

    @app.before_request
    def check_csrf():
        if request.method == "POST":
            sent = request.form.get("csrf", "")
            if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
                abort(400)

    @app.context_processor
    def inject():
        current = lang()
        texts = translations[current]
        return {
            "lang": current,
            "dir": "rtl" if current == "he" else "ltr",
            "t": lambda key: texts.get(key, key),
            "csrf_token": csrf_token,
            "phone": current_phone(),
            "localized": lambda item: item[current],
            "category_name": lambda cid: categories[cid][current] if cid in categories else cid,
            "sub_name": lambda cid, sid: next(
                (s[current] for s in categories.get(cid, {}).get("subcategories", [])
                 if s["id"] == sid), sid),
            "status_info": lambda sid: {
                "name": statuses[sid][current] if sid in statuses else sid,
                "color": statuses[sid]["color"] if sid in statuses else "#d9d9d9",
            },
            "fmt_date": fmt_date,
            "request_no": lambda rid: f"SR-{rid:04d}",
            "next_path": request.full_path.rstrip("?") if request else "/",
        }

    def fmt_date(value):
        try:
            text = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            text = value or ""
        # Keep date and time in left-to-right order inside RTL pages
        return Markup('<bdi dir="ltr">{}</bdi>').format(text)

    # ---- routes ------------------------------------------------------------
    @app.route("/")
    def index():
        return redirect(url_for("dashboard" if current_phone() else "login"))

    @app.route("/lang/<code>")
    def set_lang(code):
        if code in LANGS:
            session["lang"] = code
        return redirect(safe_next(request.args.get("next")))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            digits = re.sub(r"[\s\-()+]", "", request.form.get("phone", ""))
            if PHONE_RE.match(digits):
                session["phone"] = digits
                return redirect(url_for("dashboard"))
            error = "invalid_phone"
        return render_template("login.html", error=error, demo_phones=db.DEMO_PHONES)

    @app.route("/logout", methods=["POST"])
    def logout():
        session.pop("phone", None)
        return redirect(url_for("login"))

    def require_login():
        if not current_phone():
            abort(redirect(url_for("login")))

    @app.route("/dashboard")
    def dashboard():
        require_login()
        status = request.args.get("status", "")
        category = request.args.get("category", "")
        q = request.args.get("q", "").strip()
        if status not in statuses:
            status = ""
        if category not in categories:
            category = ""
        rows = db.list_requests(conn(), current_phone(), status or None,
                                category or None, q or None)
        counts = db.status_counts(conn(), current_phone())
        return render_template(
            "dashboard.html", rows=rows, counts=counts, total=sum(counts.values()),
            statuses=cfg["statuses"], categories=cfg["categories"],
            f_status=status, f_category=category, f_q=q)

    @app.route("/requests/new", methods=["GET", "POST"])
    def new_request():
        require_login()
        error = None
        form = {"category": "", "subcategory": "", "description": ""}
        if request.method == "POST":
            form = {k: request.form.get(k, "").strip() for k in form}
            cat = categories.get(form["category"])
            valid_sub = cat and any(s["id"] == form["subcategory"]
                                    for s in cat["subcategories"])
            if not valid_sub:
                error = "invalid_category"
            elif len(form["description"]) > MAX_DESCRIPTION:
                error = "description_too_long"
            else:
                db.create_request(conn(), current_phone(), form["category"],
                                  form["subcategory"], form["description"])
                flash("request_created")
                return redirect(url_for("dashboard"))
        return render_template("new_request.html", categories=cfg["categories"],
                               form=form, error=error, max_len=MAX_DESCRIPTION)

    @app.route("/requests/<int:request_id>")
    def request_detail(request_id):
        require_login()
        row = db.get_request(conn(), request_id, current_phone())
        if row is None:
            abort(404)
        return render_template("detail.html", r=row,
                               history=db.get_history(conn(), request_id))

    @app.errorhandler(400)
    def bad_request(_e):
        return render_template("error.html", message_key="bad_request"), 400

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", message_key="not_found"), 404

    return app


if __name__ == "__main__":
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")
