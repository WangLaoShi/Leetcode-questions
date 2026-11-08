/**
 * 会员等级中间件
 * 新会员（注册 < 24小时 且 登录 < 10次）不能访问 hints
 */
import { Request, Response, NextFunction } from 'express';
import { queryOne } from '../db/users.js';
import { config } from '../config.js';
import type { User } from '../types/index.js';

// 扩展 Express Request 类型
declare global {
  namespace Express {
    interface Request {
      isPremiumMember?: boolean;
    }
  }
}

/**
 * 判断用户是否为正式会员
 */
export async function checkMembership(userId: number): Promise<boolean> {
  const user = await queryOne<User>('SELECT * FROM users WHERE id = ?', [userId]);
  
  if (!user) {
    return false;
  }
  
  return isPremiumMember(user);
}

/**
 * 判断用户是否为正式会员
 * 条件：注册 >= 24小时 或 登录 >= 10次
 */
export function isPremiumMember(user: User): boolean {
  const createdAt = new Date(user.created_at);
  const now = new Date();
  const hoursSinceRegistration = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60);
  
  return hoursSinceRegistration >= config.membership.upgradeHours || 
         user.login_count >= config.membership.upgradeLoginCount;
}

/**
 * 获取会员状态信息
 */
export async function getMembershipInfo(userId: number): Promise<{
  isPremium: boolean;
  hoursRemaining: number;
  loginsRemaining: number;
}> {
  const user = await queryOne<User>('SELECT * FROM users WHERE id = ?', [userId]);
  
  if (!user) {
    return { isPremium: false, hoursRemaining: 0, loginsRemaining: 0 };
  }
  
  const createdAt = new Date(user.created_at);
  const now = new Date();
  const hoursSinceRegistration = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60);
  
  const hoursRemaining = Math.max(0, config.membership.upgradeHours - hoursSinceRegistration);
  const loginsRemaining = Math.max(0, config.membership.upgradeLoginCount - user.login_count);
  
  return {
    isPremium: isPremiumMember(user),
    hoursRemaining: Math.ceil(hoursRemaining),
    loginsRemaining,
  };
}

/**
 * 要求正式会员权限
 */
export async function requirePremium(req: Request, res: Response, next: NextFunction): Promise<void> {
  if (!req.user) {
    res.status(401).json({ error: '请先登录' });
    return;
  }
  
  const isPremium = await checkMembership(req.user.userId);
  
  if (!isPremium) {
    const info = await getMembershipInfo(req.user.userId);
    res.status(403).json({ 
      error: '此内容需要正式会员权限',
      hint: `注册满${config.membership.upgradeHours}小时（还需${info.hoursRemaining}小时）或登录满${config.membership.upgradeLoginCount}次（还需${info.loginsRemaining}次）后自动升级`,
    });
    return;
  }
  
  next();
}
