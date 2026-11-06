"""Sample selection and acceptance checks, including rerun, failure, and revision."""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

from qb.db import connect, table_counts
from qb.importer import import_records
from qb.util import DB_DIR, NORMALIZED, REPORTS, utc_now

MUST = [
    "two-sum",
    "add-two-numbers",
    "median-of-two-sorted-arrays",
    "regular-expression-matching",
    "zigzag-conversion",
    "container-with-most-water",
    "combine-two-tables",
    "word-frequency",
    "print-in-order",
    "check-if-object-instance-of-class",
    "create-a-dataframe-from-list",
    "construct-quad-tree",
]
STABLE = [
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
    "data_issue",
]


def select_sample_slugs() -> list[str]:
    rows = []
    with (NORMALIZED / "leetcode-api.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            content = record["contents"][0]
            rows.append(
                {
                    "slug": record["identity"]["slug"],
                    "category": record.get("category"),
                    "difficulty": record.get("difficulty"),
                    "paid": record.get("is_paid_only"),
                    "has_statement": bool(content.get("statement_markdown")),
                    "assets": len(record.get("assets") or []),
                    "pid": record["identity"].get("platform_question_id"),
                    "display": record["identity"].get("display_id"),
                }
            )
    by_slug = {row["slug"]: row for row in rows}
    chosen: list[str] = []
    missing = []
    for slug in MUST:
        if slug in by_slug:
            chosen.append(slug)
        else:
            missing.append(slug)
    paid = next((row["slug"] for row in rows if row["paid"] is True), None)
    if paid and paid not in chosen:
        chosen.append(paid)
    elif not paid:
        missing.append("paid-problem")
    for difficulty in ("easy", "medium", "hard"):
        extra = [
            row["slug"]
            for row in rows
            if row["difficulty"] == difficulty
            and row["category"] == "algorithm"
            and row["has_statement"]
            and row["slug"] not in chosen
        ]
        chosen.extend(extra[:8])
    for category in ("database", "shell", "concurrency", "javascript", "pandas"):
        if any(by_slug[slug]["category"] == category for slug in chosen):
            continue
        found = next((row["slug"] for row in rows if row["category"] == category and row["has_statement"]), None)
        if found:
            chosen.append(found)
        else:
            missing.append(f"category:{category}")
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "sample-selection.json").write_text(
        json.dumps(
            {
                "count": len(chosen),
                "missing": missing,
                "paid_slug": paid,
                "id_mismatch_example": by_slug.get("construct-quad-tree"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return chosen


def _check(checks: list[dict], name: str, ok: bool, detail) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def run_acceptance(db_path: Path, slugs: list[str]) -> dict:
    checks: list[dict] = []
    conn = connect(db_path)
    batch = conn.execute(
        "SELECT counts_json, status FROM import_batch WHERE dry_run=0 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    counts = json.loads(batch["counts_json"]) if batch else {}
    balanced = counts.get("seen", 0) == (
        counts.get("problems_created", 0)
        + counts.get("problems_matched", 0)
        + counts.get("conflicts_isolated", 0)
        + counts.get("failures", 0)
    )
    content_balanced = (
        counts.get("contents_inserted", 0) + counts.get("contents_revised", 0) + counts.get("contents_skipped", 0)
        == counts.get("problems_created", 0) + counts.get("problems_matched", 0)
    )
    _check(checks, "batch_counts_balance", balanced and content_balanced and batch["status"] in ("success", "partial"), counts)
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    _check(checks, "no_dangling_foreign_keys", not fk, len(fk))
    leaks = conn.execute(
        """
        SELECT COUNT(*) FROM problem_content
        WHERE statement_markdown LIKE '%<!-- solution:start -->%'
           OR statement_markdown LIKE '%## 解法%'
           OR statement_markdown LIKE '%## Solutions%'
           OR statement_markdown LIKE '%## Video Solution%'
           OR statement_markdown LIKE '%### 方法一%'
           OR statement_markdown LIKE '%### Approach 1%'
        """
    ).fetchone()[0]
    _check(checks, "no_editorial_in_statements", leaks == 0, leaks)
    two = conn.execute(
        """
        SELECT c.id, c.statement_markdown, c.title FROM problem_content c
        JOIN problem_source_identity i ON i.id = c.source_identity_id
        WHERE i.slug='two-sum' AND i.site='leetcode.com' AND c.locale='en' AND c.is_current=1
        """
    ).fetchone()
    statement = two["statement_markdown"] if two else ""
    _check(
        checks,
        "two_sum_statement",
        two is not None and "two numbers" in statement and "[0,1]" in statement,
        None if two else "missing",
    )
    example = conn.execute(
        "SELECT output_text, input_text FROM problem_example WHERE content_id=? AND ordinal=1",
        (two["id"],),
    ).fetchone() if two else None
    _check(checks, "two_sum_example_output", example is not None and example["output_text"] == "[0,1]", dict(example) if example else None)
    hints = conn.execute("SELECT COUNT(*) FROM problem_hint WHERE content_id=?", (two["id"],)).fetchone()[0] if two else 0
    _check(checks, "two_sum_hints_on_current_version", hints >= 1, hints)
    template = conn.execute(
        """
        SELECT template, suspected_implementation FROM starter_code
        WHERE problem_id=(SELECT problem_id FROM problem_source_identity WHERE slug='two-sum' AND site='leetcode.com')
          AND language='python3' AND is_current=1
        """
    ).fetchone()
    _check(
        checks,
        "two_sum_python_template",
        template is not None and "def twoSum" in template["template"] and template["suspected_implementation"] == 0,
        None if template else "missing",
    )
    zh = conn.execute(
        """
        SELECT c.title, c.statement_markdown FROM problem_content c
        JOIN problem_source_identity i ON i.id = c.source_identity_id
        WHERE i.slug='two-sum' AND i.site='leetcode.cn' AND c.locale='zh-CN' AND c.is_current=1
        """
    ).fetchone()
    _check(
        checks,
        "two_sum_chinese_kept_on_cn_site",
        zh is not None and zh["title"] == "两数之和" and "整数数组" in (zh["statement_markdown"] or "") and "## 解法" not in (zh["statement_markdown"] or ""),
        zh["title"] if zh else None,
    )
    sql = conn.execute(
        """
        SELECT c.type_specific_json FROM problem_content c
        JOIN problem_source_identity i ON i.id = c.source_identity_id
        WHERE i.slug='combine-two-tables' AND i.site='leetcode.com' AND c.locale='en' AND c.is_current=1
        """
    ).fetchone()
    schemas = []
    if sql:
        schemas = json.loads(sql["type_specific_json"]).get("sql", {}).get("schemas_and_samples", [])
    _check(checks, "sql_schemas_kept", len(schemas) >= 2 and any("Person" in item or "person" in item for item in schemas), len(schemas))
    quad = conn.execute(
        """
        SELECT platform_question_id, display_id FROM problem_source_identity
        WHERE slug='construct-quad-tree' AND site='leetcode.com'
        """
    ).fetchone()
    _check(
        checks,
        "internal_id_differs_from_display_id",
        quad is not None and quad["platform_question_id"] != quad["display_id"],
        dict(quad) if quad else None,
    )
    paid = conn.execute(
        """
        SELECT p.is_paid_only, c.statement_markdown, c.extraction_status, s.source_name
        FROM problem p
        JOIN problem_content c ON c.problem_id=p.id AND c.locale='en'
        JOIN content_provenance pv ON pv.object_type='content' AND pv.object_id=c.id
        JOIN source_record s ON s.id=pv.source_record_id
        WHERE p.is_paid_only=1 AND s.source_name='leetcode-api'
        LIMIT 1
        """
    ).fetchone()
    _check(
        checks,
        "paid_api_snapshot_not_backfilled",
        paid is not None and not (paid["statement_markdown"] or "").strip() and paid["extraction_status"] == "missing",
        {"source": paid["source_name"], "extraction_status": paid["extraction_status"]} if paid else None,
    )
    orphan_content = conn.execute(
        """
        SELECT COUNT(*) FROM problem_content c
        LEFT JOIN content_provenance p ON p.object_type='content' AND p.object_id=c.id
        WHERE p.id IS NULL
        """
    ).fetchone()[0]
    _check(checks, "every_statement_has_provenance", orphan_content == 0, orphan_content)
    categories = {
        row["category"]
        for row in conn.execute("SELECT DISTINCT category FROM problem WHERE category IS NOT NULL")
    }
    _check(checks, "sample_covers_available_categories", categories >= {"algorithm", "database", "shell", "concurrency", "javascript", "pandas"}, sorted(categories))
    before = table_counts(conn)
    conn.close()

    rerun = import_records(db_path, normalized_dir=NORMALIZED, slug_filter=set(slugs), reports_dir=REPORTS)
    conn = connect(db_path)
    after = table_counts(conn)
    stable = {name: before[name] == after[name] for name in STABLE}
    _check(checks, "rerun_does_not_grow_rows", all(stable.values()) and rerun["counts"]["contents_skipped"] > 0, {"stable": stable, "skipped": rerun["counts"]["contents_skipped"]})

    revised = _revision_check(db_path, checks)
    conn.close()
    _failure_check(checks)
    passed = all(item["ok"] for item in checks)
    return {"passed": passed, "checked_at": utc_now(), "checks": checks, "revision": revised}


def _revision_check(db_path: Path, checks: list[dict]) -> dict:
    record = None
    with (NORMALIZED / "leetcode-api.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            if item["identity"].get("slug") == "two-sum":
                record = item
                break
    if not record:
        _check(checks, "revision_keeps_old_statement", False, "two-sum missing")
        return {}
    record["contents"][0]["statement_markdown"] = (record["contents"][0]["statement_markdown"] or "") + "\n\nRevision marker ALPHA."
    temp = REPORTS / "revision-input"
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)
    (temp / "leetcode-api.jsonl").write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    import_records(
        db_path,
        normalized_dir=temp,
        sources=["leetcode-api"],
        slug_filter={"two-sum"},
        reports_dir=REPORTS,
    )
    conn = connect(db_path)
    rows = conn.execute(
        """
        SELECT c.revision, c.is_current, c.statement_markdown,
               (SELECT COUNT(*) FROM problem_example e WHERE e.content_id=c.id) AS examples
        FROM problem_content c
        JOIN content_provenance p ON p.object_type='content' AND p.object_id=c.id
        JOIN source_record s ON s.id=p.source_record_id
        JOIN problem_source_identity i ON i.id=c.source_identity_id
        WHERE i.slug='two-sum' AND i.site='leetcode.com' AND c.locale='en' AND s.source_name='leetcode-api'
        ORDER BY c.revision
        """
    ).fetchall()
    conn.close()
    current = [row for row in rows if row["is_current"] == 1]
    old = [row for row in rows if row["revision"] == 1]
    ok = (
        len(rows) >= 2
        and len(current) == 1
        and current[0]["revision"] == max(row["revision"] for row in rows)
        and "Revision marker ALPHA." in (current[0]["statement_markdown"] or "")
        and old
        and "Revision marker ALPHA." not in (old[0]["statement_markdown"] or "")
        and old[0]["examples"] >= 1
        and current[0]["examples"] >= 1
    )
    _check(checks, "revision_keeps_old_statement_and_examples", ok, [dict(row) | {"statement_markdown": None} for row in rows])
    return {"versions": len(rows)}


def _failure_check(checks: list[dict]) -> None:
    db_path = DB_DIR / "fail-test.sqlite"
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(db_path) + suffix)
        if path.exists():
            path.unlink()
    failed = import_records(
        db_path,
        normalized_dir=NORMALIZED,
        sources=["leetcode-api"],
        slug_filter={"two-sum"},
        fail_slug="two-sum",
        reports_dir=REPORTS,
    )
    conn = sqlite3.connect(db_path)
    problems_after_fail = conn.execute("SELECT COUNT(*) FROM problem").fetchone()[0]
    contents_after_fail = conn.execute("SELECT COUNT(*) FROM problem_content").fetchone()[0]
    conn.close()
    retried = import_records(
        db_path,
        normalized_dir=NORMALIZED,
        sources=["leetcode-api"],
        slug_filter={"two-sum"},
        reports_dir=REPORTS,
    )
    conn = sqlite3.connect(db_path)
    problems_after_retry = conn.execute("SELECT COUNT(*) FROM problem").fetchone()[0]
    conn.close()
    _check(
        checks,
        "injected_failure_rolls_back_then_retries",
        problems_after_fail == 0
        and contents_after_fail == 0
        and failed["status"] == "failed"
        and problems_after_retry == 1
        and retried["counts"]["problems_created"] == 1,
        {
            "after_fail": problems_after_fail,
            "after_retry": problems_after_retry,
            "fail_status": failed["status"],
        },
    )
