// frontend-ui/src/store/settingsStore.ts
/**
 * 设置状态管理
 * 使用 zustand 管理全局设置状态
 * 
 * v2: 模型提供者从数据库读取，通过 /api/model-providers/* 管理
 */

import { create } from 'zustand';
import type { 
  ModelProvider,
  LLMProvider, 
  EmbeddingProvider, 
  LLMConnectionStatus,
  AnnotationConfig,
  VectorizationConfig,
  PromptConfig,
  AppSettings,
  PathConfig,
  VectorDBConfig,
  IngestionProfile,
  PromptTemplate,
  TagCategory,
  TagDefinition,
  DatabaseStats,
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
  
  // 入库配置
  ingestionProfiles: IngestionProfile[];
  
  // 提示词模板
  promptTemplates: PromptTemplate[];
  
  // 标签体系
  tagCategories: TagCategory[];
  tagDefinitions: Record<string, TagDefinition[]>;
  
  // 数据库统计
  databaseStats: DatabaseStats | null;
  
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
  
  // 模型提供者 CRUD（数据库驱动）
  createProvider: (data: Partial<ModelProvider>) => Promise<ModelProvider | null>;
  updateProvider: (id: string, data: Partial<ModelProvider>) => Promise<boolean>;
  deleteProvider: (id: string) => Promise<boolean>;
  toggleProvider: (id: string, enabled: boolean) => Promise<boolean>;
  resetProviderDefaults: () => Promise<boolean>;
  
  // 保存配置（保留旧接口兼容）
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
  
  // 入库配置
  loadIngestionProfiles: (profileType?: string) => Promise<void>;
  createIngestionProfile: (data: Partial<IngestionProfile>) => Promise<IngestionProfile | null>;
  updateIngestionProfile: (id: string, data: Partial<IngestionProfile>) => Promise<boolean>;
  deleteIngestionProfile: (id: string) => Promise<boolean>;
  setDefaultIngestionProfile: (id: string) => Promise<boolean>;
  
  // 提示词模板
  loadPromptTemplates: (templateType?: string) => Promise<void>;
  createPromptTemplate: (data: Partial<PromptTemplate>) => Promise<PromptTemplate | null>;
  updatePromptTemplate: (id: string, data: Partial<PromptTemplate>) => Promise<boolean>;
  deletePromptTemplate: (id: string) => Promise<boolean>;
  
  // 标签体系
  loadTagCategories: () => Promise<void>;
  loadTagDefinitions: (categoryId: string) => Promise<void>;
  updateTagCategory: (id: string, data: Partial<TagCategory>) => Promise<boolean>;
  createTagDefinition: (data: any) => Promise<boolean>;
  updateTagDefinition: (id: string, data: Partial<TagDefinition>) => Promise<boolean>;
  deleteTagDefinition: (id: string) => Promise<boolean>;
  
  // 数据库统计
  loadDatabaseStats: () => Promise<void>;
}

const defaultAnnotationConfig: AnnotationConfig = {
  batch_size: 10,
  max_retries: 3,
  retry_delay: 1000,
  save_interval: 50,
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
  
  // 入库配置
  ingestionProfiles: [],
  
  // 提示词模板
  promptTemplates: [],
  
  // 标签体系
  tagCategories: [],
  tagDefinitions: {},
  
  // 数据库统计
  databaseStats: null,
  
  // ==================== 标注状态 ====================
  
  setAnnotationRunning: (running: boolean) => {
    set({ annotationRunning: running });
  },
  
  // ==================== 加载配置 ====================
  
  loadLLMProviders: async () => {
    try {
      // 从数据库驱动的 API 加载
      const res = await fetch(`${API_BASE}/api/model-providers/llm`);
      if (res.ok) {
        const data = await res.json();
        const providers: LLMProvider[] = data.providers || [];
        const activeProvider = data.active_provider || providers.find(p => p.is_active)?.id || providers[0]?.id || '';
        
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
      // 从数据库驱动的 API 加载
      const res = await fetch(`${API_BASE}/api/model-providers/embedding`);
      if (res.ok) {
        const data = await res.json();
        const providers: EmbeddingProvider[] = data.providers || [];
        const activeProvider = data.active_provider || providers.find(p => p.is_active)?.id || providers[0]?.id || '';
        
        set({ 
          embeddingProviders: providers, 
          activeEmbeddingProvider: activeProvider 
        });
      }
    } catch (e) {
      console.error('加载 Embedding 提供者失败:', e);
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
    
    // 通过数据库 API 持久化
    try {
      const res = await fetch(`${API_BASE}/api/model-providers/active/set`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: providerId, category: 'llm' }),
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
      const res = await fetch(`${API_BASE}/api/model-providers/test-connection`, {
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
            error: data.error || data.detail || '连接失败' 
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
    
    // 通过数据库 API 持久化
    try {
      const res = await fetch(`${API_BASE}/api/model-providers/active/set`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: providerId, category: 'embedding' }),
      });
      if (res.ok) {
        console.log(`✅ Embedding 提供者已保存: ${providerId}`);
      }
    } catch (e) {
      console.error('保存 Embedding 提供者失败:', e);
    }
  },
  
  // ==================== 模型提供者 CRUD（数据库驱动） ====================
  
  createProvider: async (data: Partial<ModelProvider>): Promise<ModelProvider | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/model-providers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const result = await res.json();
        // 刷新对应列表
        if (data.category === 'llm') await get().loadLLMProviders();
        else if (data.category === 'embedding') await get().loadEmbeddingProviders();
        return result.provider || result;
      } else {
        const err = await res.json();
        set({ error: err.detail || '创建失败' });
      }
    } catch (e: any) {
      set({ error: e.message || '创建模型失败' });
    }
    return null;
  },
  
  updateProvider: async (id: string, data: Partial<ModelProvider>): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/model-providers/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        // 刷新列表
        await Promise.all([get().loadLLMProviders(), get().loadEmbeddingProviders()]);
        return true;
      } else {
        const err = await res.json();
        set({ error: err.detail || '更新失败' });
      }
    } catch (e: any) {
      set({ error: e.message || '更新模型失败' });
    }
    return false;
  },
  
  deleteProvider: async (id: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/model-providers/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await Promise.all([get().loadLLMProviders(), get().loadEmbeddingProviders()]);
        return true;
      } else {
        const err = await res.json();
        set({ error: err.detail || '删除失败' });
      }
    } catch (e: any) {
      set({ error: e.message || '删除模型失败' });
    }
    return false;
  },
  
  toggleProvider: async (id: string, enabled: boolean): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/model-providers/${encodeURIComponent(id)}/toggle`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (res.ok) {
        await Promise.all([get().loadLLMProviders(), get().loadEmbeddingProviders()]);
        return true;
      }
    } catch (e: any) {
      set({ error: e.message || '切换状态失败' });
    }
    return false;
  },
  
  resetProviderDefaults: async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/model-providers/reset-defaults`, {
        method: 'POST',
      });
      if (res.ok) {
        await Promise.all([get().loadLLMProviders(), get().loadEmbeddingProviders()]);
        return true;
      }
    } catch (e: any) {
      set({ error: e.message || '重置失败' });
    }
    return false;
  },
  
  // ==================== 保存配置（兼容旧接口） ====================
  
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
  
  // ==================== 入库配置 ====================
  
  loadIngestionProfiles: async (profileType?: string) => {
    try {
      const url = profileType
        ? `${API_BASE}/api/ingestion-profiles?profile_type=${profileType}`
        : `${API_BASE}/api/ingestion-profiles`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        set({ ingestionProfiles: data.profiles || [] });
      }
    } catch (e) {
      console.error('加载入库配置失败:', e);
    }
  },
  
  createIngestionProfile: async (data: Partial<IngestionProfile>): Promise<IngestionProfile | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/ingestion-profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const result = await res.json();
        await get().loadIngestionProfiles();
        return result.profile;
      }
    } catch (e: any) {
      set({ error: e.message || '创建入库配置失败' });
    }
    return null;
  },
  
  updateIngestionProfile: async (id: string, data: Partial<IngestionProfile>): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/ingestion-profiles/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        await get().loadIngestionProfiles();
        return true;
      }
    } catch (e: any) {
      set({ error: e.message || '更新入库配置失败' });
    }
    return false;
  },
  
  deleteIngestionProfile: async (id: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/ingestion-profiles/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await get().loadIngestionProfiles();
        return true;
      }
    } catch (e: any) {
      set({ error: e.message || '删除入库配置失败' });
    }
    return false;
  },
  
  setDefaultIngestionProfile: async (id: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/ingestion-profiles/${encodeURIComponent(id)}/set-default`, {
        method: 'PUT',
      });
      if (res.ok) {
        await get().loadIngestionProfiles();
        return true;
      }
    } catch (e: any) {
      set({ error: e.message || '设置默认配置失败' });
    }
    return false;
  },
  
  // ==================== 提示词模板 ====================
  
  loadPromptTemplates: async (templateType?: string) => {
    try {
      const url = templateType
        ? `${API_BASE}/api/prompt-templates?template_type=${templateType}`
        : `${API_BASE}/api/prompt-templates`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        set({ promptTemplates: data.templates || [] });
      }
    } catch (e) {
      console.error('加载提示词模板失败:', e);
    }
  },
  
  createPromptTemplate: async (data: Partial<PromptTemplate>): Promise<PromptTemplate | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        const result = await res.json();
        await get().loadPromptTemplates();
        return result.template;
      }
    } catch (e: any) {
      set({ error: e.message || '创建提示词模板失败' });
    }
    return null;
  },
  
  updatePromptTemplate: async (id: string, data: Partial<PromptTemplate>): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        await get().loadPromptTemplates();
        return true;
      }
    } catch (e: any) {
      set({ error: e.message || '更新提示词模板失败' });
    }
    return false;
  },
  
  deletePromptTemplate: async (id: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        await get().loadPromptTemplates();
        return true;
      }
    } catch (e: any) {
      set({ error: e.message || '删除提示词模板失败' });
    }
    return false;
  },
  
  // ==================== 标签体系 ====================
  
  loadTagCategories: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/tags/categories`);
      if (res.ok) {
        const data = await res.json();
        set({ tagCategories: data.categories || [] });
      }
    } catch (e) {
      console.error('加载标签分类失败:', e);
    }
  },
  
  loadTagDefinitions: async (categoryId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/tags/categories/${encodeURIComponent(categoryId)}/definitions`);
      if (res.ok) {
        const data = await res.json();
        set(state => ({
          tagDefinitions: { ...state.tagDefinitions, [categoryId]: data.tags || [] }
        }));
      }
    } catch (e) {
      console.error('加载标签定义失败:', e);
    }
  },
  
  updateTagCategory: async (id: string, data: Partial<TagCategory>): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/tags/categories/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        await get().loadTagCategories();
        return true;
      }
    } catch (e: any) {
      set({ error: e.message });
    }
    return false;
  },
  
  createTagDefinition: async (data: any): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/tags/definitions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        if (data.category_id) await get().loadTagDefinitions(data.category_id);
        await get().loadTagCategories();
        return true;
      }
    } catch (e: any) {
      set({ error: e.message });
    }
    return false;
  },
  
  updateTagDefinition: async (id: string, data: Partial<TagDefinition>): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/tags/definitions/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) return true;
    } catch (e: any) {
      set({ error: e.message });
    }
    return false;
  },
  
  deleteTagDefinition: async (id: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/tags/definitions/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      });
      if (res.ok) return true;
    } catch (e: any) {
      set({ error: e.message });
    }
    return false;
  },
  
  // ==================== 数据库统计 ====================
  
  loadDatabaseStats: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/prompt-templates/stats/database`);
      if (res.ok) {
        const data = await res.json();
        set({ databaseStats: data });
      }
    } catch (e) {
      console.error('加载数据库统计失败:', e);
    }
  },
}));

export default useSettingsStore;
