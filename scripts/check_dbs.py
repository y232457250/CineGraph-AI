#!/usr/bin/env python3
import sqlite3
import os
from pathlib import Path

def check_db(db_path, name):
    print(f'\n=== {name} ===')
    print(f'Path: {db_path}')
    if not os.path.exists(db_path):
        print('Status: NOT EXISTS')
        return
    
    size = os.path.getsize(db_path)
    print(f'Size: {size / 1024:.1f} KB')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查表数量
    cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
    table_count = cursor.fetchone()[0]
    print(f'Tables: {table_count}')
    
    # 检查标签定义数量
    try:
        cursor.execute('SELECT count(*) FROM tag_definitions WHERE is_active=1')
        tag_count = cursor.fetchone()[0]
        print(f'Active Tags: {tag_count}')
    except:
        print('Active Tags: N/A')
    
    # 检查台词数量
    try:
        cursor.execute('SELECT count(*) FROM lines')
        line_count = cursor.fetchone()[0]
        print(f'Lines: {line_count}')
    except:
        print('Lines: N/A')
    
    # 检查影片数量
    try:
        cursor.execute('SELECT count(*) FROM movies')
        movie_count = cursor.fetchone()[0]
        print(f'Movies: {movie_count}')
    except:
        print('Movies: N/A')
    
    conn.close()

root = Path(__file__).parent.parent
check_db(root / 'data' / 'cinegraph.db', 'Root data/cinegraph.db')
check_db(root / 'backend' / 'data' / 'cinegraph.db', 'Backend backend/data/cinegraph.db')
