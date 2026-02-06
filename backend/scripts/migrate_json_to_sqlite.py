#!/usr/bin/env python3
"""
数据迁移脚本：从 JSON 迁移到 SQLite

功能：
1. 初始化新的 SQLite 数据库
2. 从 media_index.json 迁移影片数据
3. 从 annotations/ 目录迁移标注数据
4. 保留原有的 JSON 文件作为备份

使用方法：
    python backend/scripts/migrate_json_to_sqlite.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def migrate_movies(unified_store, json_store):
    """迁移影片数据"""
    print("\n📽️  迁移影片数据...")
    
    movies = json_store.list_movies()
    print(f"   发现 {len(movies)} 个影片")
    
    migrated = 0
    failed = 0
    
    for movie in movies:
        try:
            # 转换字段名以适配新模型
            movie_data = {
                'id': movie.get('douban_id') or movie.get('id'),
                'douban_id': movie.get('douban_id') or movie.get('id'),
                'title': movie.get('title', ''),
                'original_title': movie.get('original_title', ''),
                'year': movie.get('year'),
                'media_type': movie.get('media_type', 'movie'),
                'folder': movie.get('folder', ''),
                'poster_url': movie.get('poster_url', ''),
                'local_poster': movie.get('local_poster', ''),
                'director': movie.get('director', ''),
                'writer': movie.get('writer', ''),
                'starring': movie.get('starring', []),
                'genre': movie.get('genre', ''),
                'country': movie.get('country', ''),
                'language': movie.get('language', ''),
                'release_date': movie.get('release_date', ''),
                'douban_url': movie.get('douban_url', ''),
                'rating': movie.get('rating', ''),
                'crossover_genre': movie.get('crossover_genre', ''),
                'status': movie.get('status', 'pending'),
                'status_annotate': movie.get('status_annotate', 'pending'),
                'status_vectorize': movie.get('status_vectorize', 'pending'),
                'import_batch': movie.get('import_batch', ''),
                'episodes': movie.get('episodes', [])
            }
            
            unified_store.save_movie(movie_data)
            migrated += 1
            
            if migrated % 10 == 0:
                print(f"   已迁移 {migrated}/{len(movies)}...")
                
        except Exception as e:
            print(f"   ❌ 迁移失败 {movie.get('title', 'unknown')}: {e}")
            failed += 1
    
    print(f"   ✅ 成功: {migrated}, ❌ 失败: {failed}")
    return migrated


def migrate_annotations(unified_store, annotations_dir):
    """迁移标注数据"""
    print("\n📝 迁移标注数据...")
    
    if not annotations_dir.exists():
        print("   ⚠️  标注目录不存在，跳过")
        return 0
    
    annotation_files = list(annotations_dir.glob("*_annotated.json"))
    print(f"   发现 {len(annotation_files)} 个标注文件")
    
    migrated = 0
    failed = 0
    
    for ann_file in annotation_files:
        try:
            # 解析文件名获取 movie_id 和 episode_number
            # 格式: {movie_id}_ep{N}_annotated.json 或 {movie_id}_annotated.json
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
            
            print(f"   ✅ {filename}: {count} 条标注")
            
        except Exception as e:
            print(f"   ❌ 迁移失败 {ann_file.name}: {e}")
            failed += 1
    
    print(f"   ✅ 成功迁移 {migrated} 条标注, ❌ 失败: {failed}")
    return migrated


def create_backup(data_dir):
    """创建备份"""
    print("\n💾 创建备份...")
    
    backup_dir = data_dir / "backup" / f"pre_sqlite_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 备份 media_index.json
    media_index = data_dir / "media_index.json"
    if media_index.exists():
        import shutil
        shutil.copy(media_index, backup_dir / "media_index.json")
        print(f"   ✅ 已备份 media_index.json")
    
    # 备份 annotations
    annotations_dir = data_dir / "annotations"
    if annotations_dir.exists():
        import shutil
        backup_annotations = backup_dir / "annotations"
        shutil.copytree(annotations_dir, backup_annotations)
        print(f"   ✅ 已备份 annotations/")
    
    print(f"   📁 备份位置: {backup_dir}")
    return backup_dir


def main():
    """主函数"""
    print("=" * 60)
    print("CineGraph-AI 数据迁移工具")
    print("JSON → SQLite")
    print("=" * 60)
    
    # 路径
    data_dir = backend_dir / "data"
    db_path = data_dir / "cinegraph.db"
    media_index_path = data_dir / "media_index.json"
    annotations_dir = data_dir / "annotations"
    
    # 检查源数据
    if not media_index_path.exists():
        print("\n❌ 未找到 media_index.json，无法迁移")
        return 1
    
    print(f"\n📁 数据目录: {data_dir}")
    print(f"🎯 数据库: {db_path}")
    print(f"📄 影片数据: {media_index_path}")
    print(f"📝 标注数据: {annotations_dir}")
    
    # 确认
    print("\n⚠️  此操作将：")
    print("   1. 初始化新的 SQLite 数据库")
    print("   2. 从 JSON 导入所有数据")
    print("   3. 创建备份（保留原文件）")
    print("\n原 JSON 文件不会被删除，可作为备份。")
    
    confirm = input("\n是否继续？(yes/no): ")
    if confirm.lower() != 'yes':
        print("已取消")
        return 0
    
    # 创建备份
    backup_dir = create_backup(data_dir)
    
    # 初始化数据库
    print("\n🗄️  初始化数据库...")
    from app.models.database import init_database
    
    config_path = backend_dir.parent / "config" / "mashup_v5_config.json"
    
    try:
        manager = init_database(str(db_path), str(config_path))
        print("   ✅ 数据库初始化完成")
    except Exception as e:
        print(f"   ❌ 数据库初始化失败: {e}")
        return 1
    
    # 获取存储实例
    from app.core.store import get_unified_store
    from app.core.store.json_store import JsonMovieStore
    
    unified_store = get_unified_store()
    json_store = JsonMovieStore(media_index_path)
    
    # 迁移数据
    movie_count = migrate_movies(unified_store, json_store)
    annotation_count = migrate_annotations(unified_store, annotations_dir)
    
    # 显示结果
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print(f"\n✅ 已迁移:")
    print(f"   - 影片: {movie_count} 个")
    print(f"   - 标注: {annotation_count} 条")
    print(f"\n💾 备份位置: {backup_dir}")
    print(f"\n📝 下一步:")
    print("   1. 重启后端服务（已自动使用 SQLite）")
    print("   2. 验证数据完整性")
    print("   3. 确认无误后可删除备份（可选）")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
