# scripts-jiu/process_subtitle_enhanced.py
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
CONFIG_PATH = r"D:\AI\CineGraph-AI\config\mashup_config.json"

# 混剪专用标签体系
DEFAULT_MASHUP_CONFIG = {
    "version": "v3.0-mashup-pro",
    
    # 混剪核心功能标签（这段台词在混剪中能做什么）
    "mashup_functions": [
        "抛梗开场", "身份反转", "场景嫁接", "金句引用", 
        "跨服聊天", "强行解释", "反差萌", "名场面再现",
        "一本正经胡说", "降维打击", "时代错位", "次元突破",
        "神转折", "废话文学", "无效沟通", "自说自话",
        "蜜汁自信", "弱小可怜", "嚣张跋扈", "阴阳怪气"
    ],
    
    # 剪辑节奏标签（这段台词怎么剪）
    "editing_rhythms": [
        "快速切梗", "慢放打脸", "重复鬼畜", "戛然而止",
        "递进夸张", "突然打断", "画外音怼", "画面神配",
        "音效配合", "变速处理", "重复强调", "静音反差"
    ],
    
    # 搞笑效果标签（会产生什么笑点）
    "humor_effects": [
        "无厘头搞笑", "尴尬冷场", "傲娇口嫌", "震惊全家",
        "蜜汁自信", "弱小无助", "嚣张跋扈", "阴阳怪气",
        "一本正经", "降智打击", "强行合理", "逻辑鬼才"
    ],
    
    # 跨作品适配标签（能和哪些作品联动）
    "crossover_types": [
        "古现混搭", "中二科幻", "宫廷职场", "武侠校园",
        "仙侠现代", "历史搞笑", "恐怖喜剧", "战争日常",
        "动画真人", "日剧国剧", "欧美古风", "综艺影视"
    ],
    
    # 拼接建议标签（后面适合接什么）
    "connection_suggestions": [
        "接打脸", "接求饶", "接质疑", "接傲娇",
        "接装傻", "接暴怒", "接认怂", "接反转",
        "接解释", "接吐槽", "接玩梗", "接冷场"
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
            print(f"✅ 混剪配置加载成功: 版本 {config['version']}")
        except Exception as e:
            print(f"⚠️ 混剪配置文件解析失败，使用默认配置: {e}")
    return config

MASHUP_CONFIG = load_mashup_config()
CONFIG_VERSION = MASHUP_CONFIG["version"]

# ==================== 双系统提示词 ====================
def build_dual_prompt(current_line: str, context_lines: List[str]) -> Tuple[str, str]:
    """
    返回两个提示词：
    1. 传统语义分析提示词（原有系统）
    2. 混剪专用分析提示词（新增系统）
    """
    
    # 1. 传统语义分析提示词（保持与您原有系统兼容）
    traditional_prompt = build_traditional_prompt(current_line, context_lines)
    
    # 2. 混剪专用分析提示词
    mashup_prompt = build_mashup_specific_prompt(current_line, context_lines)
    
    return traditional_prompt, mashup_prompt

def build_traditional_prompt(current_line: str, context_lines: List[str]) -> str:
    """传统语义分析提示词（与您原有系统兼容）"""
    return f"""
### 传统语义分析 ###
请分析以下台词在原片中的含义：

台词: "{current_line}"
上下文: {json.dumps(context_lines, ensure_ascii=False)}

请输出JSON格式：
{{
  "traditional_analysis": {{
    "speech_act": "言语行为",
    "emotion": "情感状态",
    "intent": "说话意图",
    "summary": "语义摘要"
  }}
}}
"""

def build_mashup_specific_prompt(current_line: str, context_lines: List[str]) -> str:
    """混剪专用分析提示词"""
    
    mashup_func_str = ", ".join(MASHUP_CONFIG["mashup_functions"])
    rhythm_str = ", ".join(MASHUP_CONFIG["editing_rhythms"])
    humor_str = ", ".join(MASHUP_CONFIG["humor_effects"])
    crossover_str = ", ".join(MASHUP_CONFIG["crossover_types"])
    conn_str = ", ".join(MASHUP_CONFIG["connection_suggestions"])
    
    return f"""
### 🎬 混剪创作潜力分析 ###

## 你的角色
你是资深影视混剪UP主，专门制作跨作品、无厘头、搞笑向的混剪视频。

## 核心任务
分析以下台词在**脱离原片语境**后的混剪潜力。忘记它在原片中是什么意思，只考虑：
1. 在其他作品中能产生什么搞笑效果？
2. 适合用什么剪辑手法处理？
3. 能和什么类型的作品/台词拼接？

## 分析对象
当前台词: "{current_line}"
上下文参考: {json.dumps(context_lines, ensure_ascii=False)[:200]}...

## 🏷️ 标签库参考
混剪功能: {mashup_func_str}
剪辑节奏: {rhythm_str}
搞笑效果: {humor_str}
跨界类型: {crossover_str}
拼接建议: {conn_str}

## 📊 输出要求（严格JSON格式）
{{
  "mashup_analysis": {{
    // 核心混剪功能（最重要的标签）
    "primary_function": "从混剪功能标签中选择",
    
    // 次要效果标签（可选1-3个）
    "secondary_tags": ["标签1", "标签2"],
    
    // 剪辑建议
    "editing_suggestions": {{
      "rhythm": "剪辑节奏建议",
      "visual_cue": "建议配合的画面类型",
      "audio_cue": "建议配合的音效/BGM类型",
      "special_effect": "是否需要特殊效果"
    }},
    
    // 拼接潜力
    "connection_potential": {{
      "best_match": "最适合的拼接类型",
      "example_response": "示例：接什么台词能产生最好效果",
      "avoid_match": "应避免的拼接类型"
    }},
    
    // 跨作品适配性
    "crossover_score": {{
      "versatility": 0-10,  // 通用性：能用在多少不同场景
      "humor_value": 0-10,  // 搞笑值：能产生多大笑点
      "viral_potential": 0-10,  // 传播潜力：是否容易成为梗
      "recommended_genres": ["推荐作品类型1", "类型2"]
    }},
    
    // 具体创意示例
    "creative_examples": [
      "创意1：比如在XX场景中，配上XX画面，接XX台词",
      "创意2：另一种用法是..."
    ],
    
    // 实用建议
    "practical_tips": [
      "剪辑技巧提示1",
      "剪辑技巧提示2"
    ]
  }}
}}

## ✨ 优质分析标准
1. **脑洞要大**：提出意想不到的混搭方案
2. **要具体**：给出具体的画面、音效建议
3. **要实用**：对剪辑师有实际指导意义
4. **要准确**：标签选择要精准，不要堆砌

现在开始分析，直接输出JSON，不要额外解释。
"""

# ==================== 双系统解析 ====================
def parse_dual_response(traditional_response: str, mashup_response: str) -> Dict:
    """解析双系统的响应"""
    
    # 解析传统分析
    traditional_data = parse_traditional_response(traditional_response)
    
    # 解析混剪分析
    mashup_data = parse_mashup_response(mashup_response)
    
    # 合并结果
    return {
        **traditional_data,
        **mashup_data,
        "config_version": CONFIG_VERSION,
        "analysis_time": time.time()
    }

def parse_traditional_response(response_text: str) -> Dict:
    """解析传统分析响应"""
    try:
        clean_text = re.sub(r'```(?:json)?|```', '', response_text).strip()
        start_idx = clean_text.find('{')
        end_idx = clean_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_text = clean_text[start_idx:end_idx+1]
        
        parsed = json.loads(clean_text)
        return {"traditional_analysis": parsed.get("traditional_analysis", {})}
    except Exception as e:
        print(f"⚠️ 传统分析解析失败: {e}")
        return {
            "traditional_analysis": {
                "speech_act": "未知",
                "emotion": "中性",
                "intent": "无明确意图",
                "summary": "解析失败"
            }
        }

def parse_mashup_response(response_text: str) -> Dict:
    """解析混剪分析响应"""
    try:
        clean_text = re.sub(r'```(?:json)?|```', '', response_text).strip()
        start_idx = clean_text.find('{')
        end_idx = clean_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            clean_text = clean_text[start_idx:end_idx+1]
        
        parsed = json.loads(clean_text)
        
        # 验证和补全混剪分析字段
        mashup_analysis = parsed.get("mashup_analysis", {})
        
        # 确保关键字段存在
        default_mashup = {
            "primary_function": "其他",
            "secondary_tags": [],
            "editing_suggestions": {
                "rhythm": "常规剪辑",
                "visual_cue": "无特殊要求",
                "audio_cue": "无特殊要求",
                "special_effect": "无"
            },
            "connection_potential": {
                "best_match": "接常规回应",
                "example_response": "无示例",
                "avoid_match": "无"
            },
            "crossover_score": {
                "versatility": 5,
                "humor_value": 5,
                "viral_potential": 5,
                "recommended_genres": ["通用"]
            },
            "creative_examples": ["暂无创意示例"],
            "practical_tips": ["按常规剪辑即可"]
        }
        
        # 深度合并默认值
        def deep_merge(default, user):
            if isinstance(default, dict) and isinstance(user, dict):
                for key, value in default.items():
                    if key not in user:
                        user[key] = value
                    elif isinstance(value, dict):
                        deep_merge(value, user[key])
            return user
        
        mashup_analysis = deep_merge(default_mashup, mashup_analysis)
        
        return {"mashup_analysis": mashup_analysis}
        
    except Exception as e:
        print(f"⚠️ 混剪分析解析失败: {e}")
        return {
            "mashup_analysis": {
                "primary_function": "解析失败",
                "secondary_tags": [],
                "editing_suggestions": {
                    "rhythm": "常规剪辑",
                    "visual_cue": "无",
                    "audio_cue": "无",
                    "special_effect": "无"
                },
                "connection_potential": {
                    "best_match": "接常规",
                    "example_response": "解析失败",
                    "avoid_match": "无"
                },
                "crossover_score": {
                    "versatility": 0,
                    "humor_value": 0,
                    "viral_potential": 0,
                    "recommended_genres": []
                },
                "creative_examples": ["分析失败，请手动判断"],
                "practical_tips": ["分析失败"]
            }
        }

# ==================== 双系统标注 ====================
def dual_annotate_with_context(current_line: str, context_lines: List[str], max_retries=2) -> Dict:
    """双系统标注：传统分析 + 混剪分析"""
    
    traditional_prompt, mashup_prompt = build_dual_prompt(current_line, context_lines)
    
    # 修改 API 路径
    CHAT_API = LLM_API.replace("/completions", "/chat/completions")
    
    traditional_result = ""
    mashup_result = ""
    
    # 并行请求两个分析（实际是串行，但结构清晰）
    for attempt in range(max_retries):
        try:
            # 请求传统分析
            trad_response = requests.post(
                CHAT_API,
                json={
                    "model": "qwen3-chat",
                    "messages": [
                        {"role": "system", "content": "你是传统语义分析专家。"},
                        {"role": "user", "content": traditional_prompt}
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=15
            )
            trad_response.raise_for_status()
            trad_json = trad_response.json()
            traditional_result = trad_json["choices"][0]["message"]["content"].strip()
            
            # 请求混剪分析
            mashup_response = requests.post(
                CHAT_API,
                json={
                    "model": "qwen3-chat",
                    "messages": [
                        {"role": "system", "content": "你是混剪创作专家，脑洞要大。"},
                        {"role": "user", "content": mashup_prompt}
                    ],
                    "temperature": 0.7,  # 混剪需要更多创造性
                    "response_format": {"type": "json_object"}
                },
                timeout=20
            )
            mashup_response.raise_for_status()
            mashup_json = mashup_response.json()
            mashup_result = mashup_json["choices"][0]["message"]["content"].strip()
            
            # 解析合并结果
            return parse_dual_response(traditional_result, mashup_result)
            
        except Exception as e:
            print(f"❌ 第 {attempt+1} 次尝试请求失败: {e}")
            if attempt == max_retries - 1:
                # 返回默认结构
                return parse_dual_response("", "")
            time.sleep(1)

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

# ==================== 单行处理函数 ====================
def process_single_line(line_data, idx, total, window_size, all_lines):
    """处理单行字幕"""
    start_idx = max(0, idx - window_size)
    end_idx = min(total, idx + window_size + 1)
    context_texts = [all_lines[j]["text"] for j in range(start_idx, end_idx)]
    
    result = dual_annotate_with_context(line_data["text"], context_texts)
    
    return {
        "id": f"line_{idx}",
        "text": line_data["text"],
        "start": line_data["start"],
        "end": line_data["end"],
        
        # 传统分析结果
        "traditional": result["traditional_analysis"],
        
        # 混剪分析结果
        "mashup": result["mashup_analysis"],
        
        # 元数据
        "config_version": result.get("config_version", CONFIG_VERSION),
        "analysis_time": result.get("analysis_time", time.time())
    }

# ==================== 主处理流程 ====================
def process_srt_file(input_path: str, output_dir: str, window_size: int = 2, max_workers: int = 4):
    """主处理函数"""
    print("=" * 60)
    print("🎬 影视混剪双系统语义标注工具 v3.0")
    print("📊 同时进行：传统语义分析 + 混剪创作分析")
    print("=" * 60)
    
    print(f"🔍 启动分析: {input_path}")
    print(f"⚙️ 使用配置版本: {CONFIG_VERSION}")
    
    lines = parse_srt(input_path)
    if not lines: 
        print("❌ 未解析到有效字幕内容")
        return
    
    total = len(lines)
    annotated_lines = [None] * total
    start_time = time.time()
    
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
                if completed == 2:
                    print(f"\n📝 示例分析结果:")
                    print(f"   台词: {result['text'][:50]}...")
                    print(f"   传统分析: {result['traditional']['speech_act']} | {result['traditional']['emotion']}")
                    print(f"   混剪功能: {result['mashup']['primary_function']}")
                    print(f"   搞笑效果: {', '.join(result['mashup']['secondary_tags'])}")
                    print()
                    
            except Exception as e:
                print(f"❌ 行 {idx} 处理失败: {e}")
                # 创建默认结果
                annotated_lines[idx] = create_default_result(idx, lines[idx] if idx < len(lines) else None)
    
    # 移除可能的None值
    annotated_lines = [line for line in annotated_lines if line is not None]
    
    # 保存完整结果
    output_path = Path(output_dir) / f"{Path(input_path).stem}_dual_annotated.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(annotated_lines, f, ensure_ascii=False, indent=2)
    
    # 生成精简版（便于快速浏览）
    simple_output = create_simple_version(annotated_lines)
    simple_path = Path(output_dir) / f"{Path(input_path).stem}_simple.json"
    with open(simple_path, "w", encoding="utf-8") as f:
        json.dump(simple_output, f, ensure_ascii=False, indent=2)
    
    # 统计信息
    print(f"\n✨ 处理完成！")
    print(f"⏱️ 总耗时: {time.time() - start_time:.1f}秒")
    print(f"📈 处理了 {len(annotated_lines)} 行字幕")
    print(f"💾 完整结果: {output_path}")
    print(f"📋 精简版本: {simple_path}")
    
    # 显示统计信息
    show_statistics(annotated_lines)

def create_default_result(idx: int, line_data: Dict) -> Dict:
    """创建默认结果（处理失败时使用）"""
    if line_data:
        text = line_data["text"]
        start = line_data["start"]
        end = line_data["end"]
    else:
        text = ""
        start = 0
        end = 0
    
    return {
        "id": f"line_{idx}",
        "text": text,
        "start": start,
        "end": end,
        "traditional": {
            "speech_act": "未知",
            "emotion": "中性",
            "intent": "无明确意图",
            "summary": "处理失败"
        },
        "mashup": {
            "primary_function": "其他",
            "secondary_tags": [],
            "editing_suggestions": {
                "rhythm": "常规剪辑",
                "visual_cue": "无",
                "audio_cue": "无",
                "special_effect": "无"
            },
            "connection_potential": {
                "best_match": "接常规",
                "example_response": "处理失败",
                "avoid_match": "无"
            },
            "crossover_score": {
                "versatility": 0,
                "humor_value": 0,
                "viral_potential": 0,
                "recommended_genres": []
            },
            "creative_examples": ["处理失败"],
            "practical_tips": ["请手动判断"]
        },
        "config_version": CONFIG_VERSION,
        "analysis_time": time.time()
    }

def create_simple_version(annotated_lines: List[Dict]) -> List[Dict]:
    """创建精简版本，便于快速浏览"""
    simple_lines = []
    for line in annotated_lines:
        simple_lines.append({
            "id": line["id"],
            "text": line["text"][:100] + ("..." if len(line["text"]) > 100 else ""),
            "traditional_summary": f"{line['traditional']['speech_act']} | {line['traditional']['emotion']}",
            "mashup_function": line["mashup"]["primary_function"],
            "humor_tags": line["mashup"]["secondary_tags"][:3],
            "editing_tip": line["mashup"]["editing_suggestions"]["rhythm"],
            "best_connection": line["mashup"]["connection_potential"]["best_match"],
            "versatility_score": line["mashup"]["crossover_score"]["versatility"],
            "humor_score": line["mashup"]["crossover_score"]["humor_value"]
        })
    return simple_lines

def show_statistics(annotated_lines: List[Dict]):
    """显示统计信息"""
    mashup_func_counts = {}
    rhythm_counts = {}
    connection_counts = {}
    
    for line in annotated_lines:
        # 统计混剪功能
        func = line["mashup"]["primary_function"]
        mashup_func_counts[func] = mashup_func_counts.get(func, 0) + 1
        
        # 统计剪辑节奏
        rhythm = line["mashup"]["editing_suggestions"]["rhythm"]
        rhythm_counts[rhythm] = rhythm_counts.get(rhythm, 0) + 1
        
        # 统计拼接建议
        conn = line["mashup"]["connection_potential"]["best_match"]
        connection_counts[conn] = connection_counts.get(conn, 0) + 1
    
    print(f"\n📊 混剪功能分布 (Top 5):")
    sorted_funcs = sorted(mashup_func_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for func, count in sorted_funcs:
        percentage = count / len(annotated_lines) * 100
        print(f"   {func}: {count} 行 ({percentage:.1f}%)")
    
    print(f"\n🎬 剪辑节奏建议 (Top 3):")
    sorted_rhythms = sorted(rhythm_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    for rhythm, count in sorted_rhythms:
        percentage = count / len(annotated_lines) * 100
        print(f"   {rhythm}: {count} 行 ({percentage:.1f}%)")
    
    print(f"\n🔗 拼接建议分布 (Top 3):")
    sorted_conns = sorted(connection_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    for conn, count in sorted_conns:
        percentage = count / len(annotated_lines) * 100
        print(f"   {conn}: {count} 行 ({percentage:.1f}%)")
    
    # 计算平均得分
    avg_versatility = sum(line["mashup"]["crossover_score"]["versatility"] for line in annotated_lines) / len(annotated_lines)
    avg_humor = sum(line["mashup"]["crossover_score"]["humor_value"] for line in annotated_lines) / len(annotated_lines)
    
    print(f"\n⭐ 平均潜力评分:")
    print(f"   通用性: {avg_versatility:.1f}/10")
    print(f"   搞笑值: {avg_humor:.1f}/10")
    
    # 找出最有潜力的台词
    high_potential = []
    for line in annotated_lines:
        score = line["mashup"]["crossover_score"]["versatility"] + line["mashup"]["crossover_score"]["humor_value"]
        if score >= 15:  # 总分15分以上
            high_potential.append((line["id"], line["text"][:50], score))
    
    if high_potential:
        print(f"\n💎 高潜力混剪台词 (总分≥15):")
        for pid, text, score in high_potential[:3]:  # 只显示前3个
            print(f"   {pid}: {text}... (总分: {score})")

# ==================== CLI ====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="影视台词语义标注工具-混剪双系统版 v3.0")
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