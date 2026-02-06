"""
SQLite 存储实现
支持：影片管理、标注数据、无限画布
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from contextlib import contextmanager

from .base import MovieStore


class SQLiteMovieStore(MovieStore):
    """
    SQLite 影片存储实现
    
    优势：
    1. 事务支持（删除电影时自动级联删除标注）
    2. 更好的查询性能
    3. 支持树形结构（无限画布）
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = Path(__file__).resolve().parents[3] / "data" / "cinegraph.db"
        else:
            self.db_path = db_path
        
        # 确保数据库已初始化
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库（如果不存在）"""
        if not self.db_path.exists():
            schema_path = Path(__file__).parent.parent.parent / "database" / "schema.sql"
            if schema_path.exists():
                with self._get_conn() as conn:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        conn.executescript(f.read())
                    conn.commit()
    
    # ============ MovieStore 接口实现 ============
    
    def get_movie(self, douban_id: str) -> Optional[Dict[str, Any]]:
        """获取单个影片（包含剧集信息）"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 获取影片
            cursor.execute("SELECT * FROM movies WHERE id = ?", (douban_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            movie = dict(row)
            
            # 解析 starring
            if movie.get("starring"):
                try:
                    movie["starring"] = json.loads(movie["starring"])
                except:
                    movie["starring"] = []
            
            # 获取剧集
            cursor.execute(
                "SELECT * FROM episodes WHERE movie_id = ? ORDER BY episode_number",
                (douban_id,)
            )
            episodes = [dict(r) for r in cursor.fetchall()]
            if episodes:
                movie["episodes"] = episodes
            
            return movie
    
    def list_movies(self) -> List[Dict[str, Any]]:
        """获取所有影片列表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM movies ORDER BY created_at DESC")
            movies = []
            
            for row in cursor.fetchall():
                movie = dict(row)
                
                # 解析 starring
                if movie.get("starring"):
                    try:
                        movie["starring"] = json.loads(movie["starring"])
                    except:
                        movie["starring"] = []
                
                # 获取剧集
                cursor.execute(
                    "SELECT * FROM episodes WHERE movie_id = ? ORDER BY episode_number",
                    (movie["id"],)
                )
                episodes = [dict(r) for r in cursor.fetchall()]
                if episodes:
                    movie["episodes"] = episodes
                
                movies.append(movie)
            
            return movies
    
    def save_movie(self, movie: Dict[str, Any]) -> None:
        """保存单个影片"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            douban_id = movie.get("douban_id") or movie.get("id")
            if not douban_id:
                raise ValueError("Movie must have douban_id or id")
            
            # 处理剧集
            episodes = movie.pop("episodes", [])
            
            # 处理 starring
            starring = movie.get("starring", [])
            if isinstance(starring, list):
                starring = json.dumps(starring, ensure_ascii=False)
            
            # 插入/更新影片
            sql = """
            INSERT INTO movies (
                id, title, media_type, folder, poster_url, local_poster,
                director, writer, starring, genre, country, language, release_date,
                douban_url, rating, status, status_annotate, status_vectorize
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                media_type=excluded.media_type,
                folder=excluded.folder,
                poster_url=excluded.poster_url,
                local_poster=excluded.local_poster,
                director=excluded.director,
                writer=excluded.writer,
                starring=excluded.starring,
                genre=excluded.genre,
                country=excluded.country,
                language=excluded.language,
                release_date=excluded.release_date,
                douban_url=excluded.douban_url,
                rating=excluded.rating,
                status=excluded.status,
                status_annotate=excluded.status_annotate,
                status_vectorize=excluded.status_vectorize,
                updated_at=CURRENT_TIMESTAMP
            """
            
            params = (
                douban_id,
                movie.get("title", ""),
                movie.get("media_type", "movie"),
                movie.get("folder", ""),
                movie.get("poster_url", ""),
                movie.get("local_poster", ""),
                movie.get("director", ""),
                movie.get("writer", ""),
                starring,
                movie.get("genre", ""),
                movie.get("country", ""),
                movie.get("language", ""),
                movie.get("release_date", ""),
                movie.get("douban_url", ""),
                movie.get("rating", ""),
                movie.get("status", "pending"),
                movie.get("status_annotate", "pending"),
                movie.get("status_vectorize", "pending"),
            )
            
            cursor.execute(sql, params)
            
            # 保存剧集
            for ep in episodes:
                ep_sql = """
                INSERT INTO episodes (
                    movie_id, episode_number, video_path, subtitle_path,
                    video_filename, subtitle_filename, status_vectorize
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(movie_id, episode_number) DO UPDATE SET
                    video_path=excluded.video_path,
                    subtitle_path=excluded.subtitle_path,
                    video_filename=excluded.video_filename,
                    subtitle_filename=excluded.subtitle_filename,
                    status_vectorize=excluded.status_vectorize
                """
                
                ep_params = (
                    douban_id,
                    ep.get("episode_number", 0),
                    ep.get("video_path", ""),
                    ep.get("subtitle_path", ""),
                    ep.get("video_filename", ""),
                    ep.get("subtitle_filename", ""),
                    ep.get("status_vectorize", "pending"),
                )
                
                cursor.execute(ep_sql, ep_params)
            
            conn.commit()
    
    def save_movies(self, movies: List[Dict[str, Any]], merge: bool = True) -> None:
        """批量保存影片"""
        if not merge:
            # 清空现有数据（危险操作）
            with self._get_conn() as conn:
                conn.execute("DELETE FROM annotations")
                conn.execute("DELETE FROM episodes")
                conn.execute("DELETE FROM movies")
                conn.commit()
        
        for movie in movies:
            self.save_movie(movie)
    
    def delete_movie(self, douban_id: str) -> bool:
        """
        删除影片（级联删除标注和剧集）
        
        由于外键约束，会自动删除：
        - episodes 表中关联的剧集
        - annotations 表中关联的标注
        - canvas_nodes 表中关联的节点（如果有关联）
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 先删除向量数据（ChromaDB）
            self._delete_vector_data(douban_id)
            
            # 删除影片（级联删除）
            cursor.execute("DELETE FROM movies WHERE id = ?", (douban_id,))
            conn.commit()
            
            return cursor.rowcount > 0
    
    def _delete_vector_data(self, movie_id: str):
        """删除 ChromaDB 中的向量数据"""
        try:
            from ...ingestion.vectorizer import VectorStore
            store = VectorStore()
            store.delete_by_movie(movie_id)
        except Exception as e:
            print(f"[SQLiteStore] 删除向量数据失败: {e}")
    
    def update_metadata(self, douban_id: str, metadata: Dict[str, Any]) -> bool:
        """更新影片元数据"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 构建动态 SQL
            allowed_fields = {
                "title", "media_type", "folder", "poster_url", "local_poster",
                "director", "writer", "genre", "country", "language", 
                "release_date", "douban_url", "rating", "status",
                "status_annotate", "status_vectorize"
            }
            
            updates = []
            params = []
            
            for key, value in metadata.items():
                if key in allowed_fields:
                    updates.append(f"{key} = ?")
                    if key == "starring" and isinstance(value, list):
                        params.append(json.dumps(value, ensure_ascii=False))
                    else:
                        params.append(value)
            
            if not updates:
                return False
            
            params.append(douban_id)
            sql = f"UPDATE movies SET {', '.join(updates)}, updated_at=CURRENT_TIMESTAMP WHERE id = ?"
            
            cursor.execute(sql, params)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def update_episode_metadata(self, douban_id: str, episode_number: int, metadata: Dict[str, Any]) -> bool:
        """更新剧集元数据"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            allowed_fields = {
                "video_path", "subtitle_path", "video_filename", 
                "subtitle_filename", "status_vectorize"
            }
            
            updates = []
            params = []
            
            for key, value in metadata.items():
                if key in allowed_fields:
                    updates.append(f"{key} = ?")
                    params.append(value)
            
            if not updates:
                return False
            
            params.extend([douban_id, episode_number])
            sql = f"UPDATE episodes SET {', '.join(updates)} WHERE movie_id = ? AND episode_number = ?"
            
            cursor.execute(sql, params)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def search_movies(self, **filters) -> List[Dict[str, Any]]:
        """搜索影片"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            where_clauses = []
            params = []
            
            for key, value in filters.items():
                if key in ["title", "director", "genre", "status", "status_annotate"]:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            
            sql = "SELECT * FROM movies"
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
            sql += " ORDER BY created_at DESC"
            
            cursor.execute(sql, params)
            
            movies = []
            for row in cursor.fetchall():
                movie = dict(row)
                if movie.get("starring"):
                    try:
                        movie["starring"] = json.loads(movie["starring"])
                    except:
                        movie["starring"] = []
                movies.append(movie)
            
            return movies
    
    # ============ 标注数据操作 ============
    
    def get_annotations(self, media_id: str, episode_number: Optional[int] = None) -> List[Dict]:
        """获取标注数据"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            if episode_number is not None:
                cursor.execute(
                    """SELECT * FROM annotations 
                       WHERE media_id = ? AND episode_number = ? 
                       ORDER BY line_index""",
                    (media_id, episode_number)
                )
            else:
                cursor.execute(
                    """SELECT * FROM annotations 
                       WHERE media_id = ? AND episode_number IS NULL 
                       ORDER BY line_index""",
                    (media_id,)
                )
            
            results = []
            for row in cursor.fetchall():
                ann = self._row_to_annotation(dict(row))
                results.append(ann)
            
            return results
    
    def _row_to_annotation(self, row: Dict) -> Dict:
        """将数据库行转换为标注格式"""
        # 解析 mashup_tags
        mashup_tags = {}
        if row.get("mashup_tags"):
            try:
                mashup_tags = json.loads(row["mashup_tags"])
            except:
                pass
        
        return {
            "id": row["id"],
            "text": row["text"],
            "vector_text": row.get("vector_text", row["text"]),
            "source": {
                "media_id": f"{row['media_id']}_ep{row['episode_number']}" if row.get("episode_number") else row["media_id"],
                "start": row["start"],
                "end": row["end"]
            },
            "mashup_tags": mashup_tags,
            "semantic_summary": row.get("semantic_summary", ""),
            "editing_params": {
                "duration": row.get("duration", 0)
            },
            "annotated_at": row.get("annotated_at")
        }
    
    def save_annotations(self, media_id: str, annotations: List[Dict], episode_number: Optional[int] = None) -> bool:
        """保存标注数据"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            for idx, ann in enumerate(annotations):
                source = ann.get("source", {})
                mashup_tags = ann.get("mashup_tags", {})
                editing = ann.get("editing_params", {})
                
                sql = """
                INSERT INTO annotations (
                    id, media_id, episode_number, line_index,
                    text, vector_text, start, "end", duration,
                    mashup_tags, semantic_summary, annotated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    text=excluded.text,
                    vector_text=excluded.vector_text,
                    start=excluded.start,
                    "end"=excluded.end,
                    duration=excluded.duration,
                    mashup_tags=excluded.mashup_tags,
                    semantic_summary=excluded.semantic_summary
                """
                
                ann_id = ann.get("id", f"{media_id}_ep{episode_number}_line_{idx}" if episode_number else f"{media_id}_line_{idx}")
                
                params = (
                    ann_id,
                    media_id,
                    episode_number,
                    idx,
                    ann.get("text", ""),
                    ann.get("vector_text", ann.get("text", "")),
                    source.get("start", 0),
                    source.get("end", 0),
                    editing.get("duration", source.get("end", 0) - source.get("start", 0)),
                    json.dumps(mashup_tags, ensure_ascii=False),
                    ann.get("semantic_summary", ""),
                    ann.get("annotated_at")
                )
                
                cursor.execute(sql, params)
            
            # 更新影片标注状态
            cursor.execute(
                "UPDATE movies SET status_annotate = 'done', updated_at=CURRENT_TIMESTAMP WHERE id = ?",
                (media_id,)
            )
            
            conn.commit()
            return True
    
    def delete_annotations(self, media_id: str, episode_number: Optional[int] = None) -> bool:
        """删除标注数据"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            if episode_number is not None:
                cursor.execute(
                    "DELETE FROM annotations WHERE media_id = ? AND episode_number = ?",
                    (media_id, episode_number)
                )
            else:
                cursor.execute(
                    "DELETE FROM annotations WHERE media_id = ?",
                    (media_id,)
                )
            
            conn.commit()
            return cursor.rowcount > 0
    
    # ============ 无限画布操作 ============
    
    def create_canvas(self, canvas_id: str, name: str, description: str = "") -> bool:
        """创建画布"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO canvases (id, name, description) VALUES (?, ?, ?)",
                    (canvas_id, name, description)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def get_canvas(self, canvas_id: str) -> Optional[Dict]:
        """获取画布信息（包含完整树形结构）"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 获取画布
            cursor.execute("SELECT * FROM canvases WHERE id = ?", (canvas_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            canvas = dict(row)
            
            # 获取所有节点（使用递归 CTE 构建树）
            cursor.execute(
                """
                WITH RECURSIVE tree AS (
                    -- 根节点
                    SELECT *, 0 as level, CAST(order AS TEXT) as sort_path
                    FROM canvas_nodes
                    WHERE canvas_id = ? AND parent_id IS NULL
                    
                    UNION ALL
                    
                    -- 子节点
                    SELECT n.*, t.level + 1, t.sort_path || '.' || CAST(n.order AS TEXT)
                    FROM canvas_nodes n
                    JOIN tree t ON n.parent_id = t.id
                    WHERE n.canvas_id = ?
                )
                SELECT * FROM tree ORDER BY sort_path
                """,
                (canvas_id, canvas_id)
            )
            
            nodes = []
            for r in cursor.fetchall():
                node = dict(r)
                if node.get("metadata"):
                    try:
                        node["metadata"] = json.loads(node["metadata"])
                    except:
                        pass
                nodes.append(node)
            
            canvas["nodes"] = self._build_tree(nodes)
            
            # 获取连接
            cursor.execute(
                "SELECT * FROM canvas_edges WHERE canvas_id = ?",
                (canvas_id,)
            )
            canvas["edges"] = [dict(r) for r in cursor.fetchall()]
            
            return canvas
    
    def _build_tree(self, nodes: List[Dict]) -> List[Dict]:
        """将扁平列表构建为树形结构"""
        if not nodes:
            return []
        
        node_map = {n["id"]: n for n in nodes}
        roots = []
        
        for node in nodes:
            node["children"] = []
            if node.get("parent_id") and node["parent_id"] in node_map:
                node_map[node["parent_id"]]["children"].append(node)
            else:
                roots.append(node)
        
        return roots
    
    def save_canvas_node(self, node: Dict) -> bool:
        """保存画布节点"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO canvas_nodes (
                id, canvas_id, parent_id, node_type, title, content,
                annotation_id, "order", path, depth,
                pos_x, pos_y, width, height, color,
                collapsed, locked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                parent_id=excluded.parent_id,
                title=excluded.title,
                content=excluded.content,
                annotation_id=excluded.annotation_id,
                "order"=excluded.order,
                path=excluded.path,
                depth=excluded.depth,
                pos_x=excluded.pos_x,
                pos_y=excluded.pos_y,
                width=excluded.width,
                height=excluded.height,
                color=excluded.color,
                collapsed=excluded.collapsed,
                locked=excluded.locked,
                updated_at=CURRENT_TIMESTAMP
            """
            
            metadata = node.get("metadata", {})
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata, ensure_ascii=False)
            
            params = (
                node["id"],
                node["canvas_id"],
                node.get("parent_id"),
                node.get("node_type", "note"),
                node.get("title", ""),
                node.get("content", ""),
                node.get("annotation_id"),
                node.get("order", 0),
                node.get("path", ""),
                node.get("depth", 0),
                node.get("pos_x"),
                node.get("pos_y"),
                node.get("width"),
                node.get("height"),
                node.get("color"),
                node.get("collapsed", False),
                node.get("locked", False),
            )
            
            cursor.execute(sql, params)
            conn.commit()
            return True
    
    def delete_canvas_node(self, node_id: str) -> bool:
        """删除节点（级联删除子节点）"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM canvas_nodes WHERE id = ?", (node_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def list_canvases(self) -> List[Dict]:
        """列出所有画布"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM canvases ORDER BY updated_at DESC")
            return [dict(r) for r in cursor.fetchall()]
