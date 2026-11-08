/**
 * 题目详情页
 */
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { problemsApi, recordsApi } from '../api/client';
import { useLocale } from '../contexts/LocaleContext';
import { useAuth } from '../contexts/AuthContext';
import type { ProblemDetail, ProblemRecord } from '../types';

// 使用 atom-one-light 主题，浅色背景更适合阅读
import 'highlight.js/styles/atom-one-light.css';

// 自定义代码块组件 - 检测示例内容并渲染 markdown
function CodeBlock({ className, children, ...props }: any) {
  const match = /language-(\w+)/.exec(className || '');
  const content = String(children).replace(/\n$/, '');
  
  // 检测是否包含示例格式 (**Input:** 或 **Output:**)
  const isExample = /\*\*(Input|Output|Example)\*\*/i.test(content);
  
  if (isExample) {
    // 将 **bold** 转换为 <strong>
    const formatted = content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br/>');
    
    return (
      <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 my-4">
        <code dangerouslySetInnerHTML={{ __html: formatted }} />
      </pre>
    );
  }
  
  return (
    <pre className={className} {...props}>
      <code className={match ? match[1] : ''}>{children}</code>
    </pre>
  );
}

export default function ProblemDetailPage() {
  const { identifier } = useParams<{ identifier: string }>();
  const { locale, site } = useLocale();
  const { isAuthenticated, membership } = useAuth();
  
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('python3');
  const [record, setRecord] = useState<ProblemRecord | null>(null);
  const [showLockedHint, setShowLockedHint] = useState(false);

  useEffect(() => {
    if (identifier) {
      loadProblem();
      if (isAuthenticated) {
        loadRecord();
      }
    }
  }, [identifier, locale, site]);

  const loadProblem = async () => {
    setLoading(true);
    try {
      const response = await problemsApi.getDetail(identifier!, { site, locale });
      if (response.data.success) {
        setProblem(response.data.data);
        if (response.data.data.starterCodes.length > 0) {
          setSelectedLanguage(response.data.data.starterCodes[0].language);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '加载题目失败');
    } finally {
      setLoading(false);
    }
  };

  const loadRecord = async () => {
    if (!problem) return;
    try {
      const response = await recordsApi.getRecord(problem.id);
      if (response.data.success && response.data.data) {
        setRecord(response.data.data);
      }
    } catch (err) {
      // 忽略错误
    }
  };

  const loadHints = async () => {
    try {
      const response = await problemsApi.getHints(identifier!, { site, locale });
      if (response.data.success) {
        setHints(response.data.data);
        setShowLockedHint(false);
      }
    } catch (err: any) {
      if (err.response?.status === 403) {
        setShowLockedHint(true);
      }
    }
  };

  const updateRecord = async (status: 'attempting' | 'completed') => {
    if (!problem) return;
    try {
      const response = await recordsApi.upsert({
        problemId: problem.id,
        slug: problem.slug || '',
        status,
        language: selectedLanguage,
      });
      if (response.data.success) {
        setRecord(response.data.data);
      }
    } catch (err) {
      console.error('更新记录失败:', err);
    }
  };

  const getDifficultyColor = (difficulty: string | null) => {
    switch (difficulty) {
      case 'easy': return 'text-[#00b8a3] bg-[#00b8a3]/10';
      case 'medium': return 'text-[#ffc01e] bg-[#ffc01e]/10';
      case 'hard': return 'text-[#ff375f] bg-[#ff375f]/10';
      default: return 'text-gray-500 bg-gray-100';
    }
  };

  const getDifficultyLabel = (difficulty: string | null) => {
    switch (difficulty) {
      case 'easy': return '简单';
      case 'medium': return '中等';
      case 'hard': return '困难';
      default: return '未知';
    }
  };

  if (loading) {
    return <div className="text-center py-12">加载中...</div>;
  }

  if (error || !problem) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">{error || '题目不存在'}</p>
        <Link to="/problems" className="text-blue-600 hover:underline mt-4 inline-block">
          返回题目列表
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-xl p-6 shadow-sm mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-gray-500">{problem.displayId}</span>
              <span className={`px-2 py-1 rounded text-xs font-medium ${getDifficultyColor(problem.difficulty)}`}>
                {getDifficultyLabel(problem.difficulty)}
              </span>
              {problem.category && (
                <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600">
                  {problem.category}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold">{problem.title}</h1>
            {problem.url && (
              <a
                href={problem.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline mt-2 inline-block"
              >
                在 LeetCode 上查看 →
              </a>
            )}
          </div>
          
          {/* Action buttons */}
          {isAuthenticated && (
            <div className="flex gap-2">
              <button
                onClick={() => updateRecord('attempting')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  record?.status === 'attempting'
                    ? 'bg-[#ffc01e] text-black'
                    : 'bg-gray-100 hover:bg-gray-200'
                }`}
              >
                尝试中
              </button>
              <button
                onClick={() => updateRecord('completed')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  record?.status === 'completed'
                    ? 'bg-[#00b8a3] text-white'
                    : 'bg-gray-100 hover:bg-gray-200'
                }`}
              >
                已完成
              </button>
            </div>
          )}
        </div>

        {/* Tags */}
        {problem.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {problem.tags.map(tag => (
              <span key={tag.code} className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600">
                {tag.name}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Statement */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">题目描述</h2>
            <div className="markdown-body prose max-w-none">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]} 
                rehypePlugins={[rehypeHighlight]}
                components={{ code: CodeBlock }}
              >
                {problem.content.statement || '暂无题干'}
              </ReactMarkdown>
            </div>
          </div>

          {/* Examples */}
          {problem.content.examples.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">示例</h2>
              <div className="space-y-4">
                {problem.content.examples.map((example, index) => (
                  <div key={index} className="border rounded-lg p-4 bg-gray-50">
                    <div className="font-medium text-sm text-gray-500 mb-2">
                      示例 {example.ordinal}
                    </div>
                    {example.input && (
                      <div className="mb-2">
                        <span className="text-sm font-medium">输入：</span>
                        <code className="ml-2 px-2 py-1 bg-white rounded text-sm">{example.input}</code>
                      </div>
                    )}
                    {example.output && (
                      <div className="mb-2">
                        <span className="text-sm font-medium">输出：</span>
                        <code className="ml-2 px-2 py-1 bg-white rounded text-sm">{example.output}</code>
                      </div>
                    )}
                    {example.explanation && (
                      <div>
                        <span className="text-sm font-medium">解释：</span>
                        <p className="mt-1 text-sm text-gray-600">{example.explanation}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Constraints */}
          {problem.content.constraints.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">约束条件</h2>
              <ul className="list-disc list-inside space-y-2 text-gray-700">
                {problem.content.constraints.map((constraint, index) => (
                  <li key={index}>{constraint}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Hints */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">提示</h2>
            {problem.hintsLocked ? (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <p className="text-gray-500 mb-4">提示内容需要正式会员权限</p>
                {membership && !membership.isPremium && (
                  <p className="text-sm text-gray-400">
                    还需 {membership.hoursRemaining} 小时或 {membership.loginsRemaining} 次登录升级
                  </p>
                )}
                {!isAuthenticated && (
                  <Link to="/login" className="text-[#ffa116] hover:underline">
                    登录 →
                  </Link>
                )}
              </div>
            ) : hints.length > 0 ? (
              <div className="space-y-3">
                {hints.map((hint, index) => (
                  <div key={index} className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-gray-700">{hint}</p>
                  </div>
                ))}
              </div>
            ) : problem.hints.length > 0 ? (
              <div className="space-y-3">
                {problem.hints.map((hint, index) => (
                  <div key={index} className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-gray-700">{hint}</p>
                  </div>
                ))}
              </div>
            ) : (
              <button
                onClick={loadHints}
                className="text-[#ffa116] hover:underline"
              >
                加载提示
              </button>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Starter Code */}
          {problem.starterCodes.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm">
              <h2 className="text-lg font-semibold mb-4">初始代码</h2>
              
              {/* Language selector */}
              <div className="flex flex-wrap gap-2 mb-4">
                {problem.starterCodes.map(code => (
                  <button
                    key={code.language}
                    onClick={() => setSelectedLanguage(code.language)}
                    className={`px-3 py-1 rounded text-sm transition-colors ${
                      selectedLanguage === code.language
                        ? 'bg-[#ffa116] text-black'
                        : 'bg-gray-100 hover:bg-gray-200'
                    }`}
                  >
                    {code.languageName || code.language}
                  </button>
                ))}
              </div>

              {/* Code display */}
              <pre className="bg-[#1e1e1e] rounded-lg p-4 overflow-x-auto">
                <code className="text-sm text-gray-100">
                  {problem.starterCodes.find(c => c.language === selectedLanguage)?.template || '暂无代码'}
                </code>
              </pre>
            </div>
          )}

          {/* Info */}
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <h2 className="text-lg font-semibold mb-4">题目信息</h2>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">题号</dt>
                <dd>{problem.displayId}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Slug</dt>
                <dd className="text-right">{problem.slug}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">站点</dt>
                <dd>{problem.site}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">难度</dt>
                <dd>
                  <span className={`px-2 py-0.5 rounded text-xs ${getDifficultyColor(problem.difficulty)}`}>
                    {getDifficultyLabel(problem.difficulty)}
                  </span>
                </dd>
              </div>
              {problem.isPaidOnly && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">会员题</dt>
                  <dd className="text-[#ffa116]">是</dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
