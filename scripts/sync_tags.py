#!/usr/bin/env python3
"""
同步标签定义到数据库 - 简化版
"""
import sqlite3
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_SCHEMA = PROJECT_ROOT / "docs" / "cinegraph_database_schema.sql"
DATA_DB = PROJECT_ROOT / "data" / "cinegraph.db"
BACKEND_DB = PROJECT_ROOT / "backend" / "data" / "cinegraph.db"

def execute_sql_inserts(db_path, sql_content, table_names):
    """执行指定表的INSERT语句"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    results = {}
    
    for table in table_names:
        # 匹配INSERT语句（跨多行）
        pattern = rf'INSERT INTO {table}\b[^;]+;'
        matches = re.findall(pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        if matches:
            # 先清空表
            try:
                if table == 'tag_definitions':
                    cursor.execute("DELETE FROM tag_definitions WHERE is_builtin = 1 OR is_builtin IS NULL")
                elif table == 'model_providers':
                    cursor.execute("DELETE FROM model_providers WHERE is_default = 1 OR is_default IS NULL")
                elif table in ['tag_connection_rules', 'tag_hierarchy', 'tag_constraints', 
                              'tag_localization', 'culture_specific_tags']:
                    cursor.execute(f"DELETE FROM {table}")
                elif table in ['tag_categories', 'annotation_strategies', 'ingestion_profiles']:
                    cursor.execute(f"DELETE FROM {table}")
                conn.commit()
            except sqlite3.Error as e:
                print(f"  WARN: Clear {table} failed: {e}")
            
            # 执行INSERT
            count = 0
            for sql in matches:
                try:
                    cursor.execute(sql)
                    count += 1
                except sqlite3.Error as e:
                    if 'UNIQUE constraint failed' in str(e):
                        pass  # 忽略重复键错误
                    else:
                        print(f"    ERROR in {table}: {e}")
            
            conn.commit()
            results[table] = count
        else:
            results[table] = 0
    
    conn.close()
    return results

def sync_database(db_path):
    """同步单个数据库"""
    print(f"\nSyncing to: {db_path}")
    
    if not db_path.exists():
        print(f"  ERROR: Database not found")
        return
    
    sql_content = DOCS_SCHEMA.read_text(encoding='utf-8')
    
    tables = [
        'tag_categories',
        'tag_definitions', 
        'tag_connection_rules',
        'tag_hierarchy',
        'tag_constraints',
        'tag_localization',
        'culture_specific_tags',
        'model_providers',
        'annotation_strategies',
        'ingestion_profiles',
    ]
    
    results = execute_sql_inserts(db_path, sql_content, tables)
    
    for table, count in results.items():
        status = "OK" if count > 0 else "WARN"
        print(f"  [{status}] {table}: {count} statements")

def main():
    print("=" * 60)
    print("CineGraph-AI Tag System Sync")
    print("=" * 60)
    
    if not DOCS_SCHEMA.exists():
        print(f"ERROR: SQL file not found: {DOCS_SCHEMA}")
        return 1
    
    # 同步到 data/cinegraph.db
    if DATA_DB.exists():
        sync_database(DATA_DB)
    else:
        print(f"\nWARN: Data DB not found: {DATA_DB}")
    
    # 同步到 backend/data/cinegraph.db
    if BACKEND_DB.exists():
        sync_database(BACKEND_DB)
    else:
        print(f"\nWARN: Backend DB not found: {BACKEND_DB}")
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit(main())
