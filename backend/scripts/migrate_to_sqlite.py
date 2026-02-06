#!/usr/bin/env python3
"""
数据迁移脚本：从 JSON 迁移到 SQLite
使用：python migrate_to_sqlite.py [--dry-run]
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_data_dir() -> Path:
    """获取数据目录"""
    return Path(__file__).parent.parent / "data"


def init_database(db_path: Path) -> sqlite3.Connection:
    """初始化数据库"""
    schema_path = Path(__file__).parent.parent / "app" / "database" / "schema.sql"
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    
    return conn


def migrate_movies(conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """迁移影片数据"""
    index_file = get_data_dir() / "media_index.json"
    
    if not index_file.exists():
        print("[ERROR] media_index.json not found")
        return 0
    
    with open(index_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    movies = data.get("movies", [])
    migrated = 0
    
    cursor = conn.cursor()
    
    for movie in movies:
        movie_id = movie.get("douban_id", "")
        if not movie_id:
            continue
        
        # 处理剧集
        episodes = movie.pop("episodes", [])
        
        # 解析 starring
        starring = movie.get("starring", [])
        if isinstance(starring, list):
            starring = json.dumps(starring, ensure_ascii=False)
        
        # 插入电影
        sql = """
        INSERT OR REPLACE INTO movies (
            id, title, media_type, folder, poster_url, local_poster,
            director, writer, starring, genre, country, language, release_date,
            douban_url, rating, status, status_annotate, status_vectorize
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            movie_id,
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
        
        if not dry_run:
            cursor.execute(sql, params)
        
        # 插入剧集
        for ep in episodes:
            ep_sql = """
            INSERT OR REPLACE INTO episodes (
                movie_id, episode_number, video_path, subtitle_path,
                video_filename, subtitle_filename, status_vectorize
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            ep_params = (
                movie_id,
                ep.get("episode_number", 0),
                ep.get("video_path", ""),
                ep.get("subtitle_path", ""),
                ep.get("video_filename", ""),
                ep.get("subtitle_filename", ""),
                ep.get("status_vectorize", "pending"),
            )
            
            if not dry_run:
                cursor.execute(ep_sql, ep_params)
        
        migrated += 1
        print(f"  [OK] {movie.get('title', movie_id)} - {len(episodes)} episodes")
    
    if not dry_run:
        conn.commit()
    
    return migrated


def migrate_annotations(conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """迁移标注数据"""
    annotations_dir = get_data_dir() / "annotations"
    
    if not annotations_dir.exists():
        print("❌ annotations 目录不存在")
        return 0
    
    cursor = conn.cursor()
    migrated = 0
    total_lines = 0
    
    for json_file in annotations_dir.glob("*_annotated.json"):
        # 解析文件名
        name = json_file.stem.replace("_annotated", "")
        
        if "_ep" in name:
            parts = name.rsplit("_ep", 1)
            media_id = parts[0]
            try:
                episode_number = int(parts[1])
            except ValueError:
                episode_number = None
        else:
            media_id = name
            episode_number = None
        
        # 读取标注
        with open(json_file, "r", encoding="utf-8") as f:
            annotations = json.load(f)
        
        if not isinstance(annotations, list):
            continue
        
        # 插入每行标注
        for idx, ann in enumerate(annotations):
            # 提取 source 信息
            source = ann.get("source", {})
            if not source:
                source = {
                    "media_id": ann.get("movie_id", media_id),
                    "start": ann.get("start", 0),
                    "end": ann.get("end", 0)
                }
            
            # 提取 mashup_tags
            mashup_tags = ann.get("mashup_tags", {})
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
                    "style_effect": ann.get("style_effect", ""),
                }
            
            # 提取 editing_params
            editing = ann.get("editing_params", {})
            duration = editing.get("duration", source.get("end", 0) - source.get("start", 0))
            
            sql = """
            INSERT OR REPLACE INTO annotations (
                id, media_id, episode_number, line_index,
                text, vector_text, start, "end", duration,
                mashup_tags, semantic_summary, annotated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            ann_id = ann.get("id", f"{name}_line_{idx}")
            
            params = (
                ann_id,
                media_id,
                episode_number,
                idx,
                ann.get("text", ""),
                ann.get("vector_text", ann.get("text", "")),
                source.get("start", 0),
                source.get("end", 0),
                duration,
                json.dumps(mashup_tags, ensure_ascii=False),
                ann.get("semantic_summary", ""),
                ann.get("annotated_at")
            )
            
            if not dry_run:
                cursor.execute(sql, params)
            
            total_lines += 1
        
        migrated += 1
        print(f"  [OK] {json_file.name} - {len(annotations)} lines")
    
    if not dry_run:
        conn.commit()
    
    print(f"\n[STATS] Total: {migrated} files, {total_lines} annotation lines")
    return migrated


def main():
    import argparse
    parser = argparse.ArgumentParser(description="迁移数据到 SQLite")
    parser.add_argument("--dry-run", action="store_true", help="试运行，不实际写入")
    parser.add_argument("--backup", action="store_true", default=True, help="备份原数据")
    args = parser.parse_args()
    
    print("=" * 60)
    print("CineGraph AI Data Migration Tool")
    print("=" * 60)
    
    db_path = get_data_dir() / "cinegraph.db"
    
    if args.dry_run:
        print("\n[DRY RUN] Simulation mode, no actual writes\n")
    else:
        print(f"\n[DB] Database path: {db_path}\n")
        
        # 备份
        if args.backup and db_path.exists():
            backup_path = db_path.with_suffix(".db.backup")
            backup_path.write_bytes(db_path.read_bytes())
            print(f"[BACKUP] Original database backed up to: {backup_path}\n")
    
    # 连接数据库
    if args.dry_run:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        # 加载 schema
        schema_path = Path(__file__).parent.parent / "app" / "database" / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    else:
        conn = init_database(db_path)
    
    # 迁移影片
    print("\n[Migrating] Movies data...")
    movie_count = migrate_movies(conn, args.dry_run)
    print(f"[Done] Migrated {movie_count} movies")
    
    # 迁移标注
    print("\n[Migrating] Annotations data...")
    ann_count = migrate_annotations(conn, args.dry_run)
    print(f"[Done] Migrated {ann_count} annotation files")
    
    # 验证
    if not args.dry_run:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        movies_in_db = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM annotations")
        lines_in_db = cursor.fetchone()[0]
        
        print("\n" + "=" * 60)
        print("[RESULT] Migration Summary:")
        print(f"   Movies: {movies_in_db}")
        print(f"   Annotation lines: {lines_in_db}")
        print("=" * 60)
    
    conn.close()
    
    print("\n[SUCCESS] Migration completed!")
    if args.dry_run:
        print("\nHint: Remove --dry-run flag to execute actual migration")


if __name__ == "__main__":
    main()
