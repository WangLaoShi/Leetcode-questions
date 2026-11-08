/**
 * 首页
 */
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { problemsApi } from '../api/client';

export default function HomePage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    total: 0,
    easy: 0,
    medium: 0,
    hard: 0,
  });
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    // 获取题目统计
    problemsApi.getList({ limit: 1 }).then(response => {
      if (response.data.success) {
        setStats(prev => ({ ...prev, total: response.data.data.total }));
      }
    });
    
    // 获取各难度数量
    ['easy', 'medium', 'hard'].forEach(difficulty => {
      problemsApi.getList({ difficulty, limit: 1 }).then(response => {
        if (response.data.success) {
          setStats(prev => ({ ...prev, [difficulty]: response.data.data.total }));
        }
      });
    });
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/problems?search=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-16 bg-gradient-to-r from-[#1a1a2e] to-[#16213e] rounded-2xl text-white">
        <h1 className="text-5xl font-bold mb-4">LeetCode 题目库</h1>
        <p className="text-xl text-gray-300 mb-8">
          本地查询 · 离线可用 · 完整题干
        </p>
        
        {/* Search Bar */}
        <form onSubmit={handleSearch} className="max-w-2xl mx-auto px-4">
          <div className="flex">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索题号、标题或 slug..."
              className="flex-1 px-6 py-4 rounded-l-xl text-gray-900 text-lg focus:outline-none focus:ring-2 focus:ring-[#ffa116]"
            />
            <button
              type="submit"
              className="px-8 py-4 bg-[#ffa116] hover:bg-[#e8920f] text-black font-semibold rounded-r-xl transition-colors"
            >
              搜索
            </button>
          </div>
        </form>
      </section>

      {/* Stats Section */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm text-center">
          <div className="text-4xl font-bold text-[#1a1a2e]">{stats.total}</div>
          <div className="text-gray-500 mt-2">题目总数</div>
        </div>
        <div className="bg-white rounded-xl p-6 shadow-sm text-center">
          <div className="text-4xl font-bold text-[#00b8a3]">{stats.easy}</div>
          <div className="text-gray-500 mt-2">简单</div>
        </div>
        <div className="bg-white rounded-xl p-6 shadow-sm text-center">
          <div className="text-4xl font-bold text-[#ffc01e]">{stats.medium}</div>
          <div className="text-gray-500 mt-2">中等</div>
        </div>
        <div className="bg-white rounded-xl p-6 shadow-sm text-center">
          <div className="text-4xl font-bold text-[#ff375f]">{stats.hard}</div>
          <div className="text-gray-500 mt-2">困难</div>
        </div>
      </section>

      {/* Quick Links */}
      <section className="grid md:grid-cols-3 gap-6">
        <Link
          to="/problems?difficulty=easy"
          className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow border-l-4 border-[#00b8a3]"
        >
          <h3 className="text-xl font-semibold mb-2">简单题目</h3>
          <p className="text-gray-500">适合入门，共 {stats.easy} 题</p>
        </Link>
        <Link
          to="/problems?category=database"
          className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow border-l-4 border-[#ffa116]"
        >
          <h3 className="text-xl font-semibold mb-2">数据库专题</h3>
          <p className="text-gray-500">SQL 练习题集</p>
        </Link>
        <Link
          to="/problems?difficulty=hard"
          className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow border-l-4 border-[#ff375f]"
        >
          <h3 className="text-xl font-semibold mb-2">挑战困难</h3>
          <p className="text-gray-500">高难度题目，共 {stats.hard} 题</p>
        </Link>
      </section>

      {/* Features */}
      <section className="bg-white rounded-xl p-8 shadow-sm">
        <h2 className="text-2xl font-bold mb-6 text-center">功能特点</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-[#ffa116]/10 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-[#ffa116]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="font-semibold">搜索筛选</h3>
            <p className="text-sm text-gray-500 mt-1">按题号、标题、难度、类别</p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-[#ffa116]/10 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-[#ffa116]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
              </svg>
            </div>
            <h3 className="font-semibold">中英文切换</h3>
            <p className="text-sm text-gray-500 mt-1">支持英文和中文题干</p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-[#ffa116]/10 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-[#ffa116]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="font-semibold">做题记录</h3>
            <p className="text-sm text-gray-500 mt-1">记录进度，统计完成情况</p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-[#ffa116]/10 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-[#ffa116]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <h3 className="font-semibold">代码模板</h3>
            <p className="text-sm text-gray-500 mt-1">多语言初始代码框架</p>
          </div>
        </div>
      </section>
    </div>
  );
}
