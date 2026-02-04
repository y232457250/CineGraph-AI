# backend/app/ingestion/__init__.py
"""
数据摄入模块
- enricher: 豆瓣元数据抓取
- semantic_annotator: 语义标注
- vectorizer: 向量化入库
"""

from .enricher import start_enrichment, get_status
