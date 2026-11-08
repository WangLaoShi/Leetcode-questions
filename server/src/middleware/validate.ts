/**
 * 请求验证中间件
 */
import { Request, Response, NextFunction } from 'express';
import { z, ZodSchema } from 'zod';

/**
 * 创建验证中间件
 */
export function validate(schema: ZodSchema, source: 'body' | 'query' | 'params' = 'body') {
  return (req: Request, res: Response, next: NextFunction): void => {
    const result = schema.safeParse(req[source]);
    
    if (!result.success) {
      const errors = result.error.errors.map(e => ({
        field: e.path.join('.'),
        message: e.message,
      }));
      res.status(400).json({ error: '请求参数错误', details: errors });
      return;
    }
    
    req[source] = result.data;
    next();
  };
}

// 常用验证 Schema
export const registerSchema = z.object({
  username: z.string().min(3, '用户名至少3个字符').max(20, '用户名最多20个字符')
    .regex(/^[a-zA-Z0-9_]+$/, '用户名只能包含字母、数字和下划线'),
  email: z.string().email('邮箱格式不正确'),
  password: z.string().min(6, '密码至少6个字符'),
});

export const loginSchema = z.object({
  username: z.string().min(1, '请输入用户名或邮箱'),
  password: z.string().min(1, '请输入密码'),
});

export const problemListSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
  search: z.string().optional(),
  difficulty: z.enum(['easy', 'medium', 'hard']).optional(),
  category: z.enum(['algorithm', 'database', 'shell', 'concurrency', 'javascript', 'pandas']).optional(),
  tag: z.string().optional(),
  site: z.enum(['leetcode.com', 'leetcode.cn']).default('leetcode.com'),
  locale: z.enum(['en', 'zh-CN']).default('en'),
  sort: z.enum(['id', 'display_id', 'title', 'difficulty']).default('display_id'),
  order: z.enum(['asc', 'desc']).default('asc'),
});

export const problemRecordSchema = z.object({
  problemId: z.number().int().positive(),
  slug: z.string().min(1),
  status: z.enum(['not_started', 'attempting', 'completed']).optional(),
  language: z.string().optional(),
  viewedHints: z.boolean().optional(),
  notes: z.string().optional(),
});

export type RegisterInput = z.infer<typeof registerSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type ProblemListInput = z.infer<typeof problemListSchema>;
export type ProblemRecordInput = z.infer<typeof problemRecordSchema>;
