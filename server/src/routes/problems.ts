/**
 * 题目路由
 */
import { Router, Request, Response } from 'express';
import * as problemService from '../services/problemService.js';
import { validate, problemListSchema } from '../middleware/validate.js';
import { requireAuth, optionalAuth } from '../middleware/auth.js';
import { requirePremium, checkMembership } from '../middleware/membership.js';

const router = Router();

/**
 * GET /api/problems
 * 获取题目列表（分页、搜索、筛选）
 */
router.get('/', validate(problemListSchema, 'query'), async (req: Request, res: Response) => {
  try {
    const result = await problemService.getProblemList(req.query as any);
    
    res.json({
      success: true,
      data: result,
    });
  } catch (err) {
    console.error('获取题目列表失败:', err);
    res.status(500).json({ error: '获取题目列表失败' });
  }
});

/**
 * GET /api/problems/tags
 * 获取所有标签
 */
router.get('/tags', async (req: Request, res: Response) => {
  try {
    const tags = await problemService.getAllTags();
    
    res.json({
      success: true,
      data: tags,
    });
  } catch (err) {
    res.status(500).json({ error: '获取标签列表失败' });
  }
});

/**
 * GET /api/problems/categories
 * 获取所有类别
 */
router.get('/categories', async (req: Request, res: Response) => {
  try {
    const categories = await problemService.getAllCategories();
    
    res.json({
      success: true,
      data: categories,
    });
  } catch (err) {
    res.status(500).json({ error: '获取类别列表失败' });
  }
});

/**
 * GET /api/problems/:identifier
 * 获取题目详情
 * identifier 可以是题号（display_id）或 slug
 */
router.get('/:identifier', optionalAuth, async (req: Request, res: Response) => {
  try {
    const { identifier } = req.params;
    const site = (req.query.site as string) || 'leetcode.com';
    const locale = (req.query.locale as string) || 'en';
    
    const problem = await problemService.getProblemDetail(identifier, site, locale);
    
    if (!problem) {
      res.status(404).json({ error: '题目不存在' });
      return;
    }
    
    // 检查用户是否有权限查看提示
    let canViewHints = false;
    if (req.user) {
      canViewHints = await checkMembership(req.user.userId);
    }
    
    // 如果无权查看提示，则隐藏提示内容
    const response = {
      ...problem,
      hints: canViewHints ? problem.hints : [],
      hintsLocked: !canViewHints,
    };
    
    res.json({
      success: true,
      data: response,
    });
  } catch (err) {
    console.error('获取题目详情失败:', err);
    res.status(500).json({ error: '获取题目详情失败' });
  }
});

/**
 * GET /api/problems/:identifier/hints
 * 获取题目提示（需要正式会员）
 */
router.get('/:identifier/hints', requireAuth, requirePremium, async (req: Request, res: Response) => {
  try {
    const { identifier } = req.params;
    const site = (req.query.site as string) || 'leetcode.com';
    const locale = (req.query.locale as string) || 'en';
    
    const hints = await problemService.getProblemHintsByIdentifier(identifier, site, locale);
    
    res.json({
      success: true,
      data: hints,
    });
  } catch (err) {
    res.status(500).json({ error: '获取提示失败' });
  }
});

export default router;
