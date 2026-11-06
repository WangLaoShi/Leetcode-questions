"""Run the three adapters and write normalized JSONL."""

from __future__ import annotations

import json
from pathlib import Path

from qb.adapters import (
    adapt_api_question,
    adapt_doocs_file,
    adapt_neenza_file,
    contains_forbidden_solution,
)
from qb.schema_check import validate_problem
from qb.util import NORMALIZED, RAW, REPORTS, read_json, sha256_file, utc_now, write_json


def _snapshot() -> dict:
    path = Path(__file__).resolve().parents[2] / "manifests" / "snapshot.json"
    if path.exists():
        return read_json(path)
    return {"recorded_at": utc_now(), "sources": {}}


def _commit(snapshot: dict, name: str) -> str:
    return snapshot.get("sources", {}).get(name, {}).get("git_commit", "unknown")


def _retrieved(snapshot: dict) -> str:
    return snapshot.get("recorded_at") or utc_now()


def normalize_all(only: str | None = None) -> dict:
    snapshot = _snapshot()
    retrieved = _retrieved(snapshot)
    NORMALIZED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    failures_path = REPORTS / "normalize-failures.jsonl"
    failures_path.write_text("", encoding="utf-8")
    stats = {}
    if only in (None, "neenza"):
        stats["neenza"] = _normalize_neenza(snapshot, retrieved, failures_path)
    if only in (None, "leetcode-api"):
        stats["leetcode-api"] = _normalize_api(snapshot, retrieved, failures_path)
    if only in (None, "doocs"):
        stats["doocs"] = _normalize_doocs(snapshot, retrieved, failures_path)
    write_json(REPORTS / "normalize-stats.json", {"finished_at": utc_now(), "sources": stats})
    return stats


def _write_record(handle, record, failures, origin, path) -> str:
    marker = contains_forbidden_solution(record)
    if marker:
        failures.write(
            json.dumps(
                {"origin": origin, "path": path, "reason": "solution_marker_in_output", "detail": marker},
                ensure_ascii=False,
            )
            + "\n"
        )
        return "rejected"
    errors = validate_problem(record)
    if errors:
        failures.write(
            json.dumps(
                {"origin": origin, "path": path, "reason": "schema", "detail": errors[:12]},
                ensure_ascii=False,
            )
            + "\n"
        )
        return "rejected"
    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record["contents"][0]["extraction_status"]


def _normalize_neenza(snapshot, retrieved, failures_path: Path) -> dict:
    root = RAW / "neenza" / "repo" / "problems"
    files = sorted(root.glob("*.json"))
    out = NORMALIZED / "neenza.jsonl"
    counts = {"files": len(files), "written": 0, "rejected": 0}
    commit = _commit(snapshot, "neenza")
    with out.open("w", encoding="utf-8") as handle, failures_path.open("a", encoding="utf-8") as failures:
        for index, path in enumerate(files, start=1):
            try:
                record = adapt_neenza_file(path, commit, retrieved)
                status = _write_record(handle, record, failures, "neenza", path.name)
            except Exception as exc:
                failures.write(
                    json.dumps(
                        {"origin": "neenza", "path": path.name, "reason": "exception", "detail": type(exc).__name__ + ": " + str(exc)[:300]},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                counts["rejected"] += 1
                continue
            if status == "rejected":
                counts["rejected"] += 1
            else:
                counts["written"] += 1
            if index % 500 == 0:
                print(f"neenza {index}/{len(files)}", flush=True)
    print(f"neenza done {counts}", flush=True)
    return counts


def _normalize_api(snapshot, retrieved, failures_path: Path) -> dict:
    path = RAW / "leetcode-api" / "repo" / "data" / "leetcode_questions.json"
    digest = sha256_file(path)
    commit = _commit(snapshot, "leetcode-api")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    out = NORMALIZED / "leetcode-api.jsonl"
    counts = {"files": 1, "questions": len(data), "written": 0, "rejected": 0}
    with out.open("w", encoding="utf-8") as handle, failures_path.open("a", encoding="utf-8") as failures:
        for index, item in enumerate(data, start=1):
            question = item.get("data", {}).get("question") if isinstance(item, dict) else None
            if not question:
                failures.write(
                    json.dumps({"origin": "leetcode-api", "path": f"index:{index}", "reason": "missing_question"}, ensure_ascii=False)
                    + "\n"
                )
                counts["rejected"] += 1
                continue
            locator = f"questionId:{question.get('questionId')}"
            try:
                record = adapt_api_question(question, commit, retrieved, digest, locator)
                status = _write_record(handle, record, failures, "leetcode-api", locator)
            except Exception as exc:
                failures.write(
                    json.dumps(
                        {
                            "origin": "leetcode-api",
                            "path": locator,
                            "reason": "exception",
                            "detail": type(exc).__name__ + ": " + str(exc)[:300],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                counts["rejected"] += 1
                continue
            if status == "rejected":
                counts["rejected"] += 1
            else:
                counts["written"] += 1
            if index % 500 == 0:
                print(f"leetcode-api {index}/{len(data)}", flush=True)
    print(f"leetcode-api done {counts}", flush=True)
    return counts


def _normalize_doocs(snapshot, retrieved, failures_path: Path) -> dict:
    repo = RAW / "doocs" / "repo"
    files = sorted((repo / "solution").rglob("*.md"))
    commit = _commit(snapshot, "doocs")
    out = NORMALIZED / "doocs.jsonl"
    counts = {"files": len(files), "written": 0, "rejected": 0, "skipped_non_problem": 0}
    with out.open("w", encoding="utf-8") as handle, failures_path.open("a", encoding="utf-8") as failures:
        for index, path in enumerate(files, start=1):
            try:
                record, failure = adapt_doocs_file(path, repo, commit, retrieved)
            except Exception as exc:
                failures.write(
                    json.dumps(
                        {
                            "origin": "doocs",
                            "path": path.relative_to(repo).as_posix(),
                            "reason": "exception",
                            "detail": type(exc).__name__ + ": " + str(exc)[:300],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                counts["rejected"] += 1
                continue
            if failure:
                if failure["reason"] == "skipped_non_problem":
                    counts["skipped_non_problem"] += 1
                else:
                    counts["rejected"] += 1
                    failures.write(json.dumps({"origin": "doocs", **failure}, ensure_ascii=False) + "\n")
                continue
            status = _write_record(handle, record, failures, "doocs", record["sources"][0]["path"])
            if status == "rejected":
                counts["rejected"] += 1
            else:
                counts["written"] += 1
            if index % 500 == 0:
                print(f"doocs {index}/{len(files)}", flush=True)
    print(f"doocs done {counts}", flush=True)
    return counts
