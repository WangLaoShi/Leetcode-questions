"""Command line for manifest, normalize, import, acceptance, and queries."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from qb.accept import run_acceptance, select_sample_slugs
from qb.coverage import write_coverage
from qb.db import connect, migrate, table_counts
from qb.importer import import_records
from qb.inventory import build_inventory
from qb.manifest import write_manifest
from qb.normalize import normalize_all
from qb.util import BACKUPS, DB_DIR, FIXTURES, NORMALIZED, REPORTS, utc_now, write_json


def _slugs(value: str | None) -> set[str] | None:
    if not value:
        return None
    path = Path(value)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("slugs", [])
        return set(data)
    return {item.strip() for item in value.split(",") if item.strip()}


def _import(args) -> dict:
    return import_records(
        Path(args.db),
        normalized_dir=NORMALIZED,
        sources=[args.source] if args.source else None,
        slug_filter=_slugs(args.slugs),
        dry_run=args.dry_run,
        fail_slug=args.fail_slug,
        reports_dir=REPORTS,
    )


def _backup(db: Path) -> dict:
    stamp = utc_now().replace(":", "").replace("-", "")
    dest = BACKUPS / f"question-bank-{stamp}.sqlite"
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(db)
    target = sqlite3.connect(dest)
    source.backup(target)
    source.close()
    target.close()
    check = sqlite3.connect(dest)
    integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
    restored = check.execute("SELECT COUNT(*) FROM problem").fetchone()[0]
    original = sqlite3.connect(db).execute("SELECT COUNT(*) FROM problem").fetchone()[0]
    check.close()
    report = {
        "backup": str(dest),
        "integrity_check": integrity,
        "problem_count_backup": restored,
        "problem_count_source": original,
        "restorable": integrity == "ok" and restored == original,
    }
    write_json(REPORTS / "backup-verify.json", report)
    return report


def _query(args) -> None:
    conn = connect(Path(args.db))
    clauses = ["c.is_current = 1"]
    params: list = []
    if args.slug:
        clauses.append("i.slug = ?")
        params.append(args.slug)
    if args.display_id:
        clauses.append("i.display_id = ?")
        params.append(args.display_id)
    if args.title:
        clauses.append("c.title LIKE ?")
        params.append(f"%{args.title}%")
    if args.site:
        clauses.append("i.site = ?")
        params.append(args.site)
    if args.locale:
        clauses.append("c.locale = ?")
        params.append(args.locale)
    if args.category:
        clauses.append("p.category = ?")
        params.append(args.category)
    if args.difficulty:
        clauses.append("p.difficulty = ?")
        params.append(args.difficulty)
    limit = args.limit or 20
    sql = f"""
        SELECT p.id, i.site, i.display_id, i.slug, i.platform_question_id,
               p.category, p.difficulty, p.is_paid_only, c.locale, c.title,
               c.revision, c.extraction_status, length(c.statement_markdown) AS statement_chars
        FROM problem p
        JOIN problem_source_identity i ON i.problem_id = p.id
        JOIN problem_content c ON c.source_identity_id = i.id
        WHERE {' AND '.join(clauses)}
        LIMIT {int(limit)}
    """
    rows = [dict(row) for row in conn.execute(sql, params)]
    if args.issues:
        rows = [dict(row) for row in conn.execute(
            "SELECT issue_type, severity, status, COUNT(*) AS n FROM data_issue GROUP BY 1, 2, 3 ORDER BY n DESC"
        )]
    text = json.dumps(rows, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    conn.close()


def _remove_db(path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            candidate.unlink()


def run_all() -> None:
    print("manifest", flush=True)
    write_manifest()
    print("inventory", flush=True)
    build_inventory()
    print("normalize", flush=True)
    normalize_all()
    slugs = select_sample_slugs()
    FIXTURES.mkdir(parents=True, exist_ok=True)
    write_json(FIXTURES / "sample-slugs.json", {"slugs": slugs, "count": len(slugs)})
    sample_db = DB_DIR / "sample.sqlite"
    _remove_db(sample_db)
    print("sample import", len(slugs), flush=True)
    sample_report = import_records(
        sample_db,
        normalized_dir=NORMALIZED,
        slug_filter=set(slugs),
        reports_dir=REPORTS,
    )
    print("sample", sample_report["status"], sample_report["counts"], flush=True)
    acceptance = run_acceptance(sample_db, slugs)
    write_json(REPORTS / "sample-acceptance.json", acceptance)
    if not acceptance["passed"]:
        raise SystemExit("sample acceptance failed; full import not started")
    full_db = DB_DIR / "question-bank.sqlite"
    _remove_db(full_db)
    print("full dry-run", flush=True)
    dry = import_records(full_db, normalized_dir=NORMALIZED, dry_run=True, reports_dir=REPORTS)
    print("dry-run", dry["status"], dry["counts"], flush=True)
    print("full import", flush=True)
    full = import_records(full_db, normalized_dir=NORMALIZED, reports_dir=REPORTS)
    print("full", full["status"], full["counts"], flush=True)
    coverage = write_coverage(full_db)
    backup = _backup(full_db)
    conn = connect(full_db)
    smoke = {
        "by_slug": _one(conn, "two-sum", "leetcode.com", "en"),
        "by_display": _one_display(conn, "175"),
        "issues": [dict(row) for row in conn.execute(
            "SELECT issue_type, COUNT(*) AS n FROM data_issue GROUP BY 1 ORDER BY n DESC"
        )],
        "counts": table_counts(conn),
    }
    conn.close()
    write_json(REPORTS / "query-smoke.json", smoke)
    summary = {
        "finished_at": utc_now(),
        "sample_status": sample_report["status"],
        "acceptance_passed": acceptance["passed"],
        "dry_run_status": dry["status"],
        "full_status": full["status"],
        "full_counts": full["counts"],
        "coverage_problems": coverage["problems"],
        "backup_restorable": backup["restorable"],
    }
    write_json(REPORTS / "pipeline-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def _one(conn, slug, site, locale):
    row = conn.execute(
        """
        SELECT c.title, substr(c.statement_markdown, 1, 180) AS head
        FROM problem_content c
        JOIN problem_source_identity i ON i.id = c.source_identity_id
        WHERE i.slug=? AND i.site=? AND c.locale=? AND c.is_current=1
        """,
        (slug, site, locale),
    ).fetchone()
    return dict(row) if row else None


def _one_display(conn, display_id):
    row = conn.execute(
        """
        SELECT i.slug, c.title FROM problem_content c
        JOIN problem_source_identity i ON i.id = c.source_identity_id
        WHERE i.display_id=? AND i.site='leetcode.com' AND c.is_current=1 AND c.locale='en'
        """,
        (display_id,),
    ).fetchone()
    return dict(row) if row else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Question bank pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest")
    sub.add_parser("inventory")
    norm = sub.add_parser("normalize")
    norm.add_argument("--source", choices=["neenza", "leetcode-api", "doocs"])
    imp = sub.add_parser("import")
    imp.add_argument("--db", required=True)
    imp.add_argument("--source", choices=["neenza", "leetcode-api", "doocs"])
    imp.add_argument("--slugs")
    imp.add_argument("--dry-run", action="store_true")
    imp.add_argument("--fail-slug")
    sub.add_parser("accept")
    cov = sub.add_parser("coverage")
    cov.add_argument("--db", required=True)
    bak = sub.add_parser("backup")
    bak.add_argument("--db", required=True)
    query = sub.add_parser("query")
    query.add_argument("--db", required=True)
    query.add_argument("--slug")
    query.add_argument("--display-id")
    query.add_argument("--title")
    query.add_argument("--site")
    query.add_argument("--locale")
    query.add_argument("--category")
    query.add_argument("--difficulty")
    query.add_argument("--limit", type=int)
    query.add_argument("--issues", action="store_true")
    query.add_argument("--out")
    sub.add_parser("all")
    mig = sub.add_parser("migrate")
    mig.add_argument("--db", required=True)
    args = parser.parse_args()
    if args.cmd == "manifest":
        write_manifest()
    elif args.cmd == "inventory":
        build_inventory()
    elif args.cmd == "normalize":
        normalize_all(args.source)
    elif args.cmd == "import":
        report = _import(args)
        print(json.dumps({"status": report["status"], "counts": report["counts"], "committed": report["committed"]}, ensure_ascii=False))
    elif args.cmd == "accept":
        slugs = json.loads((FIXTURES / "sample-slugs.json").read_text(encoding="utf-8"))["slugs"]
        report = run_acceptance(DB_DIR / "sample.sqlite", slugs)
        write_json(REPORTS / "sample-acceptance.json", report)
        print(json.dumps({"passed": report["passed"], "checks": report["checks"]}, ensure_ascii=False, indent=2))
        if not report["passed"]:
            raise SystemExit(1)
    elif args.cmd == "coverage":
        print(json.dumps(write_coverage(Path(args.db)), ensure_ascii=False, indent=2))
    elif args.cmd == "backup":
        print(json.dumps(_backup(Path(args.db)), ensure_ascii=False, indent=2))
    elif args.cmd == "query":
        _query(args)
    elif args.cmd == "migrate":
        conn = connect(Path(args.db))
        migrate(conn)
        conn.close()
    elif args.cmd == "all":
        run_all()


if __name__ == "__main__":
    main()
