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
-- 第七部分：LLM集成与配置
-- ============================================================

CREATE TABLE llm_model_configs (
    id TEXT PRIMARY KEY,
    provider_type TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    base_url TEXT,
    api_key TEXT,
    api_version TEXT,
    model_name TEXT NOT NULL,
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    top_p REAL DEFAULT 1.0,
    frequency_penalty REAL DEFAULT 0,
    presence_penalty REAL DEFAULT 0,
    timeout INTEGER DEFAULT 60,
    max_retries INTEGER DEFAULT 3,
    retry_delay INTEGER DEFAULT 1,
    is_available BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    is_local BOOLEAN DEFAULT 0,
    supported_tasks TEXT,
    input_price_per_1k REAL,
    output_price_per_1k REAL,
    avg_response_time_ms INTEGER,
    success_rate REAL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_llm_provider ON llm_model_configs(provider_type);
CREATE INDEX idx_llm_available ON llm_model_configs(is_available);
CREATE INDEX idx_llm_default ON llm_model_configs(is_default);

INSERT INTO llm_model_configs (id, provider_type, provider_name, base_url, model_name, is_default, supported_tasks, description) VALUES
('ollama-qwen', 'ollama', '本地 Qwen', 'http://localhost:11434', 'qwen2.5:14b', 1, '["annotation", "chat"]', '本地Ollama运行的Qwen模型'),
('openai-gpt4', 'openai', 'OpenAI GPT-4', 'https://api.openai.com/v1', 'gpt-4', 0, '["annotation", "chat", "search"]', 'OpenAI GPT-4'),
('openai-gpt35', 'openai', 'OpenAI GPT-3.5', 'https://api.openai.com/v1', 'gpt-3.5-turbo', 0, '["chat", "code"]', 'OpenAI GPT-3.5');

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
    FOREIGN KEY (model_id) REFERENCES llm_model_configs(id) ON DELETE CASCADE
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
-- 第八部分：标签体系配置
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
('sentence_type', '句型', '决定接话逻辑的句型分类', 1, 1, 1, 1),
('emotion', '情绪', '用于递进和对比的情绪标签', 1, 1, 1, 2),
('tone', '语气', '用于节奏控制的语气标签', 1, 1, 0, 3),
('character_type', '角色类型', '跨剧匹配的角色类型', 1, 1, 0, 4),
('context_dye', '语境染色', '台词带来的整体氛围底色', 2, 1, 0, 10),
('subtext_type', '隐含语义', '潜台词类型', 2, 1, 0, 11),
('social_function', '社交功能', '这句话的社交作用', 2, 1, 0, 12),
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
    can_follow TEXT,
    can_lead_to TEXT,
    related_tags TEXT,
    llm_hints TEXT,
    example_phrases TEXT,
    is_builtin BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES tag_categories(id) ON DELETE CASCADE
);

CREATE INDEX idx_tag_def_category ON tag_definitions(category_id);
CREATE INDEX idx_tag_def_value ON tag_definitions(value);

INSERT INTO tag_definitions (id, category_id, value, display_name, description, is_builtin, sort_order) VALUES
('st_question', 'sentence_type', 'question', '问句', '提出问题，期待回答', 1, 1),
('st_answer', 'sentence_type', 'answer', '答句', '回答问题', 1, 2),
('st_threat', 'sentence_type', 'threat', '威胁', '威胁恐吓对方', 1, 3),
('st_mock', 'sentence_type', 'mock', '嘲讽', '嘲讽讥笑对方', 1, 4),
('st_command', 'sentence_type', 'command', '命令', '命令或指示', 1, 5),
('emo_angry', 'emotion', 'angry', '愤怒', '愤怒、生气', 1, 1),
('emo_funny', 'emotion', 'funny', '搞笑', '幽默、滑稽', 1, 2),
('emo_fear', 'emotion', 'fear', '害怕', '恐惧、害怕', 1, 3),
('emo_sad', 'emotion', 'sad', '悲伤', '悲伤、难过', 1, 4),
('meta_eat', 'metaphor_category', 'eat', '吃/饥饿', '食欲、欲望、占有隐喻', 1, 1),
('meta_hard', 'metaphor_category', 'hard', '硬/软', '实力、性格、性暗示隐喻', 1, 2),
('meta_space', 'metaphor_category', 'space', '进/出', '空间、权力、准入隐喻', 1, 3);

CREATE TABLE tag_connection_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_category_id TEXT NOT NULL,
    from_tag_id TEXT NOT NULL,
    to_category_id TEXT NOT NULL,
    to_tag_id TEXT NOT NULL,
    connection_type TEXT,
    weight REAL DEFAULT 1.0,
    description TEXT,
    condition_text TEXT,
    is_active BOOLEAN DEFAULT 1
);

INSERT INTO tag_connection_rules (from_category_id, from_tag_id, to_category_id, to_tag_id, connection_type, weight, description) VALUES
('sentence_type', 'st_question', 'sentence_type', 'st_answer', 'continuation', 0.9, '问句后接答句'),
('sentence_type', 'st_threat', 'sentence_type', 'st_mock', 'escalation', 0.8, '威胁升级成嘲讽');

-- ============================================================
-- 第九部分：标注配置
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
('standard', '标准标注', '完整的四层标签+隐喻分析', 'full', '["sentence_type", "emotion", "tone", "character_type", "context_dye", "metaphor_category"]', 10, 1),
('quick', '快速标注', '只标注基础标签', 'quick', '["sentence_type", "emotion"]', 20, 0);

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
