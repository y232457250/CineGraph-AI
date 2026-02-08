// frontend-ui/src/settings/ModelManagementTab.tsx
/**
 * 设置中心 - 模型管理Tab
 */

import { useState, useMemo } from 'react';
import {
  Cpu, CheckCircle2, XCircle, Loader2, ChevronDown,
  RefreshCw, AlertTriangle, Zap, ZapOff,
  Server, TestTube, Plus, Cloud, Star,
  Pencil, Trash2, RotateCcw,
} from 'lucide-react';
import useSettingsStore from '../store/settingsStore';
import type { ModelProvider } from '../types/settings';
import { emptyProvider } from './SettingsShared';
import ModelEditorModal from './ModelEditorModal';

export default function ModelManagementTab() {
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

  const handleAdd = () => { setEditingProvider(emptyProvider(modelTab)); setIsNewProvider(true); setShowEditor(true); };
  const handleEdit = (p: ModelProvider) => { setEditingProvider({ ...p }); setIsNewProvider(false); setShowEditor(true); };

  const handleSave = async () => {
    if (!editingProvider) return;
    setLoading(true);
    try {
      if (isNewProvider) await createProvider(editingProvider as any);
      else await updateProvider(editingProvider.id!, editingProvider as any);
      setShowEditor(false); setEditingProvider(null);
      if (modelTab === 'llm') await loadLLMProviders(); else await loadEmbeddingProviders();
    } catch (e: any) { alert('保存失败: ' + (e.message || '未知错误')); }
    setLoading(false);
  };

  const handleDelete = async (id: string) => {
    setLoading(true);
    try { await deleteProvider(id); setConfirmDelete(null); if (modelTab === 'llm') await loadLLMProviders(); else await loadEmbeddingProviders(); }
    catch (e: any) { alert('删除失败: ' + (e.message || '未知错误')); }
    setLoading(false);
  };

  const handleTest = async (p: ModelProvider) => {
    setTestResults(prev => ({ ...prev, [p.id]: 'loading' }));
    try { const ok = await testLLMConnection(p.id); setTestResults(prev => ({ ...prev, [p.id]: ok ? 'success' : 'fail' })); }
    catch { setTestResults(prev => ({ ...prev, [p.id]: 'fail' })); }
  };

  const handleReset = async () => {
    setLoading(true);
    try { await resetProviderDefaults(); setConfirmReset(false); await loadLLMProviders(); await loadEmbeddingProviders(); }
    catch (e: any) { alert('重置失败: ' + (e.message || '未知错误')); }
    setLoading(false);
  };

  const toggleExpand = (id: string) => {
    setExpandedCards(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });
  };

  const renderCard = (p: ModelProvider) => {
    const isActive = p.id === activeProviderId;
    const expanded = expandedCards.has(p.id);
    const test = testResults[p.id];
    return (
      <div key={p.id} className={`rounded-lg border transition-all ${isActive ? 'border-blue-500/60 bg-blue-500/5 shadow-lg shadow-blue-500/10' : p.enabled ? 'border-white/10 bg-white/[0.02] hover:border-white/20' : 'border-white/5 bg-white/[0.01] opacity-50'}`}>
        <div className="flex items-center gap-3 px-3 py-2 cursor-pointer" onClick={() => toggleExpand(p.id)}>
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isActive ? 'bg-green-400 shadow-green-400/50 shadow-lg' : p.enabled ? 'bg-gray-500' : 'bg-red-500/50'}`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm truncate">{p.name}</span>
              {isActive && <span className="text-[10px] px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded-full flex items-center gap-1"><Star size={8} /> 激活</span>}
              {p.is_default && <span className="text-[10px] px-1.5 py-0.5 bg-gray-500/20 text-gray-400 rounded-full">预置</span>}
            </div>
            <div className="text-xs text-gray-500 truncate">{p.model} · {p.price_info || '无价格信息'}</div>
          </div>
          {test === 'loading' && <Loader2 size={14} className="animate-spin text-blue-400" />}
          {test === 'success' && <CheckCircle2 size={14} className="text-green-400" />}
          {test === 'fail' && <XCircle size={14} className="text-red-400" />}
          <ChevronDown size={14} className={`text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>

        {expanded && (
          <div className="px-3 pb-2.5 border-t border-white/5 pt-2.5 space-y-2">
            <div className="grid grid-cols-3 gap-x-4 gap-y-1 text-xs">
              <div><span className="text-gray-500">API 地址</span><p className="text-gray-300 truncate">{p.base_url}</p></div>
              <div><span className="text-gray-500">模型</span><p className="text-gray-300 truncate">{p.model}</p></div>
              <div><span className="text-gray-500">超时</span><p className="text-gray-300">{p.timeout}s</p></div>
              {modelTab === 'llm' && <><div><span className="text-gray-500">温度</span><p className="text-gray-300">{p.temperature}</p></div><div><span className="text-gray-500">最大Token</span><p className="text-gray-300">{p.max_tokens}</p></div></>}
              {modelTab === 'embedding' && <><div><span className="text-gray-500">维度</span><p className="text-gray-300">{p.dimension || '自动'}</p></div><div><span className="text-gray-500">API风格</span><p className="text-gray-300">{p.api_style}</p></div></>}
              <div><span className="text-gray-500">API Key</span><p className="text-gray-300">{p.api_key || '(无)'}</p></div>
            </div>
            {p.description && <p className="text-xs text-gray-500 italic">{p.description}</p>}
            <div className="flex gap-1.5 flex-wrap">
              <button onClick={(e) => { e.stopPropagation(); handleTest(p); }} className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"><TestTube size={11} /> 测试</button>
              {!isActive && p.enabled && <button onClick={(e) => { e.stopPropagation(); modelTab === 'llm' ? setActiveLLMProvider(p.id) : setActiveEmbeddingProvider(p.id); }} className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 transition"><Zap size={11} /> 激活</button>}
              <button onClick={(e) => { e.stopPropagation(); toggleProvider(p.id, !p.enabled); }} className={`flex items-center gap-1 px-2 py-1 text-xs rounded-lg transition ${p.enabled ? 'bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400' : 'bg-green-500/10 hover:bg-green-500/20 text-green-400'}`}>{p.enabled ? <><ZapOff size={11} /> 停用</> : <><Zap size={11} /> 启用</>}</button>
              <button onClick={(e) => { e.stopPropagation(); handleEdit(p); }} className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"><Pencil size={11} /> 编辑</button>
              {providers.length > 1 && <button onClick={(e) => { e.stopPropagation(); setConfirmDelete(p.id); }} className="flex items-center gap-1 px-2 py-1 text-xs rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition"><Trash2 size={11} /> 删除</button>}
            </div>
          </div>
        )}

        {confirmDelete === p.id && (
          <div className="px-3 pb-2 border-t border-red-500/20 pt-2 flex items-center gap-3">
            <AlertTriangle size={14} className="text-red-400 flex-shrink-0" />
            <span className="text-xs text-red-300">确认删除此模型？</span>
            <div className="flex-1" />
            <button onClick={() => handleDelete(p.id)} className="text-xs px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded-lg transition">确认</button>
            <button onClick={() => setConfirmDelete(null)} className="text-xs px-3 py-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg transition">取消</button>
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
          <h2 className="text-lg font-bold flex items-center gap-2"><Cpu size={22} className="text-blue-400" /> 模型管理</h2>
          <p className="text-xs text-gray-500 mt-0.5">管理语义标注/AI助手模型和向量化模型</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => { loadLLMProviders(); loadEmbeddingProviders(); }} className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"><RefreshCw size={12} /> 刷新</button>
          <button onClick={() => setConfirmReset(true)} className="flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 transition"><RotateCcw size={12} /> 重置</button>
        </div>
      </div>

      {/* Tab 切换 + 统计 */}
      <div className="flex items-center gap-4">
        <div className="flex gap-1 p-0.5 bg-white/5 rounded-lg">
          <button onClick={() => setModelTab('llm')} className={`px-4 py-1.5 text-xs rounded-md transition-all ${modelTab === 'llm' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>🧠 语义标注/AI助手模型</button>
          <button onClick={() => setModelTab('embedding')} className={`px-4 py-1.5 text-xs rounded-md transition-all ${modelTab === 'embedding' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>📐 向量化模型</button>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>已配置 <strong className="text-white">{providers.length}</strong></span>
          <span>启用 <strong className="text-green-400">{providers.filter(p => p.enabled).length}</strong></span>
          <span>激活 <strong className="text-blue-400">{providers.find(p => p.id === activeProviderId)?.name || '-'}</strong></span>
        </div>
      </div>

      {/* 添加按钮 */}
      <button onClick={handleAdd} className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-dashed border-white/10 hover:border-blue-500/40 bg-white/[0.01] hover:bg-blue-500/5 text-gray-400 hover:text-blue-400 transition-all text-sm">
        <Plus size={16} /> 添加{modelTab === 'llm' ? '语义标注/AI助手' : '向量化'}模型
      </button>

      {/* 模型列表 */}
      <div className="space-y-4">
        {grouped.local.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-[11px] text-gray-400 uppercase tracking-wider px-1"><Server size={11} /> 本地模型 ({grouped.local.length})</div>
            <div className="space-y-1.5">{grouped.local.map(renderCard)}</div>
          </div>
        )}
        {grouped.commercial.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-[11px] text-gray-400 uppercase tracking-wider px-1"><Cloud size={11} /> 商用 API ({grouped.commercial.length})</div>
            <div className="space-y-1.5">{grouped.commercial.map(renderCard)}</div>
          </div>
        )}
        {providers.length === 0 && (
          <div className="text-center py-10 text-gray-600"><Cpu size={28} className="mx-auto mb-2 opacity-50" /><p className="text-sm">暂无模型，点击上方按钮添加</p></div>
        )}
      </div>

      {/* 编辑弹窗 */}
      {showEditor && editingProvider && (
        <ModelEditorModal provider={editingProvider} isNew={isNewProvider} loading={loading} onSave={handleSave} onClose={() => { setShowEditor(false); setEditingProvider(null); }} onChange={setEditingProvider} />
      )}

      {/* 重置确认 */}
      {confirmReset && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setConfirmReset(false)}>
          <div className="bg-[#1a1a1a] rounded-2xl border border-orange-500/20 shadow-2xl max-w-sm w-full p-5 space-y-3" onClick={e => e.stopPropagation()}>
            <div className="flex items-center gap-3"><AlertTriangle size={20} className="text-orange-400" /><h3 className="font-bold">重置为默认配置？</h3></div>
            <p className="text-sm text-gray-400">此操作将删除所有自定义模型，恢复为系统默认配置。</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setConfirmReset(false)} className="px-4 py-1.5 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition">取消</button>
              <button onClick={handleReset} disabled={loading} className="px-4 py-1.5 text-sm rounded-lg bg-orange-600 hover:bg-orange-500 text-white transition flex items-center gap-2">{loading && <Loader2 size={14} className="animate-spin" />}确认重置</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
