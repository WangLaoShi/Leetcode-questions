-- Runtime schema for the local question bank.
-- SQLite is the executable engine on this machine. PostgreSQL DDL is in ../postgres/001_init.sql.
-- JSON documents are TEXT. Empty strings are rejected as identifiers.
-- Problems are not deleted when a later snapshot omits them.

PRAGMA foreign_keys = ON;

CREATE TABLE problem (
    id INTEGER PRIMARY KEY,
    category TEXT CHECK (category IS NULL OR category IN ('algorithm','database','shell','concurrency','javascript','pandas')),
    category_raw TEXT,
    difficulty TEXT CHECK (difficulty IS NULL OR difficulty IN ('easy','medium','hard')),
    difficulty_raw TEXT,
    is_paid_only INTEGER CHECK (is_paid_only IS NULL OR is_paid_only IN (0, 1)),
    lifecycle TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE problem_source_identity (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL REFERENCES problem(id) ON DELETE RESTRICT,
    platform TEXT NOT NULL,
    site TEXT NOT NULL,
    platform_question_id TEXT CHECK (platform_question_id IS NULL OR length(platform_question_id) > 0),
    display_id TEXT CHECK (display_id IS NULL OR length(display_id) > 0),
    slug TEXT CHECK (slug IS NULL OR length(slug) > 0),
    url TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX uq_identity_pid
    ON problem_source_identity(platform, site, platform_question_id)
    WHERE platform_question_id IS NOT NULL;
CREATE UNIQUE INDEX uq_identity_slug
    ON problem_source_identity(platform, site, slug)
    WHERE slug IS NOT NULL;
CREATE UNIQUE INDEX uq_identity_display
    ON problem_source_identity(platform, site, display_id)
    WHERE display_id IS NOT NULL;
CREATE INDEX ix_identity_problem ON problem_source_identity(problem_id);
CREATE INDEX ix_problem_category ON problem(category);
CREATE INDEX ix_problem_difficulty ON problem(difficulty);

CREATE TABLE source_record (
    id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL,
    repo_url TEXT,
    repo_path TEXT NOT NULL,
    git_commit TEXT,
    retrieved_at TEXT NOT NULL,
    file_sha256 TEXT,
    request_params_json TEXT,
    UNIQUE (source_name, repo_path, git_commit, file_sha256)
);

CREATE TABLE problem_content (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL REFERENCES problem(id) ON DELETE RESTRICT,
    source_identity_id INTEGER NOT NULL REFERENCES problem_source_identity(id) ON DELETE RESTRICT,
    locale TEXT NOT NULL,
    title TEXT,
    statement_markdown TEXT,
    statement_format TEXT,
    constraints_json TEXT NOT NULL,
    follow_ups_json TEXT NOT NULL,
    type_specific_json TEXT NOT NULL,
    field_status_json TEXT NOT NULL,
    extraction_status TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    revision INTEGER NOT NULL,
    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE INDEX ix_content_problem_locale ON problem_content(problem_id, locale, is_current);
CREATE INDEX ix_content_title ON problem_content(title);
CREATE INDEX ix_content_hash ON problem_content(content_hash);

CREATE TABLE content_revision (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES problem_content(id) ON DELETE RESTRICT,
    previous_content_id INTEGER REFERENCES problem_content(id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE problem_example (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES problem_content(id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL,
    input_text TEXT,
    output_text TEXT,
    explanation TEXT,
    images_json TEXT NOT NULL,
    UNIQUE (content_id, ordinal)
);

CREATE TABLE problem_hint (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES problem_content(id) ON DELETE RESTRICT,
    locale TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    body TEXT NOT NULL,
    UNIQUE (content_id, locale, ordinal)
);

CREATE TABLE tag (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (source, code)
);

CREATE TABLE problem_tag (
    problem_id INTEGER NOT NULL REFERENCES problem(id) ON DELETE RESTRICT,
    tag_id INTEGER NOT NULL REFERENCES tag(id) ON DELETE RESTRICT,
    source_record_id INTEGER REFERENCES source_record(id) ON DELETE RESTRICT,
    PRIMARY KEY (problem_id, tag_id)
);
CREATE INDEX ix_problem_tag_tag ON problem_tag(tag_id);

CREATE TABLE starter_code (
    id INTEGER PRIMARY KEY,
    problem_id INTEGER NOT NULL REFERENCES problem(id) ON DELETE RESTRICT,
    content_id INTEGER REFERENCES problem_content(id) ON DELETE RESTRICT,
    language TEXT NOT NULL,
    language_name TEXT,
    template TEXT NOT NULL,
    suspected_implementation INTEGER NOT NULL CHECK (suspected_implementation IN (0, 1)),
    content_hash TEXT NOT NULL,
    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
    source_record_id INTEGER REFERENCES source_record(id) ON DELETE RESTRICT,
    UNIQUE (problem_id, language, content_hash)
);
CREATE INDEX ix_starter_problem ON starter_code(problem_id, language, is_current);

CREATE TABLE asset (
    id INTEGER PRIMARY KEY,
    media_type TEXT,
    original_url TEXT NOT NULL UNIQUE,
    storage_path TEXT,
    sha256 TEXT
);

CREATE TABLE content_asset (
    content_id INTEGER NOT NULL REFERENCES problem_content(id) ON DELETE RESTRICT,
    asset_id INTEGER NOT NULL REFERENCES asset(id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL,
    alt_text TEXT,
    PRIMARY KEY (content_id, asset_id, ordinal)
);

CREATE TABLE content_provenance (
    id INTEGER PRIMARY KEY,
    object_type TEXT NOT NULL,
    object_id INTEGER NOT NULL,
    source_record_id INTEGER NOT NULL REFERENCES source_record(id) ON DELETE RESTRICT,
    extract_locator TEXT NOT NULL,
    UNIQUE (object_type, object_id, source_record_id, extract_locator)
);
CREATE INDEX ix_provenance_source ON content_provenance(source_record_id);

CREATE TABLE import_batch (
    id INTEGER PRIMARY KEY,
    source_filter TEXT,
    status TEXT NOT NULL,
    dry_run INTEGER NOT NULL CHECK (dry_run IN (0, 1)),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    counts_json TEXT,
    notes TEXT
);

CREATE TABLE data_issue (
    id INTEGER PRIMARY KEY,
    batch_id INTEGER REFERENCES import_batch(id) ON DELETE RESTRICT,
    problem_id INTEGER REFERENCES problem(id) ON DELETE RESTRICT,
    source_record_id INTEGER REFERENCES source_record(id) ON DELETE RESTRICT,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    detail_json TEXT,
    fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE INDEX ix_issue_type ON data_issue(issue_type, status);
