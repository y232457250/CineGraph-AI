#!/usr/bin/env python3
"""
同步标签定义到数据库
从 docs/cinegraph_database_schema.sql 提取标签数据并导入到数据库
"""
import sqlite3
import re
import json
from pathlib import Path

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_SCHEMA = PROJECT_ROOT / "docs" / "cinegraph_database_schema.sql"
DATA_DB = PROJECT_ROOT / "data" / "cinegraph.db"
BACKEND_DB = PROJECT_ROOT / "backend" / "data" / "cinegraph.db"

def extract_insert_statements(sql_content, table_name):
    """从SQL内容中提取INSERT语句"""
    # 匹配 INSERT INTO table_name VALUES ... 语句
    pattern = rf"INSERT INTO {table_name}\s+VALUES\s*([^;]+);"
    matches = re.findall(pattern, sql_content, re.IGNORECASE | re.DOTALL)
    
    statements = []
    for match in matches:
        # 处理多行INSERT
        values_str = match.strip()
        statements.append(values_str)
    
    return statements

def parse_values(values_str):
    """解析VALUES字符串为元组列表"""
    # 这是一个简化的解析器，处理基本的SQL值
    values_list = []
    
    # 按), (分割多个值组
    # 首先去掉最外层的括号
    values_str = values_str.strip()
    if values_str.startswith('('):
        values_str = values_str[1:]
    if values_str.endswith(')'):
        values_str = values_str[:-1]
    
    # 使用正则表达式分割值组
    # 处理括号嵌套的情况
    depth = 0
    current = []
    chars = []
    
    i = 0
    while i < len(values_str):
        char = values_str[i]
        
        if char == '(':
            depth += 1
            if depth == 1:
                chars = []
            else:
                chars.append(char)
        elif char == ')':
            depth -= 1
            if depth == 0:
                current.append(''.join(chars).strip())
                values_list.append(tuple(parse_single_value(v.strip()) for v in split_values(current[-1])))
                current = []
            else:
                chars.append(char)
        elif depth > 0:
            chars.append(char)
        
        i += 1
    
    return values_list

def split_values(values_str):
    """分割单个值组中的值"""
    values = []
    depth = 0
    current = []
    in_string = False
    string_char = None
    
    i = 0
    while i < len(values_str):
        char = values_str[i]
        
        if not in_string and char in "'\"":
            in_string = True
            string_char = char
        elif in_string and char == string_char:
            # 检查是否是转义
            if i + 1 < len(values_str) and values_str[i + 1] == string_char:
                current.append(char)
                i += 1
            else:
                in_string = False
                string_char = None
        elif not in_string and char == ',':
            values.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
        
        i += 1
    
    if current:
        values.append(''.join(current).strip())
    
    return values

def parse_single_value(value_str):
    """解析单个SQL值"""
    value_str = value_str.strip()
    
    # 字符串
    if (value_str.startswith("'") and value_str.endswith("'")) or \
       (value_str.startswith('"') and value_str.endswith('"')):
        return value_str[1:-1].replace("''", "'").replace('""', '"')
    
    # NULL
    if value_str.upper() == 'NULL':
        return None
    
    # 数字
    try:
        if '.' in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        pass
    
    # 布尔值
    if value_str.upper() == 'TRUE':
        return True
    if value_str.upper() == 'FALSE':
        return False
    
    return value_str

def extract_tag_data_from_sql(sql_content):
    """从SQL内容中提取所有标签相关数据"""
    data = {
        'tag_categories': [],
        'tag_definitions': [],
        'tag_connection_rules': [],
        'tag_hierarchy': [],
        'tag_constraints': [],
        'tag_localization': [],
        'culture_specific_tags': [],
        'model_providers': [],
        'annotation_strategies': [],
        'ingestion_profiles': [],
    }
    
    # 使用正则表达式提取INSERT语句
    insert_pattern = r"INSERT INTO (\w+)\s*\(([^)]+)\)\s*VALUES\s*([^;]+);"
    matches = re.findall(insert_pattern, sql_content, re.IGNORECASE | re.DOTALL)
    
    for table_name, columns, values_str in matches:
        table_name = table_name.lower()
        if table_name not in data:
            continue
        
        columns = [c.strip() for c in columns.split(',')]
        
        # 解析值
        # 找到所有的值组
        value_groups = []
        depth = 0
        start = 0
        in_string = False
        string_char = None
        
        for i, char in enumerate(values_str):
            if not in_string and char in "'\"":
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                if i + 1 < len(values_str) and values_str[i + 1] == string_char:
                    continue
                in_string = False
            elif not in_string:
                if char == '(':
                    if depth == 0:
                        start = i + 1
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth == 0:
                        value_str = values_str[start:i]
                        value_groups.append(parse_value_tuple(value_str))
        
        data[table_name].extend(value_groups)
    
    return data

def parse_value_tuple(value_str):
    """解析值元组"""
    values = []
    depth = 0
    current = []
    in_string = False
    string_char = None
    
    i = 0
    while i < len(value_str):
        char = value_str[i]
        
        if not in_string and char in "'\"":
            in_string = True
            string_char = char
            current.append(char)
        elif in_string:
            current.append(char)
            if char == string_char:
                # 检查是否是转义
                if i + 1 < len(value_str) and value_str[i + 1] == string_char:
                    i += 1
                    current.append(values_str[i])
                else:
                    in_string = False
        elif char == '(':
            depth += 1
            current.append(char)
        elif char == ')':
            depth -= 1
            current.append(char)
        elif char == ',' and depth == 0:
            values.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
        
        i += 1
    
    if current:
        values.append(''.join(current).strip())
    
    # 解析每个值
    return [parse_single_value(v) for v in values]

def sync_to_database(db_path, data):
    """同步数据到数据库"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0].lower() for row in cursor.fetchall()}
    
    # 要同步的表（按顺序）
    tables_to_sync = [
        ('tag_categories', ['id', 'name', 'description', 'layer', 'icon', 'color', 'is_editable', 'is_required', 'is_multi_select', 'sort_order', 'is_active']),
        ('tag_definitions', ['id', 'category_id', 'value', 'display_name', 'description', 'color', 'icon', 'can_follow', 'can_lead_to', 'related_tags', 'llm_hints', 'example_phrases', 'importance_score', 'rarity_score', 'cultural_context', 'genre_specificity', 'is_builtin', 'is_active', 'sort_order', 'usage_count']),
        ('tag_connection_rules', ['from_category_id', 'from_tag_id', 'to_category_id', 'to_tag_id', 'connection_type', 'weight', 'description', 'condition_text', 'is_active']),
        ('tag_hierarchy', ['parent_tag_id', 'child_tag_id', 'relation_type', 'weight']),
        ('tag_constraints', ['category_id', 'constraint_type', 'tag_ids', 'constraint_message', 'is_active']),
        ('tag_localization', ['tag_id', 'language_code', 'display_name', 'description', 'cultural_note']),
        ('culture_specific_tags', ['id', 'tag_id', 'culture_code', 'specific_meaning', 'example_lines']),
        ('model_providers', ['id', 'name', 'category', 'provider_type', 'local_mode', 'base_url', 'model', 'api_key', 'max_tokens', 'temperature', 'timeout', 'dimension', 'api_style', 'description', 'price_info', 'is_active', 'is_default', 'sort_order', 'enabled', 'extra_config']),
        ('annotation_strategies', ['id', 'name', 'description', 'applicable_scenes', 'annotation_depth', 'included_tag_categories', 'llm_model_id', 'batch_size', 'concurrent_requests', 'is_default', 'is_active']),
        ('ingestion_profiles', ['id', 'name', 'description', 'profile_type', 'model_provider_id', 'batch_size', 'concurrent_requests', 'max_retries', 'retry_delay', 'timeout', 'save_interval', 'annotation_depth', 'included_tag_categories', 'chunk_overlap', 'normalize_embeddings', 'is_default', 'is_active']),
    ]
    
    for table_name, columns in tables_to_sync:
        if table_name not in existing_tables:
            print(f"  WARN: Table {table_name} not found, skip")
            continue
        
        if table_name not in data or not data[table_name]:
            print(f"  WARN: No data for {table_name}, skip")
            continue
        
        # 清空现有数据（保留用户自定义的）
        if table_name == 'tag_definitions':
            cursor.execute(f"DELETE FROM {table_name} WHERE is_builtin = 1")
        elif table_name == 'model_providers':
            cursor.execute(f"DELETE FROM {table_name} WHERE is_default = 1")
        elif table_name in ['tag_categories', 'annotation_strategies', 'ingestion_profiles']:
            cursor.execute(f"DELETE FROM {table_name}")
        elif table_name in ['tag_connection_rules', 'tag_hierarchy', 'tag_constraints', 'tag_localization', 'culture_specific_tags']:
            cursor.execute(f"DELETE FROM {table_name}")
        
        # 插入新数据
        placeholders = ', '.join(['?' for _ in columns])
        sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        rows = data[table_name]
        inserted = 0
        
        for row in rows:
            # 确保行数据长度与列数匹配
            if len(row) < len(columns):
                row = list(row) + [None] * (len(columns) - len(row))
            elif len(row) > len(columns):
                row = row[:len(columns)]
            
            try:
                cursor.execute(sql, row)
                inserted += 1
            except sqlite3.Error as e:
                print(f"    ERROR: Insert failed: {e}")
                print(f"       数据: {row}")
        
        print(f"  OK: {table_name}: {inserted} rows inserted")
    
    conn.commit()
    conn.close()
    print(f"\nOK: Data synced to: {db_path}")

def simple_sync(db_path, sql_file):
    """简单的同步方法：直接执行SQL文件的INSERT语句"""
    print(f"\nSyncing tags to: {db_path}")
    
    if not db_path.exists():
        print(f"  ERROR: Database not found: {db_path}")
        return False
    
    if not sql_file.exists():
        print(f"  ERROR: SQL file not found: {sql_file}")
        return False
    
    # 读取SQL文件
    sql_content = sql_file.read_text(encoding='utf-8')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 要执行的INSERT语句（按顺序）
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
    
    for table in tables:
        # 提取并执行INSERT语句
        pattern = rf"(INSERT INTO {table}\s*\([^)]+\)\s*VALUES\s*\([^)]+\);)"
        matches = re.findall(pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        if not matches:
            # 尝试另一种格式：INSERT INTO table VALUES (...)
            pattern = rf"(INSERT INTO {table}\s+VALUES\s+\([^)]+\);)"
            matches = re.findall(pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        if matches:
            # 先清空表中的内置数据
            try:
                if table == 'tag_definitions':
                    cursor.execute("DELETE FROM tag_definitions WHERE is_builtin = 1 OR is_builtin IS NULL")
                elif table == 'model_providers':
                    cursor.execute("DELETE FROM model_providers WHERE is_default = 1 OR is_default IS NULL")
                elif table in ['tag_connection_rules', 'tag_hierarchy', 'tag_constraints', 
                              'tag_localization', 'culture_specific_tags']:
                    cursor.execute(f"DELETE FROM {table}")
                elif table in ['tag_categories', 'annotation_strategies']:
                    cursor.execute(f"DELETE FROM {table}")
                conn.commit()
            except sqlite3.Error as e:
                print(f"  WARN: Clear {table} failed: {e}")
            
            # 执行INSERT语句
            count = 0
            for sql in matches:
                try:
                    cursor.execute(sql)
                    count += 1
                except sqlite3.Error as e:
                    # 可能是重复键，忽略
                    pass
            
            conn.commit()
            print(f"  OK: {table}: {count} statements")
        else:
            print(f"  WARN: {table}: No INSERT statements found")
    
    conn.close()
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("CineGraph-AI Tag System Sync Tool")
    print("=" * 60)
    
    # 检查SQL文件
    if not DOCS_SCHEMA.exists():
        print(f"ERROR: SQL file not found: {DOCS_SCHEMA}")
        return 1
    
    print(f"SQL File: {DOCS_SCHEMA}")
    
    # 同步到 data/cinegraph.db
    if DATA_DB.exists():
        simple_sync(DATA_DB, DOCS_SCHEMA)
    else:
        print(f"\nWARN: Data database not found: {DATA_DB}")
    
    # 同步到 backend/data/cinegraph.db
    if BACKEND_DB.exists():
        simple_sync(BACKEND_DB, DOCS_SCHEMA)
    else:
        print(f"\nWARN: Backend database not found: {BACKEND_DB}")
        print("  Please run: cd backend && python scripts/init_database.py")
    
    print("\n" + "=" * 60)
    print("Sync completed!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit(main())
