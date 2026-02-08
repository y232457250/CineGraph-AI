-- ============================================================
-- CineGraph-AI 完整数据库架构
-- 版本: 1.0.0
-- 描述: 支持影片入库、语义标注、向量化、无限画布、LLM协作的完整数据库
-- ============================================================

-- ============================================================
-- 第一部分：系统配置与元数据
-- ============================================================

-- 系统配置表
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化系统版本
INSERT INTO system_config (key, value, description) VALUES
('db_version', '1.0.0', '数据库版本'),
('app_version', '1.0.0', '应用版本'),
('last_migration', datetime('now'), '上次迁移时间');

-- ============================================================
-- 第二部分：用户与权限（可选，支持多用户协作）
-- ============================================================

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT,
    avatar_url TEXT,
    preferences TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- 第三部分：影片入库模块
-- ============================================================

-- 影片主表
CREATE TABLE movies (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_title TEXT,
    media_type TEXT DEFAULT 'movie',
    year INTEGER,
    folder TEXT,
    folder_path TEXT,
    poster_url TEXT,
    local_poster TEXT,
    director TEXT,
    writer TEXT,
    starring TEXT,
    genre TEXT,
    country TEXT,
    language TEXT,
    release_date TEXT,
    douban_url TEXT,
    rating TEXT,
    import_batch TEXT,
    imported_by TEXT,
    status_import TEXT DEFAULT 'pending',
    status_annotate TEXT DEFAULT 'pending',
    status_vectorize TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_movies_type ON movies(media_type);
CREATE INDEX idx_movies_year ON movies(year);
CREATE INDEX idx_movies_status ON movies(status_annotate, status_vectorize);
CREATE INDEX idx_movies_batch ON movies(import_batch);

-- 剧集表（电视剧用）
CREATE TABLE episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id TEXT NOT NULL,
    episode_number INTEGER NOT NULL,
    video_path TEXT,
    subtitle_path TEXT,
    video_filename TEXT,
    subtitle_filename TEXT,
    status_vectorize TEXT DEFAULT 'pending',
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
    UNIQUE(movie_id, episode_number)
);

CREATE INDEX idx_episodes_movie ON episodes(movie_id);
CREATE INDEX idx_episodes_number ON episodes(movie_id, episode_number);

-- ============================================================
-- 第四部分：语义标注模块（核心）
-- ============================================================

-- 台词主表
CREATE TABLE lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id TEXT UNIQUE NOT NULL,
    movie_id TEXT NOT NULL,
    episode_number INTEGER,
    line_index INTEGER DEFAULT 0,
    text TEXT NOT NULL,
    clean_text TEXT,
    vector_text TEXT,
    start_time REAL DEFAULT 0,
    end_time REAL DEFAULT 0,
    duration REAL DEFAULT 0,
    character_name TEXT,
    character_id INTEGER,
    
    -- 第一层：基础标签
    sentence_type TEXT,
    can_follow TEXT,
    can_lead_to TEXT,
    emotion TEXT,
    emotion_transition TEXT,
    tone TEXT,
    character_type TEXT,
    
    -- 第二层：潜台词
    context_dye TEXT,
    context_intensity REAL DEFAULT 0.5,
    subtext_type TEXT,
    subtext_description TEXT,
    is_meme BOOLEAN DEFAULT 0,
    meme_name TEXT,
    meme_popularity INTEGER,
    social_function TEXT,
    surface_sentiment TEXT,
    actual_sentiment TEXT,
    sentiment_polarity TEXT,
    
    -- 第三层：隐喻
    metaphor_category TEXT,
    metaphor_keyword TEXT,
    metaphor_direction TEXT,
    metaphor_strength REAL DEFAULT 0.5,
    semantic_field TEXT,
    
    -- 算法字段
    intensity INTEGER DEFAULT 5,
    hook_score REAL DEFAULT 0.5,
    ambiguity REAL DEFAULT 0.5,
    viral_potential REAL DEFAULT 0.5,
    tags_json TEXT,
    
    -- 向量化状态
    vectorized BOOLEAN DEFAULT 0,
    vector_id TEXT,
    
    -- 标注信息
    annotated_by TEXT,
    annotated_at TIMESTAMP,
    annotation_confidence REAL,
    is_signature BOOLEAN DEFAULT 0,
    is_catchphrase BOOLEAN DEFAULT 0,
    signature_score REAL DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);

CREATE INDEX idx_lines_movie ON lines(movie_id);
CREATE INDEX idx_lines_episode ON lines(movie_id, episode_number);
CREATE INDEX idx_lines_sentence ON lines(sentence_type);
CREATE INDEX idx_lines_emotion ON lines(emotion);
CREATE INDEX idx_lines_tone ON lines(tone);
CREATE INDEX idx_lines_character ON lines(character_type);
CREATE INDEX idx_lines_context ON lines(context_dye);
CREATE INDEX idx_lines_metaphor ON lines(metaphor_category);
CREATE INDEX idx_lines_semantic ON lines(semantic_field);
CREATE INDEX idx_lines_vectorized ON lines(vectorized);
CREATE INDEX idx_lines_signature ON lines(is_signature);

-- 角色规范化表
CREATE TABLE characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id TEXT NOT NULL,
    name TEXT NOT NULL,
    normalized_name TEXT,
    character_type TEXT,
    actor TEXT,
    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
);

CREATE INDEX idx_characters_movie ON characters(movie_id);
CREATE INDEX idx_characters_name ON characters(normalized_name);

-- ============================================================
-- 第五部分：向量化与搜索
-- ============================================================

CREATE TABLE vectorization_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    error_message TEXT,
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (line_id) REFERENCES lines(line_id) ON DELETE CASCADE
);

CREATE INDEX idx_vector_queue_status ON vectorization_queue(status);
CREATE INDEX idx_vector_queue_priority ON vectorization_queue(priority);

CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    session_id TEXT,
    search_mode TEXT,
    search_conditions TEXT,
    result_count INTEGER,
    execution_time_ms INTEGER,
    user_rating INTEGER,
    selected_line_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (selected_line_id) REFERENCES lines(line_id) ON DELETE SET NULL
);

CREATE INDEX idx_search_history_user ON search_history(user_id);
CREATE INDEX idx_search_history_session ON search_history(session_id);

-- ============================================================
-- 第六部分：无限画布模块
-- ============================================================

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    owner_id TEXT,
    is_public BOOLEAN DEFAULT 0,
    theme TEXT,
    style TEXT DEFAULT 'absurd',
    viewport_x REAL DEFAULT 0,
    viewport_y REAL DEFAULT 0,
    viewport_zoom REAL DEFAULT 1,
    config_json TEXT,
    total_duration REAL DEFAULT 0,
    target_duration REAL DEFAULT 29,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);

CREATE TABLE canvas_nodes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    parent_id TEXT,
    node_order INTEGER DEFAULT 0,
    depth INTEGER DEFAULT 0,
    node_type TEXT DEFAULT 'clip',
    line_id TEXT,
    title TEXT,
    content TEXT,
    pos_x REAL DEFAULT 0,
    pos_y REAL DEFAULT 0,
    width REAL DEFAULT 200,
    height REAL DEFAULT 100,
    color TEXT,
    z_index INTEGER DEFAULT 0,
    collapsed BOOLEAN DEFAULT 0,
    locked BOOLEAN DEFAULT 0,
    trim_start REAL DEFAULT 0,
    trim_end REAL,
    volume REAL DEFAULT 1,
    timeline_start REAL,
    timeline_duration REAL,
    metadata_json TEXT,
    association_source TEXT DEFAULT 'manual',
    association_confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES canvas_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (line_id) REFERENCES lines(line_id) ON DELETE SET NULL
);

CREATE INDEX idx_nodes_project ON canvas_nodes(project_id);
CREATE INDEX idx_nodes_parent ON canvas_nodes(parent_id);
CREATE INDEX idx_nodes_line ON canvas_nodes(line_id);
CREATE INDEX idx_nodes_type ON canvas_nodes(node_type);

CREATE TABLE canvas_edges (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    source_anchor TEXT DEFAULT 'output',
    target_anchor TEXT DEFAULT 'input',
    relation_type TEXT,
    relation_strength REAL DEFAULT 0.5,
    label TEXT,
    color TEXT,
    width REAL DEFAULT 2,
    is_dashed BOOLEAN DEFAULT 0,
    metaphor_transition TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES canvas_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES canvas_nodes(id) ON DELETE CASCADE
);

CREATE INDEX idx_edges_project ON canvas_edges(project_id);
CREATE INDEX idx_edges_source ON canvas_edges(source_id);
CREATE INDEX idx_edges_target ON canvas_edges(target_id);

CREATE TABLE sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    name TEXT DEFAULT 'main',
    total_duration REAL DEFAULT 0,
    target_duration REAL DEFAULT 29,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE sequence_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    item_order INTEGER NOT NULL,
    trim_start REAL DEFAULT 0,
    trim_end REAL,
    volume REAL DEFAULT 1,
    transition_type TEXT DEFAULT 'cut',
    transition_duration REAL DEFAULT 0,
    FOREIGN KEY (sequence_id) REFERENCES sequences(id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES canvas_nodes(id) ON DELETE CASCADE
);

CREATE INDEX idx_seq_items_sequence ON sequence_items(sequence_id);
CREATE INDEX idx_seq_items_order ON sequence_items(sequence_id, item_order);

-- ============================================================
-- 第七部分：LLM集成与模型管理
-- ============================================================

-- 模型提供者统一配置表（替代旧版 llm_model_configs）
-- 统一管理 LLM 和 Embedding 模型
CREATE TABLE model_providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,           -- 'llm' 或 'embedding'
    provider_type TEXT NOT NULL DEFAULT 'local',  -- 'local' 或 'commercial'
    local_mode TEXT DEFAULT '',        -- 'ollama' / 'docker' / ''
    base_url TEXT NOT NULL,
    model TEXT NOT NULL,               -- 模型名称/ID
    api_key TEXT DEFAULT '',           -- API Key（可为空，或环境变量 ${VAR}）
    max_tokens INTEGER DEFAULT 2000,
    temperature REAL DEFAULT 0.7,
    timeout INTEGER DEFAULT 60,
    dimension INTEGER DEFAULT 0,       -- Embedding向量维度（0=自动检测）
    api_style TEXT DEFAULT 'openai',   -- 'openai' / 'ollama'
    description TEXT DEFAULT '',
    price_info TEXT DEFAULT '',         -- 价格描述
    is_active BOOLEAN DEFAULT 0,       -- 是否为当前激活的提供者
    is_default BOOLEAN DEFAULT 0,      -- 是否为系统预置
    sort_order INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT 1,
    extra_config TEXT DEFAULT '{}',     -- JSON 扩展配置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_provider_category ON model_providers(category);
CREATE INDEX idx_provider_active ON model_providers(is_active);
CREATE INDEX idx_provider_category_active ON model_providers(category, is_active);

-- 默认 LLM 提供者
INSERT INTO model_providers (id, name, category, provider_type, local_mode, base_url, model, max_tokens, temperature, timeout, description, price_info, is_active, is_default, sort_order, enabled) VALUES
-- === Ollama 本地模型 ===
('ollama_qwen3_4b', 'Qwen3:4B (本地Ollama)', 'llm', 'local', 'ollama', 'http://localhost:11434/v1', 'qwen3:4b', 2000, 0.7, 120, '通过Ollama运行的本地Qwen3 4B模型，轻量快速', '免费', 1, 1, 10, 1),
('ollama_qwen3_8b', 'Qwen3:8B (本地Ollama)', 'llm', 'local', 'ollama', 'http://localhost:11434/v1', 'qwen3:8b', 4000, 0.7, 180, '本地Qwen3 8B，标注质量更好', '免费', 0, 1, 11, 1),
-- === Ollama 云端模型 ===
('ollama_cloud_deepseek_v3', 'DeepSeek-V3.1:671B (Ollama云)', 'llm', 'local', 'ollama', 'http://localhost:11434/v1', 'deepseek-v3.1:671b-cloud', 4000, 0.7, 120, 'Ollama云端DeepSeek V3.1', '免费(有配额)', 0, 1, 20, 1),
('ollama_cloud_qwen_vl', 'Qwen3-VL:235B (Ollama云)', 'llm', 'local', 'ollama', 'http://localhost:11434/v1', 'qwen3-vl:235b-cloud', 4000, 0.7, 150, 'Ollama云端Qwen3 VL多模态', '免费(有配额)', 0, 1, 21, 1),
-- === 商用 API ===
('deepseek_chat', 'DeepSeek-V3', 'llm', 'commercial', '', 'https://api.deepseek.com/v1', 'deepseek-chat', 4000, 0.7, 30, 'DeepSeek V3，中文效果极佳，性价比最高', '¥1/百万token(输入) ¥2/百万token(输出)', 0, 1, 30, 1),
('aliyun_qwen_max', '通义千问Max', 'llm', 'commercial', '', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'qwen-max-latest', 4000, 0.7, 45, '阿里云通义千问Max，最强中文能力', '¥2/百万token(输入) ¥6/百万token(输出)', 0, 1, 40, 1),
('openai_gpt4o', 'GPT-4o', 'llm', 'commercial', '', 'https://api.openai.com/v1', 'gpt-4o', 4000, 0.7, 30, 'OpenAI GPT-4o，强大的多模态能力', '$2.5/百万token(输入) $10/百万token(输出)', 0, 1, 50, 1),
('moonshot_kimi_k1', 'Kimi-K1', 'llm', 'commercial', '', 'https://api.moonshot.cn/v1', 'kimi-k1', 4000, 0.7, 45, 'Moonshot Kimi K1，超长上下文支持', '¥6/百万token(输入)', 0, 1, 60, 1),
('zhipu_glm4', 'GLM-4', 'llm', 'commercial', '', 'https://open.bigmodel.cn/api/paas/v4', 'glm-4', 4000, 0.7, 45, '智谱GLM-4，中文能力强大', '¥5/百万token(输入)', 0, 1, 70, 1),
('anthropic_claude_sonnet', 'Claude 3.5 Sonnet', 'llm', 'commercial', '', 'https://api.anthropic.com/v1', 'claude-3-5-sonnet-20241022', 4000, 0.7, 45, 'Anthropic Claude 3.5 Sonnet，最佳综合能力', '$3/百万token(输入) $15/百万token(输出)', 0, 1, 80, 1),
('google_gemini_pro', 'Gemini 2.0 Flash', 'llm', 'commercial', '', 'https://generativelanguage.googleapis.com/v1beta', 'gemini-2.0-flash', 4000, 0.7, 45, 'Google Gemini 2.0 Flash，快速高效', '免费(有配额)', 0, 1, 90, 1);

-- 默认 Embedding 提供者
INSERT INTO model_providers (id, name, category, provider_type, local_mode, base_url, model, dimension, timeout, api_style, description, price_info, is_active, is_default, sort_order, enabled) VALUES
-- === Ollama 本地模型 ===
('ollama_qwen3_embedding', 'Qwen3-Embedding:4B (本地Ollama)', 'embedding', 'local', 'ollama', 'http://localhost:11434', 'qwen3-embedding:4b-fp16', 0, 60, 'ollama', '本地Qwen3 Embedding模型', '免费', 1, 1, 10, 1),
-- === 商用 API ===
('siliconflow_bge_m3', 'BGE-M3 (硅基流动)', 'embedding', 'commercial', '', 'https://api.siliconflow.cn/v1', 'BAAI/bge-m3', 1024, 30, 'openai', '硅基流动BGE-M3，多语言效果极佳', '免费', 0, 1, 20, 1),
('aliyun_embedding_v3', 'text-embedding-v3 (阿里云)', 'embedding', 'commercial', '', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'text-embedding-v3', 1024, 30, 'openai', '阿里云Embedding V3，中文最优', '¥0.0007/千token', 0, 1, 30, 1),
('openai_embedding_large', 'text-embedding-3-large (OpenAI)', 'embedding', 'commercial', '', 'https://api.openai.com/v1', 'text-embedding-3-large', 3072, 45, 'openai', 'OpenAI Embedding Large，最强性能', '$0.13/百万token', 0, 1, 40, 1),
('deepseek_embedding', 'DeepSeek-Embedding', 'embedding', 'commercial', '', 'https://api.deepseek.com/v1', 'deepseek-embedding', 1024, 30, 'openai', 'DeepSeek Embedding，中文高性价比', '¥0.5/百万token', 0, 1, 50, 1);

-- 兼容旧表的视图（如有引用 llm_model_configs 的旧代码）
CREATE VIEW IF NOT EXISTS llm_model_configs AS
SELECT
    id, provider_type, name AS provider_name, base_url, api_key,
    '' AS api_version, model AS model_name, temperature, max_tokens,
    1.0 AS top_p, 0 AS frequency_penalty, 0 AS presence_penalty,
    timeout, 3 AS max_retries, 1 AS retry_delay,
    enabled AS is_available, is_default,
    CASE WHEN provider_type = 'local' THEN 1 ELSE 0 END AS is_local,
    '["annotation","chat"]' AS supported_tasks,
    NULL AS input_price_per_1k, NULL AS output_price_per_1k,
    NULL AS avg_response_time_ms, NULL AS success_rate,
    description, created_at, updated_at
FROM model_providers
WHERE category = 'llm';

CREATE TABLE llm_chat_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    project_id TEXT,
    model_id TEXT NOT NULL,
    strategy_id TEXT,
    topic TEXT,
    context TEXT,
    message_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (model_id) REFERENCES model_providers(id) ON DELETE CASCADE
);

CREATE TABLE llm_chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    parsed_data TEXT,
    referenced_line_ids TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES llm_chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_chat_session ON llm_chat_messages(session_id);

CREATE TABLE semantic_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    line_id TEXT NOT NULL,
    match_scores TEXT,
    overall_score REAL,
    match_reason TEXT,
    rank INTEGER,
    is_selected BOOLEAN DEFAULT 0,
    user_rating INTEGER,
    FOREIGN KEY (session_id) REFERENCES llm_chat_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (line_id) REFERENCES lines(line_id) ON DELETE CASCADE
);

CREATE INDEX idx_matches_session ON semantic_matches(session_id);
CREATE INDEX idx_matches_line ON semantic_matches(line_id);

CREATE TABLE creative_paths (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    name TEXT,
    description TEXT,
    theme TEXT,
    path_data TEXT,
    node_count INTEGER DEFAULT 0,
    duration_estimate INTEGER,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- ============================================================
-- 第八部分：标签体系配置（增强版）
-- ============================================================

CREATE TABLE tag_categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    layer INTEGER DEFAULT 1,
    icon TEXT,
    color TEXT,
    is_editable BOOLEAN DEFAULT 1,
    is_required BOOLEAN DEFAULT 0,
    is_multi_select BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

INSERT INTO tag_categories (id, name, description, layer, is_editable, is_required, sort_order) VALUES
-- 第一层：基础标签
('sentence_type', '句型', '决定接话逻辑的句型分类', 1, 1, 1, 1),
('emotion', '情绪', '用于递进和对比的情绪标签', 1, 1, 1, 2),
('tone', '语气', '用于节奏控制的语气标签', 1, 1, 0, 3),
('character_type', '角色类型', '跨剧匹配的角色类型', 1, 1, 0, 4),
('scene_type', '场景类型', '对话发生的场景分类', 1, 1, 0, 5),
('speech_style', '说话风格', '台词的语言风格', 1, 1, 0, 6),
-- 第二层：潜台词
('context_dye', '语境染色', '台词带来的整体氛围底色', 2, 1, 0, 10),
('subtext_type', '隐含语义', '潜台词类型', 2, 1, 0, 11),
('social_function', '社交功能', '这句话的社交作用', 2, 1, 0, 12),
('dramatic_function', '戏剧功能', '在剧本结构中的作用', 2, 1, 0, 13),
('power_dynamic', '权力动态', '对话中的权力关系', 2, 1, 0, 14),
-- 第三层：隐喻
('metaphor_category', '隐喻类别', '身体化隐喻类别', 3, 1, 0, 20),
('semantic_field', '语义场', '跨隐喻的主题聚合', 3, 1, 0, 21);

CREATE TABLE tag_definitions (
    id TEXT PRIMARY KEY,
    category_id TEXT NOT NULL,
    value TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    color TEXT,
    icon TEXT,
    can_follow TEXT,                   -- JSON: 可接在哪些标签后
    can_lead_to TEXT,                  -- JSON: 后可接哪些标签
    related_tags TEXT,                 -- JSON: 关联标签
    llm_hints TEXT,                    -- LLM识别提示
    example_phrases TEXT,              -- JSON: 示例短语
    importance_score REAL DEFAULT 0.5, -- 标签重要性评分
    rarity_score REAL DEFAULT 0.5,     -- 稀有度评分
    cultural_context TEXT,             -- 文化背景提示
    genre_specificity TEXT,            -- 特定类型适用性（如：action/comedy/drama）
    is_builtin BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES tag_categories(id) ON DELETE CASCADE
);

CREATE INDEX idx_tag_def_category ON tag_definitions(category_id);
CREATE INDEX idx_tag_def_value ON tag_definitions(value);
CREATE INDEX idx_tag_def_active ON tag_definitions(is_active);

-- ---- sentence_type 句型标签 ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('st_question', 'sentence_type', 'question', '问句', '提出问题，期待回答', 1, 1),
('st_answer', 'sentence_type', 'answer', '答句', '回答问题', 1, 2),
('st_threat', 'sentence_type', 'threat', '威胁', '威胁恐吓对方', 1, 3),
('st_mock', 'sentence_type', 'mock', '嘲讽', '嘲讽讥笑对方', 1, 4),
('st_command', 'sentence_type', 'command', '命令', '命令或指示', 1, 5),
('st_statement', 'sentence_type', 'statement', '陈述句', '表达观点或事实', 1, 6),
('st_exclamation', 'sentence_type', 'exclamation', '感叹句', '表达强烈感情', 1, 7),
('st_rhetorical', 'sentence_type', 'rhetorical', '反问句', '不需回答的提问', 1, 8),
('st_doubt', 'sentence_type', 'doubt', '质疑句', '表达怀疑', 1, 9),
('st_plea', 'sentence_type', 'plea', '恳求', '请求、恳求', 1, 10),
('st_declaration', 'sentence_type', 'declaration', '宣告', '郑重宣布', 1, 11),
('st_monologue', 'sentence_type', 'monologue', '独白', '自言自语或旁白', 1, 12);

-- ---- emotion 情绪标签 ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('emo_angry', 'emotion', 'angry', '愤怒', '愤怒、生气', 1, 1),
('emo_funny', 'emotion', 'funny', '搞笑', '幽默、滑稽', 1, 2),
('emo_fear', 'emotion', 'fear', '害怕', '恐惧、害怕', 1, 3),
('emo_sad', 'emotion', 'sad', '悲伤', '悲伤、难过', 1, 4),
('emo_neutral', 'emotion', 'neutral', '中性', '无明显情绪', 1, 5),
('emo_sarcasm', 'emotion', 'sarcasm', '讽刺', '讽刺挖苦', 1, 6),
('emo_irony', 'emotion', 'irony', '反讽', '说反话、反讽', 1, 7),
('emo_nostalgia', 'emotion', 'nostalgia', '怀旧', '怀念过去', 1, 8),
('emo_confusion', 'emotion', 'confusion', '困惑', '困惑不解', 1, 9),
('emo_contempt', 'emotion', 'contempt', '轻蔑', '蔑视、不屑', 1, 10),
('emo_joy', 'emotion', 'joy', '喜悦', '快乐、开心', 1, 11),
('emo_despair', 'emotion', 'despair', '绝望', '绝望、无助', 1, 12),
('emo_surprise', 'emotion', 'surprise', '惊讶', '出乎意料', 1, 13),
('emo_disgust', 'emotion', 'disgust', '厌恶', '反感、厌恶', 1, 14);

-- ---- scene_type 场景类型标签（新增） ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('scene_confrontation', 'scene_type', 'confrontation', '对峙', '双方正面交锋', 1, 1),
('scene_negotiation', 'scene_type', 'negotiation', '谈判', '利益协商', 1, 2),
('scene_confession', 'scene_type', 'confession', '告白', '表达感情', 1, 3),
('scene_argument', 'scene_type', 'argument', '争吵', '激烈争论', 1, 4),
('scene_interrogation', 'scene_type', 'interrogation', '审讯', '盘问追查', 1, 5),
('scene_casual', 'scene_type', 'casual', '日常', '日常闲聊', 1, 6),
('scene_ceremony', 'scene_type', 'ceremony', '仪式', '正式场合', 1, 7),
('scene_crisis', 'scene_type', 'crisis', '危机', '紧急情况', 1, 8);

-- ---- speech_style 说话风格标签（新增） ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('style_formal', 'speech_style', 'formal', '正式', '书面化、正式场合', 1, 1),
('style_slang', 'speech_style', 'slang', '俚语', '口语化、接地气', 1, 2),
('style_poetic', 'speech_style', 'poetic', '诗意', '富有文学性', 1, 3),
('style_technical', 'speech_style', 'technical', '技术', '专业术语', 1, 4),
('style_humorous', 'speech_style', 'humorous', '幽默', '诙谐调侃', 1, 5),
('style_cold', 'speech_style', 'cold', '冷酷', '冷淡、无情', 1, 6);

-- ---- dramatic_function 戏剧功能标签（新增） ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('drama_turning_point', 'dramatic_function', 'turning_point', '转折点', '情节重大转折', 1, 1),
('drama_reveal', 'dramatic_function', 'reveal', '揭示', '重要信息揭露', 1, 2),
('drama_escalation', 'dramatic_function', 'escalation', '冲突升级', '矛盾激化', 1, 3),
('drama_resolution', 'dramatic_function', 'resolution', '化解', '矛盾解决', 1, 4),
('drama_foreshadow', 'dramatic_function', 'foreshadow', '伏笔', '埋下后续线索', 1, 5),
('drama_climax', 'dramatic_function', 'climax', '高潮', '情感或剧情最高点', 1, 6);

-- ---- power_dynamic 权力动态标签（新增） ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('power_dominant', 'power_dynamic', 'dominant', '支配', '占据话语主导权', 1, 1),
('power_submissive', 'power_dynamic', 'submissive', '服从', '被动接受', 1, 2),
('power_equal', 'power_dynamic', 'equal', '平等', '势均力敌', 1, 3),
('power_subversive', 'power_dynamic', 'subversive', '颠覆', '弱势方反转', 1, 4),
('power_manipulative', 'power_dynamic', 'manipulative', '操控', '暗中控制', 1, 5);

-- ---- metaphor_category 隐喻类别（扩展） ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('meta_eat', 'metaphor_category', 'eat', '吃/饥饿', '食欲、欲望、占有隐喻', 1, 1),
('meta_hard', 'metaphor_category', 'hard', '硬/软', '实力、性格、性暗示隐喻', 1, 2),
('meta_space', 'metaphor_category', 'space', '进/出', '空间、权力、准入隐喻', 1, 3),
('meta_light', 'metaphor_category', 'light', '光/暗', '光明、黑暗、启示、隐藏', 1, 4),
('meta_water', 'metaphor_category', 'water', '水/火', '情感流动、激情、毁灭', 1, 5),
('meta_body', 'metaphor_category', 'body', '身体部位', '心脏=情感、头脑=理性等', 1, 6),
('meta_journey', 'metaphor_category', 'journey', '旅程', '人生旅程、进步、目标', 1, 7),
('meta_war', 'metaphor_category', 'war', '战争', '对抗、攻防、策略', 1, 8),
('meta_animal', 'metaphor_category', 'animal', '动物', '兽性、本能、特质类比', 1, 9),
('meta_weather', 'metaphor_category', 'weather', '天气', '心情变化、局势变幻', 1, 10);

-- ---- tone 语气标签 ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('tone_strong', 'tone', 'strong', '强硬', '强势、坚定的语气', 1, 1),
('tone_weak', 'tone', 'weak', '软弱', '卑微、无力的语气', 1, 2),
('tone_provocative', 'tone', 'provocative', '挑衅', '挑衅、刺激对方', 1, 3),
('tone_calm', 'tone', 'calm', '平静', '冷静、克制的语气', 1, 4),
('tone_sarcastic', 'tone', 'sarcastic', '讽刺', '阴阳怪气、反话', 1, 5),
('tone_pleading', 'tone', 'pleading', '恳求', '卑微恳求的语气', 1, 6),
('tone_authoritative', 'tone', 'authoritative', '权威', '不容置疑的语气', 1, 7),
('tone_playful', 'tone', 'playful', '戏谑', '开玩笑、调侃', 1, 8),
('tone_cold', 'tone', 'cold', '冷漠', '冷冰冰、不带感情', 1, 9),
('tone_emotional', 'tone', 'emotional', '动情', '饱含深情的语气', 1, 10),
('tone_hesitant', 'tone', 'hesitant', '犹豫', '吞吞吐吐、不确定', 1, 11),
('tone_threatening', 'tone', 'threatening', '威胁', '暗含威胁的语气', 1, 12);

-- ---- character_type 角色类型标签 ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('char_hero', 'character_type', 'hero', '英雄', '正义主角、拯救者', 1, 1),
('char_villain', 'character_type', 'villain', '反派', '对立面、坏人', 1, 2),
('char_comic', 'character_type', 'comic', '喜剧', '搞笑担当、谐星', 1, 3),
('char_mentor', 'character_type', 'mentor', '导师', '引导者、智者', 1, 4),
('char_lover', 'character_type', 'lover', '情人', '恋人、痴情者', 1, 5),
('char_trickster', 'character_type', 'trickster', '骗子', '狡猾、欺诈者', 1, 6),
('char_underdog', 'character_type', 'underdog', '弱者', '被压迫的小人物', 1, 7),
('char_boss', 'character_type', 'boss', '大佬', '权力者、领导', 1, 8),
('char_sidekick', 'character_type', 'sidekick', '跟班', '忠实追随者', 1, 9),
('char_antihero', 'character_type', 'antihero', '反英雄', '亦正亦邪的角色', 1, 10);

-- ---- context_dye 语境染色标签 ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('ctx_infidelity', 'context_dye', 'infidelity', '出轨', '涉及感情背叛的语境', 1, 1),
('ctx_absurd', 'context_dye', 'absurd', '荒诞', '超现实、荒谬的语境', 1, 2),
('ctx_taboo', 'context_dye', 'taboo', '禁忌', '触碰社会禁忌的语境', 1, 3),
('ctx_power', 'context_dye', 'power', '权力', '涉及权力博弈的语境', 1, 4),
('ctx_betrayal', 'context_dye', 'betrayal', '背叛', '信任被辜负的语境', 1, 5),
('ctx_revenge', 'context_dye', 'revenge', '复仇', '以牙还牙的语境', 1, 6),
('ctx_sacrifice', 'context_dye', 'sacrifice', '牺牲', '为他人舍弃自我的语境', 1, 7),
('ctx_deception', 'context_dye', 'deception', '欺骗', '谎言与伪装的语境', 1, 8),
('ctx_romantic', 'context_dye', 'romantic', '浪漫', '爱情、温馨的语境', 1, 9),
('ctx_dark_humor', 'context_dye', 'dark_humor', '黑色幽默', '用幽默包裹的残酷', 1, 10),
('ctx_nostalgia', 'context_dye', 'nostalgia', '怀旧', '追忆往昔的语境', 1, 11),
('ctx_survival', 'context_dye', 'survival', '求生', '生死攸关的语境', 1, 12);

-- ---- subtext_type 隐含语义标签 ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('sub_irony', 'subtext_type', 'irony', '反讽', '说的和想的完全相反', 1, 1),
('sub_sarcasm', 'subtext_type', 'sarcasm', '讽刺', '尖锐的嘲讽', 1, 2),
('sub_metaphor', 'subtext_type', 'metaphor', '隐喻', '借物言他', 1, 3),
('sub_threat_veiled', 'subtext_type', 'threat_veiled', '暗示威胁', '表面平静暗藏杀机', 1, 4),
('sub_double_meaning', 'subtext_type', 'double_meaning', '双关', '一语双意', 1, 5),
('sub_euphemism', 'subtext_type', 'euphemism', '委婉', '避开直说用婉转表达', 1, 6),
('sub_understatement', 'subtext_type', 'understatement', '轻描淡写', '故意说得很轻', 1, 7),
('sub_exaggeration', 'subtext_type', 'exaggeration', '夸张', '故意放大事实', 1, 8),
('sub_self_deprecation', 'subtext_type', 'self_deprecation', '自嘲', '拿自己开涮', 1, 9),
('sub_passive_aggressive', 'subtext_type', 'passive_aggressive', '被动攻击', '表面顺从暗中反抗', 1, 10),
('sub_guilt_trip', 'subtext_type', 'guilt_trip', '道德绑架', '用愧疚感操控他人', 1, 11),
('sub_humblebrag', 'subtext_type', 'humblebrag', '凡尔赛', '假装谦虚实则炫耀', 1, 12);

-- ---- social_function 社交功能标签 ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('sf_roast', 'social_function', 'roast', '吐槽', '调侃、损人', 1, 1),
('sf_showoff', 'social_function', 'showoff', '炫耀', '展示优越感', 1, 2),
('sf_sympathy', 'social_function', 'sympathy', '求同情', '博取同情', 1, 3),
('sf_bonding', 'social_function', 'bonding', '拉近关系', '增进亲密感', 1, 4),
('sf_boundary', 'social_function', 'boundary', '划清界限', '保持距离', 1, 5),
('sf_persuasion', 'social_function', 'persuasion', '说服', '试图改变对方想法', 1, 6),
('sf_comfort', 'social_function', 'comfort', '安慰', '给予情感支持', 1, 7),
('sf_provocation', 'social_function', 'provocation', '激将', '故意激怒以达到目的', 1, 8),
('sf_deflection', 'social_function', 'deflection', '转移话题', '回避敏感话题', 1, 9),
('sf_power_play', 'social_function', 'power_play', '权力展示', '彰显地位和控制力', 1, 10),
('sf_confession', 'social_function', 'confession', '坦白', '说出真心话', 1, 11),
('sf_flattery', 'social_function', 'flattery', '拍马屁', '恭维讨好', 1, 12);

-- ---- semantic_field 语义场标签 ----
INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('sem_desperation', 'semantic_field', 'desperation', '绝望挣扎', '走投无路、背水一战', 1, 1),
('sem_power_struggle', 'semantic_field', 'power_struggle', '权力斗争', '地位争夺、博弈', 1, 2),
('sem_identity_crisis', 'semantic_field', 'identity_crisis', '身份危机', '自我认知冲突', 1, 3),
('sem_moral_dilemma', 'semantic_field', 'moral_dilemma', '道德困境', '对错难辨的选择', 1, 4),
('sem_love_hate', 'semantic_field', 'love_hate', '爱恨纠葛', '感情的复杂交织', 1, 5),
('sem_betrayal_trust', 'semantic_field', 'betrayal_trust', '信任崩塌', '信任被打破', 1, 6),
('sem_social_mask', 'semantic_field', 'social_mask', '社交面具', '虚伪与真实的对立', 1, 7),
('sem_class_conflict', 'semantic_field', 'class_conflict', '阶层冲突', '贫富差距、阶层对立', 1, 8),
('sem_fate_destiny', 'semantic_field', 'fate_destiny', '命运无常', '无法掌控的命运', 1, 9),
('sem_freedom_cage', 'semantic_field', 'freedom_cage', '自由与束缚', '挣脱与困住', 1, 10),
('sem_growth', 'semantic_field', 'growth', '成长蜕变', '从幼稚到成熟', 1, 11),
('sem_revenge_justice', 'semantic_field', 'revenge_justice', '复仇与正义', '以暴制暴还是以德报怨', 1, 12);

-- ---- 标签连接规则（完善） ----
CREATE TABLE tag_connection_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_category_id TEXT NOT NULL,
    from_tag_id TEXT NOT NULL,
    to_category_id TEXT NOT NULL,
    to_tag_id TEXT NOT NULL,
    connection_type TEXT,              -- continuation/contrast/escalation/cause_effect/correlation/character_typical
    weight REAL DEFAULT 1.0,
    description TEXT,
    condition_text TEXT,
    is_active BOOLEAN DEFAULT 1
);

INSERT INTO tag_connection_rules (from_category_id, from_tag_id, to_category_id, to_tag_id, connection_type, weight, description) VALUES
-- 句型衔接规则
('sentence_type', 'st_question', 'sentence_type', 'st_answer', 'continuation', 0.9, '问句后接答句'),
('sentence_type', 'st_threat', 'sentence_type', 'st_mock', 'escalation', 0.8, '威胁升级成嘲讽'),
('sentence_type', 'st_command', 'sentence_type', 'st_doubt', 'contrast', 0.7, '命令后接质疑形成反抗'),
('sentence_type', 'st_statement', 'sentence_type', 'st_rhetorical', 'escalation', 0.6, '陈述后接反问加强力度'),
('sentence_type', 'st_mock', 'sentence_type', 'st_threat', 'escalation', 0.85, '嘲讽升级为威胁'),
('sentence_type', 'st_plea', 'sentence_type', 'st_command', 'contrast', 0.7, '恳求与命令形成反差'),
('sentence_type', 'st_declaration', 'sentence_type', 'st_doubt', 'contrast', 0.75, '宣告后接质疑制造张力'),
-- 句型→情绪因果关系
('sentence_type', 'st_threat', 'emotion', 'emo_fear', 'cause_effect', 0.7, '威胁引发恐惧'),
('sentence_type', 'st_mock', 'emotion', 'emo_angry', 'cause_effect', 0.75, '嘲讽引发愤怒'),
('sentence_type', 'st_question', 'emotion', 'emo_confusion', 'association', 0.6, '提问常伴随困惑'),
('sentence_type', 'st_plea', 'emotion', 'emo_despair', 'cause_effect', 0.65, '恳求源于绝望'),
-- 情绪关联
('emotion', 'emo_angry', 'emotion', 'emo_sad', 'contrast', 0.7, '愤怒与悲伤对比'),
('emotion', 'emo_funny', 'emotion', 'emo_sad', 'contrast', 0.9, '搞笑与悲伤强烈反差'),
('emotion', 'emo_fear', 'emotion', 'emo_angry', 'escalation', 0.6, '恐惧转化为愤怒'),
('emotion', 'emo_contempt', 'emotion', 'emo_angry', 'cause_effect', 0.7, '轻蔑引发愤怒'),
('emotion', 'emo_surprise', 'emotion', 'emo_fear', 'escalation', 0.5, '惊讶升级为恐惧'),
-- 角色典型行为
('character_type', 'char_villain', 'sentence_type', 'st_threat', 'character_typical', 0.9, '反派典型台词'),
('character_type', 'char_hero', 'sentence_type', 'st_declaration', 'character_typical', 0.85, '英雄人物常用宣告'),
('character_type', 'char_comic', 'emotion', 'emo_funny', 'character_typical', 0.9, '喜剧角色常见搞笑'),
('character_type', 'char_mentor', 'sentence_type', 'st_statement', 'character_typical', 0.7, '导师角色常用陈述'),
('character_type', 'char_boss', 'sentence_type', 'st_command', 'character_typical', 0.85, '大佬角色常用命令'),
('character_type', 'char_underdog', 'sentence_type', 'st_plea', 'character_typical', 0.75, '弱者角色常用恳求'),
('character_type', 'char_trickster', 'subtext_type', 'sub_double_meaning', 'character_typical', 0.8, '骗子角色常用双关'),
('character_type', 'char_antihero', 'tone', 'tone_sarcastic', 'character_typical', 0.75, '反英雄角色常用讽刺语气'),
-- 语气→情绪关联
('tone', 'tone_strong', 'emotion', 'emo_angry', 'association', 0.7, '强硬语气常伴愤怒'),
('tone', 'tone_pleading', 'emotion', 'emo_despair', 'association', 0.75, '恳求语气常伴绝望'),
('tone', 'tone_playful', 'emotion', 'emo_funny', 'association', 0.8, '戏谑语气常伴搞笑'),
('tone', 'tone_cold', 'emotion', 'emo_contempt', 'association', 0.7, '冷漠语气常伴轻蔑'),
('tone', 'tone_emotional', 'emotion', 'emo_sad', 'association', 0.65, '动情语气常伴悲伤'),
-- 语境染色→隐含语义关联
('context_dye', 'ctx_deception', 'subtext_type', 'sub_euphemism', 'association', 0.7, '欺骗语境常伴委婉手法'),
('context_dye', 'ctx_power', 'social_function', 'sf_power_play', 'association', 0.85, '权力语境常伴权力展示'),
('context_dye', 'ctx_absurd', 'subtext_type', 'sub_exaggeration', 'association', 0.75, '荒诞语境常伴夸张手法'),
('context_dye', 'ctx_dark_humor', 'subtext_type', 'sub_irony', 'association', 0.8, '黑色幽默常伴反讽'),
-- 社交功能→潜台词关联
('social_function', 'sf_roast', 'subtext_type', 'sub_sarcasm', 'association', 0.85, '吐槽常伴讽刺'),
('social_function', 'sf_showoff', 'subtext_type', 'sub_humblebrag', 'association', 0.8, '炫耀常伴凡尔赛'),
('social_function', 'sf_provocation', 'tone', 'tone_provocative', 'association', 0.9, '激将常伴挑衅语气'),
('social_function', 'sf_flattery', 'subtext_type', 'sub_euphemism', 'association', 0.7, '拍马屁常伴委婉'),
-- 语义场→隐喻关联
('semantic_field', 'sem_power_struggle', 'metaphor_category', 'meta_war', 'association', 0.85, '权力斗争常用战争隐喻'),
('semantic_field', 'sem_desperation', 'metaphor_category', 'meta_water', 'association', 0.6, '绝望挣扎常用水/火隐喻'),
('semantic_field', 'sem_love_hate', 'metaphor_category', 'meta_light', 'association', 0.65, '爱恨纠葛常用光暗隐喻'),
('semantic_field', 'sem_identity_crisis', 'metaphor_category', 'meta_journey', 'association', 0.7, '身份危机常用旅程隐喻'),
('semantic_field', 'sem_freedom_cage', 'metaphor_category', 'meta_space', 'association', 0.8, '自由与束缚常用空间隐喻'),
-- 场景→情绪
('scene_type', 'scene_confrontation', 'emotion', 'emo_angry', 'association', 0.8, '对峙场景常见愤怒'),
('scene_type', 'scene_confession', 'emotion', 'emo_nostalgia', 'association', 0.6, '告白常伴怀旧'),
('scene_type', 'scene_crisis', 'emotion', 'emo_fear', 'association', 0.75, '危机场景引发恐惧'),
-- 戏剧功能
('dramatic_function', 'drama_climax', 'emotion', 'emo_angry', 'association', 0.8, '高潮处常有强烈情绪'),
('dramatic_function', 'drama_turning_point', 'emotion', 'emo_surprise', 'cause_effect', 0.7, '转折带来惊讶'),
('dramatic_function', 'drama_reveal', 'sentence_type', 'st_exclamation', 'association', 0.6, '揭示常伴感叹'),
-- 权力动态
('power_dynamic', 'power_dominant', 'sentence_type', 'st_command', 'correlation', 0.85, '支配者常用命令'),
('power_dynamic', 'power_submissive', 'sentence_type', 'st_plea', 'correlation', 0.8, '服从者常用恳求'),
('power_dynamic', 'power_subversive', 'dramatic_function', 'drama_turning_point', 'association', 0.75, '权力颠覆即是转折');

-- ---- 标签层级关系表（新增） ----
CREATE TABLE tag_hierarchy (
    parent_tag_id TEXT NOT NULL,
    child_tag_id TEXT NOT NULL,
    relation_type TEXT DEFAULT 'is_a', -- is_a / part_of / related_to
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (parent_tag_id, child_tag_id),
    FOREIGN KEY (parent_tag_id) REFERENCES tag_definitions(id) ON DELETE CASCADE,
    FOREIGN KEY (child_tag_id) REFERENCES tag_definitions(id) ON DELETE CASCADE
);

-- 情绪细分层次
INSERT INTO tag_hierarchy (parent_tag_id, child_tag_id, relation_type) VALUES
('emo_angry', 'emo_contempt', 'is_a'),
('emo_angry', 'emo_disgust', 'related_to'),
('emo_sad', 'emo_despair', 'is_a'),
('emo_sad', 'emo_nostalgia', 'related_to'),
('emo_fear', 'emo_surprise', 'related_to'),
('emo_funny', 'emo_sarcasm', 'related_to'),
('emo_funny', 'emo_irony', 'related_to');

-- 语气层级关系
INSERT INTO tag_hierarchy (parent_tag_id, child_tag_id, relation_type) VALUES
('tone_strong', 'tone_authoritative', 'is_a'),
('tone_strong', 'tone_threatening', 'related_to'),
('tone_weak', 'tone_pleading', 'is_a'),
('tone_weak', 'tone_hesitant', 'related_to'),
('tone_sarcastic', 'tone_playful', 'related_to'),
('tone_cold', 'tone_threatening', 'related_to');

-- 角色类型层级关系
INSERT INTO tag_hierarchy (parent_tag_id, child_tag_id, relation_type) VALUES
('char_hero', 'char_antihero', 'related_to'),
('char_villain', 'char_trickster', 'related_to'),
('char_hero', 'char_mentor', 'related_to'),
('char_boss', 'char_villain', 'related_to'),
('char_underdog', 'char_sidekick', 'related_to');

-- 潜台词层级关系
INSERT INTO tag_hierarchy (parent_tag_id, child_tag_id, relation_type) VALUES
('sub_irony', 'sub_sarcasm', 'is_a'),
('sub_irony', 'sub_passive_aggressive', 'related_to'),
('sub_exaggeration', 'sub_humblebrag', 'related_to'),
('sub_euphemism', 'sub_understatement', 'is_a'),
('sub_threat_veiled', 'sub_passive_aggressive', 'related_to');

-- 语境染色层级关系
INSERT INTO tag_hierarchy (parent_tag_id, child_tag_id, relation_type) VALUES
('ctx_deception', 'ctx_betrayal', 'related_to'),
('ctx_power', 'ctx_revenge', 'related_to'),
('ctx_absurd', 'ctx_dark_humor', 'related_to'),
('ctx_romantic', 'ctx_nostalgia', 'related_to'),
('ctx_survival', 'ctx_sacrifice', 'related_to');

-- ---- 标签约束规则表（新增） ----
CREATE TABLE tag_constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id TEXT NOT NULL,
    constraint_type TEXT NOT NULL,     -- mutual_exclusive / requires / excludes / co_occurs
    tag_ids TEXT NOT NULL,             -- JSON数组
    constraint_message TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES tag_categories(id) ON DELETE CASCADE
);

INSERT INTO tag_constraints (category_id, constraint_type, tag_ids, constraint_message) VALUES
('emotion', 'mutual_exclusive', '["emo_angry", "emo_joy"]', '愤怒和喜悦通常不会同时出现'),
('emotion', 'mutual_exclusive', '["emo_fear", "emo_contempt"]', '恐惧和轻蔑很难共存'),
('sentence_type', 'mutual_exclusive', '["st_question", "st_command"]', '问句和命令互斥'),
('power_dynamic', 'mutual_exclusive', '["power_dominant", "power_submissive"]', '支配和服从互斥'),
-- 语气约束
('tone', 'mutual_exclusive', '["tone_strong", "tone_weak"]', '强硬和软弱的语气互斥'),
('tone', 'mutual_exclusive', '["tone_calm", "tone_emotional"]', '平静和动情的语气互斥'),
('tone', 'mutual_exclusive', '["tone_playful", "tone_threatening"]', '戏谑和威胁的语气互斥'),
-- 角色类型约束
('character_type', 'mutual_exclusive', '["char_hero", "char_villain"]', '英雄和反派通常互斥'),
('character_type', 'mutual_exclusive', '["char_mentor", "char_sidekick"]', '导师和跟班互斥'),
-- 潜台词约束
('subtext_type', 'mutual_exclusive', '["sub_euphemism", "sub_exaggeration"]', '委婉和夸张手法互斥'),
('subtext_type', 'co_occurs', '["sub_irony", "sub_passive_aggressive"]', '反讽常伴随被动攻击'),
-- 语境染色约束
('context_dye', 'mutual_exclusive', '["ctx_romantic", "ctx_revenge"]', '浪漫和复仇语境互斥'),
('context_dye', 'co_occurs', '["ctx_deception", "ctx_betrayal"]', '欺骗常伴随背叛');

-- ---- 标签本地化/多语言表（新增） ----
CREATE TABLE tag_localization (
    tag_id TEXT NOT NULL,
    language_code TEXT NOT NULL,       -- zh-CN / en-US / ja-JP
    display_name TEXT NOT NULL,
    description TEXT,
    cultural_note TEXT,                -- 文化差异说明
    PRIMARY KEY (tag_id, language_code),
    FOREIGN KEY (tag_id) REFERENCES tag_definitions(id) ON DELETE CASCADE
);

-- 英文本地化
INSERT INTO tag_localization (tag_id, language_code, display_name, description) VALUES
-- sentence_type
('st_question', 'en-US', 'Question', 'Asking a question, expecting an answer'),
('st_answer', 'en-US', 'Answer', 'Responding to a question'),
('st_threat', 'en-US', 'Threat', 'Threatening or intimidating'),
('st_mock', 'en-US', 'Mockery', 'Mocking or ridiculing'),
('st_command', 'en-US', 'Command', 'Giving orders'),
('st_statement', 'en-US', 'Statement', 'Stating facts or opinions'),
('st_exclamation', 'en-US', 'Exclamation', 'Expressing strong emotion'),
('st_rhetorical', 'en-US', 'Rhetorical', 'Question not expecting an answer'),
('st_doubt', 'en-US', 'Doubt', 'Expressing skepticism'),
('st_plea', 'en-US', 'Plea', 'Begging or pleading'),
('st_declaration', 'en-US', 'Declaration', 'Solemn announcement'),
('st_monologue', 'en-US', 'Monologue', 'Speaking to oneself or narration'),
-- emotion
('emo_angry', 'en-US', 'Angry', 'Anger, rage'),
('emo_funny', 'en-US', 'Funny', 'Humorous, comedic'),
('emo_fear', 'en-US', 'Fear', 'Terror, fright'),
('emo_sad', 'en-US', 'Sad', 'Sadness, sorrow'),
('emo_neutral', 'en-US', 'Neutral', 'No obvious emotion'),
('emo_sarcasm', 'en-US', 'Sarcasm', 'Sarcastic, caustic'),
('emo_irony', 'en-US', 'Irony', 'Saying the opposite'),
('emo_nostalgia', 'en-US', 'Nostalgia', 'Longing for the past'),
('emo_confusion', 'en-US', 'Confusion', 'Bewildered'),
('emo_contempt', 'en-US', 'Contempt', 'Scorn, disdain'),
('emo_joy', 'en-US', 'Joy', 'Happiness, delight'),
('emo_despair', 'en-US', 'Despair', 'Hopelessness'),
('emo_surprise', 'en-US', 'Surprise', 'Unexpected'),
('emo_disgust', 'en-US', 'Disgust', 'Revulsion, aversion'),
-- tone
('tone_strong', 'en-US', 'Strong', 'Assertive, firm tone'),
('tone_weak', 'en-US', 'Weak', 'Submissive, powerless tone'),
('tone_provocative', 'en-US', 'Provocative', 'Provoking, challenging'),
('tone_calm', 'en-US', 'Calm', 'Composed, restrained'),
('tone_sarcastic', 'en-US', 'Sarcastic', 'Passive-aggressive irony'),
('tone_pleading', 'en-US', 'Pleading', 'Begging tone'),
('tone_authoritative', 'en-US', 'Authoritative', 'Commanding authority'),
('tone_playful', 'en-US', 'Playful', 'Teasing, joking'),
('tone_cold', 'en-US', 'Cold', 'Emotionless, detached'),
('tone_emotional', 'en-US', 'Emotional', 'Full of feeling'),
('tone_hesitant', 'en-US', 'Hesitant', 'Uncertain, stammering'),
('tone_threatening', 'en-US', 'Threatening', 'Implying threat'),
-- character_type
('char_hero', 'en-US', 'Hero', 'Protagonist, savior'),
('char_villain', 'en-US', 'Villain', 'Antagonist, bad guy'),
('char_comic', 'en-US', 'Comic Relief', 'Comedy character'),
('char_mentor', 'en-US', 'Mentor', 'Guide, wise figure'),
('char_lover', 'en-US', 'Lover', 'Romantic partner'),
('char_trickster', 'en-US', 'Trickster', 'Cunning deceiver'),
('char_underdog', 'en-US', 'Underdog', 'Oppressed little guy'),
('char_boss', 'en-US', 'Boss', 'Authority figure, leader'),
('char_sidekick', 'en-US', 'Sidekick', 'Loyal follower'),
('char_antihero', 'en-US', 'Anti-hero', 'Morally ambiguous character'),
-- context_dye
('ctx_infidelity', 'en-US', 'Infidelity', 'Romantic betrayal context'),
('ctx_absurd', 'en-US', 'Absurd', 'Surreal, ridiculous context'),
('ctx_taboo', 'en-US', 'Taboo', 'Social taboo context'),
('ctx_power', 'en-US', 'Power', 'Power struggle context'),
('ctx_betrayal', 'en-US', 'Betrayal', 'Trust broken context'),
('ctx_revenge', 'en-US', 'Revenge', 'Revenge context'),
('ctx_deception', 'en-US', 'Deception', 'Lies and disguise context'),
('ctx_romantic', 'en-US', 'Romantic', 'Love, warmth context'),
('ctx_dark_humor', 'en-US', 'Dark Humor', 'Humor wrapping cruelty'),
-- subtext_type
('sub_irony', 'en-US', 'Irony', 'Saying opposite of meaning'),
('sub_sarcasm', 'en-US', 'Sarcasm', 'Sharp mockery'),
('sub_metaphor', 'en-US', 'Metaphor', 'Figurative language'),
('sub_double_meaning', 'en-US', 'Double Meaning', 'Dual interpretation'),
('sub_euphemism', 'en-US', 'Euphemism', 'Indirect expression'),
('sub_self_deprecation', 'en-US', 'Self-deprecation', 'Making fun of oneself'),
('sub_passive_aggressive', 'en-US', 'Passive-aggressive', 'Surface compliance, hidden resistance'),
('sub_humblebrag', 'en-US', 'Humblebrag', 'False modesty to show off'),
-- social_function
('sf_roast', 'en-US', 'Roast', 'Teasing, dissing'),
('sf_showoff', 'en-US', 'Show Off', 'Displaying superiority'),
('sf_sympathy', 'en-US', 'Seek Sympathy', 'Seeking compassion'),
('sf_bonding', 'en-US', 'Bonding', 'Building closeness'),
('sf_persuasion', 'en-US', 'Persuasion', 'Trying to convince'),
('sf_comfort', 'en-US', 'Comfort', 'Giving emotional support'),
('sf_provocation', 'en-US', 'Provocation', 'Deliberately provoking'),
('sf_power_play', 'en-US', 'Power Play', 'Asserting dominance'),
-- metaphor_category
('meta_eat', 'en-US', 'Eat/Hunger', 'Appetite, desire, possession metaphor'),
('meta_hard', 'en-US', 'Hard/Soft', 'Strength, character metaphor'),
('meta_space', 'en-US', 'In/Out', 'Space, power, access metaphor'),
('meta_light', 'en-US', 'Light/Dark', 'Enlightenment, concealment'),
('meta_water', 'en-US', 'Water/Fire', 'Emotional flow, passion'),
('meta_war', 'en-US', 'War', 'Conflict, strategy'),
('meta_animal', 'en-US', 'Animal', 'Instinct, nature metaphor'),
-- semantic_field
('sem_desperation', 'en-US', 'Desperation', 'No way out, last stand'),
('sem_power_struggle', 'en-US', 'Power Struggle', 'Status competition'),
('sem_identity_crisis', 'en-US', 'Identity Crisis', 'Self-cognition conflict'),
('sem_moral_dilemma', 'en-US', 'Moral Dilemma', 'Right vs wrong'),
('sem_love_hate', 'en-US', 'Love-Hate', 'Complex emotional entanglement'),
('sem_betrayal_trust', 'en-US', 'Trust Collapse', 'Trust being shattered');

-- ---- 文化特定标签表（新增） ----
CREATE TABLE culture_specific_tags (
    id TEXT PRIMARY KEY,
    tag_id TEXT NOT NULL,
    culture_code TEXT NOT NULL,        -- zh-CN / en-US / ja-JP
    specific_meaning TEXT,
    example_lines TEXT,                -- JSON: 示例台词
    FOREIGN KEY (tag_id) REFERENCES tag_definitions(id) ON DELETE CASCADE
);

CREATE INDEX idx_culture_tags_tag ON culture_specific_tags(tag_id);
CREATE INDEX idx_culture_tags_culture ON culture_specific_tags(culture_code);

-- 中文影视文化特定标签
INSERT INTO culture_specific_tags (id, tag_id, culture_code, specific_meaning, example_lines) VALUES
('cst_irony_zh', 'sub_irony', 'zh-CN', '中国式反讽，常见于宫斗、职场剧，用恭维掩饰攻击', '["臣妾做不到啊", "你可真是个好人呢", "这都是为了你好"]'),
('cst_sarcasm_zh', 'sub_sarcasm', 'zh-CN', '中式阴阳怪气，含蓄而尖锐的讽刺', '["你可真行啊", "你开心就好", "随便你怎么想"]'),
('cst_power_zh', 'ctx_power', 'zh-CN', '中国式权力表达，层级分明，常见于宫廷/官场剧', '["你知道我是谁吗", "跪下", "在本宫面前也敢放肆"]'),
('cst_humblebrag_zh', 'sub_humblebrag', 'zh-CN', '中国式凡尔赛，假装抱怨实则炫耀', '["唉，又被升职了真烦", "老公送的包太多了放不下"]'),
('cst_guilt_zh', 'sub_guilt_trip', 'zh-CN', '中国式道德绑架，常用亲情/孝道/面子施压', '["我这辈子都是为了你", "你对得起我吗", "别人家的孩子都…"]'),
('cst_roast_zh', 'sf_roast', 'zh-CN', '中式吐槽，从相声传统到弹幕文化的调侃方式', '["你这是典型的嘴上抹了蜜", "你脑子是被门夹了吧"]'),
('cst_eat_zh', 'meta_eat', 'zh-CN', '中文"吃"的隐喻极丰富：吃亏、吃醋、吃香、吃软饭、吃苦', '["你吃什么醋", "有你吃亏的时候", "让他吃点苦头"]'),
('cst_dark_humor_zh', 'ctx_dark_humor', 'zh-CN', '中式黑色幽默，在苦难中找笑点', '["活着就行了还要什么自行车", "打工人打工魂"]');

-- ============================================================
-- 第九部分：入库配置（语义标注 & 向量化参数）
-- ============================================================

-- 入库配置表：保存语义标注和向量化的模型选择与参数设定
CREATE TABLE ingestion_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    profile_type TEXT NOT NULL,        -- 'annotation' 或 'vectorization'
    model_provider_id TEXT,            -- 关联 model_providers 表中的模型
    -- 通用参数
    batch_size INTEGER DEFAULT 10,
    concurrent_requests INTEGER DEFAULT 1,
    max_retries INTEGER DEFAULT 3,
    retry_delay INTEGER DEFAULT 1000,  -- 毫秒
    timeout INTEGER DEFAULT 120,       -- 秒
    -- 标注专用参数
    save_interval INTEGER DEFAULT 50,
    annotation_depth TEXT DEFAULT 'full', -- 'full' / 'quick' / 'custom'
    included_tag_categories TEXT DEFAULT '[]', -- JSON: 启用的标签类别
    -- 向量化专用参数
    chunk_overlap INTEGER DEFAULT 0,
    normalize_embeddings BOOLEAN DEFAULT 1,
    -- 状态
    is_default BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    -- 扩展配置
    extra_config TEXT DEFAULT '{}',     -- JSON 扩展配置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_provider_id) REFERENCES model_providers(id) ON DELETE SET NULL
);

CREATE INDEX idx_ingestion_profile_type ON ingestion_profiles(profile_type);
CREATE INDEX idx_ingestion_profile_active ON ingestion_profiles(is_active);
CREATE INDEX idx_ingestion_profile_model ON ingestion_profiles(model_provider_id);

-- 默认标注配置
INSERT INTO ingestion_profiles (id, name, description, profile_type, batch_size, concurrent_requests, max_retries, retry_delay, save_interval, annotation_depth, included_tag_categories, is_default) VALUES
('annotation_default', '默认标注配置', '标准四层标签全量标注', 'annotation', 10, 1, 3, 1000, 50, 'full', '["sentence_type","emotion","tone","character_type","context_dye","metaphor_category"]', 1);

-- 默认向量化配置
INSERT INTO ingestion_profiles (id, name, description, profile_type, batch_size, concurrent_requests, max_retries, retry_delay, is_default) VALUES
('vectorization_default', '默认向量化配置', '标准向量化入库配置', 'vectorization', 50, 2, 3, 500, 1);

-- ============================================================
-- 第十部分：标注策略与提示词
-- ============================================================

CREATE TABLE annotation_strategies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    applicable_scenes TEXT,
    annotation_depth TEXT,
    included_tag_categories TEXT,
    llm_model_id TEXT,
    batch_size INTEGER DEFAULT 10,
    concurrent_requests INTEGER DEFAULT 3,
    is_default BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO annotation_strategies (id, name, description, annotation_depth, included_tag_categories, batch_size, is_default) VALUES
('quick', '快速标注', '仅标注基础标签，适合初期快速入库', 'quick', '["sentence_type", "emotion", "tone"]', 50, 0),
('standard', '标准标注', '标注基础+潜台词，适合日常使用', 'standard', '["sentence_type", "emotion", "tone", "character_type", "context_dye", "subtext_type", "social_function", "is_meme"]', 20, 1),
('deep', '深度标注', '全维度标注，适合标志性台词深度分析', 'deep', '["sentence_type", "emotion", "tone", "character_type", "scene_type", "speech_style", "context_dye", "subtext_type", "social_function", "dramatic_function", "power_dynamic", "metaphor_category", "semantic_field"]', 10, 0);

CREATE TABLE annotation_prompt_templates (
    id TEXT PRIMARY KEY,
    strategy_id TEXT,
    template_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    prompt_text TEXT NOT NULL,
    variables TEXT,
    output_schema TEXT,
    compatible_models TEXT,
    version TEXT DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES annotation_strategies(id) ON DELETE SET NULL
);

CREATE INDEX idx_prompt_strategy ON annotation_prompt_templates(strategy_id);

INSERT INTO annotation_prompt_templates (id, template_type, name, description, prompt_text) VALUES
('system_standard', 'system', '标准标注系统提示', '标准四层标签标注', 
'你是一位专业的影视台词分析专家。请对以下台词进行多维度语义标注。
分析维度：句型、情绪、语气、角色类型、隐喻、语境
输出JSON格式'),
('user_single', 'user', '单句标注模板', '标注单句台词',
'请分析以下台词："{{line_text}}"
说话人：{{character_name}}
请按系统提示的维度进行分析，输出JSON结果。');

CREATE TABLE annotation_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_template_id TEXT,
    input_text TEXT NOT NULL,
    input_context TEXT,
    expected_output TEXT NOT NULL,
    explanation TEXT,
    category TEXT,
    difficulty TEXT DEFAULT 'medium',
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (prompt_template_id) REFERENCES annotation_prompt_templates(id) ON DELETE CASCADE
);

-- ============================================================
-- 第十部分：应用设置与日志
-- ============================================================

CREATE TABLE app_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type TEXT DEFAULT 'string',
    category TEXT,
    display_name TEXT,
    description TEXT,
    default_value TEXT,
    is_editable BOOLEAN DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_settings_category ON app_settings(category);

INSERT INTO app_settings (setting_key, setting_value, setting_type, category, display_name, default_value) VALUES
('app.language', 'zh-CN', 'string', 'general', '界面语言', 'zh-CN'),
('app.theme', 'dark', 'string', 'general', '主题', 'dark'),
('annotation.default_strategy', 'standard', 'string', 'annotation', '默认标注策略', 'standard'),
('llm.default_model', 'ollama-qwen', 'string', 'llm', '默认模型', 'ollama-qwen'),
('llm.timeout', '60', 'number', 'llm', '请求超时', '60'),
('canvas.grid_size', '20', 'number', 'canvas', '网格大小', '20'),
('export.default_format', 'mp4', 'string', 'export', '默认格式', 'mp4');

CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    session_id TEXT,
    operation_type TEXT,
    resource_type TEXT,
    resource_id TEXT,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_logs_user ON operation_logs(user_id);
CREATE INDEX idx_logs_type ON operation_logs(operation_type);
CREATE INDEX idx_logs_time ON operation_logs(created_at);

CREATE TABLE usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stat_date DATE NOT NULL,
    stat_category TEXT,
    stat_name TEXT,
    stat_value INTEGER,
    UNIQUE(stat_date, stat_category, stat_name)
);

-- ============================================================
-- 初始化完成标记
-- ============================================================

INSERT INTO system_config (key, value, description) VALUES
('config_schema_version', '1.0.0', '配置表结构版本'),
('initialized_at', datetime('now'), '数据库初始化时间');
