#!/usr/bin/env python3
"""修复 media_index.json 中的数据：
1. 从 folder 字段提取完整的 title
2. starring 只保留前4个演员
3. language 标准化为 中文/英文/其他
"""
import json
import re
from pathlib import Path

def normalize_language(lang_str):
    """将语言字符串简化为：中文、英文、其他、或组合"""
    if not lang_str:
        return "其他"
    
    chinese_keywords = ['汉语', '普通话', '国语', '粤语', '闽南语', '上海话', '四川话', 
                        '陕西话', '东北话', '南京话', '吴语', '客家话', '方言', '中文',
                        '台语', '潮汕话', '湖南话', '河南话', '山东话', '云南方言']
    english_keywords = ['英语', 'English', '英文']
    
    has_chinese = any(kw.lower() in lang_str.lower() for kw in chinese_keywords)
    has_english = any(kw.lower() in lang_str.lower() for kw in english_keywords)
    
    if has_chinese and has_english:
        return "中文 / 英文"
    elif has_chinese:
        return "中文"
    elif has_english:
        return "英文"
    else:
        return "其他"


def main():
    json_path = Path(__file__).parent.parent / "data" / "media_index.json"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"正在修复 {len(data.get('movies', []))} 部电影数据...")
    
    for movie in data.get('movies', []):
        # 从 folder 提取完整 title
        folder = movie.get('folder', '')
        match = re.match(r'^(\d+)[\s\-]+(.+)', folder)
        if match:
            old_title = movie.get('title')
            new_title = match.group(2).strip()
            movie['title'] = new_title
            if old_title != new_title:
                print(f"  Title: '{old_title}' -> '{new_title}'")
        
        # 限制 starring 只取前4个
        if isinstance(movie.get('starring'), list):
            old_count = len(movie['starring'])
            if old_count > 4:
                movie['starring'] = movie['starring'][:4]
                print(f"  Starring: {old_count} -> 4")
        
        # 标准化 language
        if movie.get('language'):
            old_lang = movie['language']
            new_lang = normalize_language(old_lang)
            movie['language'] = new_lang
            if old_lang != new_lang:
                print(f"  Language: '{old_lang}' -> '{new_lang}'")
    
    # 保存
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n修复完成！最终数据：")
    for m in data.get('movies', []):
        starring_str = ", ".join(m.get('starring', []))
        print(f"  {m['douban_id']}: {m['title']} | {m.get('language')} | [{starring_str}]")


if __name__ == '__main__':
    main()
