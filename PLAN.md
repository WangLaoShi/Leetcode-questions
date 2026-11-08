# LeetCode 题目库网站 - 执行计划

## 项目概述

基于现有 SQLite 题目数据库，构建一个 LeetCode 风格的题目浏览网站。

**技术栈**：
- 后端：Node.js + Express + better-sqlite3
- 前端：React + TypeScript + Vite
- 样式：Tailwind CSS（LeetCode 风格）
- 认证：JWT + bcrypt
- 数据库：SQLite（题目数据）+ SQLite（用户数据）

---

## 功能需求

### 核心功能
1. **题目浏览**：列表展示，分页加载
2. **搜索**：按题号、slug、标题搜索
3. **筛选**：按难度、类别、标签筛选
4. **中英文切换**：题目内容支持 en / zh-CN
5. **题目详情**：题干（Markdown 渲染）、示例、提示、初始代码模板

### 用户系统
1. **注册**：用户名 + 邮箱 + 密码
2. **登录**：用户名/邮箱 + 密码
3. **会话管理**：JWT token，自动续期

### 做题记录
1. **标记做题状态**：未开始 / 尝试中 / 已完成
2. **记录提交**：保存做题时间、使用的语言、是否看提示
3. **做题列表**：查看自己的做题历史
4. **进度统计**：按难度、类别统计完成数量

### 会员等级系统
| 等级 | 条件 | 权限 |
|------|------|------|
| 新会员 | 注册 < 24小时 且 登录 < 10次 | 只能看题干，不能看提示 |
| 正式会员 | 注册 >= 24小时 或 登录 >= 10次 | 可看所有内容（包括提示） |

---

## 项目结构

```
leetcode-questions/
├── db/
│   └── question-bank.sqlite          # 现有题目数据库
├── server/                           # 后端
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── index.ts                  # 入口
│   │   ├── app.ts                    # Express 应用
│   │   ├── config.ts                 # 配置
│   │   ├── db/
│   │   │   ├── questions.ts          # 题目数据库连接
│   │   │   └── users.ts              # 用户数据库连接
│   │   ├── middleware/
│   │   │   ├── auth.ts               # JWT 认证中间件
│   │   │   ├── membership.ts         # 会员等级中间件
│   │   │   └── validate.ts           # 请求验证
│   │   ├── routes/
│   │   │   ├── auth.ts               # 注册/登录/刷新token
│   │   │   ├── problems.ts           # 题目相关 API
│   │   │   └── user.ts               # 用户信息
│   │   ├── services/
│   │   │   ├── authService.ts
│   │   │   ├── problemService.ts
│   │   │   └── membershipService.ts
│   │   └── types/
│   │       └── index.ts
│   └── data/
│       └── users.sqlite              # 用户数据库文件
├── client/                           # 前端
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   └── client.ts             # Axios 封装
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── Footer.tsx
│   │   │   ├── ProblemList/
│   │   │   │   ├── ProblemTable.tsx
│   │   │   │   ├── ProblemCard.tsx
│   │   │   │   ├── FilterPanel.tsx
│   │   │   │   └── SearchBar.tsx
│   │   │   ├── ProblemDetail/
│   │   │   │   ├── Statement.tsx
│   │   │   │   ├── Examples.tsx
│   │   │   │   ├── Hints.tsx
│   │   │   │   ├── StarterCode.tsx
│   │   │   │   └── LockedContent.tsx
│   │   │   ├── Auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── RegisterForm.tsx
│   │   │   └── common/
│   │   │       ├── Button.tsx
│   │   │       ├── Input.tsx
│   │   │       ├── Modal.tsx
│   │   │       └── Loading.tsx
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── ProblemsPage.tsx
│   │   │   ├── ProblemDetailPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   ├── ProfilePage.tsx
│   │   │   └── RecordsPage.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useProblems.ts
│   │   │   └── useMembership.ts
│   │   ├── contexts/
│   │   │   ├── AuthContext.tsx
│   │   │   └── LocaleContext.tsx
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── utils/
│   │   │   ├── markdown.ts
│   │   │   └── membership.ts
│   │   └── styles/
│   │       └── globals.css
│   └── public/
└── README.md
```

---

## 数据库设计

### 题目数据库（现有，只读，不修改）

**路径**：`db/question-bank.sqlite`

已验证与 `migrations/sqlite/001_init.sql` 一致。后端只读连接，不做任何写操作。

主要使用表：
- `problem` — 题目主表
- `problem_source_identity` — 站点、slug、展示题号
- `problem_content` — 题干（多语言、多版本）
- `problem_example` — 示例
- `problem_hint` — 提示
- `starter_code` — 初始代码模板
- `tag` / `problem_tag` — 标签

### 用户数据库（新建，独立存放）

**路径**：`server/data/users.sqlite`（新建，与题目数据库分开）

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,          -- ISO 8601
    updated_at TEXT NOT NULL,
    last_login_at TEXT,
    login_count INTEGER DEFAULT 0
);

-- 会话/刷新令牌表（可选，用于主动失效）
CREATE TABLE refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked INTEGER DEFAULT 0
);

-- 登录历史（用于统计登录次数）
CREATE TABLE login_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    login_at TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT
);

-- 做题记录
CREATE TABLE problem_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    problem_id INTEGER NOT NULL,              -- 对应题目数据库的 problem.id
    slug TEXT NOT NULL,                       -- 冗余存储，方便查询
    status TEXT NOT NULL DEFAULT 'attempting', -- 'not_started' | 'attempting' | 'completed'
    language TEXT,                            -- 使用的编程语言
    viewed_hints INTEGER DEFAULT 0,           -- 是否查看了提示
    started_at TEXT,                          -- 开始做题时间
    completed_at TEXT,                        -- 完成时间
    notes TEXT,                               -- 用户笔记
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, problem_id)
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_login_history_user ON login_history(user_id);
CREATE INDEX idx_problem_records_user ON problem_records(user_id);
CREATE INDEX idx_problem_records_status ON problem_records(user_id, status);
```

---

## API 设计

### 认证 API

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 注册 | 否 |
| POST | `/api/auth/login` | 登录 | 否 |
| POST | `/api/auth/refresh` | 刷新 token | 否（需 refresh token） |
| POST | `/api/auth/logout` | 登出 | 是 |
| GET | `/api/auth/me` | 获取当前用户信息 | 是 |

### 题目 API

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/api/problems` | 题目列表（分页、筛选、搜索） | 否 |
| GET | `/api/problems/:id` | 题目详情 | 否* |
| GET | `/api/problems/:id/content` | 题干内容（指定语言） | 否* |
| GET | `/api/problems/:id/examples` | 示例列表 | 否 |
| GET | `/api/problems/:id/hints` | 提示列表 | 是（需正式会员） |
| GET | `/api/problems/:id/starter-code` | 初始代码模板 | 否 |
| GET | `/api/tags` | 标签列表 | 否 |
| GET | `/api/categories` | 类别列表 | 否 |

### 做题记录 API

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| GET | `/api/records` | 我的做题记录列表 | 是 |
| POST | `/api/records` | 创建/更新做题记录 | 是 |
| GET | `/api/records/:problemId` | 获取某题的记录 | 是 |
| GET | `/api/records/stats` | 做题统计（按难度/类别） | 是 |

> *注：题目列表和基础详情公开访问；hints 接口需要正式会员权限。

### 查询参数

**GET `/api/problems`**：
```
?page=1              # 页码，默认 1
&limit=20            # 每页条数，默认 20
&search=two-sum      # 搜索（题号/slug/标题）
&difficulty=easy     # 难度筛选
&category=algorithm  # 类别筛选
&tag=array           # 标签筛选
&site=leetcode.com   # 站点
&locale=en           # 语言
&sort=id             # 排序字段
&order=asc           # 排序方向
```

---

## 会员等级逻辑

```typescript
// 判断是否为正式会员
function isPremiumMember(user: User): boolean {
    const createdAt = new Date(user.created_at);
    const now = new Date();
    const hoursSinceRegistration = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60);
    
    // 注册满 24 小时，或登录次数 >= 10
    return hoursSinceRegistration >= 24 || user.login_count >= 10;
}

// 中间件
function requirePremium(req, res, next) {
    if (!req.user) {
        return res.status(401).json({ error: '请先登录' });
    }
    if (!isPremiumMember(req.user)) {
        return res.status(403).json({ 
            error: '此内容需要正式会员权限',
            hint: '注册满24小时或登录满10次后自动升级'
        });
    }
    next();
}
```

---

## 前端页面设计

### 1. 首页 (HomePage)
- 网站介绍
- 快速搜索入口
- 题目统计（总数、各难度数量）
- 随机一题

### 2. 题目列表页 (ProblemsPage)
- LeetCode 风格表格：题号 | 标题 | 难度 | 类别 | 标签
- 顶部搜索栏
- 左侧筛选面板（难度、类别、标签）
- 分页组件
- 语言切换按钮（EN / 中文）

### 3. 题目详情页 (ProblemDetailPage)
- 左侧：题干（Markdown 渲染）
- 右侧：示例、提示、初始代码
- 顶部：题号、标题、难度、标签、语言切换
- 提示区域：非会员显示锁定遮罩 + 升级提示

### 4. 登录/注册页
- 简洁表单
- 表单验证
- 错误提示
- 跳转回原页面

### 5. 个人中心 (ProfilePage)
- 用户信息
- 会员等级 & 升级进度
- 注册时间、登录次数
- 修改密码（可选）

### 6. 做题记录 (RecordsPage)
- 做题列表：题号、标题、状态、语言、时间
- 状态筛选：全部 / 尝试中 / 已完成
- 进度统计：按难度、类别的完成数量图表
- 点击跳转题目详情

---

## UI 风格参考

采用 LeetCode 风格：
- 主色调：深色侧边栏 + 白色内容区
- 难度颜色：Easy=绿, Medium=橙, Hard=红
- 代码块：深色背景 + 语法高亮
- 响应式布局

---

## 实施步骤

### 阶段 1：后端基础（预计 2-3 小时）
1. 初始化 Node.js 项目，安装依赖
2. 配置 TypeScript
3. 连接题目数据库（只读）
4. 创建用户数据库
5. 实现基础 Express 服务器

### 阶段 2：认证系统（预计 2-3 小时）
1. 实现注册 API
2. 实现登录 API（密码验证 + JWT 生成）
3. 实现 token 刷新
4. 实现认证中间件
5. 实现会员等级中间件

### 阶段 3：题目 API（预计 2-3 小时）
1. 实现题目列表 API（分页、搜索、筛选）
2. 实现题目详情 API
3. 实现题干内容 API（多语言支持）
4. 实现示例、提示、模板 API
5. 实现标签、类别列表 API

### 阶段 3.5：做题记录 API（预计 1-2 小时）
1. 实现做题记录 CRUD API
2. 实现做题统计 API

### 阶段 4：前端基础（预计 2-3 小时）
1. 初始化 React + Vite + TypeScript 项目
2. 配置 Tailwind CSS
3. 搭建路由结构
4. 实现 AuthContext 和 LocaleContext
5. 封装 API 客户端

### 阶段 5：前端页面（预计 5-7 小时）
1. 实现 Layout 组件（Header、Sidebar、Footer）
2. 实现首页
3. 实现题目列表页（表格、搜索、筛选、分页）
4. 实现题目详情页（Markdown 渲染、代码高亮、锁定内容、做题状态标记）
5. 实现登录/注册页
6. 实现个人中心
7. 实现做题记录页（列表、统计图表）

### 阶段 6：联调与优化（预计 2-3 小时）
1. 前后端联调
2. 错误处理完善
3. 加载状态优化
4. 响应式适配
5. 性能优化（虚拟滚动、缓存）

### 阶段 7：部署准备（预计 1-2 小时）
1. 环境变量配置
2. 构建脚本
3. 生产部署文档

**总计：约 17-26 小时**

---

## 关键依赖

### 后端
```json
{
    "express": "^4.18.0",
    "better-sqlite3": "^9.0.0",
    "bcryptjs": "^2.4.3",
    "jsonwebtoken": "^9.0.0",
    "cors": "^2.8.5",
    "zod": "^3.22.0"
}
```

### 前端
```json
{
    "react": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "rehype-highlight": "^7.0.0",
    "tailwindcss": "^3.4.0",
    "@headlessui/react": "^1.7.0"
}
```

---

## 已确认事项

1. **用户数据库位置**：`server/data/users.sqlite`，与题目数据库分开
2. **会员限制范围**：只限制 `hints`（提示）接口，题干和示例公开
3. **做题记录功能**：包含，支持标记状态、记录时间、统计进度
4. **部署方式**：待确认（本地运行 / 云服务）

---

## 下一步

确认此计划后，按阶段顺序实施。每个阶段完成后进行验证，确保功能正常。
