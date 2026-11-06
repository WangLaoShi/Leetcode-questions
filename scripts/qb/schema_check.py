"""Validator aligned with schemas/problem.schema.json. Stdlib only."""

from __future__ import annotations

from qb.util import CATEGORIES, DIFFICULTIES

EXTRACTION = {"extracted", "partial", "needs_review", "missing"}
FIELD_STATUS = {"extracted", "confirmed_empty", "not_extracted", "not_applicable"}
LOCALES = {"en", "zh-CN"}


def _err(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def validate_problem(record: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record: must be an object"]
    if record.get("schema_version") != "1.0":
        _err(errors, "schema_version", "must be 1.0")
    ident = record.get("identity")
    if not isinstance(ident, dict):
        _err(errors, "identity", "must be an object")
    else:
        for key in ("platform", "site"):
            if not isinstance(ident.get(key), str) or not ident.get(key).strip():
                _err(errors, f"identity.{key}", "required string")
        ids = [ident.get("platform_question_id"), ident.get("display_id"), ident.get("slug")]
        if not any(isinstance(v, str) and v.strip() for v in ids):
            _err(errors, "identity", "need platform_question_id, display_id, or slug")
        for key in ("platform_question_id", "display_id", "slug", "url"):
            value = ident.get(key)
            if value is not None and not isinstance(value, str):
                _err(errors, f"identity.{key}", "must be string or null")
            if isinstance(value, str) and value.strip() == "":
                _err(errors, f"identity.{key}", "empty string is not an identifier")
    category = record.get("category")
    if category is not None and category not in CATEGORIES:
        _err(errors, "category", f"invalid enum {category!r}")
    difficulty = record.get("difficulty")
    if difficulty is not None and difficulty not in DIFFICULTIES:
        _err(errors, "difficulty", f"invalid enum {difficulty!r}")
    paid = record.get("is_paid_only")
    if paid is not None and not isinstance(paid, bool):
        _err(errors, "is_paid_only", "must be boolean or null")
    contents = record.get("contents")
    if not isinstance(contents, list) or not contents:
        _err(errors, "contents", "must be a non-empty array")
    else:
        for i, content in enumerate(contents):
            _validate_content(content, f"contents[{i}]", errors)
    for key in ("tags", "starter_codes", "assets", "sources"):
        if not isinstance(record.get(key), list):
            _err(errors, key, "must be an array")
    if isinstance(record.get("sources"), list) and not record["sources"]:
        _err(errors, "sources", "at least one source is required")
    return errors


def _validate_content(content, path: str, errors: list[str]) -> None:
    if not isinstance(content, dict):
        _err(errors, path, "must be an object")
        return
    if content.get("locale") not in LOCALES:
        _err(errors, f"{path}.locale", "must be en or zh-CN")
    title = content.get("title")
    if title is not None and not isinstance(title, str):
        _err(errors, f"{path}.title", "must be string or null")
    statement = content.get("statement_markdown")
    if statement is not None and not isinstance(statement, str):
        _err(errors, f"{path}.statement_markdown", "must be string or null")
    status = content.get("extraction_status")
    if status not in EXTRACTION:
        _err(errors, f"{path}.extraction_status", "invalid")
    if status in ("extracted", "partial") and not statement:
        _err(errors, f"{path}.statement_markdown", "required when extraction succeeded")
    for key in ("constraints", "follow_ups", "examples", "hints"):
        if not isinstance(content.get(key), list):
            _err(errors, f"{path}.{key}", "must be an array")
    if not isinstance(content.get("type_specific"), dict):
        _err(errors, f"{path}.type_specific", "must be an object")
    field_status = content.get("field_status")
    if not isinstance(field_status, dict):
        _err(errors, f"{path}.field_status", "must be an object")
    else:
        for key, value in field_status.items():
            if value not in FIELD_STATUS:
                _err(errors, f"{path}.field_status.{key}", "invalid status")
    for j, example in enumerate(content.get("examples") or []):
        if not isinstance(example, dict):
            _err(errors, f"{path}.examples[{j}]", "must be an object")
            continue
        if not isinstance(example.get("ordinal"), int):
            _err(errors, f"{path}.examples[{j}].ordinal", "must be an integer")
        for key in ("input", "output", "explanation"):
            value = example.get(key)
            if value is not None and not isinstance(value, str):
                _err(errors, f"{path}.examples[{j}].{key}", "must be string or null")
