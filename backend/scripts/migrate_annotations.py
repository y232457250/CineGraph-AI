#!/usr/bin/env python3
"""
标注文件格式迁移工具 v2.0
将旧格式的标注JSON转换为新的精简规范格式

新格式规范 (精简版):
{
  "id": "心花路放_line_042",
  "text": "你敢打我",
  
  "source": {
    "media_id": "心花路放",      // 关联media_index的key
    "start": 1234.5,
    "end": 1236.2
  },
  
  "mashup_tags": {
    "sentence_type": "反问",     // 全中文
    "emotion": "愤怒",
    "tone": "挑衅",
    "primary_function": "反差萌",
    "style_effect": "嚣张跋扈",
    "can_follow": ["威胁", "挑衅", "命令"],
    "can_lead_to": ["反击", "害怕", "嘲讽"],
    "keywords": ["打", "敢"],
    "character_type": "受害者"
  },
  
  "vector_text": "反问 愤怒 挑衅 你敢打我 反击 嘲讽 打 敢",
  
  "editing_params": {
    "rhythm": "快速切梗",
    "duration": 1.7
  },
  
  "semantic_summary": "受害者反击的经典台词",
  "annotated_at": 1234567890.123
}
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List


# 英文→中文映射表
SENTENCE_TYPE_MAP = {
    "question": "问句", "answer": "答句", "command": "命令", "threat": "威胁",
    "counter_question": "反问", "mock": "嘲讽", "refuse": "拒绝", "fear": "害怕",
    "surrender": "求饶", "counter_attack": "反击", "anger": "愤怒", "exclaim": "感叹",
    "persuade": "劝说", "agree": "同意", "action": "行动", "interrupt": "打断",
    "reveal": "揭示", "obey": "服从", "comment": "评论", "shock": "震惊"
}

EMOTION_MAP = {
    "angry": "愤怒", "rage": "狂怒", "fear": "害怕", "mock": "嘲讽",
    "proud": "得意", "arrogant": "嚣张", "helpless": "无奈", "calm": "冷静",
    "shock": "震惊", "funny": "搞笑", "absurd": "荒诞", "tsundere": "傲娇"
}

TONE_MAP = {
    "strong": "强硬", "weak": "软弱", "provocative": "挑衅", "humble": "卑微",
    "arrogant": "傲慢", "questioning": "质疑", "certain": "肯定", "hesitant": "犹豫",
    "pleading": "恳求", "threatening": "威胁"
}

CHARACTER_TYPE_MAP = {
    "emperor": "皇帝", "official": "大臣", "hero": "英雄", "villain": "反派",
    "comic": "搞笑角色", "victim": "受害者", "bystander": "旁观者", "wise": "智者"
}


def to_chinese(value: str, mapping: Dict[str, str]) -> str:
    """将英文标签转换为中文"""
    if not value:
        return value
    # 去除可能的括号注释，如 "答句(answer)" -> "答句"
    clean_value = value.split("(")[0].strip()
    # 如果是英文key，转为中文
    if clean_value.lower() in mapping:
        return mapping[clean_value.lower()]
    # 如果值本身就是中文名称，直接返回
    if clean_value in mapping.values():
        return clean_value
    return clean_value


def migrate_annotation(old: Dict) -> Dict:
    """将旧格式标注转换为新的精简格式"""
    
    # 计算时长
    start = old.get("start", 0)
    end = old.get("end", 0)
    duration = round(end - start, 2) if end > start else 0
    
    # 获取media_id (从source或旧字段)
    source = old.get("source", {})
    media_id = source.get("media_id") or source.get("movie_id") or old.get("source_movie", "")
    if not start and source:
        start = source.get("start", 0)
        end = source.get("end", 0)
        duration = round(end - start, 2) if end > start else 0
    
    # 获取mashup_tags (从嵌套或旧字段)
    tags = old.get("mashup_tags", {})
    
    # 英文→中文转换
    sentence_type = to_chinese(
        tags.get("sentence_type") or old.get("sentence_type", ""), 
        SENTENCE_TYPE_MAP
    )
    emotion = to_chinese(
        tags.get("emotion") or old.get("emotion", ""), 
        EMOTION_MAP
    )
    tone = to_chinese(
        tags.get("tone") or old.get("tone", ""), 
        TONE_MAP
    )
    character_type = to_chinese(
        tags.get("character_type") or old.get("character_type", ""), 
        CHARACTER_TYPE_MAP
    )
    
    # can_follow/can_lead_to 也转中文
    can_follow_raw = tags.get("can_follow") or old.get("can_follow", [])
    can_lead_to_raw = tags.get("can_lead_to") or old.get("can_lead_to", [])
    can_follow = [to_chinese(t, SENTENCE_TYPE_MAP) for t in can_follow_raw]
    can_lead_to = [to_chinese(t, SENTENCE_TYPE_MAP) for t in can_lead_to_raw]
    
    # 获取其他字段
    keywords = tags.get("keywords") or old.get("keywords", [])
    primary_function = tags.get("primary_function") or old.get("primary_function", "")
    style_effect = tags.get("style_effect") or old.get("style_effect", "")
    
    # 获取剪辑参数
    editing = old.get("editing_params", {})
    rhythm = editing.get("rhythm") or old.get("editing_rhythm", "")
    
    # 构建新格式 (精简版)
    new = {
        "id": old.get("id", ""),
        "text": old.get("text", ""),
        
        # 📍 来源定位 (精简)
        "source": {
            "media_id": media_id,
            "start": start,
            "end": end
        },
        
        # 🎭 混剪核心标签 (全中文)
        "mashup_tags": {
            "sentence_type": sentence_type,
            "emotion": emotion,
            "tone": tone,
            "primary_function": primary_function,
            "style_effect": style_effect,
            "can_follow": can_follow,
            "can_lead_to": can_lead_to,
            "keywords": keywords,
            "character_type": character_type
        },
        
        # 🔍 向量化文本 (纯中文)
        "vector_text": generate_vector_text_v2(
            sentence_type, emotion, tone, 
            old.get("text", ""), 
            can_lead_to, keywords
        ),
        
        # 📊 剪辑参数 (精简)
        "editing_params": {
            "rhythm": rhythm,
            "duration": duration
        },
        
        # 语义摘要
        "semantic_summary": old.get("semantic_summary", ""),
        
        # 时间戳
        "annotated_at": old.get("annotated_at", 0)
    }
    
    return new


def generate_vector_text_v2(
    sentence_type: str, emotion: str, tone: str,
    text: str, can_lead_to: List[str], keywords: List[str]
) -> str:
    """生成纯中文的向量化文本"""
    parts = [sentence_type, emotion, tone, text]
    
    if can_lead_to:
        parts.extend(can_lead_to)
    
    if keywords:
        parts.extend(keywords)
    
    return " ".join(filter(None, parts))


def migrate_file(input_path: str, output_path: str = None) -> int:
    """迁移单个标注文件"""
    
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return 0
    
    # 加载旧数据
    with open(input_path, "r", encoding="utf-8") as f:
        old_data = json.load(f)
    
    if not isinstance(old_data, list):
        print(f"❌ 文件格式错误: 期望列表，得到 {type(old_data)}")
        return 0
    
    # 检查是否已经是新的精简格式
    if old_data:
        first = old_data[0]
        source = first.get("source", {})
        # 新精简格式: source只有media_id, start, end
        is_new_format = (
            "source" in first and 
            "mashup_tags" in first and
            "media_id" in source and
            "movie_id" not in source and
            "subtitle_file" not in source
        )
        if is_new_format:
            print(f"ℹ️ 文件已经是精简格式: {input_path}")
            return 0
    
    # 转换
    new_data = [migrate_annotation(ann) for ann in old_data]
    
    # 输出路径
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_migrated.json"
    else:
        output_path = Path(output_path)
    
    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 迁移完成: {input_path} -> {output_path}")
    print(f"   共 {len(new_data)} 条标注")
    
    return len(new_data)


def migrate_directory(dir_path: str, in_place: bool = False) -> int:
    """迁移目录下所有标注文件"""
    
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        print(f"❌ 目录不存在: {dir_path}")
        return 0
    
    total = 0
    json_files = list(dir_path.glob("*_annotated.json"))
    
    print(f"📂 找到 {len(json_files)} 个标注文件")
    
    for f in json_files:
        if "_migrated" in f.name:
            continue
        
        output_path = f if in_place else None
        count = migrate_file(str(f), output_path)
        total += count
    
    return total


def main():
    parser = argparse.ArgumentParser(description="标注文件格式迁移工具")
    parser.add_argument("input", help="输入文件或目录路径")
    parser.add_argument("-o", "--output", help="输出文件路径（仅用于单文件迁移）")
    parser.add_argument("--in-place", action="store_true", help="原地更新文件（目录迁移时）")
    parser.add_argument("--dry-run", action="store_true", help="仅检查，不实际迁移")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔄 标注文件格式迁移工具")
    print("=" * 60)
    
    input_path = Path(args.input)
    
    if args.dry_run:
        print("🔍 干运行模式 - 仅检查文件格式")
        if input_path.is_file():
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and "source" in data[0] and "mashup_tags" in data[0]:
                print(f"✅ {input_path} 已是新格式")
            else:
                print(f"⚠️ {input_path} 需要迁移")
        return
    
    if input_path.is_file():
        migrate_file(str(input_path), args.output)
    elif input_path.is_dir():
        total = migrate_directory(str(input_path), args.in_place)
        print(f"\n📊 总共迁移 {total} 条标注")
    else:
        print(f"❌ 路径不存在: {input_path}")


if __name__ == "__main__":
    main()
