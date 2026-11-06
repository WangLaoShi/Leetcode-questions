-- 按展示题号、slug 或标题
SELECT p.id, i.site, i.display_id, i.slug, c.locale, c.title
FROM problem p
JOIN problem_source_identity i ON i.problem_id = p.id
JOIN problem_content c ON c.problem_id = p.id AND c.is_current = 1
WHERE i.display_id = '1' OR i.slug = 'two-sum' OR c.title LIKE '%两数之和%';

-- 按类别、难度、标签
SELECT p.id, i.slug, p.category, p.difficulty, t.name
FROM problem p
JOIN problem_source_identity i ON i.problem_id = p.id
JOIN problem_tag pt ON pt.problem_id = p.id
JOIN tag t ON t.id = pt.tag_id
WHERE p.category = 'database' AND p.difficulty = 'easy' AND t.code = 'database';

-- 指定站点与语言的当前题干
SELECT c.title, c.statement_markdown, c.extraction_status
FROM problem_content c
JOIN problem_source_identity i ON i.id = c.source_identity_id
WHERE i.slug = 'two-sum' AND i.site = 'leetcode.com' AND c.locale = 'en' AND c.is_current = 1;

-- 示例、提示、模板、题型扩展
SELECT e.ordinal, e.input_text, e.output_text, e.explanation
FROM problem_example e
JOIN problem_content c ON c.id = e.content_id
WHERE c.is_current = 1;

SELECT h.ordinal, h.body FROM problem_hint h JOIN problem_content c ON c.id = h.content_id WHERE c.is_current = 1;

SELECT language, template, suspected_implementation
FROM starter_code WHERE is_current = 1;

SELECT type_specific_json FROM problem_content WHERE is_current = 1;

-- 来源、当前版本、历史版本
SELECT c.id, c.revision, c.is_current, s.source_name, s.git_commit, s.repo_path, p.extract_locator, r.reason
FROM problem_content c
JOIN content_provenance p ON p.object_type = 'content' AND p.object_id = c.id
JOIN source_record s ON s.id = p.source_record_id
LEFT JOIN content_revision r ON r.content_id = c.id;

-- 缺失、冲突、待核实
SELECT issue_type, severity, status, detail_json
FROM data_issue
WHERE status = 'open'
ORDER BY issue_type;
