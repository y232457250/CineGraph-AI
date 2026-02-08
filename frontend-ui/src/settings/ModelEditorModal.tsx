// frontend-ui/src/settings/ModelEditorModal.tsx
/**
 * 模型编辑弹窗 - 被模型管理和入库管理共用
 */

import { Loader2 } from 'lucide-react';
import type { ModelProvider } from '../types/settings';

export default function ModelEditorModal({
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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-[#1a1a1a] rounded-2xl border border-white/10 shadow-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="px-5 py-3 border-b border-white/5">
          <h3 className="text-base font-bold">{isNew ? '添加模型' : '编辑模型'}</h3>
          <p className="text-xs text-gray-500">{isNew ? '配置新的模型提供者' : `编辑: ${provider.name}`}</p>
        </div>

        <div className="p-4 space-y-3">
          {/* 名称 */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">显示名称 *</label>
            <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50" value={provider.name || ''} onChange={e => onChange({ ...provider, name: e.target.value })} placeholder="例: 我的Ollama模型" />
          </div>

          {/* 提供者类型 + 本地模式 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">提供者类型</label>
              <select className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none" value={provider.provider_type || 'local'}
                onChange={e => {
                  const t = e.target.value as 'local' | 'commercial';
                  onChange({ ...provider, provider_type: t, local_mode: t === 'local' ? 'ollama' : '', base_url: t === 'local' ? (provider.category === 'llm' ? 'http://localhost:11434/v1' : 'http://localhost:11434') : provider.base_url || '' });
                }}>
                <option value="local">本地部署</option>
                <option value="commercial">商用API</option>
              </select>
            </div>
            {provider.provider_type === 'local' && (
              <div>
                <label className="text-xs text-gray-400 mb-1 block">本地模式</label>
                <select className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none" value={provider.local_mode || 'ollama'} onChange={e => onChange({ ...provider, local_mode: e.target.value })}>
                  <option value="ollama">Ollama</option>
                  <option value="docker">Docker</option>
                </select>
              </div>
            )}
          </div>

          {/* API 地址 + 模型名称 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">API 地址 *</label>
              <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50" value={provider.base_url || ''} onChange={e => onChange({ ...provider, base_url: e.target.value })} placeholder="http://localhost:11434/v1" />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">模型名称 *</label>
              <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50" value={provider.model || ''} onChange={e => onChange({ ...provider, model: e.target.value })} placeholder="qwen3:4b" />
            </div>
          </div>

          {/* API Key */}
          <div>
            <label className="text-xs text-gray-400 mb-1 block">API Key</label>
            <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50" value={provider.api_key || ''} onChange={e => onChange({ ...provider, api_key: e.target.value })} placeholder="留空或引用环境变量" />
          </div>

          {/* Embedding 专用参数 */}
          {provider.category === 'embedding' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">API风格</label>
                <select className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none" value={provider.api_style || 'openai'} onChange={e => onChange({ ...provider, api_style: e.target.value })}>
                  <option value="openai">OpenAI</option>
                  <option value="ollama">Ollama</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">向量维度</label>
                <input type="number" className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none" value={provider.dimension || 0} onChange={e => onChange({ ...provider, dimension: parseInt(e.target.value) || 0 })} placeholder="0=自动" />
              </div>
            </div>
          )}

          {/* LLM 专用参数 */}
          {provider.category === 'llm' && (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">最大Token</label>
                <input type="number" className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none" value={provider.max_tokens || 2000} onChange={e => onChange({ ...provider, max_tokens: parseInt(e.target.value) || 2000 })} />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">温度</label>
                <input type="number" step="0.1" className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none" value={provider.temperature ?? 0.7} onChange={e => onChange({ ...provider, temperature: parseFloat(e.target.value) || 0.7 })} />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">超时(秒)</label>
                <input type="number" className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none" value={provider.timeout || 60} onChange={e => onChange({ ...provider, timeout: parseInt(e.target.value) || 60 })} />
              </div>
            </div>
          )}

          {/* 描述 + 价格 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 mb-1 block">描述</label>
              <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50" value={provider.description || ''} onChange={e => onChange({ ...provider, description: e.target.value })} placeholder="模型简介..." />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">价格信息</label>
              <input className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm outline-none focus:border-blue-500/50" value={provider.price_info || ''} onChange={e => onChange({ ...provider, price_info: e.target.value })} placeholder="免费 / ¥1/百万token" />
            </div>
          </div>
        </div>

        {/* 底部操作 */}
        <div className="px-4 py-3 border-t border-white/5 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-1.5 text-sm rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 transition">取消</button>
          <button onClick={onSave} disabled={loading || !provider.name || !provider.model || !provider.base_url}
            className="px-5 py-1.5 text-sm rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center gap-2">
            {loading && <Loader2 size={14} className="animate-spin" />}
            {isNew ? '添加' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
