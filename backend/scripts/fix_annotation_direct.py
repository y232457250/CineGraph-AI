#!/usr/bin/env python3
"""
直接修复标注数据：将JSON标注文件导入SQLite数据库
绕过复杂的模块导入
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# 路径配置
backend_dir = Path(__file__).parent.parent
data_dir = backend_dir / "data"
db_path = data_dir / "cinegraph.db"
annotations_dir = data_dir / "annotations"

def parse_annotation_file(filename):
    """解析标注文件名，提取movie_id和episode_number"""
    # 格式: {movie_id}_ep{N}_annotated.json 或 {movie_id}_annotated.json
    stem = filename.replace('_annotated.json', '')
    parts = stem.split('_ep')
    
    movie_id = parts[0]
    episode_number = int(parts[1]) if len(parts) > 1 else None
    return movie_id, episode_number

def migrate_annotations():
    """迁移标注数据到SQLite"""
    
    if not db_path.exists():
        print(f"[ERROR] 数据库不存在: {db_path}")
        return 0
    
    if not annotations_dir.exists():
        print(f"[ERROR] 标注目录不存在: {annotations_dir}")
        return 0
    
    annotation_files = list(annotations_dir.glob("*_annotated.json"))
    print(f"[INFO] 发现 {len(annotation_files)} 个标注文件")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 检查lines表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lines'")
    if not cursor.fetchone():
        print("[ERROR] lines表不存在，请先初始化数据库")
        conn.close()
        return 0
    
    migrated = 0
    failed = 0
    
    for ann_file in annotation_files:
        try:
            movie_id, episode_number = parse_annotation_file(ann_file.name)
            
            # 读取标注数据
            with open(ann_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            
            if not isinstance(annotations, list):
                print(f"[WARN] {ann_file.name}: 格式不正确，跳过")
                continue
            
            # 插入数据
            for idx, ann in enumerate(annotations):
                try:
                    # 生成line_id
                    ep_suffix = f"_ep{episode_number}" if episode_number else ""
                    line_id = f"{movie_id}{ep_suffix}_line_{idx}"
                    
                    # 提取基础字段
                    text = ann.get('text', '')
                    vector_text = ann.get('vector_text', '')
                    start_time = ann.get('source', {}).get('start', 0)
                    end_time = ann.get('source', {}).get('end', 0)
                    
                    # 提取标签字段
                    tags = ann.get('mashup_tags', {})
                    sentence_type = tags.get('sentence_type', '')
                    emotion = tags.get('emotion', '')
                    tone = tags.get('tone', '')
                    character_type = tags.get('character_type', '')
                    
                    # 检查是否已存在
                    cursor.execute(
                        "SELECT id FROM lines WHERE line_id = ?",
                        (line_id,)
                    )
                    if cursor.fetchone():
                        # 更新现有记录
                        cursor.execute("""
                            UPDATE lines SET 
                                text = ?, vector_text = ?, start_time = ?, end_time = ?,
                                sentence_type = ?, emotion = ?, tone = ?, character_type = ?,
                                updated_at = ?
                            WHERE line_id = ?
                        """, (
                            text, vector_text, start_time, end_time,
                            sentence_type, emotion, tone, character_type,
                            datetime.utcnow().isoformat(),
                            line_id
                        ))
                    else:
                        # 插入新记录
                        cursor.execute("""
                            INSERT INTO lines (
                                line_id, movie_id, episode_number, line_index,
                                text, vector_text, start_time, end_time,
                                sentence_type, emotion, tone, character_type,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            line_id, movie_id, episode_number, idx,
                            text, vector_text, start_time, end_time,
                            sentence_type, emotion, tone, character_type,
                            datetime.utcnow().isoformat(),
                            datetime.utcnow().isoformat()
                        ))
                    
                    migrated += 1
                    
                except Exception as e:
                    print(f"[ERROR] 插入记录失败 {ann_file.name} idx={idx}: {e}")
                    failed += 1
            
            print(f"[OK] {ann_file.name}: {len(annotations)} 条标注已导入")
            
        except Exception as e:
            print(f"[ERROR] 迁移失败 {ann_file.name}: {e}")
            failed += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n[SUCCESS] 成功导入 {migrated} 条标注, 失败: {failed}")
    return migrated

if __name__ == "__main__":
    migrate_annotations()
