# backend/app/api/prompt_templates.py
"""
提示词模板管理 API
管理语义标注提示词、检索对话提示词模板、标签体系等
"""

import json
import uuid
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/prompt-templates", tags=["Prompt Templates"])

# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent / "data" / "cinegraph.db"


# ==================== 数据模型 ====================

class PromptTemplateCreate(BaseModel):
    strategy_id: Optional[str] = None
    template_type: str  # 'system' / 'user' / 'retrieval' / 'chat'
    name: str
    description: str = ""
    prompt_text: str
    variables: Optional[str] = None
    output_schema: Optional[str] = None
    compatible_models: Optional[str] = None
    version: str = "1.0.0"


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_text: Optional[str] = None
    variables: Optional[str] = None
    output_schema: Optional[str] = None
    compatible_models: Optional[str] = None
    version: Optional[str] = None
    is_active: Optional[bool] = None


class TagCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class TagDefinitionCreate(BaseModel):
    category_id: str
    value: str
    display_name: str
    description: str = ""
    color: Optional[str] = None
    llm_hints: Optional[str] = None
    example_phrases: Optional[str] = None


class TagDefinitionUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    llm_hints: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


# ==================== 辅助函数 ====================

def get_db():
    db_path = DB_PATH
    if not db_path.exists():
        raise HTTPException(status_code=500, detail="数据库文件不存在")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# ==================== 提示词模板 API ====================

@router.get("")
async def list_templates(template_type: str = None):
    """列出所有提示词模板"""
    conn = get_db()
    try:
        if template_type:
            rows = conn.execute(
                "SELECT * FROM annotation_prompt_templates WHERE template_type = ? ORDER BY created_at",
                (template_type,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM annotation_prompt_templates ORDER BY template_type, created_at"
            ).fetchall()
        
        templates = [dict(row) for row in rows]
        conn.close()
        return {"templates": templates, "total": len(templates)}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{template_id}")
async def get_template(template_id: str):
    """获取单个模板详情"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM annotation_prompt_templates WHERE id = ?", (template_id,)
        ).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_template(request: PromptTemplateCreate):
    """创建新的提示词模板"""
    template_id = f"prompt_{uuid.uuid4().hex[:8]}"
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO annotation_prompt_templates 
            (id, strategy_id, template_type, name, description, prompt_text, variables, output_schema, compatible_models, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template_id, request.strategy_id, request.template_type,
            request.name, request.description, request.prompt_text,
            request.variables, request.output_schema, request.compatible_models,
            request.version
        ))
        conn.commit()
        row = conn.execute("SELECT * FROM annotation_prompt_templates WHERE id = ?", (template_id,)).fetchone()
        conn.close()
        return {"success": True, "template": dict(row), "message": "模板创建成功"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/{template_id}")
async def update_template(template_id: str, request: PromptTemplateUpdate):
    """更新提示词模板"""
    conn = get_db()
    try:
        existing = conn.execute("SELECT * FROM annotation_prompt_templates WHERE id = ?", (template_id,)).fetchone()
        if not existing:
            conn.close()
            raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")
        
        updates = []
        values = []
        for key, value in request.model_dump(exclude_none=True).items():
            if key == 'is_active':
                updates.append(f"{key} = ?")
                values.append(int(value))
            else:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            conn.close()
            raise HTTPException(status_code=400, detail="没有需要更新的字段")
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(template_id)
        conn.execute(f"UPDATE annotation_prompt_templates SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()
        
        row = conn.execute("SELECT * FROM annotation_prompt_templates WHERE id = ?", (template_id,)).fetchone()
        conn.close()
        return {"success": True, "template": dict(row), "message": "更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """删除提示词模板"""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM annotation_prompt_templates WHERE id = ?", (template_id,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"模板不存在: {template_id}")
        
        conn.execute("DELETE FROM annotation_prompt_templates WHERE id = ?", (template_id,))
        conn.commit()
        conn.close()
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ==================== 标签分类 API ====================

@router.get("/tags/categories")
async def list_tag_categories():
    """列出所有标签分类"""
    conn = get_db()
    try:
        categories = conn.execute(
            "SELECT * FROM tag_categories ORDER BY layer, sort_order"
        ).fetchall()
        
        result = []
        for cat in categories:
            cat_dict = dict(cat)
            # 获取该分类下的标签数量
            count = conn.execute(
                "SELECT COUNT(*) FROM tag_definitions WHERE category_id = ? AND is_active = 1",
                (cat_dict['id'],)
            ).fetchone()[0]
            cat_dict['tag_count'] = count
            cat_dict['is_editable'] = bool(cat_dict.get('is_editable', 1))
            cat_dict['is_required'] = bool(cat_dict.get('is_required', 0))
            cat_dict['is_active'] = bool(cat_dict.get('is_active', 1))
            result.append(cat_dict)
        
        conn.close()
        return {"categories": result, "total": len(result)}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/categories/{category_id}/definitions")
async def list_tag_definitions(category_id: str):
    """列出某个分类下的所有标签定义"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM tag_definitions WHERE category_id = ? ORDER BY sort_order",
            (category_id,)
        ).fetchall()
        tags = [dict(row) for row in rows]
        for tag in tags:
            tag['is_builtin'] = bool(tag.get('is_builtin', 0))
            tag['is_active'] = bool(tag.get('is_active', 1))
        conn.close()
        return {"tags": tags, "total": len(tags)}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tags/categories/{category_id}")
async def update_tag_category(category_id: str, request: TagCategoryUpdate):
    """更新标签分类"""
    conn = get_db()
    try:
        updates = []
        values = []
        for key, value in request.model_dump(exclude_none=True).items():
            if isinstance(value, bool):
                updates.append(f"{key} = ?")
                values.append(int(value))
            else:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if updates:
            values.append(category_id)
            conn.execute(f"UPDATE tag_categories SET {', '.join(updates)} WHERE id = ?", values)
            conn.commit()
        
        conn.close()
        return {"success": True, "message": "更新成功"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tags/definitions")
async def create_tag_definition(request: TagDefinitionCreate):
    """创建新的标签定义"""
    tag_id = f"{request.category_id}_{request.value}"
    conn = get_db()
    try:
        # 检查是否已存在
        existing = conn.execute("SELECT id FROM tag_definitions WHERE id = ?", (tag_id,)).fetchone()
        if existing:
            conn.close()
            raise HTTPException(status_code=400, detail=f"标签已存在: {tag_id}")
        
        # 获取最大排序号
        max_order = conn.execute(
            "SELECT MAX(sort_order) FROM tag_definitions WHERE category_id = ?",
            (request.category_id,)
        ).fetchone()[0] or 0
        
        conn.execute("""
            INSERT INTO tag_definitions (id, category_id, value, display_name, description, color, llm_hints, example_phrases, sort_order, is_builtin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            tag_id, request.category_id, request.value, request.display_name,
            request.description, request.color, request.llm_hints, request.example_phrases,
            max_order + 1
        ))
        conn.commit()
        
        row = conn.execute("SELECT * FROM tag_definitions WHERE id = ?", (tag_id,)).fetchone()
        conn.close()
        return {"success": True, "tag": dict(row), "message": "标签创建成功"}
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.put("/tags/definitions/{tag_id}")
async def update_tag_definition(tag_id: str, request: TagDefinitionUpdate):
    """更新标签定义"""
    conn = get_db()
    try:
        updates = []
        values = []
        for key, value in request.model_dump(exclude_none=True).items():
            if isinstance(value, bool):
                updates.append(f"{key} = ?")
                values.append(int(value))
            else:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if updates:
            values.append(tag_id)
            conn.execute(f"UPDATE tag_definitions SET {', '.join(updates)} WHERE id = ?", values)
            conn.commit()
        
        conn.close()
        return {"success": True, "message": "更新成功"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tags/definitions/{tag_id}")
async def delete_tag_definition(tag_id: str):
    """删除标签定义（内置标签不可删除）"""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM tag_definitions WHERE id = ?", (tag_id,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"标签不存在: {tag_id}")
        if row['is_builtin']:
            conn.close()
            raise HTTPException(status_code=403, detail="内置标签不可删除，可以禁用")
        
        conn.execute("DELETE FROM tag_definitions WHERE id = ?", (tag_id,))
        conn.commit()
        conn.close()
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数据库统计 API ====================

@router.get("/stats/database")
async def get_database_stats():
    """获取数据库统计信息"""
    conn = get_db()
    try:
        stats = {}
        
        # 影片数量
        stats['movies_total'] = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        stats['movies_annotated'] = conn.execute("SELECT COUNT(*) FROM movies WHERE status_annotate = 'done'").fetchone()[0]
        stats['movies_vectorized'] = conn.execute("SELECT COUNT(*) FROM movies WHERE status_vectorize = 'done'").fetchone()[0]
        
        # 台词数量
        try:
            stats['lines_total'] = conn.execute("SELECT COUNT(*) FROM lines").fetchone()[0]
            stats['lines_vectorized'] = conn.execute("SELECT COUNT(*) FROM lines WHERE vectorized = 1").fetchone()[0]
        except:
            stats['lines_total'] = 0
            stats['lines_vectorized'] = 0
        
        # 模型数量
        stats['models_llm'] = conn.execute("SELECT COUNT(*) FROM model_providers WHERE category = 'llm'").fetchone()[0]
        stats['models_embedding'] = conn.execute("SELECT COUNT(*) FROM model_providers WHERE category = 'embedding'").fetchone()[0]
        stats['models_active_llm'] = conn.execute("SELECT COUNT(*) FROM model_providers WHERE category = 'llm' AND is_active = 1").fetchone()[0]
        stats['models_active_embedding'] = conn.execute("SELECT COUNT(*) FROM model_providers WHERE category = 'embedding' AND is_active = 1").fetchone()[0]
        
        # 标签统计
        stats['tag_categories'] = conn.execute("SELECT COUNT(*) FROM tag_categories").fetchone()[0]
        stats['tag_definitions'] = conn.execute("SELECT COUNT(*) FROM tag_definitions WHERE is_active = 1").fetchone()[0]
        
        # 数据库文件大小
        import os
        db_size = os.path.getsize(str(DB_PATH))
        stats['db_size_bytes'] = db_size
        stats['db_size_mb'] = round(db_size / 1024 / 1024, 2)
        
        conn.close()
        return stats
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
