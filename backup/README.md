# CineGraph-AI 备份说明

## 备份信息

| 项目 | 详情 |
|------|------|
| **备份文件** | `backup_20260206_230549.zip` |
| **备份时间** | 2026-02-06 23:05:51 |
| **备份大小** | 0.38 MB (390 KB) |

## 备份内容

### 1. 数据库（已初始化）
- ✅ **SQLite 数据库**: `backend/data/cinegraph.db` (420 KB)
- ✅ **ChromaDB 向量库**: `data/chroma_db/` (1.44 MB)

### 2. 配置文件
- `config/config.yaml`
- `backend/requirements.txt`
- `requirements.txt`
- `package.json`

### 3. 源代码
- **后端**: 32 个文件 (`backend/app/`, `backend/main.py`)
- **前端**: 15 个文件 (`frontend-ui/`)

### 4. 数据文件
- 14 个数据文件（分析结果、标注数据等）

## 使用方法

### 创建新备份
```powershell
.\scripts\backup_project.ps1
```

### 从备份还原
```powershell
# 方法1: 使用备份文件名
.\scripts\restore_project.ps1 backup_20260206_230549.zip

# 方法2: 省略 .zip 后缀
.\scripts\restore_project.ps1 backup_20260206_230549
```

## 验证项目状态

### 后端启动
```powershell
cd backend
.\..\venv\Scripts\python.exe main.py
# 或激活虚拟环境后
python main.py
```

### 前端启动
```powershell
cd frontend-ui
# 根据实际前端框架启动
```

## 注意事项

1. **数据库已初始化**: 此备份包含完整的数据库，可直接恢复使用
2. **向量库已包含**: ChromaDB 向量数据已完整备份
3. **端口占用**: 如果启动时报端口错误，请先结束占用 8000 端口的进程
4. **虚拟环境**: 确保使用虚拟环境的 Python 运行后端
