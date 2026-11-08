/**
 * 页面布局
 */
import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      <footer className="bg-[#1a1a2e] text-gray-400 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p>LeetCode 题目库 · 仅供学习参考</p>
          <p className="text-sm mt-2">
            数据来源：neenza/leetcode-problems, noworneverev/leetcode-api, doocs/leetcode
          </p>
        </div>
      </footer>
    </div>
  );
}
