"""Split a statement into examples, constraints, and follow-ups.

The full statement is always kept. Structured fields are a supplement.
Chinese 「提示」 is the constraint heading used by LeetCode / doocs, not an editorial hint.
"""

from __future__ import annotations

import re

_HEADER_PREFIX = re.compile(r"^[#>*\-\s]*")
_MD_MARK = re.compile(r"[*`]+")

_EXAMPLE = re.compile(r"^(?:example|示例)\s*(\d+)\s*[:：]?\s*$", re.I)
_CONSTRAINT = re.compile(r"^(?:constraints|约束|提示)\s*[:：]?\s*$", re.I)
_FOLLOW = re.compile(r"^(?:follow-?up|进阶)\s*[:：]\s*(.*)$", re.I)
_FIELD = re.compile(
    r"^(input|输入|output|输出|explanation|解释)\s*[:：]\s*(.*)$",
    re.I,
)


def _plain_line(line: str) -> str:
    text = line.strip()
    text = _HEADER_PREFIX.sub("", text)
    text = text.replace("**", "").replace("__", "")
    text = _MD_MARK.sub("", text)
    return text.strip()


def _join(parts: list[str]) -> str | None:
    text = "\n".join(parts).strip()
    return text or None


def parse_example_block(text: str) -> dict:
    mode = None
    buckets = {"in": [], "out": [], "ex": []}
    for raw in text.splitlines():
        line = _plain_line(raw)
        if not line or line == "```":
            if mode:
                buckets[mode].append("")
            continue
        matched = _FIELD.match(line)
        if matched:
            key = matched.group(1).lower()
            rest = matched.group(2).strip()
            if key in ("input", "输入"):
                mode = "in"
            elif key in ("output", "输出"):
                mode = "out"
            else:
                mode = "ex"
            buckets[mode] = [rest] if rest else []
            continue
        if mode:
            buckets[mode].append(raw.strip())
    return {
        "input": _join(buckets["in"]),
        "output": _join(buckets["out"]),
        "explanation": _join(buckets["ex"]),
    }


def parse_sections(statement: str | None) -> dict:
    """Return structured supplements. Does not remove text from the statement."""
    result = {
        "constraints": [],
        "follow_ups": [],
        "examples": [],
        "sql_pres": [],
        "saw_example_header": False,
        "saw_constraint_header": False,
    }
    if not statement:
        return result

    lines = statement.split("\n")
    sections: list[tuple[str, list[str]]] = [("body", [])]
    follow_inline: list[str] = []

    def push(kind: str):
        sections.append((kind, []))

    for raw in lines:
        plain = _plain_line(raw)
        if plain == "```":
            sections[-1][1].append(raw)
            continue
        if _EXAMPLE.match(plain):
            result["saw_example_header"] = True
            push("example")
            sections[-1][1].append(raw)
            continue
        if _CONSTRAINT.match(plain):
            result["saw_constraint_header"] = True
            push("constraints")
            continue
        follow = _FOLLOW.match(plain)
        if follow:
            push("follow")
            if follow.group(1).strip():
                follow_inline.append(follow.group(1).strip())
                sections[-1][1].append(follow.group(1).strip())
            continue
        sections[-1][1].append(raw)

    ordinal = 0
    for kind, chunk in sections:
        text = "\n".join(chunk).strip()
        if kind == "example":
            ordinal += 1
            parsed = parse_example_block(text)
            parsed["ordinal"] = ordinal
            result["examples"].append(parsed)
        elif kind == "constraints":
            items = []
            for line in chunk:
                plain = _plain_line(line)
                if not plain or plain == "```":
                    continue
                plain = re.sub(r"^(?:[-*]|\d+\.)\s+", "", plain).strip()
                if plain:
                    items.append(plain)
            result["constraints"].extend(items)
        elif kind == "follow":
            body = "\n".join(
                _plain_line(line) for line in chunk if _plain_line(line) and _plain_line(line) != "```"
            ).strip()
            if body:
                result["follow_ups"].append(body)

    # ASCII / markdown table schemas live in fenced blocks.
    fences = re.findall(r"```(.*?)```", statement, flags=re.S)
    for fence in fences:
        if re.search(r"\+[-=+]+\+", fence) or re.search(r"列名|Column Name", fence, re.I):
            result["sql_pres"].append(fence.strip())
    return result


def field_status_for_list(values: list, saw_header: bool, source_had_field: bool | None) -> str:
    if values:
        return "extracted"
    if source_had_field is True:
        return "confirmed_empty"
    if saw_header:
        return "not_extracted"
    if source_had_field is False:
        return "not_extracted"
    return "not_extracted"


def extraction_status(statement: str | None, sections: dict, examples_ok: bool) -> str:
    if not statement:
        return "missing"
    if sections["saw_example_header"] and not examples_ok:
        return "partial"
    return "extracted"
