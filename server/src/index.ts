/**
 * 服务器入口
 */
import { createApp } from './app.js';
import { config } from './config.js';
import { getQuestionsDb, closeQuestionsDb } from './db/questions.js';
import { getUsersDb, closeUsersDb } from './db/users.js';

async function main() {
  console.log('正在初始化数据库...');
  
  // 初始化数据库连接
  await getQuestionsDb();
  console.log('✓ 题目数据库已加载（只读）');
  
  await getUsersDb();
  console.log('✓ 用户数据库已就绪');
  
  // 创建并启动服务器
  const app = createApp();
  
  const server = app.listen(config.server.port, () => {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   LeetCode 题目库 API 服务器                              ║
║                                                           ║
║   地址: http://localhost:${config.server.port}                        ║
║   环境: ${process.env.NODE_ENV || 'development'}                                    ║
║                                                           ║
║   API 端点:                                               ║
║   - POST /api/auth/register    注册                       ║
║   - POST /api/auth/login       登录                       ║
║   - GET  /api/auth/me          当前用户                    ║
║   - GET  /api/problems         题目列表                    ║
║   - GET  /api/problems/:id     题目详情                    ║
║   - GET  /api/problems/:id/hints  题目提示（需会员）       ║
║   - GET  /api/records          做题记录                    ║
║   - POST /api/records          保存记录                    ║
║   - GET  /api/records/stats    做题统计                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    `);
  });

  // 优雅关闭
  function shutdown() {
    console.log('\n正在关闭服务器...');
    
    server.close(async () => {
      console.log('HTTP 服务器已关闭');
      
      closeQuestionsDb();
      closeUsersDb();
      
      console.log('数据库连接已关闭');
      process.exit(0);
    });
    
    // 强制关闭超时
    setTimeout(() => {
      console.error('强制关闭');
      process.exit(1);
    }, 10000);
  }

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}

main().catch(err => {
  console.error('启动失败:', err);
  process.exit(1);
});
