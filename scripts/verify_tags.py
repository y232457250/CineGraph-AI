#!/usr/bin/env python3
"""
验证数据库标签数据
"""
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "data" / "cinegraph.db"

def verify_tags():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 60)
    print("CineGraph-AI 标签系统验证报告")
    print("=" * 60)
    
    # 1. 标签类别统计
    print("\n【一、标签类别统计】")
    cursor.execute('SELECT id, name, layer, is_required FROM tag_categories ORDER BY layer, sort_order')
    categories = cursor.fetchall()
    for cat in categories:
        required = "必填" if cat['is_required'] else "可选"
        print(f"  Layer{cat['layer']} - {cat['id']}: {cat['name']} ({required})")
    
    # 2. 各分类标签详情
    print("\n【二、标签定义详情】")
    for cat in categories:
        cat_id = cat['id']
        cat_name = cat['name']
        cursor.execute('''
            SELECT value, display_name, description 
            FROM tag_definitions 
            WHERE category_id=? AND is_active=1 
            ORDER BY sort_order
        ''', (cat_id,))
        tags = cursor.fetchall()
        print(f"\n  >> {cat_name} ({cat_id}) - {len(tags)} tags:")
        for tag in tags:
            desc = tag['description'] or ''
            print(f"      {tag['value']:20s} = {tag['display_name']:15s}  {desc}")
    
    # 3. 标签连接规则
    print("\n【三、标签连接规则】")
    cursor.execute('SELECT COUNT(*) as count FROM tag_connection_rules WHERE is_active=1')
    count = cursor.fetchone()['count']
    print(f"  活跃规则数: {count}")
    
    # 显示部分规则示例
    cursor.execute('''
        SELECT from_category_id, from_tag_id, to_category_id, to_tag_id, 
               connection_type, weight, description
        FROM tag_connection_rules 
        WHERE is_active=1 
        LIMIT 10
    ''')
    rules = cursor.fetchall()
    print("  规则示例:")
    for rule in rules:
        print(f"    {rule['from_category_id']}.{rule['from_tag_id']} -> [{rule['connection_type']}({rule['weight']})] -> {rule['to_category_id']}.{rule['to_tag_id']}")
    
    # 4. 标签层级关系
    print("\n【四、标签层级关系】")
    cursor.execute('SELECT COUNT(*) as count FROM tag_hierarchy')
    count = cursor.fetchone()['count']
    print(f"  层级关系数: {count}")
    
    # 5. 标签约束规则
    print("\n【五、标签约束规则】")
    cursor.execute('''
        SELECT category_id, constraint_type, tag_ids, constraint_message 
        FROM tag_constraints 
        WHERE is_active=1
    ''')
    constraints = cursor.fetchall()
    print(f"  约束规则数: {len(constraints)}")
    for c in constraints:
        print(f"    [{c['constraint_type']}] {c['category_id']}: {c['constraint_message']}")
    
    # 6. 多语言支持
    print("\n【六、多语言支持】")
    cursor.execute('SELECT language_code, COUNT(*) as count FROM tag_localization GROUP BY language_code')
    langs = cursor.fetchall()
    for lang in langs:
        print(f"  {lang['language_code']}: {lang['count']}个标签")
    
    # 7. 文化特定标签
    print("\n【七、文化特定标签】")
    cursor.execute('''
        SELECT c.id, c.tag_id, t.display_name as tag_name, c.specific_meaning
        FROM culture_specific_tags c
        JOIN tag_definitions t ON c.tag_id = t.id
        WHERE c.culture_code = 'zh-CN'
    ''')
    cultures = cursor.fetchall()
    for c in cultures:
        print(f"  {c['tag_name']}: {c['specific_meaning']}")
    
    # 8. 标注策略
    print("\n【八、标注策略】")
    cursor.execute('''
        SELECT id, name, description, annotation_depth, included_tag_categories, batch_size, is_default
        FROM annotation_strategies
        WHERE is_active=1
        ORDER BY batch_size DESC
    ''')
    strategies = cursor.fetchall()
    for s in strategies:
        default_mark = " [默认]" if s['is_default'] else ""
        print(f"  >> {s['name']}{default_mark}")
        print(f"    描述: {s['description']}")
        print(f"    深度: {s['annotation_depth']}, 批大小: {s['batch_size']}")
        import json
        categories = json.loads(s['included_tag_categories'])
        print(f"    包含类别: {', '.join(categories)}")
    
    # 9. 模型提供者
    print("\n【九、模型提供者】")
    cursor.execute('''
        SELECT category, id, name, provider_type, is_active
        FROM model_providers
        WHERE enabled=1
        ORDER BY category, sort_order
    ''')
    models = cursor.fetchall()
    current_category = None
    for m in models:
        if m['category'] != current_category:
            current_category = m['category']
            print(f"  >> {current_category.upper()}:")
        active_mark = " [激活]" if m['is_active'] else ""
        print(f"    - {m['id']}: {m['name']} ({m['provider_type']}){active_mark}")
    
    # 10. 统计汇总
    print("\n【十、统计汇总】")
    cursor.execute('SELECT COUNT(*) as count FROM tag_definitions WHERE is_active=1')
    total_tags = cursor.fetchone()['count']
    cursor.execute('SELECT COUNT(DISTINCT category_id) as count FROM tag_definitions WHERE is_active=1')
    total_categories = cursor.fetchone()['count']
    
    print(f"  标签类别数: {total_categories}")
    print(f"  活跃标签数: {total_tags}")
    print(f"  连接规则数: {count}")
    print(f"  层级关系数: {cursor.execute('SELECT COUNT(*) FROM tag_hierarchy').fetchone()[0]}")
    print(f"  约束规则数: {len(constraints)}")
    print(f"  多语言标签: {sum(lang['count'] for lang in langs)}")
    print(f"  文化特定标签: {len(cultures)}")
    print(f"  标注策略数: {len(strategies)}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("验证完成！")
    print("=" * 60)

if __name__ == "__main__":
    verify_tags()
