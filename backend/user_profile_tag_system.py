"""
用户人格画像标签系统 (User Personality Profile Tag System) v2.0

整合情绪、习惯、性格、行为模式的多维标签系统
基于 Formation Engine 8维性格轨迹 + 扩展标签体系

核心功能：
1. 标签提取 - 从所有用户输入中自动提取标签
2. 标签存储 - 权重计算、时间衰减、置信度管理
3. 人格画像 - 基于标签和FormationStateVector生成唯一画像
4. 画像演化 - 追踪用户人格轨迹变化
"""

import json
import math
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import uuid


# ==================== 枚举定义 ====================

class TagSource(Enum):
    """标签来源类型"""
    EMOTION_CHECKIN = "emotion_checkin"      # 情绪打卡
    DECISION_EVENT = "decision_event"        # 决策事件
    HABIT_EXECUTION = "habit_execution"      # 习惯执行
    JOURNAL_ENTRY = "journal_entry"          # 日记/灵修
    CHAT_INTERACTION = "chat_interaction"    # 对话交互
    PRAYER_REQUEST = "prayer_request"        # 祷告请求
    FORMATION_ANALYSIS = "formation"         # Formation Engine分析
    BEHAVIOR_REGULATION = "behavior"         # 行为调节
    MANUAL = "manual"                        # 用户手动添加
    SYSTEM_INFERRED = "system"               # 系统推断
    TEST_ASSESSMENT = "assessment"             # 测评问卷


class TagCategory(Enum):
    """标签分类 - 8大维度"""
    # 1. 情绪维度
    EMOTION_TYPE = "emotion_type"            # 情绪类型（焦虑、喜悦等）
    EMOTION_PATTERN = "emotion_pattern"      # 情绪模式（波动型、稳定型等）
    
    # 2. 习惯维度
    HABIT_TYPE = "habit_type"                # 习惯类型（健康、灵修等）
    HABIT_CONSISTENCY = "habit_consistency"  # 习惯坚持度
    ROUTINE_PREFERENCE = "routine"           # 作息偏好
    
    # 3. 性格维度 - 对应FormationStateVector
    CHARACTER_TRAIT = "character_trait"      # 性格特质
    FORMATION_DIMENSION = "formation_dim"    # 8维性格指标
    
    # 4. 行为模式
    BEHAVIOR_PATTERN = "behavior"            # 行为模式（逃避、完美主义等）
    RESPONSE_STYLE = "response_style"        # 应对风格
    STRESS_REACTION = "stress_reaction"      # 压力反应
    
    # 5. 生活领域
    LIFE_DOMAIN = "life_domain"              # 生活领域（工作、关系、健康等）
    LIFE_STAGE = "life_stage"                # 人生阶段
    
    # 6. 价值观与动机
    VALUE_PRIORITY = "value"                 # 价值观/优先级
    MOTIVE_TYPE = "motive"                   # 动机类型（恐惧、爱、骄傲等）
    
    # 7. 关系与社交
    RELATIONSHIP_TYPE = "relationship"       # 关系类型
    ATTACHMENT_STYLE = "attachment"          # 依恋风格
    SOCIAL_PREFERENCE = "social"               # 社交偏好
    
    # 8. 认知与灵性
    COGNITIVE_STYLE = "cognitive"            # 认知风格
    SPIRITUAL_STATE = "spiritual"            # 灵性状态
    DECISION_STYLE = "decision"              # 决策风格


class PersonalityArchetype(Enum):
    """人格原型 - 基于标签聚类的人格类型"""
    SEEKER = "seeker"                        # 探索者 - 好奇、开放、寻求意义
    STEWARD = "steward"                      # 管家 - 负责、可靠、照顾他人
    WARRIOR = "warrior"                      # 战士 - 勇敢、坚韧、对抗困难
    ARTIST = "artist"                        # 艺术家 - 敏感、创造、情感丰富
    THINKER = "thinker"                      # 思考者 - 理性、分析、追求真理
    CAREGIVER = "caregiver"                  # 照顾者 - 同理心、滋养、支持
    LEADER = "leader"                        # 领袖 - 果断、影响、承担责任
    CONTEMPLATIVE = "contemplative"          # 默观者 - 内省、安静、深度思考
    ACTIVIST = "activist"                    # 行动者 - 热情、驱动、追求改变
    DIPLOMAT = "diplomat"                    # 外交家 - 和谐、调解、避免冲突


class FormationDimension(Enum):
    """8维性格轨迹指标 - 对应FormationStateVector"""
    HUMILITY = "humility"                    # 谦逊度
    FEAR_TENDENCY = "fear_tendency"          # 恐惧倾向
    PRIDE_TENDENCY = "pride_tendency"        # 骄傲倾向
    EMOTIONAL_STABILITY = "emotional_stability"  # 情绪稳定性
    TRUTH_ALIGNMENT = "truth_alignment"      # 真理对齐
    RELATIONAL_HEALTH = "relational_health"  # 关系健康
    RESILIENCE = "resilience"                # 韧性
    SPIRITUAL_CLARITY = "spiritual_clarity"  # 灵性清晰


class DominantLoop(Enum):
    """5种主导循环模式"""
    FEAR_CONTROL = "fear_control_loop"      # 恐惧-控制循环
    SHAME_AVOIDANCE = "shame_avoidance_loop"  # 羞耻-逃避循环
    PRIDE_COMPARISON = "pride_comparison_loop"  # 骄傲-比较循环
    DESIRE_IMPULSE = "desire_impulse_loop"    # 欲望-冲动循环
    TRUTH_STABILITY = "truth_stability_loop"  # 真理-稳定循环（健康）


class TrajectoryDirection(Enum):
    """轨迹方向"""
    STABILIZING = "stabilizing"
    FRAGMENTING = "fragmenting"
    IMPROVING_CLARITY = "improving_clarity"
    INCREASING_VOLATILITY = "increasing_volatility"
    CYCLICAL = "cyclical"
    UNKNOWN = "unknown"


# ==================== 数据模型 ====================

@dataclass
class UserTag:
    """用户标签数据模型"""
    id: str
    user_id: str
    tag_name: str
    tag_category: str
    tag_subcategory: Optional[str] = None
    source: str = "system"
    confidence: float = 0.5              # 置信度 0-1
    weight: float = 1.0                  # 权重，随时间衰减 0-10
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    last_seen_at: datetime = field(default_factory=datetime.utcnow)
    occurrence_count: int = 1              # 出现次数
    
    # 上下文信息
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    related_emotions: List[str] = field(default_factory=list)
    related_decisions: List[str] = field(default_factory=list)
    related_habits: List[str] = field(default_factory=list)
    source_events: List[str] = field(default_factory=list)  # 来源事件ID
    
    # 时间序列数据
    history_weights: List[Tuple[datetime, float]] = field(default_factory=list)
    
    is_active: bool = True
    is_manually_added: bool = False
    is_system_core: bool = False         # 是否为核心标签（不易删除）
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # 转换datetime为ISO格式
        result['first_seen_at'] = self.first_seen_at.isoformat() if self.first_seen_at else None
        result['last_seen_at'] = self.last_seen_at.isoformat() if self.last_seen_at else None
        result['history_weights'] = [
            [t.isoformat(), w] for t, w in self.history_weights
        ]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserTag':
        """从字典创建标签实例"""
        if 'first_seen_at' in data and isinstance(data['first_seen_at'], str):
            data['first_seen_at'] = datetime.fromisoformat(data['first_seen_at'])
        if 'last_seen_at' in data and isinstance(data['last_seen_at'], str):
            data['last_seen_at'] = datetime.fromisoformat(data['last_seen_at'])
        if 'history_weights' in data:
            data['history_weights'] = [
                (datetime.fromisoformat(t), w) for t, w in data['history_weights']
            ]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FormationStateVector:
    """8维性格轨迹状态向量"""
    humility: float = 0.5
    fear_tendency: float = 0.5
    pride_tendency: float = 0.5
    emotional_stability: float = 0.5
    truth_alignment: float = 0.5
    relational_health: float = 0.5
    resilience: float = 0.5
    spiritual_clarity: float = 0.5
    
    # 元数据
    computed_at: datetime = field(default_factory=datetime.utcnow)
    data_points: int = 0
    confidence: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'humility': round(self.humility, 3),
            'fear_tendency': round(self.fear_tendency, 3),
            'pride_tendency': round(self.pride_tendency, 3),
            'emotional_stability': round(self.emotional_stability, 3),
            'truth_alignment': round(self.truth_alignment, 3),
            'relational_health': round(self.relational_health, 3),
            'resilience': round(self.resilience, 3),
            'spiritual_clarity': round(self.spiritual_clarity, 3),
            'computed_at': self.computed_at.isoformat() if self.computed_at else None,
            'data_points': self.data_points,
            'confidence': round(self.confidence, 3),
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormationStateVector':
        vector = cls()
        for dim in FormationDimension:
            if dim.value in data:
                setattr(vector, dim.value, data[dim.value])
        if 'computed_at' in data:
            vector.computed_at = datetime.fromisoformat(data['computed_at']) if isinstance(data['computed_at'], str) else data['computed_at']
        vector.data_points = data.get('data_points', 0)
        vector.confidence = data.get('confidence', 0.5)
        return vector


@dataclass
class PersonalityProfile:
    """用户人格画像"""
    user_id: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    # 核心画像数据
    formation_vector: FormationStateVector = field(default_factory=FormationStateVector)
    dominant_loop: Optional[str] = None
    trajectory_direction: Optional[str] = None
    personality_archetype: Optional[str] = None
    
    # 标签聚合
    top_emotion_tags: List[Dict] = field(default_factory=list)
    top_behavior_tags: List[Dict] = field(default_factory=list)
    top_value_tags: List[Dict] = field(default_factory=list)
    top_relationship_tags: List[Dict] = field(default_factory=list)
    life_dominant_domains: List[str] = field(default_factory=list)
    
    # 模式识别
    recurring_patterns: List[Dict] = field(default_factory=list)
    growth_indicators: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # 时间维度
    profile_stability: float = 0.5       # 画像稳定性 0-1
    change_velocity: float = 0.0         # 变化速度
    trend_direction: str = "stable"        # stable|improving|declining|volatile
    
    # 叙事描述
    profile_summary: str = ""
    core_narrative: str = ""              # 核心生命叙事
    growth_pathway: str = ""              # 成长路径建议
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'formation_vector': self.formation_vector.to_dict(),
            'dominant_loop': self.dominant_loop,
            'trajectory_direction': self.trajectory_direction,
            'personality_archetype': self.personality_archetype,
            'top_emotion_tags': self.top_emotion_tags,
            'top_behavior_tags': self.top_behavior_tags,
            'top_value_tags': self.top_value_tags,
            'top_relationship_tags': self.top_relationship_tags,
            'life_dominant_domains': self.life_dominant_domains,
            'recurring_patterns': self.recurring_patterns,
            'growth_indicators': self.growth_indicators,
            'risk_factors': self.risk_factors,
            'profile_stability': round(self.profile_stability, 3),
            'change_velocity': round(self.change_velocity, 3),
            'trend_direction': self.trend_direction,
            'profile_summary': self.profile_summary,
            'core_narrative': self.core_narrative,
            'growth_pathway': self.growth_pathway,
        }


@dataclass
class TagExtractionResult:
    """标签提取结果"""
    tags: List[Dict[str, Any]] = field(default_factory=list)
    source_type: str = ""
    source_id: Optional[str] = None
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0
    
    def merge(self, other: 'TagExtractionResult') -> 'TagExtractionResult':
        """合并两个提取结果"""
        merged = TagExtractionResult(
            tags=self.tags + other.tags,
            source_type=f"{self.source_type},{other.source_type}",
            extracted_at=datetime.utcnow(),
            confidence=(self.confidence + other.confidence) / 2
        )
        return merged


# ==================== 标签提取引擎 ====================

class TagExtractor:
    """
    标签提取引擎 - 从各种用户输入中自动提取标签
    支持多语言（中英文）、多来源、上下文感知
    """
    
    # 扩展标签词典 - 中英文对照
    TAG_PATTERNS = {
        # 1. 情绪类型标签
        TagCategory.EMOTION_TYPE: {
            '焦虑型': ['焦虑', '紧张', '担忧', '不安', 'stress', 'anxiety', 'worried', 'anxious'],
            '抑郁型': ['抑郁', '悲伤', '沮丧', '低落', 'depressed', 'sad', 'down', 'depression'],
            '愤怒型': ['愤怒', '生气', '恼火', '暴躁', 'angry', 'mad', 'frustrated', 'rage'],
            '恐惧型': ['恐惧', '害怕', '恐慌', 'fear', 'afraid', 'scared', 'panic', 'terrified'],
            '喜悦型': ['喜悦', '开心', '高兴', '快乐', 'joy', 'happy', 'glad', 'delighted', 'joyful'],
            '平静型': ['平静', '安宁', 'peace', 'calm', 'peaceful', 'tranquil', 'serene'],
            '孤独型': ['孤独', '寂寞', 'lonely', 'alone', 'isolated', 'solitary'],
            '羞愧型': ['羞愧', '羞耻', 'shame', 'ashamed', 'embarrassed', 'humiliated'],
            '内疚型': ['内疚', '自责', 'guilt', 'guilty', 'remorse', 'regretful'],
            '感恩型': ['感恩', '感谢', '感激', 'gratitude', 'thankful', 'grateful', 'appreciative'],
            '盼望型': ['盼望', '希望', '期待', 'hope', 'hopeful', 'expecting', 'optimistic'],
            '迷茫型': ['迷茫', '困惑', 'confused', 'confusion', 'uncertain', 'lost', 'puzzled'],
            '兴奋型': ['兴奋', '激动', 'enthusiastic', 'excited', 'thrilled', 'elated'],
            '疲惫型': ['疲惫', '累', 'tired', 'exhausted', 'fatigued', 'weary', 'drained'],
            '满足型': ['满足', '满意', 'content', 'satisfied', 'fulfilled', 'contented'],
        },
        
        # 2. 情绪模式标签
        TagCategory.EMOTION_PATTERN: {
            '情绪波动型': ['情绪起伏', '忽高忽低', 'mood swings', 'emotional roller coaster'],
            '情绪压抑型': ['压抑', '憋', 'bottled up', 'suppressed', 'repressed'],
            '情绪外放型': ['外放', '表达', 'expressive', 'emotional outburst'],
            '情绪敏感型': ['敏感', '容易受伤', 'sensitive', 'thin-skinned', 'hypersensitive'],
            '情绪稳定型': ['稳定', '平和', 'stable', 'even-tempered', 'steady'],
            '情绪回避型': ['回避情绪', '不想感受', 'avoid emotions', 'numb', 'detached'],
        },
        
        # 3. 习惯类型标签
        TagCategory.HABIT_TYPE: {
            '灵修习惯': ['灵修', '读经', '祷告', '敬拜', 'devotion', 'bible reading', 'prayer'],
            '健康习惯': ['运动', '健身', '饮食', '睡眠', 'exercise', 'workout', 'healthy eating'],
            '学习习惯': ['阅读', '学习', '写作', 'study', 'reading', 'writing', 'learning'],
            '社交习惯': ['社交', '聚会', '联络', 'social', 'meet friends', 'networking'],
            '工作习惯': ['工作', '专注', '效率', 'work', 'focus', 'productivity'],
            '休息习惯': ['休息', '放松', '娱乐', 'rest', 'relax', 'recreation'],
            '服务习惯': ['服事', '帮助', '志愿', 'service', 'volunteer', 'help others'],
        },
        
        # 4. 习惯坚持度
        TagCategory.HABIT_CONSISTENCY: {
            '高度自律': ['坚持', '每天', '从不间断', 'consistent', 'disciplined', 'committed'],
            '间歇性努力': ['偶尔', '有时候', '三天打鱼', 'on and off', 'sporadic', 'inconsistent'],
            '启动困难': ['开始难', '拖延', '启动', 'hard to start', 'procrastinate', 'initiation'],
            '容易放弃': ['放弃', '中断', '坚持不下去', 'give up', 'quit', 'abandon'],
            '完美主义停滞': ['等准备好', '完美主义', 'paralysis', 'perfectionism', 'all or nothing'],
        },
        
        # 5. 作息偏好
        TagCategory.ROUTINE_PREFERENCE: {
            '早起型': ['早起', '晨型', 'morning person', 'early bird', 'wake up early'],
            '夜猫子': ['晚睡', '夜猫', 'night owl', 'stay up late', 'evening person'],
            '规律作息': ['规律', '按时', 'consistent schedule', 'regular routine'],
            '紊乱作息': ['紊乱', '不规律', '熬夜', 'irregular', 'chaotic schedule'],
        },
        
        # 6. 性格特质标签 - 对应8维
        TagCategory.CHARACTER_TRAIT: {
            '谦逊型': ['谦逊', '低调', 'humility', 'humble', 'modest'],
            '自信型': ['自信', '肯定自己', 'confident', 'self-assured', 'self-confidence'],
            '谨慎型': ['谨慎', '小心', 'cautious', 'careful', 'prudent'],
            '冒险型': ['冒险', '大胆', 'risk-taking', 'adventurous', 'bold'],
            '坚韧型': ['坚韧', '不屈', 'resilient', 'perseverant', 'tenacious'],
            '脆弱型': ['脆弱', '易受伤', 'vulnerable', 'fragile', 'delicate'],
            '真诚型': ['真诚', '真实', 'authentic', 'genuine', 'sincere'],
            '防御型': ['防御', '保护自己', 'defensive', 'guarded', 'protective'],
        },
        
        # 7. 行为模式
        TagCategory.BEHAVIOR_PATTERN: {
            '逃避型': ['逃避', '躲', '回避', 'avoid', 'avoidance', 'escape', 'run away'],
            '完美主义': ['完美', '挑剔', '苛刻', 'perfect', 'perfectionist', 'exacting'],
            '拖延型': ['拖延', '推迟', 'procrastinate', 'delay', 'put off', 'procrastination'],
            '冲动型': ['冲动', '鲁莽', 'impulsive', 'rash', 'impulse', 'spontaneous'],
            '控制型': ['控制', '掌控', 'control', 'dominant', 'controlling', 'micromanage'],
            '讨好型': ['讨好', '取悦', '迎合', 'please', 'people-pleaser', 'appease'],
            '自我批评型': ['自我批评', '自责', 'self-criticism', 'self-blame', 'self-critical'],
            '过度思考型': ['想太多', '反复思考', 'overthink', 'ruminate', 'over analyze'],
            '寻求认可型': ['认可', '肯定', 'approval', 'validation', 'seeking', 'external validation'],
            '边界模糊型': ['边界', '界限', 'boundary', 'blurred', 'unclear', 'poor boundaries'],
            '竞争型': ['竞争', '比较', 'compete', 'comparison', 'competitive', 'rivalry'],
            '合作型': ['合作', '配合', 'cooperate', 'collaborative', 'team player'],
            '独立型': ['独立', '自主', 'independent', 'self-reliant', 'autonomous'],
            '依赖型': ['依赖', '依靠', 'dependent', 'reliant', 'needy'],
        },
        
        # 8. 应对风格
        TagCategory.RESPONSE_STYLE: {
            '问题解决型': ['解决问题', '想办法', 'problem-solver', 'solution-focused', 'fix it'],
            '情绪导向型': ['先处理情绪', '感受优先', 'emotion-focused', 'process feelings'],
            '寻求支持型': ['找人倾诉', '寻求帮助', 'seek support', 'reach out', 'ask for help'],
            '独自承担型': ['自己扛', '不麻烦人', 'handle alone', 'self-sufficient', 'lone wolf'],
            '反思型': ['反思', '思考', 'reflective', 'contemplative', 'introspective'],
            '行动型': ['立即行动', '先做了再说', 'action-oriented', 'doer', 'proactive'],
            '等待型': ['等待', '观望', 'wait', 'see what happens', 'wait and see'],
        },
        
        # 9. 压力反应
        TagCategory.STRESS_REACTION: {
            '压力下焦虑': ['压力焦虑', 'stress anxiety', 'anxious under pressure'],
            '压力下愤怒': ['压力愤怒', 'irritable', 'angry under stress', 'pressure anger'],
            '压力下退缩': ['压力退缩', 'withdraw', 'shut down', 'retreat under stress'],
            '压力下奋进': ['压力奋进', 'rise to challenge', 'thrive under pressure'],
            '压力下求助': ['压力求助', 'ask help under stress', 'reach out when stressed'],
        },
        
        # 10. 生活领域
        TagCategory.LIFE_DOMAIN: {
            '工作领域': ['工作', '职场', '事业', 'job', 'work', 'career', 'profession', 'occupation'],
            '家庭领域': ['家庭', '家人', '夫妻', '亲子', 'family', 'home', 'household', 'domestic'],
            '关系领域': ['关系', '友谊', '社交', 'relationship', 'friendship', 'social', 'connections'],
            '健康领域': ['健康', '身体', '生病', 'health', 'wellness', 'physical', 'fitness'],
            '财务领域': ['财务', '金钱', '经济', 'financial', 'money', 'economy', 'finance'],
            '信仰领域': ['信仰', '灵修', '神', 'faith', 'spiritual', 'prayer', 'god', 'religion'],
            '学习领域': ['学习', '考试', '学业', 'study', 'education', 'school', 'academic'],
            '娱乐领域': ['娱乐', '休息', '爱好', 'entertainment', 'hobby', 'recreation', 'leisure'],
        },
        
        # 11. 人生阶段
        TagCategory.LIFE_STAGE: {
            '探索期': ['探索', '寻找', 'exploring', 'searching', 'finding oneself'],
            '建立期': ['建立', '创业', 'establishing', 'building', 'setting up'],
            '稳定期': ['稳定', '安逸', 'stable', 'settled', 'secure'],
            '转型期': ['转型', '改变', 'transition', 'changing', 'shifting'],
            '危机期': ['危机', '困难', 'crisis', 'difficult time', 'struggling'],
            '恢复期': ['恢复', '重建', 'recovering', 'rebuilding', 'healing'],
        },
        
        # 12. 价值观
        TagCategory.VALUE_PRIORITY: {
            '安全感导向': ['安全', '稳定', 'security', 'safety', 'stability', 'certainty'],
            '自由导向': ['自由', '自主', 'freedom', 'autonomy', 'liberty', 'independence'],
            '成就导向': ['成就', '成功', 'achievement', 'success', 'accomplishment', 'excellence'],
            '被爱导向': ['被爱', '接纳', 'love', 'acceptance', 'belonging', 'connection'],
            '尊重导向': ['尊重', '尊严', 'respect', 'dignity', 'honor', 'esteem'],
            '真实导向': ['真实', '诚实', 'authentic', 'truth', 'honesty', 'genuine'],
            '和谐导向': ['和谐', '和睦', 'harmony', 'peace', 'balance', 'unity'],
            '成长导向': ['成长', '进步', 'growth', 'progress', 'development', 'evolution'],
            '服务导向': ['服务', '奉献', 'service', 'giving', 'contribution', 'helping'],
            '享乐导向': ['享乐', '快乐', 'pleasure', 'enjoyment', 'fun', 'happiness'],
        },
        
        # 13. 动机类型
        TagCategory.MOTIVE_TYPE: {
            '恐惧驱动': ['恐惧', '害怕', 'fear driven', 'afraid', 'scared motivation'],
            '骄傲驱动': ['骄傲', '虚荣', 'pride driven', 'ego', 'image conscious'],
            '爱驱动': ['爱', '关心', 'love driven', 'caring', 'compassionate'],
            '欲望驱动': ['欲望', '想要', 'desire driven', 'wanting', 'craving'],
            '责任驱动': ['责任', '义务', 'duty driven', 'obligation', 'responsible'],
            '野心驱动': ['野心', '抱负', 'ambition driven', 'aspiring', 'achievement motivated'],
        },
        
        # 14. 关系类型
        TagCategory.RELATIONSHIP_TYPE: {
            '亲密关系': ['亲密', '伴侣', 'spouse', 'partner', 'intimate', 'romantic'],
            '亲子关系': ['孩子', '父母', 'parent', 'child', 'parenting', 'mother', 'father'],
            '职场关系': ['同事', '上司', '下属', 'colleague', 'boss', 'workplace', 'professional'],
            '友谊关系': ['朋友', '友情', 'friend', 'friendship', 'buddy', 'pal'],
            '原生家庭': ['原生家庭', '父母', 'family-of-origin', 'birth family', 'parents'],
            '权威关系': ['权威', '老师', 'authority', 'teacher', 'mentor', 'leader'],
            '社群关系': ['社群', '教会', 'community', 'church', 'group', 'fellowship'],
        },
        
        # 15. 依恋风格
        TagCategory.ATTACHMENT_STYLE: {
            '安全依恋': ['安全', '信任', 'secure', 'trusting', 'securely attached'],
            '焦虑依恋': ['焦虑', '怕被抛弃', 'anxious', 'preoccupied', 'fear of abandonment'],
            '回避依恋': ['回避', '保持距离', 'avoidant', 'dismissive', 'emotionally distant'],
            '混乱依恋': ['混乱', '矛盾', 'disorganized', 'fearful-avoidant', 'unresolved'],
        },
        
        # 16. 社交偏好
        TagCategory.SOCIAL_PREFERENCE: {
            '外向型': ['外向', '社交', 'extrovert', 'sociable', 'outgoing', 'gregarious'],
            '内向型': ['内向', '独处', 'introvert', 'solitary', 'reserved', 'quiet'],
            '混合型': ['混合', '视情况', 'ambivert', 'flexible', 'context dependent'],
            '小圈子型': ['小圈子', '密友', 'small circle', 'close friends', 'intimate group'],
            '广泛社交型': ['广泛社交', '认识很多人', 'broad network', 'many acquaintances'],
        },
        
        # 17. 认知风格
        TagCategory.COGNITIVE_STYLE: {
            '全或无思维': ['全或无', '黑白', 'all-or-nothing', 'black-white', 'binary', 'dichotomous'],
            '灾难化思维': ['灾难', '最糟', 'catastrophize', 'worst-case', 'disaster', 'awfulizing'],
            '读心术': ['读心', '知道', 'mind-reading', 'assume', 'knowing', 'presuming'],
            '个人化': ['个人化', '针对我', 'personalize', 'about-me', 'targeted', 'self-referential'],
            '过度概括': ['总是', '从不', 'overgeneralize', 'always', 'never', 'global labeling'],
            '负面过滤': ['负面', '只看', 'negative-filter', 'focus-negative', 'selective attention'],
            '理性分析型': ['理性', '分析', 'rational', 'analytical', 'logical', 'systematic'],
            '直觉感受型': ['直觉', '感受', 'intuitive', 'feeling', 'gut sense', 'holistic'],
            '细节关注型': ['细节', '具体', 'detail-oriented', 'specific', 'concrete', 'precise'],
            '大局观型': ['大局', '整体', 'big picture', 'global', 'holistic', 'strategic'],
        },
        
        # 18. 灵性状态
        TagCategory.SPIRITUAL_STATE: {
            '灵性干枯': ['干枯', '远离神', 'dry', 'distant', 'spiritual-dryness', 'desert'],
            '被弃感': ['被弃', '离弃', 'forsaken', 'abandoned', 'god-forsaken', 'deserted'],
            '怀疑期': ['怀疑', '不信', 'doubt', 'unbelief', 'skepticism', 'questioning'],
            '认罪悔改': ['认罪', '悔改', 'repent', 'confession', 'sin-acknowledgment', 'turning'],
            '感恩灵修': ['感恩', '赞美', 'gratitude', 'praise', 'thanksgiving', 'worship'],
            '寻求引导': ['引导', '旨意', 'guidance', 'will-of-god', 'direction', 'leading'],
            '亲密连接': ['亲密', '亲近神', 'intimate', 'close-to-god', 'connected', 'union'],
            '成长进步': ['成长', '进深', 'growing', 'deepening', 'maturing', 'advancing'],
        },
        
        # 19. 决策风格
        TagCategory.DECISION_STYLE: {
            '快速决策': ['快速', '立即', 'quick', 'fast', 'immediate', 'decisive', 'prompt'],
            '拖延决策': ['拖延', '推迟', 'delay', 'procrastinate', 'put-off', 'hesitant'],
            '寻求共识': ['共识', '商量', 'consensus', 'discuss', 'together', 'collaborative'],
            '独自决定': ['独自', '自己', 'alone', 'independent', 'self', 'autonomous'],
            '避免冲突': ['避免', '冲突', 'avoid-conflict', 'keep-peace', 'harmony', 'appeasing'],
            '风险偏好': ['风险', '冒险', 'risk', 'adventure', 'daring', 'bold'],
            '保守谨慎': ['保守', '谨慎', 'conservative', 'cautious', 'careful', 'prudent'],
            '分析型': ['分析', '研究', 'analytical', 'research', 'data-driven', 'evidence-based'],
            '直觉型': ['直觉', '感觉', 'intuitive', 'gut-feeling', 'instinct', 'inner sense'],
            '咨询型': ['咨询', '问意见', 'consultative', 'seek advice', 'ask around'],
        },
    }
    
    def __init__(self):
        self.tag_patterns = self.TAG_PATTERNS
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译匹配模式以提高性能"""
        self._compiled = {}
        for category, tags in self.tag_patterns.items():
            self._compiled[category] = {}
            for tag_name, keywords in tags.items():
                # 创建正则表达式以提高匹配精度
                patterns = []
                for kw in keywords:
                    if len(kw) >= 3:
                        patterns.append(re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE))
                    else:
                        patterns.append(kw.lower())
                self._compiled[category][tag_name] = patterns
    
    def extract_from_text(self, text: str, source: TagSource = TagSource.SYSTEM_INFERRED,
                         context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """从文本中提取标签 - 核心方法"""
        if not text or not isinstance(text, str):
            return []
        
        text_lower = text.lower()
        extracted_tags = []
        
        for category, tags in self._compiled.items():
            for tag_name, patterns in tags.items():
                match_score = 0
                matched_keywords = []
                
                for pattern in patterns:
                    if isinstance(pattern, re.Pattern):
                        matches = pattern.findall(text)
                        if matches:
                            match_score += len(matches) * 2  # 正则匹配权重更高
                            matched_keywords.extend(matches)
                    else:
                        if pattern in text_lower:
                            match_score += 1
                            matched_keywords.append(pattern)
                
                if match_score > 0:
                    # 计算置信度：基础0.5 + 匹配分*系数，上限0.95
                    confidence = min(0.4 + (match_score * 0.12), 0.95)
                    
                    # 根据来源调整权重
                    source_weight_boost = {
                        TagSource.MANUAL: 0.15,
                        TagSource.TEST_ASSESSMENT: 0.12,
                        TagSource.FORMATION_ANALYSIS: 0.10,
                        TagSource.EMOTION_CHECKIN: 0.08,
                        TagSource.DECISION_EVENT: 0.08,
                        TagSource.HABIT_EXECUTION: 0.05,
                    }.get(source, 0)
                    
                    confidence = min(confidence + source_weight_boost, 0.95)
                    
                    tag_data = {
                        'tag_name': tag_name,
                        'tag_category': category.value,
                        'source': source.value,
                        'confidence': round(confidence, 2),
                        'matched_keywords': list(set(matched_keywords)),
                        'extraction_method': 'pattern_match',
                        'context': context or {},
                    }
                    extracted_tags.append(tag_data)
        
        # 按置信度排序，去重（保留最高置信度）
        extracted_tags.sort(key=lambda x: x['confidence'], reverse=True)
        seen = set()
        unique_tags = []
        for tag in extracted_tags:
            key = (tag['tag_name'], tag['tag_category'])
            if key not in seen:
                seen.add(key)
                unique_tags.append(tag)
        
        return unique_tags
    
    def extract_from_emotion_checkin(self, checkin_data: Dict[str, Any]) -> TagExtractionResult:
        """从情绪打卡数据提取标签"""
        all_tags = []
        
        # 1. 情绪标签
        emotion_label = checkin_data.get('emotionLabel', '')
        if emotion_label:
            tags = self.extract_from_text(emotion_label, TagSource.EMOTION_CHECKIN)
            all_tags.extend(tags)
        
        # 2. 情绪描述文本
        emotion_query = checkin_data.get('emotionQuery', '')
        if emotion_query:
            tags = self.extract_from_text(emotion_query, TagSource.EMOTION_CHECKIN)
            all_tags.extend(tags)
        
        # 3. 生活处境
        scenario = checkin_data.get('scenarioCategory', '') + ' ' + checkin_data.get('scenarioDetail', '')
        if scenario.strip():
            tags = self.extract_from_text(scenario, TagSource.EMOTION_CHECKIN,
                                          context={'source_field': 'scenario'})
            all_tags.extend(tags)
        
        # 4. 行为驱动
        driver = checkin_data.get('driverType', '') + ' ' + checkin_data.get('driverOption', '')
        if driver.strip():
            tags = self.extract_from_text(driver, TagSource.EMOTION_CHECKIN,
                                          context={'source_field': 'behavior_driver'})
            all_tags.extend(tags)
        
        # 5. 祷告/感恩文本
        prayer = checkin_data.get('prayerRequest', '')
        gratitude = checkin_data.get('gratitude', '')
        for text, field in [(prayer, 'prayer'), (gratitude, 'gratitude')]:
            if text:
                tags = self.extract_from_text(text, TagSource.EMOTION_CHECKIN,
                                              context={'source_field': field})
                all_tags.extend(tags)
        
        # 6. 状态标签
        mood = checkin_data.get('mood', '')
        sleep = checkin_data.get('sleep', '')
        energy = checkin_data.get('energy', '')
        
        state_indicators = {
            '疲惫': ['累', '疲劳', 'tired', 'exhausted'],
            '低落': ['低落', 'down', 'sad'],
            '焦虑': ['焦虑', 'anxious', 'worried'],
            '兴奋': ['兴奋', 'excited', 'energetic'],
        }
        for state, keywords in state_indicators.items():
            for kw in keywords:
                if (mood and kw in mood.lower()) or (sleep and kw in sleep.lower()) or (energy and kw in energy.lower()):
                    all_tags.append({
                        'tag_name': state,
                        'tag_category': TagCategory.EMOTION_TYPE.value,
                        'source': TagSource.EMOTION_CHECKIN.value,
                        'confidence': 0.6,
                        'context': {'source_field': 'state_indicator'}
                    })
                    break
        
        return TagExtractionResult(
            tags=all_tags,
            source_type='emotion_checkin',
            source_id=checkin_data.get('id'),
            confidence=0.7 if all_tags else 0
        )
    
    def extract_from_decision(self, decision_data: Dict[str, Any]) -> TagExtractionResult:
        """从决策事件提取标签"""
        all_tags = []
        
        # 决策描述
        title = decision_data.get('title', '')
        description = decision_data.get('description', '')
        
        for text, field in [(title, 'title'), (description, 'description')]:
            if text:
                tags = self.extract_from_text(text, TagSource.DECISION_EVENT,
                                              context={'source_field': field})
                all_tags.extend(tags)
        
        # 决策类别映射到生活领域
        category_map = {
            'career': '工作领域',
            'relationship': '关系领域',
            'family': '家庭领域',
            'financial': '财务领域',
            'health': '健康领域',
            'spiritual': '信仰领域',
            'education': '学习领域',
        }
        category = decision_data.get('category', '')
        if category in category_map:
            all_tags.append({
                'tag_name': category_map[category],
                'tag_category': TagCategory.LIFE_DOMAIN.value,
                'source': TagSource.DECISION_EVENT.value,
                'confidence': 0.85,
                'context': {'decision_category': category}
            })
        
        # 动机分析
        motive = decision_data.get('motive_analysis', {})
        if motive:
            motive_scores = {
                '恐惧驱动': motive.get('fear_driven_score', 0),
                '骄傲驱动': motive.get('pride_driven_score', 0),
                '爱驱动': motive.get('love_driven_score', 0),
                '欲望驱动': motive.get('desire_driven_score', 0),
            }
            for tag_name, score in motive_scores.items():
                if score > 0.6:
                    all_tags.append({
                        'tag_name': tag_name,
                        'tag_category': TagCategory.MOTIVE_TYPE.value,
                        'source': TagSource.DECISION_EVENT.value,
                        'confidence': round(score, 2),
                        'context': {'motive_score': score}
                    })
        
        # 紧急/重要程度映射到决策风格
        urgency = decision_data.get('urgency_level', 3)
        importance = decision_data.get('importance_level', 3)
        
        if urgency >= 4 and importance >= 4:
            all_tags.append({
                'tag_name': '快速决策',
                'tag_category': TagCategory.DECISION_STYLE.value,
                'source': TagSource.DECISION_EVENT.value,
                'confidence': 0.6,
                'context': {'urgency': urgency, 'importance': importance}
            })
        
        return TagExtractionResult(
            tags=all_tags,
            source_type='decision_event',
            source_id=decision_data.get('id'),
            confidence=0.75 if all_tags else 0
        )
    
    def extract_from_habit(self, habit_data: Dict[str, Any]) -> TagExtractionResult:
        """从习惯数据提取标签"""
        all_tags = []
        
        # 习惯名称和描述
        habit_name = habit_data.get('habit_name', '')
        description = habit_data.get('habit_description', '')
        
        for text, field in [(habit_name, 'name'), (description, 'description')]:
            if text:
                tags = self.extract_from_text(text, TagSource.HABIT_EXECUTION,
                                              context={'source_field': field})
                # 过滤出习惯相关标签
                habit_tags = [t for t in tags if t['tag_category'] in 
                             [TagCategory.HABIT_TYPE.value, TagCategory.ROUTINE_PREFERENCE.value]]
                all_tags.extend(habit_tags)
        
        # 执行数据分析
        executions = habit_data.get('executions', [])
        if executions:
            completion_rate = sum(1 for e in executions if e.get('completed')) / len(executions)
            
            if completion_rate >= 0.8:
                all_tags.append({
                    'tag_name': '高度自律',
                    'tag_category': TagCategory.HABIT_CONSISTENCY.value,
                    'source': TagSource.HABIT_EXECUTION.value,
                    'confidence': round(completion_rate, 2),
                    'context': {'completion_rate': completion_rate}
                })
            elif completion_rate <= 0.3:
                all_tags.append({
                    'tag_name': '容易放弃',
                    'tag_category': TagCategory.HABIT_CONSISTENCY.value,
                    'source': TagSource.HABIT_EXECUTION.value,
                    'confidence': round(1 - completion_rate, 2),
                    'context': {'completion_rate': completion_rate}
                })
        
        # 连续天数
        streak = habit_data.get('current_streak_days', 0)
        if streak >= 21:
            all_tags.append({
                'tag_name': '高度自律',
                'tag_category': TagCategory.HABIT_CONSISTENCY.value,
                'source': TagSource.HABIT_EXECUTION.value,
                'confidence': min(0.5 + streak * 0.01, 0.9),
                'context': {'streak_days': streak}
            })
        
        return TagExtractionResult(
            tags=all_tags,
            source_type='habit_execution',
            source_id=habit_data.get('id'),
            confidence=0.6 if all_tags else 0
        )
    
    def extract_from_formation(self, formation_data: Dict[str, Any]) -> TagExtractionResult:
        """从Formation Engine分析结果提取标签"""
        all_tags = []
        
        # 8维状态向量映射到性格标签
        state_vector = formation_data.get('state_vector', {})
        dimension_tags = {
            'humility': ('谦逊型', 0.6),
            'fear_tendency': ('恐惧型', 0.7),
            'pride_tendency': ('骄傲倾向', 0.7),
            'emotional_stability': ('情绪稳定型', 0.6),
            'truth_alignment': ('真诚型', 0.6),
            'relational_health': ('关系良好', 0.6),
            'resilience': ('坚韧型', 0.6),
            'spiritual_clarity': ('灵性清晰', 0.6),
        }
        
        for dim, (tag_name, threshold) in dimension_tags.items():
            score = state_vector.get(dim, 0.5)
            if dim in ['fear_tendency', 'pride_tendency']:
                # 这些维度高表示问题
                if score > threshold:
                    all_tags.append({
                        'tag_name': tag_name,
                        'tag_category': TagCategory.CHARACTER_TRAIT.value,
                        'source': TagSource.FORMATION_ANALYSIS.value,
                        'confidence': round(score, 2),
                        'context': {'dimension': dim, 'score': score}
                    })
            else:
                # 其他维度高表示优势
                if score > threshold + 0.15:
                    all_tags.append({
                        'tag_name': tag_name,
                        'tag_category': TagCategory.CHARACTER_TRAIT.value,
                        'source': TagSource.FORMATION_ANALYSIS.value,
                        'confidence': round(score, 2),
                        'context': {'dimension': dim, 'score': score}
                    })
        
        # 主导循环
        dominant_loop = formation_data.get('dominant_loop', '')
        if dominant_loop:
            loop_tags = {
                'fear_control_loop': ['恐惧驱动', '控制型'],
                'shame_avoidance_loop': ['逃避型', '羞愧感'],
                'pride_comparison_loop': ['骄傲驱动', '竞争型'],
                'desire_impulse_loop': ['冲动型', '欲望驱动'],
                'truth_stability_loop': ['稳定型', '真实导向'],
            }
            for tag_name in loop_tags.get(dominant_loop, []):
                all_tags.append({
                    'tag_name': tag_name,
                    'tag_category': TagCategory.BEHAVIOR_PATTERN.value,
                    'source': TagSource.FORMATION_ANALYSIS.value,
                    'confidence': 0.75,
                    'context': {'dominant_loop': dominant_loop}
                })
        
        # 轨迹方向
        trajectory = formation_data.get('trajectory_direction', '')
        if trajectory:
            trajectory_tags = {
                'stabilizing': '情绪稳定型',
                'fragmenting': '情绪压力型',
                'improving_clarity': '灵性成长型',
                'increasing_volatility': '波动变化型',
            }
            if trajectory in trajectory_tags:
                all_tags.append({
                    'tag_name': trajectory_tags[trajectory],
                    'tag_category': TagCategory.EMOTION_PATTERN.value,
                    'source': TagSource.FORMATION_ANALYSIS.value,
                    'confidence': 0.7,
                    'context': {'trajectory': trajectory}
                })
        
        return TagExtractionResult(
            tags=all_tags,
            source_type='formation_analysis',
            confidence=0.8 if all_tags else 0
        )


# ==================== 标签存储管理 ====================

class UserTagStore:
    """
    用户标签存储管理
    支持权重计算、时间衰减、置信度管理
    """
    
    # 时间衰减配置
    RECENCY_DECAY = 0.92              # 历史衰减系数
    WEIGHT_DECAY_DAYS = 30            # 衰减计算周期（天）
    MAX_WEIGHT = 10.0                 # 最大权重
    MIN_ACTIVE_WEIGHT = 0.3           # 活跃标签最低权重
    
    # 来源权重加成
    SOURCE_WEIGHT_BOOST = {
        TagSource.MANUAL.value: 1.5,
        TagSource.TEST_ASSESSMENT.value: 1.3,
        TagSource.FORMATION_ANALYSIS.value: 1.2,
        TagSource.DECISION_EVENT.value: 1.1,
        TagSource.EMOTION_CHECKIN.value: 1.0,
        TagSource.HABIT_EXECUTION.value: 0.9,
        TagSource.JOURNAL_ENTRY.value: 0.9,
        TagSource.CHAT_INTERACTION.value: 0.8,
        TagSource.PRAYER_REQUEST.value: 0.8,
        TagSource.BEHAVIOR_REGULATION.value: 0.8,
        TagSource.SYSTEM_INFERRED.value: 0.7,
    }
    
    def __init__(self, db_pool=None, use_memory: bool = False):
        self.db_pool = db_pool
        self.use_memory = use_memory
        self._memory_store: Dict[str, Dict[str, UserTag]] = {}  # user_id -> {tag_name: UserTag}
        
        if db_pool and not use_memory:
            self._init_table()
    
    def _init_table(self):
        """初始化数据库表"""
        if not self.db_pool:
            return
        
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # 主标签表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_profile_tags (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id TEXT NOT NULL,
                        tag_name TEXT NOT NULL,
                        tag_category TEXT NOT NULL,
                        tag_subcategory TEXT,
                        source TEXT NOT NULL,
                        confidence REAL DEFAULT 0.5,
                        weight REAL DEFAULT 1.0,
                        first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        occurrence_count INTEGER DEFAULT 1,
                        context_snapshot JSONB DEFAULT '{}',
                        related_emotions JSONB DEFAULT '[]',
                        related_decisions JSONB DEFAULT '[]',
                        related_habits JSONB DEFAULT '[]',
                        source_events JSONB DEFAULT '[]',
                        history_weights JSONB DEFAULT '[]',
                        is_active BOOLEAN DEFAULT TRUE,
                        is_manually_added BOOLEAN DEFAULT FALSE,
                        is_system_core BOOLEAN DEFAULT FALSE,
                        UNIQUE(user_id, tag_name)
                    )
                """)
                
                # 索引
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_profile_tags_user_id 
                    ON user_profile_tags(user_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_profile_tags_category 
                    ON user_profile_tags(tag_category, user_id)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_profile_tags_weight 
                    ON user_profile_tags(user_id, weight DESC)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_profile_tags_active 
                    ON user_profile_tags(user_id, is_active, weight DESC)
                """)
                
                # 标签事件关联表（用于追踪标签来源）
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tag_event_links (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tag_id UUID REFERENCES user_profile_tags(id) ON DELETE CASCADE,
                        event_type TEXT NOT NULL,
                        event_id TEXT NOT NULL,
                        event_data JSONB DEFAULT '{}',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                conn.commit()
                print('[profile_tags] Database tables initialized', flush=True)
        finally:
            self.db_pool.putconn(conn)
    
    def add_or_update_tags(self, user_id: str, tags: List[Dict[str, Any]],
                          source_event: Optional[Dict] = None) -> List[str]:
        """
        添加或更新标签
        
        Args:
            user_id: 用户ID
            tags: 标签列表
            source_event: 来源事件 {'type': 'emotion_checkin', 'id': 'xxx', 'data': {...}}
        
        Returns:
            标签ID列表
        """
        if not tags:
            return []
        
        if self.use_memory:
            return self._add_or_update_memory(user_id, tags, source_event)
        else:
            return self._add_or_update_db(user_id, tags, source_event)
    
    def _add_or_update_memory(self, user_id: str, tags: List[Dict],
                              source_event: Optional[Dict]) -> List[str]:
        """内存存储模式"""
        if user_id not in self._memory_store:
            self._memory_store[user_id] = {}
        
        user_tags = self._memory_store[user_id]
        tag_ids = []
        
        for tag_data in tags:
            tag_name = tag_data['tag_name']
            now = datetime.utcnow()
            
            if tag_name in user_tags:
                # 更新现有标签
                existing = user_tags[tag_name]
                existing.occurrence_count += 1
                existing.last_seen_at = now
                
                # 权重递增（带衰减考虑）
                time_diff = (now - existing.last_seen_at).days
                decay_factor = self.RECENCY_DECAY ** max(time_diff, 0)
                old_weight = existing.weight * decay_factor
                
                # 新权重 = 旧权重衰减值 + 新信号权重
                source_boost = self.SOURCE_WEIGHT_BOOST.get(tag_data.get('source', 'system'), 1.0)
                new_signal = tag_data.get('confidence', 0.5) * source_boost
                
                existing.weight = min(old_weight + new_signal * 0.5, self.MAX_WEIGHT)
                existing.confidence = max(existing.confidence, tag_data.get('confidence', 0.5))
                existing.history_weights.append((now, existing.weight))
                
                # 合并上下文
                if 'context' in tag_data:
                    existing.context_snapshot.update(tag_data['context'])
                
                # 记录事件来源
                if source_event:
                    event_ref = f"{source_event.get('type')}:{source_event.get('id')}"
                    if event_ref not in existing.source_events:
                        existing.source_events.append(event_ref)
                
                tag_ids.append(existing.id)
            else:
                # 创建新标签
                source_boost = self.SOURCE_WEIGHT_BOOST.get(tag_data.get('source', 'system'), 1.0)
                initial_weight = tag_data.get('confidence', 0.5) * 2 * source_boost
                
                new_tag = UserTag(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    tag_name=tag_name,
                    tag_category=tag_data.get('tag_category', 'unknown'),
                    tag_subcategory=tag_data.get('tag_subcategory'),
                    source=tag_data.get('source', 'system'),
                    confidence=tag_data.get('confidence', 0.5),
                    weight=min(initial_weight, self.MAX_WEIGHT),
                    first_seen_at=now,
                    last_seen_at=now,
                    occurrence_count=1,
                    context_snapshot=tag_data.get('context', {}),
                    history_weights=[(now, min(initial_weight, self.MAX_WEIGHT))],
                    is_manually_added=tag_data.get('source') == TagSource.MANUAL.value
                )
                
                if source_event:
                    new_tag.source_events = [f"{source_event.get('type')}:{source_event.get('id')}"]
                
                user_tags[tag_name] = new_tag
                tag_ids.append(new_tag.id)
        
        return tag_ids
    
    def _add_or_update_db(self, user_id: str, tags: List[Dict],
                          source_event: Optional[Dict]) -> List[str]:
        """数据库存储模式"""
        conn = self.db_pool.getconn()
        tag_ids = []
        
        try:
            with conn.cursor() as cur:
                for tag_data in tags:
                    tag_name = tag_data['tag_name']
                    tag_category = tag_data.get('tag_category', 'unknown')
                    source = tag_data.get('source', 'system')
                    confidence = tag_data.get('confidence', 0.5)
                    context = json.dumps(tag_data.get('context', {}))
                    
                    # 检查是否已存在
                    cur.execute("""
                        SELECT id, occurrence_count, weight, last_seen_at, 
                               confidence, context_snapshot, source_events
                        FROM user_profile_tags
                        WHERE user_id = %s AND tag_name = %s
                    """, (user_id, tag_name))
                    
                    result = cur.fetchone()
                    
                    if result:
                        # 更新现有标签
                        tag_id, count, old_weight, last_seen, old_conf, old_context, old_events = result
                        
                        # 计算时间衰减
                        now = datetime.utcnow()
                        days_diff = (now - last_seen).days if last_seen else 0
                        decay_factor = self.RECENCY_DECAY ** max(days_diff, 0)
                        decayed_weight = old_weight * decay_factor
                        
                        # 新权重计算
                        source_boost = self.SOURCE_WEIGHT_BOOST.get(source, 1.0)
                        new_signal = confidence * source_boost
                        new_weight = min(decayed_weight + new_signal * 0.5, self.MAX_WEIGHT)
                        new_count = count + 1
                        new_conf = max(old_conf, confidence)
                        
                        # 更新历史权重
                        history = [(last_seen, old_weight)] if last_seen else []
                        history.append((now, new_weight))
                        
                        # 合并上下文
                        merged_context = {}
                        try:
                            merged_context = json.loads(old_context) if old_context else {}
                        except Exception:
                            pass
                        merged_context.update(tag_data.get('context', {}))
                        
                        # 更新事件来源
                        events = []
                        try:
                            events = json.loads(old_events) if old_events else []
                        except Exception:
                            pass
                        if source_event:
                            event_ref = f"{source_event.get('type')}:{source_event.get('id')}"
                            if event_ref not in events:
                                events.append(event_ref)
                        
                        cur.execute("""
                            UPDATE user_profile_tags
                            SET last_seen_at = NOW(),
                                occurrence_count = %s,
                                weight = %s,
                                confidence = %s,
                                context_snapshot = %s::jsonb,
                                history_weights = history_weights || %s::jsonb,
                                source_events = %s::jsonb,
                                is_active = TRUE
                            WHERE id = %s
                            RETURNING id
                        """, (new_count, new_weight, new_conf,
                              json.dumps(merged_context),
                              json.dumps([[now.isoformat(), new_weight]]),
                              json.dumps(events),
                              tag_id))
                        
                        tag_ids.append(tag_id)
                    else:
                        # 创建新标签
                        source_boost = self.SOURCE_WEIGHT_BOOST.get(source, 1.0)
                        initial_weight = min(confidence * 2 * source_boost, self.MAX_WEIGHT)
                        
                        events = []
                        if source_event:
                            events = [f"{source_event.get('type')}:{source_event.get('id')}"]
                        
                        cur.execute("""
                            INSERT INTO user_profile_tags
                            (user_id, tag_name, tag_category, source, confidence, weight,
                             context_snapshot, history_weights, source_events, is_manually_added)
                            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                            RETURNING id
                        """, (user_id, tag_name, tag_category, source, confidence, initial_weight,
                              context,
                              json.dumps([[datetime.utcnow().isoformat(), initial_weight]]),
                              json.dumps(events),
                              source == TagSource.MANUAL.value))
                        
                        tag_id = cur.fetchone()[0]
                        tag_ids.append(tag_id)
                
                conn.commit()
        finally:
            self.db_pool.putconn(conn)
        
        return tag_ids
    
    def get_user_tags(self, user_id: str, category: Optional[str] = None,
                     limit: int = 50, active_only: bool = True,
                     min_weight: float = 0.5) -> List[Dict[str, Any]]:
        """获取用户标签列表"""
        if self.use_memory:
            return self._get_user_tags_memory(user_id, category, limit, active_only, min_weight)
        else:
            return self._get_user_tags_db(user_id, category, limit, active_only, min_weight)
    
    def _get_user_tags_memory(self, user_id: str, category: Optional[str],
                             limit: int, active_only: bool, min_weight: float) -> List[Dict]:
        """内存模式获取标签"""
        user_tags = self._memory_store.get(user_id, {})
        
        tags = []
        for tag in user_tags.values():
            if active_only and not tag.is_active:
                continue
            if category and tag.tag_category != category:
                continue
            if tag.weight < min_weight:
                continue
            tags.append(tag)
        
        # 按权重排序
        tags.sort(key=lambda t: t.weight, reverse=True)
        return [t.to_dict() for t in tags[:limit]]
    
    def _get_user_tags_db(self, user_id: str, category: Optional[str],
                         limit: int, active_only: bool, min_weight: float) -> List[Dict]:
        """数据库模式获取标签"""
        conn = self.db_pool.getconn()
        
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT id, tag_name, tag_category, tag_subcategory, source,
                           confidence, weight, first_seen_at, last_seen_at,
                           occurrence_count, context_snapshot, related_emotions,
                           related_decisions, related_habits, source_events,
                           is_active, is_manually_added, is_system_core
                    FROM user_profile_tags
                    WHERE user_id = %s AND weight >= %s
                """
                params = [user_id, min_weight]
                
                if active_only:
                    query += " AND is_active = TRUE"
                
                if category:
                    query += " AND tag_category = %s"
                    params.append(category)
                
                query += " ORDER BY weight DESC, occurrence_count DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                
                columns = [desc[0] for desc in cur.description]
                tags = []
                
                for row in cur.fetchall():
                    tag_dict = dict(zip(columns, row))
                    # 解析JSON字段
                    for field in ['context_snapshot', 'related_emotions', 'related_decisions',
                                 'related_habits', 'source_events']:
                        if tag_dict.get(field):
                            try:
                                tag_dict[field] = json.loads(tag_dict[field])
                            except Exception:
                                pass
                    tags.append(tag_dict)
                
                return tags
        finally:
            self.db_pool.putconn(conn)
    
    def get_tag_insights(self, user_id: str) -> Dict[str, Any]:
        """获取用户标签洞察统计"""
        tags = self.get_user_tags(user_id, limit=200, active_only=True, min_weight=0.3)
        
        if not tags:
            return {
                'user_id': user_id,
                'total_tags': 0,
                'category_distribution': [],
                'top_tags': [],
                'recent_tags': [],
                'stable_tags': [],
                'emerging_tags': [],
            }
        
        # 分类统计
        category_counts = defaultdict(lambda: {'count': 0, 'total_weight': 0, 'tags': []})
        for tag in tags:
            cat = tag['tag_category']
            category_counts[cat]['count'] += 1
            category_counts[cat]['total_weight'] += tag['weight']
            category_counts[cat]['tags'].append(tag)
        
        category_distribution = [
            {
                'category': cat,
                'count': stats['count'],
                'average_weight': round(stats['total_weight'] / stats['count'], 2),
                'top_tag': max(stats['tags'], key=lambda t: t['weight'])['tag_name'] if stats['tags'] else None
            }
            for cat, stats in sorted(category_counts.items(), key=lambda x: x[1]['count'], reverse=True)
        ]
        
        # 识别稳定标签（高权重、多次出现）
        stable_tags = [
            t for t in tags
            if t['weight'] >= 5.0 and t['occurrence_count'] >= 3
        ]
        
        # 识别新兴标签（最近30天内首次出现）
        now = datetime.utcnow()
        emerging_tags = []
        for t in tags:
            first_seen = t.get('first_seen_at')
            if first_seen:
                if isinstance(first_seen, str):
                    first_seen = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
                if (now - first_seen).days <= 30:
                    emerging_tags.append(t)
        
        return {
            'user_id': user_id,
            'total_tags': len(tags),
            'active_categories': len(category_distribution),
            'average_weight': round(sum(t['weight'] for t in tags) / len(tags), 2) if tags else 0,
            'category_distribution': category_distribution,
            'top_tags': [{'name': t['tag_name'], 'category': t['tag_category'], 'weight': t['weight']} 
                        for t in tags[:10]],
            'recent_tags': [{'name': t['tag_name'], 'last_seen': t['last_seen_at']} 
                           for t in sorted(tags, key=lambda x: x['last_seen_at'], reverse=True)[:10]],
            'stable_tags': [{'name': t['tag_name'], 'weight': t['weight'], 'count': t['occurrence_count']} 
                           for t in stable_tags[:10]],
            'emerging_tags': [{'name': t['tag_name'], 'first_seen': t['first_seen_at']} 
                             for t in emerging_tags[:10]],
        }
    
    def apply_time_decay(self, user_id: Optional[str] = None):
        """应用时间衰减"""
        if self.use_memory:
            return self._apply_decay_memory(user_id)
        else:
            return self._apply_decay_db(user_id)
    
    def _apply_decay_memory(self, user_id: Optional[str]):
        """内存模式时间衰减"""
        target_users = [user_id] if user_id else list(self._memory_store.keys())
        
        for uid in target_users:
            user_tags = self._memory_store.get(uid, {})
            for tag in user_tags.values():
                days_diff = (datetime.utcnow() - tag.last_seen_at).days
                if days_diff > 7:  # 超过7天未更新才衰减
                    decay_factor = self.RECENCY_DECAY ** (days_diff / 7)
                    tag.weight *= decay_factor
                    
                    if tag.weight < self.MIN_ACTIVE_WEIGHT:
                        tag.is_active = False
    
    def _apply_decay_db(self, user_id: Optional[str]):
        """数据库模式时间衰减"""
        conn = self.db_pool.getconn()
        
        try:
            with conn.cursor() as cur:
                if user_id:
                    # 指定用户的衰减
                    cur.execute("""
                        UPDATE user_profile_tags
                        SET weight = weight * POWER(%s, 
                            GREATEST(EXTRACT(DAY FROM NOW() - last_seen_at) / 7, 0)),
                            is_active = CASE 
                                WHEN weight * POWER(%s, 
                                    GREATEST(EXTRACT(DAY FROM NOW() - last_seen_at) / 7, 0)) < %s 
                                THEN FALSE 
                                ELSE is_active 
                            END
                        WHERE user_id = %s
                    """, (self.RECENCY_DECAY, self.RECENCY_DECAY, self.MIN_ACTIVE_WEIGHT, user_id))
                else:
                    # 全局衰减
                    cur.execute("""
                        UPDATE user_profile_tags
                        SET weight = weight * POWER(%s, 
                            GREATEST(EXTRACT(DAY FROM NOW() - last_seen_at) / 7, 0)),
                            is_active = CASE 
                                WHEN weight * POWER(%s, 
                                    GREATEST(EXTRACT(DAY FROM NOW() - last_seen_at) / 7, 0)) < %s 
                                THEN FALSE 
                                ELSE is_active 
                            END
                    """, (self.RECENCY_DECAY, self.RECENCY_DECAY, self.MIN_ACTIVE_WEIGHT))
                
                conn.commit()
        finally:
            self.db_pool.putconn(conn)
    
    def deactivate_tag(self, user_id: str, tag_name: str) -> bool:
        """停用标签"""
        if self.use_memory:
            user_tags = self._memory_store.get(user_id, {})
            if tag_name in user_tags:
                user_tags[tag_name].is_active = False
                return True
            return False
        else:
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_profile_tags
                        SET is_active = FALSE
                        WHERE user_id = %s AND tag_name = %s
                        RETURNING id
                    """, (user_id, tag_name))
                    result = cur.fetchone()
                    conn.commit()
                    return result is not None
            finally:
                self.db_pool.putconn(conn)
    
    def reactivate_tag(self, user_id: str, tag_name: str) -> bool:
        """重新激活标签"""
        if self.use_memory:
            user_tags = self._memory_store.get(user_id, {})
            if tag_name in user_tags:
                user_tags[tag_name].is_active = True
                user_tags[tag_name].weight = max(user_tags[tag_name].weight, 1.0)
                return True
            return False
        else:
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_profile_tags
                        SET is_active = TRUE, weight = GREATEST(weight, 1.0)
                        WHERE user_id = %s AND tag_name = %s
                        RETURNING id
                    """, (user_id, tag_name))
                    result = cur.fetchone()
                    conn.commit()
                    return result is not None
            finally:
                self.db_pool.putconn(conn)


# ==================== 人格画像生成引擎 ====================

class PersonalityProfileEngine:
    """
    人格画像生成引擎
    基于标签和FormationStateVector生成用户唯一画像
    """
    
    # 人格原型识别规则（基于标签组合）
    ARCHETYPE_RULES = {
        PersonalityArchetype.SEEKER: {
            'required': ['探索期', '好奇'],
            'preferred': ['寻求引导', '学习型', '迷茫型', '盼望型'],
            'formation_prefs': {'spiritual_clarity': (0.4, 0.7), 'humility': (0.5, 0.8)},
        },
        PersonalityArchetype.STEWARD: {
            'required': ['责任驱动', '高度自律'],
            'preferred': ['管家', '照顾者', '服务型', '谨慎型'],
            'formation_prefs': {'resilience': (0.5, 0.8), 'relational_health': (0.5, 0.8)},
        },
        PersonalityArchetype.WARRIOR: {
            'required': ['坚韧型'],
            'preferred': ['战士', '勇敢', '对抗', '压力下奋进'],
            'formation_prefs': {'resilience': (0.6, 0.9), 'fear_tendency': (0.2, 0.5)},
        },
        PersonalityArchetype.ARTIST: {
            'required': ['艺术家', '创造'],
            'preferred': ['敏感', '情感丰富', '直觉型', '喜悦型'],
            'formation_prefs': {'emotional_stability': (0.3, 0.6), 'spiritual_clarity': (0.4, 0.7)},
        },
        PersonalityArchetype.THINKER: {
            'required': ['思考者', '理性分析型'],
            'preferred': ['分析', '研究', '逻辑', '深度思考'],
            'formation_prefs': {'truth_alignment': (0.6, 0.9), 'humility': (0.5, 0.8)},
        },
        PersonalityArchetype.CAREGIVER: {
            'required': ['爱驱动', '照顾者'],
            'preferred': ['同理心', '滋养', '支持', '服务型'],
            'formation_prefs': {'relational_health': (0.6, 0.9), 'love driven': 'high'},
        },
        PersonalityArchetype.LEADER: {
            'required': ['领袖', '果断'],
            'preferred': ['影响', '承担责任', '快速决策', '自信型'],
            'formation_prefs': {'truth_alignment': (0.5, 0.8), 'pride_tendency': (0.3, 0.6)},
        },
        PersonalityArchetype.CONTEMPLATIVE: {
            'required': ['默观者', '内省'],
            'preferred': ['安静', '深度思考', '灵修习惯', '平静型'],
            'formation_prefs': {'spiritual_clarity': (0.6, 0.9), 'humility': (0.6, 0.9)},
        },
        PersonalityArchetype.ACTIVIST: {
            'required': ['行动者', '热情'],
            'preferred': ['驱动', '追求改变', '使命', '兴奋型'],
            'formation_prefs': {'resilience': (0.5, 0.8), 'truth_alignment': (0.5, 0.8)},
        },
        PersonalityArchetype.DIPLOMAT: {
            'required': ['外交家', '和谐'],
            'preferred': ['调解', '避免冲突', '共识', '和平'],
            'formation_prefs': {'relational_health': (0.6, 0.9), 'fear_tendency': (0.3, 0.6)},
        },
    }
    
    # 成长路径建议模板
    GROWTH_PATHWAYS = {
        'fear_control_loop': {
            'pattern': '恐惧-控制循环',
            'description': '当感到恐惧时，倾向于通过控制来应对',
            'growth_focus': ['安全感建立', '信任练习', '放手训练'],
            'suggested_practices': ['每日交托祷告', '小步冒险', '控制清单觉察'],
        },
        'shame_avoidance_loop': {
            'pattern': '羞耻-逃避循环',
            'description': '因羞耻感而逃避，逃避又加重羞耻',
            'growth_focus': ['自我接纳', '脆弱练习', '恩典内化'],
            'suggested_practices': ['羞耻日记', '安全分享', '恩典默想'],
        },
        'pride_comparison_loop': {
            'pattern': '骄傲-比较循环',
            'description': '通过与他人比较来维持自我价值',
            'growth_focus': ['价值锚定', '感恩练习', '服务他人'],
            'suggested_practices': ['每日感恩', '匿名服务', '价值清单'],
        },
        'desire_impulse_loop': {
            'pattern': '欲望-冲动循环',
            'description': '被欲望驱动，冲动行动后后悔',
            'growth_focus': ['延迟满足', '意图觉察', '替代满足'],
            'suggested_practices': ['STOP技巧', '欲望日记', '健康替代'],
        },
        'truth_stability_loop': {
            'pattern': '真理-稳定循环',
            'description': '面对真理带来内在的稳定',
            'growth_focus': ['深化 truth_alignment', '分享真理', '引导他人'],
            'suggested_practices': ['真理默想', '智慧分享', '导师角色'],
        },
    }
    
    def __init__(self, tag_store: UserTagStore):
        self.tag_store = tag_store
    
    def generate_profile(self, user_id: str, formation_vector: Optional[FormationStateVector] = None,
                        include_history: bool = True) -> PersonalityProfile:
        """
        生成用户人格画像
        
        Args:
            user_id: 用户ID
            formation_vector: 8维性格状态向量（可选）
            include_history: 是否包含历史趋势
        
        Returns:
            PersonalityProfile 人格画像
        """
        # 1. 获取用户所有标签
        all_tags = self.tag_store.get_user_tags(user_id, limit=100, active_only=True, min_weight=0.5)
        
        if not all_tags and not formation_vector:
            return PersonalityProfile(
                user_id=user_id,
                profile_summary="数据不足，无法生成画像"
            )
        
        # 2. 分类整理标签
        categorized_tags = self._categorize_tags(all_tags)
        
        # 3. 识别人格原型
        archetype = self._identify_archetype(all_tags, formation_vector)
        
        # 4. 识别主导循环
        dominant_loop = self._identify_dominant_loop(all_tags, formation_vector)
        
        # 5. 确定轨迹方向
        trajectory = self._determine_trajectory(all_tags, formation_vector)
        
        # 6. 识别生活主导领域
        life_domains = self._identify_life_dominant_domains(categorized_tags.get(TagCategory.LIFE_DOMAIN.value, []))
        
        # 7. 识别重复模式
        patterns = self._identify_recurring_patterns(all_tags)
        
        # 8. 生成叙事描述
        summary, narrative, pathway = self._generate_narrative(
            archetype, dominant_loop, trajectory, categorized_tags, formation_vector
        )
        
        # 9. 构建画像
        profile = PersonalityProfile(
            user_id=user_id,
            generated_at=datetime.utcnow(),
            formation_vector=formation_vector or FormationStateVector(),
            dominant_loop=dominant_loop,
            trajectory_direction=trajectory,
            personality_archetype=archetype.value if archetype else None,
            top_emotion_tags=self._format_top_tags(categorized_tags.get(TagCategory.EMOTION_TYPE.value, []), 5),
            top_behavior_tags=self._format_top_tags(
                categorized_tags.get(TagCategory.BEHAVIOR_PATTERN.value, []) + 
                categorized_tags.get(TagCategory.RESPONSE_STYLE.value, []), 5),
            top_value_tags=self._format_top_tags(categorized_tags.get(TagCategory.VALUE_PRIORITY.value, []), 5),
            top_relationship_tags=self._format_top_tags(categorized_tags.get(TagCategory.RELATIONSHIP_TYPE.value, []), 3),
            life_dominant_domains=life_domains,
            recurring_patterns=patterns,
            growth_indicators=self._identify_growth_indicators(all_tags, formation_vector),
            risk_factors=self._identify_risk_factors(all_tags, formation_vector),
            profile_stability=self._calculate_profile_stability(all_tags),
            change_velocity=self._calculate_change_velocity(all_tags),
            trend_direction=self._determine_trend_direction(all_tags, formation_vector),
            profile_summary=summary,
            core_narrative=narrative,
            growth_pathway=pathway,
        )
        
        return profile
    
    def _categorize_tags(self, tags: List[Dict]) -> Dict[str, List[Dict]]:
        """按类别分组标签"""
        categorized = defaultdict(list)
        for tag in tags:
            categorized[tag['tag_category']].append(tag)
        
        # 每个类别内按权重排序
        for cat in categorized:
            categorized[cat].sort(key=lambda t: t['weight'], reverse=True)
        
        return dict(categorized)
    
    def _identify_archetype(self, tags: List[Dict], 
                           formation_vector: Optional[FormationStateVector]) -> Optional[PersonalityArchetype]:
        """基于标签和状态向量识别人格原型"""
        tag_names = {t['tag_name'] for t in tags}
        
        scores = {}
        for archetype, rules in self.ARCHETYPE_RULES.items():
            score = 0
            
            # 检查必需标签
            required_met = all(req in tag_names for req in rules['required'])
            if not required_met:
                continue
            score += len(rules['required']) * 3
            
            # 检查偏好标签
            for pref in rules['preferred']:
                if pref in tag_names:
                    score += 2
            
            # 检查formation维度
            if formation_vector:
                for dim, (min_val, max_val) in rules.get('formation_prefs', {}).items():
                    if hasattr(formation_vector, dim):
                        val = getattr(formation_vector, dim)
                        if min_val <= val <= max_val:
                            score += 1.5
            
            scores[archetype] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _identify_dominant_loop(self, tags: List[Dict],
                               formation_vector: Optional[FormationStateVector]) -> Optional[str]:
        """识别主导循环"""
        tag_names = {t['tag_name'] for t in tags}
        
        # 基于标签识别
        loop_indicators = {
            'fear_control_loop': ['恐惧驱动', '控制型', '焦虑型', '压力下退缩'],
            'shame_avoidance_loop': ['羞愧型', '逃避型', '羞耻感', '情绪压抑型'],
            'pride_comparison_loop': ['骄傲驱动', '竞争型', '寻求认可型', '完美主义'],
            'desire_impulse_loop': ['欲望驱动', '冲动型', '容易放弃', '拖延型'],
            'truth_stability_loop': ['灵性清晰', '情绪稳定型', '真实导向', '成长导向'],
        }
        
        loop_scores = {}
        for loop, indicators in loop_indicators.items():
            score = sum(1 for ind in indicators if ind in tag_names)
            # 加权：高权重标签贡献更多
            for tag in tags:
                if tag['tag_name'] in indicators:
                    score += tag['weight'] * 0.5
            loop_scores[loop] = score
        
        # 基于formation向量验证
        if formation_vector:
            if formation_vector.fear_tendency > 0.6:
                loop_scores['fear_control_loop'] = loop_scores.get('fear_control_loop', 0) + 2
            if formation_vector.pride_tendency > 0.6:
                loop_scores['pride_comparison_loop'] = loop_scores.get('pride_comparison_loop', 0) + 2
            if formation_vector.spiritual_clarity > 0.65 and formation_vector.emotional_stability > 0.6:
                loop_scores['truth_stability_loop'] = loop_scores.get('truth_stability_loop', 0) + 2
        
        if loop_scores:
            best_loop = max(loop_scores.items(), key=lambda x: x[1])
            if best_loop[1] >= 2:  # 最低阈值
                return best_loop[0]
        
        return None
    
    def _determine_trajectory(self, tags: List[Dict],
                             formation_vector: Optional[FormationStateVector]) -> str:
        """确定轨迹方向"""
        trajectory_scores = {
            'stabilizing': 0,
            'fragmenting': 0,
            'improving_clarity': 0,
            'increasing_volatility': 0,
            'cyclical': 0,
        }
        
        tag_names = {t['tag_name'] for t in tags}
        
        # 基于标签
        if '情绪稳定型' in tag_names or '灵性成长型' in tag_names:
            trajectory_scores['stabilizing'] += 2
        if '情绪波动型' in tag_names or '焦虑型' in tag_names:
            trajectory_scores['increasing_volatility'] += 2
        if '灵性成长型' in tag_names or '感恩型' in tag_names:
            trajectory_scores['improving_clarity'] += 2
        if '迷茫型' in tag_names or '混乱依恋' in tag_names:
            trajectory_scores['fragmenting'] += 1
        
        # 基于formation向量
        if formation_vector:
            healthy_dims = sum([
                formation_vector.humility > 0.6,
                formation_vector.emotional_stability > 0.6,
                formation_vector.truth_alignment > 0.6,
                formation_vector.relational_health > 0.6,
                formation_vector.resilience > 0.6,
                formation_vector.spiritual_clarity > 0.6,
            ])
            unhealthy_dims = sum([
                formation_vector.fear_tendency > 0.6,
                formation_vector.pride_tendency > 0.6,
            ])
            
            if healthy_dims >= 4 and unhealthy_dims <= 1:
                trajectory_scores['improving_clarity'] += 2
            elif unhealthy_dims >= 2:
                trajectory_scores['fragmenting'] += 2
            elif healthy_dims >= 3:
                trajectory_scores['stabilizing'] += 1
        
        best = max(trajectory_scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else 'unknown'
    
    def _identify_life_dominant_domains(self, domain_tags: List[Dict]) -> List[str]:
        """识别生活主导领域"""
        if not domain_tags:
            return []
        
        # 提取领域名称（去掉"领域"后缀）
        domains = []
        for tag in domain_tags[:5]:  # 取前5
            name = tag['tag_name'].replace('领域', '').replace('型', '')
            domains.append({
                'domain': name,
                'weight': tag['weight'],
                'intensity': 'high' if tag['weight'] > 6 else 'medium' if tag['weight'] > 3 else 'low'
            })
        
        return domains
    
    def _identify_recurring_patterns(self, tags: List[Dict]) -> List[Dict]:
        """识别重复出现的模式"""
        patterns = []
        
        # 查找高频率、高权重的标签组合
        behavior_tags = [t for t in tags if t['tag_category'] == TagCategory.BEHAVIOR_PATTERN.value]
        emotion_tags = [t for t in tags if t['tag_category'] == TagCategory.EMOTION_TYPE.value]
        
        # 常见模式识别
        pattern_rules = [
            {
                'name': '压力-焦虑-逃避',
                'conditions': ['焦虑型', '压力下焦虑', '逃避型'],
                'category': 'stress_response',
            },
            {
                'name': '完美-拖延-自责',
                'conditions': ['完美主义', '拖延型', '自我批评型'],
                'category': 'perfectionism_trap',
            },
            {
                'name': '讨好-边界模糊-疲惫',
                'conditions': ['讨好型', '边界模糊型', '疲惫型'],
                'category': 'people_pleasing',
            },
            {
                'name': '控制-恐惧-孤独',
                'conditions': ['控制型', '恐惧驱动', '孤独型'],
                'category': 'control_fear',
            },
            {
                'name': '感恩-满足-成长',
                'conditions': ['感恩型', '满足型', '成长导向'],
                'category': 'gratitude_growth',
                'is_positive': True,
            },
        ]
        
        tag_names = {t['tag_name'] for t in tags}
        
        for rule in pattern_rules:
            matches = [c for c in rule['conditions'] if c in tag_names]
            if len(matches) >= 2:
                # 计算模式强度
                matched_tags = [t for t in tags if t['tag_name'] in matches]
                avg_weight = sum(t['weight'] for t in matched_tags) / len(matched_tags)
                
                patterns.append({
                    'pattern_name': rule['name'],
                    'category': rule['category'],
                    'matched_indicators': matches,
                    'strength': round(avg_weight, 2),
                    'is_positive': rule.get('is_positive', False),
                    'description': self._get_pattern_description(rule['category']),
                })
        
        # 按强度排序
        patterns.sort(key=lambda p: p['strength'], reverse=True)
        return patterns[:5]  # 返回前5个
    
    def _get_pattern_description(self, category: str) -> str:
        """获取模式描述"""
        descriptions = {
            'stress_response': '在压力下倾向于焦虑并选择逃避应对',
            'perfectionism_trap': '追求完美导致拖延，进而自我批评的循环',
            'people_pleasing': '过度讨好他人导致边界不清和身心疲惫',
            'control_fear': '因恐惧而控制，控制导致关系疏离',
            'gratitude_growth': '感恩带来满足感和持续成长',
        }
        return descriptions.get(category, '')
    
    def _identify_growth_indicators(self, tags: List[Dict],
                                   formation_vector: Optional[FormationStateVector]) -> List[str]:
        """识别成长指标"""
        indicators = []
        
        tag_names = {t['tag_name'] for t in tags}
        
        # 基于标签
        positive_tags = ['感恩型', '成长导向', '坚韧型', '寻求引导', '认罪悔改', '真实导向']
        for tag in positive_tags:
            if tag in tag_names:
                indicators.append(tag)
        
        # 基于formation向量
        if formation_vector:
            if formation_vector.humility > 0.6:
                indicators.append('谦逊成长')
            if formation_vector.truth_alignment > 0.6:
                indicators.append('真理对齐')
            if formation_vector.resilience > 0.6:
                indicators.append('韧性增强')
            if formation_vector.spiritual_clarity > 0.6:
                indicators.append('灵性清晰')
        
        return indicators[:5]
    
    def _identify_risk_factors(self, tags: List[Dict],
                              formation_vector: Optional[FormationStateVector]) -> List[str]:
        """识别风险因素"""
        risks = []
        
        tag_names = {t['tag_name'] for t in tags}
        
        # 高风险标签
        risk_tags = {
            '焦虑型': '持续焦虑状态',
            '抑郁型': '抑郁倾向',
            '恐惧驱动': '恐惧主导',
            '逃避型': '逃避模式',
            '自我批评型': '严厉自我批评',
            '边界模糊型': '边界问题',
            '控制型': '控制倾向',
        }
        
        for tag, description in risk_tags.items():
            if tag in tag_names:
                risks.append({'tag': tag, 'description': description})
        
        # 基于formation向量
        if formation_vector:
            if formation_vector.fear_tendency > 0.7:
                risks.append({'tag': '高恐惧倾向', 'description': '恐惧循环活跃'})
            if formation_vector.pride_tendency > 0.7:
                risks.append({'tag': '高骄傲倾向', 'description': '骄傲循环活跃'})
        
        return risks[:5]
    
    def _calculate_profile_stability(self, tags: List[Dict]) -> float:
        """计算画像稳定性"""
        if not tags:
            return 0.5
        
        # 高权重、多次出现的标签越多，画像越稳定
        stable_indicators = sum(1 for t in tags if t['weight'] >= 4 and t['occurrence_count'] >= 3)
        total = len(tags)
        
        stability = min(stable_indicators / max(total * 0.3, 3), 1.0)
        return round(stability, 2)
    
    def _calculate_change_velocity(self, tags: List[Dict]) -> float:
        """计算变化速度"""
        if not tags:
            return 0.0
        
        # 基于新兴标签数量和新近更新频率
        now = datetime.utcnow()
        recent_updates = 0
        
        for tag in tags:
            last_seen = tag.get('last_seen_at')
            if last_seen:
                if isinstance(last_seen, str):
                    last_seen = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                if (now - last_seen).days <= 7:
                    recent_updates += 1
        
        velocity = recent_updates / max(len(tags) * 0.2, 2)
        return round(min(velocity, 1.0), 2)
    
    def _determine_trend_direction(self, tags: List[Dict],
                                  formation_vector: Optional[FormationStateVector]) -> str:
        """确定趋势方向"""
        # 基于标签变化趋势
        positive_count = sum(1 for t in tags if t['tag_name'] in 
                           ['感恩型', '成长导向', '灵性清晰', '坚韧型'])
        negative_count = sum(1 for t in tags if t['tag_name'] in 
                           ['焦虑型', '抑郁型', '恐惧驱动', '逃避型'])
        
        if positive_count > negative_count * 1.5:
            return 'improving'
        elif negative_count > positive_count * 1.5:
            return 'declining'
        elif self._calculate_change_velocity(tags) > 0.5:
            return 'volatile'
        else:
            return 'stable'
    
    def _format_top_tags(self, tags: List[Dict], limit: int) -> List[Dict]:
        """格式化顶部标签"""
        return [
            {
                'name': t['tag_name'],
                'weight': round(t['weight'], 2),
                'confidence': t['confidence'],
                'occurrences': t['occurrence_count'],
            }
            for t in tags[:limit]
        ]
    
    def _generate_narrative(self, archetype: Optional[PersonalityArchetype],
                         dominant_loop: Optional[str],
                         trajectory: str,
                         categorized_tags: Dict,
                         formation_vector: Optional[FormationStateVector]) -> Tuple[str, str, str]:
        """生成画像叙事描述"""
        
        # 核心画像摘要
        parts = []
        
        if archetype:
            parts.append(f"你是一个{archetype.value}型的人")
        
        if dominant_loop:
            loop_desc = {
                'fear_control_loop': '在恐惧与控制之间寻找平衡',
                'shame_avoidance_loop': '正在学习面对羞耻而非逃避',
                'pride_comparison_loop': '在比较中寻求真实的自我价值',
                'desire_impulse_loop': '在欲望与节制之间成长',
                'truth_stability_loop': '在真理中找到稳定的力量',
            }.get(dominant_loop, '')
            if loop_desc:
                parts.append(loop_desc)
        
        # 主导情绪
        emotion_tags = categorized_tags.get(TagCategory.EMOTION_TYPE.value, [])
        if emotion_tags:
            top_emotion = emotion_tags[0]['tag_name']
            parts.append(f"常体验{top_emotion}情绪")
        
        summary = '。'.join(parts) + '。' if parts else '正在形成中的独特人格'
        
        # 核心生命叙事
        narrative_parts = []
        
        # 基于主导循环构建叙事
        if dominant_loop and dominant_loop in self.GROWTH_PATHWAYS:
            pathway_info = self.GROWTH_PATHWAYS[dominant_loop]
            narrative_parts.append(f"你的生命故事围绕着{pathway_info['pattern']}展开。")
            narrative_parts.append(pathway_info['description'])
        
        # 加入轨迹描述
        trajectory_desc = {
            'stabilizing': '你正走在稳定整合的道路上',
            'improving_clarity': '你的灵性视野日益清晰',
            'fragmenting': '你正处于需要重新整合的季节',
            'increasing_volatility': '你正在经历较多波动的时期',
            'cyclical': '你的生命呈现周期性模式',
        }.get(trajectory, '你的轨迹正在形成中')
        
        narrative_parts.append(trajectory_desc)
        
        # 加入优势领域
        domain_tags = categorized_tags.get(TagCategory.LIFE_DOMAIN.value, [])
        if domain_tags:
            top_domain = domain_tags[0]['tag_name'].replace('领域', '')
            narrative_parts.append(f"在{top_domain}领域有深刻体验。")
        
        narrative = ' '.join(narrative_parts)
        
        # 成长路径建议
        pathway_parts = []
        
        if dominant_loop and dominant_loop in self.GROWTH_PATHWAYS:
            info = self.GROWTH_PATHWAYS[dominant_loop]
            pathway_parts.append(f"成长焦点：{', '.join(info['growth_focus'])}。")
            pathway_parts.append(f"建议实践：{', '.join(info['suggested_practices'])}。")
        
        # 基于轨迹的建议
        if trajectory == 'improving_clarity':
            pathway_parts.append("继续深化真理内化和感恩练习。")
        elif trajectory == 'fragmenting':
            pathway_parts.append("建议寻求导师陪伴，建立稳定属灵节奏。")
        elif trajectory == 'stabilizing':
            pathway_parts.append("可以开始帮助有类似挣扎的人。")
        
        pathway = ' '.join(pathway_parts)
        
        return summary, narrative, pathway


# ==================== 全局实例 ====================

# 标签提取器实例
tag_extractor = TagExtractor()

# 标签存储实例（需要初始化）
_tag_store: Optional[UserTagStore] = None
_profile_engine: Optional[PersonalityProfileEngine] = None


def init_profile_system(db_pool=None, use_memory: bool = False):
    """初始化人格画像系统"""
    global _tag_store, _profile_engine
    
    _tag_store = UserTagStore(db_pool, use_memory=use_memory)
    _profile_engine = PersonalityProfileEngine(_tag_store)
    
    print('[profile_system] User Personality Profile System initialized', flush=True)
    return _tag_store, _profile_engine


def get_tag_store() -> Optional[UserTagStore]:
    """获取标签存储实例"""
    return _tag_store


def get_profile_engine() -> Optional[PersonalityProfileEngine]:
    """获取画像生成引擎"""
    return _profile_engine


def extract_and_store_tags(user_id: str, data: Dict[str, Any], 
                          source_type: str, event_id: Optional[str] = None) -> List[str]:
    """
    便捷函数：从数据中提取并存储标签
    
    Args:
        user_id: 用户ID
        data: 原始数据
        source_type: 来源类型 (emotion_checkin, decision_event, habit_execution, etc.)
        event_id: 事件ID
    
    Returns:
        存储的标签ID列表
    """
    if not _tag_store:
        raise RuntimeError("Profile system not initialized. Call init_profile_system() first.")
    
    # 根据来源类型选择提取方法
    source_map = {
        'emotion_checkin': (TagSource.EMOTION_CHECKIN, tag_extractor.extract_from_emotion_checkin),
        'decision_event': (TagSource.DECISION_EVENT, tag_extractor.extract_from_decision),
        'habit_execution': (TagSource.HABIT_EXECUTION, tag_extractor.extract_from_habit),
        'formation_analysis': (TagSource.FORMATION_ANALYSIS, tag_extractor.extract_from_formation),
    }
    
    if source_type in source_map:
        source, extract_func = source_map[source_type]
        result = extract_func(data)
    else:
        # 通用文本提取
        text = json.dumps(data) if isinstance(data, dict) else str(data)
        result = TagExtractionResult(
            tags=tag_extractor.extract_from_text(text, TagSource.SYSTEM_INFERRED),
            source_type=source_type
        )
    
    # 存储标签
    source_event = {'type': source_type, 'id': event_id} if event_id else None
    return _tag_store.add_or_update_tags(user_id, result.tags, source_event)


def generate_user_profile(user_id: str, 
                         formation_vector: Optional[Dict] = None) -> Dict[str, Any]:
    """
    便捷函数：生成用户人格画像
    
    Args:
        user_id: 用户ID
        formation_vector: 8维状态向量字典（可选）
    
    Returns:
        人格画像字典
    """
    if not _profile_engine:
        raise RuntimeError("Profile system not initialized. Call init_profile_system() first.")
    
    vector = None
    if formation_vector:
        vector = FormationStateVector.from_dict(formation_vector)
    
    profile = _profile_engine.generate_profile(user_id, vector)
    return profile.to_dict()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 内存模式测试
    init_profile_system(use_memory=True)
    
    # 测试数据
    test_checkin = {
        'emotionLabel': '焦虑',
        'emotionQuery': '最近工作压力很大，感觉很焦虑，晚上睡不着',
        'scenarioCategory': '工作',
        'scenarioDetail': '项目 deadline 临近',
        'driverType': '恐惧',
        'driverOption': '害怕失败',
        'mood': '疲惫',
        'prayerRequest': '求神给我平安和智慧处理工作',
    }
    
    # 提取标签
    result = tag_extractor.extract_from_emotion_checkin(test_checkin)
    print(f"提取到 {len(result.tags)} 个标签:")
    for tag in result.tags[:10]:
        print(f"  - {tag['tag_name']} ({tag['tag_category']}): 置信度 {tag['confidence']}")
    
    # 存储标签
    user_id = "test_user_001"
    tag_ids = extract_and_store_tags(user_id, test_checkin, 'emotion_checkin', 'evt_001')
    print(f"\n存储了 {len(tag_ids)} 个标签")
    
    # 获取标签洞察
    insights = _tag_store.get_tag_insights(user_id)
    print(f"\n标签洞察: {json.dumps(insights, indent=2, ensure_ascii=False)}")
    
    # 生成画像
    formation_vector = {
        'humility': 0.6,
        'fear_tendency': 0.7,
        'pride_tendency': 0.4,
        'emotional_stability': 0.5,
        'truth_alignment': 0.6,
        'relational_health': 0.5,
        'resilience': 0.6,
        'spiritual_clarity': 0.5,
    }
    
    profile = generate_user_profile(user_id, formation_vector)
    print(f"\n人格画像:")
    print(f"  原型: {profile.get('personality_archetype')}")
    print(f"  主导循环: {profile.get('dominant_loop')}")
    print(f"  轨迹方向: {profile.get('trajectory_direction')}")
    print(f"  摘要: {profile.get('profile_summary')}")
    print(f"  叙事: {profile.get('core_narrative')}")
    print(f"  成长路径: {profile.get('growth_pathway')}")
