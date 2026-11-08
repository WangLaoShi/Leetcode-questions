// 用户类型
export interface User {
  id: number;
  username: string;
  email: string;
  password_hash: string;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  login_count: number;
}

// 公开用户信息（不含密码）
export type PublicUser = Omit<User, 'password_hash'>;

// JWT Payload
export interface JwtPayload {
  userId: number;
  username: string;
}

// 做题记录状态
export type ProblemRecordStatus = 'not_started' | 'attempting' | 'completed';

// 做题记录
export interface ProblemRecord {
  id: number;
  user_id: number;
  problem_id: number;
  slug: string;
  status: ProblemRecordStatus;
  language: string | null;
  viewed_hints: number;
  started_at: string | null;
  completed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// 题目相关类型（从数据库读取）
export interface Problem {
  id: number;
  category: string | null;
  category_raw: string | null;
  difficulty: string | null;
  difficulty_raw: string | null;
  is_paid_only: number | null;
  lifecycle: string;
  created_at: string;
  updated_at: string;
}

export interface ProblemSourceIdentity {
  id: number;
  problem_id: number;
  platform: string;
  site: string;
  platform_question_id: string | null;
  display_id: string | null;
  slug: string | null;
  url: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProblemContent {
  id: number;
  problem_id: number;
  source_identity_id: number;
  locale: string;
  title: string | null;
  statement_markdown: string | null;
  statement_format: string | null;
  constraints_json: string;
  follow_ups_json: string;
  type_specific_json: string;
  field_status_json: string;
  extraction_status: string;
  content_hash: string;
  revision: number;
  is_current: number;
  created_at: string;
}

export interface ProblemExample {
  id: number;
  content_id: number;
  ordinal: number;
  input_text: string | null;
  output_text: string | null;
  explanation: string | null;
  images_json: string;
}

export interface ProblemHint {
  id: number;
  content_id: number;
  locale: string;
  ordinal: number;
  body: string;
}

export interface StarterCode {
  id: number;
  problem_id: number;
  content_id: number | null;
  language: string;
  language_name: string | null;
  template: string;
  suspected_implementation: number;
  content_hash: string;
  is_current: number;
  source_record_id: number | null;
}

export interface Tag {
  id: number;
  source: string;
  code: string;
  name: string;
}

// API 请求/响应类型
export interface ProblemListParams {
  page?: number;
  limit?: number;
  search?: string;
  difficulty?: string;
  category?: string;
  tag?: string;
  site?: string;
  locale?: string;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface ProblemListResponse {
  problems: ProblemListItem[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

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

export interface ProblemDetailResponse {
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
  starterCodes: Array<{
    language: string;
    languageName: string | null;
    template: string;
  }>;
}
