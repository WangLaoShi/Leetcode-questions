/**
 * 做题记录服务
 */
import { getUsersDb, queryAll, queryOne, execute } from '../db/users.js';
import { queryAll as queryQuestionsAll } from '../db/questions.js';
import type { ProblemRecord, ProblemRecordStatus } from '../types/index.js';

/**
 * 创建或更新做题记录
 */
export async function upsertProblemRecord(params: {
  userId: number;
  problemId: number;
  slug: string;
  status?: ProblemRecordStatus;
  language?: string;
  viewedHints?: boolean;
  notes?: string;
}): Promise<ProblemRecord> {
  const now = new Date().toISOString();
  
  const {
    userId,
    problemId,
    slug,
    status = 'attempting',
    language,
    viewedHints,
    notes,
  } = params;
  
  // 检查是否已存在记录
  const existing = await queryOne<ProblemRecord>(
    'SELECT * FROM problem_records WHERE user_id = ? AND problem_id = ?',
    [userId, problemId]
  );
  
  if (existing) {
    // 更新现有记录
    const updates: string[] = [];
    const values: (string | number | null)[] = [];
    
    if (status !== undefined) {
      updates.push('status = ?');
      values.push(status);
      if (status === 'completed') {
        updates.push('completed_at = ?');
        values.push(now);
      }
    }
    if (language !== undefined) {
      updates.push('language = ?');
      values.push(language);
    }
    if (viewedHints !== undefined) {
      updates.push('viewed_hints = ?');
      values.push(viewedHints ? 1 : 0);
    }
    if (notes !== undefined) {
      updates.push('notes = ?');
      values.push(notes);
    }
    
    updates.push('updated_at = ?');
    values.push(now);
    values.push(existing.id);
    
    await execute(`UPDATE problem_records SET ${updates.join(', ')} WHERE id = ?`, values);
    
    const updated = await queryOne<ProblemRecord>('SELECT * FROM problem_records WHERE id = ?', [existing.id]);
    if (!updated) {
      throw new Error('更新记录失败');
    }
    return updated;
  } else {
    // 创建新记录
    const startedAt = status !== 'not_started' ? now : null;
    const completedAt = status === 'completed' ? now : null;
    
    const result = await execute(`
      INSERT INTO problem_records 
        (user_id, problem_id, slug, status, language, viewed_hints, started_at, completed_at, notes, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      userId,
      problemId,
      slug,
      status,
      language || null,
      viewedHints ? 1 : 0,
      startedAt,
      completedAt,
      notes || null,
      now,
      now
    ]);
    
    const record = await queryOne<ProblemRecord>('SELECT * FROM problem_records WHERE id = ?', [result.lastId]);
    if (!record) {
      throw new Error('创建记录失败');
    }
    return record;
  }
}

/**
 * 获取用户的做题记录列表
 */
export async function getUserRecords(
  userId: number,
  status?: ProblemRecordStatus
): Promise<ProblemRecord[]> {
  let sql = 'SELECT * FROM problem_records WHERE user_id = ?';
  const values: (string | number)[] = [userId];
  
  if (status) {
    sql += ' AND status = ?';
    values.push(status);
  }
  
  sql += ' ORDER BY updated_at DESC';
  
  return queryAll<ProblemRecord>(sql, values);
}

/**
 * 获取单个做题记录
 */
export async function getProblemRecord(userId: number, problemId: number): Promise<ProblemRecord | null> {
  const record = await queryOne<ProblemRecord>(
    'SELECT * FROM problem_records WHERE user_id = ? AND problem_id = ?',
    [userId, problemId]
  );
  
  return record;
}

/**
 * 获取做题统计
 */
export async function getRecordStats(userId: number): Promise<{
  total: number;
  byStatus: Record<ProblemRecordStatus, number>;
  byDifficulty: Record<string, number>;
  byCategory: Record<string, number>;
  recentRecords: ProblemRecord[];
}> {
  // 总数
  const totalResult = await queryOne<{ count: number }>(
    'SELECT COUNT(*) as count FROM problem_records WHERE user_id = ?',
    [userId]
  );
  const total = totalResult?.count || 0;
  
  // 按状态统计
  const byStatusRows = await queryAll<{ status: string; count: number }>(`
    SELECT status, COUNT(*) as count 
    FROM problem_records 
    WHERE user_id = ?
    GROUP BY status
  `, [userId]);
  
  const byStatus: Record<string, number> = {
    not_started: 0,
    attempting: 0,
    completed: 0,
  };
  byStatusRows.forEach(row => {
    byStatus[row.status] = row.count;
  });
  
  // 按难度统计（需要关联题目数据库）
  const byDifficulty: Record<string, number> = {
    easy: 0,
    medium: 0,
    hard: 0,
    unknown: 0,
  };
  
  // 按类别统计
  const byCategory: Record<string, number> = {};
  
  if (total > 0) {
    // 获取所有记录的 problem_id
    const records = await queryAll<{ problem_id: number }>(
      'SELECT problem_id FROM problem_records WHERE user_id = ?',
      [userId]
    );
    
    const problemIds = records.map(r => r.problem_id);
    
    if (problemIds.length > 0) {
      const placeholders = problemIds.map(() => '?').join(',');
      
      // 从题目数据库获取难度和类别
      const problems = await queryQuestionsAll<{ id: number; difficulty: string | null; category: string | null }>(`
        SELECT id, difficulty, category FROM problem WHERE id IN (${placeholders})
      `, problemIds);
      
      problems.forEach(p => {
        // 难度统计
        const diff = p.difficulty || 'unknown';
        byDifficulty[diff] = (byDifficulty[diff] || 0) + 1;
        
        // 类别统计
        const cat = p.category || 'unknown';
        byCategory[cat] = (byCategory[cat] || 0) + 1;
      });
    }
  }
  
  // 最近记录
  const recentRecords = await queryAll<ProblemRecord>(`
    SELECT * FROM problem_records 
    WHERE user_id = ?
    ORDER BY updated_at DESC
    LIMIT 10
  `, [userId]);
  
  return {
    total,
    byStatus: byStatus as Record<ProblemRecordStatus, number>,
    byDifficulty,
    byCategory,
    recentRecords,
  };
}
