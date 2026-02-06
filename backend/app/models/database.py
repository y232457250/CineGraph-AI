# backend/app/models/database.py
"""
CineGraph-AI SQLAlchemy ORM 数据库模型
融合混剪标签体系 + 无限画布 + 抖音算法优化

基于设计文档实现，支持：
1. 四层标签体系（句型、情绪、语气、角色）
2. 无限画布（树形节点结构）
3. 抖音混剪指标（hook_score, intensity 等）
4. 接话规则实体化
"""

import enum
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, ForeignKey, Text,
    DateTime, Boolean, Table, Index, event, JSON, Enum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, backref
from sqlalchemy.sql import text

Base = declarative_base()

# ==================== 枚举类型（基于 mashup_v5_config） ====================

class SentenceType(enum.Enum):
    """句型分类 - 决定接话逻辑"""
    QUESTION = "question"           # 问句
    ANSWER = "answer"               # 答句
    COMMAND = "command"             # 命令
    THREAT = "threat"               # 威胁
    COUNTER_QUESTION = "counter_question"  # 反问
    MOCK = "mock"                   # 嘲讽
    REFUSE = "refuse"               # 拒绝
    FEAR = "fear"                   # 害怕
    SURRENDER = "surrender"         # 求饶
    COUNTER_ATTACK = "counter_attack"      # 反击
    ANGER = "anger"                 # 愤怒
    EXCLAIM = "exclaim"             # 感叹
    PERSUADE = "persuade"           # 劝说
    AGREE = "agree"                 # 同意
    ACTION = "action"               # 行动
    INTERRUPT = "interrupt"         # 打断
    REVEAL = "reveal"               # 揭示
    OBEY = "obey"                   # 服从
    COMMENT = "comment"             # 评论
    SHOCK = "shock"                 # 震惊
    STATEMENT = "statement"         # 陈述

class Emotion(enum.Enum):
    """情绪标签 - 用于递进和对比"""
    ANGRY = "angry"                 # 愤怒
    RAGE = "rage"                   # 狂怒
    FEAR = "fear"                   # 害怕
    PANIC = "panic"                 # 恐慌
    MOCK = "mock"                   # 嘲讽
    HUMILIATE = "humiliate"         # 羞辱
    PROUD = "proud"                 # 得意
    ARROGANT = "arrogant"           # 嚣张
    HELPLESS = "helpless"           # 无奈
    CALM = "calm"                   # 冷静
    DETERMINED = "determined"       # 坚定
    SHOCK = "shock"                 # 震惊
    FUNNY = "funny"                 # 搞笑
    ABSURD = "absurd"               # 荒诞
    CHAOS = "chaos"                 # 混乱
    TSUNDERE = "tsundere"           # 傲娇
    HONEST = "honest"               # 坦诚
    BRAVE = "brave"                 # 勇敢
    HUMBLE = "humble"               # 卑微
    RESPECT = "respect"             # 尊敬
    NORMAL = "normal"               # 正常
    SERIOUS = "serious"             # 严肃
    DIRECT = "direct"               # 直接

class Tone(enum.Enum):
    """语气标签"""
    STRONG = "strong"               # 强硬
    WEAK = "weak"                   # 软弱
    PROVOCATIVE = "provocative"     # 挑衅
    HUMBLE = "humble"               # 卑微
    ARROGANT = "arrogant"           # 傲慢
    QUESTIONING = "questioning"     # 质疑
    CERTAIN = "certain"             # 肯定
    HESITANT = "hesitant"           # 犹豫
    PLEADING = "pleading"           # 恳求
    THREATENING = "threatening"     # 威胁

class CharacterType(enum.Enum):
    """角色类型 - 跨剧匹配"""
    EMPEROR = "emperor"             # 皇帝/领导
    OFFICIAL = "official"           # 大臣/下属
    HERO = "hero"                   # 英雄/主角
    VILLAIN = "villain"             # 反派
    COMIC = "comic"                 # 搞笑角色
    VICTIM = "victim"               # 受害者
    BYSTANDER = "bystander"         # 旁观者
    WISE = "wise"                   # 智者/军师

class TransitionType(enum.Enum):
    """情绪/句型转换类型"""
    ESCALATION = "escalation"       # 递进
    CONTRAST = "contrast"           # 对比
    CONTINUATION = "continuation"   # 延续
    CALLBACK = "callback"           # callback

class NodeType(enum.Enum):
    """画布节点类型"""
    ROOT = "root"                   # 根节点
    SCENE = "scene"                 # 场景/幕
    CLIP = "clip"                   # 片段（引用台词）
    TRANSITION = "transition"       # 转场
    EFFECT = "effect"               # 特效节点
    NOTE = "note"                   # 备注

# ==================== 关联表 ====================

line_function_association = Table(
    'line_function_association',
    Base.metadata,
    Column('line_id', Integer, ForeignKey('lines.id', ondelete='CASCADE'), primary_key=True),
    Column('function_name', String(50), primary_key=True),
    Column('confidence', Float, default=1.0)
)

line_style_association = Table(
    'line_style_association',
    Base.metadata,
    Column('line_id', Integer, ForeignKey('lines.id', ondelete='CASCADE'), primary_key=True),
    Column('style_name', String(50), primary_key=True),
    Column('confidence', Float, default=1.0)
)

# ==================== 核心实体 ====================

class Movie(Base):
    """影视作品库"""
    __tablename__ = 'movies'
    
    id = Column(String(50), primary_key=True)  # douban_id 或 custom_xxx
    title = Column(String(200), nullable=False, index=True)
    original_title = Column(String(200))
    year = Column(Integer, index=True)
    media_type = Column(String(20), default='movie')  # movie/tv/animation
    
    # 文件信息
    folder = Column(String(500))
    poster_url = Column(String(500))
    local_poster = Column(String(500))
    
    # 豆瓣元数据
    director = Column(String(200))
    writer = Column(String(200))
    starring = Column(Text)  # JSON 数组
    genre = Column(String(200))
    country = Column(String(100))
    language = Column(String(100))
    release_date = Column(String(50))
    douban_url = Column(String(500))
    rating = Column(String(10))
    
    # 跨界类型（crossover_genres）
    crossover_genre = Column(String(50))  # 古装+科幻/动画+现实/武侠+现代...
    
    # 状态
    status = Column(String(20), default='pending')  # pending, ready
    status_annotate = Column(String(20), default='pending')  # pending, partial, done
    status_vectorize = Column(String(20), default='pending')  # pending, partial, done
    
    import_batch = Column(String(50), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    episodes = relationship("Episode", back_populates="movie", cascade="all, delete-orphan")
    lines = relationship("Line", back_populates="movie", cascade="all, delete-orphan", lazy="dynamic")
    characters = relationship("Character", back_populates="movie", cascade="all, delete-orphan", lazy="dynamic")
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        starring = []
        if self.starring:
            try:
                starring = json.loads(self.starring)
            except:
                starring = []
        
        result = {
            'id': self.id,
            'douban_id': self.id,  # 兼容旧代码
            'title': self.title,
            'original_title': self.original_title,
            'year': self.year,
            'media_type': self.media_type,
            'folder': self.folder,
            'poster_url': self.poster_url,
            'local_poster': self.local_poster,
            'director': self.director,
            'writer': self.writer,
            'starring': starring,
            'genre': self.genre,
            'country': self.country,
            'language': self.language,
            'release_date': self.release_date,
            'douban_url': self.douban_url,
            'rating': self.rating,
            'crossover_genre': self.crossover_genre,
            'status': self.status,
            'status_annotate': self.status_annotate,
            'status_vectorize': self.status_vectorize,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # 添加剧集信息
        if self.episodes:
            result['episodes'] = [ep.to_dict() for ep in self.episodes]
        
        return result


class Episode(Base):
    """剧集表"""
    __tablename__ = 'episodes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(String(50), ForeignKey('movies.id', ondelete='CASCADE'), nullable=False)
    episode_number = Column(Integer, nullable=False)
    video_path = Column(String(500))
    subtitle_path = Column(String(500))
    video_filename = Column(String(200))
    subtitle_filename = Column(String(200))
    status_vectorize = Column(String(20), default='pending')
    
    movie = relationship("Movie", back_populates="episodes")
    
    __table_args__ = (
        UniqueConstraint('movie_id', 'episode_number', name='uq_episode'),
    )
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'movie_id': self.movie_id,
            'episode_number': self.episode_number,
            'video_path': self.video_path,
            'subtitle_path': self.subtitle_path,
            'video_filename': self.video_filename,
            'subtitle_filename': self.subtitle_filename,
            'status_vectorize': self.status_vectorize,
        }


class Character(Base):
    """角色规范化"""
    __tablename__ = 'characters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(String(50), ForeignKey('movies.id', ondelete='CASCADE'), index=True)
    name = Column(String(100), nullable=False)
    normalized_name = Column(String(100), index=True)
    character_type = Column(String(20), index=True)  # 角色类型
    actor = Column(String(100))
    
    movie = relationship("Movie", back_populates="characters")
    lines = relationship("Line", back_populates="character")


class Line(Base):
    """
    核心台词表 - 融合方案
    结合四层标签 + 抖音算法字段
    """
    __tablename__ = 'lines'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(String(100), unique=True, index=True)  # {media_id}_ep{N}_line_{idx}
    movie_id = Column(String(50), ForeignKey('movies.id', ondelete='CASCADE'), index=True)
    character_id = Column(Integer, ForeignKey('characters.id', ondelete='SET NULL'), index=True, nullable=True)
    episode_number = Column(Integer, nullable=True)  # NULL表示电影
    line_index = Column(Integer, default=0)  # 在剧集中的行号
    
    # 基础内容
    text = Column(Text, nullable=False)
    clean_text = Column(Text)  # 去标点，用于检索
    vector_text = Column(Text)  # 用于向量化的文本
    start_time = Column(Float, default=0.0)
    end_time = Column(Float, default=0.0)
    duration = Column(Float, default=0.0)  # 秒，抖音算法关键字段
    
    audio_path = Column(String(500))
    audio_hash = Column(String(64), index=True)
    
    # ==================== 四层标签体系（核心） ====================
    
    # 1. 句型层
    sentence_type = Column(String(30), index=True)
    can_follow_types = Column(Text)      # JSON: ["question", "command"]
    can_lead_to_types = Column(Text)     # JSON: ["answer", "refuse"]
    
    # 2. 情绪层
    emotion = Column(String(30), index=True)
    emotion_transition = Column(String(20))  # escalation/contrast/stable
    
    # 3. 语气层
    tone = Column(String(30), index=True)
    
    # 4. 角色层
    character_type = Column(String(30), index=True)
    
    # ==================== 抖音算法优化字段 ====================
    
    intensity = Column(Integer, default=5)        # 1-10，冲突强度
    hook_score = Column(Float, default=0.5)       # 0-1，前3秒吸引力
    ambiguity = Column(Float, default=0.5)        # 0-1，出处模糊度（引发评论）
    completeness = Column(Float, default=1.0)     # 语义完整度
    
    # ==================== 功能与风格标签 ====================
    
    primary_function = Column(String(50))  # 强行解释/身份反转...
    style_effect = Column(String(50))      # 反讽高级黑/自嘲解构...
    editing_rhythm = Column(String(50))    # 快速切梗/慢放打脸/重复鬼畜...
    sound_effects = Column(Text)           # JSON: ["变速处理", "回声效果"]
    
    # 潜台词
    semantic_summary = Column(Text)
    keywords = Column(Text)  # JSON: 关键词提取
    
    # ==================== 向量化状态 ====================
    
    vectorized = Column(Boolean, default=False)
    vector_id = Column(String(100))  # ChromaDB中的ID
    
    # ==================== 使用统计（抖音回传优化） ====================
    
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    avg_completion_rate = Column(Float)  # 历史完播率缓存
    
    annotated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    movie = relationship("Movie", back_populates="lines")
    character = relationship("Character", back_populates="lines")
    canvas_nodes = relationship("CanvasNode", back_populates="line", lazy="dynamic")
    
    # 复合索引
    __table_args__ = (
        Index('idx_line_media_ep', 'movie_id', 'episode_number', 'line_index'),
        Index('idx_connection', 'sentence_type', 'emotion', 'character_type'),
    )
    
    def to_dict(self, include_audio: bool = False) -> Dict:
        """API返回格式"""
        can_follow = []
        can_lead_to = []
        kw = []
        sounds = []
        
        try:
            if self.can_follow_types:
                can_follow = json.loads(self.can_follow_types)
            if self.can_lead_to_types:
                can_lead_to = json.loads(self.can_lead_to_types)
            if self.keywords:
                kw = json.loads(self.keywords)
            if self.sound_effects:
                sounds = json.loads(self.sound_effects)
        except:
            pass
        
        return {
            'id': self.line_id or str(self.id),
            'text': self.text,
            'vector_text': self.vector_text,
            'movie_id': self.movie_id,
            'movie': self.movie.title if self.movie else None,
            'episode_number': self.episode_number,
            'character': self.character.name if self.character else None,
            'character_type': self.character_type,
            
            # 时间信息
            'source': {
                'media_id': self.movie_id,
                'start': self.start_time,
                'end': self.end_time
            },
            
            # 四层标签
            'mashup_tags': {
                'sentence_type': self.sentence_type,
                'emotion': self.emotion,
                'tone': self.tone,
                'character_type': self.character_type,
                'can_follow': can_follow,
                'can_lead_to': can_lead_to,
                'keywords': kw,
                'primary_function': self.primary_function,
                'style_effect': self.style_effect,
            },
            
            # 抖音指标
            'intensity': self.intensity,
            'hook_score': self.hook_score,
            'ambiguity': self.ambiguity,
            'duration': self.duration,
            
            # 剪辑参数
            'editing_params': {
                'rhythm': self.editing_rhythm,
                'duration': self.duration,
            },
            
            'semantic_summary': self.semantic_summary,
            'audio_url': self.audio_path if include_audio else None,
            'vectorized': self.vectorized,
            'annotated_at': self.annotated_at.timestamp() if self.annotated_at else None,
        }
    
    @staticmethod
    def from_annotation_dict(ann: Dict, movie_id: str, episode_number: Optional[int] = None, idx: int = 0) -> 'Line':
        """从标注字典创建 Line 对象"""
        source = ann.get('source', {})
        tags = ann.get('mashup_tags', {})
        editing = ann.get('editing_params', {})
        
        line = Line(
            line_id=ann.get('id', f"{movie_id}_ep{episode_number}_line_{idx}" if episode_number else f"{movie_id}_line_{idx}"),
            movie_id=movie_id,
            episode_number=episode_number,
            line_index=idx,
            text=ann.get('text', ''),
            vector_text=ann.get('vector_text', ann.get('text', '')),
            start_time=source.get('start', 0),
            end_time=source.get('end', 0),
            duration=editing.get('duration', source.get('end', 0) - source.get('start', 0)),
            
            # 四层标签
            sentence_type=tags.get('sentence_type'),
            emotion=tags.get('emotion'),
            tone=tags.get('tone'),
            character_type=tags.get('character_type'),
            can_follow_types=json.dumps(tags.get('can_follow', []), ensure_ascii=False),
            can_lead_to_types=json.dumps(tags.get('can_lead_to', []), ensure_ascii=False),
            keywords=json.dumps(tags.get('keywords', []), ensure_ascii=False),
            
            # 功能风格
            primary_function=tags.get('primary_function'),
            style_effect=tags.get('style_effect'),
            editing_rhythm=editing.get('rhythm'),
            
            semantic_summary=ann.get('semantic_summary', ''),
            annotated_at=datetime.fromtimestamp(ann.get('annotated_at', 0)) if ann.get('annotated_at') else None,
        )
        
        # 自动计算抖音指标
        line.calculate_douyin_scores()
        
        return line
    
    def calculate_douyin_scores(self):
        """基于标签自动计算抖音指标"""
        # intensity映射
        high_intensity_types = ['threat', 'command', 'counter_attack', 'anger']
        mid_intensity_types = ['mock', 'refuse', 'counter_question']
        low_intensity_types = ['surrender', 'fear', 'agree']
        
        if self.sentence_type in high_intensity_types:
            self.intensity = 8
            if self.emotion == 'rage':
                self.intensity = 10
        elif self.sentence_type in mid_intensity_types:
            self.intensity = 6
        elif self.sentence_type in low_intensity_types:
            self.intensity = 3
        else:
            self.intensity = 5
        
        # hook_score映射
        hook_types = ['question', 'threat', 'interrupt', 'reveal']
        if self.sentence_type in hook_types:
            self.hook_score = 0.7 + (0.2 if self.intensity >= 8 else 0)
        else:
            self.hook_score = 0.5 + (self.intensity / 20)
        
        # ambiguity映射
        self.ambiguity = 0.5


# ==================== 接话规则实体化 ====================

class ConnectionRule(Base):
    """
    将 v5 config 中的 connection_rules 实体化
    支持 O(1) 查询接话权重
    """
    __tablename__ = 'connection_rules'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_type = Column(String(20), index=True)  # sentence/emotion/tone
    from_type = Column(String(50), index=True)
    to_type = Column(String(50), index=True)
    weight = Column(Float, default=1.0)
    transition_type = Column(String(20))  # escalation/contrast/continuation
    
    __table_args__ = (
        Index('idx_rule_query', 'rule_type', 'from_type', 'weight'),
    )
    
    @staticmethod
    def init_from_v5_config(session, config_path: str = None):
        """从 v5 config 初始化规则"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'mashup_v5_config.json'
        
        if not Path(config_path).exists():
            print(f"⚠️ 配置文件不存在: {config_path}")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        rules = []
        
        # 1. 导入句型连接规则
        for rule in config.get('connection_rules', {}).get('rules', []):
            for to_type in rule.get('to', []):
                rules.append(ConnectionRule(
                    rule_type='sentence',
                    from_type=rule['from'],
                    to_type=to_type,
                    weight=rule.get('weight', 1.0),
                    transition_type='continuation'
                ))
        
        # 2. 导入情绪递进规则
        for trans_type, pairs in config.get('connection_rules', {}).get('emotion_transitions', {}).items():
            for pair in pairs:
                if len(pair) >= 2:
                    rules.append(ConnectionRule(
                        rule_type='emotion',
                        from_type=pair[0],
                        to_type=pair[1],
                        weight=1.2 if trans_type == 'escalation' else 1.0,
                        transition_type=trans_type
                    ))
        
        if rules:
            session.bulk_save_objects(rules)
            session.commit()
            print(f"✅ 已导入 {len(rules)} 条接话规则")


# ==================== 无限画布实体 ====================

class Project(Base):
    """混剪项目（画布）"""
    __tablename__ = 'projects'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    theme = Column(String(100))  # 主题标签
    style = Column(String(50), default='absurd')  # absurd/emotional/suspense
    
    # 画布视口状态
    viewport_x = Column(Float, default=0.0)
    viewport_y = Column(Float, default=0.0)
    viewport_zoom = Column(Float, default=1.0)
    
    # 元数据
    metadata_json = Column('metadata', Text)  # JSON
    
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    nodes = relationship("CanvasNode", back_populates="project", cascade="all, delete-orphan")
    edges = relationship("CanvasEdge", back_populates="project", cascade="all, delete-orphan")
    sequences = relationship("Sequence", back_populates="project", cascade="all, delete-orphan")
    
    def to_dict(self, include_nodes: bool = False) -> Dict:
        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'theme': self.theme,
            'style': self.style,
            'viewport': {
                'x': self.viewport_x,
                'y': self.viewport_y,
                'zoom': self.viewport_zoom,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'metadata': self.metadata_json,
        }
        
        if include_nodes:
            result['nodes'] = [n.to_dict() for n in self.nodes]
            result['edges'] = [e.to_dict() for e in self.edges]
        
        return result


class CanvasNode(Base):
    """画布上的节点实例"""
    __tablename__ = 'canvas_nodes'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    parent_id = Column(String(36), ForeignKey('canvas_nodes.id', ondelete='CASCADE'), nullable=True)
    line_id = Column(Integer, ForeignKey('lines.id', ondelete='SET NULL'), index=True, nullable=True)
    
    # 节点类型
    node_type = Column(String(20), default='clip')  # root/scene/clip/transition/effect/note
    
    # 节点内容
    title = Column(String(200))
    content = Column(Text)  # 详细内容/备注
    
    # 树形结构
    order = Column(Integer, default=0)
    path = Column(String(500))  # 物化路径
    depth = Column(Integer, default=0)
    
    # 空间坐标（无限画布）
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    width = Column(Float, default=200.0)
    height = Column(Float, default=100.0)
    z_index = Column(Integer, default=0)
    
    # 视觉属性
    color = Column(String(20))
    custom_intensity = Column(Integer)  # 覆盖Line的intensity
    
    # 音频编辑
    trim_start = Column(Float, default=0.0)
    trim_end = Column(Float)
    volume = Column(Float, default=1.0)
    
    # 节点状态
    collapsed = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    project = relationship("Project", back_populates="nodes")
    line = relationship("Line", back_populates="canvas_nodes")
    children = relationship("CanvasNode", backref=backref('parent', remote_side=[id]))
    outgoing_edges = relationship("CanvasEdge", foreign_keys="CanvasEdge.source_id", back_populates="source")
    incoming_edges = relationship("CanvasEdge", foreign_keys="CanvasEdge.target_id", back_populates="target")
    
    __table_args__ = (
        Index('idx_nodes_canvas', 'project_id'),
        Index('idx_nodes_parent', 'parent_id'),
        Index('idx_nodes_path', 'path'),
    )
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'parent_id': self.parent_id,
            'line_id': self.line_id,
            'node_type': self.node_type,
            'title': self.title,
            'content': self.content,
            'order': self.order,
            'depth': self.depth,
            'position': {'x': self.pos_x, 'y': self.pos_y},
            'size': {'width': self.width, 'height': self.height},
            'z_index': self.z_index,
            'color': self.color,
            'trim_start': self.trim_start,
            'trim_end': self.trim_end,
            'volume': self.volume,
            'collapsed': self.collapsed,
            'locked': self.locked,
            # 关联的台词信息
            'line': self.line.to_dict() if self.line else None,
        }


class CanvasEdge(Base):
    """画布连线"""
    __tablename__ = 'canvas_edges'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'))
    
    source_id = Column(String(36), ForeignKey('canvas_nodes.id', ondelete='CASCADE'), index=True)
    target_id = Column(String(36), ForeignKey('canvas_nodes.id', ondelete='CASCADE'), index=True)
    
    # 连接点类型
    source_anchor = Column(String(20), default='output')  # output/contrast/context
    target_anchor = Column(String(20), default='input')   # input/context
    
    # 关系类型（基于接话规则）
    relation_type = Column(String(20))  # continuation/contrast/escalation/callback
    strength = Column(Float, default=0.5)
    shared_tags = Column(Text)  # JSON: 共享的隐喻标签
    
    # 视觉样式
    color = Column(String(20))
    width = Column(Float, default=2.0)
    is_dashed = Column(Boolean, default=False)
    is_animated = Column(Boolean, default=False)
    label = Column(String(100))
    
    # 贝塞尔控制点
    control_point_x = Column(Float)
    control_point_y = Column(Float)
    
    source = relationship("CanvasNode", foreign_keys=[source_id], back_populates="outgoing_edges")
    target = relationship("CanvasNode", foreign_keys=[target_id], back_populates="incoming_edges")
    project = relationship("Project", back_populates="edges")
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'source': self.source_id,
            'target': self.target_id,
            'source_anchor': self.source_anchor,
            'target_anchor': self.target_anchor,
            'relation_type': self.relation_type,
            'strength': self.strength,
            'color': self.color,
            'width': self.width,
            'is_dashed': self.is_dashed,
            'is_animated': self.is_animated,
            'label': self.label,
        }


class Sequence(Base):
    """时间轴序列"""
    __tablename__ = 'sequences'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'))
    name = Column(String(100), default='主序列')
    
    total_duration = Column(Float, default=0.0)
    target_duration = Column(Float, default=20.0)  # 抖音黄金时长
    
    project = relationship("Project", back_populates="sequences")
    items = relationship("SequenceItem", back_populates="sequence", order_by="SequenceItem.order", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'total_duration': self.total_duration,
            'target_duration': self.target_duration,
            'items': [item.to_dict() for item in self.items],
        }


class SequenceItem(Base):
    """时间轴项目"""
    __tablename__ = 'sequence_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_id = Column(Integer, ForeignKey('sequences.id', ondelete='CASCADE'), index=True)
    node_id = Column(String(36), ForeignKey('canvas_nodes.id', ondelete='CASCADE'), index=True)
    
    order = Column(Integer, nullable=False)
    trim_start = Column(Float, default=0.0)
    trim_end = Column(Float)
    volume = Column(Float, default=1.0)
    
    transition_type = Column(String(50), default='cut')  # cut/fade/jitter
    transition_duration = Column(Float, default=0.0)
    
    sequence = relationship("Sequence", back_populates="items")
    node = relationship("CanvasNode")
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'sequence_id': self.sequence_id,
            'node_id': self.node_id,
            'order': self.order,
            'trim_start': self.trim_start,
            'trim_end': self.trim_end,
            'volume': self.volume,
            'transition_type': self.transition_type,
            'transition_duration': self.transition_duration,
        }


# ==================== 辅助标签表 ====================

class LineFunction(Base):
    """混剪功能标签（primary_functions）"""
    __tablename__ = 'line_functions'
    
    name = Column(String(50), primary_key=True)
    description = Column(Text)
    color = Column(String(7), default='#ffffff')


class LineStyle(Base):
    """风格效果标签（style_effects）"""
    __tablename__ = 'line_styles'
    
    name = Column(String(50), primary_key=True)
    description = Column(Text)


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = 'system_config'
    
    key = Column(String(100), primary_key=True)
    value = Column(Text)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== 数据库管理器 ====================

class DatabaseManager:
    """数据库管理器"""
    
    _instance = None
    _engine = None
    _Session = None
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if self._engine is not None:
            return
        
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'data' / 'cinegraph.db'
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._engine = create_engine(
            f'sqlite:///{self.db_path}',
            echo=False,
            connect_args={'check_same_thread': False}
        )
        self._Session = sessionmaker(bind=self._engine)
        
        # 启用外键和WAL模式
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
    
    def init_db(self, v5_config_path: str = None):
        """初始化数据库"""
        Base.metadata.create_all(self._engine)
        
        session = self.get_session()
        try:
            # 检查是否已初始化
            existing = session.query(SystemConfig).filter_by(key='db_version').first()
            if existing:
                print(f"✅ 数据库已存在，版本: {existing.value}")
                return
            
            # 初始化版本号
            session.add(SystemConfig(key='db_version', value='2.0.0', description='融合版数据库'))
            
            # 导入接话规则
            ConnectionRule.init_from_v5_config(session, v5_config_path)
            
            # 导入功能标签
            if v5_config_path is None:
                v5_config_path = Path(__file__).parent.parent.parent.parent / 'config' / 'mashup_v5_config.json'
            
            if Path(v5_config_path).exists():
                with open(v5_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                for func_name in config.get('primary_functions', []):
                    session.add(LineFunction(name=func_name))
                
                for style_name in config.get('style_effects', []):
                    session.add(LineStyle(name=style_name))
                
                session.commit()
                print(f"✅ 标签初始化完成")
            
            print(f"✅ 数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            session.rollback()
            print(f"❌ 数据库初始化失败: {e}")
            raise
        finally:
            session.close()
    
    def get_session(self):
        """获取数据库会话"""
        return self._Session()
    
    @property
    def engine(self):
        return self._engine


def get_db_manager(db_path: str = None) -> DatabaseManager:
    """获取数据库管理器单例"""
    if db_path is None:
        # 尝试从设置模块获取
        try:
            from config.settings import get_settings
            settings = get_settings()
            db_path = settings.database.sqlite_path
        except ImportError:
            pass
    return DatabaseManager(db_path)


def init_database(db_path: str = None, v5_config_path: str = None):
    """初始化数据库的便捷函数"""
    manager = get_db_manager(db_path)
    manager.init_db(v5_config_path)
    return manager
