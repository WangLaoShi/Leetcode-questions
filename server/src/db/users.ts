/**
 * 用户数据库连接（读写）
 * 使用 sql.js（纯 JavaScript SQLite 实现）
 */
import initSqlJs, { Database } from 'sql.js';
import fs from 'fs';
import path from 'path';
import { config } from '../config.js';

let db: Database | null = null;
let saveTimer: NodeJS.Timeout | null = null;

// 确保数据目录存在
function ensureDataDir(): void {
  const dir = path.dirname(config.paths.usersDb);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// 初始化数据库表结构
function initTables(database: Database): void {
  database.run(`
    -- 用户表
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      last_login_at TEXT,
      login_count INTEGER DEFAULT 0
    );

    -- 刷新令牌表（用于主动失效）
    CREATE TABLE IF NOT EXISTS refresh_tokens (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      token TEXT UNIQUE NOT NULL,
      expires_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      revoked INTEGER DEFAULT 0
    );

    -- 登录历史（用于统计登录次数）
    CREATE TABLE IF NOT EXISTS login_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      login_at TEXT NOT NULL,
      ip_address TEXT,
      user_agent TEXT
    );

    -- 做题记录
    CREATE TABLE IF NOT EXISTS problem_records (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      problem_id INTEGER NOT NULL,
      slug TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'attempting',
      language TEXT,
      viewed_hints INTEGER DEFAULT 0,
      started_at TEXT,
      completed_at TEXT,
      notes TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(user_id, problem_id)
    );

    -- 索引
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
    CREATE INDEX IF NOT EXISTS idx_login_history_user ON login_history(user_id);
    CREATE INDEX IF NOT EXISTS idx_problem_records_user ON problem_records(user_id);
    CREATE INDEX IF NOT EXISTS idx_problem_records_status ON problem_records(user_id, status);
  `);
}

// 保存数据库到文件（防抖）
function scheduleSave(): void {
  if (saveTimer) {
    clearTimeout(saveTimer);
  }
  saveTimer = setTimeout(() => {
    if (db) {
      const data = db.export();
      const buffer = Buffer.from(data);
      fs.writeFileSync(config.paths.usersDb, buffer);
    }
  }, 1000);
}

export async function getUsersDb(): Promise<Database> {
  if (!db) {
    ensureDataDir();
    const SQL = await initSqlJs();
    
    // 如果数据库文件存在，加载它
    if (fs.existsSync(config.paths.usersDb)) {
      const buffer = fs.readFileSync(config.paths.usersDb);
      db = new SQL.Database(buffer);
    } else {
      db = new SQL.Database();
    }
    
    // 初始化表结构
    initTables(db);
    // 立即保存一次
    scheduleSave();
  }
  return db;
}

export function closeUsersDb(): void {
  if (saveTimer) {
    clearTimeout(saveTimer);
  }
  if (db) {
    // 最后一次保存
    const data = db.export();
    const buffer = Buffer.from(data);
    fs.writeFileSync(config.paths.usersDb, buffer);
    db.close();
    db = null;
  }
}

// 辅助函数：执行查询并返回结果数组
export async function queryAll<T = any>(sql: string, params: any[] = []): Promise<T[]> {
  const database = await getUsersDb();
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

// 辅助函数：执行写操作
export async function execute(sql: string, params: any[] = []): Promise<{ lastId: number; changes: number }> {
  const database = await getUsersDb();
  database.run(sql, params);
  scheduleSave();
  
  // 获取最后插入的 ID 和受影响行数
  const lastId = database.exec("SELECT last_insert_rowid() as id")[0]?.values[0][0] as number || 0;
  const changes = database.getRowsModified();
  
  return { lastId, changes };
}
