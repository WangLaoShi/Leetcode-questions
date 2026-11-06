"""Source adapters. Each source becomes schema 1.0 records. Editorials are dropped."""

from __future__ import annotations

import json
import re
from pathlib import Path

from qb.htmlmd import extract_images, html_to_markdown
from qb.statement import extraction_status, parse_sections
from qb.util import (
    blank_to_none,
    map_category,
    map_difficulty,
    newlines,
    sha256_file,
    slug_code,
)

_SOLUTION_MARKERS = (
    "<!-- solution:start -->",
    "## 解法",
    "## Solutions",
    "## Video Solution",
    "### 方法一",
    "### Approach 1",
)

_FRONT_MATTER = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.S)
_HEADING = re.compile(r"^#\s+\[([^\]]+)\]\((https?://[^)\s]+)\)", re.M)
_DESC = re.compile(
    r"<!--\s*description:start\s*-->(.*)<!--\s*description:end\s*-->",
    re.S,
)
_SLUG_FROM_URL = re.compile(r"/problems/([^/?#]+)/?", re.I)
_PROBLEM_DIR = re.compile(r"^\d{4}\..+")


def _source(name: str, repo_url: str, commit: str, path: str, locator: str, retrieved_at: str, file_hash: str) -> dict:
    return {
        "name": name,
        "repo_url": repo_url,
        "git_commit": commit,
        "path": path,
        "locator": locator,
        "retrieved_at": retrieved_at,
        "file_sha256": file_hash,
    }


def _suspected_implementation(code: str) -> bool:
    if not code or len(code) < 500:
        return False
    lines = []
    for line in code.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "*", "/*", "--")):
            continue
        lines.append(stripped)
    control = sum(1 for line in lines if any(k in line for k in (" for ", " while ", " if ", "for(", "while(", "if(")))
    returns = sum(1 for line in lines if line.startswith("return ") and len(line) > 14)
    return control >= 3 and returns >= 1 and len(lines) >= 30


def _build_content(
    *,
    locale: str,
    title: str | None,
    statement: str | None,
    statement_format: str,
    hints: list[str] | None,
    hints_field_present: bool,
    extra_examples: list[dict] | None,
    category: str | None,
) -> dict:
    statement = newlines(statement) if statement else None
    if statement == "":
        statement = None
    sections = parse_sections(statement)
    examples = []
    if extra_examples:
        for item in extra_examples:
            examples.append(
                {
                    "ordinal": int(item["ordinal"]),
                    "input": item.get("input"),
                    "output": item.get("output"),
                    "explanation": item.get("explanation"),
                    "images": item.get("images") or [],
                }
            )
        examples_status = "extracted" if examples else "confirmed_empty"
    else:
        examples = [
            {
                "ordinal": ex["ordinal"],
                "input": ex.get("input"),
                "output": ex.get("output"),
                "explanation": ex.get("explanation"),
                "images": [],
            }
            for ex in sections["examples"]
        ]
        parsed_ok = bool(examples) and all(ex.get("input") or ex.get("output") for ex in examples)
        if examples and parsed_ok:
            examples_status = "extracted"
        elif sections["saw_example_header"]:
            examples_status = "not_extracted"
            examples = []
        else:
            examples_status = "not_extracted"

    constraints = sections["constraints"]
    if constraints:
        constraints_status = "extracted"
    elif sections["saw_constraint_header"]:
        constraints_status = "confirmed_empty"
    else:
        constraints_status = "not_extracted"

    follow_ups = sections["follow_ups"]
    follow_status = "extracted" if follow_ups else "not_extracted"

    if hints_field_present:
        hint_values = [h.strip() for h in (hints or []) if isinstance(h, str) and h.strip()]
        hints_status = "extracted" if hint_values else "confirmed_empty"
    else:
        hint_values = []
        hints_status = "not_extracted"

    type_specific: dict = {}
    type_status = "not_applicable"
    if category == "database" or sections["sql_pres"]:
        type_specific = {"sql": {"schemas_and_samples": sections["sql_pres"]}}
        type_status = "extracted" if sections["sql_pres"] else "not_extracted"
    elif category == "pandas":
        type_specific = {"pandas": {}}
        type_status = "not_extracted"
    elif category == "shell":
        type_specific = {"shell": {}}
        type_status = "not_extracted"
    elif category == "concurrency":
        type_specific = {"concurrency": {}}
        type_status = "not_extracted"
    elif category == "javascript":
        type_specific = {"javascript": {}}
        type_status = "not_extracted"

    examples_ok = examples_status == "extracted" or not sections["saw_example_header"]
    status = extraction_status(statement, sections, examples_ok)
    if statement and extra_examples and "Example 1:" in (statement or "") and examples:
        # neenza often leaves example bodies only in the structured field
        if not re.search(r"Input:|输入：", statement):
            blocks = [statement.rstrip(), "", "## Examples"]
            for ex in examples:
                blocks.append(f"### Example {ex['ordinal']}")
                if ex.get("input"):
                    blocks.append(f"Input: {ex['input']}")
                if ex.get("output"):
                    blocks.append(f"Output: {ex['output']}")
                if ex.get("explanation"):
                    blocks.append(f"Explanation: {ex['explanation']}")
                blocks.append("")
            statement = "\n".join(blocks).strip()

    return {
        "locale": locale,
        "title": title,
        "statement_markdown": statement,
        "statement_format": statement_format,
        "constraints": constraints,
        "follow_ups": follow_ups,
        "examples": examples,
        "hints": hint_values,
        "type_specific": type_specific,
        "field_status": {
            "statement": "extracted" if statement else "missing" if status == "missing" else "not_extracted",
            "constraints": constraints_status,
            "follow_ups": follow_status,
            "examples": examples_status,
            "hints": hints_status,
            "type_specific": type_status,
        },
        "extraction_status": status,
    }


def _starter_codes(snippets) -> tuple[list[dict], str]:
    codes = []
    if snippets is None:
        return codes, "not_extracted"
    if isinstance(snippets, dict):
        items = [{"lang": k, "langSlug": k, "code": v} for k, v in snippets.items()]
    elif isinstance(snippets, list):
        items = snippets
    else:
        return codes, "not_extracted"
    if not items:
        return codes, "confirmed_empty"
    for item in items:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        if not isinstance(code, str):
            continue
        lang = blank_to_none(item.get("langSlug") or item.get("langsSlug") or item.get("lang"))
        if not lang:
            continue
        codes.append(
            {
                "language": lang,
                "language_name": item.get("lang") or lang,
                "template": newlines(code) or "",
                "suspected_implementation": _suspected_implementation(code),
            }
        )
    return codes, "extracted" if codes else "confirmed_empty"


def _assets_from(statement: str | None, extra_urls: list[str] | None = None) -> list[dict]:
    assets = extract_images(statement)
    seen = {a["url"] for a in assets}
    for url in extra_urls or []:
        if url and url not in seen:
            seen.add(url)
            assets.append({"url": url, "alt": ""})
    return [{"original_url": a["url"], "alt": a.get("alt") or "", "media_type": _media_type(a["url"])} for a in assets]


def _media_type(url: str) -> str:
    path = url.split("?")[0].lower()
    for ext, kind in (
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".gif", "image/gif"),
        (".webp", "image/webp"),
        (".svg", "image/svg+xml"),
    ):
        if path.endswith(ext):
            return kind
    return "application/octet-stream"


def _record(
    *,
    site: str,
    platform_question_id: str | None,
    display_id: str | None,
    slug: str | None,
    url: str | None,
    category_raw,
    difficulty_raw,
    is_paid_only,
    content: dict,
    tags: list[dict],
    starters: list[dict],
    starter_status: str,
    assets: list[dict],
    source: dict,
    adapter_issues: list[dict],
) -> dict:
    content["field_status"]["starter_codes"] = starter_status
    if content["field_status"]["statement"] == "missing":
        content["field_status"]["statement"] = "not_extracted"
    return {
        "schema_version": "1.0",
        "identity": {
            "platform": "leetcode",
            "site": site,
            "platform_question_id": platform_question_id,
            "display_id": display_id,
            "slug": slug,
            "url": url,
        },
        "category": map_category(category_raw),
        "difficulty": map_difficulty(difficulty_raw),
        "is_paid_only": is_paid_only,
        "raw": {
            "category": category_raw,
            "difficulty": difficulty_raw,
            "is_paid_only": is_paid_only,
        },
        "contents": [content],
        "tags": tags,
        "starter_codes": starters,
        "assets": assets,
        "sources": [source],
        "adapter_issues": adapter_issues,
    }


def _parse_neenza_examples(examples) -> list[dict]:
    parsed = []
    if not isinstance(examples, list):
        return parsed
    for index, item in enumerate(examples, start=1):
        if not isinstance(item, dict):
            continue
        text = item.get("example_text") or ""
        from qb.statement import parse_example_block

        body = parse_example_block(text)
        ordinal = item.get("example_num") or index
        try:
            ordinal = int(ordinal)
        except (TypeError, ValueError):
            ordinal = index
        images = [u for u in (item.get("images") or []) if isinstance(u, str) and u.strip()]
        parsed.append(
            {
                "ordinal": ordinal,
                "input": body.get("input"),
                "output": body.get("output"),
                "explanation": body.get("explanation"),
                "images": images,
            }
        )
    return parsed


def adapt_neenza_file(path: Path, commit: str, retrieved_at: str, file_hash: str | None = None) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rel = "problems/" + path.name
    digest = file_hash or sha256_file(path)
    issues = []
    if data.get("solution") or data.get("solutions"):
        issues.append(
            {
                "issue_type": "editorial_excluded",
                "severity": "info",
                "detail": "solution/editorial field present in source and not imported",
            }
        )
    examples = _parse_neenza_examples(data.get("examples"))
    description = data.get("description")
    if isinstance(description, str) and re.search(r"<p>|<pre>|<code>", description):
        statement_format = "html"
        statement = html_to_markdown(description)
    else:
        statement_format = "markdown"
        statement = description if isinstance(description, str) else None
    content = _build_content(
        locale="en",
        title=blank_to_none(data.get("title")),
        statement=statement,
        statement_format=statement_format,
        hints=data.get("hints") if isinstance(data.get("hints"), list) else [],
        hints_field_present="hints" in data,
        extra_examples=examples if "examples" in data else None,
        category=None,
    )
    if "constraints" in data and isinstance(data.get("constraints"), list) and data["constraints"] and not content["constraints"]:
        content["constraints"] = [c.strip() for c in data["constraints"] if isinstance(c, str) and c.strip()]
        content["field_status"]["constraints"] = "extracted" if content["constraints"] else "confirmed_empty"
    elif "constraints" in data and not data.get("constraints") and not content["constraints"]:
        content["field_status"]["constraints"] = "confirmed_empty"
    if "follow_ups" in data and isinstance(data.get("follow_ups"), list):
        if data["follow_ups"] and not content["follow_ups"]:
            content["follow_ups"] = [c.strip() for c in data["follow_ups"] if isinstance(c, str) and c.strip()]
        if content["follow_ups"]:
            content["field_status"]["follow_ups"] = "extracted"
        elif not data["follow_ups"]:
            content["field_status"]["follow_ups"] = "confirmed_empty"
    starters, starter_status = _starter_codes(data.get("code_snippets"))
    tags = []
    for topic in data.get("topics") or []:
        if isinstance(topic, str) and topic.strip():
            tags.append({"source": "leetcode-topic", "code": slug_code(topic), "name": topic.strip()})
    extra_urls = []
    for ex in examples:
        extra_urls.extend(ex.get("images") or [])
    slug = blank_to_none(data.get("problem_slug"))
    url = f"https://leetcode.com/problems/{slug}/" if slug else None
    return _record(
        site="leetcode.com",
        platform_question_id=blank_to_none(str(data.get("problem_id"))) if data.get("problem_id") is not None else None,
        display_id=blank_to_none(str(data.get("frontend_id"))) if data.get("frontend_id") is not None else None,
        slug=slug,
        url=url,
        category_raw=None,
        difficulty_raw=data.get("difficulty"),
        is_paid_only=None,
        content=content,
        tags=tags,
        starters=starters,
        starter_status=starter_status,
        assets=_assets_from(content.get("statement_markdown"), extra_urls),
        source=_source(
            "neenza",
            "https://github.com/neenza/leetcode-problems",
            commit,
            rel,
            f"file:{path.name}",
            retrieved_at,
            digest,
        ),
        adapter_issues=issues,
    )


def adapt_api_question(question: dict, commit: str, retrieved_at: str, file_hash: str, locator: str) -> dict:
    url = blank_to_none(question.get("url"))
    slug = blank_to_none(question.get("titleSlug"))
    if not slug and url:
        matched = _SLUG_FROM_URL.search(url)
        slug = matched.group(1) if matched else None
    if not url and slug:
        url = f"https://leetcode.com/problems/{slug}/"
    issues = []
    if question.get("solution"):
        issues.append(
            {
                "issue_type": "editorial_excluded",
                "severity": "info",
                "detail": "GraphQL solution object present and not imported",
            }
        )
    raw_content = question.get("content")
    if isinstance(raw_content, str) and raw_content.strip():
        statement = html_to_markdown(raw_content)
        statement_format = "html"
    else:
        statement = None
        statement_format = "html"
    paid = question.get("isPaidOnly")
    if not isinstance(paid, bool):
        paid = None
    content = _build_content(
        locale="en",
        title=blank_to_none(question.get("title")),
        statement=statement,
        statement_format=statement_format,
        hints=question.get("hints") if isinstance(question.get("hints"), list) else [],
        hints_field_present="hints" in question,
        extra_examples=None,
        category=map_category(question.get("categoryTitle")),
    )
    if paid is True and not statement:
        content["extraction_status"] = "missing"
        content["field_status"]["statement"] = "not_extracted"
        issues.append(
            {
                "issue_type": "paid_statement_absent",
                "severity": "info",
                "detail": "isPaidOnly and this snapshot has no statement; premium text was not fetched",
            }
        )
    starters, starter_status = _starter_codes(question.get("codeSnippets"))
    tags = []
    for topic in question.get("topicTags") or []:
        name = topic.get("name") if isinstance(topic, dict) else None
        if name and str(name).strip():
            tags.append({"source": "leetcode-topic", "code": slug_code(str(name)), "name": str(name).strip()})
    pid = question.get("questionId")
    fid = question.get("questionFrontendId")
    return _record(
        site="leetcode.com",
        platform_question_id=blank_to_none(str(pid)) if pid is not None else None,
        display_id=blank_to_none(str(fid)) if fid is not None else None,
        slug=slug,
        url=url,
        category_raw=question.get("categoryTitle"),
        difficulty_raw=question.get("difficulty"),
        is_paid_only=paid,
        content=content,
        tags=tags,
        starters=starters,
        starter_status=starter_status,
        assets=_assets_from(content.get("statement_markdown")),
        source=_source(
            "leetcode-api",
            "https://github.com/noworneverev/leetcode-api",
            commit,
            "data/leetcode_questions.json",
            locator,
            retrieved_at,
            file_hash,
        ),
        adapter_issues=issues,
    )


def _front_matter(text: str) -> dict:
    matched = _FRONT_MATTER.match(text)
    if not matched:
        return {"difficulty": None, "tags": []}
    body = matched.group(1)
    difficulty = None
    diff = re.search(r"^difficulty:\s*(.+)$", body, re.M)
    if diff:
        difficulty = diff.group(1).strip().strip('"').strip("'")
    tags = []
    tag_block = re.search(r"^tags:\s*\n((?:\s*-\s*.+\n?)*)", body, re.M)
    if tag_block:
        for line in tag_block.group(1).splitlines():
            item = re.sub(r"^\s*-\s*", "", line).strip()
            if item:
                tags.append(item)
    return {"difficulty": difficulty, "tags": tags}


def _category_from_doocs_tags(tags: list[str]) -> str | None:
    folded = {t.strip().lower() for t in tags}
    if folded & {"数据库", "database"}:
        return "Database"
    if folded & {"shell"}:
        return "Shell"
    if folded & {"pandas"}:
        return "pandas"
    if folded & {"concurrency", "多线程"}:
        return "Concurrency"
    if folded & {"javascript"}:
        return "JavaScript"
    return None


def adapt_doocs_file(path: Path, repo_root: Path, commit: str, retrieved_at: str) -> tuple[dict | None, dict | None]:
    """Return (record, failure). Index files are failures with kind skipped_non_problem."""
    rel = path.relative_to(repo_root).as_posix()
    parent = path.parent.name
    if path.name not in ("README.md", "README_EN.md") or not _PROBLEM_DIR.match(parent):
        return None, {
            "path": rel,
            "reason": "skipped_non_problem",
            "detail": "not a per-problem README",
        }
    text = path.read_text(encoding="utf-8-sig")
    if any(marker in text and "<!-- description:end -->" in text and marker in text.split("<!-- description:end -->", 1)[-1] for marker in ("## 解法", "## Solutions")):
        pass
    desc = _DESC.search(text)
    heading = _HEADING.search(text)
    if not desc or not heading:
        return None, {
            "path": rel,
            "reason": "description_boundary_unconfirmed",
            "detail": "missing description markers or title link; file not imported",
        }
    body = desc.group(1)
    if "<!-- solution:start -->" in body or "## 解法" in body or "## Solutions" in body:
        return None, {
            "path": rel,
            "reason": "description_contains_solution_marker",
            "detail": "refused to import because the description region includes a solution marker",
        }
    label, url = heading.group(1).strip(), heading.group(2).strip()
    display_id = None
    title = label
    split = re.match(r"^(\d+)\.\s+(.*)$", label)
    if split:
        display_id = split.group(1)
        title = split.group(2).strip()
    else:
        split = re.match(r"^(.+?)\.\s+(\D.*)$", label)
        if split:
            display_id = split.group(1).strip()
            title = split.group(2).strip()
    slug_match = _SLUG_FROM_URL.search(url)
    slug = slug_match.group(1) if slug_match else None
    host = re.match(r"https?://([^/]+)/", url)
    host_name = host.group(1).lower() if host else ""
    if host_name.endswith("leetcode.cn"):
        site = "leetcode.cn"
    elif host_name.endswith("leetcode.com"):
        site = "leetcode.com"
    else:
        return None, {
            "path": rel,
            "reason": "unknown_problem_host",
            "detail": url,
        }
    locale = "en" if path.name == "README_EN.md" else "zh-CN"
    meta = _front_matter(text)
    category_raw = _category_from_doocs_tags(meta["tags"])
    statement = html_to_markdown(body)
    content = _build_content(
        locale=locale,
        title=blank_to_none(title),
        statement=statement,
        statement_format="html",
        hints=None,
        hints_field_present=False,
        extra_examples=None,
        category=map_category(category_raw) if category_raw else None,
    )
    tags = [
        {"source": "doocs", "code": slug_code(name), "name": name}
        for name in meta["tags"]
        if name.strip()
    ]
    digest = sha256_file(path)
    record = _record(
        site=site,
        platform_question_id=None,
        display_id=display_id,
        slug=slug,
        url=url,
        category_raw=category_raw,
        difficulty_raw=meta.get("difficulty"),
        is_paid_only=None,
        content=content,
        tags=tags,
        starters=[],
        starter_status="not_extracted",
        assets=_assets_from(content.get("statement_markdown")),
        source=_source(
            "doocs",
            "https://github.com/doocs/leetcode",
            commit,
            rel,
            "marker:description",
            retrieved_at,
            digest,
        ),
        adapter_issues=[],
    )
    return record, None


def contains_forbidden_solution(record: dict) -> str | None:
    for content in record.get("contents") or []:
        statement = content.get("statement_markdown") or ""
        for marker in _SOLUTION_MARKERS:
            if marker in statement:
                return marker
    return None
