"""Shared helpers: time, hashing, enums, text compare keys."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw"
MANIFESTS = ROOT / "manifests"
NORMALIZED = ROOT / "normalized"
REPORTS = ROOT / "reports"
SCHEMAS = ROOT / "schemas"
MIGRATIONS = ROOT / "migrations"
FIXTURES = ROOT / "tests" / "fixtures"
DB_DIR = ROOT / "db"
BACKUPS = ROOT / "backups"

CATEGORY_MAP = {
    "algorithms": "algorithm",
    "algorithm": "algorithm",
    "database": "database",
    "shell": "shell",
    "concurrency": "concurrency",
    "javascript": "javascript",
    "pandas": "pandas",
}

DIFFICULTY_MAP = {
    "easy": "easy",
    "medium": "medium",
    "hard": "hard",
    "简单": "easy",
    "中等": "medium",
    "困难": "hard",
}

CATEGORIES = set(CATEGORY_MAP.values())
DIFFICULTIES = {"easy", "medium", "hard"}

SOURCE_PRIORITY = {"leetcode-api": 0, "neenza": 1, "doocs": 2}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def blank_to_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return value


def map_category(raw):
    if raw is None:
        return None
    key = str(raw).strip().lower()
    return CATEGORY_MAP.get(key)


def map_difficulty(raw):
    if raw is None:
        return None
    key = str(raw).strip().lower()
    return DIFFICULTY_MAP.get(key) or DIFFICULTY_MAP.get(str(raw).strip())


def newlines(text: str | None) -> str | None:
    if text is None:
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")


def compare_key(text: str | None) -> str:
    if not text:
        return ""
    t = text.lower().replace("\xa0", " ")
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[*_`#\[\]()!>|\-]", "", t)
    t = re.sub(r"\s+", "", t)
    return t


def slug_code(name: str) -> str:
    text = name.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-\u4e00-\u9fff]+", "", text)
    return text.strip("-") or name.strip().lower()


def read_json(path: Path):
    with path.open(encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
