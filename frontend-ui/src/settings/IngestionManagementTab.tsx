// frontend-ui/src/settings/IngestionManagementTab.tsx
/**
 * 设置中心 - 入库管理Tab
 * 仅显示标注参数和向量化参数配置（模型选择已在模型管理Tab中）
 */

import { useState, useEffect } from 'react';
import {
  Sliders, Save, Loader2, CheckCircle2, AlertCircle, Zap, Layers,
  ExternalLink, Cpu,
} from 'lucide-react';
import useSettingsStore from '../store/settingsStore';
import { SettingsSection } from './SettingsShared';

export default function IngestionManagementTab() {
  const {
    annotationConfig, vectorizationConfig,
    saveAnnotationConfig, saveVectorizationConfig,
    loadSettingsSections,
    llmProviders, embeddingProviders, activeLLMProvider, activeEmbeddingProvider,
    loadLLMProviders, loadEmbeddingProviders,
  } = useSettingsStore();

  // 获取当前激活的模型信息
  const activeLLM = llmProviders.find(p => p.id === activeLLMProvider);
  const activeEmbedding = embeddingProviders.find(p => p.id === activeEmbeddingProvider);

  useEffect(() => {
    if (llmProviders.length === 0) loadLLMProviders();
    if (embeddingProviders.length === 0) loadEmbeddingProviders();
  }, []);

  const [savingAnnotation, setSavingAnnotation] = useState(false);
  const [savingVector, setSavingVector] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

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

  // Toast 自动消失
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 2500);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const showToast = (message: string, type: 'success' | 'error') => setToast({ message, type });

  const handleSaveAnnotation = async () => {
    setSavingAnnotation(true);
    try {
      await saveAnnotationConfig(annotationDraft);
      await loadSettingsSections();
      showToast('标注参数保存成功', 'success');
    } catch (e: any) {
      showToast('保存失败: ' + (e.message || '未知错误'), 'error');
    }
    setSavingAnnotation(false);
  };

  const handleSaveVector = async () => {
    setSavingVector(true);
    try {
      await saveVectorizationConfig(vectorDraft);
      await loadSettingsSections();
      showToast('向量化参数保存成功', 'success');
    } catch (e: any) {
      showToast('保存失败: ' + (e.message || '未知错误'), 'error');
    }
    setSavingVector(false);
  };

  const inputCls = "w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50 transition";

  return (
    <>
      {/* Toast 通知 */}
      {toast && (
        <div className={`fixed top-6 right-6 z-[100] flex items-center gap-2 px-4 py-2.5 rounded-xl shadow-2xl border backdrop-blur-md transition-all duration-300 ${
          toast.type === 'success'
            ? 'bg-green-500/15 border-green-500/30 text-green-400'
            : 'bg-red-500/15 border-red-500/30 text-red-400'
        }`}>
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* 页面标题 */}
      <div>
        <h2 className="text-lg font-bold flex items-center gap-2">
          <Sliders size={22} className="text-blue-400" /> 入库管理
        </h2>
        <p className="text-xs text-gray-500 mt-0.5">配置语义标注和向量化的运行参数</p>
      </div>

      {/* 当前使用模型 */}
      <div className="grid grid-cols-2 gap-3">
        {/* 语义标注模型 */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500 font-medium">语义标注 / AI助手模型</span>
            <button
              onClick={() => window.dispatchEvent(new CustomEvent('settings:changeTab', { detail: 'models' }))}
              className="flex items-center gap-1 px-2 py-1 text-[10px] rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-blue-400 transition"
              title="前往模型管理"
            >
              <ExternalLink size={10} /> 管理
            </button>
          </div>
          {activeLLM ? (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400 shadow-green-400/50 shadow-lg flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-white truncate">{activeLLM.name}</p>
                <p className="text-[11px] text-gray-500 truncate">{activeLLM.model} · {activeLLM.price_info || '无价格信息'}</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-gray-600">
              <Cpu size={14} />
              <span className="text-xs">未配置，请前往模型管理设置</span>
            </div>
          )}
        </div>

        {/* 向量化模型 */}
        <div className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500 font-medium">向量化模型</span>
            <button
              onClick={() => window.dispatchEvent(new CustomEvent('settings:changeTab', { detail: 'models' }))}
              className="flex items-center gap-1 px-2 py-1 text-[10px] rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-blue-400 transition"
              title="前往模型管理"
            >
              <ExternalLink size={10} /> 管理
            </button>
          </div>
          {activeEmbedding ? (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400 shadow-green-400/50 shadow-lg flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-white truncate">{activeEmbedding.name}</p>
                <p className="text-[11px] text-gray-500 truncate">{activeEmbedding.model} · {activeEmbedding.price_info || '无价格信息'}</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-gray-600">
              <Cpu size={14} />
              <span className="text-xs">未配置，请前往模型管理设置</span>
            </div>
          )}
        </div>
      </div>

      {/* ===== 标注参数 ===== */}
      <SettingsSection
        title="标注参数"
        icon={<Zap size={16} />}
        description="控制语义标注的批处理和重试策略"
        action={
          <button onClick={handleSaveAnnotation} disabled={savingAnnotation}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition disabled:opacity-50 font-medium">
            {savingAnnotation ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} 保存
          </button>
        }
      >
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">批处理大小</label>
            <input type="number" className={inputCls} value={annotationDraft.batch_size}
              onChange={e => setAnnotationDraft({ ...annotationDraft, batch_size: parseInt(e.target.value) || 10 })} />
            <p className="text-[10px] text-gray-600 mt-1">每次发送给LLM的台词数量</p>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">并发请求数</label>
            <input type="number" className={inputCls} value={annotationDraft.concurrent_requests}
              onChange={e => setAnnotationDraft({ ...annotationDraft, concurrent_requests: parseInt(e.target.value) || 1 })} />
            <p className="text-[10px] text-gray-600 mt-1">同时发送的请求数量</p>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">最大重试</label>
            <input type="number" className={inputCls} value={annotationDraft.max_retries}
              onChange={e => setAnnotationDraft({ ...annotationDraft, max_retries: parseInt(e.target.value) || 3 })} />
            <p className="text-[10px] text-gray-600 mt-1">失败后的重试次数</p>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">重试延迟 (ms)</label>
            <input type="number" className={inputCls} value={annotationDraft.retry_delay}
              onChange={e => setAnnotationDraft({ ...annotationDraft, retry_delay: parseInt(e.target.value) || 1000 })} />
            <p className="text-[10px] text-gray-600 mt-1">重试间隔毫秒数</p>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-gray-400 mb-1.5 block">自动保存间隔 (每N条)</label>
            <input type="number" className={inputCls} value={annotationDraft.save_interval}
              onChange={e => setAnnotationDraft({ ...annotationDraft, save_interval: parseInt(e.target.value) || 50 })} />
            <p className="text-[10px] text-gray-600 mt-1">每标注N条自动写入数据库</p>
          </div>
        </div>
      </SettingsSection>

      {/* ===== 向量化参数 ===== */}
      <SettingsSection
        title="向量化参数"
        icon={<Layers size={16} />}
        description="控制Embedding向量化的批处理和重试策略"
        action={
          <button onClick={handleSaveVector} disabled={savingVector}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition disabled:opacity-50 font-medium">
            {savingVector ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} 保存
          </button>
        }
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">批处理大小</label>
            <input type="number" className={inputCls} value={vectorDraft.batch_size}
              onChange={e => setVectorDraft({ ...vectorDraft, batch_size: parseInt(e.target.value) || 50 })} />
            <p className="text-[10px] text-gray-600 mt-1">每次发送给Embedding模型的文本数量</p>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">并发请求数</label>
            <input type="number" className={inputCls} value={vectorDraft.concurrent_requests}
              onChange={e => setVectorDraft({ ...vectorDraft, concurrent_requests: parseInt(e.target.value) || 2 })} />
            <p className="text-[10px] text-gray-600 mt-1">同时发送的请求数量</p>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">最大重试</label>
            <input type="number" className={inputCls} value={vectorDraft.max_retries}
              onChange={e => setVectorDraft({ ...vectorDraft, max_retries: parseInt(e.target.value) || 3 })} />
            <p className="text-[10px] text-gray-600 mt-1">失败后的重试次数</p>
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1.5 block">重试延迟 (ms)</label>
            <input type="number" className={inputCls} value={vectorDraft.retry_delay}
              onChange={e => setVectorDraft({ ...vectorDraft, retry_delay: parseInt(e.target.value) || 500 })} />
            <p className="text-[10px] text-gray-600 mt-1">重试间隔毫秒数</p>
          </div>
        </div>
      </SettingsSection>

    </>
  );
}
