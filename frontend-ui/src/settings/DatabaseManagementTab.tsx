// frontend-ui/src/settings/DatabaseManagementTab.tsx
/**
 * 设置中心 - 数据库管理Tab
 */

import { useState, useEffect } from 'react';
import {
  Database, Loader2, RefreshCw, HardDrive,
  FolderOpen, Archive, BarChart3, Activity, Trash2,
} from 'lucide-react';
import useSettingsStore from '../store/settingsStore';
import { SettingsSection } from './SettingsShared';

export default function DatabaseManagementTab() {
  const { databaseStats, loadDatabaseStats } = useSettingsStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadDatabaseStats(); }, []);

  const handleRefresh = async () => { setLoading(true); await loadDatabaseStats(); setLoading(false); };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2">
            <Database size={22} className="text-blue-400" /> 数据库管理
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">数据库统计与维护操作</p>
        </div>
        <button onClick={handleRefresh} disabled={loading}
          className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> 刷新
        </button>
      </div>

      {databaseStats ? (
        <>
          {/* 数据概览 - 紧凑卡片 */}
          <SettingsSection title="数据概览" icon={<BarChart3 size={16} />}>
            <div className="grid grid-cols-4 gap-3">
              {[
                { value: databaseStats.movies_total, label: '影片总数', color: 'text-white' },
                { value: databaseStats.movies_annotated, label: '已标注', color: 'text-green-400' },
                { value: databaseStats.movies_vectorized, label: '已向量化', color: 'text-blue-400' },
                { value: databaseStats.lines_total, label: '台词总数', color: 'text-purple-400' },
              ].map(item => (
                <div key={item.label} className="p-3 rounded-lg bg-white/[0.03] border border-white/5 text-center">
                  <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
                  <div className="text-[11px] text-gray-500 mt-0.5">{item.label}</div>
                </div>
              ))}
            </div>
          </SettingsSection>

          {/* 详细统计 */}
          <SettingsSection title="详细统计" icon={<Activity size={16} />}>
            <div className="space-y-1.5">
              {[
                { label: '已向量化台词', value: `${databaseStats.lines_vectorized} / ${databaseStats.lines_total}` },
                { label: 'LLM 模型数', value: `${databaseStats.models_llm} (激活: ${databaseStats.models_active_llm})` },
                { label: 'Embedding 模型数', value: `${databaseStats.models_embedding} (激活: ${databaseStats.models_active_embedding})` },
                { label: '标签分类 / 定义', value: `${databaseStats.tag_categories} / ${databaseStats.tag_definitions}` },
                { label: '数据库大小', value: `${databaseStats.db_size_mb} MB` },
              ].map((item, i, arr) => (
                <div key={item.label} className={`flex items-center justify-between py-1.5 text-sm ${i < arr.length - 1 ? 'border-b border-white/5' : ''}`}>
                  <span className="text-gray-400">{item.label}</span>
                  <span className="text-white">{item.value}</span>
                </div>
              ))}
            </div>
          </SettingsSection>

          {/* 向量化进度 */}
          {databaseStats.lines_total > 0 && (
            <SettingsSection title="向量化进度" icon={<HardDrive size={16} />}>
              <div>
                <div className="flex justify-between text-xs text-gray-400 mb-1.5">
                  <span>已向量化</span>
                  <span>{Math.round((databaseStats.lines_vectorized / databaseStats.lines_total) * 100)}%</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 rounded-full transition-all duration-500"
                    style={{ width: `${(databaseStats.lines_vectorized / databaseStats.lines_total) * 100}%` }} />
                </div>
              </div>
            </SettingsSection>
          )}

          {/* 维护操作 */}
          <SettingsSection title="数据库维护" icon={<Archive size={16} />}>
            <div className="grid grid-cols-2 gap-2">
              <button className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/5 hover:border-white/10 text-gray-300 hover:text-white transition text-sm">
                <Archive size={14} className="text-blue-400" /> 备份数据库
              </button>
              <button className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/5 hover:border-white/10 text-gray-300 hover:text-white transition text-sm">
                <RefreshCw size={14} className="text-green-400" /> 优化数据库
              </button>
              <button className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/5 hover:border-white/10 text-gray-300 hover:text-white transition text-sm">
                <FolderOpen size={14} className="text-yellow-400" /> 数据导出
              </button>
              <button className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-white/[0.03] border border-white/5 hover:border-red-500/20 text-gray-300 hover:text-red-400 transition text-sm">
                <Trash2 size={14} className="text-red-400" /> 清理缓存
              </button>
            </div>
          </SettingsSection>
        </>
      ) : (
        <div className="text-center py-12 text-gray-600">
          <Loader2 size={28} className="mx-auto mb-3 animate-spin" />
          <p className="text-sm">加载数据库统计信息...</p>
        </div>
      )}
    </>
  );
}
