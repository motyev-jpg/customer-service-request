"""Keep the static demo (docs/) in sync with the Flask app's config and demo data."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_static import build  # noqa: E402


def test_docs_match_generated_output(tmp_path):
    build(tmp_path)
    for rel in ("data/categories.json", "data/translations.json", "data/demo.json"):
        expected = json.loads((tmp_path / rel).read_text(encoding="utf-8"))
        actual = json.loads((ROOT / "docs" / rel).read_text(encoding="utf-8"))
        assert actual == expected, f"{rel} is stale, run: python tools/build_static.py"
    for rel in ("css/style.css", "assets/logo.svg"):
        assert (ROOT / "docs" / rel).read_text(encoding="utf-8") == \
            (tmp_path / rel).read_text(encoding="utf-8"), f"{rel} is stale"


def test_translation_keys_match_between_languages():
    tr = json.loads((ROOT / "docs" / "data" / "translations.json").read_text(encoding="utf-8"))
    assert set(tr["en"]) == set(tr["he"])


def test_gitignore_does_not_exclude_docs_data():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    assert "data/" not in lines, "use /data/ so docs/data/ is not ignored"


def test_no_airtable_token_in_repo_files():
    import re
    pattern = re.compile(r"pat[A-Za-z0-9]{14}\.[a-f0-9]{64}")
    skip = {".venv", ".git", "data", "__pycache__", ".pytest_cache"}
    for path in ROOT.rglob("*"):
        if path.is_file() and not skip & set(path.relative_to(ROOT).parts):
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert not pattern.search(text), f"Airtable token found in {path}"
