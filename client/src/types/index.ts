/**
 * 类型定义
 */

// 用户
export interface User {
  id: number;
  username: string;
  email: string;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  login_count: number;
}

// 会员信息
export interface MembershipInfo {
  isPremium: boolean;
  hoursRemaining: number;
  loginsRemaining: number;
}

// 题目列表项
export interface ProblemListItem {
  id: number;
  displayId: string | null;
  slug: string | null;
  title: string | null;
  difficulty: string | null;
  category: string | null;
  site: string;
  locale: string;
  tags: string[];
}

// 题目列表响应
export interface ProblemListResponse {
  problems: ProblemListItem[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

// 题目详情
export interface ProblemDetail {
  id: number;
  displayId: string | null;
  slug: string | null;
  title: string | null;
  difficulty: string | null;
  category: string | null;
  isPaidOnly: boolean;
  site: string;
  url: string | null;
  tags: Array<{ code: string; name: string; source: string }>;
  content: {
    statement: string | null;
    constraints: string[];
    followUps: string[];
    examples: Array<{
      ordinal: number;
      input: string | null;
      output: string | null;
      explanation: string | null;
    }>;
  };
  hints: string[];
  hintsLocked: boolean;
  starterCodes: Array<{
    language: string;
    languageName: string | null;
    template: string;
  }>;
}

// 做题记录
export interface ProblemRecord {
  id: number;
  user_id: number;
  problem_id: number;
  slug: string;
  status: 'not_started' | 'attempting' | 'completed';
  language: string | null;
  viewed_hints: number;
  started_at: string | null;
  completed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// 做题统计
export interface RecordStats {
  total: number;
  byStatus: {
    not_started: number;
    attempting: number;
    completed: number;
  };
  byDifficulty: Record<string, number>;
  byCategory: Record<string, number>;
  recentRecords: ProblemRecord[];
}

// 标签
export interface Tag {
  code: string;
  name: string;
  source: string;
  count: number;
}

// 类别
export interface Category {
  name: string;
  count: number;
}

// API 响应
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
}
