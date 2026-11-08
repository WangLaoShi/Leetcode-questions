/**
 * 认证服务
 */
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { getUsersDb, queryOne, execute } from '../db/users.js';
import { config } from '../config.js';
import type { User, PublicUser, JwtPayload } from '../types/index.js';

// 密码加密轮数
const SALT_ROUNDS = 10;

/**
 * 注册新用户
 */
export async function register(
  username: string, 
  email: string, 
  password: string
): Promise<{ user: PublicUser; tokens: { accessToken: string; refreshToken: string } }> {
  const now = new Date().toISOString();
  
  // 检查用户名和邮箱是否已存在
  const existing = await queryOne<{ id: number }>(
    'SELECT id FROM users WHERE username = ? OR email = ?',
    [username, email]
  );
  
  if (existing) {
    throw new Error('用户名或邮箱已存在');
  }
  
  // 加密密码
  const passwordHash = await bcrypt.hash(password, SALT_ROUNDS);
  
  // 插入用户
  const result = await execute(`
    INSERT INTO users (username, email, password_hash, created_at, updated_at, login_count)
    VALUES (?, ?, ?, ?, ?, 0)
  `, [username, email, passwordHash, now, now]);
  
  const userId = result.lastId;
  
  // 获取新用户信息
  const user = await queryOne<User>('SELECT * FROM users WHERE id = ?', [userId]);
  
  if (!user) {
    throw new Error('创建用户失败');
  }
  
  // 生成令牌
  const tokens = generateTokens({ userId: user.id, username: user.username });
  
  // 保存刷新令牌
  await saveRefreshToken(user.id, tokens.refreshToken, tokens.refreshTokenExpiry);
  
  return {
    user: toPublicUser(user),
    tokens,
  };
}

/**
 * 用户登录
 */
export async function login(
  usernameOrEmail: string,
  password: string,
  ipAddress?: string,
  userAgent?: string
): Promise<{ user: PublicUser; tokens: { accessToken: string; refreshToken: string } }> {
  // 查找用户（支持用户名或邮箱登录）
  const user = await queryOne<User>(
    'SELECT * FROM users WHERE username = ? OR email = ?',
    [usernameOrEmail, usernameOrEmail]
  );
  
  if (!user) {
    throw new Error('用户名或密码错误');
  }
  
  // 验证密码
  const isValid = await bcrypt.compare(password, user.password_hash);
  if (!isValid) {
    throw new Error('用户名或密码错误');
  }
  
  // 更新登录信息
  const now = new Date().toISOString();
  await execute(`
    UPDATE users 
    SET last_login_at = ?, login_count = login_count + 1, updated_at = ?
    WHERE id = ?
  `, [now, now, user.id]);
  
  // 记录登录历史
  await execute(`
    INSERT INTO login_history (user_id, login_at, ip_address, user_agent)
    VALUES (?, ?, ?, ?)
  `, [user.id, now, ipAddress || null, userAgent || null]);
  
  // 生成令牌
  const tokens = generateTokens({ userId: user.id, username: user.username });
  
  // 保存刷新令牌
  await saveRefreshToken(user.id, tokens.refreshToken, tokens.refreshTokenExpiry);
  
  // 重新获取用户信息（包含更新后的 login_count）
  const updatedUser = await queryOne<User>('SELECT * FROM users WHERE id = ?', [user.id]);
  
  if (!updatedUser) {
    throw new Error('获取用户信息失败');
  }
  
  return {
    user: toPublicUser(updatedUser),
    tokens,
  };
}

/**
 * 刷新访问令牌
 */
export async function refreshAccessToken(refreshToken: string): Promise<{ accessToken: string; refreshToken: string }> {
  // 验证刷新令牌
  let payload: JwtPayload;
  try {
    payload = jwt.verify(refreshToken, config.jwt.secret) as JwtPayload;
  } catch {
    throw new Error('无效的刷新令牌');
  }
  
  // 检查令牌是否存在且未撤销
  const storedToken = await queryOne<{ user_id: number; expires_at: string }>(`
    SELECT user_id, expires_at FROM refresh_tokens 
    WHERE token = ? AND user_id = ? AND revoked = 0 AND expires_at > ?
  `, [refreshToken, payload.userId, new Date().toISOString()]);
  
  if (!storedToken) {
    throw new Error('刷新令牌已失效');
  }
  
  // 获取用户信息
  const user = await queryOne<User>('SELECT * FROM users WHERE id = ?', [payload.userId]);
  if (!user) {
    throw new Error('用户不存在');
  }
  
  // source_tokens
  await execute('UPDATE refresh_tokens SET revoked = 1 WHERE token = ?', [refreshToken]);
  
  // 生成新令牌
  const tokens = generateTokens({ userId: user.id, username: user.username });
  await saveRefreshToken(user.id, tokens.refreshToken, tokens.refreshTokenExpiry);
  
  return tokens;
}

/**
 * 登出（撤销刷新令牌）
 */
export async function logout(refreshToken: string): Promise<void> {
  await execute('UPDATE refresh_tokens SET revoked = 1 WHERE token = ?', [refreshToken]);
}

/**
 * 获取用户信息
 */
export async function getUser(userId: number): Promise<PublicUser | null> {
  const user = await queryOne<User>('SELECT * FROM users WHERE id = ?', [userId]);
  return user ? toPublicUser(user) : null;
}

// 生成访问令牌和刷新令牌
function generateTokens(payload: JwtPayload): { 
  accessToken: string; 
  refreshToken: string; 
  refreshTokenExpiry: string;
} {
  // 访问令牌 15 分钟过期
  const accessToken = jwt.sign(payload, config.jwt.secret, {
    expiresIn: 15 * 60, // 15 minutes in seconds
  });
  
  // 刷新令牌 7 天过期
  const refreshTokenExpiry = new Date();
  refreshTokenExpiry.setDate(refreshTokenExpiry.getDate() + 7);
  
  const refreshToken = jwt.sign(
    { ...payload, exp: Math.floor(refreshTokenExpiry.getTime() / 1000) },
    config.jwt.secret
  );
  
  return { accessToken, refreshToken, refreshTokenExpiry: refreshTokenExpiry.toISOString() };
}

// 保存刷新令牌
async function saveRefreshToken(userId: number, token: string, expiresAt: string): Promise<void> {
  const now = new Date().toISOString();
  await execute(`
    INSERT INTO refresh_tokens (user_id, token, expires_at, created_at)
    VALUES (?, ?, ?, ?)
  `, [userId, token, expiresAt, now]);
}

// 转换为公开用户信息
function toPublicUser(user: User): PublicUser {
  const { password_hash, ...publicUser } = user;
  return publicUser;
}
