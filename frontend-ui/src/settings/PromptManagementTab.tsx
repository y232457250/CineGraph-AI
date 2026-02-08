// frontend-ui/src/settings/PromptManagementTab.tsx
/**
 * 设置中心 - 提示词管理Tab
 * 语义标签 / 标注提示词(prompt_config.json) / 检索对话模板
 */

import { useState, useEffect, useMemo } from 'react';
import {
  BookOpen, Plus, RefreshCw, Tag, MessageSquare,
  Pencil, Trash2, Check, X, ChevronDown, ChevronRight,
  Save, Loader2, CheckCircle2, AlertCircle,
  Layers, Eye, EyeOff,
  FileJson, RotateCcw,
} from 'lucide-react';
import useSettingsStore from '../store/settingsStore';
import type { PromptTemplate } from '../types/settings';
import { SettingsSection } from './SettingsShared';

const API_BASE = 'http://127.0.0.1:8000';

// ==================== 标签颜色方案 ====================
const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  sentence_type: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20', dot: 'bg-blue-400' },
  emotion:       { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/20', dot: 'bg-rose-400' },
  tone:          { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20', dot: 'bg-amber-400' },
  character_type:{ bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', dot: 'bg-emerald-400' },
  scene_type:    { bg: 'bg-violet-500/10', text: 'text-violet-400', border: 'border-violet-500/20', dot: 'bg-violet-400' },
  speaking_style:{ bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20', dot: 'bg-cyan-400' },
  speech_style:  { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20', dot: 'bg-cyan-400' },
  context_dye:   { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/20', dot: 'bg-orange-400' },
  subtext_type:  { bg: 'bg-pink-500/10', text: 'text-pink-400', border: 'border-pink-500/20', dot: 'bg-pink-400' },
  social_function:{ bg: 'bg-teal-500/10', text: 'text-teal-400', border: 'border-teal-500/20', dot: 'bg-teal-400' },
  dramatic_function: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20', dot: 'bg-indigo-400' },
  power_dynamic: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', dot: 'bg-red-400' },
  semantic_field:{ bg: 'bg-lime-500/10', text: 'text-lime-400', border: 'border-lime-500/20', dot: 'bg-lime-400' },
  primary_function: { bg: 'bg-sky-500/10', text: 'text-sky-400', border: 'border-sky-500/20', dot: 'bg-sky-400' },
  metaphor_category: { bg: 'bg-fuchsia-500/10', text: 'text-fuchsia-400', border: 'border-fuchsia-500/20', dot: 'bg-fuchsia-400' },
};
const DEFAULT_COLOR = { bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500/20', dot: 'bg-gray-400' };

const LAYER_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: 'L1 核心', color: 'text-blue-400' },
  2: { label: 'L2 进阶', color: 'text-purple-400' },
  3: { label: 'L3 扩展', color: 'text-gray-400' },
};

export default function PromptManagementTab() {
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
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [showNewTag, setShowNewTag] = useState<string | null>(null);
  const [newTagForm, setNewTagForm] = useState({ value: '', display_name: '', description: '' });
  const [confirmDeleteTemplate, setConfirmDeleteTemplate] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [filterLayer, setFilterLayer] = useState<number | null>(null);

  // 标注提示词配置（来自 prompt_config.json）
  const [promptConfig, setPromptConfig] = useState<any>(null);
  const [promptConfigDraft, setPromptConfigDraft] = useState<string>('');
  const [savingPromptConfig, setSavingPromptConfig] = useState(false);
  const [loadingPromptConfig, setLoadingPromptConfig] = useState(false);

  useEffect(() => { loadPromptTemplates(); loadTagCategories(); }, []);

  // Toast 自动消失
  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 2500); return () => clearTimeout(t); }
  }, [toast]);

  const showToast = (message: string, type: 'success' | 'error') => setToast({ message, type });

  // 加载 prompt_config.json
  const loadPromptConfigFile = async () => {
    setLoadingPromptConfig(true);
    try {
      const res = await fetch(`${API_BASE}/api/config/prompt`);
      if (res.ok) {
        const data = await res.json();
        setPromptConfig(data);
        setPromptConfigDraft(JSON.stringify(data, null, 2));
      }
    } catch (e) { console.error('加载提示词配置失败:', e); }
    setLoadingPromptConfig(false);
  };

  // 切换到标注提示词时加载
  useEffect(() => { if (promptTab === 'annotation') loadPromptConfigFile(); }, [promptTab]);

  // 保存 prompt_config.json
  const handleSavePromptConfig = async () => {
    setSavingPromptConfig(true);
    try {
      const parsed = JSON.parse(promptConfigDraft);
      const res = await fetch(`${API_BASE}/api/config/prompt`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      if (res.ok) {
        setPromptConfig(parsed);
        showToast('提示词配置保存成功', 'success');
      } else {
        showToast('保存失败: ' + (await res.text()), 'error');
      }
    } catch (e: any) {
      showToast('JSON 格式错误: ' + e.message, 'error');
    }
    setSavingPromptConfig(false);
  };

  // 重置 prompt_config.json
  const handleResetPromptConfig = () => {
    if (promptConfig) {
      setPromptConfigDraft(JSON.stringify(promptConfig, null, 2));
      showToast('已还原为上次保存的配置', 'success');
    }
  };

  const retrievalTemplates = promptTemplates.filter(t => t.template_type === 'retrieval' || t.template_type === 'chat');

  // 按层级分组标签分类
  const categoriesByLayer = useMemo(() => {
    const groups: Record<number, typeof tagCategories> = {};
    const filtered = filterLayer ? tagCategories.filter(c => c.layer === filterLayer) : tagCategories;
    filtered.forEach(cat => {
      const layer = cat.layer || 1;
      if (!groups[layer]) groups[layer] = [];
      groups[layer].push(cat);
    });
    return groups;
  }, [tagCategories, filterLayer]);

  const toggleCategory = (catId: string) => {
    setExpandedCategories(prev => {
      const s = new Set(prev);
      if (s.has(catId)) s.delete(catId);
      else { s.add(catId); if (!tagDefinitions[catId]) loadTagDefinitions(catId); }
      return s;
    });
  };

  const handleSaveTemplate = async () => {
    if (!editingTemplate) return;
    try {
      if (isNewTemplate) await createPromptTemplate(editingTemplate as any);
      else await updatePromptTemplate(editingTemplate.id!, editingTemplate as any);
      setShowTemplateEditor(false); setEditingTemplate(null);
      await loadPromptTemplates();
    } catch (e: any) { alert('保存失败: ' + (e.message || '')); }
  };

  const handleDeleteTemplate = async (id: string) => {
    try { await deletePromptTemplate(id); setConfirmDeleteTemplate(null); await loadPromptTemplates(); }
    catch (e: any) { alert('删除失败: ' + (e.message || '')); }
  };

  const handleAddTag = async (categoryId: string) => {
    if (!newTagForm.value || !newTagForm.display_name) return;
    try {
      await createTagDefinition({ category_id: categoryId, ...newTagForm });
      setNewTagForm({ value: '', display_name: '', description: '' });
      setShowNewTag(null);
      await loadTagDefinitions(categoryId);
      await loadTagCategories();
      showToast('标签添加成功', 'success');
    } catch (e: any) { showToast('添加失败: ' + (e.message || ''), 'error'); }
  };

  // ==================== 语义标签分类卡片 ====================
  const renderCategoryCard = (cat: any) => {
    const expanded = expandedCategories.has(cat.id);
    const colors = CATEGORY_COLORS[cat.id] || DEFAULT_COLOR;
    const tags = tagDefinitions[cat.id] || [];
    const activeTags = tags.filter((t: any) => t.is_active);

    return (
      <div key={cat.id} className={`rounded-xl border transition-all overflow-hidden ${expanded ? `${colors.border} shadow-lg` : 'border-white/5 hover:border-white/10'}`}>
        {/* 分类头部 */}
        <div className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-white/[0.02] transition"
          onClick={() => toggleCategory(cat.id)}>
          <div className={`w-8 h-8 rounded-lg ${colors.bg} flex items-center justify-center flex-shrink-0`}>
            <Tag size={14} className={colors.text} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm text-white">{cat.name}</span>
              {cat.is_required && <span className="text-[9px] px-1.5 py-0.5 bg-red-500/15 text-red-400 rounded-md font-medium">必填</span>}
              {!!cat.is_multi_select && <span className="text-[9px] px-1.5 py-0.5 bg-blue-500/15 text-blue-400 rounded-md">多选</span>}
            </div>
            {cat.description && <p className="text-[11px] text-gray-600 mt-0.5 truncate">{cat.description}</p>}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`text-[10px] px-2 py-0.5 rounded-md ${colors.bg} ${colors.text} font-medium`}>
              {activeTags.length > 0 ? `${activeTags.length}/${cat.tag_count || tags.length}` : (cat.tag_count ?? 0)}
            </span>
            {expanded ? <ChevronDown size={14} className="text-gray-500" /> : <ChevronRight size={14} className="text-gray-500" />}
          </div>
        </div>

        {/* 标签列表 */}
        {expanded && (
          <div className="px-4 pb-4 border-t border-white/5 pt-3 space-y-3">
            {/* 标签网格 */}
            <div className="flex flex-wrap gap-2">
              {tags.map((tag: any) => (
                <div key={tag.id} className={`group relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-all cursor-default ${
                  tag.is_active
                    ? `${colors.bg} ${colors.text} border ${colors.border}`
                    : 'bg-white/[0.03] text-gray-600 border border-white/5 line-through'
                }`}>
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${tag.is_active ? colors.dot : 'bg-gray-600'}`} />
                  <span title={tag.description || tag.value} className="font-medium">{tag.display_name}</span>
                  {tag.is_builtin && <span className="text-[8px] opacity-50">内置</span>}

                  {/* 悬停操作 */}
                  <div className="hidden group-hover:flex items-center gap-0.5 ml-1">
                    <button onClick={async (e) => { e.stopPropagation(); await updateTagDefinition(tag.id, { is_active: !tag.is_active }); loadTagDefinitions(cat.id); }}
                      className={`p-0.5 rounded transition ${tag.is_active ? 'hover:bg-red-500/20 hover:text-red-400' : 'hover:bg-green-500/20 hover:text-green-400'}`}
                      title={tag.is_active ? '禁用' : '启用'}>
                      {tag.is_active ? <EyeOff size={10} /> : <Eye size={10} />}
                    </button>
                    {!tag.is_builtin && (
                      <button onClick={async (e) => { e.stopPropagation(); await deleteTagDefinition(tag.id); loadTagDefinitions(cat.id); loadTagCategories(); }}
                        className="p-0.5 rounded hover:bg-red-500/20 hover:text-red-400 transition" title="删除">
                        <Trash2 size={10} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {tags.length === 0 && <span className="text-xs text-gray-600 italic">加载中...</span>}
            </div>

            {/* 添加新标签 */}
            {showNewTag === cat.id ? (
              <div className="flex gap-2 items-end p-3 bg-white/[0.02] rounded-lg border border-white/5">
                <div className="flex-1">
                  <label className="text-[10px] text-gray-500 mb-1 block font-medium">标签值 (英文)</label>
                  <input className="w-full bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500/50 transition"
                    value={newTagForm.value} onChange={e => setNewTagForm({ ...newTagForm, value: e.target.value })} placeholder="english_key" />
                </div>
                <div className="flex-1">
                  <label className="text-[10px] text-gray-500 mb-1 block font-medium">显示名称</label>
                  <input className="w-full bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500/50 transition"
                    value={newTagForm.display_name} onChange={e => setNewTagForm({ ...newTagForm, display_name: e.target.value })} placeholder="中文名" />
                </div>
                <div className="flex-1">
                  <label className="text-[10px] text-gray-500 mb-1 block font-medium">描述 (可选)</label>
                  <input className="w-full bg-white/5 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs outline-none focus:border-blue-500/50 transition"
                    value={newTagForm.description} onChange={e => setNewTagForm({ ...newTagForm, description: e.target.value })} placeholder="简要描述" />
                </div>
                <button onClick={() => handleAddTag(cat.id)} disabled={!newTagForm.value || !newTagForm.display_name}
                  className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition disabled:opacity-40 font-medium whitespace-nowrap">
                  <Check size={11} className="inline mr-1" />添加
                </button>
                <button onClick={() => { setShowNewTag(null); setNewTagForm({ value: '', display_name: '', description: '' }); }}
                  className="px-2.5 py-1.5 text-xs bg-white/5 text-gray-400 rounded-lg hover:bg-white/10 transition">
                  <X size={11} />
                </button>
              </div>
            ) : (
              <button onClick={() => setShowNewTag(cat.id)} className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-400 transition px-1 py-1">
                <Plus size={12} /> 添加标签
              </button>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderTemplateList = (templates: PromptTemplate[]) => (
    <div className="space-y-2">
      {templates.map(t => (
        <div key={t.id} className="px-3 py-2.5 rounded-lg border border-white/10 bg-white/[0.02] hover:border-white/20 transition">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
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
            <div className="flex items-center gap-1.5">
              <button onClick={() => { setEditingTemplate({ ...t }); setIsNewTemplate(false); setShowTemplateEditor(true); }}
                className="px-1.5 py-1 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition"><Pencil size={11} /></button>
              {confirmDeleteTemplate === t.id ? (
                <div className="flex items-center gap-1">
                  <button onClick={() => handleDeleteTemplate(t.id)} className="px-2 py-1 text-xs rounded-lg bg-red-600 hover:bg-red-500 text-white transition">确认</button>
                  <button onClick={() => setConfirmDeleteTemplate(null)} className="px-2 py-1 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 transition">取消</button>
                </div>
              ) : (
                <button onClick={() => setConfirmDeleteTemplate(t.id)} className="px-1.5 py-1 text-xs rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition"><Trash2 size={11} /></button>
              )}
            </div>
          </div>
          {t.description && <p className="text-xs text-gray-500 mb-1.5">{t.description}</p>}
          <pre className="text-xs text-gray-400 bg-black/30 rounded-lg p-2 overflow-x-auto max-h-20 overflow-y-auto whitespace-pre-wrap">
            {t.prompt_text?.substring(0, 300)}{(t.prompt_text?.length || 0) > 300 ? '...' : ''}
          </pre>
          {t.variables && (
            <div className="mt-1.5 flex items-center gap-1 text-[10px] text-gray-600">
              <span>变量:</span>
              {t.variables.split(',').map(v => <span key={v.trim()} className="px-1.5 py-0.5 bg-white/5 rounded">{`{{${v.trim()}}}`}</span>)}
            </div>
          )}
        </div>
      ))}
      {templates.length === 0 && <div className="text-center py-6 text-gray-500 text-sm">暂无模板，点击右上角添加</div>}
    </div>
  );

  // 统计信息
  const totalTags = tagCategories.reduce((sum, c) => sum + (c.tag_count || 0), 0);
  const l1Count = tagCategories.filter(c => c.layer === 1).length;
  const l2Count = tagCategories.filter(c => c.layer === 2).length;
  const l3Count = tagCategories.filter(c => (c.layer || 0) >= 3).length;

  return (
    <>
      {/* Toast */}
      {toast && (
        <div className={`fixed top-6 right-6 z-[100] flex items-center gap-2 px-4 py-2.5 rounded-xl shadow-2xl border backdrop-blur-md transition-all duration-300 ${
          toast.type === 'success' ? 'bg-green-500/15 border-green-500/30 text-green-400' : 'bg-red-500/15 border-red-500/30 text-red-400'
        }`}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* 标题 */}
      <div>
        <h2 className="text-lg font-bold flex items-center gap-2">
          <BookOpen size={22} className="text-blue-400" /> 提示词管理
        </h2>
        <p className="text-xs text-gray-500 mt-0.5">管理语义标签、标注提示词和检索对话模板</p>
      </div>

      {/* Tab切换 */}
      <div className="flex gap-1 p-0.5 bg-white/5 rounded-lg w-fit">
        <button onClick={() => setPromptTab('tags')} className={`px-4 py-1.5 text-xs rounded-md transition-all ${promptTab === 'tags' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}> 语义标签</button>
        <button onClick={() => setPromptTab('annotation')} className={`px-4 py-1.5 text-xs rounded-md transition-all ${promptTab === 'annotation' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}> 标注提示词</button>
        <button onClick={() => setPromptTab('retrieval')} className={`px-4 py-1.5 text-xs rounded-md transition-all ${promptTab === 'retrieval' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}> 检索对话</button>
      </div>

      {/* ===== 语义标签管理 ===== */}
      {promptTab === 'tags' && (
        <div className="space-y-4">
          {/* 统计栏 + 筛选 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-4 text-xs">
                <span className="text-gray-500">{tagCategories.length} 个分类  {totalTags} 个标签</span>
                <div className="flex items-center gap-1">
                  <button onClick={() => setFilterLayer(null)} className={`px-2 py-0.5 rounded-md transition text-[11px] ${filterLayer === null ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'}`}>全部</button>
                  <button onClick={() => setFilterLayer(1)} className={`px-2 py-0.5 rounded-md transition text-[11px] ${filterLayer === 1 ? 'bg-blue-500/20 text-blue-400' : 'text-gray-500 hover:text-gray-300'}`}>L1 核心 ({l1Count})</button>
                  <button onClick={() => setFilterLayer(2)} className={`px-2 py-0.5 rounded-md transition text-[11px] ${filterLayer === 2 ? 'bg-purple-500/20 text-purple-400' : 'text-gray-500 hover:text-gray-300'}`}>L2 进阶 ({l2Count})</button>
                  {l3Count > 0 && <button onClick={() => setFilterLayer(3)} className={`px-2 py-0.5 rounded-md transition text-[11px] ${filterLayer === 3 ? 'bg-gray-500/20 text-gray-300' : 'text-gray-500 hover:text-gray-300'}`}>L3 ({l3Count})</button>}
                </div>
              </div>
            </div>
            <button onClick={() => loadTagCategories()} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 transition">
              <RefreshCw size={11} /> 刷新
            </button>
          </div>

          {/* 按层级渲染 */}
          {Object.entries(categoriesByLayer).sort(([a], [b]) => Number(a) - Number(b)).map(([layer, cats]) => {
            const layerInfo = LAYER_LABELS[Number(layer)] || { label: `L${layer}`, color: 'text-gray-400' };
            return (
              <div key={layer} className="space-y-2">
                <div className="flex items-center gap-2 px-1">
                  <Layers size={12} className={layerInfo.color} />
                  <span className={`text-[11px] font-medium uppercase tracking-wider ${layerInfo.color}`}>{layerInfo.label}</span>
                  <div className="flex-1 border-t border-white/5" />
                  <span className="text-[10px] text-gray-600">{cats.length} 类</span>
                </div>
                <div className="space-y-1.5">
                  {cats.map(renderCategoryCard)}
                </div>
              </div>
            );
          })}

          {tagCategories.length === 0 && (
            <div className="text-center py-16 text-gray-600">
              <Tag size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">暂无标签分类</p>
              <p className="text-xs mt-1 text-gray-700">请初始化数据库以加载默认标签</p>
            </div>
          )}
        </div>
      )}

      {/* ===== 标注提示词 (prompt_config.json) ===== */}
      {promptTab === 'annotation' && (
        <div className="space-y-4">
          {/* 说明 */}
          <div className="flex items-start gap-3 px-4 py-3 bg-amber-500/5 border border-amber-500/10 rounded-xl">
            <AlertCircle size={16} className="text-amber-400 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-gray-400 space-y-1">
              <p className="text-amber-300 font-medium">标注提示词配置说明</p>
              <p>此处直接编辑 <code className="px-1.5 py-0.5 bg-white/5 rounded text-amber-300">config/prompt_config.json</code> 文件。</p>
              <p>标注引擎会从此文件读取 system_prompt 和 user_prompt_template，修改后立即生效。</p>
              <p>可用变量: <code className="text-blue-400">{'{current_line}'}</code>, <code className="text-blue-400">{'{context_lines}'}</code>, <code className="text-blue-400">{'{sentence_types}'}</code>, <code className="text-blue-400">{'{emotions}'}</code>, <code className="text-blue-400">{'{tones}'}</code>, <code className="text-blue-400">{'{character_types}'}</code>, <code className="text-blue-400">{'{primary_functions}'}</code>, <code className="text-blue-400">{'{style_effects}'}</code>, <code className="text-blue-400">{'{output_format}'}</code></p>
            </div>
          </div>

          <SettingsSection
            title="prompt_config.json"
            icon={<FileJson size={16} />}
            description="语义标注引擎实际使用的提示词配置"
            action={
              <div className="flex items-center gap-2">
                <button onClick={handleResetPromptConfig}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 transition">
                  <RotateCcw size={11} /> 还原
                </button>
                <button onClick={handleSavePromptConfig} disabled={savingPromptConfig}
                  className="flex items-center gap-1.5 px-3 py-1 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition disabled:opacity-50 font-medium">
                  {savingPromptConfig ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />} 保存
                </button>
              </div>
            }
          >
            {loadingPromptConfig ? (
              <div className="flex items-center justify-center py-10"><Loader2 size={20} className="animate-spin text-gray-500" /></div>
            ) : (
              <textarea
                className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-3 text-xs outline-none resize-none font-mono leading-relaxed focus:border-blue-500/50 transition custom-scrollbar"
                style={{ minHeight: '420px' }}
                value={promptConfigDraft}
                onChange={e => setPromptConfigDraft(e.target.value)}
                spellCheck={false}
              />
            )}
          </SettingsSection>
        </div>
      )}

      {/* ===== 检索对话提示词 ===== */}
      {promptTab === 'retrieval' && (
        <SettingsSection title="检索对话模板" icon={<MessageSquare size={16} />} description="与LLM对话检索时使用的模板"
          action={
            <button onClick={() => { setEditingTemplate({ template_type: 'retrieval', name: '', prompt_text: '', version: '1.0.0', description: '' }); setIsNewTemplate(true); setShowTemplateEditor(true); }}
              className="flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition"><Plus size={11} /> 新建</button>
          }>
          {renderTemplateList(retrievalTemplates)}
        </SettingsSection>
      )}

      {/* 模板编辑弹窗 */}
      {showTemplateEditor && editingTemplate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowTemplateEditor(false)}>
          <div className="bg-[#1a1a1a] rounded-2xl border border-white/10 shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="px-5 py-3 border-b border-white/5">
              <h3 className="font-bold">{isNewTemplate ? '新建提示词模板' : '编辑提示词模板'}</h3>
            </div>
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">模板名称 *</label>
                  <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50"
                    value={editingTemplate.name || ''} onChange={e => setEditingTemplate({ ...editingTemplate, name: e.target.value })} placeholder="输入模板名称" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">模板类型</label>
                  <select className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none"
                    value={editingTemplate.template_type || 'retrieval'} onChange={e => setEditingTemplate({ ...editingTemplate, template_type: e.target.value as any })}>
                    <option value="retrieval">检索模板</option><option value="chat">对话模板</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">描述</label>
                <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50"
                  value={editingTemplate.description || ''} onChange={e => setEditingTemplate({ ...editingTemplate, description: e.target.value })} placeholder="简要描述模板用途" />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">提示词内容 *</label>
                <textarea className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none resize-none h-40 focus:border-blue-500/50 font-mono"
                  value={editingTemplate.prompt_text || ''} onChange={e => setEditingTemplate({ ...editingTemplate, prompt_text: e.target.value })}
                  placeholder={'输入提示词内容...\n支持变量: {{query}}, {{results}} 等'} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">变量列表</label>
                  <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50"
                    value={editingTemplate.variables || ''} onChange={e => setEditingTemplate({ ...editingTemplate, variables: e.target.value })} placeholder="query,results" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">版本</label>
                  <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50"
                    value={editingTemplate.version || '1.0.0'} onChange={e => setEditingTemplate({ ...editingTemplate, version: e.target.value })} />
                </div>
              </div>
            </div>
            <div className="px-5 py-3 border-t border-white/5 flex justify-end gap-3">
              <button onClick={() => { setShowTemplateEditor(false); setEditingTemplate(null); }} className="px-4 py-1.5 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition">取消</button>
              <button onClick={handleSaveTemplate} disabled={!editingTemplate.name || !editingTemplate.prompt_text}
                className="px-5 py-1.5 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed transition">保存</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
