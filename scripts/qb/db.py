"""SQLite connection and migration."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from qb.util import MIGRATIONS


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='problem'"
    ).fetchone()
    if existing:
        return
    sql = (MIGRATIONS / "sqlite" / "001_init.sql").read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    names = [
        "problem",
        "problem_source_identity",
        "problem_content",
        "problem_example",
        "problem_hint",
        "tag",
        "problem_tag",
        "starter_code",
        "asset",
        "content_asset",
        "source_record",
        "content_provenance",
        "content_revision",
        "import_batch",
        "data_issue",
    ]
    return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in names}
