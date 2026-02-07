# backend/app/api/ingestion_profiles.py
"""
入库配置 API
管理语义标注和向量化的模型选择与参数设定
"""

import json
import uuid
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/ingestion-profiles", tags=["Ingestion Profiles"])

# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent / "data" / "cinegraph.db"


# ==================== 数据模型 ====================

class IngestionProfileCreate(BaseModel):
    name: str
    description: str = ""
    profile_type: str  # 'annotation' 或 'vectorization'
    model_provider_id: Optional[str] = None
    batch_size: int = 10
    concurrent_requests: int = 1
    max_retries: int = 3
    retry_delay: int = 1000
    timeout: int = 120
    save_interval: int = 50
    annotation_depth: str = "full"
    included_tag_categories: List[str] = []
    chunk_overlap: int = 0
    normalize_embeddings: bool = True
    extra_config: Dict = {}


class IngestionProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_provider_id: Optional[str] = None
    batch_size: Optional[int] = None
    concurrent_requests: Optional[int] = None
    max_retries: Optional[int] = None
    retry_delay: Optional[int] = None
    timeout: Optional[int] = None
    save_interval: Optional[int] = None
    annotation_depth: Optional[str] = None
    included_tag_categories: Optional[List[str]] = None
    chunk_overlap: Optional[int] = None
    normalize_embeddings: Optional[bool] = None
    is_active: Optional[bool] = None
    extra_config: Optional[Dict] = None


# ==================== 辅助函数 ====================

def get_db():
    """获取数据库连接"""
    db_path = DB_PATH
    if not db_path.exists():
        raise HTTPException(status_code=500, detail="数据库文件不存在")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table():
    """确保 ingestion_profiles 表存在"""
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                profile_type TEXT NOT NULL,
                model_provider_id TEXT,
                batch_size INTEGER DEFAULT 10,
                concurrent_requests INTEGER DEFAULT 1,
                max_retries INTEGER DEFAULT 3,
                retry_delay INTEGER DEFAULT 1000,
                timeout INTEGER DEFAULT 120,
                save_interval INTEGER DEFAULT 50,
                annotation_depth TEXT DEFAULT 'full',
                included_tag_categories TEXT DEFAULT '[]',
                chunk_overlap INTEGER DEFAULT 0,
                normalize_embeddings BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                extra_config TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_provider_id) REFERENCES model_providers(id) ON DELETE SET NULL
            )
        """)
        
        # 插入默认配置（如果不存在）
        existing = conn.execute("SELECT COUNT(*) FROM ingestion_profiles").fetchone()[0]
        if existing == 0:
            conn.execute("""
                INSERT INTO ingestion_profiles (id, name, description, profile_type, batch_size, concurrent_requests, max_retries, retry_delay, save_interval, annotation_depth, included_tag_categories, is_default)
                VALUES ('annotation_default', '默认标注配置', '标准四层标签全量标注', 'annotation', 10, 1, 3, 1000, 50, 'full', '["sentence_type","emotion","tone","character_type","context_dye","metaphor_category"]', 1)
            """)
            conn.execute("""
                INSERT INTO ingestion_profiles (id, name, description, profile_type, batch_size, concurrent_requests, max_retries, retry_delay, is_default)
                VALUES ('vectorization_default', '默认向量化配置', '标准向量化入库配置', 'vectorization', 50, 2, 3, 500, 1)
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        conn.close()
        print(f"⚠️ 初始化 ingestion_profiles 表失败: {e}")


def row_to_dict(row) -> Dict:
    """将数据库行转换为字典"""
    d = dict(row)
    # 解析 JSON 字段
    if 'included_tag_categories' in d and isinstance(d['included_tag_categories'], str):
        try:
            d['included_tag_categories'] = json.loads(d['included_tag_categories'])
        except:
            d['included_tag_categories'] = []
    if 'extra_config' in d and isinstance(d['extra_config'], str):
        try:
            d['extra_config'] = json.loads(d['extra_config'])
        except:
            d['extra_config'] = {}
    # bool 转换
    d['is_default'] = bool(d.get('is_default', 0))
    d['is_active'] = bool(d.get('is_active', 1))
    d['normalize_embeddings'] = bool(d.get('normalize_embeddings', 1))
    return d


# 启动时确保表存在
try:
    ensure_table()
except:
    pass


# ==================== API 路由 ====================

@router.get("")
async def list_profiles(profile_type: str = None):
    """列出所有入库配置"""
    ensure_table()
    conn = get_db()
    try:
        if profile_type:
            rows = conn.execute(
                "SELECT * FROM ingestion_profiles WHERE profile_type = ? ORDER BY is_default DESC, created_at ASC",
                (profile_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ingestion_profiles ORDER BY profile_type, is_default DESC, created_at ASC"
            ).fetchall()
        
        profiles = [row_to_dict(row) for row in rows]
        conn.close()
        return {"profiles": profiles, "total": len(profiles)}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/annotation")
async def get_annotation_profiles():
    """获取标注配置列表"""
    ensure_table()
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM ingestion_profiles WHERE profile_type = 'annotation' ORDER BY is_default DESC, created_at ASC"
        ).fetchall()
        profiles = [row_to_dict(row) for row in rows]
        
        # 获取当前活跃的（默认）
        active = next((p for p in profiles if p['is_default']), profiles[0] if profiles else None)
        
        conn.close()
        return {"profiles": profiles, "active_profile": active}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vectorization")
async def get_vectorization_profiles():
    """获取向量化配置列表"""
    ensure_table()
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM ingestion_profiles WHERE profile_type = 'vectorization' ORDER BY is_default DESC, created_at ASC"
        ).fetchall()
        profiles = [row_to_dict(row) for row in rows]
        active = next((p for p in profiles if p['is_default']), profiles[0] if profiles else None)
        
        conn.close()
        return {"profiles": profiles, "active_profile": active}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{profile_id}")
async def get_profile(profile_id: str):
    """获取单个配置详情"""
    ensure_table()
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM ingestion_profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"配置不存在: {profile_id}")
        return row_to_dict(row)
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_profile(request: IngestionProfileCreate):
    """创建新的入库配置"""
    ensure_table()
    profile_id = f"{request.profile_type}_{uuid.uuid4().hex[:8]}"
    
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO ingestion_profiles 
            (id, name, description, profile_type, model_provider_id, batch_size, concurrent_requests,
             max_retries, retry_delay, timeout, save_interval, annotation_depth, included_tag_categories,
             chunk_overlap, normalize_embeddings, extra_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id, request.name, request.description, request.profile_type,
            request.model_provider_id, request.batch_size, request.concurrent_requests,
            request.max_retries, request.retry_delay, request.timeout, request.save_interval,
            request.annotation_depth, json.dumps(request.included_tag_categories),
            request.chunk_overlap, int(request.normalize_embeddings),
            json.dumps(request.extra_config)
        ))
        conn.commit()
        
        # 返回创建的记录
        row = conn.execute("SELECT * FROM ingestion_profiles WHERE id = ?", (profile_id,)).fetchone()
        conn.close()
        return {"success": True, "profile": row_to_dict(row), "message": "入库配置创建成功"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/{profile_id}")
async def update_profile(profile_id: str, request: IngestionProfileUpdate):
    """更新入库配置"""
    ensure_table()
    conn = get_db()
    try:
        # 检查是否存在
        existing = conn.execute("SELECT * FROM ingestion_profiles WHERE id = ?", (profile_id,)).fetchone()
        if not existing:
            conn.close()
            raise HTTPException(status_code=404, detail=f"配置不存在: {profile_id}")
        
        # 构建更新语句
        updates = []
        values = []
        update_data = request.model_dump(exclude_none=True)
        
        for key, value in update_data.items():
            if key == 'included_tag_categories':
                updates.append(f"{key} = ?")
                values.append(json.dumps(value))
            elif key == 'extra_config':
                updates.append(f"{key} = ?")
                values.append(json.dumps(value))
            elif key == 'normalize_embeddings':
                updates.append(f"{key} = ?")
                values.append(int(value))
            else:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            conn.close()
            raise HTTPException(status_code=400, detail="没有需要更新的字段")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(profile_id)
        
        conn.execute(
            f"UPDATE ingestion_profiles SET {', '.join(updates)} WHERE id = ?",
            values
        )
        conn.commit()
        
        row = conn.execute("SELECT * FROM ingestion_profiles WHERE id = ?", (profile_id,)).fetchone()
        conn.close()
        return {"success": True, "profile": row_to_dict(row), "message": "更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str):
    """删除入库配置（默认配置不可删除）"""
    ensure_table()
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM ingestion_profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"配置不存在: {profile_id}")
        
        if row['is_default']:
            conn.close()
            raise HTTPException(status_code=403, detail="默认配置不可删除")
        
        conn.execute("DELETE FROM ingestion_profiles WHERE id = ?", (profile_id,))
        conn.commit()
        conn.close()
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.put("/{profile_id}/set-default")
async def set_default_profile(profile_id: str):
    """设置某个配置为默认"""
    ensure_table()
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM ingestion_profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"配置不存在: {profile_id}")
        
        profile_type = row['profile_type']
        
        # 取消同类型的其他默认
        conn.execute(
            "UPDATE ingestion_profiles SET is_default = 0 WHERE profile_type = ?",
            (profile_type,)
        )
        # 设置新默认
        conn.execute(
            "UPDATE ingestion_profiles SET is_default = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (profile_id,)
        )
        conn.commit()
        conn.close()
        return {"success": True, "message": f"已设为默认{profile_type}配置"}
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")
