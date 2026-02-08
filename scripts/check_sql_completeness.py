#!/usr/bin/env python3
"""
检查SQL脚本的完整性
"""
import re
from pathlib import Path
from collections import defaultdict

SQL_FILE = Path(__file__).parent.parent / "docs" / "cinegraph_database_schema.sql"

def count_insert_rows(sql_content, table_name):
    """统计INSERT语句的行数"""
    pattern = rf'INSERT INTO {table_name}\b[^;]+;'
    matches = re.findall(pattern, sql_content, re.IGNORECASE | re.DOTALL)
    
    total_rows = 0
    for sql in matches:
        # 计算VALUES后面的元组数量 (通过),(来统计)
        # 去除注释
        sql_clean = re.sub(r'--[^\n]*', '', sql)
        # 计算),(的数量+1
        total_rows += sql_clean.count('),(') + 1
    
    return len(matches), total_rows

def extract_tag_categories(sql_content):
    """提取tag_categories中定义的类别"""
    pattern = r"INSERT INTO tag_categories\s*\([^)]+\)\s*VALUES\s*([^;]+);"
    match = re.search(pattern, sql_content, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    
    values_str = match.group(1)
    # 提取每个元组的第一个字段（id）
    ids = re.findall(r"'([^']+)'\s*,\s*'", values_str)
    return ids

def extract_tag_definitions_by_category(sql_content):
    """按类别统计tag_definitions"""
    pattern = r"INSERT INTO tag_definitions\s*\([^)]+\)\s*VALUES\s*([^;]+);"
    matches = re.findall(pattern, sql_content, re.IGNORECASE | re.DOTALL)
    
    categories = defaultdict(int)
    for values_str in matches:
        # 提取每个元组的第二个字段（category_id）
        rows = re.findall(r"'[^']+'\s*,\s*'([^']+)'", values_str)
        for cat in rows:
            categories[cat] += 1
    
    return dict(categories)

def main():
    print("=" * 70)
    print("SQL脚本完整性检查")
    print("=" * 70)
    
    if not SQL_FILE.exists():
        print(f"错误: 找不到文件 {SQL_FILE}")
        return 1
    
    sql_content = SQL_FILE.read_text(encoding='utf-8')
    
    # 检查核心表
    print("\n【一、核心配置表数据】")
    tables = [
        ('tag_categories', '标签类别'),
        ('tag_definitions', '标签定义'),
        ('tag_connection_rules', '标签连接规则'),
        ('tag_hierarchy', '标签层级关系'),
        ('tag_constraints', '标签约束规则'),
        ('tag_localization', '标签多语言'),
        ('culture_specific_tags', '文化特定标签'),
        ('model_providers', '模型提供者'),
        ('annotation_strategies', '标注策略'),
        ('ingestion_profiles', '入库配置'),
        ('annotation_prompt_templates', '提示词模板'),
    ]
    
    for table, name in tables:
        stmt_count, row_count = count_insert_rows(sql_content, table)
        status = "OK" if row_count > 0 else "MISSING"
        print(f"  [{status}] {name:20s} ({table:30s}): {stmt_count} statements, {row_count} rows")
    
    # 检查tag_categories
    print("\n【二、标签类别详情】")
    categories = extract_tag_categories(sql_content)
    print(f"  共定义 {len(categories)} 个类别:")
    for i, cat in enumerate(categories, 1):
        print(f"    {i:2d}. {cat}")
    
    # 检查tag_definitions分布
    print("\n【三、标签定义分布】")
    tag_dist = extract_tag_definitions_by_category(sql_content)
    total_tags = sum(tag_dist.values())
    print(f"  共定义 {total_tags} 个标签:")
    for cat, count in sorted(tag_dist.items()):
        print(f"    - {cat:25s}: {count:3d} 个标签")
    
    # 检查是否所有类别都有标签定义
    print("\n【四、完整性检查】")
    missing_defs = set(categories) - set(tag_dist.keys())
    if missing_defs:
        print(f"  警告: 以下类别缺少标签定义:")
        for cat in missing_defs:
            print(f"    - {cat}")
    else:
        print(f"  [OK] 所有 {len(categories)} 个类别都有标签定义")
    
    # 检查lines表字段
    print("\n【五、Lines表字段检查】")
    lines_schema = re.search(r'CREATE TABLE lines \((.+?)\);', sql_content, re.DOTALL | re.IGNORECASE)
    if lines_schema:
        schema_text = lines_schema.group(1)
        fields = re.findall(r'^\s*(\w+)\s+', schema_text, re.MULTILINE)
        print(f"  Lines表共 {len(fields)} 个字段:")
        # 分类显示
        basic = [f for f in fields if f in ['id', 'line_id', 'movie_id', 'episode_number', 'line_index', 'text', 'clean_text', 'vector_text', 'start_time', 'end_time', 'duration', 'character_name', 'character_id']]
        layer1 = [f for f in fields if f in ['sentence_type', 'can_follow', 'can_lead_to', 'emotion', 'emotion_transition', 'tone', 'character_type']]
        layer2 = [f for f in fields if f in ['context_dye', 'context_intensity', 'subtext_type', 'subtext_description', 'is_meme', 'meme_name', 'meme_popularity', 'social_function', 'surface_sentiment', 'actual_sentiment', 'sentiment_polarity']]
        layer3 = [f for f in fields if f in ['metaphor_category', 'metaphor_keyword', 'metaphor_direction', 'metaphor_strength', 'semantic_field']]
        algo = [f for f in fields if f in ['intensity', 'hook_score', 'ambiguity', 'viral_potential', 'tags_json']]
        vector = [f for f in fields if f in ['vectorized', 'vector_id']]
        meta = [f for f in fields if f in ['annotated_by', 'annotated_at', 'annotation_confidence', 'is_signature', 'is_catchphrase', 'signature_score', 'created_at', 'updated_at']]
        
        print(f"    基础字段: {len(basic)} 个")
        print(f"    第一层: {len(layer1)} 个")
        print(f"    第二层: {len(layer2)} 个")
        print(f"    第三层: {len(layer3)} 个")
        print(f"    算法字段: {len(algo)} 个")
        print(f"    向量化: {len(vector)} 个")
        print(f"    元数据: {len(meta)} 个")
    
    print("\n" + "=" * 70)
    print("检查完成!")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    exit(main())
