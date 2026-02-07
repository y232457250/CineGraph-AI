/**
 * ModelManagementPanel - 独立模型管理页面
 * 
 * 提供完整的模型提供者CRUD管理界面：
 * - 查看所有已配置的LLM和Embedding模型
 * - 添加/编辑/删除模型
 * - 测试连接
 * - 激活/停用模型
 * - 重置为默认配置
 */
import { useState, useEffect, useMemo } from 'react';
import { useSettingsStore } from './store/settingsStore';
import type { ModelProvider } from './types/settings';
import {
  Cpu, Plus, Pencil, Trash2, RotateCcw, Zap, ZapOff,
  CheckCircle2, XCircle, Loader2, RefreshCw, ChevronDown,
  Server, Cloud, AlertTriangle, TestTube, Star
} from 'lucide-react';

type TabKey = 'llm' | 'embedding';

// 空白模型模板
const emptyProvider = (category: TabKey): Partial<ModelProvider> => ({
  name: '',
  category,
  provider_type: 'local',
  local_mode: 'ollama',
  base_url: category === 'llm' ? 'http://localhost:11434/v1' : 'http://localhost:11434',
  model: '',
  api_key: '',
  api_style: 'openai',
  max_tokens: 2000,
  temperature: 0.7,
  timeout: 60,
  dimension: 0,
  description: '',
  price_info: '',
});

export default function ModelManagementPanel() {
  const {
    llmProviders, embeddingProviders,
    activeLLMProvider, activeEmbeddingProvider,
    loadLLMProviders, loadEmbeddingProviders,
    setActiveLLMProvider, setActiveEmbeddingProvider,
    testLLMConnection,
    createProvider, updateProvider, deleteProvider, toggleProvider, resetProviderDefaults,
  } = useSettingsStore();

  const [activeTab, setActiveTab] = useState<TabKey>('llm');
  const [showEditor, setShowEditor] = useState(false);
  const [editingProvider, setEditingProvider] = useState<Partial<ModelProvider> | null>(null);
  const [isNewProvider, setIsNewProvider] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, 'loading' | 'success' | 'fail'>>({});
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [loading, setLoading] = useState(false);
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

  // 加载数据
  useEffect(() => {
    loadLLMProviders();
    loadEmbeddingProviders();
  }, []);

  const providers = activeTab === 'llm' ? llmProviders : embeddingProviders;
  const activeProviderId = activeTab === 'llm' ? activeLLMProvider : activeEmbeddingProvider;

  // 按类型分组
  const grouped = useMemo(() => {
    const local = providers.filter(p => p.provider_type === 'local');
    const commercial = providers.filter(p => p.provider_type === 'commercial');
    return { local, commercial };
  }, [providers]);

  // 操作：添加
  const handleAdd = () => {
    setEditingProvider(emptyProvider(activeTab));
    setIsNewProvider(true);
    setShowEditor(true);
  };

  // 操作：编辑
  const handleEdit = (p: ModelProvider) => {
    setEditingProvider({ ...p });
    setIsNewProvider(false);
    setShowEditor(true);
  };

  // 操作：保存
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
      // 刷新列表
      if (activeTab === 'llm') await loadLLMProviders();
      else await loadEmbeddingProviders();
    } catch (e: any) {
      alert('保存失败: ' + (e.message || '未知错误'));
    }
    setLoading(false);
  };

  // 操作：删除
  const handleDelete = async (id: string) => {
    setLoading(true);
    try {
      await deleteProvider(id);
      setConfirmDelete(null);
      if (activeTab === 'llm') await loadLLMProviders();
      else await loadEmbeddingProviders();
    } catch (e: any) {
      alert('删除失败: ' + (e.message || '未知错误'));
    }
    setLoading(false);
  };

  // 操作：激活
  const handleActivate = async (id: string) => {
    try {
      if (activeTab === 'llm') await setActiveLLMProvider(id);
      else await setActiveEmbeddingProvider(id);
    } catch (e: any) {
      alert('激活失败: ' + (e.message || '未知错误'));
    }
  };

  // 操作：启用/禁用
  const handleToggle = async (id: string, currentEnabled: boolean) => {
    try {
      await toggleProvider(id, !currentEnabled);
    } catch (e: any) {
      alert('操作失败: ' + (e.message || '未知错误'));
    }
  };

  // 操作：测试连接
  const handleTest = async (p: ModelProvider) => {
    setTestResults(prev => ({ ...prev, [p.id]: 'loading' }));
    try {
      const ok = await testLLMConnection(p.id);
      setTestResults(prev => ({ ...prev, [p.id]: ok ? 'success' : 'fail' }));
    } catch {
      setTestResults(prev => ({ ...prev, [p.id]: 'fail' }));
    }
  };

  // 操作：重置
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

  // 切换卡片展开
  const toggleCard = (id: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  // 渲染模型卡片
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
        <div className="flex items-center gap-3 px-4 py-3 cursor-pointer" onClick={() => toggleCard(p.id)}>
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

          {/* 测试状态 */}
          {test === 'loading' && <Loader2 size={14} className="animate-spin text-blue-400" />}
          {test === 'success' && <CheckCircle2 size={14} className="text-green-400" />}
          {test === 'fail' && <XCircle size={14} className="text-red-400" />}

          <ChevronDown size={14} className={`text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>

        {/* 展开详情 */}
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
              {activeTab === 'llm' && (
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
              {activeTab === 'embedding' && (
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
            {p.description && (
              <p className="text-xs text-gray-500 italic">{p.description}</p>
            )}

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
                  onClick={(e) => { e.stopPropagation(); handleActivate(p.id); }}
                  className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 transition"
                >
                  <Zap size={12} /> 激活
                </button>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); handleToggle(p.id, p.enabled); }}
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
            <button onClick={() => handleDelete(p.id)} className="text-xs px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded-lg transition">
              确认
            </button>
            <button onClick={() => setConfirmDelete(null)} className="text-xs px-3 py-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg transition">
              取消
            </button>
          </div>
        )}
      </div>
    );
  };

  // 渲染分组
  const renderGroup = (title: string, icon: React.ReactNode, items: ModelProvider[]) => {
    if (items.length === 0) return null;
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-gray-400 uppercase tracking-wider px-1 py-1">
          {icon}
          <span>{title}</span>
          <span className="text-gray-600">({items.length})</span>
        </div>
        <div className="space-y-2">
          {items.map(renderCard)}
        </div>
      </div>
    );
  };

  return (
    <div className="w-full h-full overflow-y-auto p-6 bg-[#0d0d0d]">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 页面标题 */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Cpu size={28} className="text-blue-400" />
              模型管理
            </h1>
            <p className="text-sm text-gray-500 mt-1">管理 LLM 和 Embedding 模型提供者，所有配置存储在数据库中</p>
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

        {/* Tab 切换 */}
        <div className="flex gap-1 p-1 bg-white/5 rounded-xl w-fit">
          <button
            onClick={() => setActiveTab('llm')}
            className={`px-5 py-2 text-sm rounded-lg transition-all ${
              activeTab === 'llm'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            🧠 LLM 大语言模型
          </button>
          <button
            onClick={() => setActiveTab('embedding')}
            className={`px-5 py-2 text-sm rounded-lg transition-all ${
              activeTab === 'embedding'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
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
            <div className="text-2xl font-bold text-blue-400">
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
          <span className="text-sm">添加{activeTab === 'llm' ? 'LLM' : 'Embedding'}模型</span>
        </button>

        {/* 模型列表 */}
        <div className="space-y-6">
          {renderGroup('本地模型', <Server size={12} />, grouped.local)}
          {renderGroup('商用 API', <Cloud size={12} />, grouped.commercial)}
        </div>

        {providers.length === 0 && (
          <div className="text-center py-16 text-gray-600">
            <Cpu size={48} className="mx-auto mb-4 opacity-30" />
            <p>暂无{activeTab === 'llm' ? 'LLM' : 'Embedding'}模型配置</p>
            <p className="text-sm mt-1">点击上方"添加模型"按钮来配置</p>
          </div>
        )}
      </div>

      {/* ===== 编辑模态框 ===== */}
      {showEditor && editingProvider && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowEditor(false)}>
          <div className="bg-[#1a1a1a] rounded-2xl border border-white/10 shadow-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b border-white/5">
              <h3 className="text-lg font-bold">{isNewProvider ? '添加模型' : '编辑模型'}</h3>
              <p className="text-xs text-gray-500 mt-1">
                {isNewProvider ? '配置新的模型提供者' : `编辑: ${editingProvider.name}`}
              </p>
            </div>

            <div className="p-5 space-y-4">
              {/* 名称 */}
              <div>
                <label className="text-xs text-gray-400 mb-1 block">显示名称 *</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingProvider.name || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, name: e.target.value })}
                  placeholder="例: 我的Ollama模型"
                />
              </div>

              {/* 类型选择 */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">提供者类型</label>
                  <select
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                    value={editingProvider.provider_type || 'local'}
                    onChange={e => {
                      const type = e.target.value as 'local' | 'commercial';
                      setEditingProvider({
                        ...editingProvider,
                        provider_type: type,
                        local_mode: type === 'local' ? 'ollama' : '',
                        base_url: type === 'local'
                          ? (editingProvider.category === 'llm' ? 'http://localhost:11434/v1' : 'http://localhost:11434')
                          : editingProvider.base_url || '',
                      });
                    }}
                  >
                    <option value="local">本地部署</option>
                    <option value="commercial">商用API</option>
                  </select>
                </div>
                {editingProvider.provider_type === 'local' && (
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">本地模式</label>
                    <select
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                      value={editingProvider.local_mode || 'ollama'}
                      onChange={e => setEditingProvider({ ...editingProvider, local_mode: e.target.value })}
                    >
                      <option value="ollama">Ollama</option>
                      <option value="docker">Docker</option>
                    </select>
                  </div>
                )}
              </div>

              {/* API配置 */}
              <div>
                <label className="text-xs text-gray-400 mb-1 block">API 地址 *</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingProvider.base_url || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, base_url: e.target.value })}
                  placeholder="http://localhost:11434/v1"
                />
              </div>

              <div>
                <label className="text-xs text-gray-400 mb-1 block">模型名称 *</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingProvider.model || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, model: e.target.value })}
                  placeholder="qwen3:4b"
                />
              </div>

              <div>
                <label className="text-xs text-gray-400 mb-1 block">API Key</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingProvider.api_key || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, api_key: e.target.value })}
                  placeholder="留空或 ${ENV_VAR} 引用环境变量"
                />
              </div>

              {/* Embedding专用 */}
              {editingProvider.category === 'embedding' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">API风格</label>
                    <select
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                      value={editingProvider.api_style || 'openai'}
                      onChange={e => setEditingProvider({ ...editingProvider, api_style: e.target.value })}
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
                      value={editingProvider.dimension || 0}
                      onChange={e => setEditingProvider({ ...editingProvider, dimension: parseInt(e.target.value) || 0 })}
                      placeholder="0=自动"
                    />
                  </div>
                </div>
              )}

              {/* LLM参数 */}
              {editingProvider.category === 'llm' && (
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">最大Token</label>
                    <input
                      type="number"
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none"
                      value={editingProvider.max_tokens || 2000}
                      onChange={e => setEditingProvider({ ...editingProvider, max_tokens: parseInt(e.target.value) || 2000 })}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 mb-1 block">温度</label>
                    <input
                      type="number"
                      step="0.1"
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

              {/* 元信息 */}
              <div>
                <label className="text-xs text-gray-400 mb-1 block">描述</label>
                <textarea
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none resize-none h-16 focus:border-blue-500/50"
                  value={editingProvider.description || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, description: e.target.value })}
                  placeholder="模型简介..."
                />
              </div>

              <div>
                <label className="text-xs text-gray-400 mb-1 block">价格信息</label>
                <input
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none focus:border-blue-500/50"
                  value={editingProvider.price_info || ''}
                  onChange={e => setEditingProvider({ ...editingProvider, price_info: e.target.value })}
                  placeholder="如: 免费 / ¥1/百万token"
                />
              </div>
            </div>

            {/* 底部按钮 */}
            <div className="p-5 border-t border-white/5 flex justify-end gap-3">
              <button
                onClick={() => setShowEditor(false)}
                className="px-4 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={loading || !editingProvider.name || !editingProvider.model || !editingProvider.base_url}
                className="px-6 py-2 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center gap-2"
              >
                {loading && <Loader2 size={14} className="animate-spin" />}
                {isNewProvider ? '添加' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===== 重置确认模态框 ===== */}
      {confirmReset && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setConfirmReset(false)}>
          <div className="bg-[#1a1a1a] rounded-2xl border border-orange-500/20 shadow-2xl max-w-sm w-full p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <AlertTriangle size={24} className="text-orange-400" />
              <h3 className="text-lg font-bold">重置为默认配置？</h3>
            </div>
            <p className="text-sm text-gray-400">
              此操作将删除所有自定义模型，恢复为系统默认的模型提供者配置。已激活的模型将被重置。
            </p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirmReset(false)} className="px-4 py-2 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition">
                取消
              </button>
              <button onClick={handleReset} disabled={loading} className="px-4 py-2 text-sm rounded-lg bg-orange-600 hover:bg-orange-500 text-white transition flex items-center gap-2">
                {loading && <Loader2 size={14} className="animate-spin" />}
                确认重置
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
