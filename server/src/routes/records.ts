/**
 * 做题记录路由
 */
import { Router, Request, Response } from 'express';
import * as recordService from '../services/membershipService.js';
import { requireAuth } from '../middleware/auth.js';
import { validate, problemRecordSchema } from '../middleware/validate.js';
import type { ProblemRecordStatus } from '../types/index.js';

const router = Router();

// 所有记录相关接口都需要登录
router.use(requireAuth);

/**
 * GET /api/records
 * 获取我的做题记录列表
 */
router.get('/', async (req: Request, res: Response) => {
  try {
    const userId = req.user!.userId;
    const status = req.query.status as ProblemRecordStatus | undefined;
    
    const records = await recordService.getUserRecords(userId, status);
    
    res.json({
      success: true,
      data: records,
    });
  } catch (err) {
    res.status(500).json({ error: '获取做题记录失败' });
  }
});

/**
 * GET /api/records/stats
 * 获取做题统计
 */
router.get('/stats', async (req: Request, res: Response) => {
  try {
    const userId = req.user!.userId;
    const stats = await recordService.getRecordStats(userId);
    
    res.json({
      success: true,
      data: stats,
    });
  } catch (err) {
    res.status(500).json({ error: '获取统计失败' });
  }
});

/**
 * GET /api/records/:problemId
 * 获取某题的做题记录
 */
router.get('/:problemId', async (req: Request, res: Response) => {
  try {
    const userId = req.user!.userId;
    const problemId = parseInt(req.params.problemId, 10);
    
    if (isNaN(problemId)) {
      res.status(400).json({ error: '无效的题目 ID' });
      return;
    }
    
    const record = await recordService.getProblemRecord(userId, problemId);
    
    res.json({
      success: true,
      data: record,
    });
  } catch (err) {
    res.status(500).json({ error: '获取做题记录失败' });
  }
});

/**
 * POST /api/records
 * 创建或更新做题记录
 */
router.post('/', validate(problemRecordSchema), async (req: Request, res: Response) => {
  try {
    const userId = req.user!.userId;
    const { problemId, slug, status, language, viewedHints, notes } = req.body;
    
    const record = await recordService.upsertProblemRecord({
      userId,
      problemId,
      slug,
      status,
      language,
      viewedHints,
      notes,
    });
    
    res.status(201).json({
      success: true,
      data: record,
    });
  } catch (err) {
    console.error('保存做题记录失败:', err);
    res.status(500).json({ error: '保存做题记录失败' });
  }
});

export default router;
