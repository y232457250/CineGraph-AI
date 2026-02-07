# backend/app/ingestion/vectorizer.py
"""
向量化入库模块 - 将标注数据存入ChromaDB
支持单句向量化，用于混剪接话搜索
"""

import os
import json
import time
import yaml
import requests
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️ ChromaDB未安装，请运行: pip install chromadb")


# ==================== 配置 ====================
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_PATH = DATA_DIR / "chroma_db"
EMBEDDING_CONFIG_PATH = CONFIG_DIR / "embedding_providers.yaml"


# ==================== Embedding提供者 ====================
class EmbeddingProvider:
    """Embedding提供者"""
    
    def __init__(self, config: Dict):
        self.name = config.get("name", "Unknown")
        self.type = config.get("type", "local")
        self.base_url = config.get("base_url", "")
        self.model = config.get("model", "")
        self._has_dimension = "dimension" in config
        self.dimension = config.get("dimension", 1536)
        self.timeout = config.get("timeout", 60)
        self.api_style = config.get("api_style", "openai")
        self.truncate = config.get("truncate", True)
        
        # 处理API Key
        api_key = config.get("api_key", "")
        if api_key and api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            self.api_key = os.environ.get(env_var, "")
        else:
            self.api_key = api_key
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """获取文本向量"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        base_url = self.base_url.rstrip("/")
        if self.api_style == "ollama":
            url = f"{base_url}/embed" if base_url.endswith("/api") else f"{base_url}/api/embed"
            payload = {
                "model": self.model,
                "input": texts,
                "truncate": self.truncate
            }
            if self._has_dimension and self.dimension:
                payload["dimensions"] = self.dimension
        else:
            url = f"{base_url}/embeddings"
            payload = {
                "model": self.model,
                "input": texts
            }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            
            # 提取embedding
            if "embeddings" in result:
                return result.get("embeddings", [])
            embeddings = []
            if "data" in result:
                for item in result["data"]:
                    embeddings.append(item["embedding"])
            return embeddings
        except Exception as e:
            raise Exception(f"Embedding调用失败: {e}")
    
    def embed_single(self, text: str) -> List[float]:
        """获取单个文本向量"""
        results = self.embed([text])
        return results[0] if results else []


class EmbeddingManager:
    """Embedding管理器 - 优先从数据库读取，回退到YAML"""
    
    def __init__(self, config_path: Path = EMBEDDING_CONFIG_PATH):
        self.config_path = config_path
        self.providers: Dict[str, Dict] = {}
        self.active_provider: str = ""
        self._use_db = False
        self._load_config()
    
    def _load_config(self):
        """加载配置 - 优先数据库，回退YAML"""
        try:
            self._load_from_db()
            if self.providers:
                self._use_db = True
                return
        except Exception as e:
            print(f"⚠️ 从数据库加载Embedding配置失败，回退到YAML: {e}")
        
        self._load_from_yaml()
    
    def _load_from_db(self):
        """从数据库加载配置"""
        from app.core.model_provider_service import get_model_provider_service
        service = get_model_provider_service()
        
        providers_list = service.list_providers(category='embedding')
        if not providers_list:
            return
        
        self.providers = {}
        for p in providers_list:
            provider_id = p['id']
            config = service.get_provider_config(provider_id)
            if config:
                self.providers[provider_id] = config
                if p.get('is_active'):
                    self.active_provider = provider_id
        
        if not self.active_provider and self.providers:
            self.active_provider = next(iter(self.providers))
        
        print(f"✅ Embedding配置从数据库加载成功，当前使用: {self.active_provider} ({len(self.providers)} 个提供者)")
    
    def _load_from_yaml(self):
        """从YAML文件加载配置（回退方案）"""
        if not self.config_path.exists():
            self._use_default_config()
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            self.active_provider = config.get("active_provider", "local_qwen_embedding")
            
            for key, value in config.items():
                if isinstance(value, dict) and "base_url" in value:
                    self.providers[key] = value
            
            print(f"✅ Embedding配置从YAML加载成功，当前使用: {self.active_provider}")
        except Exception as e:
            print(f"⚠️ Embedding配置加载失败: {e}")
            self._use_default_config()
    
    def _use_default_config(self):
        """使用默认配置"""
        self.active_provider = "local_qwen_embedding"
        self.providers = {
            "local_qwen_embedding": {
                "name": "本地Qwen3-Embedding",
                "type": "local",
                "base_url": "http://localhost:8002/v1",
                "model": "qwen3-embedding-4b",
                "dimension": 2560
            }
        }
    
    def get_provider(self, provider_name: str = None) -> EmbeddingProvider:
        """获取Embedding提供者"""
        name = provider_name or self.active_provider
        if name not in self.providers:
            raise ValueError(f"未知的Embedding提供者: {name}")
        return EmbeddingProvider(self.providers[name])
    
    def get_dimension(self, provider_name: str = None) -> int:
        """获取向量维度"""
        name = provider_name or self.active_provider
        if name in self.providers:
            return self.providers[name].get("dimension", 1536)
        return 1536


# ==================== ChromaDB管理 ====================
class VectorStore:
    """向量数据库管理"""
    
    COLLECTION_NAME = "mashup_lines"
    
    def __init__(self, db_path: Path = CHROMA_DB_PATH):
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB未安装")
        
        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 获取或创建collection
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "台词混剪向量库"}
        )
        
        print(f"✅ ChromaDB初始化成功，当前有 {self.collection.count()} 条记录")
    
    def add_lines(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict]
    ):
        """添加台词向量"""
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        print(f"✅ 已添加 {len(ids)} 条记录")
    
    def upsert_lines(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict]
    ):
        """更新或插入台词向量"""
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        print(f"✅ 已更新/插入 {len(ids)} 条记录")
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Dict = None,
        where_document: Dict = None
    ) -> Dict:
        """搜索相似台词"""
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"]
        )
    
    def search_by_text(
        self,
        query_text: str,
        embedding_provider: EmbeddingProvider,
        n_results: int = 10,
        where: Dict = None
    ) -> List[Dict]:
        """通过文本搜索相似台词"""
        # 获取查询向量
        query_embedding = embedding_provider.embed_single(query_text)
        
        # 搜索
        results = self.search(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where
        )
        
        # 格式化结果
        formatted = []
        if results and results.get("ids"):
            ids = results["ids"][0]
            documents = results["documents"][0] if results.get("documents") else []
            metadatas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []
            
            for i, id_ in enumerate(ids):
                formatted.append({
                    "id": id_,
                    "text": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else 0,
                    "score": 1 - (distances[i] if i < len(distances) else 0)  # 转换为相似度
                })
        
        return formatted
    
    def search_next_line(
        self,
        current_line_id: str,
        embedding_provider: EmbeddingProvider,
        n_results: int = 10
    ) -> List[Dict]:
        """搜索能接的下一句台词"""
        # 获取当前台词信息
        current = self.collection.get(ids=[current_line_id], include=["metadatas"])
        
        if not current or not current.get("metadatas"):
            return []
        
        metadata = current["metadatas"][0]
        can_lead_to = metadata.get("can_lead_to", [])
        
        if not can_lead_to:
            # 如果没有can_lead_to，使用向量相似度搜索
            return self.search_by_text(
                query_text=metadata.get("vector_text", ""),
                embedding_provider=embedding_provider,
                n_results=n_results
            )
        
        # 根据can_lead_to过滤
        # ChromaDB的where查询支持$in操作符
        results = []
        for sentence_type in can_lead_to:
            partial_results = self.search_by_text(
                query_text=metadata.get("vector_text", ""),
                embedding_provider=embedding_provider,
                n_results=n_results // len(can_lead_to) + 1,
                where={"sentence_type": sentence_type}
            )
            results.extend(partial_results)
        
        # 按分数排序并去重
        seen = set()
        unique_results = []
        for r in sorted(results, key=lambda x: x["score"], reverse=True):
            if r["id"] not in seen and r["id"] != current_line_id:
                seen.add(r["id"])
                unique_results.append(r)
        
        return unique_results[:n_results]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        count = self.collection.count()
        
        # 获取电影分布
        all_data = self.collection.get(include=["metadatas"])
        movie_counts = {}
        sentence_type_counts = {}
        emotion_counts = {}
        
        if all_data and all_data.get("metadatas"):
            for meta in all_data["metadatas"]:
                # 电影统计 - 兼容新旧格式
                movie = meta.get("media_id") or meta.get("movie_title") or meta.get("movie_id") or meta.get("source_movie", "unknown")
                movie_counts[movie] = movie_counts.get(movie, 0) + 1
                
                # 句型统计
                st = meta.get("sentence_type", "unknown")
                sentence_type_counts[st] = sentence_type_counts.get(st, 0) + 1
                
                # 情绪统计
                emotion = meta.get("emotion", "unknown")
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        return {
            "total_lines": count,
            "movies": movie_counts,
            "sentence_types": sentence_type_counts,
            "emotions": emotion_counts
        }
    
    def delete_by_movie(self, movie_name: str):
        """删除某部电影的所有台词"""
        # 尝试新格式 (media_id)
        try:
            self.collection.delete(where={"media_id": movie_name})
        except:
            pass
        # 兼容旧格式
        try:
            self.collection.delete(where={"movie_id": movie_name})
        except:
            pass
        try:
            self.collection.delete(where={"source_movie": movie_name})
        except:
            pass
        print(f"✅ 已删除电影 '{movie_name}' 的所有台词")
    
    def reset(self):
        """重置数据库"""
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "台词混剪向量库"}
        )
        print("✅ 向量库已重置")


# ==================== 向量化器 ====================
class Vectorizer:
    """向量化器 - 将标注数据向量化并存入ChromaDB"""
    
    def __init__(self, embedding_provider: str = None):
        self.embedding_manager = EmbeddingManager()
        
        if embedding_provider:
            self.embedding_manager.active_provider = embedding_provider
        
        self.embedding = self.embedding_manager.get_provider()
        self.store = VectorStore()
    
    def vectorize_annotations(
        self,
        annotations_path: str,
        batch_size: int = 50,
        progress_callback=None
    ) -> int:
        """向量化标注文件并存入数据库"""
        
        # 加载标注数据
        with open(annotations_path, "r", encoding="utf-8") as f:
            annotations = json.load(f)
        
        if not annotations:
            print("❌ 标注文件为空")
            return 0
        
        total = len(annotations)
        print(f"📊 开始向量化 {total} 条标注...")
        
        start_time = time.time()
        processed = 0
        
        # 分批处理
        for i in range(0, total, batch_size):
            batch = annotations[i:i+batch_size]
            
            # 准备数据
            ids = []
            texts = []
            documents = []
            metadatas = []
            
            for ann in batch:
                line_id = ann.get("id", f"line_{i}")
                
                # 使用vector_text进行向量化，如果没有则使用text
                vector_text = ann.get("vector_text", ann.get("text", ""))
                
                ids.append(line_id)
                texts.append(vector_text)
                documents.append(ann.get("text", ""))
                
                # 获取嵌套的source和mashup_tags
                source = ann.get("source", {})
                mashup_tags = ann.get("mashup_tags", {})
                editing_params = ann.get("editing_params", {})
                
                # 兼容旧格式 (source)
                if not source:
                    source = {
                        "media_id": ann.get("source_movie", "") or ann.get("movie_id", ""),
                        "start": ann.get("start", 0),
                        "end": ann.get("end", 0)
                    }
                
                # 兼容旧格式 (mashup_tags)
                if not mashup_tags:
                    mashup_tags = {
                        "sentence_type": ann.get("sentence_type", ""),
                        "emotion": ann.get("emotion", ""),
                        "tone": ann.get("tone", ""),
                        "character_type": ann.get("character_type", ""),
                        "can_follow": ann.get("can_follow", []),
                        "can_lead_to": ann.get("can_lead_to", []),
                        "keywords": ann.get("keywords", []),
                        "primary_function": ann.get("primary_function", ""),
                        "style_effect": ann.get("style_effect", "")
                    }
                
                # 元数据 - 精简版 (用于搜索过滤)
                metadatas.append({
                    "text": ann.get("text", ""),
                    # 来源信息 (精简)
                    "media_id": source.get("media_id", "") or source.get("movie_id", ""),
                    "start": source.get("start", 0),
                    "end": source.get("end", 0),
                    # 混剪标签 (核心)
                    "sentence_type": mashup_tags.get("sentence_type", ""),
                    "emotion": mashup_tags.get("emotion", ""),
                    "tone": mashup_tags.get("tone", ""),
                    "character_type": mashup_tags.get("character_type", ""),
                    "can_follow": json.dumps(mashup_tags.get("can_follow", []), ensure_ascii=False),
                    "can_lead_to": json.dumps(mashup_tags.get("can_lead_to", []), ensure_ascii=False),
                    "keywords": json.dumps(mashup_tags.get("keywords", []), ensure_ascii=False),
                    "primary_function": mashup_tags.get("primary_function", ""),
                    "style_effect": mashup_tags.get("style_effect", ""),
                    # 剪辑参数 (精简)
                    "rhythm": editing_params.get("rhythm", ""),
                    "duration": editing_params.get("duration", 0)
                })
            
            # 获取向量
            try:
                embeddings = self.embedding.embed(texts)
            except Exception as e:
                print(f"❌ 批次 {i//batch_size + 1} 向量化失败: {e}")
                continue
            
            # 存入数据库
            try:
                self.store.upsert_lines(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
            except Exception as e:
                print(f"❌ 批次 {i//batch_size + 1} 存储失败: {e}")
                continue
            
            processed += len(batch)
            
            # 进度回调
            if progress_callback:
                progress_callback(processed, total)
            
            # 控制台进度
            if (i // batch_size + 1) % 5 == 0 or i + batch_size >= total:
                elapsed = time.time() - start_time
                speed = processed / elapsed if elapsed > 0 else 0
                print(f"🔄 进度: {processed}/{total} ({processed/total:.1%}) | 速度: {speed:.1f}条/秒")
        
        print(f"✅ 向量化完成！共处理 {processed} 条，耗时 {time.time() - start_time:.1f}秒")
        
        return processed
    
    def search(
        self,
        query: str,
        n_results: int = 10,
        filters: Dict = None
    ) -> List[Dict]:
        """搜索台词"""
        return self.store.search_by_text(
            query_text=query,
            embedding_provider=self.embedding,
            n_results=n_results,
            where=filters
        )
    
    def find_next_lines(
        self,
        current_line_id: str,
        n_results: int = 10
    ) -> List[Dict]:
        """查找能接的下一句"""
        return self.store.search_next_line(
            current_line_id=current_line_id,
            embedding_provider=self.embedding,
            n_results=n_results
        )
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.store.get_stats()


# ==================== CLI ====================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="台词向量化入库工具")
    parser.add_argument("action", choices=["vectorize", "search", "stats", "reset"],
                       help="操作类型: vectorize=向量化, search=搜索, stats=统计, reset=重置")
    parser.add_argument("--input", help="标注JSON文件路径 (vectorize模式)")
    parser.add_argument("--query", help="搜索查询 (search模式)")
    parser.add_argument("--limit", type=int, default=10, help="结果数量")
    parser.add_argument("--batch-size", type=int, default=50, help="批处理大小")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎬 台词向量化工具")
    print("=" * 60)
    
    vectorizer = Vectorizer()
    
    if args.action == "vectorize":
        if not args.input:
            print("❌ 请指定输入文件: --input <path>")
            return
        vectorizer.vectorize_annotations(args.input, batch_size=args.batch_size)
    
    elif args.action == "search":
        if not args.query:
            print("❌ 请指定搜索查询: --query <text>")
            return
        
        results = vectorizer.search(args.query, n_results=args.limit)
        print(f"\n🔍 搜索结果 ({len(results)} 条):")
        for i, r in enumerate(results):
            meta = r['metadata']
            # 兼容新旧格式
            movie = meta.get('media_id') or meta.get('movie_title') or meta.get('movie_id') or meta.get('source_movie', '未知')
            print(f"\n{i+1}. [{movie}]")
            print(f"   台词: {r['text']}")
            print(f"   句型: {meta.get('sentence_type', '')} | 情绪: {meta.get('emotion', '')}")
            print(f"   相似度: {r['score']:.2%}")
    
    elif args.action == "stats":
        stats = vectorizer.get_stats()
        print(f"\n📊 向量库统计:")
        print(f"   总台词数: {stats['total_lines']}")
        print(f"\n   电影分布:")
        for movie, count in stats.get("movies", {}).items():
            print(f"     {movie}: {count} 条")
        print(f"\n   句型分布:")
        for st, count in list(stats.get("sentence_types", {}).items())[:10]:
            print(f"     {st}: {count} 条")
    
    elif args.action == "reset":
        confirm = input("⚠️ 确定要重置向量库吗？这将删除所有数据！(y/N): ")
        if confirm.lower() == 'y':
            vectorizer.store.reset()
        else:
            print("已取消")


if __name__ == "__main__":
    main()
