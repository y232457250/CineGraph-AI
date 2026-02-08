// frontend-ui/src/settings/SettingsShared.tsx
/**
 * 设置中心 - 共享UI组件
 */

import { ChevronRight } from 'lucide-react';
import type { ModelProvider } from '../types/settings';

// ==================== 设置Tab类型 ====================
export type SettingsTab = 'models' | 'ingestion' | 'database' | 'prompts';

// ==================== SettingsSection 区块容器 ====================
export function SettingsSection({ title, icon, children, description, badge, action }: {
  title: string; icon: React.ReactNode; children: React.ReactNode;
  description?: string; badge?: string; action?: React.ReactNode;
}) {
  return (
    <div className="bg-[#151515] rounded-lg border border-white/5 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-blue-400">{icon}</div>
          <div>
            <h3 className="font-medium text-white text-sm">{title}</h3>
            {description && <p className="text-[11px] text-gray-500 mt-0.5 leading-none">{description}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {badge && <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">{badge}</span>}
          {action}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// ==================== SettingsNavItem 左侧导航项 ====================
export function SettingsNavItem({ icon, label, active, onClick, badge }: {
  icon: React.ReactNode; label: string; active?: boolean; onClick?: () => void; badge?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-all ${
        active ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' : 'text-gray-400 hover:text-white hover:bg-white/5'
      }`}
    >
      <div className="flex items-center gap-2.5">
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

// ==================== 空白模型模板 ====================
export const emptyProvider = (category: 'llm' | 'embedding'): Partial<ModelProvider> => ({
  name: '', category, provider_type: 'local', local_mode: 'ollama',
  base_url: category === 'llm' ? 'http://localhost:11434/v1' : 'http://localhost:11434',
  model: '', api_key: '', api_style: 'openai', max_tokens: 2000, temperature: 0.7,
  timeout: 60, dimension: 0, description: '', price_info: '',
});
