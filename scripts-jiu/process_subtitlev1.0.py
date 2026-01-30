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

# 完整的默认配置（包含所有必需字段）
DEFAULT_CONFIG = {
    "version": "v1.0",
    "emotions": ["喜悦", "愤怒", "悲伤", "恐惧", "惊讶", "讽刺", "幽默", "中性"],
    "themes": [
        "身份错位", "语言荒诞", "生存反转", "文化玩梗", 
        "情感反转", "关系试探", "权力博弈", "其他"
    ],
    "priority_emotions": ["讽刺", "幽默"]
}

def load_semantic_config() -> dict:
    """安全加载配置，确保所有必需字段存在"""
    config = DEFAULT_CONFIG.copy()  # 以默认配置为基础
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            
            # 仅更新存在的字段，保留默认配置中缺失字段的默认值
            for key in ["version", "emotions", "themes", "priority_emotions"]:
                if key in user_config and user_config[key]:
                    config[key] = user_config[key]
            
            print(f"✅ 已加载配置文件: {CONFIG_PATH}")
            print(f"   情绪列表: {', '.join(config['emotions'][:3])}...")
            print(f"   主题列表: {', '.join(config['themes'][:3])}...")
        except Exception as e:
            print(f"⚠️ 配置文件解析失败 ({e})，使用默认配置")
    else:
        print(f"⚠️ 未找到配置文件 {CONFIG_PATH}，使用默认配置")
    
    # 验证必需字段
    required_fields = ["version", "emotions", "themes", "priority_emotions"]
    for field in required_fields:
        if field not in config or not config[field]:
            raise ValueError(f"配置缺失必需字段: {field}")
    
    return config

# 安全加载配置（带错误处理）
try:
    SEMANTIC_CONFIG = load_semantic_config()
    EMOTIONS = SEMANTIC_CONFIG["emotions"]
    THEMES = SEMANTIC_CONFIG["themes"]
    PRIORITY_EMOTIONS = SEMANTIC_CONFIG["priority_emotions"]
    CONFIG_VERSION = SEMANTIC_CONFIG["version"]
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    print("请检查配置文件格式或使用默认配置")
    sys.exit(1)

# ==================== 构建提示词 ====================
def build_prompt(current_line: str, context_lines: List[str]) -> str:
    emotions_str = json.dumps(EMOTIONS, ensure_ascii=False)
    themes_str = json.dumps(THEMES, ensure_ascii=False)
    priority_str = "、".join(PRIORITY_EMOTIONS)
    
    return (
        "你是一位影视混剪语义分析专家，专精小品/相声/脱口秀的网络热梗。"
        "请严格按以下要求输出纯JSON，禁止任何额外文字、解释、Markdown、注释或剧情描述。"
        "输出必须是严格的JSON格式，不要包含任何其他内容（包括代码块标记）。"
        "确保JSON包含以下三个必需字段：line_annotation, context_annotation, config_version。"
        
        "【输出格式要求】"
        "{"
        '  "line_annotation": {'
        '    "emotion": "情感",'
        '    "theme": "主题",'
        '    "subtext": "实则开头的50字内分析"'
        '  },'
        '  "context_annotation": {'
        '    "emotion": "情感",'
        '    "theme": "主题",'
        '    "subtext": "50字内直接描述"'
        '  },'
        f'  "config_version": "{CONFIG_VERSION}"'
        "}"
        
        "【字段规则】"
        "▶ line_annotation（当前台词）："
        f"- emotion: 从列表中选1项：{emotions_str}（优先考虑：{priority_str}）"
        f"- theme: 从列表中选1项或组合成4-8字动词短语：{themes_str}，必须体现动作性"
        "- subtext: 50字内，理解当前文字，直击真实意图，禁止'实则''因为''由于''看出来了'等词，禁止括号、省略号、占位说明"
        
        "▶ context_annotation（对话片段）："
        f"- emotion: 从列表中选1项：{emotions_str}"
        f"- theme: 从列表中选1项或组合成4-8字动词短语：{themes_str}"
        "- subtext: 50字内，直接描述双方互动真实目的，禁止'实则''看出来了'、'因为'、括号、省略号、占位文字"
        
        "【强制规则】"
        "1. 身份错位台词 → theme='身份错位'"
        "2. 语言重复台词 → theme='语言荒诞'"
        "3. 无反转台词 → emotion='中性', subtext='无明显反转'"
        "4. 所有subtext字段必须是完整句子，不得包含'...'、'（50字内）'等占位符"
        "5. 主题必须体现动作性（如'制造误会'✅，而非'误会'❌）"
        
        "【待分析内容】"
        f"当前台词：'{current_line}'"
        f"上下文片段：{json.dumps(context_lines, ensure_ascii=False)}"
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
        if len(parts) < 3:
            continue
        try:
            time_range = parts[1]
            text = " ".join(parts[2:]).replace("\n", " ").strip()
            if not text or "-->" not in time_range:
                continue
            start_str, end_str = time_range.split(" --> ")
            start = _time_to_seconds(start_str)
            end = _time_to_seconds(end_str)
            lines.append({
                "text": text,
                "start": start,
                "end": end
            })
        except Exception as e:
            continue  # 跳过解析失败的块
    return lines

def _time_to_seconds(time_str: str) -> float:
    h, m, s_ms = time_str.replace(",", ".").split(":")
    return float(h) * 3600 + float(m) * 60 + float(s_ms)

# ==================== JSON解析与验证 ====================
def parse_llm_response(response_text: str) -> dict:
    """严格验证并修复LLM返回的JSON"""
    # 移除Markdown标记
    response_text = re.sub(r'```(?:json)?|```', '', response_text).strip()
    
    # 确保JSON结构完整
    if not response_text.startswith('{'):
        response_text = '{' + response_text
    if not response_text.endswith('}'):
        response_text = response_text + '}'
    
    try:
        parsed = json.loads(response_text)
        
        # 验证必需字段
        required = ["line_annotation", "context_annotation", "config_version"]
        for field in required:
            if field not in parsed:
                raise ValueError(f"缺少必需字段: {field}")
        
        # 验证嵌套结构
        for key in ["line_annotation", "context_annotation"]:
            if not isinstance(parsed[key], dict):
                raise ValueError(f"{key} 必须是对象")
            for subkey in ["emotion", "theme", "subtext"]:
                if subkey not in parsed[key]:
                    raise ValueError(f"缺少子字段: {key}.{subkey}")
        
        return parsed
    except Exception as e:
        # 安全回退方案
        return {
            "line_annotation": {
                "emotion": "中性",
                "theme": "其他",
                "subtext": "无明显反转"
            },
            "context_annotation": {
                "emotion": "中性",
                "theme": "其他",
                "subtext": "无明显互动意图"
            },
            "config_version": CONFIG_VERSION
        }

# ==================== 语义标注 ====================
def annotate_with_context(current_line: str, context_lines: List[str], max_retries=2) -> Dict:
    prompt = build_prompt(current_line, context_lines)
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                LLM_API,
                json={
                    "model": "qwen3-chat",
                    "prompt": prompt,
                    "max_tokens": 250,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                },
                timeout=25,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["text"].strip()
            
            parsed = parse_llm_response(content)
            
            # 验证emotion和theme在允许列表中（宽松验证）
            if parsed["line_annotation"]["emotion"] not in EMOTIONS:
                parsed["line_annotation"]["emotion"] = "中性"
            if parsed["line_annotation"]["theme"] not in THEMES:
                parsed["line_annotation"]["theme"] = "其他"
            
            return parsed
        except Exception as e:
            if attempt == max_retries - 1:
                return parse_llm_response("")  # 触发回退方案
            time.sleep(0.5)  # 短暂等待后重试

# ==================== 单行处理函数 ====================
def process_single_line(line_data, idx, total, window_size, all_lines):
    line = line_data
    start_idx = max(0, idx - window_size)
    end_idx = min(total, idx + window_size + 1)
    context_texts = [all_lines[j]["text"] for j in range(start_idx, end_idx)]
    
    result = annotate_with_context(line["text"], context_texts)
    
    return {
        "id": f"line_{idx}",
        "text": line["text"],
        "start": line["start"],
        "end": line["end"],
        "emotion": result["line_annotation"]["emotion"],
        "theme": result["line_annotation"]["theme"],
        "subtext": result["line_annotation"]["subtext"],
        "dialogue_context": {
            "emotion": result["context_annotation"]["emotion"],
            "theme": result["context_annotation"]["theme"],
            "subtext": result["context_annotation"]["subtext"]
        },
        "config_version": result.get("config_version", CONFIG_VERSION)
    }

# ==================== 主处理流程 ====================
def process_srt(input_path: str, output_dir: str, window_size: int = 1, max_workers: int = 4):
    print(f"🔍 解析字幕文件: {input_path}")
    lines = parse_srt(input_path)
    if not lines:
        print("❌ 未解析到有效字幕行，请检查字幕文件格式")
        return
    
    total = len(lines)
    print(f"✅ 成功解析 {total} 行字幕")
    print(f"🚀 开始批量处理 (线程数: {max_workers}, 窗口大小: {window_size})...")
    
    annotated_lines = [None] * total  # 预分配列表保持顺序
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
                
                # 每10%或最后10行显示进度
                if completed % max(1, total // 10) == 0 or completed >= total - 5:
                    elapsed = time.time() - start_time
                    progress = completed / total
                    eta = (elapsed / progress - elapsed) if progress > 0 else 0
                    speed = completed / elapsed if elapsed > 0 else 0
                    print(f"🔄 [{completed}/{total}] {progress:.0%} | 速度: {speed:.1f}行/秒 | ETA: {eta:.0f}s | '{result['text'][:25]}...'")
            except Exception as e:
                print(f"❌ 处理第 {idx} 行时出错: {e}")
                # 安全回退
                annotated_lines[idx] = {
                    "id": f"line_{idx}",
                    "text": lines[idx]["text"],
                    "start": lines[idx]["start"],
                    "end": lines[idx]["end"],
                    "emotion": "中性",
                    "theme": "其他",
                    "subtext": "处理失败",
                    "dialogue_context": {
                        "emotion": "中性",
                        "theme": "其他",
                        "subtext": "处理失败"
                    },
                    "config_version": CONFIG_VERSION
                }
    
    # 过滤None值（理论上不应有）
    annotated_lines = [line for line in annotated_lines if line is not None]
    
    # 保存结果
    base_name = Path(input_path).stem
    output_path = Path(output_dir) / f"{base_name}_annotated.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(annotated_lines, f, ensure_ascii=False, indent=2)
    
    total_time = time.time() - start_time
    print("\n" + "="*50)
    print(f"✅ 处理完成！")
    print(f"📊 总行数: {total} | 耗时: {total_time:.1f}秒 | 平均速度: {total/total_time:.1f}行/秒")
    print(f"📁 输出路径: {output_path}")
    print(f"📌 配置版本: {CONFIG_VERSION}")
    print("="*50)

# ==================== CLI 入口 ====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🚀 影视字幕多维语义标注工具（多线程加速版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python process_subtitle.py "D:/AI/CineGraph-AI/data/media/subtitles/test.srt" "D:/AI/CineGraph-AI/data/analysis" --workers 6
        """
    )
    parser.add_argument("input", help="输入 .srt 字幕文件路径")
    parser.add_argument("output_dir", help="输出 JSON 目录")
    parser.add_argument("--window", type=int, default=1, help="上下文窗口大小（默认: 1）")
    parser.add_argument("--workers", type=int, default=4, help="并行处理线程数（建议: 4-8）")
    
    args = parser.parse_args()
    
    # 验证输入文件
    if not os.path.exists(args.input):
        print(f"❌ 输入文件不存在: {args.input}")
        sys.exit(1)
    
    # 验证API连接
    try:
        requests.get(LLM_API.replace("/v1/completions", "/health"), timeout=3)
        print(f"✅ LLM API 服务正常: {LLM_API}")
    except:
        print(f"⚠️  LLM API 服务可能未启动: {LLM_API}")
        print("   请确保 Qwen3-Chat 服务已通过 Docker 启动")
        # 不中断，继续处理（会使用回退方案）
    
    process_srt(args.input, args.output_dir, args.window, args.workers)