// frontend-ui/src/types/settings.ts
/**
 * 设置模块类型定义
 */

// ==================== 模型提供者统一类型（数据库驱动） ====================

export interface ModelProvider {
  id: string;
  name: string;
  category: 'llm' | 'embedding';
  provider_type: 'local' | 'commercial';
  local_mode: string;  // 'ollama' | 'docker' | ''
  base_url: string;
  model: string;
  api_key: string;      // 脱敏后的 API Key
  max_tokens: number;
  temperature: number;
  timeout: number;
  dimension: number;     // Embedding 专用
  api_style: string;     // 'openai' | 'ollama'
  description: string;
  price_info: string;
  is_active: boolean;
  is_default: boolean;
  sort_order: number;
  enabled: boolean;
  extra_config: Record<string, any>;
  created_at: string | null;
  updated_at: string | null;
}

// 兼容旧类型（向后兼容）
export type LLMProvider = ModelProvider;
export type EmbeddingProvider = ModelProvider;

export interface LLMConnectionStatus {
  status: 'idle' | 'testing' | 'connected' | 'failed';
  error?: string;
  latency?: number;
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

// ==================== 入库配置（数据库驱动） ====================

export interface IngestionProfile {
  id: string;
  name: string;
  description: string;
  profile_type: 'annotation' | 'vectorization';
  model_provider_id: string | null;
  batch_size: number;
  concurrent_requests: number;
  max_retries: number;
  retry_delay: number;
  timeout: number;
  save_interval: number;
  annotation_depth: string;
  included_tag_categories: string[];
  chunk_overlap: number;
  normalize_embeddings: boolean;
  is_default: boolean;
  is_active: boolean;
  extra_config: Record<string, any>;
  created_at: string | null;
  updated_at: string | null;
}

// ==================== 提示词模板 ====================

export interface PromptTemplate {
  id: string;
  strategy_id: string | null;
  template_type: 'system' | 'user' | 'retrieval' | 'chat';
  name: string;
  description: string;
  prompt_text: string;
  variables: string | null;
  output_schema: string | null;
  compatible_models: string | null;
  version: string;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

// ==================== 标签分类与定义 ====================

export interface TagCategory {
  id: string;
  name: string;
  description: string;
  layer: number;
  icon: string | null;
  color: string | null;
  is_editable: boolean;
  is_required: boolean;
  is_multi_select: boolean;
  sort_order: number;
  is_active: boolean;
  tag_count?: number;
}

export interface TagDefinition {
  id: string;
  category_id: string;
  value: string;
  display_name: string;
  description: string;
  color: string | null;
  llm_hints: string | null;
  example_phrases: string | null;
  is_builtin: boolean;
  is_active: boolean;
  sort_order: number;
  usage_count: number;
}

// ==================== 数据库统计 ====================

export interface DatabaseStats {
  movies_total: number;
  movies_annotated: number;
  movies_vectorized: number;
  lines_total: number;
  lines_vectorized: number;
  models_llm: number;
  models_embedding: number;
  models_active_llm: number;
  models_active_embedding: number;
  tag_categories: number;
  tag_definitions: number;
  db_size_bytes: number;
  db_size_mb: number;
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
