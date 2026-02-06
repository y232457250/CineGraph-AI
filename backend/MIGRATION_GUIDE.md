# CineGraph-AI 数据库迁移指南

## 概述

本项目已从 JSON 文件存储迁移到 SQLite 数据库存储，以获得更好的性能、事务支持和无限画布功能。

## 主要变化

### 1. 存储层

- **旧**: JSON 文件 (`media_index.json`, `annotations/*.json`)
- **新**: SQLite 数据库 (`data/cinegraph.db`)

### 2. 设置存储

- **旧**: YAML 文件 (`backend/config/settings.yaml`)
- **新**: 数据库表 (`system_config`)

### 3. API 接口

- 所有 API 路由现在默认使用 `unified_store` (SQLAlchemy ORM)
- 向后兼容：设置 `STORE_BACKEND=json` 可回退到 JSON 模式

## 迁移步骤

### 第一步：安装依赖

```bash
pip install -r requirements.txt
```

### 第二步：初始化数据库

```bash
cd backend
python scripts/init_database.py
```

这将：
1. 创建 SQLite 数据库
2. 初始化表结构
3. 导入接话规则
4. 导入功能/风格标签

### 第三步：迁移现有数据（如果有）

```bash
python scripts/migrate_json_to_sqlite.py
```

这将：
1. 备份现有 JSON 文件
2. 迁移影片数据
3. 迁移标注数据
4. 保留原文件作为备份

### 第四步：启动服务

```bash
python main.py
```

服务将自动使用 SQLite 存储。

## 数据库结构

### 核心表

| 表名 | 说明 |
|------|------|
| `movies` | 影片元数据 |
| `episodes` | 剧集信息 |
| `lines` | 台词/标注数据（核心） |
| `characters` | 角色信息 |
| `projects` | 无限画布项目 |
| `canvas_nodes` | 画布节点 |
| `canvas_edges` | 画布连线 |
| `sequences` | 时间轴序列 |
| `sequence_items` | 序列项目 |
| `connection_rules` | 接话规则 |
| `system_config` | 系统设置 |

### Lines 表字段

```sql
- 基础信息: id, movie_id, episode_number, text, vector_text
- 时间: start_time, end_time, duration
- 四层标签: sentence_type, emotion, tone, character_type
- 接话逻辑: can_follow_types, can_lead_to_types
- 抖音指标: intensity, hook_score, ambiguity
- 向量化: vectorized, vector_id
```

## 使用新的存储接口

### 统一存储服务 (推荐)

```python
from app.core.store import get_unified_store

store = get_unified_store()

# 影片管理
movies = store.list_movies()
store.save_movie(movie_data)

# 标注数据
store.save_annotations(movie_id, annotations)
lines = store.search_lines(emotion="angry", limit=10)

# 无限画布
project = store.create_project(name="新项目")
store.add_canvas_node(project_id, node_data)
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

## 向后兼容

如果需要回退到 JSON 存储：

```bash
# Windows
set STORE_BACKEND=json

# Linux/Mac
export STORE_BACKEND=json

# 然后启动服务
python main.py
```

## 故障排除

### 数据库锁定错误

SQLite 默认使用 WAL 模式，支持并发读取。如果遇到锁定错误：

```python
# 检查是否有其他进程在使用数据库
# Windows
handle.exe data/cinegraph.db

# 或者重启服务
```

### 迁移失败

1. 检查 `media_index.json` 是否存在
2. 检查标注文件格式是否正确
3. 查看备份目录 `data/backup/`

### 设置未保存

确保数据库已正确初始化：

```python
from app.api.settings import init_default_settings
init_default_settings()
```

## 性能优化

### 索引

数据库已预设以下索引：

- `idx_line_media_ep`: 加速按影片/剧集查询
- `idx_connection`: 加速接话查询
- `idx_rule_query`: 加速规则查询

### 查询优化

使用 `unified_store` 的方法会自动使用最优查询：

```python
# 好的做法：使用存储方法
lines = store.search_lines(emotion="angry", limit=10)

# 避免：全表扫描
session.query(Line).all()  # 如果数据量大
```

## 备份与恢复

### 备份数据库

```bash
cp data/cinegraph.db data/cinegraph.db.backup
```

### 恢复数据库

```bash
cp data/cinegraph.db.backup data/cinegraph.db
```

### 导出为 JSON（兼容旧格式）

```python
from app.core.store import get_unified_store
import json

store = get_unified_store()
movies = store.list_movies()

with open('export.json', 'w', encoding='utf-8') as f:
    json.dump({'movies': movies}, f, ensure_ascii=False, indent=2)
```

## 开发指南

### 添加新表

在 `backend/app/models/database.py` 中定义模型：

```python
class NewTable(Base):
    __tablename__ = 'new_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    # ... 其他字段
```

然后运行：

```python
from app.models.database import init_database
init_database()
```

SQLAlchemy 会自动创建新表。

### 修改现有表

SQLite 不支持直接修改表结构。需要：

1. 创建新表
2. 迁移数据
3. 删除旧表
4. 重命名新表

或使用 Alembic 进行数据库迁移管理。

## 联系支持

如有问题，请检查：

1. 日志输出
2. 数据库文件权限
3. 依赖包版本
