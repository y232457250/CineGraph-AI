# CineGraph-AI JSON → SQLite 迁移 - 修改摘要

## 文件修改列表

### 1. 存储层 (`app/core/store/`)

#### `__init__.py` (重写)
- 将默认存储后端从 JSON 改为 SQLite
- 添加 `get_unified_store()` 函数
- 优化导入顺序和错误处理

#### `unified_store.py` (增强)
- 添加 `vectorize_texts()` 方法用于批量向量化
- 增强注释和文档

### 2. 数据模型 (`app/models/`)

#### `database.py` (已存在，基础版本)
- SQLAlchemy ORM 模型定义
- 包含：Movie, Episode, Line, Character, Project, CanvasNode, CanvasEdge, Sequence, SequenceItem, ConnectionRule, SystemConfig
- 支持四层标签体系（句型、情绪、语气、角色）
- 支持抖音算法字段（intensity, hook_score, ambiguity）

### 3. API 路由 (`app/routers/`)

#### `ingest.py` (重写)
- 从 JSON 存储改为使用 `unified_store`
- 更新 `list_movies()` 方法
- 更新 `import_scan_results()` 方法
- 新增 `add_episode()` 和 `update_movie_status()` 端点

#### `library.py` (重写)
- 使用 `unified_store` 进行数据操作
- 更新 `_get_annotation_status()` 支持数据库查询
- 更新 `list_library()` 获取影片列表
- 更新 `get_movie()` 获取单个影片
- 更新 `delete_from_library()` 使用级联删除
- 更新 `delete_episode_from_library()` 删除剧集
- 新增标注数据 API（`get_movie_annotations`, `save_movie_annotations`, `delete_movie_annotations`）

#### `vectorize.py` (重写)
- 支持从数据库读取待向量化数据
- 新增 `get_pending_lines()` 端点
- 支持批量向量化数据库中的台词
- 保留对 JSON 文件的向后兼容

#### `canvas.py` (已存在，使用 unified_store)
- 无限画布 API 路由
- 项目管理、节点管理、连线管理、时间轴序列

#### `annotation.py` (已支持)
- 已更新为同时保存到 JSON 和 SQLite

#### `search.py` (无需修改)
- 使用 Vectorizer 直接搜索，保持不变

### 4. API 模块 (`app/api/`)

#### `settings.py` (重写)
- 从 YAML 文件存储改为数据库存储
- 新增 `SystemConfig` 表操作
- `load_settings_from_db()` - 从数据库加载设置
- `save_settings_to_db()` - 保存设置到数据库
- `init_default_settings()` - 初始化默认设置
- 新增 `/database/stats` 端点获取数据库统计

### 5. 向量化模块 (`app/ingestion/`)

#### `vectorizer.py` (增强)
- 新增 `add_texts()` 方法支持批量向量化

### 6. 脚本 (`scripts/`)

#### `init_database.py` (已存在)
- 数据库初始化脚本

#### `migrate_json_to_sqlite.py` (新增)
- 从 JSON 迁移到 SQLite 的完整迁移脚本
- 备份现有数据
- 迁移影片和标注数据

#### `verify_setup.py` (新增)
- 验证系统设置脚本
- 检查依赖、数据库、存储层、设置模块、画布功能

### 7. 文档

#### `MIGRATION_GUIDE.md` (新增)
- 完整的数据库迁移指南
- 包含迁移步骤、使用说明、故障排除

#### `CHANGES_SUMMARY.md` (本文件)
- 修改摘要

#### `requirements.txt` (更新)
- 添加 SQLAlchemy 依赖
- 整理所有项目依赖

## 数据库表结构

```
movies              - 影片元数据
episodes            - 剧集信息
lines               - 台词/标注数据（核心）
characters          - 角色信息
projects            - 画布项目
canvas_nodes        - 画布节点
canvas_edges        - 画布连线
sequences           - 时间轴序列
sequence_items      - 序列项目
connection_rules    - 接话规则
line_functions      - 混剪功能标签
line_styles         - 风格效果标签
system_config       - 系统设置
```

## 关键接口

### UnifiedStore (推荐)

```python
from app.core.store import get_unified_store

store = get_unified_store()

# 影片
store.list_movies()
store.get_movie(movie_id)
store.save_movie(movie_data)
store.delete_movie(movie_id)

# 标注
store.save_annotations(movie_id, annotations, episode_number)
store.get_annotations(movie_id, episode_number)
store.get_all_annotations(movie_id)
store.delete_annotations(movie_id, episode_number)

# 搜索
store.search_lines(sentence_type="question", emotion="angry")
store.find_hook_lines(limit=10)
store.find_next_lines(current_line_id)

# 画布
store.create_project(name, description, theme)
store.get_project(project_id)
store.list_projects()
store.add_canvas_node(project_id, node_data)
store.add_canvas_edge(project_id, edge_data)

# 向量化
store.get_pending_vectorization(movie_id, limit)
store.update_vectorize_status(movie_id, line_ids, vectorized, vector_ids)
```

### 数据库模型 (直接访问)

```python
from app.models.database import get_db_manager, Movie, Line

db_manager = get_db_manager()
session = db_manager.get_session()

# 查询
movies = session.query(Movie).all()
lines = session.query(Line).filter(Line.emotion == "angry").all()

session.close()
```

## 环境变量

```bash
# 存储后端 (默认: sqlite)
STORE_BACKEND=sqlite   # 使用 SQLite（推荐）
STORE_BACKEND=json     # 使用 JSON（向后兼容）
```

## 启动步骤

1. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

2. 初始化数据库
   ```bash
   cd backend
   python scripts/init_database.py
   ```

3. 迁移数据（如有需要）
   ```bash
   python scripts/migrate_json_to_sqlite.py
   ```

4. 验证设置
   ```bash
   python scripts/verify_setup.py
   ```

5. 启动服务
   ```bash
   python main.py
   ```

## 向后兼容

- 设置 `STORE_BACKEND=json` 可回退到 JSON 存储
- 标注模块同时保存到 JSON 和 SQLite
- 保留原有 API 接口不变
