// frontend-ui/src/SettingsPanel.tsx
/**
 * 设置中心 - 重新设计版本
 * 4个主要模块：模型管理 / 入库管理 / 数据库管理 / 提示词管理
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Settings, Cpu, Database, FileText,
  CheckCircle2, XCircle, Loader2, ChevronRight, ChevronDown,
  RefreshCw, AlertTriangle, Check, X, Zap, ZapOff,
  Server, Sliders, Save, TestTube,
  HardDrive, FolderOpen, Tag, Plus, Cloud, Star,
  Pencil, Trash2, RotateCcw, BookOpen, MessageSquare,
  Activity, Archive, BarChart3,
} from 'lucide-react';
import useSettingsStore from './store/settingsStore';
import type {
  ModelProvider, AnnotationConfig, VectorizationConfig,
  IngestionProfile, PromptTemplate, TagCategory, TagDefinition,
} from './types/settings';

// ==================== 设置Tab类型 ====================
type SettingsTab = 'models' | 'ingestion' | 'database' | 'prompts';

// ==================== 子组件 ====================

function SettingsSection({ title, icon, children, description, badge, action }: {
  title: string; icon: React.ReactNode; children: React.ReactNode;
  description?: string; badge?: string; action?: React.ReactNode;
}) {
  return (
    <div className="bg-[#151515] rounded-xl border border-white/5 overflow-hidden">
      <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-blue-400">{icon}</div>
          <div>
            <h3 className="font-medium text-white">{title}</h3>
            {description && <p className="text-xs text-gray-500 mt-0.5">{description}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {badge && <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">{badge}</span>}
          {action}
        </div>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function SettingsNavItem({ icon, label, active, onClick, badge }: {
  icon: React.ReactNode; label: string; active?: boolean; onClick?: () => void; badge?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all ${
        active ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' : 'text-gray-400 hover:text-white hover:bg-white/5'
      }`}
    >
      <div className="flex items-center gap-3">
        {icon}
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        {badge !== undefined && badge > 0 && (
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${active ? 'bg-white/20' : 'bg-yellow-500 text-black font-bold'}`}>
            {badge}
          </span>
        )}
        <ChevronRight size={14} className="opacity-50" />
      </div>
    </button>
  );
}

// 空白模型模板
const emptyProvider = (category: 'llm' | 'embedding'): Partial<ModelProvider> => ({
  name: '', category, provider_type: 'local', local_mode: 'ollama',
  base_url: category === 'llm' ? 'http://localhost:11434/v1' : 'http://localhost:11434',
  model: '', api_key: '', api_style: 'openai', max_tokens: 2000, temperature: 0.7,
  timeout: 60, dimension: 0, description: '', price_info: '',
});

// ==================== 主组件 ====================

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
    loadLLMProviders();
    loadEmbeddingProviders();
    loadSettingsSections();
  }, []);

  // 切换tab时加载对应数据
  useEffect(() => {
    if (activeTab === 'ingestion') {
      loadIngestionProfiles();
    } else if (activeTab === 'database') {
      loadDatabaseStats();
    } else if (activeTab === 'prompts') {
      loadPromptTemplates();
      loadTagCategories();
    }
  }, [activeTab]);

  return (
    <div className="w-full h-full flex bg-[#0a0a0a] overflow-hidden">
      {/* 左侧导航 */}
      <div className="w-72 bg-[#111] border-r border-white/5 p-6 flex flex-col overflow-y-auto">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Settings size={24} className="text-blue-400" />
            <h1 className="text-xl font-bold text-white">设置中心</h1>
          </div>
          <p className="text-xs text-gray-500">管理 AI 模型和系统配置</p>
        </div>

        <div className="space-y-2">
          <SettingsNavItem
            icon={<Cpu size={18} />} label="模型管理"
            active={activeTab === 'models'} onClick={() => setActiveTab('models')}
            badge={llmProviders.length + embeddingProviders.length}
          />
          <SettingsNavItem
            icon={<Sliders size={18} />} label="入库管理"
            active={activeTab === 'ingestion'} onClick={() => setActiveTab('ingestion')}
          />
          <SettingsNavItem
            icon={<Database size={18} />} label="数据库管理"
            active={activeTab === 'database'} onClick={() => setActiveTab('database')}
          />
          <SettingsNavItem
            icon={<BookOpen size={18} />} label="提示词管理"
            active={activeTab === 'prompts'} onClick={() => setActiveTab('prompts')}
          />
        </div>

        <div className="flex-1" />
        <div className="text-xs text-gray-600 mt-4">
          CineGraph-AI v1.0.0-beta
        </div>
      </div>

      {/* 右侧内容 */}
      <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
        <div className="max-w-4xl mx-auto space-y-6">
          {activeTab === 'models' && <ModelManagementTab />}
          {activeTab === 'ingestion' && <IngestionManagementTab />}
          {activeTab === 'database' && <DatabaseManagementTab />}
          {activeTab === 'prompts' && <PromptManagementTab />}
        </div>
      </div>
    </div>
  );
}


// ==================== Tab 1: 模型管理 ====================

function ModelManagementTab() {
  const {
    llmProviders, embeddingProviders, activeLLMProvider, activeEmbeddingProvider,
    loadLLMProviders, loadEmbeddingProviders,
    setActiveLLMProvider, setActiveEmbeddingProvider, testLLMConnection,
    createProvider, updateProvider, deleteProvider, toggleProvider, resetProviderDefaults,
  } = useSettingsStore();

  const [modelTab, setModelTab] = useState<'llm' | 'embedding'>('llm');
  const [showEditor, setShowEditor] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Partial<ModelProvider> | null>(null);
  const [isNewProvider, setIsNewProvider] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, 'loading' | 'success' | 'fail'>>({});
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [loading, setLoading] = useState(false);

  const providers = modelTab === 'llm' ? llmProviders : embeddingProviders;
  const activeProviderId = modelTab === 'llm' ? activeLLMProvider : activeEmbeddingProvider;

  const grouped = useMemo(() => ({
    local: providers.filter(p => p.provider_type === 'local'),
    commercial: providers.filter(p => p.provider_type === 'commercial'),
  }), [providers]);

  const handleAdd = () => {
    setEditingProvider(emptyProvider(modelTab));
    setIsNewProvider(true);
    setShowEditor(true);
  };

  const handleEdit = (p: ModelProvider) => {
    setEditingProvider({ ...p });
    setIsNewProvider(false);
    setShowEditor(true);
  };

  const handleSave = async () => {
    if (!editingProvider) return;
    setLoading(true);
    try {
      if (isNewProvider) {
        await createProvider(editingProvider as any);
      } else {
        await updateProvider(editingProvider.id!, editingProvider as any);
      }
      setShowEditor(false);
      setEditingProvider(null);
      if (modelTab === 'llm') await loadLLMProviders();
      else await loadEmbeddingProviders();
    } catch (e: any) {
      alert('保存失败: ' + (e.message || '未知错误'));
    }
    setLoading(false);
  };

  const handleDelete = async (id: string) => {
    setLoading(true);
    try {
      await deleteProvider(id);
      setConfirmDelete(null);
      if (modelTab === 'llm') await loadLLMProviders();
      else await loadEmbeddingProviders();
    } catch (e: any) {
      alert('删除失败: ' + (e.message || '未知错误'));
    }
    setLoading(false);
  };

  const handleTest = async (p: ModelProvider) => {
    setTestResults(prev => ({ ...prev, [p.id]: 'loading' }));
    try {
      const ok = await testLLMConnection(p.id);
      setTestResults(prev => ({ ...prev, [p.id]: ok ? 'success' : 'fail' }));
    } catch {
      setTestResults(prev => ({ ...prev, [p.id]: 'fail' }));
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await resetProviderDefaults();
      setConfirmReset(false);
      await loadLLMProviders();
      await loadEmbeddingProviders();
    } catch (e: any) {
      alert('重置失败: ' + (e.message || '未知错误'));
    }
    setLoading(false);
  };

  const toggleExpand = (id: string) => {
    setExpandedCards(prev => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id); else s.add(id);
      return s;
    });
  };

  const renderCard = (p: ModelProvider) => {
    const isActive = p.id === activeProviderId;
    const expanded = expandedCards.has(p.id);
    const test = testResults[p.id];
    return (
      <div
        key={p.id}
        className={`rounded-xl border transition-all ${
          isActive
            ? 'border-blue-500/60 bg-blue-500/5 shadow-lg shadow-blue-500/10'
            : p.enabled
              ? 'border-white/10 bg-white/[0.02] hover:border-white/20'
              : 'border-white/5 bg-white/[0.01] opacity-50'
        }`}
      >
        {/* 卡片头部 */}
        <div
          className="flex items-center gap-3 px-4 py-3 cursor-pointer"
          onClick={() => toggleExpand(p.id)}
        >
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
            isActive ? 'bg-green-400 shadow-green-400/50 shadow-lg' : p.enabled ? 'bg-gray-500' : 'bg-red-500/50'
          }`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm truncate">{p.name}</span>
              {isActive && (
                <span className="text-[10px] px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded-full flex items-center gap-1">
                  <Star size={8} /> 当前激活
                </span>
              )}
              {p.is_default && (
                <span className="text-[10px] px-1.5 py-0.5 bg-gray-500/20 text-gray-400 rounded-full">预置</span>
              )}
            </div>
            <div className="text-xs text-gray-500 truncate mt-0.5">
              {p.model} · {p.price_info || '无价格信息'}
            </div>
          </div>
          {test === 'loading' && <Loader2 size={14} className="animate-spin text-blue-400" />}
          {test === 'success' && <CheckCircle2 size={14} className="text-green-400" />}
          {test === 'fail' && <XCircle size={14} className="text-red-400" />}
          <ChevronDown size={14} className={`text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>

        {/* 展开内容 */}
        {expanded && (
          <div className="px-4 pb-3 border-t border-white/5 pt-3 space-y-3">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-500">API 地址</span>
                <p className="text-gray-300 truncate">{p.base_url}</p>
              </div>
              <div>
                <span className="text-gray-500">模型</span>
                <p className="text-gray-300 truncate">{p.model}</p>
              </div>
              {modelTab === 'llm' && (
                <>
                  <div>
                    <span className="text-gray-500">温度</span>
                    <p className="text-gray-300">{p.temperature}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">最大Token</span>
                    <p className="text-gray-300">{p.max_tokens}</p>
                  </div>
                </>
              )}
              {modelTab === 'embedding' && (
                <>
                  <div>
                    <span className="text-gray-500">维度</span>
                    <p className="text-gray-300">{p.dimension || '自动'}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">API风格</span>
                    <p className="text-gray-300">{p.api_style}</p>
                  </div>
                </>
              )}
              <div>
                <span className="text-gray-500">超时</span>
                <p className="text-gray-300">{p.timeout}s</p>
              </div>
              <div>
                <span className="text-gray-500">API Key</span>
                <p className="text-gray-300">{p.api_key || '(无)'}</p>
              </div>
            </div>
            {p.description && <p className="text-xs text-gray-500 italic">{p.description}</p>}

            {/* 操作按钮 */}
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={(e) => { e.stopPropagation(); handleTest(p); }}
                className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
              >
                <TestTube size={12} /> 测试
              </button>
              {!isActive && p.enabled && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    modelTab === 'llm' ? setActiveLLMProvider(p.id) : setActiveEmbeddingProvider(p.id);
                  }}
                  className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 transition"
                >
                  <Zap size={12} /> 激活
                </button>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); toggleProvider(p.id, !p.enabled); }}
                className={`flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg transition ${
                  p.enabled
                    ? 'bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400'
                    : 'bg-green-500/10 hover:bg-green-500/20 text-green-400'
                }`}
              >
                {p.enabled ? <><ZapOff size={12} /> 停用</> : <><Zap size={12} /> 启用</>}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleEdit(p); }}
                className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
              >
                <Pencil size={12} /> 编辑
              </button>
              {!p.is_default && (
                <button
                  onClick={(e) => { e.stopPropagation(); setConfirmDelete(p.id); }}
                  className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition"
                >
                  <Trash2 size={12} /> 删除
                </button>
              )}
            </div>
          </div>
        )}

        {/* 删除确认 */}
        {confirmDelete === p.id && (
          <div className="px-4 pb-3 border-t border-red-500/20 pt-2 flex items-center gap-3">
            <AlertTriangle size={14} className="text-red-400 flex-shrink-0" />
            <span className="text-xs text-red-300">确认删除此模型？</span>
            <div className="flex-1" />
            <button
              onClick={() => handleDelete(p.id)}
              className="text-xs px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded-lg transition"
            >
              确认
            </button>
            <button
              onClick={() => setConfirmDelete(null)}
              className="text-xs px-3 py-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg transition"
            >
              取消
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-3">
            <Cpu size={28} className="text-blue-400" /> 模型管理
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            管理 LLM 和 Embedding 模型提供者，所有配置存储在数据库中
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { loadLLMProviders(); loadEmbeddingProviders(); }}
            className="flex items-center gap-1.5 px-3 py-2 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
          >
            <RefreshCw size={14} /> 刷新
          </button>
          <button
            onClick={() => setConfirmReset(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs rounded-lg bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 transition"
          >
            <RotateCcw size={14} /> 重置默认
          </button>
        </div>
      </div>

      {/* LLM / Embedding Tab 切换 */}
      <div className="flex gap-1 p-1 bg-white/5 rounded-xl w-fit">
        <button
          onClick={() => setModelTab('llm')}
          className={`px-5 py-2 text-sm rounded-lg transition-all ${
            modelTab === 'llm' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          🧠 LLM 大语言模型
        </button>
        <button
          onClick={() => setModelTab('embedding')}
          className={`px-5 py-2 text-sm rounded-lg transition-all ${
            modelTab === 'embedding' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          📐 Embedding 向量模型
        </button>
      </div>

      {/* 统计摘要 */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
          <div className="text-2xl font-bold text-white">{providers.length}</div>
          <div className="text-xs text-gray-500">已配置模型</div>
        </div>
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
          <div className="text-2xl font-bold text-green-400">{providers.filter(p => p.enabled).length}</div>
          <div className="text-xs text-gray-500">已启用</div>
        </div>
        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/5">
          <div className="text-2xl font-bold text-blue-400 truncate text-sm">
            {providers.find(p => p.id === activeProviderId)?.name || '-'}
          </div>
          <div className="text-xs text-gray-500">当前激活</div>
        </div>
      </div>

      {/* 添加模型按钮 */}
      <button
        onClick={handleAdd}
        className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border border-dashed border-white/10 hover:border-blue-500/40 bg-white/[0.01] hover:bg-blue-500/5 text-gray-400 hover:text-blue-400 transition-all"
      >
        <Plus size={18} />
        <span className="text-sm">添加{modelTab === 'llm' ? ' LLM ' : ' Embedding '}模型</span>
      </button>

      {/* 模型列表 */}
      <div className="space-y-6">
        {grouped.local.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-gray-400 uppercase tracking-wider px-1 py-1">
              <Server size={12} />
              <span>本地模型</span>
              <span className="text-gray-600">({grouped.local.length})</span>
            </div>
            <div className="space-y-2">{grouped.local.map(renderCard)}</div>
          </div>
        )}
        {grouped.commercial.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-gray-400 uppercase tracking-wider px-1 py-1">
              <Cloud size={12} />
              <span>商用 API</span>
              <span className="text-gray-600">({grouped.commercial.length})</span>
            </div>
            <div className="space-y-2">{grouped.commercial.map(renderCard)}</div>
          </div>
        )}
        {providers.length === 0 && (
          <div className="text-center py-12 text-gray-600">
            <Cpu size={32} className="mx-auto mb-3 opacity-50" />
            <p>暂无{modelTab === 'llm' ? 'LLM' : 'Embedding'}模型</p>
            <p className="text-xs mt-1">点击上方按钮添加模型</p>
          </div>
        )}
      </div>

      {/* 编辑模态框 */}
      {showEditor && editingProvider && (
        <ModelEditorModal
          provider={editingProvider}
          isNew={isNewProvider}
          loading={loading}
          onSave={handleSave}
          onClose={() => { setShowEditor(false); setEditingProvider(null); }}
          onChange={setEditingProvider}
        />
      )}

      {/* 重置确认弹窗 */}
      {confirmReset && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setConfirmReset(false)}
        >
          <div
            className="bg-[#1a1a1a] rounded-2xl border border-orange-500/20 shadow-2xl max-w-sm w-full p-6 space-y-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center gap-3">
              <AlertTriangle size={24} className="text-orange-400" />
              <h3 className="text-lg font-bold">重置为默认配置？</h3>
            </div>
            <p className="text-sm text-gray-400">
              此操作将删除所有自定义模型，恢复为系统默认的模型提供者配置。
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmReset(false)}
                className="px-4 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
              >
                取消
              </button>
              <button
                onClick={handleReset}
                disabled={loading}
                className="px-4 py-2 text-sm rounded-lg bg-orange-600 hover:bg-orange-500 text-white transition flex items-center gap-2"
              >
                {loading && <Loader2 size={14} className="animate-spin" />}
                确认重置
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}


// ==================== 模型编辑弹窗组件 ====================

function ModelEditorModal({
  provider, isNew, loading, onSave, onClose, onChange,
}: {
  provider: Partial<ModelProvider>;
  isNew: boolean;
  loading: boolean;
  onSave: () => void;
  onClose: () => void;
  onChange: (p: Partial<ModelProvider>) => void;
}) {
  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-[#1a1a1a] rounded-2xl border border-white/10 shadow-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="p-5 border-b border-white/5">
          <h3 className="text-lg font-bold">{isNew ? '添加模型' : '编辑模型'}</h3>
          <p className="text-xs text-gray-500 mt-1">
            {isNew ? '配置新的模型提供者' : `编辑: ${provider.name}`}
          </p>
        </div>

        <div className="p-5 space-y-4">
          {/* 名称 */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">显示名称 *</label>
            <input
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
              value={provider.name || ''}
              onChange={e => onChange({ ...provider, name: e.target.value })}
              placeholder="例: 我的Ollama模型"
            />
          </div>

          {/* 提供者类型 + 本地模式 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">提供者类型</label>
              <select
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                value={provider.provider_type || 'local'}
                onChange={e => {
                  const t = e.target.value as 'local' | 'commercial';
                  onChange({
                    ...provider,
                    provider_type: t,
                    local_mode: t === 'local' ? 'ollama' : '',
                    base_url: t === 'local'
                      ? (provider.category === 'llm' ? 'http://localhost:11434/v1' : 'http://localhost:11434')
                      : provider.base_url || '',
                  });
                }}
              >
                <option value="local">本地部署</option>
                <option value="commercial">商用API</option>
              </select>
            </div>
            {provider.provider_type === 'local' && (
              <div>
                <label className="text-xs text-gray-400 mb-1 block">本地模式</label>
                <select
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                  value={provider.local_mode || 'ollama'}
                  onChange={e => onChange({ ...provider, local_mode: e.target.value })}
                >
                  <option value="ollama">Ollama</option>
                  <option value="docker">Docker</option>
                </select>
              </div>
            )}
          </div>

          {/* API 地址 */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">API 地址 *</label>
            <input
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
              value={provider.base_url || ''}
              onChange={e => onChange({ ...provider, base_url: e.target.value })}
              placeholder="http://localhost:11434/v1"
            />
          </div>

          {/* 模型名称 */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">模型名称 *</label>
            <input
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
              value={provider.model || ''}
              onChange={e => onChange({ ...provider, model: e.target.value })}
              placeholder="qwen3:4b"
            />
          </div>

          {/* API Key */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">API Key</label>
            <input
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
              value={provider.api_key || ''}
              onChange={e => onChange({ ...provider, api_key: e.target.value })}
              placeholder="留空或引用环境变量"
            />
          </div>

          {/* Embedding 专用参数 */}
          {provider.category === 'embedding' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">API风格</label>
                <select
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                  value={provider.api_style || 'openai'}
                  onChange={e => onChange({ ...provider, api_style: e.target.value })}
                >
                  <option value="openai">OpenAI</option>
                  <option value="ollama">Ollama</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">向量维度</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                  value={provider.dimension || 0}
                  onChange={e => onChange({ ...provider, dimension: parseInt(e.target.value) || 0 })}
                  placeholder="0=自动"
                />
              </div>
            </div>
          )}

          {/* LLM 专用参数 */}
          {provider.category === 'llm' && (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">最大Token</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                  value={provider.max_tokens || 2000}
                  onChange={e => onChange({ ...provider, max_tokens: parseInt(e.target.value) || 2000 })}
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">温度</label>
                <input
                  type="number"
                  step="0.1"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                  value={provider.temperature ?? 0.7}
                  onChange={e => onChange({ ...provider, temperature: parseFloat(e.target.value) || 0.7 })}
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">超时(秒)</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                  value={provider.timeout || 60}
                  onChange={e => onChange({ ...provider, timeout: parseInt(e.target.value) || 60 })}
                />
              </div>
            </div>
          )}

          {/* 描述 */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">描述</label>
            <textarea
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none resize-none h-16 focus:border-blue-500/50"
              value={provider.description || ''}
              onChange={e => onChange({ ...provider, description: e.target.value })}
              placeholder="模型简介..."
            />
          </div>

          {/* 价格信息 */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">价格信息</label>
            <input
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
              value={provider.price_info || ''}
              onChange={e => onChange({ ...provider, price_info: e.target.value })}
              placeholder="如: 免费 / ¥1/百万token"
            />
          </div>
        </div>

        {/* 底部操作 */}
        <div className="p-5 border-t border-white/5 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
          >
            取消
          </button>
          <button
            onClick={onSave}
            disabled={loading || !provider.name || !provider.model || !provider.base_url}
            className="px-6 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center gap-2"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            {isNew ? '添加' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}


// ==================== Tab 2: 入库管理 ====================

function IngestionManagementTab() {
  const {
    llmProviders, embeddingProviders,
    annotationConfig, vectorizationConfig,
    loadLLMProviders, loadEmbeddingProviders,
    saveAnnotationConfig, saveVectorizationConfig,
    testLLMConnection, updateProvider,
  } = useSettingsStore();

  const [ingestionTab, setIngestionTab] = useState<'annotation' | 'vectorization'>('annotation');
  const [testResults, setTestResults] = useState<Record<string, 'loading' | 'success' | 'fail'>>({});
  const [showModelEditor, setShowModelEditor] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Partial<ModelProvider> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadLLMProviders();
    loadEmbeddingProviders();
  }, []);

  // 标注参数草稿
  const [annotationDraft, setAnnotationDraft] = useState({
    batch_size: annotationConfig.batch_size,
    concurrent_requests: annotationConfig.concurrent_requests,
    max_retries: annotationConfig.max_retries,
    retry_delay: annotationConfig.retry_delay,
    save_interval: annotationConfig.save_interval,
  });

  const [vectorDraft, setVectorDraft] = useState({
    batch_size: vectorizationConfig.batch_size,
    concurrent_requests: vectorizationConfig.concurrent_requests,
    max_retries: vectorizationConfig.max_retries,
    retry_delay: vectorizationConfig.retry_delay,
  });

  // 响应store变化
  useEffect(() => {
    setAnnotationDraft({
      batch_size: annotationConfig.batch_size,
      concurrent_requests: annotationConfig.concurrent_requests,
      max_retries: annotationConfig.max_retries,
      retry_delay: annotationConfig.retry_delay,
      save_interval: annotationConfig.save_interval,
    });
  }, [annotationConfig]);

  useEffect(() => {
    setVectorDraft({
      batch_size: vectorizationConfig.batch_size,
      concurrent_requests: vectorizationConfig.concurrent_requests,
      max_retries: vectorizationConfig.max_retries,
      retry_delay: vectorizationConfig.retry_delay,
    });
  }, [vectorizationConfig]);

  const handleTestModel = async (providerId: string) => {
    setTestResults(prev => ({ ...prev, [providerId]: 'loading' }));
    try {
      const ok = await testLLMConnection(providerId);
      setTestResults(prev => ({ ...prev, [providerId]: ok ? 'success' : 'fail' }));
    } catch {
      setTestResults(prev => ({ ...prev, [providerId]: 'fail' }));
    }
  };

  const handleEditModel = (p: ModelProvider) => {
    setEditingProvider({ ...p });
    setShowModelEditor(true);
  };

  const handleSaveAnnotation = async () => {
    setSaving(true);
    try { await saveAnnotationConfig(annotationDraft); } catch {}
    setSaving(false);
  };

  const handleSaveVector = async () => {
    setSaving(true);
    try { await saveVectorizationConfig(vectorDraft); } catch {}
    setSaving(false);
  };

  const handleSaveModelEdit = async () => {
    if (editingProvider?.id) {
      await updateProvider(editingProvider.id, editingProvider as any);
      setShowModelEditor(false);
      loadLLMProviders();
      loadEmbeddingProviders();
    }
  };

  const renderModelList = (models: ModelProvider[]) => (
    <div className="space-y-3">
      {models.map(p => (
        <div
          key={p.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${
            p.is_active
              ? 'border-green-500/40 bg-green-500/5'
              : 'border-white/10 bg-white/[0.02] hover:border-white/20'
          }`}
        >
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${p.is_active ? 'bg-green-400' : 'bg-gray-500'}`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{p.name}</span>
              {p.is_active && (
                <span className="text-[10px] px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded-full">激活中</span>
              )}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {p.model} · {p.category === 'embedding' ? `维度: ${p.dimension || '自动'} · ` : ''}{p.price_info || '-'}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {testResults[p.id] === 'loading' && <Loader2 size={14} className="animate-spin text-blue-400" />}
            {testResults[p.id] === 'success' && <CheckCircle2 size={14} className="text-green-400" />}
            {testResults[p.id] === 'fail' && <XCircle size={14} className="text-red-400" />}
            <button
              onClick={() => handleTestModel(p.id)}
              className="px-2.5 py-1.5 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition flex items-center gap-1"
              title="测试连接"
            >
              <TestTube size={12} /> 测试
            </button>
            <button
              onClick={() => handleEditModel(p)}
              className="px-2.5 py-1.5 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition flex items-center gap-1"
              title="编辑模型"
            >
              <Pencil size={12} /> 编辑
            </button>
          </div>
        </div>
      ))}
      {models.length === 0 && (
        <div className="text-center py-8 text-gray-500 text-sm">
          暂无启用的模型，请先在「模型管理」中配置
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* 页面标题 */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-3">
          <Sliders size={28} className="text-blue-400" /> 入库管理
        </h2>
        <p className="text-sm text-gray-500 mt-1">配置语义标注和向量化的模型、参数设定</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-1 p-1 bg-white/5 rounded-xl w-fit">
        <button
          onClick={() => setIngestionTab('annotation')}
          className={`px-5 py-2 text-sm rounded-lg transition-all ${
            ingestionTab === 'annotation' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          🏷️ 语义标定参数
        </button>
        <button
          onClick={() => setIngestionTab('vectorization')}
          className={`px-5 py-2 text-sm rounded-lg transition-all ${
            ingestionTab === 'vectorization' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          📐 向量化设定
        </button>
      </div>

      {/* ===== 语义标定设定 ===== */}
      {ingestionTab === 'annotation' && (
        <div className="space-y-6">
          <SettingsSection
            title="LLM 模型选择"
            icon={<Cpu size={18} />}
            description="选择用于语义标注的大语言模型 — 仅显示已启用的模型"
          >
            {renderModelList(llmProviders.filter(p => p.enabled))}
          </SettingsSection>

          <SettingsSection
            title="标注参数设置"
            icon={<Sliders size={18} />}
            description="调整语义标注的批处理和并发参数"
            action={
              <button
                onClick={handleSaveAnnotation}
                disabled={saving}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition disabled:opacity-50"
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} 保存
              </button>
            }
          >
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-400 mb-1.5 block">批处理大小</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={annotationDraft.batch_size}
                  onChange={e => setAnnotationDraft({ ...annotationDraft, batch_size: parseInt(e.target.value) || 10 })}
                />
                <p className="text-[10px] text-gray-600 mt-1">每次发送给LLM的台词数量</p>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1.5 block">并发请求数</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={annotationDraft.concurrent_requests}
                  onChange={e => setAnnotationDraft({ ...annotationDraft, concurrent_requests: parseInt(e.target.value) || 1 })}
                />
                <p className="text-[10px] text-gray-600 mt-1">同时进行的请求数</p>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1.5 block">最大重试次数</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={annotationDraft.max_retries}
                  onChange={e => setAnnotationDraft({ ...annotationDraft, max_retries: parseInt(e.target.value) || 3 })}
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1.5 block">重试延迟 (ms)</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={annotationDraft.retry_delay}
                  onChange={e => setAnnotationDraft({ ...annotationDraft, retry_delay: parseInt(e.target.value) || 1000 })}
                />
              </div>
              <div className="col-span-2">
                <label className="text-xs text-gray-400 mb-1.5 block">自动保存间隔</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={annotationDraft.save_interval}
                  onChange={e => setAnnotationDraft({ ...annotationDraft, save_interval: parseInt(e.target.value) || 50 })}
                />
                <p className="text-[10px] text-gray-600 mt-1">每标注多少条自动保存一次</p>
              </div>
            </div>
          </SettingsSection>
        </div>
      )}

      {/* ===== 向量化设定 ===== */}
      {ingestionTab === 'vectorization' && (
        <div className="space-y-6">
          <SettingsSection
            title="Embedding 模型选择"
            icon={<Cpu size={18} />}
            description="选择用于向量化的嵌入模型 — 仅显示已启用的模型"
          >
            {renderModelList(embeddingProviders.filter(p => p.enabled))}
          </SettingsSection>

          <SettingsSection
            title="向量化参数设置"
            icon={<Sliders size={18} />}
            description="调整向量化入库的批处理和并发参数"
            action={
              <button
                onClick={handleSaveVector}
                disabled={saving}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition disabled:opacity-50"
              >
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} 保存
              </button>
            }
          >
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-gray-400 mb-1.5 block">批处理大小</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={vectorDraft.batch_size}
                  onChange={e => setVectorDraft({ ...vectorDraft, batch_size: parseInt(e.target.value) || 50 })}
                />
                <p className="text-[10px] text-gray-600 mt-1">每批向量化的条数</p>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1.5 block">并发请求数</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={vectorDraft.concurrent_requests}
                  onChange={e => setVectorDraft({ ...vectorDraft, concurrent_requests: parseInt(e.target.value) || 2 })}
                />
                <p className="text-[10px] text-gray-600 mt-1">同时进行的请求数</p>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1.5 block">最大重试次数</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={vectorDraft.max_retries}
                  onChange={e => setVectorDraft({ ...vectorDraft, max_retries: parseInt(e.target.value) || 3 })}
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1.5 block">重试延迟 (ms)</label>
                <input
                  type="number"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={vectorDraft.retry_delay}
                  onChange={e => setVectorDraft({ ...vectorDraft, retry_delay: parseInt(e.target.value) || 500 })}
                />
              </div>
            </div>
          </SettingsSection>
        </div>
      )}

      {/* 模型编辑弹窗（简化版） */}
      {showModelEditor && editingProvider && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowModelEditor(false)}
        >
          <div
            className="bg-[#1a1a1a] rounded-2xl border border-white/10 shadow-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-5 border-b border-white/5">
              <h3 className="text-lg font-bold">编辑模型参数</h3>
              <p className="text-xs text-gray-500 mt-1">修改: {editingProvider.name}</p>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">API 地址</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingProvider.base_url || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, base_url: e.target.value })}
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">模型名称</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingProvider.model || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, model: e.target.value })}
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">API Key</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingProvider.api_key || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, api_key: e.target.value })}
                />
              </div>
              {editingProvider.category === 'llm' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">温度</label>
                    <input
                      type="number" step="0.1"
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                      value={editingProvider.temperature ?? 0.7}
                      onChange={e => setEditingProvider({ ...editingProvider, temperature: parseFloat(e.target.value) || 0.7 })}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">超时(秒)</label>
                    <input
                      type="number"
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                      value={editingProvider.timeout || 60}
                      onChange={e => setEditingProvider({ ...editingProvider, timeout: parseInt(e.target.value) || 60 })}
                    />
                  </div>
                </div>
              )}
            </div>
            <div className="p-5 border-t border-white/5 flex justify-end gap-3">
              <button
                onClick={() => setShowModelEditor(false)}
                className="px-4 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
              >
                取消
              </button>
              <button
                onClick={handleSaveModelEdit}
                className="px-6 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium transition"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}


// ==================== Tab 3: 数据库管理 ====================

function DatabaseManagementTab() {
  const { databaseStats, loadDatabaseStats } = useSettingsStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadDatabaseStats(); }, []);

  const handleRefresh = async () => {
    setLoading(true);
    await loadDatabaseStats();
    setLoading(false);
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-3">
            <Database size={28} className="text-blue-400" /> 数据库管理
          </h2>
          <p className="text-sm text-gray-500 mt-1">查看数据库统计信息和维护操作</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> 刷新
        </button>
      </div>

      {databaseStats ? (
        <div className="space-y-6">
          {/* 数据概览 */}
          <SettingsSection title="数据概览" icon={<BarChart3 size={18} />} description="数据库核心指标">
            <div className="grid grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/5 text-center">
                <div className="text-3xl font-bold text-white">{databaseStats.movies_total}</div>
                <div className="text-xs text-gray-500 mt-1">影片总数</div>
              </div>
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/5 text-center">
                <div className="text-3xl font-bold text-green-400">{databaseStats.movies_annotated}</div>
                <div className="text-xs text-gray-500 mt-1">已标注</div>
              </div>
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/5 text-center">
                <div className="text-3xl font-bold text-blue-400">{databaseStats.movies_vectorized}</div>
                <div className="text-xs text-gray-500 mt-1">已向量化</div>
              </div>
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/5 text-center">
                <div className="text-3xl font-bold text-purple-400">{databaseStats.lines_total}</div>
                <div className="text-xs text-gray-500 mt-1">台词总数</div>
              </div>
            </div>
          </SettingsSection>

          {/* 详细统计 */}
          <SettingsSection title="详细统计" icon={<Activity size={18} />}>
            <div className="space-y-3">
              {[
                { label: '已向量化台词', value: `${databaseStats.lines_vectorized} / ${databaseStats.lines_total}` },
                { label: 'LLM 模型数', value: `${databaseStats.models_llm} (激活: ${databaseStats.models_active_llm})` },
                { label: 'Embedding 模型数', value: `${databaseStats.models_embedding} (激活: ${databaseStats.models_active_embedding})` },
                { label: '标签分类', value: `${databaseStats.tag_categories}` },
                { label: '标签定义', value: `${databaseStats.tag_definitions}` },
                { label: '数据库大小', value: `${databaseStats.db_size_mb} MB` },
              ].map((item, i, arr) => (
                <div key={item.label} className={`flex items-center justify-between py-2 ${i < arr.length - 1 ? 'border-b border-white/5' : ''}`}>
                  <span className="text-sm text-gray-400">{item.label}</span>
                  <span className="text-sm text-white">{item.value}</span>
                </div>
              ))}
            </div>
          </SettingsSection>

          {/* 向量化进度 */}
          {databaseStats.lines_total > 0 && (
            <SettingsSection title="向量化进度" icon={<HardDrive size={18} />}>
              <div>
                <div className="flex justify-between text-xs text-gray-400 mb-2">
                  <span>已向量化</span>
                  <span>{Math.round((databaseStats.lines_vectorized / databaseStats.lines_total) * 100)}%</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-600 to-indigo-500 rounded-full transition-all duration-500"
                    style={{ width: `${(databaseStats.lines_vectorized / databaseStats.lines_total) * 100}%` }}
                  />
                </div>
              </div>
            </SettingsSection>
          )}

          {/* 维护操作 */}
          <SettingsSection title="数据库维护" icon={<Archive size={18} />} description="数据库管理和维护操作">
            <div className="grid grid-cols-2 gap-3">
              <button className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-white/10 text-gray-300 hover:text-white transition text-sm">
                <Archive size={16} className="text-blue-400" /> 备份数据库
              </button>
              <button className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-white/10 text-gray-300 hover:text-white transition text-sm">
                <RefreshCw size={16} className="text-green-400" /> 优化数据库
              </button>
              <button className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-white/10 text-gray-300 hover:text-white transition text-sm">
                <FolderOpen size={16} className="text-yellow-400" /> 数据导出
              </button>
              <button className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-red-500/20 text-gray-300 hover:text-red-400 transition text-sm">
                <Trash2 size={16} className="text-red-400" /> 清理缓存
              </button>
            </div>
          </SettingsSection>
        </div>
      ) : (
        <div className="text-center py-16 text-gray-600">
          <Loader2 size={32} className="mx-auto mb-4 animate-spin" />
          <p>加载数据库统计信息...</p>
        </div>
      )}
    </>
  );
}


// ==================== Tab 4: 提示词管理 ====================

function PromptManagementTab() {
  const {
    promptTemplates, tagCategories, tagDefinitions,
    loadPromptTemplates, loadTagCategories, loadTagDefinitions,
    createPromptTemplate, updatePromptTemplate, deletePromptTemplate,
    createTagDefinition, updateTagDefinition, deleteTagDefinition,
  } = useSettingsStore();

  const [promptTab, setPromptTab] = useState<'tags' | 'annotation' | 'retrieval'>('tags');
  const [showTemplateEditor, setShowTemplateEditor] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Partial<PromptTemplate> | null>(null);
  const [isNewTemplate, setIsNewTemplate] = useState(false);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [showNewTag, setShowNewTag] = useState<string | null>(null);
  const [newTagForm, setNewTagForm] = useState({ value: '', display_name: '', description: '' });
  const [confirmDeleteTemplate, setConfirmDeleteTemplate] = useState<string | null>(null);

  useEffect(() => {
    loadPromptTemplates();
    loadTagCategories();
  }, []);

  // 按类型筛选模板
  const annotationTemplates = promptTemplates.filter(t => t.template_type === 'system' || t.template_type === 'user');
  const retrievalTemplates = promptTemplates.filter(t => t.template_type === 'retrieval' || t.template_type === 'chat');

  const handleSaveTemplate = async () => {
    if (!editingTemplate) return;
    try {
      if (isNewTemplate) {
        await createPromptTemplate(editingTemplate as any);
      } else {
        await updatePromptTemplate(editingTemplate.id!, editingTemplate as any);
      }
      setShowTemplateEditor(false);
      setEditingTemplate(null);
      await loadPromptTemplates();
    } catch (e: any) {
      alert('保存失败: ' + (e.message || ''));
    }
  };

  const handleDeleteTemplate = async (id: string) => {
    try {
      await deletePromptTemplate(id);
      setConfirmDeleteTemplate(null);
      await loadPromptTemplates();
    } catch (e: any) {
      alert('删除失败: ' + (e.message || ''));
    }
  };

  const handleAddTag = async (categoryId: string) => {
    if (!newTagForm.value || !newTagForm.display_name) return;
    try {
      await createTagDefinition({ category_id: categoryId, ...newTagForm });
      setNewTagForm({ value: '', display_name: '', description: '' });
      setShowNewTag(null);
      await loadTagDefinitions(categoryId);
      await loadTagCategories();
    } catch (e: any) {
      alert('添加失败: ' + (e.message || ''));
    }
  };

  const renderTemplateList = (templates: PromptTemplate[], type: string) => (
    <div className="space-y-3">
      {templates.map(t => (
        <div key={t.id} className="px-4 py-3 rounded-xl border border-white/10 bg-white/[0.02] hover:border-white/20 transition">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{t.name}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                t.template_type === 'system' ? 'bg-blue-500/20 text-blue-400'
                  : t.template_type === 'user' ? 'bg-green-500/20 text-green-400'
                    : t.template_type === 'retrieval' ? 'bg-purple-500/20 text-purple-400'
                      : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {t.template_type === 'system' ? '系统' : t.template_type === 'user' ? '用户' : t.template_type === 'retrieval' ? '检索' : '对话'}
              </span>
              <span className="text-[10px] px-1.5 py-0.5 bg-gray-500/20 text-gray-400 rounded-full">v{t.version}</span>
              {t.is_active && <span className="text-[10px] px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded-full">激活</span>}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => { setEditingTemplate({ ...t }); setIsNewTemplate(false); setShowTemplateEditor(true); }}
                className="px-2 py-1 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
              >
                <Pencil size={12} />
              </button>
              {confirmDeleteTemplate === t.id ? (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleDeleteTemplate(t.id)}
                    className="px-2 py-1 text-xs rounded-lg bg-red-600 hover:bg-red-500 text-white transition"
                  >
                    确认
                  </button>
                  <button
                    onClick={() => setConfirmDeleteTemplate(null)}
                    className="px-2 py-1 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 transition"
                  >
                    取消
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmDeleteTemplate(t.id)}
                  className="px-2 py-1 text-xs rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          </div>
          {t.description && <p className="text-xs text-gray-500 mb-2">{t.description}</p>}
          <pre className="text-xs text-gray-400 bg-black/30 rounded-lg p-3 overflow-x-auto max-h-24 overflow-y-auto whitespace-pre-wrap">
            {t.prompt_text?.substring(0, 300)}{(t.prompt_text?.length || 0) > 300 ? '...' : ''}
          </pre>
          {t.variables && (
            <div className="mt-2 flex items-center gap-1 text-[10px] text-gray-600">
              <span>变量:</span>
              {t.variables.split(',').map(v => (
                <span key={v.trim()} className="px-1.5 py-0.5 bg-white/5 rounded">{`{{${v.trim()}}}`}</span>
              ))}
            </div>
          )}
        </div>
      ))}
      {templates.length === 0 && (
        <div className="text-center py-8 text-gray-500 text-sm">暂无模板，点击右上角添加</div>
      )}
    </div>
  );

  return (
    <>
      {/* 页面标题 */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-3">
          <BookOpen size={28} className="text-blue-400" /> 提示词管理
        </h2>
        <p className="text-sm text-gray-500 mt-1">管理语义标签、标注提示词和检索对话模板</p>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-1 p-1 bg-white/5 rounded-xl w-fit">
        <button
          onClick={() => setPromptTab('tags')}
          className={`px-5 py-2 text-sm rounded-lg transition-all ${
            promptTab === 'tags' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          🏷️ 语义标签
        </button>
        <button
          onClick={() => setPromptTab('annotation')}
          className={`px-5 py-2 text-sm rounded-lg transition-all ${
            promptTab === 'annotation' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          ✍️ 标注提示词
        </button>
        <button
          onClick={() => setPromptTab('retrieval')}
          className={`px-5 py-2 text-sm rounded-lg transition-all ${
            promptTab === 'retrieval' ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          💬 检索对话模板
        </button>
      </div>

      {/* ===== 语义标签管理 ===== */}
      {promptTab === 'tags' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <p className="text-xs text-gray-500">管理语义标注中使用的标签分类和标签定义</p>
            <button
              onClick={() => { loadTagCategories(); }}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 transition"
            >
              <RefreshCw size={12} /> 刷新
            </button>
          </div>

          {tagCategories.length > 0 ? tagCategories.map(cat => (
            <div key={cat.id} className="rounded-xl border border-white/5 bg-[#151515] overflow-hidden">
              {/* 分类头部 */}
              <div
                className="flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-white/[0.02] transition"
                onClick={() => {
                  if (expandedCategory === cat.id) {
                    setExpandedCategory(null);
                  } else {
                    setExpandedCategory(cat.id);
                    if (!tagDefinitions[cat.id]) loadTagDefinitions(cat.id);
                  }
                }}
              >
                <div className="flex items-center gap-2 flex-1">
                  <Tag size={14} className="text-blue-400" />
                  <span className="font-medium text-sm">{cat.name}</span>
                  <span className="text-xs text-gray-600">· 第{cat.layer}层</span>
                  {cat.is_required && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded-full">必填</span>
                  )}
                  {cat.is_multi_select && (
                    <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded-full">多选</span>
                  )}
                  <span className="text-[10px] px-1.5 py-0.5 bg-gray-500/20 text-gray-400 rounded-full">
                    {cat.tag_count || 0} 个标签
                  </span>
                </div>
                <ChevronDown
                  size={14}
                  className={`text-gray-500 transition-transform ${expandedCategory === cat.id ? 'rotate-180' : ''}`}
                />
              </div>

              {/* 展开的标签列表 */}
              {expandedCategory === cat.id && (
                <div className="px-5 pb-4 border-t border-white/5 pt-3">
                  {cat.description && <p className="text-xs text-gray-500 mb-3">{cat.description}</p>}

                  {/* 标签列表 */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    {(tagDefinitions[cat.id] || []).map(tag => (
                      <div
                        key={tag.id}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition ${
                          tag.is_active
                            ? 'bg-blue-500/10 text-blue-300 border border-blue-500/20'
                            : 'bg-white/5 text-gray-500 border border-white/5 line-through'
                        }`}
                      >
                        <span title={tag.description || tag.value}>{tag.display_name}</span>
                        {tag.is_builtin && <span className="text-[9px] text-gray-600">内置</span>}
                        <button
                          onClick={async () => {
                            await updateTagDefinition(tag.id, { is_active: !tag.is_active });
                            loadTagDefinitions(cat.id);
                          }}
                          className="ml-1 hover:text-yellow-400 transition"
                          title={tag.is_active ? '禁用' : '启用'}
                        >
                          {tag.is_active ? <X size={10} /> : <Check size={10} />}
                        </button>
                        {!tag.is_builtin && (
                          <button
                            onClick={async () => {
                              await deleteTagDefinition(tag.id);
                              loadTagDefinitions(cat.id);
                              loadTagCategories();
                            }}
                            className="hover:text-red-400 transition"
                            title="删除"
                          >
                            <Trash2 size={10} />
                          </button>
                        )}
                      </div>
                    ))}
                    {(tagDefinitions[cat.id] || []).length === 0 && (
                      <span className="text-xs text-gray-600">加载中...</span>
                    )}
                  </div>

                  {/* 添加新标签 */}
                  {showNewTag === cat.id ? (
                    <div className="flex gap-2 items-end">
                      <div className="flex-1">
                        <label className="text-[10px] text-gray-500 mb-0.5 block">值 (英文)</label>
                        <input
                          className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-xs outline-none focus:border-blue-500/50"
                          value={newTagForm.value}
                          onChange={e => setNewTagForm({ ...newTagForm, value: e.target.value })}
                          placeholder="english_key"
                        />
                      </div>
                      <div className="flex-1">
                        <label className="text-[10px] text-gray-500 mb-0.5 block">显示名</label>
                        <input
                          className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-xs outline-none focus:border-blue-500/50"
                          value={newTagForm.display_name}
                          onChange={e => setNewTagForm({ ...newTagForm, display_name: e.target.value })}
                          placeholder="中文名"
                        />
                      </div>
                      <button
                        onClick={() => handleAddTag(cat.id)}
                        disabled={!newTagForm.value || !newTagForm.display_name}
                        className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-500 transition disabled:opacity-40"
                      >
                        添加
                      </button>
                      <button
                        onClick={() => { setShowNewTag(null); setNewTagForm({ value: '', display_name: '', description: '' }); }}
                        className="px-2 py-1 text-xs bg-white/5 text-gray-400 rounded hover:bg-white/10 transition"
                      >
                        取消
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowNewTag(cat.id)}
                      className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-400 transition"
                    >
                      <Plus size={12} /> 添加标签
                    </button>
                  )}
                </div>
              )}
            </div>
          )) : (
            <div className="text-center py-12 text-gray-600">
              <Tag size={32} className="mx-auto mb-3 opacity-50" />
              <p>暂无标签分类</p>
            </div>
          )}
        </div>
      )}

      {/* ===== 标注提示词 ===== */}
      {promptTab === 'annotation' && (
        <SettingsSection
          title="标注提示词模板"
          icon={<MessageSquare size={18} />}
          description="语义标注时与LLM交互使用的系统提示词和用户模板"
          action={
            <button
              onClick={() => {
                setEditingTemplate({ template_type: 'system', name: '', prompt_text: '', version: '1.0.0', description: '' });
                setIsNewTemplate(true);
                setShowTemplateEditor(true);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition"
            >
              <Plus size={12} /> 新建模板
            </button>
          }
        >
          {renderTemplateList(annotationTemplates, 'annotation')}
        </SettingsSection>
      )}

      {/* ===== 检索对话提示词 ===== */}
      {promptTab === 'retrieval' && (
        <SettingsSection
          title="检索对话模板"
          icon={<MessageSquare size={18} />}
          description="与LLM对话检索时使用的提示词模板"
          action={
            <button
              onClick={() => {
                setEditingTemplate({ template_type: 'retrieval', name: '', prompt_text: '', version: '1.0.0', description: '' });
                setIsNewTemplate(true);
                setShowTemplateEditor(true);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition"
            >
              <Plus size={12} /> 新建模板
            </button>
          }
        >
          {renderTemplateList(retrievalTemplates, 'retrieval')}
        </SettingsSection>
      )}

      {/* 模板编辑弹窗 */}
      {showTemplateEditor && editingTemplate && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowTemplateEditor(false)}
        >
          <div
            className="bg-[#1a1a1a] rounded-2xl border border-white/10 shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-5 border-b border-white/5">
              <h3 className="text-lg font-bold">{isNewTemplate ? '新建提示词模板' : '编辑提示词模板'}</h3>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">模板名称 *</label>
                  <input
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                    value={editingTemplate.name || ''}
                    onChange={e => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                    placeholder="输入模板名称"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">模板类型</label>
                  <select
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                    value={editingTemplate.template_type || 'system'}
                    onChange={e => setEditingTemplate({ ...editingTemplate, template_type: e.target.value as any })}
                  >
                    <option value="system">系统提示词</option>
                    <option value="user">用户模板</option>
                    <option value="retrieval">检索模板</option>
                    <option value="chat">对话模板</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">描述</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingTemplate.description || ''}
                  onChange={e => setEditingTemplate({ ...editingTemplate, description: e.target.value })}
                  placeholder="简要描述模板用途"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">提示词内容 *</label>
                <textarea
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none resize-none h-48 focus:border-blue-500/50 font-mono"
                  value={editingTemplate.prompt_text || ''}
                  onChange={e => setEditingTemplate({ ...editingTemplate, prompt_text: e.target.value })}
                  placeholder={'输入提示词内容...\n支持变量: {{line_text}}, {{character_name}}, {{movie_title}} 等'}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">变量列表</label>
                  <input
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                    value={editingTemplate.variables || ''}
                    onChange={e => setEditingTemplate({ ...editingTemplate, variables: e.target.value })}
                    placeholder="如: line_text,character_name"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">版本</label>
                  <input
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                    value={editingTemplate.version || '1.0.0'}
                    onChange={e => setEditingTemplate({ ...editingTemplate, version: e.target.value })}
                  />
                </div>
              </div>
            </div>
            <div className="p-5 border-t border-white/5 flex justify-end gap-3">
              <button
                onClick={() => { setShowTemplateEditor(false); setEditingTemplate(null); }}
                className="px-4 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
              >
                取消
              </button>
              <button
                onClick={handleSaveTemplate}
                disabled={!editingTemplate.name || !editingTemplate.prompt_text}
                className="px-6 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
