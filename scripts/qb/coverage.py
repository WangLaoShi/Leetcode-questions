"""Coverage and quality reports after a committed import."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from qb.db import connect, table_counts
from qb.util import NORMALIZED, REPORTS, utc_now, write_json


def write_coverage(db_path: Path) -> dict:
    conn = connect(db_path)
    problems = conn.execute("SELECT COUNT(*) FROM problem").fetchone()[0]
    by_category = dict(conn.execute("SELECT COALESCE(category, 'unknown'), COUNT(*) FROM problem GROUP BY 1"))
    by_difficulty = dict(conn.execute("SELECT COALESCE(difficulty, 'unknown'), COUNT(*) FROM problem GROUP BY 1"))
    by_locale = dict(
        conn.execute(
            "SELECT locale || ':' || site, COUNT(*) FROM problem_content c JOIN problem_source_identity i ON i.id=c.source_identity_id WHERE c.is_current=1 GROUP BY 1"
        )
    )
    expected = {}
    with (NORMALIZED / "leetcode-api.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            expected[record["identity"]["slug"]] = {
                "display_id": record["identity"].get("display_id"),
                "paid": record.get("is_paid_only"),
                "has_statement": bool(record["contents"][0].get("statement_markdown")),
            }
    present = {
        row["slug"]
        for row in conn.execute(
            "SELECT slug FROM problem_source_identity WHERE site='leetcode.com' AND slug IS NOT NULL"
        )
    }
    missing = sorted(set(expected) - present)
    extra = sorted(present - set(expected))
    field_gaps = dict(
        conn.execute(
            """
            SELECT json_extract(field_status_json, '$.statement') || '|' || extraction_status, COUNT(*)
            FROM problem_content WHERE is_current=1 GROUP BY 1
            """
        )
    )
    example_status = dict(
        conn.execute(
            """
            SELECT json_extract(field_status_json, '$.examples'), COUNT(*)
            FROM problem_content WHERE is_current=1 GROUP BY 1
            """
        )
    )
    hint_status = dict(
        conn.execute(
            """
            SELECT json_extract(field_status_json, '$.hints'), COUNT(*)
            FROM problem_content WHERE is_current=1 GROUP BY 1
            """
        )
    )
    starter_status = dict(
        conn.execute(
            """
            SELECT json_extract(field_status_json, '$.starter_codes'), COUNT(*)
            FROM problem_content WHERE is_current=1 GROUP BY 1
            """
        )
    )
    issues = dict(conn.execute("SELECT issue_type, COUNT(*) FROM data_issue GROUP BY 1"))
    suspected = conn.execute("SELECT COUNT(*) FROM starter_code WHERE suspected_implementation=1").fetchone()[0]
    leaks = conn.execute(
        """
        SELECT COUNT(*) FROM problem_content
        WHERE IFNULL(statement_markdown,'') LIKE '%<!-- solution:start -->%'
           OR IFNULL(statement_markdown,'') LIKE '%## 解法%'
           OR IFNULL(statement_markdown,'') LIKE '%## Solutions%'
           OR IFNULL(statement_markdown,'') LIKE '%## Video Solution%'
        """
    ).fetchone()[0]
    cross_path = REPORTS / "cross-site-candidates.jsonl"
    cross = 0
    with cross_path.open("w", encoding="utf-8") as handle:
        for row in conn.execute(
            """
            SELECT c.slug, c.display_id, c.problem_id AS com_problem_id, n.problem_id AS cn_problem_id
            FROM problem_source_identity c
            JOIN problem_source_identity n
              ON c.platform=n.platform AND c.slug=n.slug AND c.display_id=n.display_id
            WHERE c.site='leetcode.com' AND n.site='leetcode.cn'
            ORDER BY c.display_id
            """
        ):
            handle.write(
                json.dumps(
                    {
                        "slug": row["slug"],
                        "display_id": row["display_id"],
                        "leetcode_com_problem_id": row["com_problem_id"],
                        "leetcode_cn_problem_id": row["cn_problem_id"],
                        "status": "pending_verification",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            cross += 1
    normalize_failures = 0
    failure_file = REPORTS / "normalize-failures.jsonl"
    reasons = Counter()
    if failure_file.exists():
        for line in failure_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            normalize_failures += 1
            reasons[json.loads(line).get("reason")] += 1
    coverage = {
        "generated_at": utc_now(),
        "problems": problems,
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "current_content_by_locale_site": by_locale,
        "expected_leetcode_com_slugs": len(expected),
        "missing_from_leetcode_com": missing,
        "leetcode_com_slugs_not_in_api_snapshot": extra[:50],
        "leetcode_com_slugs_not_in_api_snapshot_count": len(extra),
        "statement_field_status": field_gaps,
        "example_field_status": example_status,
        "hint_field_status": hint_status,
        "starter_field_status": starter_status,
        "cross_site_candidates_pending": cross,
        "note": "Empty statement on a paid problem is source-not-provided. not_extracted on doocs hints and starter codes means this pipeline did not have a source field. confirmed_empty means the source field existed and was empty.",
    }
    quality = {
        "generated_at": utc_now(),
        "table_counts": table_counts(conn),
        "issues": issues,
        "suspected_implementations": suspected,
        "editorial_markers_in_statements": leaks,
        "normalize_failures": normalize_failures,
        "normalize_failure_reasons": dict(reasons),
        "foreign_key_check": len(conn.execute("PRAGMA foreign_key_check").fetchall()),
    }
    write_json(REPORTS / "coverage.json", coverage)
    write_json(REPORTS / "quality.json", quality)
    known = REPORTS / "known-issues.md"
    known.write_text(
        "\n".join(
            [
                "# 已知问题",
                "",
                f"- 生成时间：{coverage['generated_at']}",
                f"- leetcode.com 预期 {len(expected)} 题，库中缺失 {len(missing)}。",
                f"- 跨站候选 {cross} 条，状态为待核实，没有自动合并。",
                f"- 题解标记进入题干的数量：{leaks}。",
                f"- 疑似完整实现的模板：{suspected}。",
                f"- 清洗失败：{normalize_failures}。",
                "- 付费题在 leetcode-api 缓存中的正文为空，没有向 LeetCode 再抓会员内容。若 doocs 快照里已有对应题干，只作为 doocs 来源另存，不回填到接口记录。",
                "- 三个快照都没有非数字展示题号。",
                "- 图片只保存 URL，没有下载文件。",
                "- 运行库是 SQLite。PostgreSQL 脚本未在本机执行。",
                "- neenza 没有许可证文件。leetcode-api 的 MIT 与 doocs 的 CC BY-SA 不自动覆盖 LeetCode 题干。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    conn.close()
    return coverage
