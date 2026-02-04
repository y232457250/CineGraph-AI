// frontend-ui/src/types/settings.ts
/**
 * 设置模块类型定义
 */

// ==================== LLM 模型配置 ====================

export interface LLMProvider {
  id: string;
  name: string;
  type: 'local' | 'commercial';
  local_mode?: 'ollama' | 'docker' | 'native';
  base_url: string;
  model: string;
  api_key?: string;
  max_tokens: number;
  temperature: number;
  timeout: number;
  description: string;
  is_active: boolean;
  price_per_1k_tokens?: number;
}

export interface LLMConnectionStatus {
  status: 'idle' | 'testing' | 'connected' | 'failed';
  error?: string;
  latency?: number;
}

// ==================== Embedding 模型配置 ====================

export interface EmbeddingProvider {
  id: string;
  name: string;
  type: 'local' | 'commercial';
  local_mode?: 'ollama' | 'docker' | 'native';
  base_url: string;
  model: string;
  dimension: number;
  description: string;
  is_active: boolean;
  price_per_1k_tokens?: number;
}

// ==================== 向量数据库配置 ====================

export interface VectorDBConfig {
  type: 'chroma' | 'milvus' | 'faiss';
  path: string;
  collection_name: string;
}

// ==================== 标注配置 ====================

export interface AnnotationConfig {
  batch_size: number;
  max_retries: number;
  retry_delay: number;
  save_interval: number;
  concurrent_requests: number;
  _loaded?: boolean;  // 标记是否已从后端加载
}

// ==================== 向量化配置 ====================

export interface VectorizationConfig {
  batch_size: number;
  max_retries: number;
  retry_delay: number;
  concurrent_requests: number;
  _loaded?: boolean;
}

// ==================== 提示词配置 ====================

export interface PromptConfig {
  version: string;
  description: string;
  system_prompt: string;
  user_prompt_template: string;
  output_format: string;
}

// ==================== 应用设置 ====================

export interface AppSettings {
  theme: 'dark' | 'light' | 'system';
  language: 'zh-CN' | 'en-US';
  autoSave: boolean;
  confirmBeforeDelete: boolean;
  showTips: boolean;
}

// ==================== 存储路径配置 ====================

export interface PathConfig {
  media_root: string;
  annotations_dir: string;
  vectors_dir: string;
  cache_dir: string;
  posters_dir: string;
}

// ==================== 综合设置状态 ====================

export interface SettingsState {
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
  annotation: AnnotationConfig;
  
  // 提示词
  promptConfig: PromptConfig;
  
  // 应用设置
  app: AppSettings;
  
  // 路径配置
  paths: PathConfig;
  
  // UI 状态
  isLoading: boolean;
  isSaving: boolean;
  hasChanges: boolean;
  error: string | null;
}

// ==================== API 响应类型 ====================

export interface SettingsResponse {
  success: boolean;
  message?: string;
  data?: any;
}

export interface ProvidersResponse {
  providers: LLMProvider[];
  active_provider: string;
}

export interface ConnectionTestResponse {
  success: boolean;
  latency?: number;
  error?: string;
  model_info?: {
    id: string;
    owned_by: string;
  };
}
