# scripts-jiu/process_subtitle.py
import os
import re
import json
import argparse
import time
import sys
from typing import List, Dict
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== 配置 ====================
LLM_API = "http://localhost:8001/v1/completions"
CONFIG_PATH = r"D:\AI\CineGraph-AI\config\theme_config.json"

# 默认配置
DEFAULT_CONFIG = {
    "version": "v1.1-mashup-optimized",
    "emotions": ["喜悦", "愤怒", "悲伤", "恐惧", "惊讶", "讽刺", "幽默", "中性", "尴尬", "嚣张"],
    "themes": [
        "身份错位", "语言荒诞", "逻辑强转", "万能衔接", 
        "发起提问", "拒绝邀约", "道德绑架", "凡尔赛", "打脸", "其他"
    ],
    "priority_emotions": ["讽刺", "幽默", "嚣张"] 
}



def load_semantic_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            for key in ["version", "emotions", "themes", "priority_emotions"]:
                if key in user_config and user_config[key]:
                    config[key] = user_config[key]
            print(f"✅ 配置加载成功: 版本 {config['version']}")
        except Exception as e:
            print(f"⚠️ 配置文件解析失败，使用默认配置: {e}")
    return config

SEMANTIC_CONFIG = load_semantic_config()
EMOTIONS = SEMANTIC_CONFIG["emotions"]
THEMES = SEMANTIC_CONFIG["themes"]
PRIORITY_EMOTIONS = SEMANTIC_CONFIG["priority_emotions"]
CONFIG_VERSION = SEMANTIC_CONFIG["version"]

# ==================== 优化后的核心提示词 ====================
def build_prompt(current_line: str, context_lines: List[str]) -> str:
    """
    影视混剪语义标注提示词 - 严格清洁版
    解决模型复读占位符、公式符号的问题。
    """
    # 动作意图库
    ACTION_INTENT_TAGS = [
        "一本正经胡说八道", "降智打击", "阴阳怪气", "强行缝合", "借机发难", 
        "装疯卖傻", "气场压制", "跨界借梗", "道德绑架", "强行狡辩",
        "确认身份", "推卸责任", "委婉拒绝", "发出威胁", "发起提问"
    ]
    
    # 功能标签库
    MASHUP_FUNCTIONAL_TAGS = [
        "反直觉转折", "逻辑鬼才", "次元壁碰撞", "万能衔接", "情绪爆发", 
        "逻辑断层", "指代不明", "打破第四面墙", "无效沟通", "氛围烘托",
        "动作衔接", "金句结束", "万能转场", "万能开场", "身份确认"
    ]

    action_tags_str = ", ".join(ACTION_INTENT_TAGS)
    function_tags_str = ", ".join(MASHUP_FUNCTIONAL_TAGS)
    
    return (
        "### Role ###\n"
        "你是一位深谙影视解构文化的剪辑专家。你需要将台词转化为高价值的语义摘要。\n\n"

        "### 写作禁令 (必须严格遵守) ###\n"
        "1. **严禁输出占位符**：禁止在 subtext 中出现 '{ }'、'['、']' 以外的引导符号，禁止出现 '+' 号。\n"
        "2. **严禁复读引导词**：禁止在 subtext 中出现 '可选'、'标签库'、'台词里的事' 等提示词里的词汇。\n"
        "3. **自然语言化**：subtext 必须是一个流畅的句子，而不是标签的简单堆砌。\n\n"

        "### subtext 编写标准 ###\n"
        "请按照以下逻辑撰写：\n"
        "1. 句首必须是一个 [动作意图标签]。\n"
        "2. 紧接着用一段具体的文字描述台词里的具体人物、动作或物品。不要抽象，要具体。\n"
        "3. 句尾必须是一个 [混剪功能标签]。\n"
        "示例格式：[气场压制] 角色对着那箱金子露出贪婪的目光并以此威胁对方，[万能转场]\n\n"

        "### 标签库 (请从中挑选) ###\n"
        f"- 动作意图: {action_tags_str}\n"
        f"- 混剪功能: {function_tags_str}\n\n"

        "### JSON Output Format ###\n"
        "{\n"
        '  "line_annotation": {"emotion": "...", "theme": "...", "subtext": "..."},\n'
        '  "context_annotation": {"emotion": "...", "theme": "...", "subtext": "..."},\n'
        f'  "config_version": "{CONFIG_VERSION}"\n'
        "}\n\n"
        
        "### 待分析数据 ###\n"
        f"台词内容: '{current_line}'\n"
        f"上下文语境: {json.dumps(context_lines, ensure_ascii=False)}\n\n"
        
        "### 任务执行 ###\n"
        "现在请直接输出该台词的 JSON 标注结果。subtext 中必须用具体台词内容替换掉所有的描述性占位符。"
    )
# ==================== 字幕解析 ====================
def parse_srt(file_path: str) -> List[Dict]:
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

# ==================== JSON解析与验证 ====================
def parse_llm_response(response_text: str) -> dict:
    # 强力剥离 Markdown 代码块
    clean_text = re.sub(r'```(?:json)?|```', '', response_text).strip()
    
    # 尝试寻找 JSON 边界（防止开头有废话）
    start_idx = clean_text.find('{')
    end_idx = clean_text.rfind('}')
    if start_idx != -1 and end_idx != -1:
        clean_text = clean_text[start_idx:end_idx+1]

    try:
        parsed = json.loads(clean_text)
        # 字段补全检测
        if "line_annotation" not in parsed: raise ValueError("Missing line_annotation")
        return parsed
    except Exception:
        # 极简回退逻辑
        return {
            "line_annotation": {"emotion": "中性", "theme": "其他", "subtext": "语义解析回退：无明显特征"},
            "context_annotation": {"emotion": "中性", "theme": "其他", "subtext": "无明确互动意图"},
            "config_version": CONFIG_VERSION
        }

# ==================== 语义标注 ====================
def annotate_with_context(current_line: str, context_lines: List[str], max_retries=2) -> Dict:
    prompt = build_prompt(current_line, context_lines)
    
    # 修改 API 路径为通用的 Chat 路径
    CHAT_API = LLM_API.replace("/completions", "/chat/completions")
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                CHAT_API,
                json={
                    "model": "qwen3-chat", 
                    "messages": [
                        {"role": "system", "content": "你是一个严格只输出JSON的语义标注专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )
            response.raise_for_status()
            res_json = response.json()
            
            # 适配 Chat API 的返回结构
            if "choices" in res_json and "message" in res_json["choices"][0]:
                content = res_json["choices"][0]["message"]["content"].strip()
            elif "choices" in res_json and "text" in res_json["choices"][0]:
                content = res_json["choices"][0]["text"].strip()
            else:
                print(f"⚠️ 无法识别的 API 返回结构: {res_json}")
                raise ValueError("Unknown API structure")

            # 调试打印：如果你在终端看到模型返回的文字，就知道哪里错了
            # print(f"DEBUG LLM 返回内容: {content}") 
            
            return parse_llm_response(content)
            
        except Exception as e:
            print(f"❌ 第 {attempt+1} 次尝试请求失败: {e}")
            if attempt == max_retries - 1:
                return parse_llm_response("") 
            time.sleep(1)
# ==================== 单行处理函数 ====================
def process_single_line(line_data, idx, total, window_size, all_lines):
    start_idx = max(0, idx - window_size)
    end_idx = min(total, idx + window_size + 1)
    context_texts = [all_lines[j]["text"] for j in range(start_idx, end_idx)]
    
    result = annotate_with_context(line_data["text"], context_texts)
    
    return {
        "id": f"line_{idx}",
        "text": line_data["text"],
        "start": line_data["start"],
        "end": line_data["end"],
        "emotion": result["line_annotation"]["emotion"],
        "theme": result["line_annotation"]["theme"],
        "subtext": result["line_annotation"]["subtext"],
        "mashup_tags": {
            "context_emotion": result["context_annotation"]["emotion"],
            "context_theme": result["context_annotation"]["theme"],
            "context_subtext": result["context_annotation"]["subtext"]
        },
        "config_version": result.get("config_version", CONFIG_VERSION)
    }

# ==================== 主处理流程 ====================
def process_srt_file(input_path: str, output_dir: str, window_size: int = 2, max_workers: int = 4):
    print(f"🔍 启动语义分析: {input_path}")
    lines = parse_srt(input_path)
    if not lines: return
    
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
                if completed % max(1, total // 10) == 0:
                    speed = completed / (time.time() - start_time)
                    print(f"🔄 进度: {completed}/{total} ({completed/total:.1%}) | 速度: {speed:.1f}行/秒")
            except Exception as e:
                print(f"❌ 行 {idx} 处理失败: {e}")

    # 保存文件
    output_path = Path(output_dir) / f"{Path(input_path).stem}_annotated.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(annotated_lines, f, ensure_ascii=False, indent=2)
    
    print(f"\n✨ 处理完成！结果保存至: {output_path}")
    print(f"⏱️ 总耗时: {time.time() - start_time:.1f}秒")

# ==================== CLI ====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="影视台词语义标注工具-混剪增强版")
    parser.add_argument("input", help="SRT文件路径")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--window", type=int, default=2, help="上下文窗口")
    parser.add_argument("--workers", type=int, default=4, help="线程数")
    
    args = parser.parse_args()
    process_srt_file(args.input, args.output_dir, args.window, args.workers)