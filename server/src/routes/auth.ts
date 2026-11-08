/**
 * 认证路由
 */
import { Router, Request, Response } from 'express';
import * as authService from '../services/authService.js';
import { validate, registerSchema, loginSchema } from '../middleware/validate.js';
import { requireAuth } from '../middleware/auth.js';
import { getMembershipInfo } from '../middleware/membership.js';

const router = Router();

/**
 * POST /api/auth/register
 * 注册新用户
 */
router.post('/register', validate(registerSchema), async (req: Request, res: Response) => {
  try {
    const { username, email, password } = req.body;
    const result = await authService.register(username, email, password);
    
    res.status(201).json({
      success: true,
      data: {
        user: result.user,
        tokens: result.tokens,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : '注册失败';
    res.status(400).json({ error: message });
  }
});

/**
 * POST /api/auth/login
 * 用户登录
 */
router.post('/login', validate(loginSchema), async (req: Request, res: Response) => {
  try {
    const { username, password } = req.body;
    const ipAddress = req.ip || req.socket.remoteAddress;
    const userAgent = req.get('user-agent');
    
    const result = await authService.login(username, password, ipAddress, userAgent);
    
    res.json({
      success: true,
      data: {
        user: result.user,
        tokens: result.tokens,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : '登录失败';
    res.status(401).json({ error: message });
  }
});

/**
 * POST /api/auth/refresh
 * 刷新访问令牌
 */
router.post('/refresh', async (req: Request, res: Response) => {
  try {
    const { refreshToken } = req.body;
    
    if (!refreshToken) {
      res.status(400).json({ error: '缺少刷新令牌' });
      return;
    }
    
    const tokens = await authService.refreshAccessToken(refreshToken);
    
    res.json({
      success: true,
      data: tokens,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : '刷新令牌失败';
    res.status(401).json({ error: message });
  }
});

/**
 * POST /api/auth/logout
 * 登出
 */
router.post('/logout', requireAuth, async (req: Request, res: Response) => {
  try {
    const { refreshToken } = req.body;
    
    if (refreshToken) {
      await authService.logout(refreshToken);
    }
    
    res.json({
      success: true,
      message: '已登出',
    });
  } catch (err) {
    res.status(500).json({ error: '登出失败' });
  }
});

/**
 * GET /api/auth/me
 * 获取当前用户信息
 */
router.get('/me', requireAuth, async (req: Request, res: Response) => {
  try {
    const user = await authService.getUser(req.user!.userId);
    
    if (!user) {
      res.status(404).json({ error: '用户不存在' });
      return;
    }
    
    const membership = await getMembershipInfo(user.id);
    
    res.json({
      success: true,
      data: {
        user,
        membership,
      },
    });
  } catch (err) {
    res.status(500).json({ error: '获取用户信息失败' });
  }
});

export default router;
