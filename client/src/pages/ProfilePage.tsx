/**
 * 个人中心页
 */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ProfilePage() {
  const { user, membership, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="text-center py-12">加载中...</div>;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  const createdAt = new Date(user.created_at);
  const now = new Date();
  const daysSinceRegistration = Math.floor(
    (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60 * 24)
  );

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">个人中心</h1>

      {/* User Info */}
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">账户信息</h2>
        <dl className="space-y-4">
          <div className="flex justify-between items-center py-2 border-b">
            <dt className="text-gray-500">用户名</dt>
            <dd className="font-medium">{user.username}</dd>
          </div>
          <div className="flex justify-between items-center py-2 border-b">
            <dt className="text-gray-500">邮箱</dt>
            <dd className="font-medium">{user.email}</dd>
          </div>
          <div className="flex justify-between items-center py-2 border-b">
            <dt className="text-gray-500">注册时间</dt>
            <dd className="font-medium">{createdAt.toLocaleDateString('zh-CN')}</dd>
          </div>
          <div className="flex justify-between items-center py-2 border-b">
            <dt className="text-gray-500">登录次数</dt>
            <dd className="font-medium">{user.login_count} 次</dd>
          </div>
          <div className="flex justify-between items-center py-2">
            <dt className="text-gray-500">上次登录</dt>
            <dd className="font-medium">
              {user.last_login_at ? new Date(user.last_login_at).toLocaleString('zh-CN') : '从未'}
            </dd>
          </div>
        </dl>
      </div>

      {/* Membership */}
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">会员状态</h2>
        
        {membership?.isPremium ? (
          <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
            <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="font-medium text-green-800">正式会员</p>
              <p className="text-sm text-green-600">您可以查看所有题目提示</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <svg className="w-8 h-8 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <div>
                <p className="font-medium text-yellow-800">新会员</p>
                <p className="text-sm text-yellow-600">部分功能受限</p>
              </div>
            </div>

            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-3">升级条件（满足任一即可）：</p>
              <ul className="space-y-2">
                <li className="flex items-center gap-2">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center ${
                    daysSinceRegistration >= 1 ? 'bg-green-500 text-white' : 'bg-gray-300'
                  }`}>
                    {daysSinceRegistration >= 1 && '✓'}
                  </span>
                  <span className="text-sm">
                    注册满 24 小时
                    {membership && membership.hoursRemaining > 0 && (
                      <span className="text-gray-500 ml-2">
                        （还需 {membership.hoursRemaining} 小时）
                      </span>
                    )}
                  </span>
                </li>
                <li className="flex items-center gap-2">
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center ${
                    user.login_count >= 10 ? 'bg-green-500 text-white' : 'bg-gray-300'
                  }`}>
                    {user.login_count >= 10 && '✓'}
                  </span>
                  <span className="text-sm">
                    登录满 10 次
                    {membership && membership.loginsRemaining > 0 && (
                      <span className="text-gray-500 ml-2">
                        （还需 {membership.loginsRemaining} 次）
                      </span>
                    )}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Progress */}
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <h2 className="text-lg font-semibold mb-4">升级进度</h2>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>时间进度</span>
              <span>{Math.min(100, Math.round((daysSinceRegistration * 24 / 24) * 100))}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#ffa116] transition-all"
                style={{ width: `${Math.min(100, (daysSinceRegistration / 1) * 100)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>登录次数</span>
              <span>{Math.min(100, Math.round((user.login_count / 10) * 100))}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#00b8a3] transition-all"
                style={{ width: `${Math.min(100, (user.login_count / 10) * 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
