"""Count fields and coverage in the raw snapshots. Does not import a database."""

from __future__ import annotations

import json
import os
import re
from collections import Counter

from qb.util import RAW, REPORTS, sha256_file, utc_now, write_json

_SLUG = re.compile(r"/problems/([^/?#]+)/?")
_HOST = re.compile(r"https?://([^/]+)/")


def _summarize_value(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int) and not isinstance(value, bool):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def build_inventory() -> dict:
    neenza = _inventory_neenza()
    api = _inventory_api()
    doocs = _inventory_doocs()
    report = {
        "generated_at": utc_now(),
        "note": "Counts describe the snapshots on disk. Declared repository coverage is not treated as the live platform total.",
        "sources": {"neenza": neenza, "leetcode-api": api, "doocs": doocs},
        "gaps": [
            "Neither snapshot contains a non-numeric display id (no LCP / 面试题 ids in these trees).",
            "leetcode-api paid problems in this cache have empty statement HTML. Premium text was not requested.",
            "neenza has no category and no is_paid_only field.",
            "doocs sparse checkout has no starter templates and no official hint field. Hints are not taken from solution sections.",
            "doocs Chinese pages link to leetcode.cn and are stored as a separate site until cross-site review.",
            "Image binaries are referenced by URL and are not downloaded.",
        ],
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    write_json(REPORTS / "source-inventory.json", report)
    print(
        f"inventory neenza={neenza['files']} api={api['questions']} doocs_md={doocs['markdown_files']}",
        flush=True,
    )
    return report


def _inventory_neenza() -> dict:
    root = RAW / "neenza" / "repo" / "problems"
    files = sorted(root.glob("*.json"))
    field_types = {}
    present = Counter()
    difficulty = Counter()
    empty_title = empty_description = with_solution = id_diff = 0
    hint_empty = example_empty = 0
    description_html = description_md = 0
    slugs = set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for key, value in data.items():
            present[key] += 1
            field_types.setdefault(key, set()).add(_summarize_value(value))
        if not (data.get("title") or "").strip():
            empty_title += 1
        description = data.get("description") or ""
        if not str(description).strip():
            empty_description += 1
        elif re.search(r"<p>|<pre>|<code>", description):
            description_html += 1
        else:
            description_md += 1
        if data.get("solution") or data.get("solutions"):
            with_solution += 1
        difficulty[data.get("difficulty")] += 1
        if str(data.get("problem_id")) != str(data.get("frontend_id")):
            id_diff += 1
        if not data.get("hints"):
            hint_empty += 1
        if not data.get("examples"):
            example_empty += 1
        if data.get("problem_slug"):
            slugs.add(data["problem_slug"])
    merged = RAW / "neenza" / "repo" / "merged_problems.json"
    return {
        "files": len(files),
        "unique_slugs": len(slugs),
        "duplicate_slugs": len(files) - len(slugs),
        "merged_problems_json_bytes": merged.stat().st_size if merged.exists() else None,
        "merged_problems_json_sha256": sha256_file(merged) if merged.exists() else None,
        "merged_file_role": "aggregate duplicate of problems/; not imported",
        "fields": {key: sorted(types) for key, types in sorted(field_types.items())},
        "field_present_count": dict(present),
        "difficulty": dict(difficulty),
        "empty_title": empty_title,
        "empty_description": empty_description,
        "description_looks_html": description_html,
        "description_looks_markdown_or_text": description_md,
        "rows_with_solution_field_excluded_from_import": with_solution,
        "internal_id_differs_from_frontend_id": id_diff,
        "empty_hints": hint_empty,
        "empty_examples": example_empty,
        "statement_format": "Mostly plain text or Markdown. Examples, constraints, follow-ups, and hints are separate fields. The description often omits example bodies.",
        "category_field": False,
        "is_paid_only_field": False,
    }


def _difficulty_pass(files) -> dict:
    difficulty = Counter()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        difficulty[data.get("difficulty")] += 1
    return dict(difficulty)


def _inventory_api() -> dict:
    path = RAW / "leetcode-api" / "repo" / "data" / "leetcode_questions.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    field_types = {}
    present = Counter()
    category = Counter()
    difficulty = Counter()
    paid = 0
    empty_content = 0
    empty_title = 0
    missing_slug = 0
    html = 0
    id_diff = 0
    with_solution = 0
    hint_empty = 0
    snippets_empty = 0
    images = 0
    frontend = []
    for item in data:
        question = item["data"]["question"]
        for key, value in question.items():
            present[key] += 1
            field_types.setdefault(key, set()).add(_summarize_value(value))
        category[question.get("categoryTitle")] += 1
        difficulty[question.get("difficulty")] += 1
        if question.get("isPaidOnly"):
            paid += 1
        content = question.get("content") or ""
        if not str(content).strip():
            empty_content += 1
        elif "<" in content and ">" in content:
            html += 1
        if not (question.get("title") or "").strip():
            empty_title += 1
        url = question.get("url") or ""
        if not _SLUG.search(url) and not question.get("titleSlug"):
            missing_slug += 1
        if str(question.get("questionId")) != str(question.get("questionFrontendId")):
            id_diff += 1
        if question.get("solution"):
            with_solution += 1
        if not question.get("hints"):
            hint_empty += 1
        if not question.get("codeSnippets"):
            snippets_empty += 1
        if "<img" in content:
            images += 1
        frontend.append(str(question.get("questionFrontendId")))
    non_numeric = sum(1 for value in frontend if not value.isdigit())
    return {
        "file": "data/leetcode_questions.json",
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "questions": len(data),
        "duplicate_internal_ids": len(frontend) - len(set(str(item["data"]["question"].get("questionId")) for item in data)),
        "duplicate_frontend_ids": len(frontend) - len(set(frontend)),
        "non_numeric_frontend_ids": non_numeric,
        "fields": {key: sorted(types) for key, types in sorted(field_types.items())},
        "field_present_count": dict(present),
        "category": dict(category),
        "difficulty": dict(difficulty),
        "paid_only": paid,
        "empty_content": empty_content,
        "empty_content_equals_paid": empty_content == paid,
        "empty_title": empty_title,
        "missing_slug": missing_slug,
        "content_html": html,
        "internal_id_differs_from_frontend_id": id_diff,
        "rows_with_solution_object_excluded_from_import": with_solution,
        "empty_hints": hint_empty,
        "empty_code_snippets": snippets_empty,
        "content_with_img": images,
        "statement_format": "HTML in question.content. Examples and constraints are inside the HTML, not separate fields. hints is a separate array. codeSnippets are starter templates. solution is an editorial object and is excluded.",
        "live_api_note": "A public GET /problem/two-sum and GET /stats were saved under raw/leetcode-api/api-samples. The detail payload matches the unwrapped question object in the JSON cache, including a solution object that this pipeline drops. /stats total matched the cache count at sample time.",
    }


def _inventory_doocs() -> dict:
    repo = RAW / "doocs" / "repo"
    solution = repo / "solution"
    locales = Counter()
    hosts = Counter()
    difficulty = Counter()
    missing_marker = 0
    non_problem = 0
    problem_files = 0
    for dirpath, _, files in os.walk(solution):
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            parent = os.path.basename(dirpath)
            if name not in ("README.md", "README_EN.md") or not re.match(r"^\d{4}\.", parent):
                non_problem += 1
                continue
            problem_files += 1
            locales["en" if name == "README_EN.md" else "zh-CN"] += 1
            with open(path, encoding="utf-8-sig") as handle:
                text = handle.read(12000)
            if "<!-- description:start -->" not in text or "<!-- description:end -->" not in text:
                missing_marker += 1
            host = _HOST.search(text)
            if host:
                hosts[host.group(1).lower()] += 1
            diff = re.search(r"^difficulty:\s*(.+)$", text, re.M)
            if diff:
                difficulty[diff.group(1).strip()] += 1
    return {
        "checkout": "sparse, depth 1, README and README_EN only",
        "markdown_files": problem_files + non_problem,
        "problem_readmes": problem_files,
        "non_problem_markdown": non_problem,
        "locales": dict(locales),
        "link_hosts_in_first_12kb": dict(hosts),
        "front_matter_difficulty": dict(difficulty),
        "missing_description_markers_in_first_12kb": missing_marker,
        "starter_code_files_checked_out": 0,
        "statement_format": "YAML front matter, then HTML inside <!-- description:start --> ... <!-- description:end -->. Solution sections sit after that marker and are not imported. Code fences inside the description are examples or schemas, not answers.",
        "fields_observed": ["front matter difficulty", "front matter tags", "title link", "description HTML"],
        "hints_field": False,
        "official_internal_id": False,
    }
