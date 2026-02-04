// frontend-ui/src/store/settingsStore.ts
/**
 * 设置状态管理
 * 使用 zustand 管理全局设置状态
 */

import { create } from 'zustand';
import type { 
  LLMProvider, 
  EmbeddingProvider, 
  LLMConnectionStatus,
  AnnotationConfig,
  VectorizationConfig,
  PromptConfig,
  AppSettings,
  PathConfig,
  VectorDBConfig 
} from '../types/settings';

const API_BASE = 'http://127.0.0.1:8000';

interface SettingsStore {
  // ==================== 状态 ====================
  
  // LLM 配置
  llmProviders: LLMProvider[];
  activeLLMProvider: string;
  llmConnectionStatus: LLMConnectionStatus;
  
  // Embedding 配置
  embeddingProviders: EmbeddingProvider[];
  activeEmbeddingProvider: string;
  
  // 向量数据库
  vectorDB: VectorDBConfig;
  
  // 标注配置
  annotationConfig: AnnotationConfig;
  
  // 向量化配置
  vectorizationConfig: VectorizationConfig;
  
  // 提示词配置
  promptConfig: PromptConfig | null;
  
  // 应用设置
  appSettings: AppSettings;
  
  // 路径配置
  pathConfig: PathConfig;
  
  // 全局标注运行状态（跨组件共享）
  annotationRunning: boolean;
  
  // UI 状态
  isLoading: boolean;
  isSaving: boolean;
  hasChanges: boolean;
  error: string | null;
  
  // 配置文件原始内容（用于编辑器）
  llmConfigRaw: string;
  promptConfigRaw: string;
  
  // ==================== 动作 ====================
  
  // 标注状态
  setAnnotationRunning: (running: boolean) => void;
  
  // 加载配置
  loadLLMProviders: () => Promise<LLMProvider[]>;
  loadEmbeddingProviders: () => Promise<void>;
  loadSettingsSections: () => Promise<void>;
  loadPromptConfig: () => Promise<void>;
  loadLLMConfigRaw: () => Promise<string>;
  loadEmbeddingConfigRaw: () => Promise<string>;
  loadAllSettings: () => Promise<void>;
  
  // LLM 操作
  setActiveLLMProvider: (providerId: string) => Promise<void>;
  testLLMConnection: (providerId: string) => Promise<boolean>;
  updateLLMProvider: (provider: Partial<LLMProvider> & { id: string }) => void;
  
  // Embedding 操作
  setActiveEmbeddingProvider: (providerId: string) => Promise<void>;
  
  // 保存配置
  saveLLMConfig: (content: string) => Promise<boolean>;
  saveEmbeddingConfig: (content: string) => Promise<boolean>;
  savePromptConfig: (content: string) => Promise<boolean>;
  saveAnnotationConfig: (config: Partial<AnnotationConfig>) => Promise<void>;
  saveVectorizationConfig: (config: Partial<VectorizationConfig>) => Promise<void>;
  saveAppSettings: (settings: Partial<AppSettings>) => void;
  
  // UI 状态
  setError: (error: string | null) => void;
  setHasChanges: (hasChanges: boolean) => void;
  resetSettings: () => void;
}

const defaultAnnotationConfig: AnnotationConfig = {
  batch_size: 10,
  max_retries: 3,
  retry_delay: 1000,
  save_interval: 5,
  concurrent_requests: 1,
  _loaded: false,  // 标记是否已从后端加载
};

const defaultVectorizationConfig: VectorizationConfig = {
  batch_size: 50,
  max_retries: 3,
  retry_delay: 500,
  concurrent_requests: 2,
  _loaded: false,
};

const defaultAppSettings: AppSettings = {
  theme: 'dark',
  language: 'zh-CN',
  autoSave: true,
  confirmBeforeDelete: true,
  showTips: true,
};

const defaultPathConfig: PathConfig = {
  media_root: 'D:\\AI\\CineGraph-AI\\data\\media',
  annotations_dir: 'data/annotations',
  vectors_dir: 'data/chroma_db',
  cache_dir: 'data/cache',
  posters_dir: 'data/posters',
};

const defaultVectorDB: VectorDBConfig = {
  type: 'chroma',
  path: 'data/chroma_db',
  collection_name: 'cinegraph_subtitles',
};

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  // 初始状态
  llmProviders: [],
  activeLLMProvider: '',
  llmConnectionStatus: { status: 'idle' },
  
  embeddingProviders: [],
  activeEmbeddingProvider: '',
  
  vectorDB: defaultVectorDB,
  annotationConfig: defaultAnnotationConfig,
  vectorizationConfig: defaultVectorizationConfig,
  promptConfig: null,
  appSettings: defaultAppSettings,
  pathConfig: defaultPathConfig,
  
  // 标注运行状态
  annotationRunning: false,
  
  isLoading: false,
  isSaving: false,
  hasChanges: false,
  error: null,
  
  llmConfigRaw: '',
  promptConfigRaw: '',
  
  // ==================== 标注状态 ====================
  
  setAnnotationRunning: (running: boolean) => {
    set({ annotationRunning: running });
  },
  
  // ==================== 加载配置 ====================
  
  loadLLMProviders: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/annotation/providers`);
      if (res.ok) {
        const data = await res.json();
        const providers: LLMProvider[] = data.providers || [];
        const activeProvider = providers.find(p => p.is_active)?.id || providers[0]?.id || '';
        
        set({ 
          llmProviders: providers, 
          activeLLMProvider: activeProvider 
        });
        
        return providers;
      }
    } catch (e) {
      console.error('加载 LLM 提供者失败:', e);
      set({ error: '加载 LLM 提供者失败' });
    }
    return [];
  },
  
  loadEmbeddingProviders: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/settings/embedding/summary`);
      if (res.ok) {
        const data = await res.json();
        const providers: EmbeddingProvider[] = data.providers || [];
        const activeProvider = providers.find(p => p.is_active)?.id || providers[0]?.id || '';
        
        set({ 
          embeddingProviders: providers, 
          activeEmbeddingProvider: activeProvider 
        });
      }
    } catch (e) {
      console.error('加载 Embedding 提供者失败:', e);
      // Embedding API 可能还未实现，不显示错误
    }
  },
  
  loadSettingsSections: async () => {
    try {
      const [annotationRes, vectorizationRes, vectorDbRes, pathsRes, appRes] = await Promise.all([
        fetch(`${API_BASE}/api/settings/annotation`),
        fetch(`${API_BASE}/api/settings/vectorization`),
        fetch(`${API_BASE}/api/settings/vector_db`),
        fetch(`${API_BASE}/api/settings/paths`),
        fetch(`${API_BASE}/api/settings/app`),
      ]);
      
      if (annotationRes.ok) {
        const annotation = await annotationRes.json();
        set({ annotationConfig: { ...annotation, _loaded: true } });
      }
      if (vectorizationRes.ok) {
        const vectorization = await vectorizationRes.json();
        set({ vectorizationConfig: { ...vectorization, _loaded: true } });
      }
      if (vectorDbRes.ok) {
        const vectorDB = await vectorDbRes.json();
        set({ vectorDB });
      }
      if (pathsRes.ok) {
        const pathConfig = await pathsRes.json();
        set({ pathConfig });
      }
      if (appRes.ok) {
        const appSettings = await appRes.json();
        set({ appSettings });
      }
    } catch (e) {
      console.error('加载设置分区失败:', e);
    }
  },
  
  loadPromptConfig: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config/prompt`);
      if (res.ok) {
        const data = await res.json();
        set({ 
          promptConfig: data,
          promptConfigRaw: JSON.stringify(data, null, 2)
        });
      }
    } catch (e) {
      console.error('加载提示词配置失败:', e);
    }
  },
  
  loadLLMConfigRaw: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config/llm-providers`);
      if (res.ok) {
        const data = await res.json();
        const content = data.content || '';
        set({ llmConfigRaw: content });
        return content;
      }
    } catch (e) {
      console.error('加载 LLM 配置文件失败:', e);
      set({ error: '加载 LLM 配置文件失败' });
    }
    return '';
  },
  
  loadEmbeddingConfigRaw: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config/embedding-providers`);
      if (res.ok) {
        const data = await res.json();
        const content = data.content || '';
        return content;
      }
    } catch (e) {
      console.error('加载 Embedding 配置文件失败:', e);
      set({ error: '加载 Embedding 配置文件失败' });
    }
    return '';
  },
  
  loadAllSettings: async () => {
    set({ isLoading: true, error: null });
    
    try {
      await Promise.all([
        get().loadLLMProviders(),
        get().loadEmbeddingProviders(),
        get().loadSettingsSections(),
        get().loadPromptConfig(),
      ]);
    } catch (e) {
      console.error('加载设置失败:', e);
      set({ error: '加载设置失败' });
    } finally {
      set({ isLoading: false });
    }
  },
  
  // ==================== LLM 操作 ====================
  
  setActiveLLMProvider: async (providerId: string) => {
    set({ activeLLMProvider: providerId, hasChanges: true });
    
    // 自动持久化到配置文件
    try {
      const res = await fetch(`${API_BASE}/api/settings/llm/active?provider_id=${encodeURIComponent(providerId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        console.log(`✅ LLM 提供者已保存: ${providerId}`);
      }
    } catch (e) {
      console.error('保存 LLM 提供者失败:', e);
    }
  },
  
  testLLMConnection: async (providerId: string): Promise<boolean> => {
    if (!providerId) {
      set({ llmConnectionStatus: { status: 'idle' } });
      return false;
    }
    
    set({ llmConnectionStatus: { status: 'testing' } });
    
    try {
      const startTime = Date.now();
      const res = await fetch(`${API_BASE}/api/annotation/test-connection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: providerId })
      });
      
      const latency = Date.now() - startTime;
      const data = await res.json();
      
      if (res.ok && data.success) {
        set({ 
          llmConnectionStatus: { 
            status: 'connected', 
            latency 
          } 
        });
        return true;
      } else {
        set({ 
          llmConnectionStatus: { 
            status: 'failed', 
            error: data.error || '连接失败' 
          } 
        });
        return false;
      }
    } catch (e: any) {
      set({ 
        llmConnectionStatus: { 
          status: 'failed', 
          error: e.message || '网络错误' 
        } 
      });
      return false;
    }
  },
  
  updateLLMProvider: (provider: Partial<LLMProvider> & { id: string }) => {
    const providers = get().llmProviders.map(p => 
      p.id === provider.id ? { ...p, ...provider } : p
    );
    set({ llmProviders: providers, hasChanges: true });
  },
  
  // ==================== Embedding 操作 ====================
  
  setActiveEmbeddingProvider: async (providerId: string) => {
    set({ activeEmbeddingProvider: providerId, hasChanges: true });
    
    // 自动持久化到配置文件
    try {
      const res = await fetch(`${API_BASE}/api/settings/embedding/active?provider_id=${encodeURIComponent(providerId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
      });
      if (res.ok) {
        console.log(`✅ Embedding 提供者已保存: ${providerId}`);
      }
    } catch (e) {
      console.error('保存 Embedding 提供者失败:', e);
    }
  },
  
  // ==================== 保存配置 ====================
  
  saveLLMConfig: async (content: string): Promise<boolean> => {
    set({ isSaving: true, error: null });
    
    try {
      const res = await fetch(`${API_BASE}/api/config/llm-providers`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });
      
      if (res.ok) {
        set({ llmConfigRaw: content, hasChanges: false });
        // 重新加载提供者列表
        await get().loadLLMProviders();
        return true;
      } else {
        const error = await res.json();
        set({ error: error.detail || '保存失败' });
        return false;
      }
    } catch (e: any) {
      set({ error: e.message || '保存失败' });
      return false;
    } finally {
      set({ isSaving: false });
    }
  },
  
  saveEmbeddingConfig: async (content: string): Promise<boolean> => {
    set({ isSaving: true, error: null });
    
    try {
      const res = await fetch(`${API_BASE}/api/config/embedding-providers`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });
      
      if (res.ok) {
        set({ hasChanges: false });
        // 重新加载提供者列表
        await get().loadEmbeddingProviders();
        return true;
      } else {
        const error = await res.json();
        set({ error: error.detail || '保存失败' });
        return false;
      }
    } catch (e: any) {
      set({ error: e.message || '保存失败' });
      return false;
    } finally {
      set({ isSaving: false });
    }
  },
  
  savePromptConfig: async (content: string): Promise<boolean> => {
    set({ isSaving: true, error: null });
    
    try {
      const res = await fetch(`${API_BASE}/api/config/prompt`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });
      
      if (res.ok) {
        set({ promptConfigRaw: content, hasChanges: false });
        // 解析并更新 promptConfig
        try {
          const parsed = JSON.parse(content);
          set({ promptConfig: parsed });
        } catch {}
        return true;
      } else {
        const error = await res.json();
        set({ error: error.detail || '保存失败' });
        return false;
      }
    } catch (e: any) {
      set({ error: e.message || '保存失败' });
      return false;
    } finally {
      set({ isSaving: false });
    }
  },
  
  saveAnnotationConfig: async (config: Partial<AnnotationConfig>) => {
    const nextConfig = { ...get().annotationConfig, ...config };
    set({ annotationConfig: nextConfig, hasChanges: true });
    
    try {
      const res = await fetch(`${API_BASE}/api/settings/annotation`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nextConfig)
      });
      if (res.ok) {
        const data = await res.json().catch(() => null);
        if (data) {
          set({ annotationConfig: { ...data, _loaded: true }, hasChanges: false });
        } else {
          set({ hasChanges: false });
        }
      }
    } catch (e) {
      console.error('保存标注参数失败:', e);
    }
  },
  
  saveVectorizationConfig: async (config: Partial<VectorizationConfig>) => {
    const nextConfig = { ...get().vectorizationConfig, ...config };
    set({ vectorizationConfig: nextConfig, hasChanges: true });
    
    try {
      const res = await fetch(`${API_BASE}/api/settings/vectorization`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nextConfig)
      });
      if (res.ok) {
        const data = await res.json().catch(() => null);
        if (data) {
          set({ vectorizationConfig: { ...data, _loaded: true }, hasChanges: false });
        } else {
          set({ hasChanges: false });
        }
      }
    } catch (e) {
      console.error('保存向量化参数失败:', e);
    }
  },
  
  saveAppSettings: (settings: Partial<AppSettings>) => {
    set({ 
      appSettings: { ...get().appSettings, ...settings },
      hasChanges: true 
    });
  },
  
  // ==================== UI 状态 ====================
  
  setError: (error: string | null) => set({ error }),
  
  setHasChanges: (hasChanges: boolean) => set({ hasChanges }),
  
  resetSettings: () => {
    set({
      annotationConfig: defaultAnnotationConfig,
      appSettings: defaultAppSettings,
      hasChanges: false,
    });
  },
}));

export default useSettingsStore;
