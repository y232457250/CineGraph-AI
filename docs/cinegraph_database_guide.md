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

### 数据库位置说明

项目中有两个数据库文件，用途不同：

| 路径 | 用途 | 说明 |
|------|------|------|
| `data/cinegraph.db` | 开发/测试用 | 项目根目录下的空数据库模板，仅包含标签定义等配置数据 |
| `backend/data/cinegraph.db` | **生产环境用** | 后端实际使用的数据库，包含影片、台词等实际业务数据 |

> **重要**: 您的实际数据（影片、台词）存储在 `backend/data/cinegraph.db` 中。初始化新环境时，只需初始化后端数据库即可。

### 创建数据库

```bash
# 初始化根目录数据库（仅标签配置）
sqlite3 data/cinegraph.db < docs/cinegraph_database_schema.sql

# 初始化后端数据库（生产环境）
cd backend
python scripts/init_database.py
```

### 验证安装

```bash
# 查看所有表
sqlite3 data/cinegraph.db ".tables"

# 查看表结构
sqlite3 data/cinegraph.db ".schema lines"

# 查看标签定义数量
sqlite3 data/cinegraph.db "SELECT category_id, COUNT(*) FROM tag_definitions GROUP BY category_id"
```

---

## 数据库架构概览

### 九大模块，36个表

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
│  7️⃣ LLM集成与模型管理                                                         │
│     model_providers, ingestion_profiles                                      │
│     llm_chat_sessions, llm_chat_messages, semantic_matches, creative_paths  │
│                                                                              │
│  8️⃣ 标注与提示词配置                                                           │
│     annotation_strategies, annotation_prompt_templates, annotation_examples  │
│     tag_categories, tag_definitions, tag_connection_rules                    │
│     tag_hierarchy, tag_constraints, tag_localization, culture_specific_tags  │
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

### 7. LLM集成与入库配置

#### `model_providers` - 模型提供者配置（统一管理LLM和Embedding）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 模型ID，如"ollama_qwen3_4b" |
| name | TEXT | 显示名称 |
| category | TEXT | 用途:llm/embedding |
| provider_type | TEXT | 类型:local/commercial |
| local_mode | TEXT | 本地模式:ollama/docker/空 |
| base_url | TEXT | API地址 |
| model | TEXT | 模型名称 |
| api_key | TEXT | 密钥（支持${ENV}引用） |
| max_tokens | INTEGER | 最大token数 |
| temperature | REAL | 温度参数 |
| timeout | INTEGER | 超时秒数 |
| dimension | INTEGER | 向量维度（Embedding专用） |
| api_style | TEXT | API风格:openai/ollama |
| description | TEXT | 描述 |
| price_info | TEXT | 价格信息 |
| is_active | BOOLEAN | 是否为当前激活 |
| is_default | BOOLEAN | 是否为系统预置 |
| enabled | BOOLEAN | 是否启用 |
| sort_order | INTEGER | 排序权重 |
| extra_config | TEXT(JSON) | 扩展配置 |

> 💡 向后兼容：系统提供 `llm_model_configs` 视图，映射到 `model_providers` 表的 LLM 类别记录

#### `ingestion_profiles` - 入库配置（语义标注 & 向量化参数）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 配置ID |
| name | TEXT | 配置名称 |
| profile_type | TEXT | annotation/vectorization |
| model_provider_id | TEXT | 关联的模型提供者 |
| batch_size | INTEGER | 批处理大小 |
| concurrent_requests | INTEGER | 并发请求数 |
| max_retries | INTEGER | 最大重试次数 |
| retry_delay | INTEGER | 重试延迟(ms) |
| timeout | INTEGER | 超时时间(s) |
| save_interval | INTEGER | 保存间隔(标注专用) |
| annotation_depth | TEXT | 标注深度:full/quick/custom |
| included_tag_categories | TEXT(JSON) | 启用的标签类别 |
| chunk_overlap | INTEGER | 向量块重叠(向量化专用) |
| normalize_embeddings | BOOLEAN | 是否归一化向量 |
| is_default | BOOLEAN | 是否为默认配置 |
| is_active | BOOLEAN | 是否启用 |
| extra_config | TEXT(JSON) | 扩展配置 |

> 💡 `ingestion_profiles` 通过 `model_provider_id` 关联 `model_providers` 表，用户可在入库管理界面选择不同模型和参数组合

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

> 包含13个类别：sentence_type, emotion, tone, character_type, scene_type, speech_style, context_dye, subtext_type, social_function, dramatic_function, power_dynamic, metaphor_category, semantic_field

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
| importance_score | REAL | 标签重要性 0-1 |
| rarity_score | REAL | 稀有度 0-1 |
| cultural_context | TEXT | 文化背景提示 |
| genre_specificity | TEXT | 类型适用性 |
| is_builtin | BOOLEAN | 是否内置 |

#### `tag_connection_rules` - 标签衔接规则
| 字段 | 类型 | 说明 |
|------|------|------|
| from_tag_id | TEXT | 源标签 |
| to_tag_id | TEXT | 目标标签 |
| connection_type | TEXT | continuation/contrast/escalation/cause_effect/correlation/character_typical |
| weight | REAL | 权重 0-1 |

> 包含55+条规则：句型衔接、句型→情绪因果、情绪关联、角色典型行为、语气→情绪、语境→潜台词、社交功能→潜台词、语义场→隐喻、场景→情绪、戏剧功能、权力动态

#### `tag_hierarchy` - 标签层级关系（新增）
| 字段 | 类型 | 说明 |
|------|------|------|
| parent_tag_id | TEXT | 父标签ID |
| child_tag_id | TEXT | 子标签ID |
| relation_type | TEXT | is_a/part_of/related_to |
| weight | REAL | 关系权重 |

#### `tag_constraints` - 标签约束规则（新增）
| 字段 | 类型 | 说明 |
|------|------|------|
| category_id | TEXT | 标签类别 |
| constraint_type | TEXT | mutual_exclusive/requires/excludes/co_occurs |
| tag_ids | TEXT(JSON) | 涉及的标签ID数组 |
| constraint_message | TEXT | 约束说明 |

#### `tag_localization` - 标签多语言（新增）
| 字段 | 类型 | 说明 |
|------|------|------|
| tag_id | TEXT | 标签ID |
| language_code | TEXT | 语言代码(zh-CN/en-US/ja-JP) |
| display_name | TEXT | 本地化名称 |
| cultural_note | TEXT | 文化差异说明 |

#### `culture_specific_tags` - 文化特定标签（新增）
| 字段 | 类型 | 说明 |
|------|------|------|
| tag_id | TEXT | 关联标签 |
| culture_code | TEXT | 文化代码 |
| specific_meaning | TEXT | 特定含义 |
| example_lines | TEXT(JSON) | 示例台词 |

---

### 9. 标注配置表

#### `annotation_strategies` - 标注策略
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PRIMARY KEY | 策略ID |
| name | TEXT | 策略名称 |
| annotation_depth | TEXT | deep/standard/quick |
| included_tag_categories | TEXT(JSON) | 包含的标签类别 |
| llm_model_id | TEXT | 使用的模型 |
| batch_size | INTEGER | 批处理大小 |

> 预设三种策略：
> - **quick（快速标注）**：仅 sentence_type/emotion/tone，batch_size=50
> - **standard（标准标注）**：基础+潜台词共8类，batch_size=20（默认）
> - **deep（深度标注）**：全13类标签，batch_size=10

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
│       │                        │                                     │        │
│       │                        ├──► (*) tag_hierarchy (parent/child) │        │
│       │                        ├──► (*) tag_localization             │        │
│       │                        └──► (*) culture_specific_tags        │        │
│       └──► (*) tag_constraints                                       │        │
│                                                                      │        │
│  model_providers ──► annotation_strategies ──► annotation_prompt_   │templates │
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
| tag_categories | tag_constraints | 1:N | category_id | CASCADE |
| tag_definitions | tag_hierarchy | 1:N | parent_tag_id | CASCADE |
| tag_definitions | tag_localization | 1:N | tag_id | CASCADE |
| tag_definitions | culture_specific_tags | 1:N | tag_id | CASCADE |

---

## 配置表使用指南

### 1. 配置LLM模型

#### 预设模型列表

数据库已预置 **30个LLM模型** 和 **12个Embedding模型**：

**LLM模型分类：**

| 类别 | 数量 | 模型 |
|------|------|------|
| **Ollama本地** | 10 | Qwen3:4B/8B, Qwen2.5:7B/14B/32B, Llama3.1:8B/70B, DeepSeek-Coder:33B, Phi-4, Gemma2:9B |
| **Ollama云端** | 2 | DeepSeek-V3.1:671B, Qwen3-VL:235B |
| **DeepSeek** | 3 | DeepSeek-V3, DeepSeek-V2, DeepSeek-Coder-V2 |
| **阿里云** | 3 | 通义千问Turbo/Plus/Max |
| **硅基流动** | 4 | Qwen3-8B, Qwen2.5-72B, DeepSeek-V2.5, Thoughtful-Star |
| **OpenAI** | 3 | GPT-4o, GPT-4o-mini, GPT-3.5-Turbo |
| **Moonshot** | 2 | Kimi-K1, Kimi-Lite |
| **智谱AI** | 2 | GLM-4, GLM-4-Flash |
| **百度** | 2 | ERNIE-Bot-4, ERNIE-Speed |

**Embedding模型分类：**

| 类别 | 数量 | 模型 |
|------|------|------|
| **Ollama本地** | 4 | Qwen3-Embed, Nomic-Embed, MXBAI-Embed, BGE-Large |
| **硅基流动** | 3 | BGE-M3, BGE-Large-ZH, BCE-Embedding |
| **阿里云** | 2 | text-embedding-v3, text-embedding-v2 |
| **OpenAI** | 2 | text-embedding-3-small, text-embedding-3-large |
| **百度** | 1 | Embedding-V1 |

#### 常用SQL命令

```sql
-- 查看所有模型提供者
SELECT id, name, category, provider_type, model, is_active, enabled 
FROM model_providers ORDER BY category, sort_order;

-- 查看当前激活的LLM
SELECT * FROM model_providers WHERE category = 'llm' AND is_active = 1;

-- 查看当前激活的Embedding
SELECT * FROM model_providers WHERE category = 'embedding' AND is_active = 1;

-- 添加新模型
INSERT INTO model_providers (
    id, name, category, provider_type, local_mode,
    base_url, model, max_tokens, temperature, timeout,
    description, price_info, is_default, sort_order, enabled
) VALUES (
    'my-ollama', '我的本地模型', 'llm', 'local', 'ollama',
    'http://localhost:11434/v1', 'qwen2.5:14b',
    2000, 0.7, 120,
    '通过Ollama运行的本地模型', '免费', 0, 100, 1
);

-- 激活指定模型
UPDATE model_providers SET is_active = 0 WHERE category = 'llm';
UPDATE model_providers SET is_active = 1 WHERE id = 'my-ollama';

-- 向后兼容查询（通过视图）
SELECT * FROM llm_model_configs;
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
| 总表数 | 39个（含4个新增标签表） |
| 核心模块 | 10个 |
| 配置表 | 14个（完全可编辑） |
| 索引数 | 65+ |
| 视图 | 1个（llm_model_configs兼容视图） |
| 预置LLM模型 | 30个 |
| 预置Embedding模型 | 12个 |
| 标签定义 | 131个 |

### 核心特性

1. **可编辑标签体系** - 通过 `tag_categories` + `tag_definitions` 管理，含13类标签、131个标签定义
2. **标签层级与约束** - `tag_hierarchy` 支持父子关系，`tag_constraints` 支持互斥/依赖规则
3. **标签国际化** - `tag_localization` 支持多语言，`culture_specific_tags` 支持文化特定含义
4. **统一模型管理** - 通过 `model_providers` 统一管理LLM(11个)和Embedding(5个)，支持本地/云端/商用API，预置模型可删除（每类至少保留1个），支持一键重置
5. **提示词模板化** - 通过 `annotation_prompt_templates` 管理
6. **完整对话记录** - `llm_chat_sessions` + `llm_chat_messages`
7. **语义关联追踪** - `semantic_matches` 记录匹配过程

### 文件清单

| 文件 | 用途 |
|------|------|
| `cinegraph_database_schema.sql` | 完整的数据库创建SQL |
| `cinegraph_database_guide.md` | 本说明文档 |

---

*文档版本: 2.1.0*  
*最后更新: 2026-02-08*  
*变更: 补全所有13类tag_definitions默认数据(tone/character_type/context_dye/subtext_type/social_function/semantic_field)，新增deep标注策略，扩充tag_connection_rules/tag_hierarchy/tag_constraints/tag_localization/culture_specific_tags默认数据*
