/**
 * 题目列表页
 */
import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { problemsApi } from '../api/client';
import { useLocale } from '../contexts/LocaleContext';
import type { ProblemListItem, Tag, Category } from '../types';

export default function ProblemsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { locale, site } = useLocale();
  
  const [problems, setProblems] = useState<ProblemListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tags, setTags] = useState<Tag[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  
  // 筛选条件
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [difficulty, setDifficulty] = useState(searchParams.get('difficulty') || '');
  const [category, setCategory] = useState(searchParams.get('category') || '');
  const [tag, setTag] = useState(searchParams.get('tag') || '');
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1'));
  const [sort, setSort] = useState(searchParams.get('sort') || 'display_id');
  const [order, setOrder] = useState<'asc' | 'desc'>(
    (searchParams.get('order') as 'asc' | 'desc') || 'asc'
  );

  useEffect(() => {
    // 加载标签和类别
    problemsApi.getTags().then(res => {
      if (res.data.success) setTags(res.data.data);
    });
    problemsApi.getCategories().then(res => {
      if (res.data.success) setCategories(res.data.data);
    });
  }, []);

  useEffect(() => {
    loadProblems();
  }, [page, difficulty, category, tag, sort, order, locale, site]);

  const loadProblems = async () => {
    setLoading(true);
    try {
      const response = await problemsApi.getList({
        page,
        limit: 20,
        search: search || undefined,
        difficulty: difficulty || undefined,
        category: category || undefined,
        tag: tag || undefined,
        site,
        locale,
        sort,
        order,
      });
      
      if (response.data.success) {
        setProblems(response.data.data.problems);
        setTotal(response.data.data.total);
        setTotalPages(response.data.data.totalPages);
      }
    } catch (error) {
      console.error('加载题目失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadProblems();
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

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">题目列表</h1>
        <span className="text-gray-500">共 {total} 题</span>
      </div>

      {/* Search and Filters */}
      <div className="bg-white rounded-xl p-4 shadow-sm space-y-4">
        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索题号、标题或 slug..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#ffa116]"
          />
          <button
            type="submit"
            className="px-6 py-2 bg-[#ffa116] hover:bg-[#e8920f] text-black font-medium rounded-lg transition-colors"
          >
            搜索
          </button>
        </form>

        {/* Filters */}
        <div className="flex flex-wrap gap-4">
          {/* Difficulty */}
          <select
            value={difficulty}
            onChange={(e) => { setDifficulty(e.target.value); setPage(1); }}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#ffa116]"
          >
            <option value="">全部难度</option>
            <option value="easy">简单</option>
            <option value="medium">中等</option>
            <option value="hard">困难</option>
          </select>

          {/* Category */}
          <select
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(1); }}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#ffa116]"
          >
            <option value="">全部类别</option>
            {categories.map(cat => (
              <option key={cat.name} value={cat.name}>
                {cat.name} ({cat.count})
              </option>
            ))}
          </select>

          {/* Sort */}
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#ffa116]"
          >
            <option value="display_id">按题号</option>
            <option value="title">按标题</option>
            <option value="difficulty">按难度</option>
          </select>

          <button
            onClick={() => setOrder(order === 'asc' ? 'desc' : 'asc')}
            className="px-4 py-2 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            {order === 'asc' ? '↑ 升序' : '↓ 降序'}
          </button>
        </div>

        {/* Tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => { setTag(''); setPage(1); }}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                !tag ? 'bg-[#ffa116] text-black' : 'bg-gray-100 hover:bg-gray-200'
              }`}
            >
              全部标签
            </button>
            {tags.slice(0, 20).map(t => (
              <button
                key={t.code}
                onClick={() => { setTag(t.code); setPage(1); }}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  tag === t.code ? 'bg-[#ffa116] text-black' : 'bg-gray-100 hover:bg-gray-200'
                }`}
              >
                {t.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Problems Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500">加载中...</div>
        ) : problems.length === 0 ? (
          <div className="p-12 text-center text-gray-500">没有找到题目</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">题号</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">标题</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">难度</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">类别</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {problems.map(problem => (
                <tr key={problem.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="w-4 h-4 border-2 border-gray-300 rounded"></div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {problem.displayId}
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/problems/${problem.slug || problem.id}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {problem.title || problem.slug}
                    </Link>
                    {problem.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {problem.tags.slice(0, 3).map(t => (
                          <span key={t} className="text-xs text-gray-400">#{t}</span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getDifficultyColor(problem.difficulty)}`}>
                      {getDifficultyLabel(problem.difficulty)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {problem.category || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-4 py-2 border rounded-lg disabled:opacity-50 hover:bg-gray-50 transition-colors"
          >
            上一页
          </button>
          <span className="px-4 py-2">
            第 {page} / {totalPages} 页
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 border rounded-lg disabled:opacity-50 hover:bg-gray-50 transition-colors"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}
