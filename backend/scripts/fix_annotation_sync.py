#!/usr/bin/env python3
"""
修复标注数据同步问题：将JSON标注文件导入SQLite数据库
"""

import json
import sys
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.store import get_unified_store

def migrate_annotations():
    """迁移标注数据"""
    data_dir = backend_dir / "data"
    annotations_dir = data_dir / "annotations"
    
    if not annotations_dir.exists():
        print("[ERROR] 标注目录不存在")
        return 0
    
    annotation_files = list(annotations_dir.glob("*_annotated.json"))
    print(f"[INFO] 发现 {len(annotation_files)} 个标注文件")
    
    unified_store = get_unified_store()
    migrated = 0
    failed = 0
    
    for ann_file in annotation_files:
        try:
            # 解析文件名获取 movie_id 和 episode_number
            filename = ann_file.stem  # 去掉 .json
            parts = filename.replace('_annotated', '').split('_ep')
            
            movie_id = parts[0]
            episode_number = int(parts[1]) if len(parts) > 1 else None
            
            # 读取标注数据
            with open(ann_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            
            # 迁移到数据库
            count = unified_store.save_annotations(movie_id, annotations, episode_number)
            migrated += count
            
            print(f"[OK] {filename}: {count} 条标注已导入")
            
        except Exception as e:
            print(f"[ERROR] 迁移失败 {ann_file.name}: {e}")
            failed += 1
    
    print(f"\n[SUCCESS] 成功导入 {migrated} 条标注, 失败: {failed}")
    return migrated

if __name__ == "__main__":
    migrate_annotations()
