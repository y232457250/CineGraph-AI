# backend/app/core/store/unified_store.py
"""
统一存储服务
基于 SQLAlchemy ORM 的数据库操作封装
支持：影片管理、标注数据、无限画布
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from contextlib import contextmanager

from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session, joinedload

from app.models.database import (
    DatabaseManager, get_db_manager,
    Movie, Episode, Line, Character, ConnectionRule,
    Project, CanvasNode, CanvasEdge, Sequence, SequenceItem,
    LineFunction, LineStyle, SystemConfig
)


class UnifiedStore:
    """
    统一存储服务
    提供所有数据库操作的统一接口
    """
    
    def __init__(self, db_path: str = None):
        self.db_manager = get_db_manager(db_path)
    
    @contextmanager
    def session_scope(self):
        """提供事务作用域"""
        session = self.db_manager.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # ==================== 影片管理 ====================
    
    def get_movie(self, movie_id: str) -> Optional[Dict]:
        """获取单个影片"""
        with self.session_scope() as session:
            movie = session.query(Movie).options(
                joinedload(Movie.episodes)
            ).filter(Movie.id == movie_id).first()
            
            if movie:
                return movie.to_dict()
            return None
    
    def list_movies(self) -> List[Dict]:
        """获取所有影片列表"""
        with self.session_scope() as session:
            movies = session.query(Movie).options(
                joinedload(Movie.episodes)
            ).order_by(desc(Movie.created_at)).all()
            
            return [m.to_dict() for m in movies]
    
    def save_movie(self, movie_data: Dict) -> bool:
        """保存影片"""
        with self.session_scope() as session:
            movie_id = movie_data.get('id') or movie_data.get('douban_id')
            if not movie_id:
                raise ValueError("Movie must have id or douban_id")
            
            # 提取剧集数据
            episodes_data = movie_data.pop('episodes', [])
            
            # 处理 starring
            starring = movie_data.get('starring', [])
            if isinstance(starring, list):
                starring = json.dumps(starring, ensure_ascii=False)
            
            # 查找或创建影片
            movie = session.query(Movie).filter(Movie.id == movie_id).first()
            if movie is None:
                movie = Movie(id=movie_id)
                session.add(movie)
            
            # 更新字段
            movie.title = movie_data.get('title', movie.title or '')
            movie.original_title = movie_data.get('original_title', movie.original_title)
            movie.year = movie_data.get('year', movie.year)
            movie.media_type = movie_data.get('media_type', movie.media_type or 'movie')
            movie.folder = movie_data.get('folder', movie.folder)
            movie.folder_path = movie_data.get('folder_path', movie.folder_path)
            movie.poster_url = movie_data.get('poster_url', movie.poster_url)
            movie.local_poster = movie_data.get('local_poster', movie.local_poster)
            movie.director = movie_data.get('director', movie.director)
            movie.writer = movie_data.get('writer', movie.writer)
            movie.starring = starring if starring else movie.starring
            movie.genre = movie_data.get('genre', movie.genre)
            movie.country = movie_data.get('country', movie.country)
            movie.language = movie_data.get('language', movie.language)
            movie.release_date = movie_data.get('release_date', movie.release_date)
            movie.douban_url = movie_data.get('douban_url', movie.douban_url)
            movie.rating = movie_data.get('rating', movie.rating)
            movie.status_import = movie_data.get('status_import', movie.status_import or 'pending')
            movie.status_annotate = movie_data.get('status_annotate', movie.status_annotate or 'pending')
            movie.status_vectorize = movie_data.get('status_vectorize', movie.status_vectorize or 'pending')
            movie.import_batch = movie_data.get('import_batch', movie.import_batch)
            movie.updated_at = datetime.utcnow()
            
            # 保存剧集
            for ep_data in episodes_data:
                ep_num = ep_data.get('episode_number', 0)
                episode = session.query(Episode).filter(
                    Episode.movie_id == movie_id,
                    Episode.episode_number == ep_num
                ).first()
                
                if episode is None:
                    episode = Episode(movie_id=movie_id, episode_number=ep_num)
                    session.add(episode)
                
                episode.video_path = ep_data.get('video_path', episode.video_path)
                episode.subtitle_path = ep_data.get('subtitle_path', episode.subtitle_path)
                episode.video_filename = ep_data.get('video_filename', episode.video_filename)
                episode.subtitle_filename = ep_data.get('subtitle_filename', episode.subtitle_filename)
                episode.status_vectorize = ep_data.get('status_vectorize', episode.status_vectorize or 'pending')
            
            return True
    
    def delete_movie(self, movie_id: str) -> bool:
        """删除影片（级联删除相关数据）"""
        with self.session_scope() as session:
            movie = session.query(Movie).filter(Movie.id == movie_id).first()
            if movie:
                # 删除向量数据
                self._delete_vector_data(movie_id)
                session.delete(movie)
                return True
            return False
    
    def delete_episode(self, movie_id: str, episode_number: int) -> Tuple[bool, int]:
        """
        删除影片的某一集
        
        Args:
            movie_id: 影片ID
            episode_number: 集数
            
        Returns:
            (是否成功, 剩余集数)
        """
        with self.session_scope() as session:
            episode = session.query(Episode).filter(
                Episode.movie_id == movie_id,
                Episode.episode_number == episode_number
            ).first()
            
            if not episode:
                return (False, -1)
            
            session.delete(episode)
            
            # 计算剩余集数
            remaining = session.query(Episode).filter(Episode.movie_id == movie_id).count()
            
            return (True, remaining)
    
    def _delete_vector_data(self, movie_id: str):
        """删除 ChromaDB 中的向量数据"""
        try:
            from app.ingestion.vectorizer import VectorStore
            store = VectorStore()
            store.delete_by_movie(movie_id)
        except Exception as e:
            print(f"[UnifiedStore] 删除向量数据失败: {e}")
    
    def update_movie_status(self, movie_id: str, **status_updates) -> bool:
        """更新影片状态"""
        with self.session_scope() as session:
            movie = session.query(Movie).filter(Movie.id == movie_id).first()
            if movie:
                if 'status_import' in status_updates:
                    movie.status_import = status_updates['status_import']
                if 'status_annotate' in status_updates:
                    movie.status_annotate = status_updates['status_annotate']
                if 'status_vectorize' in status_updates:
                    movie.status_vectorize = status_updates['status_vectorize']
                movie.updated_at = datetime.utcnow()
                return True
            return False
    
    # ==================== 标注数据管理 ====================
    
    def save_annotations(
        self, 
        movie_id: str, 
        annotations: List[Dict], 
        episode_number: Optional[int] = None
    ) -> int:
        """
        保存标注数据到 lines 表
        
        Args:
            movie_id: 影片ID
            annotations: 标注数据列表
            episode_number: 剧集编号（电影为 None）
            
        Returns:
            保存的行数
        """
        with self.session_scope() as session:
            count = 0
            
            for idx, ann in enumerate(annotations):
                line = Line.from_annotation_dict(ann, movie_id, episode_number, idx)
                
                # 检查是否已存在
                existing = session.query(Line).filter(Line.line_id == line.line_id).first()
                if existing:
                    # 更新现有记录 - 使用新的字段名
                    update_fields = [
                        # 基础字段
                        'text', 'vector_text', 'start_time', 'end_time', 'duration', 'character_name',
                        # 第一层：基础标签
                        'sentence_type', 'emotion', 'tone', 'character_type', 'can_follow', 'can_lead_to',
                        # 第二层：潜台词
                        'context_dye', 'context_intensity', 'subtext_type', 'subtext_description',
                        'is_meme', 'meme_name', 'social_function',
                        'surface_sentiment', 'actual_sentiment', 'sentiment_polarity',
                        # 第三层：隐喻
                        'metaphor_category', 'metaphor_keyword', 'metaphor_direction', 
                        'metaphor_strength', 'semantic_field',
                        # 算法字段
                        'intensity', 'hook_score', 'ambiguity', 'viral_potential'
                    ]
                    for key in update_fields:
                        setattr(existing, key, getattr(line, key))
                    existing.updated_at = datetime.utcnow()
                else:
                    session.add(line)
                
                count += 1
            
            # 更新影片标注状态
            movie = session.query(Movie).filter(Movie.id == movie_id).first()
            if movie:
                movie.status_annotate = 'done'
                movie.updated_at = datetime.utcnow()
            
            return count
    
    def get_annotations(
        self, 
        movie_id: str, 
        episode_number: Optional[int] = None
    ) -> List[Dict]:
        """获取标注数据"""
        with self.session_scope() as session:
            query = session.query(Line).filter(Line.movie_id == movie_id)
            
            if episode_number is not None:
                query = query.filter(Line.episode_number == episode_number)
            else:
                query = query.filter(Line.episode_number.is_(None))
            
            lines = query.order_by(Line.line_index).all()
            return [line.to_dict() for line in lines]
    
    def get_all_annotations(self, movie_id: str) -> List[Dict]:
        """获取影片的所有标注（包含所有剧集）"""
        with self.session_scope() as session:
            lines = session.query(Line).filter(
                Line.movie_id == movie_id
            ).order_by(Line.episode_number, Line.line_index).all()
            
            return [line.to_dict() for line in lines]
    
    def delete_annotations(
        self, 
        movie_id: str, 
        episode_number: Optional[int] = None
    ) -> int:
        """删除标注数据"""
        with self.session_scope() as session:
            query = session.query(Line).filter(Line.movie_id == movie_id)
            
            if episode_number is not None:
                query = query.filter(Line.episode_number == episode_number)
            
            count = query.delete()
            return count
    
    def search_lines(
        self,
        sentence_type: str = None,
        emotion: str = None,
        tone: str = None,
        character_type: str = None,
        min_intensity: int = None,
        max_duration: float = None,
        keywords: List[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """根据标签搜索台词"""
        with self.session_scope() as session:
            query = session.query(Line)
            
            if sentence_type:
                query = query.filter(Line.sentence_type == sentence_type)
            if emotion:
                query = query.filter(Line.emotion == emotion)
            if tone:
                query = query.filter(Line.tone == tone)
            if character_type:
                query = query.filter(Line.character_type == character_type)
            if min_intensity:
                query = query.filter(Line.intensity >= min_intensity)
            if max_duration:
                query = query.filter(Line.duration <= max_duration)
            if keywords:
                for kw in keywords:
                    query = query.filter(Line.keywords.contains(kw))
            
            lines = query.order_by(desc(Line.hook_score)).limit(limit).all()
            return [line.to_dict() for line in lines]
    
    def find_hook_lines(self, limit: int = 10) -> List[Dict]:
        """查找适合做钩子的台词（高强度 + 短时长 + 高hook）"""
        with self.session_scope() as session:
            lines = session.query(Line).filter(
                Line.intensity >= 7,
                Line.duration <= 3.0,
                Line.hook_score >= 0.6
            ).order_by(
                desc(Line.hook_score),
                desc(Line.intensity)
            ).limit(limit).all()
            
            return [line.to_dict() for line in lines]
    
    def find_next_lines(self, current_line_id: str, limit: int = 5) -> List[Dict]:
        """基于接话规则查找下一句"""
        with self.session_scope() as session:
            # 获取当前台词
            current = session.query(Line).filter(Line.line_id == current_line_id).first()
            if not current or not current.can_lead_to_types:
                return []
            
            try:
                can_lead_to = json.loads(current.can_lead_to_types)
            except:
                return []
            
            if not can_lead_to:
                return []
            
            # 查找可接的下一句
            candidates = session.query(Line).filter(
                Line.sentence_type.in_(can_lead_to),
                Line.id != current.id
            ).order_by(
                desc(Line.hook_score)
            ).limit(limit).all()
            
            return [line.to_dict() for line in candidates]
    
    # ==================== 接话规则管理 ====================
    
    def get_connection_rules(self, from_type: str = None, rule_type: str = 'sentence') -> List[Dict]:
        """获取接话规则"""
        with self.session_scope() as session:
            query = session.query(ConnectionRule).filter(ConnectionRule.rule_type == rule_type)
            
            if from_type:
                query = query.filter(ConnectionRule.from_type == from_type)
            
            rules = query.order_by(desc(ConnectionRule.weight)).all()
            
            return [{
                'from': r.from_type,
                'to': r.to_type,
                'weight': r.weight,
                'transition_type': r.transition_type
            } for r in rules]
    
    # ==================== 无限画布管理 ====================
    
    def create_project(self, name: str, description: str = '', theme: str = None) -> Dict:
        """创建画布项目"""
        with self.session_scope() as session:
            project = Project(
                name=name,
                description=description,
                theme=theme
            )
            session.add(project)
            session.flush()  # 获取ID
            
            # 创建根节点
            root_node = CanvasNode(
                project_id=project.id,
                node_type='root',
                title='根节点',
                pos_x=0,
                pos_y=0
            )
            session.add(root_node)
            
            # 创建默认序列
            sequence = Sequence(
                project_id=project.id,
                name='主序列'
            )
            session.add(sequence)
            
            return project.to_dict()
    
    def get_project(self, project_id: str, include_nodes: bool = True) -> Optional[Dict]:
        """获取项目（包含完整画布数据）"""
        with self.session_scope() as session:
            project = session.query(Project).options(
                joinedload(Project.nodes).joinedload(CanvasNode.line),
                joinedload(Project.edges),
                joinedload(Project.sequences).joinedload(Sequence.items)
            ).filter(Project.id == project_id).first()
            
            if project:
                result = project.to_dict(include_nodes=include_nodes)
                result['sequences'] = [s.to_dict() for s in project.sequences]
                return result
            return None
    
    def list_projects(self) -> List[Dict]:
        """列出所有项目"""
        with self.session_scope() as session:
            projects = session.query(Project).order_by(desc(Project.updated_at)).all()
            return [p.to_dict() for p in projects]
    
    def update_project(self, project_id: str, **updates) -> bool:
        """更新项目"""
        with self.session_scope() as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                for key, value in updates.items():
                    if hasattr(project, key):
                        setattr(project, key, value)
                project.updated_at = datetime.utcnow()
                return True
            return False
    
    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        with self.session_scope() as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                session.delete(project)
                return True
            return False
    
    # ==================== 画布节点管理 ====================
    
    def add_canvas_node(self, project_id: str, node_data: Dict) -> Dict:
        """添加画布节点"""
        with self.session_scope() as session:
            node = CanvasNode(
                project_id=project_id,
                parent_id=node_data.get('parent_id'),
                line_id=node_data.get('line_id'),
                node_type=node_data.get('node_type', 'clip'),
                title=node_data.get('title', ''),
                content=node_data.get('content'),
                order=node_data.get('order', 0),
                pos_x=node_data.get('position', {}).get('x', 0),
                pos_y=node_data.get('position', {}).get('y', 0),
                width=node_data.get('size', {}).get('width', 200),
                height=node_data.get('size', {}).get('height', 100),
                color=node_data.get('color'),
                volume=node_data.get('volume', 1.0),
            )
            session.add(node)
            session.flush()
            
            # 更新项目时间
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                project.updated_at = datetime.utcnow()
            
            return node.to_dict()
    
    def update_canvas_node(self, node_id: str, **updates) -> bool:
        """更新画布节点"""
        with self.session_scope() as session:
            node = session.query(CanvasNode).filter(CanvasNode.id == node_id).first()
            if node:
                # 处理嵌套的 position 和 size
                if 'position' in updates:
                    pos = updates.pop('position')
                    node.pos_x = pos.get('x', node.pos_x)
                    node.pos_y = pos.get('y', node.pos_y)
                
                if 'size' in updates:
                    size = updates.pop('size')
                    node.width = size.get('width', node.width)
                    node.height = size.get('height', node.height)
                
                for key, value in updates.items():
                    if hasattr(node, key):
                        setattr(node, key, value)
                
                node.updated_at = datetime.utcnow()
                return True
            return False
    
    def delete_canvas_node(self, node_id: str) -> bool:
        """删除画布节点"""
        with self.session_scope() as session:
            node = session.query(CanvasNode).filter(CanvasNode.id == node_id).first()
            if node:
                session.delete(node)
                return True
            return False
    
    def batch_update_nodes(self, project_id: str, nodes_data: List[Dict]) -> int:
        """批量更新节点位置"""
        with self.session_scope() as session:
            count = 0
            for node_data in nodes_data:
                node_id = node_data.get('id')
                if not node_id:
                    continue
                
                node = session.query(CanvasNode).filter(
                    CanvasNode.id == node_id,
                    CanvasNode.project_id == project_id
                ).first()
                
                if node:
                    if 'position' in node_data:
                        node.pos_x = node_data['position'].get('x', node.pos_x)
                        node.pos_y = node_data['position'].get('y', node.pos_y)
                    if 'size' in node_data:
                        node.width = node_data['size'].get('width', node.width)
                        node.height = node_data['size'].get('height', node.height)
                    count += 1
            
            return count
    
    # ==================== 画布连线管理 ====================
    
    def add_canvas_edge(self, project_id: str, edge_data: Dict) -> Dict:
        """添加画布连线"""
        with self.session_scope() as session:
            edge = CanvasEdge(
                project_id=project_id,
                source_id=edge_data['source'],
                target_id=edge_data['target'],
                source_anchor=edge_data.get('source_anchor', 'output'),
                target_anchor=edge_data.get('target_anchor', 'input'),
                relation_type=edge_data.get('relation_type'),
                strength=edge_data.get('strength', 0.5),
                color=edge_data.get('color'),
                label=edge_data.get('label'),
            )
            session.add(edge)
            session.flush()
            
            return edge.to_dict()
    
    def delete_canvas_edge(self, edge_id: str) -> bool:
        """删除画布连线"""
        with self.session_scope() as session:
            edge = session.query(CanvasEdge).filter(CanvasEdge.id == edge_id).first()
            if edge:
                session.delete(edge)
                return True
            return False
    
    # ==================== 时间轴序列管理 ====================
    
    def add_to_sequence(
        self, 
        sequence_id: int, 
        node_id: str, 
        order: int = None
    ) -> Dict:
        """添加节点到时间轴"""
        with self.session_scope() as session:
            sequence = session.query(Sequence).filter(Sequence.id == sequence_id).first()
            if not sequence:
                raise ValueError(f"Sequence {sequence_id} not found")
            
            # 自动计算 order
            if order is None:
                max_order = session.query(func.max(SequenceItem.order)).filter(
                    SequenceItem.sequence_id == sequence_id
                ).scalar() or 0
                order = max_order + 1
            
            item = SequenceItem(
                sequence_id=sequence_id,
                node_id=node_id,
                order=order
            )
            session.add(item)
            session.flush()
            
            # 更新序列总时长
            self._update_sequence_duration(session, sequence_id)
            
            return item.to_dict()
    
    def reorder_sequence(self, sequence_id: int, item_ids: List[int]) -> bool:
        """重排时间轴顺序"""
        with self.session_scope() as session:
            for idx, item_id in enumerate(item_ids):
                item = session.query(SequenceItem).filter(
                    SequenceItem.id == item_id,
                    SequenceItem.sequence_id == sequence_id
                ).first()
                if item:
                    item.order = idx
            return True
    
    def _update_sequence_duration(self, session: Session, sequence_id: int):
        """更新序列总时长"""
        items = session.query(SequenceItem).options(
            joinedload(SequenceItem.node).joinedload(CanvasNode.line)
        ).filter(SequenceItem.sequence_id == sequence_id).all()
        
        total = 0.0
        for item in items:
            if item.node and item.node.line:
                duration = item.trim_end or item.node.line.duration or 0
                total += duration - item.trim_start
        
        sequence = session.query(Sequence).filter(Sequence.id == sequence_id).first()
        if sequence:
            sequence.total_duration = total
    
    # ==================== 向量化状态管理 ====================
    
    def update_vectorize_status(
        self, 
        movie_id: str, 
        line_ids: List[str], 
        vectorized: bool = True,
        vector_ids: Dict[str, str] = None
    ) -> int:
        """更新向量化状态"""
        with self.session_scope() as session:
            count = 0
            for line_id in line_ids:
                line = session.query(Line).filter(Line.line_id == line_id).first()
                if line:
                    line.vectorized = vectorized
                    if vector_ids and line_id in vector_ids:
                        line.vector_id = vector_ids[line_id]
                    count += 1
            
            # 更新影片向量化状态
            movie = session.query(Movie).filter(Movie.id == movie_id).first()
            if movie:
                total_lines = session.query(Line).filter(Line.movie_id == movie_id).count()
                vectorized_lines = session.query(Line).filter(
                    Line.movie_id == movie_id,
                    Line.vectorized == True
                ).count()
                
                if vectorized_lines == 0:
                    movie.status_vectorize = 'pending'
                elif vectorized_lines < total_lines:
                    movie.status_vectorize = 'partial'
                else:
                    movie.status_vectorize = 'done'
            
            return count
    
    def get_pending_vectorization(self, movie_id: str = None, limit: int = 100) -> List[Dict]:
        """获取待向量化的台词"""
        with self.session_scope() as session:
            query = session.query(Line).filter(Line.vectorized == False)
            
            if movie_id:
                query = query.filter(Line.movie_id == movie_id)
            
            lines = query.limit(limit).all()
            return [line.to_dict() for line in lines]
    
    def vectorize_texts(self, texts: List[str], metadata_list: List[Dict] = None) -> List[str]:
        """
        向量化文本并存储到向量数据库
        
        Args:
            texts: 要向量化的文本列表
            metadata_list: 每个文本的元数据
            
        Returns:
            向量ID列表
        """
        from app.ingestion.vectorizer import Vectorizer
        vectorizer = Vectorizer()
        
        # 批量向量化
        vector_ids = []
        batch_size = 50
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_meta = metadata_list[i:i+batch_size] if metadata_list else None
            
            batch_ids = vectorizer.add_texts(batch_texts, batch_meta)
            vector_ids.extend(batch_ids)
        
        return vector_ids


# ==================== 单例获取 ====================

_unified_store: Optional[UnifiedStore] = None


def get_unified_store(db_path: str = None) -> UnifiedStore:
    """获取统一存储服务单例"""
    global _unified_store
    if _unified_store is None:
        _unified_store = UnifiedStore(db_path)
    return _unified_store
