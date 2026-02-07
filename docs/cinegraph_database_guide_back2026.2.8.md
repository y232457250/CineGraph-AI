# CineGraph-AI 数据库设计与使用指南

> 完整的数据库架构文档，包含表结构说明、ER图和使用指南

---

## 📋 目录

1. [快速开始](#快速开始)
2. [数据库架构概览](#数据库架构概览)
3. [表结构详解](#表结构详解)
4. [ER图与关系](#er图与关系)
5. [配置表使用指南](#配置表使用指南)
6. [常用查询示例](#常用查询示例)

---

## 快速开始

### 创建数据库

```bash
sqlite3 cinegraph.db < cinegraph_database_schema.sql
```

### 验证安装

```bash
sqlite3 cinegraph.db ".tables"
sqlite3 cinegraph.db ".schema lines"
```

---

## 数据库架构概览

### 九大模块，35个表

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CineGraph-AI 数据库架构                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1️⃣ 系统配置层                                                                │
│     system_config, app_settings                                              │
│                                                                              │
│  2️⃣ 用户与权限                                                               │
│     users, user_sessions                                                     │
│                                                                              │
│  3️⃣ 影片入库                                                                 │
│     movies, episodes                                                         │
│                                                                              │
│  4️⃣ 语义标注（核心）                                                          │
│     lines, characters, vectorization_queue                                   │
│     ├─ 基础标签：sentence_type, emotion, tone, character_type               │
│     ├─ 潜台词：context_dye, subtext_type, social_function                   │
│     └─ 隐喻：metaphor_category, semantic_field                              │
│                                                                              │
│  5️⃣ 搜索与向量化                                                              │
│     search_history                                                           │
│                                                                              │
│  6️⃣ 无限画布                                                                  │
│     projects, canvas_nodes, canvas_edges, sequences, sequence_items          │
│                                                                              │
│  7️⃣ LLM集成                                                                  │
│     llm_model_configs, annotation_strategies, annotation_prompt_templates    │
│     llm_chat_sessions, llm_chat_messages, semantic_matches, creative_paths  │
│                                                                              │
│  8️⃣ 配置体系                                                                  │
│     tag_categories, tag_definitions, tag_connection_rules                    │
│     annotation_examples                                                      │
│                                                                              │
│  9️⃣ 日志统计                                                                  │
│     operation_logs, usage_stats                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 表结构详解

### 1. 系统配置表

#### `system_config` - 系统核心配置
| 字段 | 类型 | 说明 |
|------|------|------|
| key | TEXT PRIMARY KEY | 配置键 |
| value | TEXT | 配置值 |
| description | TEXT | 描述 |
| updated_at | TIMESTAMP | 更新时间 |

#### `app_settings` - 应用设置
| 字段 | 类型 | 说明 |
|------|------|------|
| setting_key | TEXT UNIQUE | 设置键 |
| setting_value | TEXT | 设置值 |
| setting_type | TEXT | 类型:string/number/boolean/json |
| category | TEXT | 分类:general/annotation/llm/canvas/export |

---

### 2. 用户表

#### `users` - 用户主表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID |
| username | TEXT UNIQUE | 用户名 |
| email | TEXT UNIQUE | 邮箱 |
| password_hash | TEXT | 密码哈希 |
| preferences | TEXT(JSON) | 用户偏好 |

#### `user_sessions` - 会话管理
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | Session UUID |
| user_id | TEXT | 用户ID |
| token | TEXT UNIQUE | 会话令牌 |
| expires_at | TIMESTAMP | 过期时间 |

---

### 3. 影片入库表

#### `movies` - 影片主表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 豆瓣ID或custom_xxx |
| title | TEXT | 影片名称 |
| media_type | TEXT | movie/tv/animation |
| folder | TEXT | 文件夹名称 |
| poster_url | TEXT | 豆瓣海报URL |
| local_poster | TEXT | 本地海报路径 |
| director | TEXT | 导演 |
| starring | TEXT(JSON) | 演员列表 |
| status_annotate | TEXT | pending/processing/done |
| status_vectorize | TEXT | pending/processing/done |

#### `episodes` - 剧集表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY | 自增ID |
| movie_id | TEXT | 所属影片 |
| episode_number | INTEGER | 集数 |
| video_path | TEXT | 视频路径 |
| subtitle_path | TEXT | 字幕路径 |

---

### 4. 语义标注表（核心）

#### `lines` - 台词主表（25+字段）

**基础信息字段**
| 字段 | 类型 | 说明 |
|------|------|------|
| line_id | TEXT UNIQUE | 唯一ID |
| movie_id | TEXT | 所属影片 |
| episode_number | INTEGER | 集数 |
| text | TEXT | 原始台词 |
| vector_text | TEXT | 向量化文本 |
| start_time | REAL | 开始时间(秒) |
| character_name | TEXT | 角色名 |

**第一层：基础标签**
| 字段 | 类型 | 说明 |
|------|------|------|
| sentence_type | TEXT | 句型:question/answer/threat/mock/... |
| emotion | TEXT | 情绪:angry/funny/fear/... |
| tone | TEXT | 语气:strong/weak/provocative/... |
| character_type | TEXT | 角色类型:hero/villain/comic/... |
| can_follow | TEXT(JSON) | 可接在哪些标签后 |
| can_lead_to | TEXT(JSON) | 后可接哪些标签 |

**第二层：潜台词**
| 字段 | 类型 | 说明 |
|------|------|------|
| context_dye | TEXT | 语境染色:infidelity/absurd/taboo/... |
| subtext_type | TEXT | 隐含语义:irony/sarcasm/metaphor/... |
| is_meme | BOOLEAN | 是否网络梗 |
| meme_name | TEXT | 梗名称 |
| social_function | TEXT | 社交功能:roast/showoff/sympathy/... |
| surface_sentiment | TEXT | 表面情感 |
| actual_sentiment | TEXT | 实际情感 |
| sentiment_polarity | TEXT | consistent/ironic/mixed |

**第三层：隐喻分析**
| 字段 | 类型 | 说明 |
|------|------|------|
| metaphor_category | TEXT | 隐喻类别:eat/hard/space/wear/... |
| metaphor_keyword | TEXT | 关键词:饿/吃/硬/软/... |
| metaphor_direction | TEXT | 方向:desire/risk/ability/... |
| semantic_field | TEXT | 语义场:desperation/power_struggle/... |

**算法与状态字段**
| 字段 | 类型 | 说明 |
|------|------|------|
| intensity | INTEGER | 冲突强度 1-10 |
| hook_score | REAL | 吸引力 0-1 |
| ambiguity | REAL | 出处模糊度 0-1 |
| viral_potential | REAL | 爆梗潜力 0-1 |
| tags_json | TEXT(JSON) | 扩展字段 |
| vectorized | BOOLEAN | 是否已向量化 |
| vector_id | TEXT | ChromaDB ID |
| is_signature | BOOLEAN | 是否标志性台词 |

#### `characters` - 角色规范化
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PRIMARY KEY | 自增ID |
| movie_id | TEXT | 所属影片 |
| name | TEXT | 角色名 |
| normalized_name | TEXT | 规范化名称 |
| character_type | TEXT | 角色类型 |

---

### 5. 向量化与搜索表

#### `vectorization_queue` - 向量化任务队列
| 字段 | 类型 | 说明 |
|------|------|------|
| line_id | TEXT | 待向量化的台词 |
| status | TEXT | pending/processing/done/failed |
| priority | INTEGER | 优先级 1-10 |
| attempts | INTEGER | 重试次数 |

#### `search_history` - 搜索历史
| 字段 | 类型 | 说明 |
|------|------|------|
| search_mode | TEXT | literal/metaphor/mixed |
| search_conditions | TEXT(JSON) | 完整搜索条件 |
| result_count | INTEGER | 结果数量 |
| selected_line_id | TEXT | 用户选择的台词 |

---

### 6. 无限画布表

#### `projects` - 画布项目
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID |
| name | TEXT | 项目名称 |
| description | TEXT | 描述 |
| owner_id | TEXT | 创建者 |
| theme | TEXT | 主题 |
| style | TEXT | absurd/emotional/suspense/comedy |
| viewport_x/y/zoom | REAL | 画布视口位置 |
| total_duration | REAL | 总时长 |
| target_duration | REAL | 目标时长（抖音29秒） |
| status | TEXT | draft/editing/review/final |

#### `canvas_nodes` - 画布节点
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID |
| project_id | TEXT | 所属项目 |
| parent_id | TEXT | 父节点（树形结构） |
| line_id | TEXT | 关联台词（核心关联） |
| node_type | TEXT | root/scene/clip/transition/note |
| pos_x/y | REAL | 位置坐标 |
| width/height | REAL | 大小 |
| trim_start/end | REAL | 剪辑参数 |
| association_source | TEXT | manual/llm_suggestion/search |
| association_confidence | REAL | 关联置信度 |

#### `canvas_edges` - 画布连线
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | UUID |
| project_id | TEXT | 所属项目 |
| source_id | TEXT | 源节点 |
| target_id | TEXT | 目标节点 |
| relation_type | TEXT | continuation/contrast/escalation |
| relation_strength | REAL | 关联强度 0-1 |

#### `sequences` + `sequence_items` - 时间轴
| 字段 | 类型 | 说明 |
|------|------|------|
| project_id | TEXT | 所属项目 |
| name | TEXT | 序列名称 |
| node_id | TEXT | 引用的节点 |
| item_order | INTEGER | 顺序 |
| transition_type | TEXT | cut/fade/dissolve |

---

### 7. LLM集成表

#### `llm_model_configs` - LLM模型配置
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 模型ID |
| provider_type | TEXT | openai/ollama/azure/... |
| base_url | TEXT | API地址 |
| api_key | TEXT | 密钥（加密） |
| model_name | TEXT | 模型名称 |
| temperature | REAL | 温度参数 |
| max_tokens | INTEGER | 最大token数 |
| supported_tasks | TEXT(JSON) | 支持的任务类型 |
| is_default | BOOLEAN | 是否默认 |

#### `llm_chat_sessions` + `llm_chat_messages` - 对话记录
| 字段 | 类型 | 说明 |
|------|------|------|
| model_id | TEXT | 使用的模型 |
| role | TEXT | system/user/assistant |
| content | TEXT | 消息内容 |
| parsed_data | TEXT(JSON) | 解析后的结构化数据 |
| referenced_line_ids | TEXT(JSON) | 引用的台词ID |

#### `semantic_matches` - 语义匹配结果
| 字段 | 类型 | 说明 |
|------|------|------|
| interaction_id | TEXT | 关联的LLM交互 |
| line_id | TEXT | 匹配的台词 |
| match_scores | TEXT(JSON) | 各维度匹配分数 |
| overall_score | REAL | 综合分数 |
| match_reason | TEXT | 匹配理由 |
| is_selected | BOOLEAN | 用户是否选择 |

#### `creative_paths` - AI创作路径
| 字段 | 类型 | 说明 |
|------|------|------|
| project_id | TEXT | 所属项目 |
| path_data | TEXT(JSON) | 完整路径数据 |
| status | TEXT | draft/applied/discarded |

---

### 8. 标签配置表

#### `tag_categories` - 标签类别
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 类别ID |
| name | TEXT | 显示名称 |
| layer | INTEGER | 层级:1基础 2潜台词 3隐喻 |
| is_editable | BOOLEAN | 是否可编辑 |
| is_required | BOOLEAN | 是否必填 |

#### `tag_definitions` - 标签定义（可编辑）
| 字段 | 类型 | 说明 |
|------|------|------|
| category_id | TEXT | 所属类别 |
| value | TEXT | 标签值 |
| display_name | TEXT | 显示名称 |
| color | TEXT | 颜色 |
| can_follow | TEXT(JSON) | 后可接标签 |
| can_lead_to | TEXT(JSON) | 前可接标签 |
| llm_hints | TEXT | LLM识别提示 |
| example_phrases | TEXT(JSON) | 示例短语 |
| is_builtin | BOOLEAN | 是否内置 |

#### `tag_connection_rules` - 标签衔接规则
| 字段 | 类型 | 说明 |
|------|------|------|
| from_tag_id | TEXT | 源标签 |
| to_tag_id | TEXT | 目标标签 |
| connection_type | TEXT | continuation/contrast/escalation/shift |
| weight | REAL | 权重 0-1 |

---

### 9. 标注配置表

#### `annotation_strategies` - 标注策略
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 策略ID |
| name | TEXT | 策略名称 |
| annotation_depth | TEXT | full/standard/quick |
| included_tag_categories | TEXT(JSON) | 包含的标签类别 |
| llm_model_id | TEXT | 使用的模型 |
| batch_size | INTEGER | 批处理大小 |

#### `annotation_prompt_templates` - 提示词模板
| 字段 | 类型 | 说明 |
|------|------|------|
| strategy_id | TEXT | 关联策略 |
| template_type | TEXT | system/user/few_shot |
| name | TEXT | 模板名称 |
| prompt_text | TEXT | 提示词内容 |
| variables | TEXT(JSON) | 变量定义 |
| output_schema | TEXT(JSON) | 输出格式Schema |

#### `annotation_examples` - few-shot示例
| 字段 | 类型 | 说明 |
|------|------|------|
| prompt_template_id | TEXT | 关联模板 |
| input_text | TEXT | 输入台词 |
| expected_output | TEXT(JSON) | 期望输出 |
| explanation | TEXT | 解释说明 |

---

### 10. 日志统计表

#### `operation_logs` - 操作日志
| 字段 | 类型 | 说明 |
|------|------|------|
| operation_type | TEXT | import/annotate/vectorize/... |
| resource_type | TEXT | movie/line/project/... |
| resource_id | TEXT | 资源ID |
| details | TEXT(JSON) | 详情 |

---

## ER图与关系

### 整体关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              表关系全景图                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  users (1) ────────► (*) projects ◄──────── (*) llm_chat_sessions          │
│       │                 │                         │                          │
│       │                 │                         └──► (*) llm_chat_messages│
│       │                 │                                                    │
│       │                 ├──► (*) canvas_nodes ◄────► (0..1) lines           │
│       │                 │      │                                            │
│       │                 │      ├──► (*) canvas_edges                        │
│       │                 │      │                                            │
│       │                 │      └──► (*) sequences ◄──► (*) sequence_items   │
│       │                 │                                                   │
│       │                 └──► (*) creative_paths                             │
│       │                                                                      │
│       └──► (*) search_history ──► (*) semantic_matches ──► lines           │
│                                                                              │
│  movies (1) ────────► (*) episodes                                          │
│       │                                                                      │
│       ├──► (*) lines ◄─────────────────────────────────────────────┐        │
│       │      │                                                      │        │
│       │      ├──► (*) vectorization_queue                           │        │
│       │      │                                                      │        │
│       │      └──► (*) semantic_matches (via line_id)                │        │
│       │                                                             │        │
│       └──► (*) characters                                           │        │
│                                                                      │        │
│  tag_categories (1) ──► (*) tag_definitions ──► (*) tag_connection_│rules    │
│                                                                      │        │
│  llm_model_configs ──► annotation_strategies ──► annotation_prompt_│templates │
│                                                    │                 │        │
│                                                    └──► annotation_│examples   │
│                                                                              │
│  app_settings (独立配置表)                                                    │
│  system_config (独立配置表)                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 核心关系说明

| 主表 | 从表 | 关系 | 外键 | 级联 |
|------|------|------|------|------|
| movies | episodes | 1:N | movie_id | CASCADE |
| movies | lines | 1:N | movie_id | CASCADE |
| movies | characters | 1:N | movie_id | CASCADE |
| projects | canvas_nodes | 1:N | project_id | CASCADE |
| projects | canvas_edges | 1:N | project_id | CASCADE |
| projects | sequences | 1:N | project_id | CASCADE |
| canvas_nodes | canvas_nodes | 1:N | parent_id | CASCADE |
| canvas_nodes | lines | N:1 | line_id | SET NULL |
| canvas_nodes | canvas_edges | 1:N | source_id | CASCADE |
| sequences | sequence_items | 1:N | sequence_id | CASCADE |
| llm_chat_sessions | llm_chat_messages | 1:N | session_id | CASCADE |
| tag_categories | tag_definitions | 1:N | category_id | CASCADE |

---

## 配置表使用指南

### 1. 配置LLM模型

```sql
-- 查看所有模型
SELECT id, provider_name, model_name, is_default FROM llm_model_configs;

-- 添加新模型
INSERT INTO llm_model_configs (
    id, provider_type, provider_name, base_url, model_name,
    temperature, max_tokens, supported_tasks
) VALUES (
    'my-ollama', 'ollama', '我的本地模型',
    'http://localhost:11434', 'qwen2.5:14b',
    0.7, 2000, '["annotation", "chat"]'
);

-- 设为默认
UPDATE llm_model_configs SET is_default = 0;
UPDATE llm_model_configs SET is_default = 1 WHERE id = 'my-ollama';
```

### 2. 编辑标签体系

```sql
-- 添加新句型标签
INSERT INTO tag_definitions (
    id, category_id, value, display_name, description, color,
    can_follow, can_lead_to, llm_hints, example_phrases
) VALUES (
    'st_praise', 'sentence_type', 'praise', '赞美',
    '夸奖、称赞、表扬', '#f1c40f',
    '["action", "quality"]', '["thanks", "humble", "deny"]',
    '夸奖对方的品质或行为',
    '["你真棒", "干得漂亮", "太厉害了"]',
    0, 10
);

-- 修改标签颜色
UPDATE tag_definitions SET color = '#ff6b6b' WHERE id = 'st_threat';

-- 停用标签
UPDATE tag_definitions SET is_active = 0 WHERE id = 'st_old';
```

### 3. 配置标注策略

```sql
-- 创建自定义策略
INSERT INTO annotation_strategies (
    id, name, description, annotation_depth,
    included_tag_categories, batch_size, llm_model_id
) VALUES (
    'custom', '我的策略', '只标基础标签',
    'quick',
    '["sentence_type", "emotion", "metaphor_category"]',
    15, 'my-ollama'
);
```

### 4. 修改提示词模板

```sql
-- 查看现有模板
SELECT id, name, template_type FROM annotation_prompt_templates;

-- 更新系统提示词
UPDATE annotation_prompt_templates 
SET prompt_text = '你是一位专家。请分析：{{line_text}}'
WHERE id = 'system_standard';
```

### 5. 修改应用设置

```sql
-- 查看所有设置
SELECT setting_key, setting_value, category FROM app_settings;

-- 修改默认模型
UPDATE app_settings 
SET setting_value = 'my-ollama' 
WHERE setting_key = 'llm.default_model';

-- 修改标注置信度阈值
UPDATE app_settings 
SET setting_value = '0.8' 
WHERE setting_key = 'annotation.confidence_threshold';
```

---

## 常用查询示例

### 1. 获取影片完整信息

```sql
SELECT 
    m.*,
    COUNT(DISTINCT e.id) as episode_count,
    COUNT(DISTINCT l.id) as line_count,
    COUNT(DISTINCT CASE WHEN l.vectorized = 1 THEN l.id END) as vectorized_count
FROM movies m
LEFT JOIN episodes e ON m.id = e.movie_id
LEFT JOIN lines l ON m.id = l.movie_id
WHERE m.id = '影片ID'
GROUP BY m.id;
```

### 2. 语义搜索（混合模式）

```sql
SELECT 
    l.*,
    m.title as movie_title,
    (CASE WHEN l.emotion = 'angry' THEN 0.3 ELSE 0 END +
     CASE WHEN l.metaphor_category = 'eat' THEN 0.4 ELSE 0 END +
     CASE WHEN l.context_dye = 'infidelity' THEN 0.3 ELSE 0 END) as relevance
FROM lines l
JOIN movies m ON l.movie_id = m.id
WHERE l.emotion = 'angry' OR l.metaphor_category = 'eat'
ORDER BY relevance DESC
LIMIT 50;
```

### 3. 获取画布项目完整数据

```sql
SELECT 
    p.*,
    (SELECT COUNT(*) FROM canvas_nodes WHERE project_id = p.id) as node_count,
    (SELECT COUNT(*) FROM canvas_edges WHERE project_id = p.id) as edge_count
FROM projects p
WHERE p.id = '项目ID';
```

### 4. 基于隐喻找衔接台词

```sql
-- 当前台词是"饿"（欲望），找"吃不下"（风险）的对比
SELECT l.*, ma.*
FROM lines l
JOIN line_metaphor_analysis ma ON l.line_id = ma.line_id
WHERE ma.primary_metaphor_category = 'eat'
  AND ma.primary_metaphor_direction = 'risk'
ORDER BY ma.primary_strength DESC
LIMIT 10;
```

### 5. LLM交互与匹配结果

```sql
SELECT 
    i.request_type,
    i.prompt,
    m.line_id,
    l.text,
    m.overall_score,
    m.match_reason
FROM llm_interactions i
LEFT JOIN semantic_matches m ON i.id = m.interaction_id
LEFT JOIN lines l ON m.line_id = l.line_id
WHERE i.id = '交互ID'
ORDER BY m.overall_score DESC;
```

---

## 总结

### 数据库统计

| 类别 | 数量 |
|------|------|
| 总表数 | 35个 |
| 核心模块 | 9个 |
| 配置表 | 10个（完全可编辑） |
| 索引数 | 60+ |

### 核心特性

1. **可编辑标签体系** - 通过 `tag_categories` + `tag_definitions` 管理
2. **LLM模型自由切换** - 通过 `llm_model_configs` 配置
3. **提示词模板化** - 通过 `annotation_prompt_templates` 管理
4. **完整对话记录** - `llm_chat_sessions` + `llm_chat_messages`
5. **语义关联追踪** - `semantic_matches` 记录匹配过程

### 文件清单

| 文件 | 用途 |
|------|------|
| `cinegraph_database_schema.sql` | 完整的数据库创建SQL |
| `cinegraph_database_guide.md` | 本说明文档 |

---

*文档版本: 1.0.0*  
*最后更新: 2026-02-06*
