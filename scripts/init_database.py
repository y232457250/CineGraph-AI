#!/usr/bin/env python3
"""
初始化 SQLite 数据库脚本
用法: python init_database.py
"""

import sqlite3
import os
import sys
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
SQL_FILE = BASE_DIR / "docs" / "cinegraph_database_schema.sql"
DB_FILE = BASE_DIR / "data" / "cinegraph.db"

def init_database():
    """初始化数据库"""
    print("=" * 60)
    print("CineGraph-AI 数据库初始化工具")
    print("=" * 60)
    
    # 检查 SQL 文件是否存在
    if not SQL_FILE.exists():
        print(f"错误: SQL 文件不存在: {SQL_FILE}")
        print("请确保 docs/cinegraph_database_schema.sql 文件存在")
        return False
    
    print(f"SQL 文件: {SQL_FILE}")
    print(f"数据库将创建在: {DB_FILE}")
    
    # 创建 data 目录
    DB_FILE.parent.mkdir(exist_ok=True)
    
    # 如果数据库已存在，询问是否覆盖
    if DB_FILE.exists():
        response = input(f"\n数据库已存在: {DB_FILE}\n是否覆盖? (y/n): ")
        if response.lower() != 'y':
            print("取消初始化")
            return False
        # 备份旧数据库
        backup_file = DB_FILE.with_suffix('.db.bak')
        os.rename(DB_FILE, backup_file)
        print(f"已备份旧数据库到: {backup_file}")
    
    try:
        # 读取 SQL 文件
        print("\n正在读取 SQL 文件...")
        with open(SQL_FILE, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # 创建数据库并执行 SQL
        print("正在创建数据库...")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 执行 SQL 脚本
        cursor.executescript(sql_script)
        conn.commit()
        
        # 验证创建结果
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print("\n" + "=" * 60)
        print(f"数据库创建成功！")
        print("=" * 60)
        print(f"\n共创建 {len(tables)} 个表:")
        
        # 分类显示表
        categories = {
            '系统/配置': ['system_config', 'app_settings', 'tag_categories', 'tag_definitions', 'tag_connection_rules'],
            '用户': ['users', 'user_sessions'],
            '影片': ['movies', 'episodes'],
            '语义标注': ['lines', 'characters', 'vectorization_queue'],
            '搜索': ['search_history'],
            '画布': ['projects', 'canvas_nodes', 'canvas_edges', 'sequences', 'sequence_items'],
            'LLM': ['llm_model_configs', 'llm_chat_sessions', 'llm_chat_messages', 'semantic_matches', 'creative_paths', 'annotation_strategies', 'annotation_prompt_templates', 'annotation_examples'],
            '日志': ['operation_logs', 'usage_stats']
        }
        
        table_names = [t[0] for t in tables]
        
        for category, table_list in categories.items():
            found = [t for t in table_list if t in table_names]
            if found:
                print(f"\n  [{category}]")
                for t in found:
                    print(f"    OK {t}")
        
        # 检查是否有未分类的表
        categorized = set()
        for tables in categories.values():
            categorized.update(tables)
        uncategorized = [t for t in table_names if t not in categorized]
        if uncategorized:
            print(f"\n  [其他]")
            for t in uncategorized:
                print(f"    OK {t}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("下一步操作:")
        print("=" * 60)
        print(f"1. 在 VS Code 中右键点击: {DB_FILE}")
        print("2. 选择 'Open with SQLite Viewer' 查看数据库")
        print("3. 开始开发！")
        print("=" * 60)
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n错误: 数据库操作失败 - {e}")
        return False
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
