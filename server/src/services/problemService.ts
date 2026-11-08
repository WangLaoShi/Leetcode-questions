/**
 * 题目服务
 * 从只读数据库查询题目信息
 */
import { queryAll, queryOne } from '../db/questions.js';
import type {
  ProblemListParams,
  ProblemListResponse,
  ProblemListItem,
  ProblemDetailResponse,
  Problem,
  ProblemSourceIdentity,
  ProblemContent,
  ProblemExample,
  ProblemHint,
  StarterCode,
} from '../types/index.js';

/**
 * 获取题目列表（分页、搜索、筛选）
 */
export async function getProblemList(params: ProblemListParams): Promise<ProblemListResponse> {
  const {
    page = 1,
    limit = 20,
    search,
    difficulty,
    category,
    tag,
    site = 'leetcode.com',
    locale = 'en',
    sort = 'display_id',
    order = 'asc',
  } = params;

  const offset = (page - 1) * limit;
  
  // 构建 WHERE 条件
  const conditions: string[] = [];
  const values: (string | number)[] = [];
  
  conditions.push('i.site = ?');
  values.push(site);
  
  conditions.push('c.locale = ?');
  values.push(locale);
  
  conditions.push('c.is_current = 1');
  
  if (search) {
    conditions.push('(i.display_id = ? OR i.slug LIKE ? OR c.title LIKE ?)');
    values.push(search, `%${search}%`, `%${search}%`);
  }
  
  if (difficulty) {
    conditions.push('p.difficulty = ?');
    values.push(difficulty);
  }
  
  if (category) {
    conditions.push('p.category = ?');
    values.push(category);
  }
  
  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  
  // 排序
  const validSortFields: Record<string, string> = {
    'display_id': 'i.display_id',
    'title': 'c.title',
    'difficulty': 'CASE p.difficulty WHEN \'easy\' THEN 1 WHEN \'medium\' THEN 2 WHEN \'hard\' THEN 3 ELSE 4 END',
    'id': 'p.id',
  };
  const sortField = validSortFields[sort] || 'i.display_id';
  const sortOrder = order === 'desc' ? 'DESC' : 'ASC';
  const orderClause = `ORDER BY ${sortField} ${sortOrder}`;
  
  // Tag join
  const tagJoin = tag ? 'JOIN problem_tag pt ON pt.problem_id = p.id JOIN tag t ON t.id = pt.tag_id' : '';
  const tagCondition = tag ? 'AND t.code = ?' : '';
  if (tag) {
    values.push(tag);
  }
  
  // 查询总数
  const countSql = `
    SELECT COUNT(DISTINCT p.id) as total
    FROM problem p
    JOIN problem_source_identity i ON i.problem_id = p.id
    JOIN problem_content c ON c.source_identity_id = i.id
    ${tagJoin}
    ${whereClause}
    ${tagCondition}
  `;
  
  const countResult = await queryOne<{ total: number }>(countSql, values);
  const total = countResult?.total || 0;
  
  // 查询列表
  const listValues = [...values];
  if (tag) {
    // tag 已经在 values 里了
  }
  listValues.push(limit, offset);
  
  const listSql = `
    SELECT DISTINCT
      p.id,
      i.display_id,
      i.slug,
      c.title,
      p.difficulty,
      p.category,
      i.site,
      c.locale
    FROM problem p
    JOIN problem_source_identity i ON i.problem_id = p.id
    JOIN problem_content c ON c.source_identity_id = i.id
    ${tagJoin}
    ${whereClause}
    ${tagCondition}
    ${orderClause}
    LIMIT ? OFFSET ?
  `;
  
  const rows = await queryAll<{
    id: number;
    display_id: string | null;
    slug: string | null;
    title: string | null;
    difficulty: string | null;
    category: string | null;
    site: string;
    locale: string;
  }>(listSql, listValues);
  
  // 获取每道题的标签
  const problems: ProblemListItem[] = [];
  for (const row of rows) {
    const tags = await getProblemTags(row.id);
    problems.push({
      id: row.id,
      displayId: row.display_id,
      slug: row.slug,
      title: row.title,
      difficulty: row.difficulty,
      category: row.category,
      site: row.site,
      locale: row.locale,
      tags,
    });
  }
  
  return {
    problems,
    total,
    page,
    limit,
    totalPages: Math.ceil(total / limit),
  };
}

/**
 * 获取题目详情
 */
export async function getProblemDetail(
  identifier: string | number,
  site: string = 'leetcode.com',
  locale: string = 'en'
): Promise<ProblemDetailResponse | null> {
  // 根据 ID 或 slug 查找
  const isId = typeof identifier === 'number' || /^\d+$/.test(String(identifier));
  
  let identity: ProblemSourceIdentity | null;
  
  if (isId) {
    identity = await queryOne<ProblemSourceIdentity>(`
      SELECT * FROM problem_source_identity 
      WHERE (display_id = ? OR problem_id = ?) AND site = ?
    `, [String(identifier), String(identifier), site]);
  } else {
    identity = await queryOne<ProblemSourceIdentity>(`
      SELECT * FROM problem_source_identity 
      WHERE slug = ? AND site = ?
    `, [String(identifier), site]);
  }
  
  if (!identity) {
    return null;
  }
  
  // 获取题目基本信息
  const problem = await queryOne<Problem>('SELECT * FROM problem WHERE id = ?', [identity.problem_id]);
  if (!problem) {
    return null;
  }
  
  // 获取当前题干内容
  const content = await queryOne<ProblemContent>(`
    SELECT * FROM problem_content 
    WHERE source_identity_id = ? AND locale = ? AND is_current = 1
  `, [identity.id, locale]);
  
  // 获取标签
  const tags = await getProblemTagsWithDetails(problem.id);
  
  // 获取示例
  const examples = content 
    ? await getProblemExamples(content.id)
    : [];
  
  // 获取提示
  const hints = content
    ? await getProblemHints(content.id, locale)
    : [];
  
  // 获取初始代码
  const starterCodes = await getStarterCodes(problem.id);
  
  // 解析 JSON 字段
  const constraints = content ? JSON.parse(content.constraints_json) as string[] : [];
  const followUps = content ? JSON.parse(content.follow_ups_json) as string[] : [];
  
  return {
    id: problem.id,
    displayId: identity.display_id,
    slug: identity.slug,
    title: content?.title || null,
    difficulty: problem.difficulty,
    category: problem.category,
    isPaidOnly: problem.is_paid_only === 1,
    site: identity.site,
    url: identity.url,
    tags,
    content: {
      statement: content?.statement_markdown || null,
      constraints,
      followUps,
      examples: examples.map(e => ({
        ordinal: e.ordinal,
        input: e.input_text,
        output: e.output_text,
        explanation: e.explanation,
      })),
    },
    hints,
    starterCodes: starterCodes.map(s => ({
      language: s.language,
      languageName: s.language_name,
      template: s.template,
    })),
  };
}

/**
 * 获取题目提示
 */
export async function getProblemHintsByIdentifier(
  identifier: string | number,
  site: string = 'leetcode.com',
  locale: string = 'en'
): Promise<string[]> {
  const isId = typeof identifier === 'number' || /^\d+$/.test(String(identifier));
  
  let identity: ProblemSourceIdentity | null;
  
  if (isId) {
    identity = await queryOne<ProblemSourceIdentity>(`
      SELECT * FROM problem_source_identity 
      WHERE (display_id = ? OR problem_id = ?) AND site = ?
    `, [String(identifier), String(identifier), site]);
  } else {
    identity = await queryOne<ProblemSourceIdentity>(`
      SELECT * FROM problem_source_identity 
      WHERE slug = ? AND site = ?
    `, [String(identifier), site]);
  }
  
  if (!identity) {
    return [];
  }
  
  const content = await queryOne<{ id: number }>(`
    SELECT id FROM problem_content 
    WHERE source_identity_id = ? AND locale = ? AND is_current = 1
  `, [identity.id, locale]);
  
  if (!content) {
    return [];
  }
  
  return getProblemHints(content.id, locale);
}

/**
 * 获取标签列表
 */
export async function getAllTags(): Promise<Array<{ code: string; name: string; source: string; count: number }>> {
  return queryAll<{ code: string; name: string; source: string; count: number }>(`
    SELECT t.code, t.name, t.source, COUNT(pt.problem_id) as count
    FROM tag t
    LEFT JOIN problem_tag pt ON pt.tag_id = t.id
    GROUP BY t.id
    ORDER BY count DESC
  `);
}

/**
 * 获取类别列表
 */
export async function getAllCategories(): Promise<Array<{ name: string; count: number }>> {
  return queryAll<{ name: string; count: number }>(`
    SELECT category as name, COUNT(*) as count
    FROM problem
    WHERE category IS NOT NULL
    GROUP BY category
    ORDER BY count DESC
  `);
}

// 辅助函数：获取题目标签代码列表
async function getProblemTags(problemId: number): Promise<string[]> {
  const tags = await queryAll<{ code: string }>(`
    SELECT t.code
    FROM tag t
    JOIN problem_tag pt ON pt.tag_id = t.id
    WHERE pt.problem_id = ?
  `, [problemId]);
  
  return tags.map(t => t.code);
}

// 辅助函数：获取题目标签详情
async function getProblemTagsWithDetails(problemId: number): Promise<Array<{ code: string; name: string; source: string }>> {
  return queryAll<{ code: string; name: string; source: string }>(`
    SELECT t.code, t.name, t.source
    FROM tag t
    JOIN problem_tag pt ON pt.tag_id = t.id
    WHERE pt.problem_id = ?
  `, [problemId]);
}

// 辅助函数：获取题目示例
async function getProblemExamples(contentId: number): Promise<ProblemExample[]> {
  return queryAll<ProblemExample>(`
    SELECT * FROM problem_example 
    WHERE content_id = ?
    ORDER BY ordinal
  `, [contentId]);
}

// 辅助函数：获取题目提示
async function getProblemHints(contentId: number, locale: string): Promise<string[]> {
  const hints = await queryAll<{ body: string }>(`
    SELECT body FROM problem_hint 
    WHERE content_id = ? AND locale = ?
    ORDER BY ordinal
  `, [contentId, locale]);
  
  return hints.map(h => h.body);
}

// 辅助函数：获取初始代码
async function getStarterCodes(problemId: number): Promise<StarterCode[]> {
  return queryAll<StarterCode>(`
    SELECT * FROM starter_code 
    WHERE problem_id = ? AND is_current = 1
    ORDER BY language
  `, [problemId]);
}
