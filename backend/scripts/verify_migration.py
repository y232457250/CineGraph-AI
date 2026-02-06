#!/usr/bin/env python3
"""验证迁移结果"""
import sqlite3
import sys
from pathlib import Path

def verify():
    db_path = Path(__file__).parent.parent / "data" / "cinegraph.db"
    
    if not db_path.exists():
        print("[ERROR] Database not found!")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("Verification Report")
    print("=" * 60)
    
    # 检查表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"\n[Tables] {len(tables)} tables found:")
    for t in tables:
        print(f"  - {t}")
    
    # 检查数据
    cursor.execute('SELECT COUNT(*) FROM movies')
    movies = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM annotations')
    annotations = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM episodes')
    episodes = cursor.fetchone()[0]
    
    print(f"\n[Data Count]")
    print(f"  Movies: {movies}")
    print(f"  Episodes: {episodes}")
    print(f"  Annotations: {annotations}")
    
    # 检查样例
    print(f"\n[Sample Movies]")
    cursor.execute('SELECT id, title, media_type, status_annotate FROM movies LIMIT 5')
    for r in cursor.fetchall():
        print(f"  {r[0]}: {r[1]} ({r[2]}) - annotate:{r[3]}")
    
    # 检查标注样例
    print(f"\n[Sample Annotations]")
    cursor.execute('SELECT id, media_id, text FROM annotations LIMIT 3')
    for r in cursor.fetchall():
        text = r[2][:30] + "..." if len(r[2]) > 30 else r[2]
        print(f"  {r[0]}: {text}")
    
    # 检查外键约束
    print(f"\n[Foreign Keys]")
    cursor.execute('PRAGMA foreign_keys')
    fk_enabled = cursor.fetchone()[0]
    print(f"  Foreign key enforcement: {'ON' if fk_enabled else 'OFF'}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("Verification completed successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    verify()
