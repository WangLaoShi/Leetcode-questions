/**
 * Express 应用配置
 */
import express from 'express';
import cors from 'cors';
import { config } from './config.js';

// 导入路由
import authRoutes from './routes/auth.js';
import problemRoutes from './routes/problems.js';
import recordRoutes from './routes/records.js';

export function createApp(): express.Application {
  const app = express();

  // 中间件
  app.use(cors({
    origin: config.server.corsOrigin,
    credentials: true,
  }));

  app.use(express.json());

  // 请求日志
  app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
    next();
  });

  // 路由
  app.use('/api/auth', authRoutes);
  app.use('/api/problems', problemRoutes);
  app.use('/api/records', recordRoutes);

  // 健康检查
  app.get('/api/health', (req, res) => {
    res.json({ 
      status: 'ok', 
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    });
  });

  // 404 处理
  app.use((req, res) => {
    res.status(404).json({ error: '接口不存在' });
  });

  // 错误处理
  app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
    console.error('服务器错误:', err);
    res.status(500).json({ 
      error: '服务器内部错误',
      message: process.env.NODE_ENV === 'development' ? err.message : undefined,
    });
  });

  return app;
}

export default createApp;
