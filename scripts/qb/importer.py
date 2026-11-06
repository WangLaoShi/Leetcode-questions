"""Match normalized records and import them idempotently."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from qb.db import connect, migrate
from qb.schema_check import validate_problem
from qb.util import SOURCE_PRIORITY, canonical_hash, compare_key, utc_now, write_json

NORMALIZED_ORDER = ("leetcode-api", "neenza", "doocs")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def iter_records(sources: list[str] | None, slug_filter: set[str] | None, normalized_dir: Path):
    selected = sources or list(NORMALIZED_ORDER)
    for name in NORMALIZED_ORDER:
        if name not in selected:
            continue
        path = normalized_dir / f"{name}.jsonl"
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                slug = (record.get("identity") or {}).get("slug")
                if slug_filter is not None and slug not in slug_filter:
                    continue
                yield name, path.name, line_no, record


class Importer:
    def __init__(self, conn: sqlite3.Connection, batch_id: int, fail_slug: str | None = None):
        self.conn = conn
        self.batch_id = batch_id
        self.fail_slug = fail_slug
        self.counts = {
            "seen": 0,
            "problems_created": 0,
            "problems_matched": 0,
            "contents_inserted": 0,
            "contents_revised": 0,
            "contents_skipped": 0,
            "conflicts_isolated": 0,
            "content_conflicts": 0,
            "failures": 0,
            "schema_failures": 0,
        }
        self.failures: list[dict] = []
        self.isolated: list[dict] = []
        self.now = utc_now()

    def run_record(self, origin: str, filename: str, line_no: int, record: dict) -> None:
        self.counts["seen"] += 1
        errors = validate_problem(record)
        if errors:
            self.counts["schema_failures"] += 1
            self.counts["failures"] += 1
            self.failures.append(
                {"origin": origin, "file": filename, "line": line_no, "errors": errors[:8], "slug": record.get("identity", {}).get("slug")}
            )
            return
        slug = record["identity"].get("slug")
        self.conn.execute("SAVEPOINT rec")
        try:
            if self.fail_slug and slug == self.fail_slug:
                raise RuntimeError("injected failure before commit")
            self._import_valid(record)
            self.conn.execute("RELEASE SAVEPOINT rec")
        except Exception as exc:  # one record must not leave a partial problem
            self.conn.execute("ROLLBACK TO SAVEPOINT rec")
            self.conn.execute("RELEASE SAVEPOINT rec")
            self.counts["failures"] += 1
            self.failures.append(
                {
                    "origin": origin,
                    "file": filename,
                    "line": line_no,
                    "slug": slug,
                    "error": type(exc).__name__ + ": " + str(exc)[:300],
                }
            )

    def _import_valid(self, record: dict) -> None:
        source = record["sources"][0]
        source_id = self._source_record(source)
        for issue in record.get("adapter_issues") or []:
            if issue.get("issue_type") == "editorial_excluded":
                continue
            self._issue(
                issue["issue_type"],
                issue.get("severity", "info"),
                issue.get("detail", ""),
                source_id=source_id,
                key=f"{source['name']}|{source['locator']}|{issue['issue_type']}",
            )
        match = self._match(record["identity"])
        if match["kind"] == "isolated":
            self.counts["conflicts_isolated"] += 1
            self.isolated.append(
                {
                    "slug": record["identity"].get("slug"),
                    "display_id": record["identity"].get("display_id"),
                    "site": record["identity"].get("site"),
                    "reason": match["reason"],
                    "source": source["name"],
                    "path": source["path"],
                }
            )
            self._issue(
                "identity_conflict",
                "error",
                match["reason"],
                source_id=source_id,
                key=f"iso|{record['identity'].get('site')}|{record['identity'].get('slug')}|{record['identity'].get('display_id')}|{source['path']}",
                detail=match,
            )
            return
        if match["kind"] == "created":
            self.counts["problems_created"] += 1
        else:
            self.counts["problems_matched"] += 1
        problem_id = match["problem_id"]
        identity_id = match["identity_id"]
        self._fill_problem(problem_id, record)
        self._align_identity(identity_id, record["identity"], source_id)
        self._tags(problem_id, record.get("tags") or [], source_id)
        content = record["contents"][0]
        content_hash = canonical_hash(
            {
                "locale": content["locale"],
                "title": content.get("title"),
                "statement_markdown": content.get("statement_markdown"),
                "constraints": content.get("constraints"),
                "follow_ups": content.get("follow_ups"),
                "examples": content.get("examples"),
                "hints": content.get("hints"),
                "type_specific": content.get("type_specific"),
            }
        )
        existing = self.conn.execute(
            """
            SELECT c.id FROM problem_content c
            JOIN content_provenance p ON p.object_type='content' AND p.object_id=c.id
            WHERE c.problem_id=? AND c.locale=? AND c.content_hash=? AND p.source_record_id=? AND p.extract_locator=?
            """,
            (problem_id, content["locale"], content_hash, source_id, source["locator"]),
        ).fetchone()
        if existing:
            self.counts["contents_skipped"] += 1
            content_id = existing["id"]
        else:
            content_id = self._insert_content(problem_id, identity_id, content, content_hash, source_id, source)
        self._starters(problem_id, content_id, record.get("starter_codes") or [], source_id)
        self._assets(content_id, record.get("assets") or [])
        self._recompute_current(problem_id, content["locale"])
        self._note_content_conflict(problem_id, content["locale"], source_id)

    def _source_record(self, source: dict) -> int:
        row = self.conn.execute(
            """
            SELECT id FROM source_record
            WHERE source_name=? AND repo_path=? AND git_commit IS ? AND file_sha256 IS ?
            """,
            (source["name"], source["path"], source.get("git_commit"), source.get("file_sha256")),
        ).fetchone()
        if row:
            return row["id"]
        # git_commit/hash equality with NULL needs IS; values here are non-null.
        row = self.conn.execute(
            """
            SELECT id FROM source_record
            WHERE source_name=? AND repo_path=? AND ifnull(git_commit,'')=? AND ifnull(file_sha256,'')=?
            """,
            (source["name"], source["path"], source.get("git_commit") or "", source.get("file_sha256") or ""),
        ).fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
            """
            INSERT INTO source_record
                (source_name, repo_url, repo_path, git_commit, retrieved_at, file_sha256, request_params_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source["name"],
                source.get("repo_url"),
                source["path"],
                source.get("git_commit"),
                source.get("retrieved_at") or self.now,
                source.get("file_sha256"),
                None,
            ),
        )
        return cur.lastrowid

    def _match(self, ident: dict) -> dict:
        platform, site = ident["platform"], ident["site"]
        pid, slug, display = ident.get("platform_question_id"), ident.get("slug"), ident.get("display_id")
        if pid:
            row = self._identity_by("platform_question_id", platform, site, pid)
            if row:
                return {"kind": "matched", "problem_id": row["problem_id"], "identity_id": row["id"], "reason": "platform_question_id"}
        by_slug = self._identity_by("slug", platform, site, slug) if slug else None
        by_display = self._identity_by("display_id", platform, site, display) if display else None
        if by_slug and by_display and by_slug["problem_id"] != by_display["problem_id"]:
            return {"kind": "isolated", "reason": "slug and display_id point at different problems"}
        if by_slug and by_display:
            return {"kind": "matched", "problem_id": by_slug["problem_id"], "identity_id": by_slug["id"], "reason": "slug_and_display"}
        if by_slug and (not display or by_slug["display_id"] in (None, display)):
            return {"kind": "matched", "problem_id": by_slug["problem_id"], "identity_id": by_slug["id"], "reason": "slug"}
        if by_slug and display and by_slug["display_id"] not in (None, display):
            return {"kind": "isolated", "reason": "slug matched a problem with a different display_id"}
        if by_display and (not slug or by_display["slug"] in (None, slug)):
            return {"kind": "matched", "problem_id": by_display["problem_id"], "identity_id": by_display["id"], "reason": "display_id"}
        if by_display and slug and by_display["slug"] not in (None, slug):
            return {"kind": "isolated", "reason": "display_id matched a problem with a different slug"}
        problem_id = self._insert_problem(ident)
        identity_id = self._insert_identity(problem_id, ident)
        return {"kind": "created", "problem_id": problem_id, "identity_id": identity_id, "reason": "new"}

    def _identity_by(self, column: str, platform: str, site: str, value: str):
        if column not in ("platform_question_id", "slug", "display_id"):
            raise ValueError(column)
        return self.conn.execute(
            f"SELECT * FROM problem_source_identity WHERE platform=? AND site=? AND {column}=?",
            (platform, site, value),
        ).fetchone()

    def _insert_problem(self, ident: dict) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO problem (category, category_raw, difficulty, difficulty_raw, is_paid_only, lifecycle, created_at, updated_at)
            VALUES (NULL, NULL, NULL, NULL, NULL, 'active', ?, ?)
            """,
            (self.now, self.now),
        )
        return cur.lastrowid

    def _insert_identity(self, problem_id: int, ident: dict) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO problem_source_identity
                (problem_id, platform, site, platform_question_id, display_id, slug, url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                problem_id,
                ident["platform"],
                ident["site"],
                ident.get("platform_question_id"),
                ident.get("display_id"),
                ident.get("slug"),
                ident.get("url"),
                self.now,
                self.now,
            ),
        )
        return cur.lastrowid

    def _fill_problem(self, problem_id: int, record: dict) -> None:
        row = self.conn.execute("SELECT * FROM problem WHERE id=?", (problem_id,)).fetchone()
        category, difficulty, paid = record.get("category"), record.get("difficulty"), record.get("is_paid_only")
        raw = record.get("raw") or {}
        sets = []
        values = []
        if category and row["category"] and category != row["category"]:
            self._issue("category_conflict", "warning", f"{row['category']} vs {category}", problem_id=problem_id, key=f"cat|{problem_id}|{category}")
        elif category and not row["category"]:
            sets += ["category=?", "category_raw=?"]
            values += [category, raw.get("category")]
        if difficulty and row["difficulty"] and difficulty != row["difficulty"]:
            self._issue("difficulty_conflict", "warning", f"{row['difficulty']} vs {difficulty}", problem_id=problem_id, key=f"diff|{problem_id}|{difficulty}|{record['sources'][0]['name']}")
        elif difficulty and not row["difficulty"]:
            sets += ["difficulty=?", "difficulty_raw=?"]
            values += [difficulty, raw.get("difficulty")]
        if isinstance(paid, bool) and row["is_paid_only"] is not None and bool(row["is_paid_only"]) != paid:
            self._issue("paid_flag_conflict", "warning", "sources disagree on is_paid_only", problem_id=problem_id, key=f"paid|{problem_id}")
        elif isinstance(paid, bool) and row["is_paid_only"] is None:
            sets.append("is_paid_only=?")
            values.append(1 if paid else 0)
        if sets:
            sets.append("updated_at=?")
            values.append(self.now)
            values.append(problem_id)
            self.conn.execute(f"UPDATE problem SET {', '.join(sets)} WHERE id=?", values)

    def _align_identity(self, identity_id: int, ident: dict, source_id: int) -> None:
        row = self.conn.execute("SELECT * FROM problem_source_identity WHERE id=?", (identity_id,)).fetchone()
        for field in ("platform_question_id", "display_id", "slug", "url"):
            new = ident.get(field)
            old = row[field]
            if new and old and new != old:
                self._issue(
                    "identity_field_mismatch",
                    "warning",
                    f"{field} kept as existing value",
                    problem_id=row["problem_id"],
                    source_id=source_id,
                    key=f"idfield|{identity_id}|{field}|{new}",
                    detail={"field": field, "existing": old, "incoming": new},
                )
            elif new and not old:
                self.conn.execute(
                    f"UPDATE problem_source_identity SET {field}=?, updated_at=? WHERE id=?",
                    (new, self.now, identity_id),
                )

    def _tags(self, problem_id: int, tags: list[dict], source_id: int) -> None:
        for tag in tags:
            code, name, source = tag["code"], tag["name"], tag["source"]
            row = self.conn.execute("SELECT id FROM tag WHERE source=? AND code=?", (source, code)).fetchone()
            if row:
                tag_id = row["id"]
            else:
                tag_id = self.conn.execute(
                    "INSERT INTO tag (source, code, name) VALUES (?, ?, ?)",
                    (source, code, name),
                ).lastrowid
            self.conn.execute(
                "INSERT OR IGNORE INTO problem_tag (problem_id, tag_id, source_record_id) VALUES (?, ?, ?)",
                (problem_id, tag_id, source_id),
            )

    def _insert_content(self, problem_id, identity_id, content, content_hash, source_id, source) -> int:
        previous = self.conn.execute(
            """
            SELECT c.id, c.revision FROM problem_content c
            JOIN content_provenance p ON p.object_type='content' AND p.object_id=c.id
            JOIN source_record s ON s.id=p.source_record_id
            WHERE c.problem_id=? AND c.locale=? AND s.source_name=? AND s.repo_path=? AND p.extract_locator=?
            ORDER BY c.revision DESC LIMIT 1
            """,
            (problem_id, content["locale"], source["name"], source["path"], source["locator"]),
        ).fetchone()
        revision = 1 if not previous else previous["revision"] + 1
        reason = "initial" if not previous else "source_content_changed"
        if previous:
            self.counts["contents_revised"] += 1
        else:
            self.counts["contents_inserted"] += 1
        cur = self.conn.execute(
            """
            INSERT INTO problem_content (
                problem_id, source_identity_id, locale, title, statement_markdown, statement_format,
                constraints_json, follow_ups_json, type_specific_json, field_status_json,
                extraction_status, content_hash, revision, is_current, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                problem_id,
                identity_id,
                content["locale"],
                content.get("title"),
                content.get("statement_markdown"),
                content.get("statement_format"),
                _json(content.get("constraints") or []),
                _json(content.get("follow_ups") or []),
                _json(content.get("type_specific") or {}),
                _json(content.get("field_status") or {}),
                content["extraction_status"],
                content_hash,
                revision,
                self.now,
            ),
        )
        content_id = cur.lastrowid
        self.conn.execute(
            """
            INSERT INTO content_revision (content_id, previous_content_id, reason, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (content_id, previous["id"] if previous else None, reason, self.now),
        )
        self.conn.execute(
            """
            INSERT INTO content_provenance (object_type, object_id, source_record_id, extract_locator)
            VALUES ('content', ?, ?, ?)
            """,
            (content_id, source_id, source["locator"]),
        )
        for example in content.get("examples") or []:
            self.conn.execute(
                """
                INSERT INTO problem_example (content_id, ordinal, input_text, output_text, explanation, images_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    content_id,
                    example["ordinal"],
                    example.get("input"),
                    example.get("output"),
                    example.get("explanation"),
                    _json(example.get("images") or []),
                ),
            )
        for index, hint in enumerate(content.get("hints") or [], start=1):
            self.conn.execute(
                "INSERT INTO problem_hint (content_id, locale, ordinal, body) VALUES (?, ?, ?, ?)",
                (content_id, content["locale"], index, hint),
            )
        if not content.get("statement_markdown"):
            self._issue(
                "statement_missing",
                "info",
                content.get("field_status", {}).get("statement", ""),
                problem_id=problem_id,
                source_id=source_id,
                key=f"nostmt|{problem_id}|{content['locale']}|{source['name']}|{source['locator']}",
            )
        return content_id

    def _starters(self, problem_id, content_id, starters, source_id) -> None:
        for starter in starters:
            template = starter.get("template") or ""
            if not template.strip():
                continue
            digest = canonical_hash({"language": starter["language"], "template": template})
            self.conn.execute(
                """
                INSERT OR IGNORE INTO starter_code (
                    problem_id, content_id, language, language_name, template,
                    suspected_implementation, content_hash, is_current, source_record_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    problem_id,
                    content_id,
                    starter["language"],
                    starter.get("language_name"),
                    template,
                    1 if starter.get("suspected_implementation") else 0,
                    digest,
                    source_id,
                ),
            )
            if starter.get("suspected_implementation"):
                self._issue(
                    "suspected_implementation",
                    "warning",
                    starter["language"],
                    problem_id=problem_id,
                    source_id=source_id,
                    key=f"impl|{problem_id}|{starter['language']}|{digest[:16]}",
                )
        languages = {s["language"] for s in starters}
        for language in languages:
            self._recompute_starter(problem_id, language)

    def _recompute_starter(self, problem_id: int, language: str) -> None:
        rows = self.conn.execute(
            """
            SELECT sc.id, sr.source_name FROM starter_code sc
            LEFT JOIN source_record sr ON sr.id=sc.source_record_id
            WHERE sc.problem_id=? AND sc.language=?
            ORDER BY sc.id
            """,
            (problem_id, language),
        ).fetchall()
        if not rows:
            return
        best = sorted(rows, key=lambda row: (SOURCE_PRIORITY.get(row["source_name"], 9), row["id"]))[0]
        self.conn.execute(
            "UPDATE starter_code SET is_current=0 WHERE problem_id=? AND language=?",
            (problem_id, language),
        )
        self.conn.execute("UPDATE starter_code SET is_current=1 WHERE id=?", (best["id"],))

    def _assets(self, content_id: int, assets: list[dict]) -> None:
        for ordinal, asset in enumerate(assets, start=1):
            url = asset.get("original_url")
            if not url:
                continue
            row = self.conn.execute("SELECT id FROM asset WHERE original_url=?", (url,)).fetchone()
            if row:
                asset_id = row["id"]
            else:
                asset_id = self.conn.execute(
                    "INSERT INTO asset (media_type, original_url, storage_path, sha256) VALUES (?, ?, NULL, NULL)",
                    (asset.get("media_type"), url),
                ).lastrowid
            self.conn.execute(
                "INSERT OR IGNORE INTO content_asset (content_id, asset_id, ordinal, alt_text) VALUES (?, ?, ?, ?)",
                (content_id, asset_id, ordinal, asset.get("alt") or ""),
            )

    def _recompute_current(self, problem_id: int, locale: str) -> None:
        rows = self.conn.execute(
            """
            SELECT c.id, c.statement_markdown, c.revision, s.source_name
            FROM problem_content c
            JOIN content_provenance p ON p.object_type='content' AND p.object_id=c.id
            JOIN source_record s ON s.id=p.source_record_id
            WHERE c.problem_id=? AND c.locale=?
            """,
            (problem_id, locale),
        ).fetchall()
        if not rows:
            return

        def rank(row):
            empty = 0 if (row["statement_markdown"] or "").strip() else 1
            return (empty, SOURCE_PRIORITY.get(row["source_name"], 9), -row["revision"], row["id"])

        best = sorted(rows, key=rank)[0]
        self.conn.execute(
            "UPDATE problem_content SET is_current=0 WHERE problem_id=? AND locale=?",
            (problem_id, locale),
        )
        self.conn.execute("UPDATE problem_content SET is_current=1 WHERE id=?", (best["id"],))

    def _note_content_conflict(self, problem_id: int, locale: str, source_id: int) -> None:
        rows = self.conn.execute(
            """
            SELECT c.id, c.statement_markdown, c.is_current, s.source_name
            FROM problem_content c
            JOIN content_provenance p ON p.object_type='content' AND p.object_id=c.id
            JOIN source_record s ON s.id=p.source_record_id
            WHERE c.problem_id=? AND c.locale=?
            """,
            (problem_id, locale),
        ).fetchall()
        nonempty = [row for row in rows if (row["statement_markdown"] or "").strip()]
        keys = {compare_key(row["statement_markdown"]) for row in nonempty}
        if len(keys) <= 1:
            return
        names = sorted({row["source_name"] for row in nonempty})
        inserted = self._issue(
            "content_conflict",
            "warning",
            "same locale differs across sources; versions kept separately",
            problem_id=problem_id,
            source_id=source_id,
            key=f"conflict|{problem_id}|{locale}",
            detail={"locale": locale, "sources": names},
        )
        if inserted:
            self.counts["content_conflicts"] += 1

    def _issue(self, issue_type, severity, message, problem_id=None, source_id=None, key="", detail=None) -> None:
        fingerprint = canonical_hash({"type": issue_type, "key": key, "message": message})
        payload = {"message": message}
        if detail:
            payload["detail"] = detail
        cur = self.conn.execute(
            """
            INSERT OR IGNORE INTO data_issue
                (batch_id, problem_id, source_record_id, issue_type, severity, status, detail_json, fingerprint, created_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)
            """,
            (self.batch_id, problem_id, source_id, issue_type, severity, _json(payload), fingerprint, self.now),
        )
        return cur.rowcount


def import_records(
    db_path: Path,
    *,
    normalized_dir: Path,
    sources: list[str] | None = None,
    slug_filter: set[str] | None = None,
    dry_run: bool = False,
    fail_slug: str | None = None,
    reports_dir: Path,
) -> dict:
    conn = connect(db_path)
    migrate(conn)
    conn.isolation_level = None
    started = utc_now()
    conn.execute("BEGIN")
    batch_id = conn.execute(
        """
        INSERT INTO import_batch (source_filter, status, dry_run, started_at, notes)
        VALUES (?, 'running', ?, ?, ?)
        """,
        (
            ",".join(sources) if sources else "all",
            1 if dry_run else 0,
            started,
            "fail_slug=" + fail_slug if fail_slug else None,
        ),
    ).lastrowid
    importer = Importer(conn, batch_id, fail_slug=fail_slug)
    try:
        for origin, filename, line_no, record in iter_records(sources, slug_filter, normalized_dir):
            importer.run_record(origin, filename, line_no, record)
        status = "success"
        if importer.counts["failures"] or importer.counts["conflicts_isolated"]:
            status = "partial"
        if importer.counts["seen"] and importer.counts["failures"] == importer.counts["seen"]:
            status = "failed"
        finished = utc_now()
        conn.execute(
            "UPDATE import_batch SET status=?, finished_at=?, counts_json=? WHERE id=?",
            (status, finished, _json(importer.counts), batch_id),
        )
        report = {
            "batch_id": batch_id,
            "dry_run": dry_run,
            "status": status,
            "started_at": started,
            "finished_at": finished,
            "db": str(db_path),
            "counts": importer.counts,
            "failure_sample": importer.failures[:30],
            "isolated_sample": importer.isolated[:30],
            "isolated_total": len(importer.isolated),
        }
        reports_dir.mkdir(parents=True, exist_ok=True)
        suffix = "dry-run" if dry_run else "import"
        write_json(reports_dir / f"batch-{batch_id}-{suffix}.json", report)
        if dry_run:
            conn.execute("ROLLBACK")
            report["committed"] = False
        else:
            conn.execute("COMMIT")
            report["committed"] = True
        return report
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
