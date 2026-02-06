-- ============================================
-- CineGraph AI 数据库架构
-- 支持：影片管理、语义标注、无限画布
-- ============================================

-- 影片表
CREATE TABLE IF NOT EXISTS movies (
    id TEXT PRIMARY KEY,                    -- douban_id 或 custom_xxx
    title TEXT NOT NULL,
    media_type TEXT CHECK (media_type IN ('movie', 'tv')),
    folder TEXT,
    poster_url TEXT,
    local_poster TEXT,
    
    -- 豆瓣元数据
    director TEXT,
    writer TEXT,
    starring TEXT,                          -- JSON 数组
    genre TEXT,
    country TEXT,
    language TEXT,
    release_date TEXT,
    douban_url TEXT,
    rating TEXT,
    
    -- 状态
    status TEXT DEFAULT 'pending',          -- pending, ready
    status_annotate TEXT DEFAULT 'pending', -- pending, partial, done
    status_vectorize TEXT DEFAULT 'pending',-- pending, partial, done
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 剧集表
CREATE TABLE IF NOT EXISTS episodes (
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

-- 标注数据表（按行存储，便于查询和更新）
CREATE TABLE IF NOT EXISTS annotations (
    id TEXT PRIMARY KEY,                    -- {media_id}_ep{N}_line_{idx}
    media_id TEXT NOT NULL,                 -- 影片ID
    episode_number INTEGER,                 -- NULL表示电影
    line_index INTEGER NOT NULL,            -- 在剧集中的行号
    
    -- 台词信息
    text TEXT NOT NULL,                     -- 原始台词
    vector_text TEXT,                       -- 用于向量化的文本
    start REAL,                             -- 开始时间（秒）
    "end" REAL,                             -- 结束时间（秒）
    duration REAL,
    
    -- 混剪标签（JSON存储，灵活扩展）
    mashup_tags TEXT,                       -- JSON: {sentence_type, emotion, tone, ...}
    
    -- 语义摘要
    semantic_summary TEXT,
    
    -- 向量化状态
    vectorized BOOLEAN DEFAULT 0,           -- 是否已入向量库
    vector_id TEXT,                         -- ChromaDB中的ID
    
    annotated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (media_id) REFERENCES movies(id) ON DELETE CASCADE
);

-- 标注表索引
CREATE INDEX IF NOT EXISTS idx_annotations_media ON annotations(media_id, episode_number);
CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations(json_extract(mashup_tags, '$.sentence_type'));
CREATE INDEX IF NOT EXISTS idx_annotations_emotion ON annotations(json_extract(mashup_tags, '$.emotion'));

-- ============================================
-- 无限画布模块（树形结构）
-- ============================================

-- 画布表
CREATE TABLE IF NOT EXISTS canvases (
    id TEXT PRIMARY KEY,                    -- 画布唯一ID
    name TEXT NOT NULL,
    description TEXT,
    created_by TEXT,                        -- 创建者
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT                           -- JSON: 额外配置
);

-- 画布节点表（树形结构）
CREATE TABLE IF NOT EXISTS canvas_nodes (
    id TEXT PRIMARY KEY,                    -- 节点ID
    canvas_id TEXT NOT NULL,
    parent_id TEXT,                         -- NULL表示根节点
    
    -- 节点类型
    node_type TEXT CHECK (node_type IN (
        'root',             -- 根节点
        'scene',            -- 场景/幕
        'clip',             -- 片段（引用annotations）
        'transition',       -- 转场
        'effect',           -- 特效节点
        'note'              -- 备注
    )),
    
    -- 节点内容
    title TEXT,
    content TEXT,                           -- 详细内容/备注
    annotation_id TEXT,                     -- 关联的标注ID（clip类型）
    
    -- 树形结构
    "order" INTEGER DEFAULT 0,              -- 同层级排序
    path TEXT,                              -- 物化路径（便于查询）
    depth INTEGER DEFAULT 0,                -- 节点深度（便于查询）
    
    -- 视觉属性（画布上的位置）
    pos_x REAL,
    pos_y REAL,
    width REAL,
    height REAL,
    color TEXT,
    
    -- 状态
    collapsed BOOLEAN DEFAULT 0,            -- 是否折叠
    locked BOOLEAN DEFAULT 0,               -- 是否锁定
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (canvas_id) REFERENCES canvases(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES canvas_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (annotation_id) REFERENCES annotations(id) ON DELETE SET NULL
);

-- 树形结构索引
CREATE INDEX IF NOT EXISTS idx_nodes_canvas ON canvas_nodes(canvas_id);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON canvas_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_path ON canvas_nodes(path);

-- 节点连接表（用于非父子关系的连接，如转场线）
CREATE TABLE IF NOT EXISTS canvas_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canvas_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    edge_type TEXT DEFAULT 'default',       -- default, transition, effect
    label TEXT,
    metadata TEXT,                          -- JSON
    
    FOREIGN KEY (canvas_id) REFERENCES canvases(id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES canvas_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES canvas_nodes(id) ON DELETE CASCADE
);

-- ============================================
-- 系统配置表
-- ============================================

CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化版本号
INSERT OR IGNORE INTO system_config (key, value, description) 
VALUES ('db_version', '1.0.0', '数据库版本');
