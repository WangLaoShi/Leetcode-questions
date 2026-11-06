"""Record commits, licenses, retrieval time, and file hashes. No credentials."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from qb.util import MANIFESTS, RAW, sha256_file, utc_now, write_json


SOURCES = {
    "neenza": {
        "repo_url": "https://github.com/neenza/leetcode-problems",
        "branch": "master",
        "local": RAW / "neenza" / "repo",
        "license_file": None,
        "license_observed": "No LICENSE file in the repository snapshot.",
        "what_it_covers": "Per-problem JSON plus merged_problems.json. merged_problems.json duplicates problems/ and is not imported.",
        "hash_paths": ["problems"],
    },
    "leetcode-api": {
        "repo_url": "https://github.com/noworneverev/leetcode-api",
        "branch": "main",
        "local": RAW / "leetcode-api" / "repo",
        "license_file": "LICENSE",
        "license_observed": "MIT, copyright 2025 Yan-Ying Liao. The MIT grant covers the repository software. The cached problem JSON is LeetCode content and is not treated as MIT-licensed merely because it sits in this repo.",
        "what_it_covers": "data/leetcode_questions.json is a GraphQL questionData cache for leetcode.com. data/leetcode_questions_mini.json is a list view. Live samples are under raw/leetcode-api/api-samples.",
        "hash_paths": ["data/leetcode_questions.json", "data/leetcode_questions_mini.json", "data/problem_sets.json", "LICENSE"],
    },
    "doocs": {
        "repo_url": "https://github.com/doocs/leetcode",
        "branch": "main",
        "local": RAW / "doocs" / "repo",
        "license_file": "LICENSE",
        "license_observed": "CC BY-SA 4.0 on the repository. Sparse checkout kept LICENSE, root README, and solution/**/README.md plus README_EN.md only. Solution implementation files were not downloaded. CC BY-SA is not applied to upstream LeetCode statements.",
        "what_it_covers": "Chinese and English problem-description regions inside README files. Not an official leetcode.cn dump.",
        "hash_paths": ["solution", "LICENSE", "README.md"],
    },
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _hash_tree(root: Path, relative: str, handle) -> int:
    target = root / relative
    count = 0
    if target.is_file():
        digest = sha256_file(target)
        handle.write(json.dumps({"path": relative.replace("\\", "/"), "sha256": digest, "bytes": target.stat().st_size}) + "\n")
        return 1
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        if path.name == ".git" or ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        handle.write(json.dumps({"path": rel, "sha256": sha256_file(path), "bytes": path.stat().st_size}) + "\n")
        count += 1
        if count % 1000 == 0:
            print(f"hashed {relative} {count}", flush=True)
    return count


def write_manifest() -> dict:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    recorded = utc_now()
    sources = {}
    for name, meta in SOURCES.items():
        repo = meta["local"]
        commit = _git(repo, "rev-parse", "HEAD")
        commit_time = _git(repo, "log", "-1", "--format=%cI")
        hash_path = MANIFESTS / "files" / f"{name}.jsonl"
        hash_path.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        with hash_path.open("w", encoding="utf-8") as handle:
            for relative in meta["hash_paths"]:
                total += _hash_tree(repo, relative, handle)
        sources[name] = {
            "repo_url": meta["repo_url"],
            "branch": meta["branch"],
            "git_commit": commit,
            "git_commit_time": commit_time,
            "local_path": str(repo),
            "license_file": meta["license_file"],
            "license_observed": meta["license_observed"],
            "coverage": meta["what_it_covers"],
            "hashed_files": total,
            "hash_list": str(hash_path),
        }
        print(f"manifest {name} {commit[:12]} files={total}", flush=True)
    api_samples = RAW / "leetcode-api" / "api-samples"
    samples = []
    if api_samples.exists():
        for meta_path in sorted(api_samples.glob("*.meta.json")):
            samples.append(json.loads(meta_path.read_text(encoding="utf-8")))
    snapshot = {
        "recorded_at": recorded,
        "timezone": "UTC",
        "encoding": "UTF-8",
        "newline": "LF in normalized JSON strings",
        "credentials_stored": False,
        "sources": sources,
        "leetcode_api_live_samples": samples,
        "scope": {
            "platform": "leetcode",
            "sites_in_snapshots": ["leetcode.com", "leetcode.cn (links published by doocs, not an official cn export)"],
            "categories_expected_from_leetcode_api_cache": ["Algorithms", "Database", "Shell", "Concurrency", "JavaScript", "pandas"],
            "languages_content": ["en", "zh-CN"],
            "paid_content": "Import only text present in the public snapshots. Do not call LeetCode for missing premium statements. is_paid_only stays null when the source does not say.",
            "excluded": ["editorials", "solution implementations", "complexity writeups", "user data", "submission history"],
            "completeness": "Complete means complete for these three snapshots, not every problem that has ever existed on LeetCode.",
            "runtime_database": "SQLite, because PostgreSQL and MySQL clients are not installed. PostgreSQL DDL is still delivered.",
        },
    }
    write_json(MANIFESTS / "snapshot.json", snapshot)
    write_json(MANIFESTS / "source-catalog.json", snapshot)
    return snapshot
