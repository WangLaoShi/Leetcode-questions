/**
 * 顶部导航栏
 */
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useLocale } from '../../contexts/LocaleContext';

export default function Header() {
  const { user, isAuthenticated, logout } = useAuth();
  const { locale, toggleLocale } = useLocale();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <header className="bg-[#1a1a2e] text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <svg className="w-8 h-8 text-[#ffa116]" fill="currentColor" viewBox="0 0 24 24">
              <path d="M16.102 17.93l-2.697 2.607c-.466.467-1.111.662-1.823.662s-1.357-.195-1.824-.662l-2.697-2.607c-.466-.467-.662-1.112-.662-1.824s.196-1.357.662-1.824l2.697-2.607c.467-.466 1.112-.662 1.824-.662s1.357.196 1.823.662l2.697 2.607c.466.467.662 1.112.662 1.824s-.196 1.357-.662 1.824z"/>
            </svg>
            <span className="text-xl font-bold">LeetCode 题库</span>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <Link to="/problems" className="hover:text-[#ffa116] transition-colors">
              题目
            </Link>
            {isAuthenticated && (
              <Link to="/records" className="hover:text-[#ffa116] transition-colors">
                做题记录
              </Link>
            )}
          </nav>

          {/* Right side */}
          <div className="flex items-center space-x-4">
            {/* Language toggle */}
            <button
              onClick={toggleLocale}
              className="px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 text-sm transition-colors"
            >
              {locale === 'en' ? 'EN' : '中文'}
            </button>

            {/* User menu */}
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <Link to="/profile" className="hover:text-[#ffa116] transition-colors">
                  {user?.username}
                </Link>
                <button
                  onClick={handleLogout}
                  className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 transition-colors"
                >
                  登出
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  to="/login"
                  className="px-4 py-2 rounded hover:bg-gray-700 transition-colors"
                >
                  登录
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 rounded bg-[#ffa116] hover:bg-[#e8920f] text-black font-medium transition-colors"
                >
                  注册
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
