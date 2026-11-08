/**
 * 做题记录页
 */
import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { recordsApi } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import type { ProblemRecord, RecordStats } from '../types';

export default function RecordsPage() {
  const { isAuthenticated } = useAuth();
  const [records, setRecords] = useState<ProblemRecord[]>([]);
  const [stats, setStats] = useState<RecordStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated, filter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [recordsRes, statsRes] = await Promise.all([
        recordsApi.getList(filter ? { status: filter } : undefined),
        recordsApi.getStats(),
      ]);
      
      if (recordsRes.data.success) {
        setRecords(recordsRes.data.data);
      }
      if (statsRes.data.success) {
        setStats(statsRes.data.data);
      }
    } catch (error) {
      console.error('加载数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'not_started': return '未开始';
      case 'attempting': return '尝试中';
      case 'completed': return '已完成';
      default: return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'not_started': return 'bg-gray-100 text-gray-600';
      case 'attempting': return 'bg-yellow-100 text-yellow-700';
      case 'completed': return 'bg-green-100 text-green-700';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">做题记录</h1>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl p-4 shadow-sm text-center">
            <div className="text-3xl font-bold text-[#1a1a2e]">{stats.total}</div>
            <div className="text-gray-500 text-sm mt-1">总题数</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm text-center">
            <div className="text-3xl font-bold text-[#00b8a3]">{stats.byStatus.completed}</div>
            <div className="text-gray-500 text-sm mt-1">已完成</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm text-center">
            <div className="text-3xl font-bold text-[#ffc01e]">{stats.byStatus.attempting}</div>
            <div className="text-gray-500 text-sm mt-1">尝试中</div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm text-center">
            <div className="text-3xl font-bold text-gray-400">{stats.byStatus.not_started}</div>
            <div className="text-gray-500 text-sm mt-1">未开始</div>
          </div>
        </div>
      )}

      {/* Difficulty Stats */}
      {stats && Object.keys(stats.byDifficulty).length > 0 && (
        <div className="bg-white rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold mb-4">按难度统计</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-[#00b8a3]/10 rounded-lg">
              <div className="text-2xl font-bold text-[#00b8a3]">{stats.byDifficulty.easy || 0}</div>
              <div className="text-sm text-gray-600 mt-1">简单</div>
            </div>
            <div className="text-center p-4 bg-[#ffc01e]/10 rounded-lg">
              <div className="text-2xl font-bold text-[#ffc01e]">{stats.byDifficulty.medium || 0}</div>
              <div className="text-sm text-gray-600 mt-1">中等</div>
            </div>
            <div className="text-center p-4 bg-[#ff375f]/10 rounded-lg">
              <div className="text-2xl font-bold text-[#ff375f]">{stats.byDifficulty.hard || 0}</div>
              <div className="text-sm text-gray-600 mt-1">困难</div>
            </div>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              !filter ? 'bg-[#ffa116] text-black' : 'bg-gray-100 hover:bg-gray-200'
            }`}
          >
            全部
          </button>
          <button
            onClick={() => setFilter('attempting')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'attempting' ? 'bg-[#ffa116] text-black' : 'bg-gray-100 hover:bg-gray-200'
            }`}
          >
            尝试中
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === 'completed' ? 'bg-[#ffa116] text-black' : 'bg-gray-100 hover:bg-gray-200'
            }`}
          >
            已完成
          </button>
        </div>
      </div>

      {/* Records List */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500">加载中...</div>
        ) : records.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500 mb-4">暂无做题记录</p>
            <Link to="/problems" className="text-[#ffa116] hover:underline">
              去做题 →
            </Link>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">题目</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">语言</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">时间</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {records.map(record => (
                <tr key={record.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link
                      to={`/problems/${record.slug}`}
                      className="text-blue-600 hover:underline font-medium"
                    >
                      {record.slug}
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(record.status)}`}>
                      {getStatusLabel(record.status)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {record.language || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {record.started_at ? new Date(record.started_at).toLocaleDateString('zh-CN') : '-'}
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/problems/${record.slug}`}
                      className="text-[#ffa116] hover:underline text-sm"
                    >
                      查看 →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
