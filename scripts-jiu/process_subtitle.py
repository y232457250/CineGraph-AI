# scripts-jiu/process_subtitle_optimized.py
import os
import re
import json
import argparse
import time
import sys
from typing import List, Dict, Tuple
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
LLM_API = "http://localhost:8001/v1/completions"
CONFIG_PATH = r"D:\AI\CineGraph-AI\config\mashup_optimized_config.json"

# 优化后的标签体系 - 减少重复，增加多样性
DEFAULT_MASHUP_CONFIG = {
    "version": "v4.0-mashup-optimized",
    
    # 核心功能标签（一级标签，控制使用频率）
    "primary_functions": [
        "强行解释", "身份反转", "场景嫁接", "金句引用", 
        "跨服聊天", "反差萌", "一本正经胡说", "降维打击",
        "时代错位", "次元突破", "神转折", "废话文学"
    ],
    
    # 风格/效果标签（二级标签，增加细分）
    "style_effects": [
        "反讽高级黑", "自嘲解构", "谐音梗王", "双关大师",
        "夸张比喻", "正话反说", "无效沟通", "蜜汁自信",
        "弱小可怜", "嚣张跋扈", "傲娇口嫌", "凡尔赛文学"
    ],
    
    # 连接方式（增加多样性）
    "connection_types": [
        "接反转", "接质疑", "接自嘲", "接玩梗",
        "接冷场", "接爆发", "接解释", "接吐槽",
        "接求饶", "接傲娇", "接装傻", "接暴怒"
    ],
    
    # 剪辑节奏（标准化）
    "editing_rhythms": [
        "快速切梗", "慢放打脸", "重复鬼畜", "戛然而止",
        "递进夸张", "突然打断", "画外音怼", "画面神配"
    ],
    
    # 跨界类型（防止重复组合）
    "crossover_genres": [
        {"type": "古装+科幻", "example": "《甄嬛传》+《星际穿越》"},
        {"type": "动画+现实", "example": "《海绵宝宝》+职场剧"},
        {"type": "武侠+现代", "example": "《笑傲江湖》+办公室"},
        {"type": "恐怖+喜剧", "example": "《咒怨》+《家有儿女》"},
        {"type": "日漫+国剧", "example": "《火影忍者》+《还珠格格》"},
        {"type": "欧美+古风", "example": "《权力的游戏》+《三国演义》"}
    ],
    
    # 音效库（丰富音效建议）
    "sound_effects": [
        "变速处理", "回声效果", "混响处理", "电子变声",
        "环境音突显", "BGM骤停", "音效叠加", "静音反差"
    ]
}

def load_mashup_config() -> dict:
    config = DEFAULT_MASHUP_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            for key in config.keys():
                if key in user_config and user_config[key]:
                    config[key] = user_config[key]
            print(f"✅ 优化配置加载成功: 版本 {config['version']}")
        except Exception as e:
            print(f"⚠️ 配置文件解析失败，使用默认配置: {e}")
    return config

MASHUP_CONFIG = load_mashup_config()
CONFIG_VERSION = MASHUP_CONFIG["version"]

# ==================== 优化提示词 ====================
def build_optimized_prompt(current_line: str, context_lines: List[str]) -> str:
    """
    优化版混剪提示词 - 强调多样性和实用性
    """
    
    primary_funcs = ", ".join(MASHUP_CONFIG["primary_functions"])
    style_effects = ", ".join(MASHUP_CONFIG["style_effects"])
    connections = ", ".join(MASHUP_CONFIG["connection_types"])
    rhythms = ", ".join(MASHUP_CONFIG["editing_rhythms"])
    sound_effects = ", ".join(MASHUP_CONFIG["sound_effects"])
    
    # 随机选择跨界类型示例（避免每次相同）
    import random
    crossover_samples = random.sample(MASHUP_CONFIG["crossover_genres"], 3)
    crossover_examples = "\n".join([f"- {item['type']}: {item['example']}" for item in crossover_samples])
    
    return f"""
### 🎬 混剪创作潜力分析 - 优化版 ###

## 📋 你的角色
你是资深影视混剪UP主，擅长制作跨作品、无厘头、搞笑向的混剪视频。

## 🎯 核心任务
分析以下台词在**脱离原片语境**后的混剪潜力。忘记台词在原片中的意思，专注于：
1. 在其他作品中能产生什么搞笑效果？
2. 适合用什么剪辑手法？
3. 能和什么类型的作品/台词拼接？

## ⚠️ 多样性要求（必须遵守）
1. **避免标签堆砌**：不要过度使用"强行解释"和"降智打击"
2. **创意多样化**：提供2种不同风格的创意示例，避免重复组合
3. **连接多样化**：根据台词特点选择合适的连接方式，不只是"接求饶"
4. **音效多样化**：除了"变速处理"，提供更多音效建议

## 📝 分析对象
当前台词: "{current_line}"
上下文: {json.dumps(context_lines, ensure_ascii=False)[:150]}...

## 🏷️ 标签库参考
核心功能: {primary_funcs}
风格效果: {style_effects}
连接方式: {connections}
剪辑节奏: {rhythms}
音效建议: {sound_effects}

跨界类型示例:
{crossover_examples}

## 📊 输出格式（严格JSON）
{{
  "mashup_analysis": {{
    // 核心标签（精简，用于快速筛选）
    "quick_tags": {{
      "primary": "主要功能（从核心功能中选择，避免重复使用）",
      "style": "风格效果（从风格效果中选择，精准匹配）",
      "connection": "连接方式（从连接方式中选择，多样化）",
      "rhythm": "剪辑节奏（从剪辑节奏中选择）"
    }},
    
    // 语义摘要（用于向量化搜索）
    "semantic_summary": {{
      "brief": "一句简短描述（20字以内）",
      "keywords": ["关键词1", "关键词2", "关键词3"],
      "humor_style": "幽默风格描述",
      "use_case": "适用场景描述"
    }},
    
    // 创意参数（用于参考）
    "creative_params": {{
      "crossover_types": ["跨界类型1", "跨界类型2"],
      "audio_suggestions": ["音效建议1", "音效建议2"],
      "visual_suggestions": ["画面建议1", "画面建议2"]
    }},
    
    // 创意示例（多样化，每个示例50字以内）
    "creative_examples": [
      {{
        "style": "创意风格",
        "description": "创意描述（避免重复IP组合）",
        "key_elements": ["元素1", "元素2"]
      }},
      {{
        "style": "另一种风格",
        "description": "另一种创意描述",
        "key_elements": ["不同元素1", "不同元素2"]
      }}
    ],
    
    // 实用技巧（具体可操作）
    "practical_tips": [
      "剪辑技巧1（具体）",
      "音效技巧1（多样）",
      "节奏建议（有创意）"
    ]
  }}
}}

## ✨ 优质分析标准
1. **标签精准**：选择最贴合的标签，不堆砌
2. **创意多样**：提供2种不同风格的创意
3. **建议实用**：给出具体可操作的剪辑建议
4. **避免重复**：不使用最近分析中常用的IP组合

直接输出JSON，不要额外解释。
"""

# ==================== 后处理函数 ====================
def post_process_annotation(annotation_data: Dict) -> Dict:
    """
    后处理函数：增强标注数据的多样性和实用性
    """
    mashup = annotation_data.get("mashup_analysis", {})
    
    # 1. 确保语义摘要简洁（便于向量化）
    if "semantic_summary" in mashup:
        semantic = mashup["semantic_summary"]
        # 确保brief不超过30字
        if "brief" in semantic and len(semantic["brief"]) > 30:
            semantic["brief"] = semantic["brief"][:30] + "..."
        # 确保keywords不超过5个
        if "keywords" in semantic and len(semantic["keywords"]) > 5:
            semantic["keywords"] = semantic["keywords"][:5]
    
    # 2. 确保创意示例简洁
    if "creative_examples" in mashup:
        # 每个示例限制长度
        for example in mashup["creative_examples"]:
            if "description" in example and len(example["description"]) > 60:
                example["description"] = example["description"][:60] + "..."
            # 确保key_elements不超过3个
            if "key_elements" in example and len(example["key_elements"]) > 3:
                example["key_elements"] = example["key_elements"][:3]
    
    # 3. 确保实用技巧具体
    if "practical_tips" in mashup:
        # 限制技巧数量
        if len(mashup["practical_tips"]) > 3:
            mashup["practical_tips"] = mashup["practical_tips"][:3]
    
    # 4. 生成向量化友好字段
    annotation_data["vector_friendly"] = {
        "primary_tag": mashup.get("quick_tags", {}).get("primary", ""),
        "style_tag": mashup.get("quick_tags", {}).get("style", ""),
        "connection_tag": mashup.get("quick_tags", {}).get("connection", ""),
        "keywords": mashup.get("semantic_summary", {}).get("keywords", []),
        "humor_style": mashup.get("semantic_summary", {}).get("humor_style", ""),
        "use_case": mashup.get("semantic_summary", {}).get("use_case", "")
    }
    
    # 5. 生成用于搜索的标签字符串
    quick_tags = mashup.get("quick_tags", {})
    semantic = mashup.get("semantic_summary", {})
    
    annotation_data["search_tags"] = [
        quick_tags.get("primary", ""),
        quick_tags.get("style", ""),
        quick_tags.get("connection", ""),
        quick_tags.get("rhythm", "")
    ] + semantic.get("keywords", [])
    
    # 过滤空值
    annotation_data["search_tags"] = [tag for tag in annotation_data["search_tags"] if tag]
    
    return annotation_data

# ==================== 字幕解析 ====================
def parse_srt(file_path: str) -> List[Dict]:
    """解析SRT字幕文件"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"字幕文件不存在: {file_path}")
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    blocks = re.split(r"\n\s*\n", content.strip())
    lines = []
    for block in blocks:
        parts = block.strip().split("\n")
        if len(parts) < 3: continue
        try:
            time_range = parts[1]
            text = " ".join(parts[2:]).replace("\n", " ").strip()
            if not text or "-->" not in time_range: continue
            start_str, end_str = time_range.split(" --> ")
            lines.append({
                "text": text,
                "start": _time_to_seconds(start_str),
                "end": _time_to_seconds(end_str)
            })
        except: continue
    return lines

def _time_to_seconds(time_str: str) -> float:
    h, m, s_ms = time_str.replace(",", ".").split(":")
    return float(h) * 3600 + float(m) * 60 + float(s_ms)

# ==================== JSON解析 ====================
def parse_llm_response(response_text: str) -> Dict:
    """解析LLM响应"""
    # 强力剥离Markdown代码块
    clean_text = re.sub(r'```(?:json)?|```', '', response_text).strip()
    
    # 尝试寻找JSON边界
    start_idx = clean_text.find('{')
    end_idx = clean_text.rfind('}')
    if start_idx != -1 and end_idx != -1:
        clean_text = clean_text[start_idx:end_idx+1]
    
    try:
        parsed = json.loads(clean_text)
        
        # 验证必需字段
        if "mashup_analysis" not in parsed:
            raise ValueError("Missing mashup_analysis")
        
        # 应用后处理
        parsed = post_process_annotation(parsed)
        
        return parsed
        
    except Exception as e:
        print(f"⚠️ JSON解析失败: {e}")
        # 返回默认结构
        return create_default_annotation()

def create_default_annotation() -> Dict:
    """创建默认标注"""
    return {
        "mashup_analysis": {
            "quick_tags": {
                "primary": "其他",
                "style": "其他",
                "connection": "接常规",
                "rhythm": "常规剪辑"
            },
            "semantic_summary": {
                "brief": "无明显特征",
                "keywords": ["常规"],
                "humor_style": "无",
                "use_case": "通用场景"
            },
            "creative_params": {
                "crossover_types": ["通用"],
                "audio_suggestions": ["常规音效"],
                "visual_suggestions": ["常规画面"]
            },
            "creative_examples": [
                {
                    "style": "通用",
                    "description": "常规混剪应用",
                    "key_elements": ["通用元素"]
                }
            ],
            "practical_tips": ["按常规剪辑即可"]
        },
        "vector_friendly": {
            "primary_tag": "其他",
            "style_tag": "其他",
            "connection_tag": "接常规",
            "keywords": ["常规"],
            "humor_style": "无",
            "use_case": "通用场景"
        },
        "search_tags": ["其他", "常规"]
    }

# ==================== 语义标注 ====================
def annotate_line(current_line: str, context_lines: List[str], max_retries=2) -> Dict:
    """标注单行台词"""
    prompt = build_optimized_prompt(current_line, context_lines)
    
    # 修改API路径
    CHAT_API = LLM_API.replace("/completions", "/chat/completions")
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                CHAT_API,
                json={
                    "model": "qwen3-chat",
                    "messages": [
                        {"role": "system", "content": "你是混剪创作专家，分析要精准、有创意、多样化。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,  # 提高创造性
                    "response_format": {"type": "json_object"},
                    "max_tokens": 2000
                },
                timeout=30
            )
            response.raise_for_status()
            res_json = response.json()
            
            # 适配不同API返回结构
            if "choices" in res_json and "message" in res_json["choices"][0]:
                content = res_json["choices"][0]["message"]["content"].strip()
            elif "choices" in res_json and "text" in res_json["choices"][0]:
                content = res_json["choices"][0]["text"].strip()
            else:
                raise ValueError(f"无法识别的API返回结构: {res_json}")
            
            # 解析响应
            result = parse_llm_response(content)
            result["config_version"] = CONFIG_VERSION
            result["analysis_time"] = time.time()
            
            return result
            
        except Exception as e:
            print(f"❌ 第 {attempt+1} 次尝试失败: {e}")
            if attempt == max_retries - 1:
                result = create_default_annotation()
                result["config_version"] = CONFIG_VERSION
                result["analysis_time"] = time.time()
                return result
            time.sleep(1)

# ==================== 单行处理函数 ====================
def process_single_line(line_data, idx, total, window_size, all_lines):
    """处理单行字幕"""
    start_idx = max(0, idx - window_size)
    end_idx = min(total, idx + window_size + 1)
    context_texts = [all_lines[j]["text"] for j in range(start_idx, end_idx)]
    
    result = annotate_line(line_data["text"], context_texts)
    
    return {
        "id": f"line_{idx}",
        "text": line_data["text"],
        "start": line_data["start"],
        "end": line_data["end"],
        
        # 混剪分析结果
        **result,
        
        # 上下文信息
        "context": {
            "previous": context_texts[0] if len(context_texts) > 1 else "",
            "next": context_texts[-1] if len(context_texts) > 1 else ""
        }
    }

# ==================== 主处理流程 ====================
def process_srt_file(input_path: str, output_dir: str, window_size: int = 2, max_workers: int = 4):
    """主处理函数"""
    print("=" * 60)
    print("🎬 影视混剪语义标注工具 - 优化版 v4.0")
    print("🎯 特性：多样性优化 + 向量化友好")
    print("=" * 60)
    
    print(f"🔍 启动分析: {input_path}")
    print(f"⚙️ 配置版本: {CONFIG_VERSION}")
    
    # 解析字幕
    lines = parse_srt(input_path)
    if not lines:
        print("❌ 未解析到有效字幕内容")
        return
    
    total = len(lines)
    print(f"📊 找到 {total} 行字幕")
    
    annotated_lines = [None] * total
    start_time = time.time()
    
    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_single_line, lines[i], i, total, window_size, lines): i
            for i in range(total)
        }
        
        completed = 0
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                annotated_lines[idx] = result
                completed += 1
                
                # 进度显示
                progress_interval = max(1, total // 10)
                if completed % max(1, progress_interval) == 0:
                    elapsed = time.time() - start_time
                    speed = completed / elapsed if elapsed > 0 else 0
                    remaining = (total - completed) / speed if speed > 0 else 0
                    
                    print(f"🔄 进度: {completed}/{total} ({completed/total:.1%}) | "
                          f"速度: {speed:.1f}行/秒 | 剩余: {remaining:.0f}秒")
                
                # 显示前几个示例
                if completed == 1:
                    print(f"\n📝 示例标注结果:")
                    print(f"   台词: {result['text'][:50]}...")
                    print(f"   核心标签: {result['mashup_analysis']['quick_tags']['primary']}")
                    print(f"   连接方式: {result['mashup_analysis']['quick_tags']['connection']}")
                    print(f"   语义摘要: {result['mashup_analysis']['semantic_summary']['brief']}")
                    print()
                    
            except Exception as e:
                print(f"❌ 行 {idx} 处理失败: {e}")
                annotated_lines[idx] = create_default_line_result(idx, lines[idx] if idx < len(lines) else None)
    
    # 移除可能的None值
    annotated_lines = [line for line in annotated_lines if line is not None]
    
    # 保存完整结果
    output_path = Path(output_dir) / f"{Path(input_path).stem}_optimized.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(annotated_lines, f, ensure_ascii=False, indent=2)
    
    # 保存简化版（便于查看）
    simple_data = create_simple_version(annotated_lines)
    simple_path = Path(output_dir) / f"{Path(input_path).stem}_simple.json"
    with open(simple_path, "w", encoding="utf-8") as f:
        json.dump(simple_data, f, ensure_ascii=False, indent=2)
    
    # 生成统计信息
    stats = generate_statistics(annotated_lines)
    stats_path = Path(output_dir) / f"{Path(input_path).stem}_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # 显示结果
    print(f"\n✨ 处理完成！")
    print(f"⏱️ 总耗时: {time.time() - start_time:.1f}秒")
    print(f"📈 处理了 {len(annotated_lines)} 行字幕")
    print(f"💾 完整结果: {output_path}")
    print(f"📋 简化版本: {simple_path}")
    print(f"📊 统计信息: {stats_path}")
    
    # 显示标签分布
    print(f"\n🎭 标签分布统计:")
    for tag_type, counts in stats.get("tag_distribution", {}).items():
        print(f"  {tag_type}:")
        for tag, count in list(counts.items())[:5]:  # 只显示前5个
            percentage = count / len(annotated_lines) * 100
            print(f"    {tag}: {count} 行 ({percentage:.1f}%)")

def create_default_line_result(idx: int, line_data: Dict) -> Dict:
    """创建默认行结果"""
    if line_data:
        text = line_data["text"]
        start = line_data["start"]
        end = line_data["end"]
    else:
        text = ""
        start = 0
        end = 0
    
    default_annotation = create_default_annotation()
    
    return {
        "id": f"line_{idx}",
        "text": text,
        "start": start,
        "end": end,
        **default_annotation,
        "config_version": CONFIG_VERSION,
        "analysis_time": time.time(),
        "context": {"previous": "", "next": ""}
    }

def create_simple_version(annotated_lines: List[Dict]) -> List[Dict]:
    """创建简化版本"""
    simple_lines = []
    for line in annotated_lines:
        simple_lines.append({
            "id": line["id"],
            "text": line["text"][:60] + ("..." if len(line["text"]) > 60 else ""),
            "primary_tag": line["mashup_analysis"]["quick_tags"]["primary"],
            "style_tag": line["mashup_analysis"]["quick_tags"]["style"],
            "connection_tag": line["mashup_analysis"]["quick_tags"]["connection"],
            "brief": line["mashup_analysis"]["semantic_summary"]["brief"],
            "keywords": line["mashup_analysis"]["semantic_summary"]["keywords"],
            "humor_style": line["mashup_analysis"]["semantic_summary"]["humor_style"]
        })
    return simple_lines

def generate_statistics(annotated_lines: List[Dict]) -> Dict:
    """生成统计信息"""
    tag_distribution = {
        "primary": {},
        "style": {},
        "connection": {},
        "rhythm": {}
    }
    
    crossover_counts = {}
    humor_style_counts = {}
    
    for line in annotated_lines:
        mashup = line["mashup_analysis"]
        
        # 统计标签分布
        quick_tags = mashup["quick_tags"]
        for tag_type in tag_distribution.keys():
            tag = quick_tags.get(tag_type, "")
            tag_distribution[tag_type][tag] = tag_distribution[tag_type].get(tag, 0) + 1
        
        # 统计跨界类型
        crossover_types = mashup["creative_params"].get("crossover_types", [])
        for ct in crossover_types:
            crossover_counts[ct] = crossover_counts.get(ct, 0) + 1
        
        # 统计幽默风格
        humor_style = mashup["semantic_summary"].get("humor_style", "")
        if humor_style:
            humor_style_counts[humor_style] = humor_style_counts.get(humor_style, 0) + 1
    
    return {
        "total_lines": len(annotated_lines),
        "config_version": CONFIG_VERSION,
        "tag_distribution": tag_distribution,
        "crossover_distribution": dict(sorted(crossover_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        "humor_style_distribution": dict(sorted(humor_style_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        "processing_timestamp": time.time()
    }

# ==================== CLI ====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="影视台词语义标注工具-优化版 v4.0")
    parser.add_argument("input", help="SRT文件路径")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--window", type=int, default=2, help="上下文窗口大小（前后句数）")
    parser.add_argument("--workers", type=int, default=4, help="并发处理线程数")
    
    args = parser.parse_args()
    
    try:
        process_srt_file(args.input, args.output_dir, args.window, args.workers)
    except KeyboardInterrupt:
        print("\n🛑 用户中断处理")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 处理过程中发生错误: {e}")
        sys.exit(1)