/**
 * 题目数据库连接（只读）
 * 使用 sql.js（纯 JavaScript SQLite 实现）
 */
import initSqlJs, { Database } from 'sql.js';
import fs from 'fs';
import { config } from '../config.js';

let db: Database | null = null;

export async function getQuestionsDb(): Promise<Database> {
  if (!db) {
    const SQL = await initSqlJs();
    const buffer = fs.readFileSync(config.paths.questionsDb);
    db = new SQL.Database(buffer);
  }
  return db;
}

export function closeQuestionsDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}

// 辅助函数：执行查询并返回结果数组
export async function queryAll<T = any>(sql: string, params: any[] = []): Promise<T[]> {
  const database = await getQuestionsDb();
  const stmt = database.prepare(sql);
  stmt.bind(params);
  
  const results: T[] = [];
  while (stmt.step()) {
    results.push(stmt.getAsObject() as T);
  }
  stmt.free();
  
  return results;
}

// 辅助函数：执行查询并返回单个结果
export async function queryOne<T = any>(sql: string, params: any[] = []): Promise<T | null> {
  const results = await queryAll<T>(sql, params);
  return results[0] || null;
}
