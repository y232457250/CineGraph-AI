# backend/app/ingestion/semantic_annotator.py
"""
语义标注器 - 用于台词混剪的语义标注
支持本地模型和商用API切换
"""

import os
import re
import json
import time
import yaml
import threading
import requests
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from enum import Enum

# ==================== 配置路径 ====================
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
MASHUP_CONFIG_PATH = CONFIG_DIR / "mashup_v5_config.json"
LLM_CONFIG_PATH = CONFIG_DIR / "llm_providers.yaml"
PROMPT_CONFIG_PATH = CONFIG_DIR / "prompt_config.json"


# ==================== 英文→中文映射表 ====================
SENTENCE_TYPE_MAP = {
    "question": "问句", "answer": "答句", "command": "命令", "threat": "威胁",
    "counter_question": "反问", "mock": "嘲讽", "refuse": "拒绝", "fear": "害怕",
    "surrender": "求饶", "counter_attack": "反击", "anger": "愤怒", "exclaim": "感叹",
    "persuade": "劝说", "agree": "同意", "action": "行动", "interrupt": "打断",
    "reveal": "揭示", "obey": "服从", "comment": "评论", "shock": "震惊",
    "interjection": "感叹", "statement": "陈述"
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
    """将英文标签转换为中文，如果已经是中文则保持不变"""
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


# ==================== 数据类 ====================
@dataclass
class SourceInfo:
    """📍 来源定位信息 - 精简版
    完整媒体信息通过media_id关联media_index.json获取
    """
    media_id: str = ""      # 关联media_index的key
    start: float = 0.0      # 开始时间(秒)
    end: float = 0.0        # 结束时间(秒)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class MashupTags:
    """🎭 混剪核心标签 (用于搜索和匹配)"""
    # 句型分类 - 决定能接什么
    sentence_type: str = ""  # 问句|答句|感叹|命令|质问|威胁|拒绝|求饶|嘲讽
    
    # 情绪标签 - 用于情绪匹配
    emotion: str = ""  # 愤怒|搞笑|害怕|嘲讽|恳求|倔强|得意|无奈|狂躁
    
    # 语气标签 - 用于节奏控制
    tone: str = ""  # 强硬|软弱|挑衅|无奈|傲慢|卑微|疑惑|肯定
    
    # 核心功能
    primary_function: str = ""  # 强行解释|身份反转|场景嫁接|金句引用...
    
    # 风格效果
    style_effect: str = ""  # 反讽高级黑|自嘲解构|谐音梗王...
    
    # ⭐ 接话规则 - 混剪核心
    can_follow: List[str] = None  # 能接在什么类型后面
    can_lead_to: List[str] = None  # 后面能接什么
    
    # 关键词 (用于精准搜索)
    keywords: List[str] = None
    
    # 角色类型 (跨剧接话用)
    character_type: str = ""  # 皇帝|大臣|妖怪|英雄|受害者|施暴者|旁观者
    
    def __post_init__(self):
        if self.can_follow is None:
            self.can_follow = []
        if self.can_lead_to is None:
            self.can_lead_to = []
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EditingParams:
    """📊 剪辑参数 - 精简版"""
    rhythm: str = ""        # 快速切梗|慢放打脸|戛然而止...
    duration: float = 0.0   # 时长(秒)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LineAnnotation:
    """单句台词标注结果 - 精简版混剪规范
    
    设计原则：
    1. source只保留定位必需信息，完整媒体信息通过media_id关联
    2. 删除调试用元数据(llm_provider, config_version)
    3. 删除实用性低的字段(audio_suggest)
    4. 所有标签统一使用中文
    """
    id: str
    text: str
    
    # 📍 来源定位 (精简)
    source: SourceInfo = None
    
    # 🎭 混剪核心标签
    mashup_tags: MashupTags = None
    
    # 🔍 向量化文本 (用于embedding)
    vector_text: str = ""
    
    # 📊 剪辑参数 (精简)
    editing_params: EditingParams = None
    
    # 语义摘要
    semantic_summary: str = ""
    
    # 标注时间戳
    annotated_at: float = 0
    
    def __post_init__(self):
        if self.source is None:
            self.source = SourceInfo()
        if self.mashup_tags is None:
            self.mashup_tags = MashupTags()
        if self.editing_params is None:
            self.editing_params = EditingParams()
    
    def to_dict(self) -> Dict:
        """转换为字典，保持嵌套结构"""
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source.to_dict() if self.source else {},
            "mashup_tags": self.mashup_tags.to_dict() if self.mashup_tags else {},
            "vector_text": self.vector_text,
            "editing_params": self.editing_params.to_dict() if self.editing_params else {},
            "semantic_summary": self.semantic_summary,
            "annotated_at": self.annotated_at
        }
    
    def generate_vector_text(self):
        """生成用于向量化的文本 - 纯中文简洁格式"""
        tags = self.mashup_tags
        parts = [
            tags.sentence_type,
            tags.emotion,
            tags.tone,
            self.text,
        ]
        # 添加可引导的类型
        if tags.can_lead_to:
            parts.extend(tags.can_lead_to)
        # 添加关键词
        if tags.keywords:
            parts.extend(tags.keywords)
        
        self.vector_text = " ".join(filter(None, parts))
    
    @classmethod
    def from_dict(cls, d: Dict) -> "LineAnnotation":
        """从字典恢复 LineAnnotation 对象（用于 checkpoint 恢复）"""
        source_d = d.get("source", {})
        source = SourceInfo(
            media_id=source_d.get("media_id", ""),
            start=source_d.get("start", 0.0),
            end=source_d.get("end", 0.0)
        )
        tags_d = d.get("mashup_tags", {})
        mashup_tags = MashupTags(
            sentence_type=tags_d.get("sentence_type", ""),
            emotion=tags_d.get("emotion", ""),
            tone=tags_d.get("tone", ""),
            primary_function=tags_d.get("primary_function", ""),
            style_effect=tags_d.get("style_effect", ""),
            can_follow=tags_d.get("can_follow", []),
            can_lead_to=tags_d.get("can_lead_to", []),
            keywords=tags_d.get("keywords", []),
            character_type=tags_d.get("character_type", "")
        )
        ep_d = d.get("editing_params", {})
        editing_params = EditingParams(
            rhythm=ep_d.get("rhythm", ""),
            duration=ep_d.get("duration", 0.0)
        )
        return cls(
            id=d.get("id", ""),
            text=d.get("text", ""),
            source=source,
            mashup_tags=mashup_tags,
            vector_text=d.get("vector_text", ""),
            editing_params=editing_params,
            semantic_summary=d.get("semantic_summary", ""),
            annotated_at=d.get("annotated_at", 0)
        )


# ==================== LLM提供者管理 ====================
# 使用独立的LLM模块，支持多种模型类型
from app.llm import LLMProviderManager


# ==================== 配置加载 ====================
class MashupConfig:
    """混剪配置管理"""
    
    def __init__(self, config_path: Path = MASHUP_CONFIG_PATH):
        self.config_path = config_path
        self.config: Dict = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        if not self.config_path.exists():
            print(f"⚠️ 混剪配置文件不存在: {self.config_path}")
            self.config = {"version": "default"}
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            print(f"✅ 混剪配置加载成功: {self.config.get('version', 'unknown')}")
        except Exception as e:
            print(f"⚠️ 混剪配置加载失败: {e}")
            self.config = {"version": "default"}
    
    @property
    def version(self) -> str:
        return self.config.get("version", "unknown")
    
    @property
    def sentence_types(self) -> List[Dict]:
        return self.config.get("sentence_types", {}).get("types", [])
    
    @property
    def emotions(self) -> List[Dict]:
        return self.config.get("emotions", {}).get("types", [])
    
    @property
    def tones(self) -> List[Dict]:
        return self.config.get("tones", {}).get("types", [])
    
    @property
    def character_types(self) -> List[Dict]:
        return self.config.get("character_types", {}).get("types", [])
    
    @property
    def primary_functions(self) -> List[str]:
        return self.config.get("primary_functions", [])
    
    @property
    def style_effects(self) -> List[str]:
        return self.config.get("style_effects", [])
    
    def get_sentence_type_names(self) -> List[str]:
        return [t["name"] for t in self.sentence_types]
    
    def get_emotion_names(self) -> List[str]:
        return [e["name"] for e in self.emotions]
    
    def get_tone_names(self) -> List[str]:
        return [t["name"] for t in self.tones]
    
    def get_can_follow_for_type(self, type_id: str) -> List[str]:
        """获取某个句型能接什么类型"""
        for t in self.sentence_types:
            if t["id"] == type_id:
                return t.get("can_follow", [])
        return []


# ==================== 提示词构建 ====================
def load_prompt_config() -> Dict:
    """加载提示词配置"""
    if PROMPT_CONFIG_PATH.exists():
        try:
            with open(PROMPT_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载提示词配置失败: {e}")
    return {}


def build_annotation_prompt(
    current_line: str, 
    context_lines: List[str], 
    config: MashupConfig
) -> Tuple[str, str]:
    """构建语义标注提示词"""
    
    # 尝试从配置文件加载自定义提示词
    prompt_config = load_prompt_config()
    annotation_cfg = prompt_config.get("annotation_prompt", {})
    custom_system = annotation_cfg.get("system_prompt", "")
    custom_template = annotation_cfg.get("user_prompt_template", "")
    custom_output_format = annotation_cfg.get("output_format", None)
    
    sentence_types = ", ".join([f"{t['name']}({t['id']})" for t in config.sentence_types[:10]])
    emotions = ", ".join([e['name'] for e in config.emotions])
    tones = ", ".join([t['name'] for t in config.tones])
    char_types = ", ".join([c['name'] for c in config.character_types])
    primary_funcs = ", ".join(config.primary_functions[:8])
    style_effects = ", ".join(config.style_effects[:8])
    
    # 使用自定义或默认系统提示词
    system_prompt = custom_system if custom_system else """你是专业的影视混剪创作专家，擅长分析台词在混剪中的使用潜力。
你需要分析每句台词的句型、情绪、语气等特征，帮助创作者找到能"接上"的下一句台词。
请严格按照JSON格式输出，不要添加任何额外说明。"""
    
    default_user_prompt = f"""
## 任务
分析以下台词在**脱离原片语境**后的混剪潜力，重点关注：
1. 这句话是什么类型？（问句？命令？威胁？嘲讽？）
2. 这句话后面能接什么类型的台词？
3. 这句话适合接在什么类型的台词后面？

## 当前台词
"{current_line}"

## 上下文参考
{json.dumps(context_lines, ensure_ascii=False)}

## 可选标签

### 句型分类（必选一个）
{sentence_types}

### 情绪标签（必选一个）
{emotions}

### 语气标签（必选一个）
{tones}

### 角色类型（必选一个）
{char_types}

### 混剪功能（选最合适的）
{primary_funcs}

### 风格效果（选最合适的）
{style_effects}

## 输出格式（严格JSON）
{{
  "sentence_type": "句型ID（如question, threat, mock等）",
  "emotion": "情绪名称",
  "tone": "语气名称",
  "character_type": "角色类型名称",
  "can_follow": ["能接在什么句型后面", "最多3个"],
  "can_lead_to": ["后面能接什么句型", "最多3个"],
  "keywords": ["关键词1", "关键词2", "最多3个"],
  "primary_function": "混剪功能",
  "style_effect": "风格效果",
  "editing_rhythm": "剪辑节奏建议",
  "audio_suggest": ["音效建议1", "音效建议2"],
  "semantic_summary": "一句话描述这句台词的混剪用途（20字以内）"
}}
"""

    # 如果配置中提供了自定义模板和输出格式，优先使用
    if custom_template:
        try:
            output_format_str = ""
            if isinstance(custom_output_format, dict):
                output_format_str = json.dumps(custom_output_format, ensure_ascii=False, indent=2)
            elif custom_output_format:
                output_format_str = str(custom_output_format)
            else:
                output_format_str = "{}"

            user_prompt = custom_template.format(
                current_line=current_line,
                context_lines=json.dumps(context_lines, ensure_ascii=False),
                sentence_types=sentence_types,
                emotions=emotions,
                tones=tones,
                character_types=char_types,
                primary_functions=primary_funcs,
                style_effects=style_effects,
                output_format=output_format_str
            )
        except Exception as e:
            print(f"⚠️ 自定义提示词模板渲染失败，使用默认模板: {e}")
            user_prompt = default_user_prompt
    else:
        user_prompt = default_user_prompt
    
    return system_prompt, user_prompt


def build_batch_annotation_prompt(
    lines_batch: List[Dict],  # [{"idx": 0, "text": "...", "context": [...]}]
    config: MashupConfig
) -> Tuple[str, str]:
    """构建批量语义标注提示词 - 一次处理多行台词"""
    
    sentence_types = ", ".join([f"{t['name']}({t['id']})" for t in config.sentence_types[:10]])
    emotions = ", ".join([e['name'] for e in config.emotions])
    tones = ", ".join([t['name'] for t in config.tones])
    char_types = ", ".join([c['name'] for c in config.character_types])
    primary_funcs = ", ".join(config.primary_functions[:8])
    style_effects = ", ".join(config.style_effects[:8])
    
    system_prompt = f"""你是专业的影视混剪创作专家，擅长分析台词在混剪中的使用潜力。
你需要批量分析多句台词的句型、情绪、语气等特征。

重要要求：
1. 必须为每一句台词都生成标注，不能遗漏任何一句
2. 输出必须是一个JSON对象，包含 results 数组，长度必须为 {len(lines_batch)}
3. results 数组顺序必须与输入台词顺序完全一致
4. 只输出JSON，不要添加任何其他说明文字

每个标注对象必须包含以下字段：
- line_index: 台词序号（从1开始）
- sentence_type: 句型分类
- emotion: 情绪标签
- tone: 语气标签
- character_type: 角色类型
- can_follow: 能接在什么句型后面的数组
- can_lead_to: 后面能接什么句型的数组
- keywords: 关键词数组
- primary_function: 混剪功能
- style_effect: 风格效果
- semantic_summary: 混剪用途描述"""
    
    # 构建批量台词列表
    lines_text = "\n".join([f'{i+1}. "{item["text"]}"' for i, item in enumerate(lines_batch)])
    
    user_prompt = f"""
## 任务
批量分析以下 {len(lines_batch)} 句台词在**脱离原片语境**后的混剪潜力。

## 待分析台词
{lines_text}

## 可选标签

### 句型分类
{sentence_types}

### 情绪标签
{emotions}

### 语气标签
{tones}

### 角色类型
{char_types}

### 混剪功能
{primary_funcs}

### 风格效果
{style_effects}

## 输出格式（严格JSON对象，results为数组）
{{
    "results": [
        {{
            "line_index": 1,
            "sentence_type": "句型ID",
            "emotion": "情绪名称",
            "tone": "语气名称",
            "character_type": "角色类型",
            "can_follow": ["能接在什么句型后面"],
            "can_lead_to": ["后面能接什么句型"],
            "keywords": ["关键词"],
            "primary_function": "混剪功能",
            "style_effect": "风格效果",
            "semantic_summary": "混剪用途描述"
        }}
    ]
}}
"""
    
    return system_prompt, user_prompt


def parse_batch_llm_response(response_text: str) -> List[Dict]:
    """解析批量标注的LLM响应，返回结果列表
    
    增强版：处理各种模型返回的非标准格式，包括：
    - Markdown代码块
    - <think>标签（Qwen3等模型的思考过程）
    - 其他非JSON内容
    """
    if not response_text:
        print("⚠️ 批量响应解析失败: 响应为空")
        return []
    
    try:
        # 清理响应文本
        cleaned = response_text.strip()
        
        # 移除markdown代码块标记
        cleaned = re.sub(r'```(?:json)?', '', cleaned)
        cleaned = re.sub(r'```', '', cleaned)
        
        # 移除<think>...</think>标签（Qwen3等模型的思考过程）
        cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL)
        
        # 移除其他可能的标签
        cleaned = re.sub(r'<[^>]+>.*?</[^>]+>', '', cleaned, flags=re.DOTALL)
        
        # 去除首尾空白
        cleaned = cleaned.strip()

        # 1) 先尝试直接解析完整JSON
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                # 兼容常见包装字段
                for key in ("results", "items", "data", "annotations", "outputs", "output", "choices"):
                    val = parsed.get(key)
                    if isinstance(val, list):
                        return val
                # 单对象返回，包装成列表
                print("⚠️ 批量响应返回了单个对象，包装为列表")
                return [parsed]
        except json.JSONDecodeError:
            pass

        # 2) 提取顶层JSON数组（避免误截取对象内数组字段）
        def _extract_top_level_array(text: str):
            in_str = False
            escape = False
            depth = 0
            start = None
            for i, ch in enumerate(text):
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == '[':
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == ']' and depth > 0:
                    depth -= 1
                    if depth == 0 and start is not None:
                        return text[start:i + 1]
            return None

        array_json = _extract_top_level_array(cleaned)
        if array_json:
            try:
                results = json.loads(array_json)
                if isinstance(results, list):
                    return results
            except json.JSONDecodeError as je:
                print(f"⚠️ JSON数组解析失败: {je}")
                print(f"   提取的JSON片段: {array_json[:200] if len(array_json) > 200 else array_json}")

        # 3) 尝试提取顶层对象
        def _extract_top_level_object(text: str):
            in_str = False
            escape = False
            depth = 0
            start = None
            for i, ch in enumerate(text):
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == '}' and depth > 0:
                    depth -= 1
                    if depth == 0 and start is not None:
                        return text[start:i + 1]
            return None

        obj_json = _extract_top_level_object(cleaned)
        if obj_json:
            try:
                result = json.loads(obj_json)
                if isinstance(result, dict):
                    print("⚠️ 批量响应返回了单个对象，包装为列表")
                    return [result]
            except json.JSONDecodeError as je:
                print(f"⚠️ JSON对象解析失败: {je}")
                print(f"   提取的JSON片段: {obj_json[:200] if len(obj_json) > 200 else obj_json}")
            
    except Exception as e:
        print(f"⚠️ 批量响应解析失败: {e}")
        print(f"   响应前300字符: {response_text[:300] if len(response_text) > 300 else response_text}")
    
    return []


# ==================== 响应解析 ====================
def parse_llm_response(response_text: str) -> Dict:
    """
    解析LLM响应
    增强版：处理各种模型返回的非标准格式
    """
    if not response_text:
        print("⚠️ JSON解析失败: 响应为空")
        return {"__parse_failed__": True, "raw_output": response_text}
    
    # 清理响应
    clean_text = response_text.strip()
    
    # 移除markdown代码块标记
    clean_text = re.sub(r'```(?:json)?', '', clean_text)
    clean_text = re.sub(r'```', '', clean_text)
    
    # 移除<think>...</think>标签（Qwen3等模型的思考过程）
    clean_text = re.sub(r'<think>.*?</think>', '', clean_text, flags=re.DOTALL)
    
    # 移除其他可能的标签
    clean_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', clean_text, flags=re.DOTALL)
    
    # 1) 直接尝试解析
    try:
        parsed = json.loads(clean_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    
    # 2) 提取顶层对象
    def _extract_top_level_object(text: str):
        in_str = False
        escape = False
        depth = 0
        start = None
        for i, ch in enumerate(text):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}' and depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    return text[start:i + 1]
        return None
    
    obj_json = _extract_top_level_object(clean_text)
    if obj_json:
        try:
            return json.loads(obj_json)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            print(f"   提取的JSON: {obj_json[:200] if len(obj_json) > 200 else obj_json}")
    
    print("⚠️ JSON解析失败: 未找到有效JSON对象")
    print(f"   响应前200字符: {response_text[:200] if len(response_text) > 200 else response_text}")
    return {"__parse_failed__": True, "raw_output": response_text}


def normalize_annotation(parsed: Dict) -> Dict:
    """将不同格式的LLM输出统一到LineAnnotation字段"""
    if not isinstance(parsed, dict):
        return get_default_annotation()

    if "mashup_analysis" in parsed:
        mashup = parsed.get("mashup_analysis") or {}
        quick = mashup.get("quick_tags", {})
        semantic = mashup.get("semantic_summary", {})
        creative = mashup.get("creative_params", {})

        return {
            "sentence_type": parsed.get("sentence_type", ""),
            "emotion": parsed.get("emotion", ""),
            "tone": parsed.get("tone", ""),
            "character_type": parsed.get("character_type", ""),
            "can_follow": parsed.get("can_follow", []) or [],
            "can_lead_to": parsed.get("can_lead_to", []) or [],
            "keywords": semantic.get("keywords", []) or parsed.get("keywords", []) or [],
            "primary_function": quick.get("primary", "") or parsed.get("primary_function", ""),
            "style_effect": quick.get("style", "") or parsed.get("style_effect", ""),
            "editing_rhythm": quick.get("rhythm", "") or parsed.get("editing_rhythm", ""),
            "audio_suggest": creative.get("audio_suggestions", []) or parsed.get("audio_suggest", []) or [],
            "semantic_summary": semantic.get("brief", "") or semantic.get("use_case", "") or parsed.get("semantic_summary", ""),
            "mashup_analysis": mashup,
            "raw_output": parsed
        }

    # 默认格式：避免 raw_output 自引用导致递归
    safe_raw_output = dict(parsed)
    safe_raw_output.pop("raw_output", None)
    normalized = dict(parsed)
    normalized["raw_output"] = safe_raw_output
    return normalized


def get_default_annotation() -> Dict:
    """获取默认标注"""
    return {
        "sentence_type": "exclaim",
        "emotion": "calm",
        "tone": "certain",
        "character_type": "bystander",
        "can_follow": [],
        "can_lead_to": [],
        "keywords": [],
        "primary_function": "其他",
        "style_effect": "其他",
        "editing_rhythm": "常规剪辑",
        "audio_suggest": [],
        "semantic_summary": "常规台词"
    }


def get_unknown_annotation() -> Dict:
    """获取解析失败时的未知标注（避免默认值）"""
    return {
        "sentence_type": "未知",
        "emotion": "未知",
        "tone": "未知",
        "character_type": "未知",
        "can_follow": [],
        "can_lead_to": [],
        "keywords": [],
        "primary_function": "未知",
        "style_effect": "未知",
        "editing_rhythm": "",
        "audio_suggest": [],
        "semantic_summary": "未能解析到有效标注"
    }


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
        if len(parts) < 3:
            continue
        try:
            time_range = parts[1]
            text = " ".join(parts[2:]).replace("\n", " ").strip()
            if not text or "-->" not in time_range:
                continue
            start_str, end_str = time_range.split(" --> ")
            lines.append({
                "text": text,
                "start": _time_to_seconds(start_str),
                "end": _time_to_seconds(end_str)
            })
        except Exception:
            continue
    
    return lines


def _time_to_seconds(time_str: str) -> float:
    """时间字符串转秒数"""
    h, m, s_ms = time_str.replace(",", ".").split(":")
    return float(h) * 3600 + float(m) * 60 + float(s_ms)


# ==================== Checkpoint 工具函数 ====================
ANNOTATION_DIR = Path(__file__).parent.parent.parent / "data" / "annotations"

def _checkpoint_path(movie_id: str) -> Path:
    """获取 checkpoint 文件路径"""
    return ANNOTATION_DIR / f"{movie_id}_checkpoint.json"

def _annotation_output_path(movie_id: str) -> Path:
    """获取标注输出文件路径"""
    return ANNOTATION_DIR / f"{movie_id}_annotated.json"

def load_checkpoint(movie_id: str) -> Optional[Dict]:
    """加载 checkpoint（如果存在）
    
    Returns:
        checkpoint dict with keys:
            movie_id, llm_provider, total_lines, completed_indices,
            last_save_time, subtitle_path, movie_name
        or None if no checkpoint
    """
    cp_path = _checkpoint_path(movie_id)
    if cp_path.exists():
        try:
            with open(cp_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 加载checkpoint失败: {e}")
    return None

def delete_checkpoint(movie_id: str):
    """删除 checkpoint 文件"""
    cp_path = _checkpoint_path(movie_id)
    if cp_path.exists():
        cp_path.unlink()
        print(f"🗑️ 已删除checkpoint: {cp_path.name}")


# ==================== 语义标注器 ====================
class SemanticAnnotator:
    """语义标注器"""
    
    def __init__(self, llm_provider: str = None, max_retries: int = None, save_interval: int = None):
        self.mashup_config = MashupConfig()
        self.prompt_config = load_prompt_config()
        self.batch_settings = self.prompt_config.get("batch_settings", {})
        self.llm_manager = LLMProviderManager()
        
        # 动态参数覆盖配置文件设置
        if max_retries is not None:
            self.batch_settings["max_retries"] = max_retries
        if save_interval is not None:
            self.batch_settings["save_interval"] = save_interval
        
        if llm_provider:
            self.llm_manager.set_active_provider(llm_provider)
        
        self.llm = self.llm_manager.get_provider()
        self.provider_name = self.llm_manager.active_provider
        
        # 暂停事件（区别于取消）
        self._pause_event = threading.Event()
    
    def annotate_line(
        self, 
        text: str, 
        context_lines: List[str],
        source_movie: str = "",
        source_file: str = "",
        start: float = 0,
        end: float = 0,
        line_id: str = ""
    ) -> LineAnnotation:
        """标注单行台词"""
        
        system_prompt, user_prompt = build_annotation_prompt(
            text, context_lines, self.mashup_config
        )
        
        retry_on_failure = self.batch_settings.get("retry_on_failure", True)
        max_retries = int(self.batch_settings.get("max_retries", 2))
        attempts = 0

        while True:
            try:
                response = self.llm.chat(system_prompt, user_prompt)
                parsed = parse_llm_response(response)
                if isinstance(parsed, dict) and parsed.get("__parse_failed__"):
                    raise ValueError("LLM返回无法解析的JSON")
                break
            except Exception as e:
                attempts += 1
                if retry_on_failure and attempts <= max_retries:
                    print(f"⚠️ 标注失败，重试 {attempts}/{max_retries}: {e}")
                    continue
                print(f"❌ 标注失败: {e}")
                parsed = get_unknown_annotation()
                break

        normalized = normalize_annotation(parsed)
        if isinstance(normalized, dict) and normalized.get("__parse_failed__"):
            normalized = get_unknown_annotation()
        
        # 计算时长
        duration = end - start if end > start else 0
        
        # � 英文→中文转换
        sentence_type = to_chinese(normalized.get("sentence_type", ""), SENTENCE_TYPE_MAP)
        emotion = to_chinese(normalized.get("emotion", ""), EMOTION_MAP)
        tone = to_chinese(normalized.get("tone", ""), TONE_MAP)
        character_type = to_chinese(normalized.get("character_type", ""), CHARACTER_TYPE_MAP)
        
        # can_follow/can_lead_to 也转中文
        can_follow = [to_chinese(t, SENTENCE_TYPE_MAP) for t in normalized.get("can_follow", [])]
        can_lead_to = [to_chinese(t, SENTENCE_TYPE_MAP) for t in normalized.get("can_lead_to", [])]
        
        # 📍 构建来源信息 (精简版 - 只保留定位必需信息)
        source_info = SourceInfo(
            media_id=source_movie,  # 关联media_index的key
            start=start,
            end=end
        )
        
        # 🎭 构建混剪核心标签 (全中文)
        mashup_tags = MashupTags(
            sentence_type=sentence_type,
            emotion=emotion,
            tone=tone,
            primary_function=normalized.get("primary_function", ""),
            style_effect=normalized.get("style_effect", ""),
            can_follow=can_follow,
            can_lead_to=can_lead_to,
            keywords=normalized.get("keywords", []),
            character_type=character_type
        )
        
        # 📊 构建剪辑参数 (精简版)
        editing_params = EditingParams(
            rhythm=normalized.get("editing_rhythm", ""),
            duration=round(duration, 2)
        )
        
        # 构建标注结果 (精简版)
        annotation = LineAnnotation(
            id=line_id,
            text=text,
            source=source_info,
            mashup_tags=mashup_tags,
            editing_params=editing_params,
            semantic_summary=normalized.get("semantic_summary", ""),
            annotated_at=time.time()
        )
        
        # 生成向量化文本
        annotation.generate_vector_text()
        
        return annotation
    
    def annotate_batch(
        self,
        lines_batch: List[Dict],  # [{"idx": int, "text": str, "start": float, "end": float}]
        movie_name: str = "",
        movie_id: str = "",  # 豆瓣ID，用于media_id
        subtitle_path: str = ""
    ) -> List[LineAnnotation]:
        """批量标注多行台词 - 一次LLM调用处理多行
        
        Args:
            lines_batch: 待标注的台词列表
            movie_name: 影片名称（用于提示词和id生成）
            movie_id: 影片豆瓣ID（用于media_id关联影片库）
            subtitle_path: 字幕文件路径
        """""
        
        if not lines_batch:
            return []
        
        # 构建批量提示词
        batch_items = [{"idx": item["idx"], "text": item["text"]} for item in lines_batch]
        system_prompt, user_prompt = build_batch_annotation_prompt(batch_items, self.mashup_config)
        
        retry_on_failure = self.batch_settings.get("retry_on_failure", True)
        max_retries = int(self.batch_settings.get("max_retries", 2))
        attempts = 0
        
        parsed_results = []
        raw_response = ""
        actual_media_id = movie_id if movie_id else movie_name
        while True:
            try:
                raw_response = self.llm.chat(system_prompt, user_prompt)
                parsed_results = parse_batch_llm_response(raw_response)
                
                # 如果解析结果为空或数量不匹配，记录警告
                if len(parsed_results) == 0:
                    print(f"⚠️ 批量解析返回空结果，尝试重试...")
                    attempts += 1
                    if retry_on_failure and attempts <= max_retries:
                        continue
                    print(f"❌ 批量解析多次失败，将使用默认值")
                elif len(parsed_results) != len(lines_batch):
                    print(f"⚠️ 批量解析结果数量不匹配: 期望 {len(lines_batch)}，实际 {len(parsed_results)}")
                
                break
            except Exception as e:
                attempts += 1
                if retry_on_failure and attempts <= max_retries:
                    print(f"⚠️ 批量标注失败，重试 {attempts}/{max_retries}: {e}")
                    continue
                print(f"❌ 批量标注失败: {e}")
                break
        
        # 如果批量结果严重不足，改用单行模式补全
        if len(parsed_results) < len(lines_batch):
            print("⚠️ 批量结果不足，回退到单行标注模式补全")
            fallback_results = []
            for item in lines_batch:
                idx = item["idx"]
                try:
                    ann = self.annotate_line(
                        text=item["text"],
                        context_lines=item.get("context", []),
                        source_movie=actual_media_id,
                        source_file=subtitle_path,
                        start=item["start"],
                        end=item["end"],
                        line_id=f"{actual_media_id}_line_{idx}"
                    )
                    fallback_results.append((idx, ann))
                except Exception as e:
                    print(f"❌ 回退单行标注失败: {e}")
                    fallback_results.append((idx, LineAnnotation(
                        id=f"{actual_media_id}_line_{idx}",
                        text=item["text"],
                        source=SourceInfo(
                            media_id=actual_media_id,
                            start=item["start"],
                            end=item["end"]
                        ),
                        annotated_at=time.time()
                    )))
            return fallback_results

        # 将解析结果映射回原始行
        results = []
        
        # 记录映射情况
        parsed_count = len(parsed_results)
        batch_count = len(lines_batch)
        
        if parsed_count != batch_count:
            print(f"⚠️ 批量结果数量不匹配: 期望 {batch_count}，实际返回 {parsed_count}")
        
        # 如果解析结果数量与批次大小相同，按顺序直接映射
        use_sequential_mapping = parsed_count == batch_count
        
        # 创建一个通过line_index查找的字典，用于索引匹配
        index_map = {}
        for pr in parsed_results:
            line_idx = pr.get("line_index", pr.get("index", None))
            if line_idx is not None:
                index_map[line_idx] = pr
        
        for i, item in enumerate(lines_batch):
            idx = item["idx"]
            
            # 从批量结果中找到对应的标注
            parsed = None
            
            if use_sequential_mapping:
                # 按顺序匹配（更可靠）
                parsed = parsed_results[i]
            else:
                # 尝试通过 line_index 匹配（支持从0或1开始）
                if i + 1 in index_map:
                    parsed = index_map[i + 1]
                elif i in index_map:
                    parsed = index_map[i]
                elif i < parsed_count:
                    # 回退：如果索引在范围内，按顺序使用
                    parsed = parsed_results[i]
            
            if parsed is None:
                # 按行补标注，避免默认值
                print(f"⚠️ 行 {i} 无法匹配到标注结果，按行补标注")
                try:
                    parsed_line = self.annotate_line(
                        text=item["text"],
                        context_lines=item.get("context", []),
                        source_movie=actual_media_id,
                        source_file=subtitle_path,
                        start=item["start"],
                        end=item["end"],
                        line_id=f"{actual_media_id}_line_{idx}"
                    )
                    results.append((idx, parsed_line))
                    continue
                except Exception as e:
                    print(f"❌ 按行补标注失败: {e}")
                    parsed = get_unknown_annotation()
            
            normalized = normalize_annotation(parsed)
            
            # 计算时长
            duration = item["end"] - item["start"] if item["end"] > item["start"] else 0
            
            # 英文→中文转换
            sentence_type = to_chinese(normalized.get("sentence_type", ""), SENTENCE_TYPE_MAP)
            emotion = to_chinese(normalized.get("emotion", ""), EMOTION_MAP)
            tone = to_chinese(normalized.get("tone", ""), TONE_MAP)
            character_type = to_chinese(normalized.get("character_type", ""), CHARACTER_TYPE_MAP)
            
            can_follow = [to_chinese(t, SENTENCE_TYPE_MAP) for t in normalized.get("can_follow", [])]
            can_lead_to = [to_chinese(t, SENTENCE_TYPE_MAP) for t in normalized.get("can_lead_to", [])]
            
            source_info = SourceInfo(
                media_id=actual_media_id,
                start=item["start"],
                end=item["end"]
            )
            
            mashup_tags = MashupTags(
                sentence_type=sentence_type,
                emotion=emotion,
                tone=tone,
                character_type=character_type,
                can_follow=can_follow,
                can_lead_to=can_lead_to,
                keywords=normalized.get("keywords", []),
                primary_function=normalized.get("primary_function", ""),
                style_effect=normalized.get("style_effect", "")
            )
            
            editing_params = EditingParams(
                rhythm=normalized.get("editing_rhythm", ""),
                duration=round(duration, 2)
            )
            
            annotation = LineAnnotation(
                id=f"{actual_media_id}_line_{idx}",
                text=item["text"],
                source=source_info,
                mashup_tags=mashup_tags,
                editing_params=editing_params,
                semantic_summary=normalized.get("semantic_summary", ""),
                annotated_at=time.time()
            )
            
            annotation.generate_vector_text()
            results.append((idx, annotation))
        
        return results
    
    def annotate_subtitle_file(
        self,
        subtitle_path: str,
        movie_name: str = "",
        movie_id: str = "",  # 豆瓣ID，用于media_id关联影片库
        window_size: Optional[int] = None,
        max_workers: Optional[int] = None,
        batch_size: Optional[int] = None,
        progress_callback=None,
        cancel_event=None,
        pause_event=None,
        resume_from_checkpoint: bool = False
    ) -> List[LineAnnotation]:
        """标注整个字幕文件（支持增量保存和断点续标）
        
        Args:
            subtitle_path: 字幕文件路径
            movie_name: 影片名称（用于提示词和显示）
            movie_id: 影片豆瓣ID（用于media_id，便于与影片库关联）
            batch_size: 每次LLM调用处理的台词数量（真正的批处理）
            max_workers: 并发的批处理任务数
            window_size: 上下文窗口大小（用于单行标注模式）
            progress_callback: 进度回调
            cancel_event: 取消事件
            pause_event: 暂停事件（set时暂停）
            resume_from_checkpoint: 是否从checkpoint恢复
        """
        
        # 如果没有提供movie_id，使用movie_name作为备选
        actual_media_id = movie_id if movie_id else movie_name

        if batch_size is None:
            batch_size = int(self.batch_settings.get("batch_size", 1))
        if max_workers is None:
            max_workers = int(self.batch_settings.get("max_concurrent_workers", 4))
        if window_size is None:
            window_size = int(self.batch_settings.get("context_window_size", 2))
        
        save_interval = int(self.batch_settings.get("save_interval", 50))
        
        # 解析字幕
        lines = parse_srt(subtitle_path)
        if not lines:
            print("❌ 未解析到有效字幕内容")
            return []
        
        total = len(lines)
        if total <= 0:
            return []

        # 当批处理大小大于字幕总行数时，自动收缩到总行数
        if batch_size > total:
            batch_size = total
        if batch_size < 1:
            batch_size = 1
        
        # ===== 断点恢复：加载已完成的行 =====
        completed_indices: set = set()
        results: List[LineAnnotation] = [None] * total
        
        if resume_from_checkpoint:
            checkpoint = load_checkpoint(movie_id)
            if checkpoint and checkpoint.get("completed_indices"):
                completed_indices = set(checkpoint["completed_indices"])
                # 从已有的annotated JSON加载已完成的结果
                ann_path = _annotation_output_path(movie_id)
                if ann_path.exists():
                    try:
                        with open(ann_path, "r", encoding="utf-8") as f:
                            existing_data = json.load(f)
                        for ann_dict in existing_data:
                            # 从id中提取行号（格式: {media_id}_line_{idx}）
                            ann_id = ann_dict.get("id", "")
                            parts = ann_id.rsplit("_line_", 1)
                            if len(parts) == 2 and parts[1].isdigit():
                                idx = int(parts[1])
                                if 0 <= idx < total:
                                    results[idx] = LineAnnotation.from_dict(ann_dict)
                        print(f"🔄 从checkpoint恢复: 已完成 {len(completed_indices)}/{total} 行")
                    except Exception as e:
                        print(f"⚠️ 加载已有标注失败，从头开始: {e}")
                        completed_indices = set()
                        results = [None] * total
        
        # 判断使用批处理模式还是单行模式
        use_batch_mode = batch_size > 1
        
        remaining = total - len(completed_indices)
        if remaining <= 0:
            print(f"✅ 所有 {total} 行已标注完成，无需继续")
            results = [r for r in results if r is not None]
            return results
        
        if use_batch_mode:
            print(f"🔧 使用批处理模式: batch_size={batch_size}, max_workers={max_workers}, save_interval={save_interval}")
            print(f"📊 找到 {total} 行字幕，待处理 {remaining} 行")
        else:
            print(f"🔧 使用单行模式: window_size={window_size}, max_workers={max_workers}, save_interval={save_interval}")
            print(f"📊 找到 {total} 行字幕，待处理 {remaining} 行")
        
        start_time = time.time()
        completed = len(completed_indices)
        last_save_completed = completed  # 上次增量保存时的完成数
        paused = False  # 是否被暂停
        
        # ===== 增量保存辅助函数 =====
        def _incremental_save():
            """增量保存当前结果和checkpoint"""
            nonlocal last_save_completed
            ANNOTATION_DIR.mkdir(parents=True, exist_ok=True)
            
            # 保存已完成的标注结果
            completed_results = [r for r in results if r is not None]
            if completed_results:
                out_path = _annotation_output_path(movie_id)
                data = [a.to_dict() for a in completed_results]
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 保存checkpoint
            current_completed = [i for i in range(total) if results[i] is not None]
            cp_data = {
                "movie_id": movie_id,
                "movie_name": movie_name,
                "subtitle_path": subtitle_path,
                "llm_provider": self.provider_name,
                "total_lines": total,
                "completed_indices": current_completed,
                "completed_count": len(current_completed),
                "last_save_time": time.time(),
                "batch_size": batch_size,
                "save_interval": save_interval
            }
            cp_path = _checkpoint_path(movie_id)
            with open(cp_path, "w", encoding="utf-8") as f:
                json.dump(cp_data, f, ensure_ascii=False, indent=2)
            
            last_save_completed = completed
            print(f"💾 增量保存: {len(current_completed)}/{total} 行 ({len(current_completed)/total:.1%})")
        
        def _check_pause():
            """检查暂停事件，如果设置了就等待"""
            if pause_event and pause_event.is_set():
                print(f"⏸️ 标注已暂停，当前进度 {completed}/{total}")
                _incremental_save()
                # 等待暂停解除或取消
                while pause_event.is_set():
                    if cancel_event and cancel_event.is_set():
                        return True  # 暂停期间被取消
                    time.sleep(0.5)
                print(f"▶️ 标注恢复")
            return False
        
        if use_batch_mode:
            # 批处理模式：将台词分批，每批一次LLM调用
            batches = []
            for i in range(0, total, batch_size):
                if cancel_event and cancel_event.is_set():
                    break
                batch = []
                for j in range(i, min(i + batch_size, total)):
                    if j in completed_indices:
                        continue  # 跳过已完成的行
                    # 预计算上下文（用于批量失败时的回退单行标注）
                    start_idx = max(0, j - window_size)
                    end_idx = min(total, j + window_size + 1)
                    context = [lines[k]["text"] for k in range(start_idx, end_idx) if k != j]
                    batch.append({
                        "idx": j,
                        "text": lines[j]["text"],
                        "start": lines[j]["start"],
                        "end": lines[j]["end"],
                        "context": context
                    })
                if batch:
                    batches.append(batch)
            
            def process_batch(batch):
                return self.annotate_batch(batch, movie_name, actual_media_id, subtitle_path)
            
            # 并行处理多个批次
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for batch in batches:
                    if cancel_event and cancel_event.is_set():
                        break
                    if _check_pause():
                        break
                    futures[executor.submit(process_batch, batch)] = batch
                
                for future in as_completed(futures):
                    if cancel_event and cancel_event.is_set():
                        for f in futures:
                            f.cancel()
                        break
                    if _check_pause():
                        for f in futures:
                            f.cancel()
                        break
                    batch = futures[future]
                    try:
                        batch_results = future.result()
                        for idx, annotation in batch_results:
                            results[idx] = annotation
                            completed += 1
                            completed_indices.add(idx)
                            
                            if progress_callback and not (cancel_event and cancel_event.is_set()):
                                progress_callback(completed, total)
                        
                        # 控制台进度
                        elapsed = time.time() - start_time
                        speed = completed / elapsed if elapsed > 0 else 0
                        print(f"🔄 进度: {completed}/{total} ({completed/total:.1%}) | 速度: {speed:.1f}行/秒")
                        
                        # ===== 增量保存检查 =====
                        if save_interval > 0 and (completed - last_save_completed) >= save_interval:
                            _incremental_save()
                        
                    except Exception as e:
                        print(f"❌ 批次处理失败: {e}")
                        for item in batch:
                            idx = item["idx"]
                            results[idx] = LineAnnotation(
                                id=f"{actual_media_id}_line_{idx}",
                                text=item["text"],
                                source=SourceInfo(
                                    media_id=actual_media_id,
                                    start=item["start"],
                                    end=item["end"]
                                ),
                                annotated_at=time.time()
                            )
                            completed += 1
                            completed_indices.add(idx)
                            if progress_callback and not (cancel_event and cancel_event.is_set()):
                                progress_callback(completed, total)
        else:
            # 单行模式：每行单独一次LLM调用
            def process_line(idx: int) -> LineAnnotation:
                line = lines[idx]
                start_idx = max(0, idx - window_size)
                end_idx = min(total, idx + window_size + 1)
                context = [lines[j]["text"] for j in range(start_idx, end_idx) if j != idx]
                
                return self.annotate_line(
                    text=line["text"],
                    context_lines=context,
                    source_movie=actual_media_id,  # 使用movie_id作为media_id
                    source_file=subtitle_path,
                    start=line["start"],
                    end=line["end"],
                    line_id=f"{actual_media_id}_line_{idx}"
                )
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for i in range(total):
                    if i in completed_indices:
                        continue  # 跳过已完成的行
                    if cancel_event and cancel_event.is_set():
                        break
                    if _check_pause():
                        break
                    futures[executor.submit(process_line, i)] = i
                
                for future in as_completed(futures):
                    if cancel_event and cancel_event.is_set():
                        for f in futures:
                            f.cancel()
                        break
                    if _check_pause():
                        for f in futures:
                            f.cancel()
                        break
                    idx = futures[future]
                    try:
                        results[idx] = future.result()
                        completed += 1
                        completed_indices.add(idx)
                        
                        if progress_callback and not (cancel_event and cancel_event.is_set()):
                            progress_callback(completed, total)
                        
                        if completed % max(1, total // 10) == 0:
                            elapsed = time.time() - start_time
                            speed = completed / elapsed if elapsed > 0 else 0
                            print(f"🔄 进度: {completed}/{total} ({completed/total:.1%}) | 速度: {speed:.1f}行/秒")
                        
                        # ===== 增量保存检查 =====
                        if save_interval > 0 and (completed - last_save_completed) >= save_interval:
                            _incremental_save()
                            
                    except Exception as e:
                        print(f"❌ 行 {idx} 处理失败: {e}")
                        results[idx] = LineAnnotation(
                            id=f"{actual_media_id}_line_{idx}",
                            text=lines[idx]["text"],
                            source=SourceInfo(
                                media_id=actual_media_id,
                                start=lines[idx]["start"],
                                end=lines[idx]["end"]
                            ),
                            annotated_at=time.time()
                        )
                        completed += 1
                        completed_indices.add(idx)
        
        # 检查是否因暂停而中断
        if pause_event and pause_event.is_set():
            _incremental_save()
            paused = True
            print(f"⏸️ 标注暂停，已保存 {completed}/{total} 行")
            # 返回已完成的部分
            results = [r for r in results if r is not None]
            return results
        
        # 检查是否因取消而中断
        if cancel_event and cancel_event.is_set():
            # 取消时也做增量保存（保留已完成的部分）
            _incremental_save()
            print(f"⚠️ 标注已取消，已保存 {completed}/{total} 行")
            results = [r for r in results if r is not None]
            return results
        
        # 过滤None
        results = [r for r in results if r is not None]
        
        # 正常完成：做最终保存并删除checkpoint
        _incremental_save()
        delete_checkpoint(movie_id)
        
        print(f"✅ 标注完成！共 {len(results)} 行，耗时 {time.time() - start_time:.1f}秒")
        
        return results
    
    def save_annotations(
        self, 
        annotations: List[LineAnnotation], 
        output_path: str
    ):
        """保存标注结果"""
        data = [a.to_dict() for a in annotations]
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 标注结果已保存: {output_path}")


# ==================== CLI ====================
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="台词混剪语义标注工具 v5.0")
    parser.add_argument("input", help="SRT字幕文件路径")
    parser.add_argument("output", help="输出JSON文件路径")
    parser.add_argument("--movie", default="", help="电影名称")
    parser.add_argument("--provider", default=None, help="LLM提供者 (local_qwen, openai, deepseek等)")
    parser.add_argument("--window", type=int, default=2, help="上下文窗口大小")
    parser.add_argument("--workers", type=int, default=4, help="并发线程数")
    parser.add_argument("--list-providers", action="store_true", help="列出所有可用的LLM提供者")
    
    args = parser.parse_args()
    
    # 列出提供者
    if args.list_providers:
        manager = LLMProviderManager()
        print("\n📋 可用的LLM提供者:")
        for p in manager.list_providers():
            status = "✅ 当前" if p["is_active"] else "  "
            print(f"  {status} {p['id']}: {p['name']} ({p['type']})")
            if p["description"]:
                print(f"       {p['description']}")
        return
    
    # 执行标注
    print("=" * 60)
    print("🎬 台词混剪语义标注工具 v5.0")
    print("=" * 60)
    
    annotator = SemanticAnnotator(llm_provider=args.provider)
    
    annotations = annotator.annotate_subtitle_file(
        subtitle_path=args.input,
        movie_name=args.movie or Path(args.input).stem,
        window_size=args.window,
        max_workers=args.workers
    )
    
    if annotations:
        annotator.save_annotations(annotations, args.output)
        
        # 显示示例
        print("\n📝 标注示例:")
        for ann in annotations[:3]:
            tags = ann.mashup_tags
            print(f"  台词: {ann.text[:40]}...")
            print(f"  句型: {tags.sentence_type} | 情绪: {tags.emotion} | 语气: {tags.tone}")
            print(f"  可接: {tags.can_follow} | 可引: {tags.can_lead_to}")
            print(f"  向量文本: {ann.vector_text[:60]}...")
            print()


if __name__ == "__main__":
    main()
