import { PathLike } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const config = {
  // 路径配置
  paths: {
    // 题目数据库路径（现有，只读）
    questionsDb: path.resolve(__dirname, '../../db/question-bank.sqlite'),
    // 用户数据库路径（新建）
    usersDb: path.resolve(__dirname, '../data/users.sqlite'),
  },
  
  // JWT 配置
  jwt: {
    // 生产环境应该使用环境变量
    secret: process.env.JWT_SECRET || 'your-secret-key-change-in-production',
    accessTokenExpiry: '15m',
    refreshTokenExpiry: '7d',
  },
  
  // 服务器配置
  server: {
    port: parseInt(process.env.PORT || '3000', 10),
    corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  },
  
  // 会员配置
  membership: {
    // 新会员升级条件：注册满此小时数 或 登录满此次数
    upgradeHours: 24,
    upgradeLoginCount: 10,
  },
};
