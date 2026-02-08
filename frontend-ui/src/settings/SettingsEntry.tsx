// frontend-ui/src/settings/SettingsEntry.tsx
/**
 * 设置中心 - 入口组件 (瘦身版)
 * 仅负责布局和Tab路由，各Tab组件已拆分到独立文件
 */

import { useState, useEffect } from 'react';
import { Settings, Cpu, Database, Sliders, BookOpen, ChevronRight } from 'lucide-react';
import useSettingsStore from '../store/settingsStore';
import ModelManagementTab from './ModelManagementTab';
import IngestionManagementTab from './IngestionManagementTab';
import DatabaseManagementTab from './DatabaseManagementTab';
import PromptManagementTab from './PromptManagementTab';

type SettingsTab = 'models' | 'ingestion' | 'database' | 'prompts';

function NavItem({ icon, label, active, onClick, badge }: {
  icon: React.ReactNode; label: string; active?: boolean; onClick?: () => void; badge?: number;
}) {
  return (
    <button onClick={onClick}
      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl transition-all ${active ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>
      <div className="flex items-center gap-2.5">
        {icon}
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        {badge !== undefined && badge > 0 && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${active ? 'bg-white/20' : 'bg-yellow-500 text-black font-bold'}`}>{badge}</span>
        )}
        <ChevronRight size={14} className="opacity-50" />
      </div>
    </button>
  );
}

export default function SettingsPanel() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('models');

  const {
    llmProviders, embeddingProviders,
    loadLLMProviders, loadEmbeddingProviders,
    loadIngestionProfiles, loadPromptTemplates, loadTagCategories,
    loadDatabaseStats, loadSettingsSections,
  } = useSettingsStore();

  // 初始加载
  useEffect(() => {
    loadLLMProviders(); loadEmbeddingProviders(); loadSettingsSections();
  }, []);

  // 切换Tab时加载对应数据
  useEffect(() => {
    if (activeTab === 'ingestion') loadIngestionProfiles();
    else if (activeTab === 'database') loadDatabaseStats();
    else if (activeTab === 'prompts') { loadPromptTemplates(); loadTagCategories(); }
  }, [activeTab]);

  // 监听跨Tab跳转事件 (入库管理→模型管理)
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail === 'models') setActiveTab('models');
    };
    window.addEventListener('settings:changeTab', handler);
    return () => window.removeEventListener('settings:changeTab', handler);
  }, []);

  return (
    <div className="w-full h-full flex bg-[#0a0a0a] overflow-hidden">
      {/* 左侧导航 */}
      <div className="w-64 bg-[#111] border-r border-white/5 p-4 flex flex-col overflow-y-auto">
        <div className="mb-6">
          <div className="flex items-center gap-2.5 mb-1">
            <Settings size={20} className="text-blue-400" />
            <h1 className="text-lg font-bold text-white">设置中心</h1>
          </div>
          <p className="text-[11px] text-gray-500 ml-[30px]">管理 AI 模型和系统配置</p>
        </div>

        <div className="space-y-1">
          <NavItem icon={<Cpu size={16} />} label="模型管理" active={activeTab === 'models'} onClick={() => setActiveTab('models')} badge={llmProviders.length + embeddingProviders.length} />
          <NavItem icon={<Sliders size={16} />} label="入库管理" active={activeTab === 'ingestion'} onClick={() => setActiveTab('ingestion')} />
          <NavItem icon={<Database size={16} />} label="数据库管理" active={activeTab === 'database'} onClick={() => setActiveTab('database')} />
          <NavItem icon={<BookOpen size={16} />} label="提示词管理" active={activeTab === 'prompts'} onClick={() => setActiveTab('prompts')} />
        </div>

        <div className="flex-1" />
        <div className="text-[11px] text-gray-600 mt-4">CineGraph-AI v1.0.0-beta</div>
      </div>

      {/* 右侧内容 */}
      <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
        <div className="max-w-4xl mx-auto space-y-4">
          {activeTab === 'models' && <ModelManagementTab />}
          {activeTab === 'ingestion' && <IngestionManagementTab />}
          {activeTab === 'database' && <DatabaseManagementTab />}
          {activeTab === 'prompts' && <PromptManagementTab />}
        </div>
      </div>
    </div>
  );
}
