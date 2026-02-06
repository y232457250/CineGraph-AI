# backend/app/routers/canvas.py
"""
无限画布 API 路由
支持：项目管理、节点操作、连线操作、时间轴序列
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

from app.core.store.unified_store import get_unified_store

router = APIRouter(prefix="/api/canvas", tags=["canvas"])


# ==================== 请求/响应模型 ====================

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    theme: Optional[str] = None
    style: Optional[str] = "absurd"


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    theme: Optional[str] = None
    style: Optional[str] = None
    viewport_x: Optional[float] = None
    viewport_y: Optional[float] = None
    viewport_zoom: Optional[float] = None


class NodePosition(BaseModel):
    x: float = 0
    y: float = 0


class NodeSize(BaseModel):
    width: float = 200
    height: float = 100


class CreateNodeRequest(BaseModel):
    parent_id: Optional[str] = None
    line_id: Optional[int] = None
    node_type: str = "clip"  # root/scene/clip/transition/effect/note
    title: Optional[str] = ""
    content: Optional[str] = None
    position: Optional[NodePosition] = None
    size: Optional[NodeSize] = None
    color: Optional[str] = None
    order: int = 0


class UpdateNodeRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    position: Optional[NodePosition] = None
    size: Optional[NodeSize] = None
    color: Optional[str] = None
    collapsed: Optional[bool] = None
    locked: Optional[bool] = None
    volume: Optional[float] = None
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None


class BatchUpdateNodesRequest(BaseModel):
    nodes: List[Dict[str, Any]]


class CreateEdgeRequest(BaseModel):
    source: str
    target: str
    source_anchor: str = "output"
    target_anchor: str = "input"
    relation_type: Optional[str] = None
    strength: float = 0.5
    color: Optional[str] = None
    label: Optional[str] = None


class AddToSequenceRequest(BaseModel):
    node_id: str
    order: Optional[int] = None
    transition_type: str = "cut"
    transition_duration: float = 0.0


class ReorderSequenceRequest(BaseModel):
    item_ids: List[int]


# ==================== 项目管理 ====================

@router.get("/projects")
async def list_projects():
    """获取所有画布项目列表"""
    try:
        store = get_unified_store()
        projects = store.list_projects()
        return {"success": True, "projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects")
async def create_project(request: CreateProjectRequest):
    """创建新的画布项目"""
    try:
        store = get_unified_store()
        project = store.create_project(
            name=request.name,
            description=request.description,
            theme=request.theme
        )
        return {"success": True, "project": project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(project_id: str, include_nodes: bool = True):
    """获取项目详情（包含画布数据）"""
    try:
        store = get_unified_store()
        project = store.get_project(project_id, include_nodes=include_nodes)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"success": True, "project": project}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}")
async def update_project(project_id: str, request: UpdateProjectRequest):
    """更新项目"""
    try:
        store = get_unified_store()
        updates = request.dict(exclude_none=True)
        
        success = store.update_project(project_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    try:
        store = get_unified_store()
        success = store.delete_project(project_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 节点管理 ====================

@router.post("/projects/{project_id}/nodes")
async def create_node(project_id: str, request: CreateNodeRequest):
    """创建画布节点"""
    try:
        store = get_unified_store()
        
        node_data = {
            'parent_id': request.parent_id,
            'line_id': request.line_id,
            'node_type': request.node_type,
            'title': request.title,
            'content': request.content,
            'order': request.order,
            'color': request.color,
        }
        
        if request.position:
            node_data['position'] = {'x': request.position.x, 'y': request.position.y}
        
        if request.size:
            node_data['size'] = {'width': request.size.width, 'height': request.size.height}
        
        node = store.add_canvas_node(project_id, node_data)
        return {"success": True, "node": node}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/nodes/{node_id}")
async def update_node(node_id: str, request: UpdateNodeRequest):
    """更新节点"""
    try:
        store = get_unified_store()
        updates = {}
        
        if request.title is not None:
            updates['title'] = request.title
        if request.content is not None:
            updates['content'] = request.content
        if request.position is not None:
            updates['position'] = {'x': request.position.x, 'y': request.position.y}
        if request.size is not None:
            updates['size'] = {'width': request.size.width, 'height': request.size.height}
        if request.color is not None:
            updates['color'] = request.color
        if request.collapsed is not None:
            updates['collapsed'] = request.collapsed
        if request.locked is not None:
            updates['locked'] = request.locked
        if request.volume is not None:
            updates['volume'] = request.volume
        if request.trim_start is not None:
            updates['trim_start'] = request.trim_start
        if request.trim_end is not None:
            updates['trim_end'] = request.trim_end
        
        success = store.update_canvas_node(node_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str):
    """删除节点"""
    try:
        store = get_unified_store()
        success = store.delete_canvas_node(node_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Node not found")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/projects/{project_id}/nodes/batch")
async def batch_update_nodes(project_id: str, request: BatchUpdateNodesRequest):
    """批量更新节点（位置、大小等）"""
    try:
        store = get_unified_store()
        count = store.batch_update_nodes(project_id, request.nodes)
        return {"success": True, "updated_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 连线管理 ====================

@router.post("/projects/{project_id}/edges")
async def create_edge(project_id: str, request: CreateEdgeRequest):
    """创建连线"""
    try:
        store = get_unified_store()
        edge = store.add_canvas_edge(project_id, request.dict())
        return {"success": True, "edge": edge}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/edges/{edge_id}")
async def delete_edge(edge_id: str):
    """删除连线"""
    try:
        store = get_unified_store()
        success = store.delete_canvas_edge(edge_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Edge not found")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 时间轴序列 ====================

@router.post("/sequences/{sequence_id}/items")
async def add_to_sequence(sequence_id: int, request: AddToSequenceRequest):
    """添加节点到时间轴"""
    try:
        store = get_unified_store()
        item = store.add_to_sequence(
            sequence_id=sequence_id,
            node_id=request.node_id,
            order=request.order
        )
        return {"success": True, "item": item}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sequences/{sequence_id}/reorder")
async def reorder_sequence(sequence_id: int, request: ReorderSequenceRequest):
    """重排时间轴顺序"""
    try:
        store = get_unified_store()
        success = store.reorder_sequence(sequence_id, request.item_ids)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 台词搜索（用于添加到画布） ====================

@router.get("/lines/search")
async def search_lines(
    sentence_type: Optional[str] = None,
    emotion: Optional[str] = None,
    tone: Optional[str] = None,
    character_type: Optional[str] = None,
    min_intensity: Optional[int] = None,
    max_duration: Optional[float] = None,
    keyword: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """搜索台词（用于拖拽到画布）"""
    try:
        store = get_unified_store()
        
        keywords = [keyword] if keyword else None
        
        lines = store.search_lines(
            sentence_type=sentence_type,
            emotion=emotion,
            tone=tone,
            character_type=character_type,
            min_intensity=min_intensity,
            max_duration=max_duration,
            keywords=keywords,
            limit=limit
        )
        
        return {"success": True, "lines": lines, "count": len(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lines/hooks")
async def get_hook_lines(limit: int = Query(10, le=50)):
    """获取钩子台词（高强度、短时长、高吸引力）"""
    try:
        store = get_unified_store()
        lines = store.find_hook_lines(limit=limit)
        return {"success": True, "lines": lines, "count": len(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lines/{line_id}/next")
async def get_next_lines(line_id: str, limit: int = Query(5, le=20)):
    """基于接话规则获取可接的下一句"""
    try:
        store = get_unified_store()
        lines = store.find_next_lines(line_id, limit=limit)
        return {"success": True, "lines": lines, "count": len(lines)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules")
async def get_connection_rules(
    from_type: Optional[str] = None,
    rule_type: str = Query("sentence", regex="^(sentence|emotion|tone)$")
):
    """获取接话规则"""
    try:
        store = get_unified_store()
        rules = store.get_connection_rules(from_type=from_type, rule_type=rule_type)
        return {"success": True, "rules": rules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
