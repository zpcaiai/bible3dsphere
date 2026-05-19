#!/usr/bin/env python3
"""
决策支撑系统 (Spiritual Formation & Discernment System - SFDS)
帮助用户做出符合基督品格的决策
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import hashlib

# Database imports
from contextlib import contextmanager

# FastAPI imports
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Import the reflective discernment engine (V1 + V2)
from discernment_engine import (
    DiscernmentEngine as ReflectiveEngine,
    DiscernmentEngineV2,
    DecisionEvent as EngineDecision,
    EmotionalState as EngineEmotion,
    MotiveProfile as EngineMotive,
    SpiritualPrinciple as EnginePrinciple,
    format_result as format_engine_result,
    format_v2_result,
)
from graph_layer import GraphEngine, GraphService, get_neo4j, get_graph_service
from temporal_engine import TemporalEngine, TemporalDataAccess
from formation_pipeline import FormationPipeline, PipelineInput, init_pipeline, get_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sfds", tags=["decision_support"])

# ==================== ENUMS ====================

# ==================== 现代生活决策类别（21类，覆盖人生主要领域）====================
class DecisionCategory(str, Enum):
    # 职业与发展
    CAREER = "career"                    # 职业/工作
    EDUCATION = "education"              # 教育/学习
    CALLING = "calling"                  # 呼召/使命
    
    # 人际关系
    RELATIONSHIP = "relationship"        # 人际关系
    FAMILY = "family"                    # 家庭/亲子
    COMMUNITY = "community"              # 社群/教会
    
    # 资源管理
    FINANCIAL = "financial"              # 财务/金钱
    HOUSING = "housing"                  # 居住/房产
    POSSESSIONS = "possessions"          # 物品/消费
    
    # 身心健康
    HEALTH = "health"                    # 健康/身体
    MENTAL = "mental"                    # 心理/情绪
    
    # 灵性与道德
    TEMPTATION = "temptation"            # 试探/诱惑
    SPIRITUAL = "spiritual"              # 灵修/信仰
    MINISTRY = "ministry"                # 事工/服事
    
    # 时间与生活方式
    TIME = "time"                        # 时间/节奏
    LIFESTYLE = "lifestyle"              # 生活方式
    BOUNDARY = "boundary"                # 边界/拒绝
    
    # 危机与转变
    CRISIS = "crisis"                    # 危机/急难
    TRANSITION = "transition"          # 转变/过渡
    LOSS = "loss"                        # 失落/哀伤
    
    # 社会与文化
    ETHICS = "ethics"                    # 伦理/正义
    MEDIA = "media"                      # 媒体/信息
    OTHER = "other"                      # 其他/独特

class MotiveType(str, Enum):
    FEAR = "fear"
    PRIDE = "pride"
    LOVE = "love"
    DESIRE = "desire"
    DUTY = "duty"
    AMBITION = "ambition"

class DiscernmentSource(str, Enum):
    HOLY_SPIRIT = "holy_spirit"
    CONSCIENCE = "conscience"
    FEAR_RESPONSE = "fear_response"
    PRIDE_RESPONSE = "pride_response"
    TRAUMA_RESPONSE = "trauma_response"
    WORLDLY_VALUE = "worldly_value"
    FLESH_DESIRE = "flesh_desire"
    UNCERTAIN = "uncertain"

class GuidancePriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# ==================== PYDANTIC MODELS ====================

# ==================== 扩展状态快照（12维度，覆盖身心灵社智财道）====================
class StateSnapshot(BaseModel):
    """用户状态快照 — 12维度现代生活完整画像"""
    # 基础5维度（身心灵核心）
    stress_level: int = Field(ge=0, le=10, default=5, description="压力水平 0-10：外部要求与内部资源的差距")
    anxiety_level: int = Field(ge=0, le=10, default=5, description="焦虑水平 0-10：对未来不确定的担忧程度")
    fatigue_level: int = Field(ge=0, le=10, default=5, description="疲劳水平 0-10：身心能量耗竭的感受")
    spiritual_dryness: int = Field(ge=0, le=10, default=5, description="灵性干涸 0-10：与神连接的感受减弱")
    emotional_stability: int = Field(ge=0, le=10, default=5, description="情绪稳定性 0-10：情绪波动的可控程度")
    
    # 扩展7维度（现代生活全景）
    physical_health: int = Field(ge=0, le=10, default=5, description="身体健康 0-10：身体状况与精力水平")
    sleep_quality: int = Field(ge=0, le=10, default=5, description="睡眠质量 0-10：休息恢复与睡眠满意度")
    social_connection: int = Field(ge=0, le=10, default=5, description="社交连接 0-10：关系网络与支持系统")
    financial_pressure: int = Field(ge=0, le=10, default=5, description="财务压力 0-10：经济焦虑与资源担忧")
    cognitive_clarity: int = Field(ge=0, le=10, default=5, description="认知清晰 0-10：思维清晰度与专注力")
    identity_confusion: int = Field(ge=0, le=10, default=5, description="身份困惑 0-10：自我认知与定位迷茫")
    moral_tension: int = Field(ge=0, le=10, default=5, description="道德张力 0-10：价值观冲突与良心挣扎")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EmotionLog(BaseModel):
    """情绪记录"""
    emotion_type: str
    intensity: int = Field(ge=0, le=10)
    trigger: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MotiveAnalysis(BaseModel):
    """动机分析"""
    fear_driven_score: float = Field(ge=0, le=1, description="恐惧驱动程度")
    pride_driven_score: float = Field(ge=0, le=1, description="骄傲驱动程度")
    love_driven_score: float = Field(ge=0, le=1, description="爱驱动程度")
    desire_driven_score: float = Field(ge=0, le=1, description="欲望驱动程度")
    dominant_motive: MotiveType
    secondary_motive: Optional[MotiveType] = None
    analysis_notes: Optional[str] = None

class DiscernmentResult(BaseModel):
    """辨识结果"""
    primary_source: DiscernmentSource
    secondary_source: Optional[DiscernmentSource] = None
    confidence: float = Field(ge=0, le=1, description="置信度")
    explanation: str
    biblical_alignment: float = Field(ge=0, le=1)
    long_term_fruit_score: float = Field(ge=-1, le=1, description="长期果实预测 -1负面到1正面")

class GuidanceOutput(BaseModel):
    """指导输出"""
    structured_advice: str
    risks: List[str]
    alternative_interpretations: List[str]
    recommended_actions: List[str]
    priority: GuidancePriority
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DecisionEventCreate(BaseModel):
    """创建决策事件"""
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category: DecisionCategory
    urgency: int = Field(ge=1, le=5, description="紧急程度 1-5")
    importance: int = Field(ge=1, le=5, description="重要程度 1-5")
    state_snapshot: StateSnapshot
    emotion_logs: List[EmotionLog] = []
    context_factors: Optional[Dict[str, Any]] = None

class DecisionEventResponse(BaseModel):
    """决策事件响应"""
    id: str
    title: str
    description: Optional[str]
    category: DecisionCategory
    urgency: int
    importance: int
    state_snapshot: StateSnapshot
    emotion_logs: List[EmotionLog]
    motive_analysis: Optional[MotiveAnalysis]
    discernment_result: Optional[DiscernmentResult]
    guidance: Optional[GuidanceOutput]
    created_at: datetime
    updated_at: datetime
    status: str

class ReviewLogCreate(BaseModel):
    """回顾记录创建"""
    decision_id: str
    outcome_description: str
    peace_level: int = Field(ge=-5, le=5, description="平安感 -5后悔到5极大平安")
    regret_level: int = Field(ge=0, le=10)
    lessons_learned: Optional[str] = None
    character_impact: Optional[str] = None

class SpiritualPrinciple(BaseModel):
    """灵性原则"""
    id: str
    principle_text: str
    scripture_reference: Optional[str]
    category: str
    embedding: Optional[List[float]] = None

# ==================== SPIRITUAL PRINCIPLES DATA ====================

DEFAULT_SPIRITUAL_PRINCIPLES = [
    {"id": "1", "principle_text": "凡事察验，善美的要持守", "scripture_reference": "帖撒罗尼迦前书5:21", "category": "discernment"},
    {"id": "2", "principle_text": "你要保守你心，胜过保守一切", "scripture_reference": "箴言4:23", "category": "heart_guarding"},
    {"id": "3", "principle_text": "不要恐惧，因为我与你同在", "scripture_reference": "以赛亚书41:10", "category": "fear"},
    {"id": "4", "principle_text": "看别人比自己强", "scripture_reference": "腓立比书2:3", "category": "humility"},
    {"id": "5", "principle_text": "凭果子认出他们来", "scripture_reference": "马太福音7:20", "category": "fruit"},
    {"id": "6", "principle_text": "爱比成功更高", "scripture_reference": "哥林多前书13:1-3", "category": "love"},
    {"id": "7", "principle_text": "真理比舒适更重要", "scripture_reference": "约翰福音8:32", "category": "truth"},
    {"id": "8", "principle_text": "谦卑在智慧以先", "scripture_reference": "箴言11:2", "category": "wisdom"},
    {"id": "9", "principle_text": "安息是属灵操练", "scripture_reference": "马可福音6:31", "category": "rest"},
    {"id": "10", "principle_text": "顺服神，不顺从人", "scripture_reference": "使徒行传5:29", "category": "obedience"},
    {"id": "11", "principle_text": "愿意受苦而不愿犯罪", "scripture_reference": "希伯来书11:25", "category": "sacrifice"},
    {"id": "12", "principle_text": "患难生忍耐，忍耐生老练", "scripture_reference": "罗马书5:3-4", "category": "patience"},
    {"id": "13", "principle_text": "不可为恶所胜，反要以善胜恶", "scripture_reference": "罗马书12:21", "category": "victory"},
    {"id": "14", "principle_text": "在压力中保持平安", "scripture_reference": "约翰福音14:27", "category": "peace"},
    {"id": "15", "principle_text": "不为明天忧虑", "scripture_reference": "马太福音6:34", "category": "anxiety"},
]

# ==================== CORE DISCERNMENT ENGINE ====================

class DiscernmentEngine:
    """辨识引擎 - 核心决策分析逻辑"""
    
    @staticmethod
    def analyze_motives(state: StateSnapshot, emotions: List[EmotionLog], context: Dict) -> MotiveAnalysis:
        """分析动机 - 恐惧、骄傲、爱、欲望的比例"""
        
        # 基于状态快照计算
        fear_score = min(1.0, (state.anxiety_level + state.stress_level) / 15)
        pride_score = 0.3  # 基础值，需要更多上下文判断
        love_score = 0.5  # 基础值
        desire_score = 0.4  # 基础值
        
        # 基于情绪调整 — 覆盖 MVFE 提取的全部情绪类型
        for emotion in emotions:
            if emotion.emotion_type in ["fear", "anxiety", "worry", "panic"]:
                fear_score = min(1.0, fear_score + emotion.intensity / 10)
            elif emotion.emotion_type in ["anger", "frustration", "irritation", "disgust"]:
                pride_score = min(1.0, pride_score + emotion.intensity / 15)
            elif emotion.emotion_type in ["joy", "peace", "love", "gratitude", "hope"]:
                love_score = min(1.0, love_score + emotion.intensity / 10)
            elif emotion.emotion_type in ["desire", "longing", "craving", "lust", "envy"]:
                desire_score = min(1.0, desire_score + emotion.intensity / 10)
            elif emotion.emotion_type in ["shame", "guilt"]:
                fear_score = min(1.0, fear_score + emotion.intensity / 12)
                desire_score = min(1.0, desire_score + emotion.intensity / 20)
            elif emotion.emotion_type in ["sadness", "loneliness"]:
                fear_score = min(1.0, fear_score + emotion.intensity / 15)
                love_score = max(0.0, love_score - emotion.intensity / 20)
            elif emotion.emotion_type == "confusion":
                fear_score = min(1.0, fear_score + emotion.intensity / 20)
            elif emotion.emotion_type == "surprise":
                pass  # 惊讶是中性的，不单独影响动机
        
        # 确定主导动机
        scores = {
            MotiveType.FEAR: fear_score,
            MotiveType.PRIDE: pride_score,
            MotiveType.LOVE: love_score,
            MotiveType.DESIRE: desire_score,
        }
        
        dominant = max(scores, key=scores.get)
        secondary = None
        
        # 找第二高的
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_scores) > 1 and sorted_scores[1][1] > 0.3:
            secondary = sorted_scores[1][0]
        
        return MotiveAnalysis(
            fear_driven_score=fear_score,
            pride_driven_score=pride_score,
            love_driven_score=love_score,
            desire_driven_score=desire_score,
            dominant_motive=dominant,
            secondary_motive=secondary,
            analysis_notes=f"主导动机: {dominant.value}, 恐惧指数: {fear_score:.2f}"
        )
    
    @staticmethod
    def discern_source(motive: MotiveAnalysis, state: StateSnapshot) -> DiscernmentResult:
        """辨识来源 - 圣灵、创伤、恐惧、骄傲等"""
        
        # 规则引擎
        if motive.fear_driven_score > 0.6:
            source = DiscernmentSource.FEAR_RESPONSE
            confidence = motive.fear_driven_score
            explanation = "决策明显受恐惧驱动。恐惧驱动的决定往往导致逃避或过度控制，而非信心。"
            long_term_fruit = -0.4
            
        elif motive.pride_driven_score > 0.6:
            source = DiscernmentSource.PRIDE_RESPONSE
            confidence = motive.pride_driven_score
            explanation = "决策明显受骄傲驱动。骄傲驱动的决定往往追求外在认可而非内在平安。"
            long_term_fruit = -0.3
            
        elif motive.love_driven_score > 0.7 and motive.fear_driven_score < 0.3:
            source = DiscernmentSource.HOLY_SPIRIT
            confidence = motive.love_driven_score * 0.8
            explanation = "决策由爱与平安驱动，与圣灵的果子相符。决策包含为他人益处考虑。"
            long_term_fruit = 0.7
            
        elif state.spiritual_dryness > 6:
            source = DiscernmentSource.TRAUMA_RESPONSE
            confidence = min(1.0, state.spiritual_dryness / 10)
            explanation = "灵性干涸期做出的决策容易受创伤模式影响。建议先恢复灵性健康。"
            long_term_fruit = -0.2
            
        elif motive.desire_driven_score > 0.6:
            source = DiscernmentSource.FLESH_DESIRE
            confidence = motive.desire_driven_score
            explanation = "决策明显受肉体欲望驱动。这种决定往往带来短期满足但长期后悔。"
            long_term_fruit = -0.5
            
        else:
            source = DiscernmentSource.UNCERTAIN
            confidence = 0.5
            explanation = "动机混合，难以明确辨识。建议延迟决策，寻求更多祷告和辅导。"
            long_term_fruit = 0.0
        
        # 根据状态稳定性调整
        if state.emotional_stability < 4:
            confidence *= 0.7
            explanation += " 情绪不稳定期，决策质量可能受影响。"
            long_term_fruit -= 0.2
        
        return DiscernmentResult(
            primary_source=source,
            confidence=round(confidence, 2),
            explanation=explanation,
            biblical_alignment=0.6 if source == DiscernmentSource.HOLY_SPIRIT else 0.3,
            long_term_fruit_score=round(long_term_fruit, 2)
        )
    
    @staticmethod
    def generate_guidance(
        decision: DecisionEventCreate,
        motive: MotiveAnalysis,
        discernment: DiscernmentResult,
        principles: List[SpiritualPrinciple]
    ) -> GuidanceOutput:
        """生成指导建议"""
        
        risks = []
        alternatives = []
        actions = []
        priority = GuidancePriority.MEDIUM
        
        # 根据辨识结果生成建议
        if discernment.primary_source == DiscernmentSource.FEAR_RESPONSE:
            risks = [
                "逃避可能使问题恶化",
                "恐惧中的决定往往过度保守",
                "可能错过神的预备"
            ]
            alternatives = [
                "这可能是信心的试炼而非危险信号",
                "恐惧往往放大风险，实际后果可能没那么严重",
                "考虑如果完全不怕，你会如何选择"
            ]
            actions = [
                "暂停24-48小时，等情绪平复",
                "与信任的属灵同伴讨论",
                "背诵相关经文对抗恐惧",
                "写下最坏的后果，评估是否可承受"
            ]
            priority = GuidancePriority.HIGH
            
        elif discernment.primary_source == DiscernmentSource.PRIDE_RESPONSE:
            risks = [
                "为维护面子而坚持错误决定",
                "忽视他人合理建议",
                "成功后骄傲更加膨胀"
            ]
            alternatives = [
                "放下需要被认可的渴望",
                "考虑如果无人知晓你的选择，你会怎么做",
                "神看重的品格而非成就"
            ]
            actions = [
                "寻求你最尊重的人的诚实反馈",
                "练习说出'我不知道'",
                "默想耶稣虚己的榜样"
            ]
            priority = GuidancePriority.HIGH
            
        elif discernment.primary_source == DiscernmentSource.HOLY_SPIRIT:
            risks = [
                "即使感动也要验证实际可行性",
                "注意区分圣灵的感动与自己的兴奋",
                "属灵冲动也需要智慧执行"
            ]
            alternatives = [
                "这是方向确认而非细节的命令",
                "保持开放，神可能调整方式",
                "圣灵的感动通常伴随平安而非焦虑"
            ]
            actions = [
                "记录这次感动，便于日后回顾",
                "与属灵导师分享寻求印证",
                "制定实际可行的步骤计划",
                "预备面对可能的反对"
            ]
            priority = GuidancePriority.MEDIUM
            
        else:  # 不确定或其他
            risks = [
                "匆忙决定可能带来后悔",
                "混杂动机导致复杂后果",
                "当下最优可能非长期最优"
            ]
            alternatives = [
                "延迟决定直到获得更清晰的确信",
                "考虑咨询专业人士或属灵导师",
                "从圣经中寻找类似处境的智慧"
            ]
            actions = [
                "为自己设定决策截止日期",
                "收集更多信息",
                "列出赞成与反对的理由",
                "寻求来自不同视角的建议"
            ]
        
        # 根据紧急度调整
        if decision.urgency >= 4:
            priority = GuidancePriority.HIGH
            actions.insert(0, "⚠️ 紧急决策：在有限时间内尽力寻求属灵遮盖")
        
        advice = f"""
基于当前状态分析：
- 主导动机：{motive.dominant_motive.value}
- 决策来源：{discernment.primary_source.value}
- 长期果实预测：{discernment.long_term_fruit_score:+.1f}（负值表示可能带来问题）

{discernment.explanation}
""".strip()
        
        return GuidanceOutput(
            structured_advice=advice,
            risks=risks,
            alternative_interpretations=alternatives,
            recommended_actions=actions,
            priority=priority
        )

# ==================== DATABASE FUNCTIONS ====================

class SFDSStorage:
    """数据库存储层 (psycopg2 ThreadedConnectionPool)"""

    def __init__(self, db_pool):
        self.db = db_pool

    def _getconn(self):
        conn = self.db.getconn()
        if conn.closed:
            self.db.putconn(conn, close=True)
            conn = self.db.getconn()
        return conn

    def _putconn(self, conn):
        if conn and not conn.closed:
            try:
                conn.rollback()
            except Exception:
                pass
            self.db.putconn(conn)

    # ── sync helpers (run via asyncio.to_thread from async endpoints) ──

    def _create_decision_event_sync(self, user_id: str, decision: DecisionEventCreate) -> str:
        decision_id = str(uuid.uuid4())
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sfds_decision_events
                    (id, user_id, title, description, category, urgency, importance,
                     stress_level, anxiety_level, fatigue_level, spiritual_dryness, emotional_stability,
                     physical_health, sleep_quality, social_connection, financial_pressure,
                     cognitive_clarity, identity_confusion, moral_tension,
                     emotion_logs, context_factors, status, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
                """, (
                    decision_id, user_id, decision.title, decision.description,
                    decision.category.value, decision.urgency, decision.importance,
                    decision.state_snapshot.stress_level,
                    decision.state_snapshot.anxiety_level,
                    decision.state_snapshot.fatigue_level,
                    decision.state_snapshot.spiritual_dryness,
                    decision.state_snapshot.emotional_stability,
                    decision.state_snapshot.physical_health,
                    decision.state_snapshot.sleep_quality,
                    decision.state_snapshot.social_connection,
                    decision.state_snapshot.financial_pressure,
                    decision.state_snapshot.cognitive_clarity,
                    decision.state_snapshot.identity_confusion,
                    decision.state_snapshot.moral_tension,
                    json.dumps([e.dict() for e in decision.emotion_logs], default=str),
                    json.dumps(decision.context_factors, default=str) if decision.context_factors else None,
                    "analyzing",
                ))
                conn.commit()
        finally:
            self._putconn(conn)
        return decision_id

    def _update_motive_analysis_sync(self, decision_id: str, analysis: MotiveAnalysis):
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sfds_decision_events
                    SET motive_analysis = %s, updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(analysis.dict(), default=str), decision_id))
                conn.commit()
        finally:
            self._putconn(conn)

    def _update_discernment_result_sync(self, decision_id: str, result: DiscernmentResult):
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sfds_decision_events
                    SET discernment_result = %s, updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(result.dict(), default=str), decision_id))
                conn.commit()
        finally:
            self._putconn(conn)

    def _update_guidance_sync(self, decision_id: str, guidance: GuidanceOutput):
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE sfds_decision_events
                    SET guidance = %s, status = 'guided', updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(guidance.dict(), default=str), decision_id))
                conn.commit()
        finally:
            self._putconn(conn)

    def _get_user_decisions_sync(self, user_id: str, limit: int = 20) -> List[Dict]:
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM sfds_decision_events
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                if not cur.description:
                    return []
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._putconn(conn)

    def _get_decision_by_id_sync(self, decision_id: str) -> Optional[Dict]:
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sfds_decision_events WHERE id = %s", (decision_id,))
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
        finally:
            self._putconn(conn)

    def _create_review_log_sync(self, user_id: str, review: ReviewLogCreate) -> str:
        review_id = str(uuid.uuid4())
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sfds_review_logs
                    (id, user_id, decision_id, outcome_description, peace_level,
                     regret_level, lessons_learned, character_impact, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())
                """, (
                    review_id, user_id, review.decision_id, review.outcome_description,
                    review.peace_level, review.regret_level, review.lessons_learned,
                    review.character_impact,
                ))
                cur.execute("""
                    UPDATE sfds_decision_events
                    SET status = 'reviewed', updated_at = NOW()
                    WHERE id = %s
                """, (review.decision_id,))
                conn.commit()
        finally:
            self._putconn(conn)
        return review_id

    # ── async wrappers ──

    async def create_decision_event(self, user_id: str, decision: DecisionEventCreate) -> str:
        return await asyncio.to_thread(self._create_decision_event_sync, user_id, decision)

    async def update_motive_analysis(self, decision_id: str, analysis: MotiveAnalysis):
        await asyncio.to_thread(self._update_motive_analysis_sync, decision_id, analysis)

    async def update_discernment_result(self, decision_id: str, result: DiscernmentResult):
        await asyncio.to_thread(self._update_discernment_result_sync, decision_id, result)

    async def update_guidance(self, decision_id: str, guidance: GuidanceOutput):
        await asyncio.to_thread(self._update_guidance_sync, decision_id, guidance)

    async def get_user_decisions(self, user_id: str, limit: int = 20) -> List[Dict]:
        return await asyncio.to_thread(self._get_user_decisions_sync, user_id, limit)

    async def get_decision_by_id(self, decision_id: str) -> Optional[Dict]:
        return await asyncio.to_thread(self._get_decision_by_id_sync, decision_id)

    async def create_review_log(self, user_id: str, review: ReviewLogCreate):
        return await asyncio.to_thread(self._create_review_log_sync, user_id, review)

# ==================== API ENDPOINTS ====================

# 全局存储实例（需要在main.py中初始化）
sfds_storage: Optional[SFDSStorage] = None
discernment_engine = DiscernmentEngine()

def init_sfds_storage(db_pool):
    """初始化存储"""
    global sfds_storage
    sfds_storage = SFDSStorage(db_pool)

@router.post("/decisions", response_model=Dict[str, str])
async def create_decision(
    decision: DecisionEventCreate,
    background_tasks: BackgroundTasks,
    user_id: str = "current_user"  # 实际应从token获取
):
    """创建新的决策事件并进行分析"""
    if not sfds_storage:
        raise HTTPException(status_code=500, detail="SFDS storage not initialized")
    
    try:
        # 创建决策记录
        decision_id = await sfds_storage.create_decision_event(user_id, decision)
    except Exception as exc:
        print(f'[SFDS] create_decision_event failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail=f"决策创建失败: {exc}")
    
    # 同步执行分析（计算量小，无需后台任务）
    try:
        await analyze_decision_background(decision_id, decision, user_id)
    except Exception as exc:
        print(f'[SFDS] analyze_decision inline failed: {exc}', flush=True)
    
    return {"id": decision_id, "status": "analyzing", "message": "决策分析进行中，请稍后查看结果"}

async def analyze_decision_background(decision_id: str, decision: DecisionEventCreate, user_id: str = "current_user"):
    """后台分析决策"""
    try:
        # 1. 动机分析
        motive = discernment_engine.analyze_motives(
            decision.state_snapshot,
            decision.emotion_logs,
            decision.context_factors or {}
        )
        await sfds_storage.update_motive_analysis(decision_id, motive)
        
        # 2. 来源辨识
        discernment = discernment_engine.discern_source(
            motive,
            decision.state_snapshot
        )
        await sfds_storage.update_discernment_result(decision_id, discernment)
        
        # 3. 生成指导（简化版，实际应使用向量检索）
        principles = [SpiritualPrinciple(**p) for p in DEFAULT_SPIRITUAL_PRINCIPLES]
        guidance = discernment_engine.generate_guidance(
            decision,
            motive,
            discernment,
            principles
        )
        await sfds_storage.update_guidance(decision_id, guidance)

        # 4. 桥接 SFDS Formation Pipeline — 让辨识结果也更新 8维人格向量
        try:
            pipeline = get_pipeline()
            if pipeline:
                # user_id comes from the endpoint caller
                inp = PipelineInput(
                    user_id=user_id,
                    decision_id=decision_id,
                    title=decision.title,
                    description=decision.description or "",
                    category=decision.category.value,
                    urgency=decision.urgency,
                    importance=decision.importance,
                    anxiety_level=decision.state_snapshot.anxiety_level,
                    peace_level=max(0, 10 - decision.state_snapshot.anxiety_level),
                    clarity_level=max(0, 10 - decision.state_snapshot.spiritual_dryness),
                    spiritual_dryness=decision.state_snapshot.spiritual_dryness,
                    emotional_stability=decision.state_snapshot.emotional_stability,
                    decision_confidence=5,
                    stress_level=decision.state_snapshot.stress_level,
                    fatigue_level=decision.state_snapshot.fatigue_level,
                    emotions=[{
                        "type": e.emotion_type,
                        "intensity": e.intensity,
                        "trigger": e.trigger,
                    } for e in decision.emotion_logs],
                    motive_scores={
                        "fear": motive.fear_driven_score,
                        "pride": motive.pride_driven_score,
                        "love": motive.love_driven_score,
                        "desire": motive.desire_driven_score,
                    },
                    semantic_principles=[
                        {
                            "id": p["id"],
                            "principle_text": p["principle_text"],
                            "scripture_reference": p.get("scripture_reference", ""),
                            "category": p["category"],
                            "relevance_score": 0.7,
                        }
                        for p in DEFAULT_SPIRITUAL_PRINCIPLES
                    ],
                )
                pipeline.run(inp)
                pipeline.write_back(inp, matched_pattern_ids=[])
                logger.info(f"[SFDS] formation pipeline write-back ok for decision={decision_id[:8]}")
        except Exception as fp_err:
            logger.warning(f"[SFDS] formation pipeline bridge skipped: {fp_err}")

    except Exception as e:
        import traceback
        print(f"[SFDS] Background analysis failed: {e}\n{traceback.format_exc()}", flush=True)

@router.get("/decisions", response_model=List[Dict])
async def list_decisions(user_id: str = "current_user"):
    """获取用户决策历史"""
    if not sfds_storage:
        raise HTTPException(status_code=500, detail="SFDS storage not initialized")
    
    decisions = await sfds_storage.get_user_decisions(user_id)
    return decisions

@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str, user_id: str = "current_user"):
    """获取决策详情"""
    if not sfds_storage:
        raise HTTPException(status_code=500, detail="SFDS storage not initialized")
    
    try:
        decision = await sfds_storage.get_decision_by_id(decision_id)
    except Exception as exc:
        print(f'[SFDS] get_decision failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail=f"获取决策失败: {exc}")
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    # 解析JSON字段（psycopg2 JSONB may already be parsed as dict/list）
    for key in ('emotion_logs', 'motive_analysis', 'discernment_result', 'guidance', 'context_factors'):
        val = decision.get(key)
        if isinstance(val, str):
            try:
                decision[key] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
    
    # 重建 state_snapshot 嵌套结构 — 12维度完整恢复
    decision['state_snapshot'] = {
        # 基础5维度
        'stress_level': decision.pop('stress_level', 5),
        'anxiety_level': decision.pop('anxiety_level', 5),
        'fatigue_level': decision.pop('fatigue_level', 5),
        'spiritual_dryness': decision.pop('spiritual_dryness', 5),
        'emotional_stability': decision.pop('emotional_stability', 5),
        # 扩展7维度（兼容旧数据，默认为5）
        'physical_health': decision.pop('physical_health', 5),
        'sleep_quality': decision.pop('sleep_quality', 5),
        'social_connection': decision.pop('social_connection', 5),
        'financial_pressure': decision.pop('financial_pressure', 5),
        'cognitive_clarity': decision.pop('cognitive_clarity', 5),
        'identity_confusion': decision.pop('identity_confusion', 5),
        'moral_tension': decision.pop('moral_tension', 5),
    }
    
    # 序列化 datetime 字段
    for key in ('created_at', 'updated_at'):
        if decision.get(key) and hasattr(decision[key], 'isoformat'):
            decision[key] = decision[key].isoformat()
    
    return decision

@router.post("/decisions/{decision_id}/review")
async def create_review(
    decision_id: str,
    review: ReviewLogCreate,
    user_id: str = "current_user"
):
    """创建决策回顾记录"""
    if not sfds_storage:
        raise HTTPException(status_code=500, detail="SFDS storage not initialized")
    
    # 验证决策存在
    decision = await sfds_storage.get_decision_by_id(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    review_id = await sfds_storage.create_review_log(user_id, review)
    return {"id": review_id, "message": "回顾记录已创建"}

@router.get("/principles", response_model=List[SpiritualPrinciple])
async def get_principles(category: Optional[str] = None):
    """获取灵性原则列表"""
    principles = [SpiritualPrinciple(**p) for p in DEFAULT_SPIRITUAL_PRINCIPLES]
    
    if category:
        principles = [p for p in principles if p.category == category]
    
    return principles

@router.post("/quick-discern")
async def quick_discern(state: StateSnapshot, emotions: List[EmotionLog] = []):
    """快速辨识 - 不保存，即时分析"""
    # 快速分析动机和来源
    motive = discernment_engine.analyze_motives(state, emotions, {})
    discernment = discernment_engine.discern_source(motive, state)
    
    # 简化版指导
    guidance = GuidanceOutput(
        structured_advice=discernment.explanation,
        risks=["这是快速分析，建议详细记录以获得更准确指导"],
        alternative_interpretations=[],
        recommended_actions=["考虑完整记录此决策以获得更深入分析"],
        priority=GuidancePriority.MEDIUM
    )
    
    return {
        "motive_analysis": motive.dict(),
        "discernment": discernment.dict(),
        "quick_guidance": guidance.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== REFLECTIVE DISCERNMENT ENDPOINT ====================

class ReflectiveDiscernmentRequest(BaseModel):
    """Request for reflective discernment engine"""
    title: str
    description: str
    category: DecisionCategory
    urgency: int = Field(ge=1, le=5)
    importance: int = Field(ge=1, le=5)
    state_snapshot: StateSnapshot
    emotion_logs: List[EmotionLog] = []
    motive_analysis: Optional[MotiveAnalysis] = None


@router.post("/reflective-discern")
async def reflective_discern(request: ReflectiveDiscernmentRequest):
    """
    深度辨识分析 - 使用新版反思性辨识引擎
    
    这个端点提供更深层次的决策分析，包括：
    - 来源分类（圣灵/恐惧/骄傲/创伤/世俗等）
    - 多种解释视角
    - 风险评估
    - 非指导性的反思建议
    
    作为"灵性镜子"而非"神谕"，强调谦卑和不确定性。
    """
    # Initialize the reflective engine
    engine = ReflectiveEngine()
    
    # Convert request to engine format
    decision = EngineDecision(
        id=str(uuid.uuid4()),
        user_id="current_user",
        title=request.title,
        description=request.description,
        category=request.category.value,
        urgency_level=request.urgency,
        importance_level=request.importance,
        created_at=datetime.utcnow(),
    )
    
    emotional_state = EngineEmotion(
        emotions=[{
            "type": e.emotion_type,
            "intensity": e.intensity,
            "trigger": e.trigger
        } for e in request.emotion_logs],
        stress_level=request.state_snapshot.stress_level,
        anxiety_level=request.state_snapshot.anxiety_level,
        fatigue_level=request.state_snapshot.fatigue_level,
        spiritual_dryness=request.state_snapshot.spiritual_dryness,
        emotional_stability=request.state_snapshot.emotional_stability,
    )
    
    # Use provided motive analysis or compute default
    if request.motive_analysis:
        motive = EngineMotive(
            fear_driven_score=request.motive_analysis.fear_driven_score,
            pride_driven_score=request.motive_analysis.pride_driven_score,
            love_driven_score=request.motive_analysis.love_driven_score,
            desire_driven_score=request.motive_analysis.desire_driven_score,
            duty_driven_score=getattr(request.motive_analysis, 'duty_driven_score', 0.0),
            ambition_driven_score=getattr(request.motive_analysis, 'ambition_driven_score', 0.0),
        )
    else:
        # Default motive profile
        motive = EngineMotive(
            fear_driven_score=0.3,
            pride_driven_score=0.3,
            love_driven_score=0.4,
            desire_driven_score=0.3,
        )
    
    # Convert principles to engine format
    principles = [
        EnginePrinciple(
            id=p["id"],
            principle_text=p["principle_text"],
            scripture_reference=p.get("scripture_reference", ""),
            category=p["category"],
            relevance_score=0.7,
        )
        for p in DEFAULT_SPIRITUAL_PRINCIPLES
    ]
    
    # Run discernment
    result = engine.discern(decision, emotional_state, motive, principles)
    
    # Format for API response
    formatted = format_engine_result(result)
    
    return {
        "reflective_analysis": formatted,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "本分析作为\u201c灵性镜子\u201d而非绝对真理，请结合祷告、圣经和属灵群体的意见。"
    }


# ==================== V2 ENGINE SINGLETONS ====================

_v2_engine: Optional[DiscernmentEngineV2] = None


def init_v2_engine(db_pool=None):
    """Initialise V2 engine + Formation Pipeline with optional DB pool."""
    global _v2_engine
    temporal_dao = TemporalDataAccess(db_pool) if db_pool else TemporalDataAccess()
    temporal_eng = TemporalEngine(temporal_dao)
    graph_eng = GraphService(get_neo4j())
    _v2_engine = DiscernmentEngineV2(graph_engine=graph_eng, temporal_engine=temporal_eng)
    init_pipeline(db_pool)


def get_v2_engine() -> DiscernmentEngineV2:
    if _v2_engine is None:
        init_v2_engine()
    return _v2_engine


# ==================== V2 REQUEST / RESPONSE MODELS ====================

class SpiritualSnapshotV2(BaseModel):
    """Extended snapshot with 12 dimensions for V2 — 现代生活完整画像"""
    # 基础5维度
    anxiety_level:       int = Field(ge=0, le=10, default=5)
    peace_level:         int = Field(ge=0, le=10, default=5)
    clarity_level:       int = Field(ge=0, le=10, default=5)
    spiritual_dryness:   int = Field(ge=0, le=10, default=5)
    emotional_stability: int = Field(ge=0, le=10, default=5)
    decision_confidence: int = Field(ge=0, le=10, default=5)
    # V1 compat fields
    stress_level:        int = Field(ge=0, le=10, default=5)
    fatigue_level:       int = Field(ge=0, le=10, default=5)
    # 扩展7维度
    physical_health:     int = Field(ge=0, le=10, default=5)
    sleep_quality:       int = Field(ge=0, le=10, default=5)
    social_connection:   int = Field(ge=0, le=10, default=5)
    financial_pressure:  int = Field(ge=0, le=10, default=5)
    cognitive_clarity:   int = Field(ge=0, le=10, default=5)
    identity_confusion:  int = Field(ge=0, le=10, default=5)
    moral_tension:       int = Field(ge=0, le=10, default=5)


class V2DiscernmentRequest(BaseModel):
    """Request body for the V2 discernment endpoint."""
    title:        str = Field(min_length=1, max_length=200)
    description:  str = Field(default="")
    category:     DecisionCategory
    urgency:      int = Field(ge=1, le=5, default=3)
    importance:   int = Field(ge=1, le=5, default=3)

    snapshot:     SpiritualSnapshotV2
    emotion_logs: List[EmotionLog] = []
    motive_analysis: Optional[MotiveAnalysis] = None

    past_behavior_types: List[str] = []
    user_id:      str = Field(default="anonymous")


class TimelineRecordRequest(BaseModel):
    """Body for recording a spiritual timeline data point."""
    user_id:             str
    anxiety_level:       int = Field(ge=0, le=10)
    peace_level:         int = Field(ge=0, le=10)
    clarity_level:       int = Field(ge=0, le=10)
    spiritual_dryness:   int = Field(ge=0, le=10)
    emotional_stability: int = Field(ge=0, le=10)
    decision_confidence: int = Field(ge=0, le=10)
    source_type:         str = "checkin"
    source_id:           Optional[str] = None
    notes:               Optional[str] = None


class EmotionRecordRequest(BaseModel):
    """Body for recording an emotion cycle data point."""
    user_id:      str
    emotion_type: str
    intensity:    int = Field(ge=0, le=10)
    trigger:      Optional[str] = None
    decision_id:  Optional[str] = None


# ==================== V2 API ENDPOINTS ====================

@router.post("/v2/discern")
async def discern_v2(request: V2DiscernmentRequest):
    """
    V2 Deep Discernment — 5-layer formation pipeline.

    Layers:
    1. State snapshot  (facts)
    2. Semantic        (pgvector meaning — from request principles)
    3. Graph           (Neo4j structure — WHY)
    4. Time-series     (TimescaleDB trend — WHEN)
    5. LLM discernment (fusion reasoning)

    Returns four insight pillars + reflective questions.
    Never commands behaviour or claims divine authority.
    System is a mirror, not a judge.
    """
    pipeline = get_pipeline()

    motive_scores = None
    if request.motive_analysis:
        motive_scores = {
            "fear":    request.motive_analysis.fear_driven_score,
            "pride":   request.motive_analysis.pride_driven_score,
            "love":    request.motive_analysis.love_driven_score,
            "desire":  request.motive_analysis.desire_driven_score,
        }

    inp = PipelineInput(
        user_id=request.user_id,
        decision_id=str(uuid.uuid4()),
        title=request.title,
        description=request.description,
        category=request.category.value,
        urgency=request.urgency,
        importance=request.importance,
        anxiety_level=request.snapshot.anxiety_level,
        peace_level=request.snapshot.peace_level,
        clarity_level=request.snapshot.clarity_level,
        spiritual_dryness=request.snapshot.spiritual_dryness,
        emotional_stability=request.snapshot.emotional_stability,
        decision_confidence=request.snapshot.decision_confidence,
        stress_level=request.snapshot.stress_level,
        fatigue_level=request.snapshot.fatigue_level,
        emotions=[{
            "type": e.emotion_type,
            "intensity": e.intensity,
            "trigger": e.trigger,
        } for e in request.emotion_logs],
        motive_scores=motive_scores,
        past_behavior_types=request.past_behavior_types,
        semantic_principles=[
            {
                "id": p["id"],
                "principle_text": p["principle_text"],
                "scripture_reference": p.get("scripture_reference", ""),
                "category": p["category"],
                "relevance_score": 0.7,
            }
            for p in DEFAULT_SPIRITUAL_PRINCIPLES
        ],
    )

    output = pipeline.run(inp)
    # Persist formation metrics silently in the background so loop detection
    # has historical data to work with on future profile lookups.
    try:
        pipeline.write_back(inp, matched_pattern_ids=[])
    except Exception as exc:
        logger.warning("[discern_v2] auto write_back failed: %s", exc)
    return output.to_dict()


@router.post("/v2/timeline/record")
async def record_timeline(body: TimelineRecordRequest):
    """
    Record a spiritual formation data point to the TimescaleDB timeline.
    Call this from check-in, journal submission, or decision review flows.
    """
    engine = get_v2_engine()
    ok = engine._temporal.dao.insert_spiritual_record(
        user_id=body.user_id,
        anxiety=body.anxiety_level,
        peace=body.peace_level,
        clarity=body.clarity_level,
        dryness=body.spiritual_dryness,
        stability=body.emotional_stability,
        confidence=body.decision_confidence,
        source_type=body.source_type,
        source_id=body.source_id,
        notes=body.notes,
    )
    return {"recorded": ok, "message": "Timeline data point accepted." if ok else "DB not available — data not persisted."}


@router.post("/v2/emotions/record")
async def record_emotion(body: EmotionRecordRequest):
    """
    Record an emotion intensity data point to the emotional cycle series.
    """
    engine = get_v2_engine()
    ok = engine._temporal.dao.insert_emotion_record(
        user_id=body.user_id,
        emotion_type=body.emotion_type,
        intensity=body.intensity,
        trigger=body.trigger,
        decision_id=body.decision_id,
    )
    return {"recorded": ok}


@router.get("/v2/timeline/{user_id}")
async def get_temporal_analysis(user_id: str, days: int = 90):
    """
    Run temporal analysis for a user without a decision context.
    Useful for spiritual formation dashboards.
    """
    engine = get_v2_engine()
    insight = engine._temporal.analyze(user_id=user_id, window_days=days)
    return {
        "user_id": user_id,
        "window_days": days,
        "trend_direction": insight.trend_direction.value,
        "spiritual_season": insight.spiritual_season.value,
        "is_peak_anxiety": insight.is_peak_anxiety,
        "is_burnout_risk": insight.is_burnout_risk,
        "is_intervention_window": insight.is_intervention_window,
        "detected_patterns": [
            {
                "type": p.pattern_type.value,
                "description": p.description,
                "confidence": p.confidence,
                "severity": p.severity,
            }
            for p in insight.detected_patterns
        ],
        "summary": insight.temporal_summary,
        "stats": {
            "avg_anxiety_14d":   insight.avg_anxiety_14d,
            "avg_peace_14d":     insight.avg_peace_14d,
            "avg_dryness_14d":   insight.avg_dryness_14d,
            "avg_stability_14d": insight.avg_stability_14d,
            "data_points":       insight.data_points_available,
        },
        "intervention_guidance": insight.intervention_guidance,
    }


@router.get("/v2/graph/patterns")
async def get_graph_patterns(category: Optional[str] = None, format: Optional[str] = None):
    """
    Return spiritual formation causal patterns.

    ?format=subgraph  returns fully-typed node-link subgraph (v2.1 schema)
    ?format=chain     returns the simple chain format (default)
    ?category=fear    filter by category
    """
    from graph_layer import KNOWN_PATTERNS, PATTERN_SUBGRAPHS, format_subgraph_for_api

    if format == "subgraph":
        sgs = PATTERN_SUBGRAPHS
        if category:
            sgs = [sg for sg in sgs if sg.category == category.lower()]
        return {
            "total":    len(sgs),
            "schema":   "v2.1",
            "patterns": [format_subgraph_for_api(sg) for sg in sgs],
        }

    patterns = KNOWN_PATTERNS
    if category:
        patterns = [p for p in patterns if p.get("category", "") == category.lower()]
    return {
        "total":  len(patterns),
        "schema": "v2.0",
        "patterns": [
            {
                "id":                  p["id"],
                "category":            p.get("category", ""),
                "label":               p["label"],
                "chain":               p["chain"],
                "intervention":        p["intervention"],
                "reflective_question": p.get("reflective_question", ""),
            }
            for p in patterns
        ],
    }


@router.get("/v2/graph/detect-loop/{user_id}")
async def detect_user_loop(user_id: str):
    """
    Graph use case 1 — "Which loop is the user currently inside?"
    Detects active REINFORCES feedback loops from user's graph history.
    """
    pipeline = get_pipeline()
    loops = pipeline.graph.detect_loop(user_id)
    return {
        "user_id": user_id,
        "active_loops": loops,
        "count": len(loops),
        "note": "Loops are detected from repeating patterns — not deterministic fate. They describe current dynamics, not identity.",
    }


@router.get("/v2/graph/root-cause/{behavior_type}")
async def get_root_cause(behavior_type: str):
    """
    Graph use case 2 — "What emotion originally triggered this behavior?"
    Traverses EmotionNode → MotiveNode → BehaviorNode backwards.
    """
    pipeline = get_pipeline()
    paths = pipeline.graph.trace_root_cause(behavior_type)
    return {
        "behavior":    behavior_type,
        "root_causes": paths,
        "note": "Root cause tracing shows possible origin emotions — not the only explanation.",
    }


@router.get("/v2/graph/intervention-points/{user_id}")
async def get_intervention_points(user_id: str):
    """
    Graph use case 3 — "Where can this loop be broken?"
    Finds PrincipleNode → BREAKS → BehaviorNode edges in user's pattern history.
    """
    pipeline = get_pipeline()
    points = pipeline.graph.find_intervention_points(user_id)
    return {
        "user_id":             user_id,
        "intervention_points": points,
        "note": "Intervention points are structural leverage positions — awareness, not prescription.",
    }


@router.get("/v2/graph/principles/{motive_type}")
async def activate_principles(motive_type: str):
    """
    Graph use case 4 — "Which spiritual truth addresses this motive?"
    Returns PrincipleNodes that INFLUENCES or BREAKS the given motive type.
    """
    pipeline = get_pipeline()
    principles = pipeline.graph.activate_principles(motive_type)
    return {
        "motive":     motive_type,
        "principles": principles,
        "note": "These principles are offered as formational mirrors, not prescriptions.",
    }


class GraphReasonRequest(BaseModel):
    """Request body for the Graph Reasoning Fusion endpoint."""
    user_id:           str
    dominant_emotion:  str = "anxiety"
    dominant_motive:   str = "fear_driven_control"
    # Optional — if provided, graph analysis is richer
    emotions:          List[Dict[str, Any]] = []
    motive_scores:     Optional[Dict[str, float]] = None
    past_behaviors:    List[str] = []
    category:          str = "other"
    # Semantic principles from pgvector (optional pass-through)
    vector_principles: List[Dict[str, Any]] = []
    # Temporal context from TimescaleDB (optional pass-through)
    temporal_context:  Optional[Dict[str, Any]] = None


@router.post("/v2/graph/reason")
async def graph_reason(req: GraphReasonRequest):
    """
    SFDS v2.2 — Graph Reasoning Fusion Engine.

    Performs 6-layer structured reasoning over human inner dynamics:
      Layer 1 — Graph Structure Interpretation
      Layer 2 — Loop Dynamics Analysis
      Layer 3 — Breakpoint Detection
      Layer 4 — Vector Knowledge Alignment
      Layer 5 — Temporal Context (if provided)
      Layer 6 — Synthesis (final structured output)

    Returns a FormationReasoning structured output.
    """
    from graph_reasoning_engine import GraphReasoningFusion

    pipeline = get_pipeline()

    # Run graph analysis first (needed by reasoning engine)
    graph_insight = None
    try:
        dominant_motive = req.dominant_motive
        if req.motive_scores:
            dominant_motive = max(req.motive_scores, key=lambda k: req.motive_scores[k])
        graph_insight = pipeline.graph.analyze(
            user_id          = req.user_id,
            dominant_motive  = dominant_motive,
            emotions         = req.emotions,
            decision_category= req.category,
            past_behavior_types=req.past_behaviors,
        )
    except Exception as exc:
        logger.warning("[graph/reason] graph analyze failed: %s", exc)

    # Run 6-layer reasoning fusion
    reasoning = pipeline.reasoning.reason(
        user_id           = req.user_id,
        dominant_emotion  = req.dominant_emotion,
        dominant_motive   = req.dominant_motive,
        graph_insight     = graph_insight,
        vector_principles = req.vector_principles,
        temporal_context  = req.temporal_context,
    )

    return {
        "user_id":        req.user_id,
        "schema":         "v2.2",
        "reasoning":      reasoning.to_dict(),
        "note": (
            "This output represents structured reasoning over inner dynamics — "
            "not a spiritual verdict or behavioral prescription."
        ),
    }


# ==================== V3 FORMATION ENGINE ENDPOINTS ====================

@router.get("/v3/formation/profile/{user_id}")
async def get_formation_profile(user_id: str):
    """
    SFDS v3 — Formation Engine: long-term character dimension profile.

    Returns the accumulated formation profile for a user across all sessions:
    - 7 character dimension scores (0.0–1.0 tendency scale)
    - formation arc (breaking_through / deepening_loops / stabilizing / unknown)
    - strongest and weakest tendencies
    - trajectory narrative (probabilistic, non-directive)

    Scores represent TENDENCIES, not fixed traits.
    Genuine change is always possible — this is a mirror, not a verdict.
    """
    from formation_engine import get_formation_engine
    engine = get_formation_engine(db_pool=None)
    profile = await engine.get_profile(user_id)
    return {
        "user_id":  user_id,
        "schema":   "v3",
        "profile":  profile,
    }


@router.get("/v3/formation/dimensions")
async def get_formation_dimensions():
    """
    SFDS v3 — Returns the list of tracked character dimensions with descriptions.
    Useful for frontend rendering of the Formation Profile UI.
    """
    return {
        "schema": "v3",
        "state_vector_note": (
            "The 8-dimension FormationStateVector is NOT a moral score or personality type. "
            "It is a trajectory signal — a dynamic mirror of behavioral tendencies over time. "
            "All values are 0.05–0.95. Genuine transformation is always possible."
        ),
        "dimensions": [
            {
                "key":         "humility",
                "label":       "Humility",
                "description": "Tendency toward truth-seeking vs self-protection",
                "direction":   "higher = more truth-seeking",
                "reflective_question": "What might be driving the need to protect your own perspective right now?",
            },
            {
                "key":         "fear_tendency",
                "label":       "Fear Tendency",
                "description": "Fear-driven response tendency — higher = more fear-driven loop activity",
                "direction":   "higher = more active fear loop (not 'bad'; a signal)",
                "reflective_question": "What might you be trying to control that you actually can't — and what would it feel like to release it?",
            },
            {
                "key":         "pride_tendency",
                "label":       "Pride Tendency",
                "description": "Pride-driven response tendency — higher = more comparison/self-protection loop",
                "direction":   "higher = more active pride loop (not 'bad'; a signal)",
                "reflective_question": "Where might the need to be right or seen as capable be creating distance from others?",
            },
            {
                "key":         "emotional_stability",
                "label":       "Emotional Stability",
                "description": "Regulated response vs reactive volatility tendency",
                "direction":   "higher = more regulated",
                "reflective_question": "What patterns seem to trigger reactions before reflection has a chance to engage?",
            },
            {
                "key":         "truth_alignment",
                "label":       "Truth Alignment",
                "description": "Behavioral alignment with honest self-perception and principle",
                "direction":   "higher = more aligned",
                "reflective_question": "Where might there be a gap between what you believe and how you're actually responding?",
            },
            {
                "key":         "relational_health",
                "label":       "Relational Health",
                "description": "Other-oriented vs self-absorbed relational pattern tendency",
                "direction":   "higher = more other-oriented",
                "reflective_question": "Whose perspective or needs might you be finding it difficult to hold alongside your own?",
            },
            {
                "key":         "resilience",
                "label":       "Resilience",
                "description": "Recovery tendency after adversity vs avoidance pattern",
                "direction":   "higher = more recovery-oriented",
                "reflective_question": "What would recovery look like for you after a setback — not avoidance, but actual return?",
            },
            {
                "key":         "spiritual_clarity",
                "label":       "Spiritual Clarity",
                "description": "Clarity of inner values and reduction of dryness/confusion",
                "direction":   "higher = more clarity",
                "reflective_question": "What has been making it harder to access your own inner sense of clarity recently?",
            },
        ],
        "dominant_loops": [
            {"key": "fear_control_loop",    "description": "fear → control → overwork → burnout → fear"},
            {"key": "shame_avoidance_loop", "description": "shame → avoidance → procrastination → anxiety"},
            {"key": "pride_comparison_loop","description": "pride → comparison → anxiety → instability"},
            {"key": "desire_impulse_loop",  "description": "desire → impulsive action → regret → desire"},
            {"key": "truth_stability_loop", "description": "truth-facing → reflection → stability (healthy)"},
        ],
        "note": (
            "These dimensions describe tendencies, not identities. "
            "All scores are relative, directional, and always open to change."
        ),
    }


# ==================== DATABASE MIGRATION ====================

SFDS_TABLES_SQL = """
-- 决策支撑系统表结构

-- 决策事件主表
CREATE TABLE IF NOT EXISTS sfds_decision_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    urgency INTEGER CHECK (urgency BETWEEN 1 AND 5),
    importance INTEGER CHECK (importance BETWEEN 1 AND 5),
    
    -- 状态快照 — 12维度现代生活完整画像
    -- 基础5维度（身心灵核心）
    stress_level INTEGER CHECK (stress_level BETWEEN 0 AND 10),
    anxiety_level INTEGER CHECK (anxiety_level BETWEEN 0 AND 10),
    fatigue_level INTEGER CHECK (fatigue_level BETWEEN 0 AND 10),
    spiritual_dryness INTEGER CHECK (spiritual_dryness BETWEEN 0 AND 10),
    emotional_stability INTEGER CHECK (emotional_stability BETWEEN 0 AND 10),
    -- 扩展7维度（现代生活全景）
    physical_health INTEGER CHECK (physical_health BETWEEN 0 AND 10) DEFAULT 5,
    sleep_quality INTEGER CHECK (sleep_quality BETWEEN 0 AND 10) DEFAULT 5,
    social_connection INTEGER CHECK (social_connection BETWEEN 0 AND 10) DEFAULT 5,
    financial_pressure INTEGER CHECK (financial_pressure BETWEEN 0 AND 10) DEFAULT 5,
    cognitive_clarity INTEGER CHECK (cognitive_clarity BETWEEN 0 AND 10) DEFAULT 5,
    identity_confusion INTEGER CHECK (identity_confusion BETWEEN 0 AND 10) DEFAULT 5,
    moral_tension INTEGER CHECK (moral_tension BETWEEN 0 AND 10) DEFAULT 5,

    -- JSON存储
    emotion_logs JSONB DEFAULT '[]',
    context_factors JSONB,
    motive_analysis JSONB,
    discernment_result JSONB,
    guidance JSONB,
    
    -- 状态
    status TEXT DEFAULT 'analyzing', -- analyzing, guided, decided, reviewed, archived
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 回顾记录表
CREATE TABLE IF NOT EXISTS sfds_review_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    decision_id UUID REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    outcome_description TEXT NOT NULL,
    peace_level INTEGER CHECK (peace_level BETWEEN -5 AND 5),
    regret_level INTEGER CHECK (regret_level BETWEEN 0 AND 10),
    lessons_learned TEXT,
    character_impact TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 灵性原则表
CREATE TABLE IF NOT EXISTS sfds_spiritual_principles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principle_text TEXT NOT NULL,
    scripture_reference TEXT,
    category TEXT,
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_sfds_decisions_user_id ON sfds_decision_events(user_id);
CREATE INDEX IF NOT EXISTS idx_sfds_decisions_created_at ON sfds_decision_events(created_at);
CREATE INDEX IF NOT EXISTS idx_sfds_decisions_status ON sfds_decision_events(status);
CREATE INDEX IF NOT EXISTS idx_sfds_reviews_decision_id ON sfds_review_logs(decision_id);
CREATE INDEX IF NOT EXISTS idx_sfds_reviews_user_id ON sfds_review_logs(user_id);

-- 时间序列表 (用于追踪用户灵性成长)
CREATE TABLE IF NOT EXISTS sfds_spiritual_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    metric_date DATE NOT NULL,
    
    -- 灵性健康指标
    prayer_consistency INTEGER CHECK (prayer_consistency BETWEEN 0 AND 10),
    scripture_engagement INTEGER CHECK (scripture_engagement BETWEEN 0 AND 10),
    community_connection INTEGER CHECK (community_connection BETWEEN 0 AND 10),
    service_activity INTEGER CHECK (service_activity BETWEEN 0 AND 10),
    character_growth_score INTEGER CHECK (character_growth_score BETWEEN 0 AND 10),
    
    -- 情绪健康指标
    emotional_regulation INTEGER CHECK (emotional_regulation BETWEEN 0 AND 10),
    stress_resilience INTEGER CHECK (stress_resilience BETWEEN 0 AND 10),
    relational_health INTEGER CHECK (relational_health BETWEEN 0 AND 10),
    
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_sfds_metrics_user_date ON sfds_spiritual_metrics(user_id, metric_date);
"""
