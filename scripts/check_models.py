#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "backend" / "data" / "cinegraph.db"

def main():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("Model Providers Status")
    print("=" * 70)
    
    cursor.execute('SELECT category, COUNT(*), SUM(CASE WHEN enabled=1 THEN 1 ELSE 0 END) FROM model_providers GROUP BY category')
    for row in cursor.fetchall():
        print(f'{row[0]}: {row[1]} total, {row[2]} enabled')
    
    print()
    print("LLM Models:")
    cursor.execute("SELECT id, name FROM model_providers WHERE category='llm' ORDER BY sort_order")
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f'  {i:2d}. {row[0]:40s} - {row[1]}')
    
    print()
    print("Embedding Models:")
    cursor.execute("SELECT id, name FROM model_providers WHERE category='embedding' ORDER BY sort_order")
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f'  {i:2d}. {row[0]:40s} - {row[1]}')
    
    conn.close()

if __name__ == "__main__":
    main()
