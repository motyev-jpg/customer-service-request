"""Server-side settings file (holds the Airtable token). Lives in data/, which git ignores."""
import json
import os
from pathlib import Path


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)  # best effort, no effect on Windows
    except OSError:
        pass
    tmp.replace(path)


def mask(token):
    return f"{token[:3]}…{token[-4:]}" if token and len(token) > 8 else "…"
