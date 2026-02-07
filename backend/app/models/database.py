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
    folder_path = Column(String(500))  # 完整文件夹路径
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
    
    # 状态
    status_import = Column(String(20), default='pending')  # pending, done
    status_annotate = Column(String(20), default='pending')  # pending, partial, done
    status_vectorize = Column(String(20), default='pending')  # pending, partial, done
    
    import_batch = Column(String(50), index=True)
    imported_by = Column(String(100))  # 导入者
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
            'folder_path': self.folder_path,
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
            'status_import': self.status_import,
            'status_annotate': self.status_annotate,
            'status_vectorize': self.status_vectorize,
            'import_batch': self.import_batch,
            'imported_by': self.imported_by,
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
    核心台词表 - 基于 cinegraph_database_schema.sql
    支持三层标签体系 + 抖音算法字段
    """
    __tablename__ = 'lines'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(String(100), unique=True, index=True)  # {media_id}_ep{N}_line_{idx}
    movie_id = Column(String(50), ForeignKey('movies.id', ondelete='CASCADE'), index=True)
    episode_number = Column(Integer, nullable=True)  # NULL表示电影
    line_index = Column(Integer, default=0)  # 在剧集中的行号
    
    # 基础内容
    text = Column(Text, nullable=False)
    clean_text = Column(Text)  # 去标点，用于检索
    vector_text = Column(Text)  # 用于向量化的文本
    start_time = Column(Float, default=0.0)
    end_time = Column(Float, default=0.0)
    duration = Column(Float, default=0.0)  # 秒
    character_name = Column(String(100))
    character_id = Column(Integer, ForeignKey('characters.id', ondelete='SET NULL'), index=True, nullable=True)
    
    # ==================== 第一层：基础标签 ====================
    sentence_type = Column(String(30), index=True)
    can_follow = Column(Text)      # JSON: 可接在哪些标签后
    can_lead_to = Column(Text)     # JSON: 后可接哪些标签
    emotion = Column(String(30), index=True)
    emotion_transition = Column(String(20))  # escalation/contrast/stable
    tone = Column(String(30), index=True)
    character_type = Column(String(30), index=True)
    
    # ==================== 第二层：潜台词 ====================
    context_dye = Column(String(50), index=True)  # 语境染色
    context_intensity = Column(Float, default=0.5)
    subtext_type = Column(String(50))  # 隐含语义
    subtext_description = Column(Text)
    is_meme = Column(Boolean, default=False)  # 是否网络梗
    meme_name = Column(String(100))  # 梗名称
    meme_popularity = Column(Integer)  # 梗热度
    social_function = Column(String(50))  # 社交功能
    surface_sentiment = Column(String(30))  # 表面情感
    actual_sentiment = Column(String(30))  # 实际情感
    sentiment_polarity = Column(String(20))  # consistent/ironic/mixed
    
    # ==================== 第三层：隐喻分析 ====================
    metaphor_category = Column(String(50), index=True)  # 隐喻类别
    metaphor_keyword = Column(String(100))  # 关键词
    metaphor_direction = Column(String(50))  # 方向
    metaphor_strength = Column(Float, default=0.5)
    semantic_field = Column(String(50), index=True)  # 语义场
    
    # ==================== 算法字段 ====================
    intensity = Column(Integer, default=5)        # 1-10，冲突强度
    hook_score = Column(Float, default=0.5)       # 0-1，前3秒吸引力
    ambiguity = Column(Float, default=0.5)        # 0-1，出处模糊度
    viral_potential = Column(Float, default=0.5)  # 爆梗潜力
    tags_json = Column(Text)  # 扩展字段 JSON
    
    # ==================== 向量化状态 ====================
    vectorized = Column(Boolean, default=False, index=True)
    vector_id = Column(String(100))  # ChromaDB中的ID
    
    # ==================== 标注信息 ====================
    annotated_by = Column(String(100))
    annotated_at = Column(DateTime)
    annotation_confidence = Column(Float)
    is_signature = Column(Boolean, default=False, index=True)  # 是否标志性台词
    is_catchphrase = Column(Boolean, default=False)  # 是否金句
    signature_score = Column(Float, default=0)
    
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
        can_follow_list = []
        can_lead_to_list = []
        tags = {}
        
        try:
            if self.can_follow:
                can_follow_list = json.loads(self.can_follow)
            if self.can_lead_to:
                can_lead_to_list = json.loads(self.can_lead_to)
            if self.tags_json:
                tags = json.loads(self.tags_json)
        except:
            pass
        
        return {
            'id': self.line_id or str(self.id),
            'text': self.text,
            'vector_text': self.vector_text,
            'movie_id': self.movie_id,
            'movie': self.movie.title if self.movie else None,
            'episode_number': self.episode_number,
            'character': self.character_name or (self.character.name if self.character else None),
            'character_type': self.character_type,
            
            # 时间信息
            'source': {
                'media_id': self.movie_id,
                'start': self.start_time,
                'end': self.end_time
            },
            
            # 三层标签
            'mashup_tags': {
                'sentence_type': self.sentence_type,
                'emotion': self.emotion,
                'tone': self.tone,
                'character_type': self.character_type,
                'can_follow': can_follow_list,
                'can_lead_to': can_lead_to_list,
            },
            
            # 潜台词层
            'subtext': {
                'context_dye': self.context_dye,
                'context_intensity': self.context_intensity,
                'subtext_type': self.subtext_type,
                'is_meme': self.is_meme,
                'meme_name': self.meme_name,
                'social_function': self.social_function,
                'surface_sentiment': self.surface_sentiment,
                'actual_sentiment': self.actual_sentiment,
                'sentiment_polarity': self.sentiment_polarity,
            },
            
            # 隐喻层
            'metaphor': {
                'category': self.metaphor_category,
                'keyword': self.metaphor_keyword,
                'direction': self.metaphor_direction,
                'strength': self.metaphor_strength,
                'semantic_field': self.semantic_field,
            },
            
            # 抖音指标
            'intensity': self.intensity,
            'hook_score': self.hook_score,
            'ambiguity': self.ambiguity,
            'viral_potential': self.viral_potential,
            'duration': self.duration,
            
            # 标注状态
            'is_signature': self.is_signature,
            'is_catchphrase': self.is_catchphrase,
            'signature_score': self.signature_score,
            'vectorized': self.vectorized,
            'annotated_at': self.annotated_at.timestamp() if self.annotated_at else None,
            'tags': tags,
        }
    
    @staticmethod
    def from_annotation_dict(ann: Dict, movie_id: str, episode_number: Optional[int] = None, idx: int = 0) -> 'Line':
        """从标注字典创建 Line 对象"""
        source = ann.get('source', {})
        tags = ann.get('mashup_tags', {})
        subtext = ann.get('subtext', {})
        metaphor = ann.get('metaphor', {})
        
        line = Line(
            line_id=ann.get('id', f"{movie_id}_ep{episode_number}_line_{idx}" if episode_number else f"{movie_id}_line_{idx}"),
            movie_id=movie_id,
            episode_number=episode_number,
            line_index=idx,
            text=ann.get('text', ''),
            vector_text=ann.get('vector_text', ann.get('text', '')),
            start_time=source.get('start', 0),
            end_time=source.get('end', 0),
            duration=ann.get('duration', source.get('end', 0) - source.get('start', 0)),
            character_name=ann.get('character', ''),
            
            # 第一层：基础标签
            sentence_type=tags.get('sentence_type'),
            emotion=tags.get('emotion'),
            tone=tags.get('tone'),
            character_type=tags.get('character_type'),
            can_follow=json.dumps(tags.get('can_follow', []), ensure_ascii=False),
            can_lead_to=json.dumps(tags.get('can_lead_to', []), ensure_ascii=False),
            
            # 第二层：潜台词
            context_dye=subtext.get('context_dye'),
            context_intensity=subtext.get('context_intensity', 0.5),
            subtext_type=subtext.get('subtext_type'),
            subtext_description=subtext.get('description'),
            is_meme=subtext.get('is_meme', False),
            meme_name=subtext.get('meme_name'),
            social_function=subtext.get('social_function'),
            surface_sentiment=subtext.get('surface_sentiment'),
            actual_sentiment=subtext.get('actual_sentiment'),
            sentiment_polarity=subtext.get('sentiment_polarity'),
            
            # 第三层：隐喻
            metaphor_category=metaphor.get('category'),
            metaphor_keyword=metaphor.get('keyword'),
            metaphor_direction=metaphor.get('direction'),
            metaphor_strength=metaphor.get('strength', 0.5),
            semantic_field=metaphor.get('semantic_field'),
            
            # 算法字段
            intensity=ann.get('intensity', 5),
            hook_score=ann.get('hook_score', 0.5),
            ambiguity=ann.get('ambiguity', 0.5),
            viral_potential=ann.get('viral_potential', 0.5),
            
            annotated_at=datetime.fromtimestamp(ann.get('annotated_at', 0)) if ann.get('annotated_at') else None,
        )
        
        # 自动计算抖音指标（如果没有提供）
        if not ann.get('intensity'):
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


class ModelProvider(Base):
    """模型提供者配置表 - 统一管理 LLM 和 Embedding 模型
    
    支持:
    - 本地 Ollama 模型（含云端模型）
    - 商用 API（DeepSeek、阿里云、OpenAI、硅基流动等）
    - 用户自定义添加的任意 OpenAI 兼容 API
    """
    __tablename__ = 'model_providers'
    
    id = Column(String(100), primary_key=True)  # 唯一标识符，如 "ollama_qwen3_4b"
    name = Column(String(200), nullable=False)   # 显示名称
    
    # 模型用途: llm / embedding
    category = Column(String(20), nullable=False, index=True)  # "llm" 或 "embedding"
    
    # 提供者类型: local / commercial
    provider_type = Column(String(20), nullable=False, default='local')
    
    # 本地模式: ollama / docker / 空(商用API)
    local_mode = Column(String(20), default='')
    
    # API 配置
    base_url = Column(String(500), nullable=False)
    model = Column(String(200), nullable=False)   # 模型名称/ID
    api_key = Column(String(500), default='')      # API Key（可为空，或环境变量引用 ${VAR}）
    
    # 模型参数
    max_tokens = Column(Integer, default=2000)
    temperature = Column(Float, default=0.7)
    timeout = Column(Integer, default=60)
    
    # Embedding 专用
    dimension = Column(Integer, default=0)        # 向量维度（0=自动检测）
    api_style = Column(String(20), default='openai')  # openai / ollama
    
    # 元信息
    description = Column(Text, default='')
    price_info = Column(String(200), default='')   # 价格描述，如 "¥1/百万token"
    is_active = Column(Boolean, default=False, index=True)  # 是否为当前激活的提供者
    is_default = Column(Boolean, default=False)    # 是否为系统预置（用户不可删除）
    sort_order = Column(Integer, default=0)        # 排序权重
    enabled = Column(Boolean, default=True)        # 是否启用
    
    # 扩展配置（JSON格式，存储额外参数）
    extra_config = Column(Text, default='{}')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_provider_category_active', 'category', 'is_active'),
    )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        extra = {}
        if self.extra_config:
            try:
                extra = json.loads(self.extra_config)
            except:
                pass
        
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'provider_type': self.provider_type,
            'local_mode': self.local_mode or '',
            'base_url': self.base_url,
            'model': self.model,
            'api_key': self._mask_api_key(),
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'timeout': self.timeout,
            'dimension': self.dimension,
            'api_style': self.api_style or 'openai',
            'description': self.description or '',
            'price_info': self.price_info or '',
            'is_active': self.is_active,
            'is_default': self.is_default,
            'sort_order': self.sort_order,
            'enabled': self.enabled,
            'extra_config': extra,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_provider_config(self) -> Dict:
        """转换为 Provider 可用的配置字典（含完整 API Key）"""
        import os
        api_key = self.api_key or ''
        if api_key.startswith('${') and api_key.endswith('}'):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var, '')
        
        extra = {}
        if self.extra_config:
            try:
                extra = json.loads(self.extra_config)
            except:
                pass
        
        return {
            'name': self.name,
            'type': self.provider_type,
            'local_mode': self.local_mode or '',
            'base_url': self.base_url,
            'model': self.model,
            'api_key': api_key,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'timeout': self.timeout,
            'dimension': self.dimension,
            'api_style': self.api_style or 'openai',
            'description': self.description or '',
            **extra,
        }
    
    def _mask_api_key(self) -> str:
        """隐藏 API Key"""
        if not self.api_key:
            return ''
        if self.api_key.startswith('${'):
            return self.api_key  # 环境变量引用直接返回
        if len(self.api_key) > 8:
            return self.api_key[:4] + '****' + self.api_key[-4:]
        return '****'


# ==================== 增强标签体系表 ====================

class TagHierarchy(Base):
    """标签层级关系表 - 父子/关联标签"""
    __tablename__ = 'tag_hierarchy'
    
    parent_tag_id = Column(String(100), primary_key=True)
    child_tag_id = Column(String(100), primary_key=True)
    relation_type = Column(String(20), default='is_a')  # is_a / part_of / related_to
    weight = Column(Float, default=1.0)
    
    def to_dict(self) -> Dict:
        return {
            'parent_tag_id': self.parent_tag_id,
            'child_tag_id': self.child_tag_id,
            'relation_type': self.relation_type,
            'weight': self.weight,
        }


class TagConstraint(Base):
    """标签约束规则表 - 互斥/依赖/共现"""
    __tablename__ = 'tag_constraints'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(String(100), nullable=False, index=True)
    constraint_type = Column(String(30), nullable=False)  # mutual_exclusive / requires / excludes / co_occurs
    tag_ids = Column(Text, nullable=False)  # JSON 数组
    constraint_message = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        tag_ids_list = []
        if self.tag_ids:
            try:
                tag_ids_list = json.loads(self.tag_ids)
            except:
                pass
        return {
            'id': self.id,
            'category_id': self.category_id,
            'constraint_type': self.constraint_type,
            'tag_ids': tag_ids_list,
            'constraint_message': self.constraint_message,
            'is_active': self.is_active,
        }


class TagLocalization(Base):
    """标签本地化/多语言表"""
    __tablename__ = 'tag_localization'
    
    tag_id = Column(String(100), primary_key=True)
    language_code = Column(String(10), primary_key=True)  # zh-CN / en-US / ja-JP
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    cultural_note = Column(Text)  # 文化差异说明
    
    def to_dict(self) -> Dict:
        return {
            'tag_id': self.tag_id,
            'language_code': self.language_code,
            'display_name': self.display_name,
            'description': self.description,
            'cultural_note': self.cultural_note,
        }


class CultureSpecificTag(Base):
    """文化特定标签表"""
    __tablename__ = 'culture_specific_tags'
    
    id = Column(String(100), primary_key=True)
    tag_id = Column(String(100), nullable=False, index=True)
    culture_code = Column(String(10), nullable=False, index=True)  # zh-CN / en-US / ja-JP
    specific_meaning = Column(Text)
    example_lines = Column(Text)  # JSON: 示例台词
    
    def to_dict(self) -> Dict:
        examples = []
        if self.example_lines:
            try:
                examples = json.loads(self.example_lines)
            except:
                pass
        return {
            'id': self.id,
            'tag_id': self.tag_id,
            'culture_code': self.culture_code,
            'specific_meaning': self.specific_meaning,
            'example_lines': examples,
        }


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
            # 数据库位于 backend/data 文件夹
            # backend/app/models/database.py -> backend/data/cinegraph.db
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
                # 确保新表也被创建（增量迁移）
                Base.metadata.create_all(self._engine)
                # 确保模型提供者表有数据
                provider_count = session.query(ModelProvider).count()
                if provider_count == 0:
                    self._init_default_model_providers(session)
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
            
            # 初始化默认模型提供者
            self._init_default_model_providers(session)
            
            print(f"✅ 数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            session.rollback()
            print(f"❌ 数据库初始化失败: {e}")
            raise
        finally:
            session.close()
    
    def _init_default_model_providers(self, session):
        """初始化默认的模型提供者配置"""
        default_providers = [
            # ==================== LLM 提供者 ====================
            # --- 本地 Ollama ---
            ModelProvider(
                id='ollama_qwen3_4b', name='Qwen3:4B (本地Ollama)',
                category='llm', provider_type='local', local_mode='ollama',
                base_url='http://localhost:11434/v1', model='qwen3:4b',
                max_tokens=2000, temperature=0.7, timeout=120,
                description='通过Ollama运行的本地Qwen3 4B模型，免费使用',
                price_info='免费', is_active=True, is_default=True, sort_order=10,
            ),
            ModelProvider(
                id='ollama_qwen3_8b', name='Qwen3:8B (本地Ollama)',
                category='llm', provider_type='local', local_mode='ollama',
                base_url='http://localhost:11434/v1', model='qwen3:8b',
                max_tokens=4000, temperature=0.7, timeout=180,
                description='本地Qwen3 8B，标注质量更好但速度稍慢',
                price_info='免费', is_default=True, sort_order=11,
            ),
            # --- Ollama 云模型 ---
            ModelProvider(
                id='ollama_cloud_qwen3_235b', name='Qwen3-VL:235B (Ollama云)',
                category='llm', provider_type='local', local_mode='ollama',
                base_url='http://localhost:11434/v1', model='qwen3-vl:235b-cloud',
                max_tokens=4000, temperature=0.7, timeout=120,
                description='Ollama云端Qwen3 VL 235B，免费但有配额限制',
                price_info='免费(有配额)', is_default=True, sort_order=20,
            ),
            ModelProvider(
                id='ollama_cloud_deepseek_v3', name='DeepSeek-V3.1:671B (Ollama云)',
                category='llm', provider_type='local', local_mode='ollama',
                base_url='http://localhost:11434/v1', model='deepseek-v3.1:671b-cloud',
                max_tokens=4000, temperature=0.7, timeout=120,
                description='Ollama云端DeepSeek V3.1，免费但有配额限制',
                price_info='免费(有配额)', is_default=True, sort_order=21,
            ),
            ModelProvider(
                id='ollama_cloud_qwen3_coder', name='Qwen3-Coder:480B (Ollama云)',
                category='llm', provider_type='local', local_mode='ollama',
                base_url='http://localhost:11434/v1', model='qwen3-coder:480b-cloud',
                max_tokens=4000, temperature=0.7, timeout=120,
                description='Ollama云端Qwen3 Coder 480B',
                price_info='免费(有配额)', is_default=True, sort_order=22,
            ),
            # --- 商用 API ---
            ModelProvider(
                id='deepseek_chat', name='DeepSeek V3',
                category='llm', provider_type='commercial', local_mode='',
                base_url='https://api.deepseek.com/v1', model='deepseek-chat',
                api_key='${DEEPSEEK_API_KEY}',
                max_tokens=4000, temperature=0.7, timeout=30,
                description='DeepSeek V3，中文效果极佳，性价比最高的商用模型',
                price_info='¥1/百万token(输入) ¥2/百万token(输出)',
                is_default=True, sort_order=30,
            ),
            ModelProvider(
                id='aliyun_qwen_turbo', name='通义千问Turbo',
                category='llm', provider_type='commercial', local_mode='',
                base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
                model='qwen-turbo-latest', api_key='${DASHSCOPE_API_KEY}',
                max_tokens=4000, temperature=0.7, timeout=30,
                description='阿里云通义千问Turbo，速度快价格低',
                price_info='¥0.3/百万token(输入) ¥0.6/百万token(输出)',
                is_default=True, sort_order=31,
            ),
            ModelProvider(
                id='aliyun_qwen_max', name='通义千问Max',
                category='llm', provider_type='commercial', local_mode='',
                base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
                model='qwen-max', api_key='${DASHSCOPE_API_KEY}',
                max_tokens=4000, temperature=0.7, timeout=60,
                description='阿里云通义千问Max，效果最好',
                price_info='¥2/百万token(输入) ¥6/百万token(输出)',
                is_default=True, sort_order=32,
            ),
            ModelProvider(
                id='siliconflow_qwen3_8b', name='Qwen3-8B (硅基流动)',
                category='llm', provider_type='commercial', local_mode='',
                base_url='https://api.siliconflow.cn/v1',
                model='Qwen/Qwen3-8B', api_key='${SILICONFLOW_API_KEY}',
                max_tokens=4000, temperature=0.7, timeout=30,
                description='硅基流动免费Qwen3-8B，注册送额度',
                price_info='免费(有额度)',
                is_default=True, sort_order=33,
            ),
            ModelProvider(
                id='openai_gpt4o_mini', name='GPT-4o-mini',
                category='llm', provider_type='commercial', local_mode='',
                base_url='https://api.openai.com/v1', model='gpt-4o-mini',
                api_key='${OPENAI_API_KEY}',
                max_tokens=4000, temperature=0.7, timeout=30,
                description='OpenAI GPT-4o-mini，性价比之选',
                price_info='$0.15/百万token(输入) $0.6/百万token(输出)',
                is_default=True, sort_order=40,
            ),
            ModelProvider(
                id='zhipu_glm4', name='智谱GLM-4',
                category='llm', provider_type='commercial', local_mode='',
                base_url='https://open.bigmodel.cn/api/paas/v4',
                model='glm-4', api_key='${ZHIPU_API_KEY}',
                max_tokens=4000, temperature=0.7, timeout=30,
                description='智谱GLM-4，国产大模型',
                price_info='¥0.1/千token',
                is_default=True, sort_order=41,
            ),
            ModelProvider(
                id='volcengine_doubao', name='豆包1.5 Pro',
                category='llm', provider_type='commercial', local_mode='',
                base_url='https://ark.cn-beijing.volces.com/api/v3',
                model='doubao-1-5-pro-32k', api_key='${VOLCENGINE_API_KEY}',
                max_tokens=4000, temperature=0.7, timeout=30,
                description='火山引擎豆包1.5 Pro',
                price_info='¥0.8/百万token(输入) ¥2/百万token(输出)',
                is_default=True, sort_order=42,
            ),
            
            # ==================== Embedding 提供者 ====================
            # --- 本地 Ollama ---
            ModelProvider(
                id='ollama_qwen3_embedding', name='Qwen3-Embedding:4B (本地Ollama)',
                category='embedding', provider_type='local', local_mode='ollama',
                base_url='http://localhost:11434', model='qwen3-embedding:4b-fp16',
                timeout=60, api_style='ollama',
                description='通过Ollama运行的本地Embedding模型',
                price_info='免费', is_active=True, is_default=True, sort_order=10,
            ),
            # --- 商用 API ---
            ModelProvider(
                id='siliconflow_bge_m3', name='BGE-M3 (硅基流动)',
                category='embedding', provider_type='commercial', local_mode='',
                base_url='https://api.siliconflow.cn/v1',
                model='BAAI/bge-m3', api_key='${SILICONFLOW_API_KEY}',
                dimension=1024, timeout=30, api_style='openai',
                description='硅基流动免费BGE-M3，中文效果极佳',
                price_info='免费',
                is_default=True, sort_order=20,
            ),
            ModelProvider(
                id='aliyun_embedding_v3', name='text-embedding-v3 (阿里云)',
                category='embedding', provider_type='commercial', local_mode='',
                base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
                model='text-embedding-v3', api_key='${DASHSCOPE_API_KEY}',
                dimension=1024, timeout=30, api_style='openai',
                description='阿里云通用文本Embedding V3',
                price_info='¥0.0007/千token',
                is_default=True, sort_order=21,
            ),
            ModelProvider(
                id='openai_embedding_small', name='text-embedding-3-small (OpenAI)',
                category='embedding', provider_type='commercial', local_mode='',
                base_url='https://api.openai.com/v1',
                model='text-embedding-3-small', api_key='${OPENAI_API_KEY}',
                dimension=1536, timeout=30, api_style='openai',
                description='OpenAI Embedding Small',
                price_info='$0.02/百万token',
                is_default=True, sort_order=30,
            ),
            ModelProvider(
                id='volcengine_embedding', name='Doubao-Embedding (火山引擎)',
                category='embedding', provider_type='commercial', local_mode='',
                base_url='https://ark.cn-beijing.volces.com/api/v3',
                model='doubao-embedding', api_key='${VOLCENGINE_API_KEY}',
                dimension=2048, timeout=30, api_style='openai',
                description='火山引擎豆包Embedding',
                price_info='¥0.0005/千token',
                is_default=True, sort_order=31,
            ),
        ]
        
        try:
            for provider in default_providers:
                existing = session.query(ModelProvider).filter_by(id=provider.id).first()
                if not existing:
                    session.add(provider)
            
            session.commit()
            print(f"✅ 默认模型提供者初始化完成 ({len(default_providers)} 个)")
            
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
