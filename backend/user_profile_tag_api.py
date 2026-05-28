"""
用户人格画像标签系统 API
提供标签提取、存储、查询和人格画像生成的RESTful接口
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks

# 导入人格画像系统
from user_profile_tag_system import (
    init_profile_system, get_tag_store, get_profile_engine,
    extract_and_store_tags, generate_user_profile,
    TagCategory, TagSource, PersonalityProfile, FormationStateVector,
    tag_extractor
)

router = APIRouter(prefix="/api/profile", tags=["user_profile"])


# ==================== Pydantic 模型 ====================

class TagCreateRequest(BaseModel):
    """手动创建标签请求"""
    tag_name: str = Field(..., min_length=1, max_length=100, description="标签名称")
    tag_category: str = Field(..., description="标签类别")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class TagBatchCreateRequest(BaseModel):
    """批量创建标签请求"""
    tags: List[TagCreateRequest]
    source_event: Optional[Dict[str, Any]] = Field(default=None, description="来源事件信息")


class TagResponse(BaseModel):
    """标签响应"""
    id: str
    tag_name: str
    tag_category: str
    tag_subcategory: Optional[str]
    source: str
    confidence: float
    weight: float
    first_seen_at: str
    last_seen_at: str
    occurrence_count: int
    is_active: bool
    is_manually_added: bool


class TagListResponse(BaseModel):
    """标签列表响应"""
    user_id: str
    total: int
    tags: List[TagResponse]
    category_distribution: List[Dict[str, Any]]


class TagInsightsResponse(BaseModel):
    """标签洞察响应"""
    user_id: str
    total_tags: int
    active_categories: int
    average_weight: float
    category_distribution: List[Dict[str, Any]]
    top_tags: List[Dict[str, Any]]
    recent_tags: List[Dict[str, Any]]
    stable_tags: List[Dict[str, Any]]
    emerging_tags: List[Dict[str, Any]]


class ExtractTagsRequest(BaseModel):
    """提取标签请求"""
    text: str = Field(..., min_length=1, description="待提取标签的文本")
    source_type: str = Field(default="system", description="来源类型")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class ExtractTagsFromEventRequest(BaseModel):
    """从事件数据提取标签请求"""
    event_data: Dict[str, Any] = Field(..., description="事件数据")
    event_type: str = Field(..., description="事件类型 (emotion_checkin, decision_event, habit_execution, formation_analysis)")
    event_id: Optional[str] = Field(default=None, description="事件ID")


class ExtractTagsResponse(BaseModel):
    """提取标签响应"""
    extracted_count: int
    tags: List[Dict[str, Any]]
    stored_tag_ids: List[str]
    source_type: str
    confidence: float


class FormationStateVectorInput(BaseModel):
    """8维性格状态向量输入"""
    humility: float = Field(default=0.5, ge=0.05, le=0.95)
    fear_tendency: float = Field(default=0.5, ge=0.05, le=0.95)
    pride_tendency: float = Field(default=0.5, ge=0.05, le=0.95)
    emotional_stability: float = Field(default=0.5, ge=0.05, le=0.95)
    truth_alignment: float = Field(default=0.5, ge=0.05, le=0.95)
    relational_health: float = Field(default=0.5, ge=0.05, le=0.95)
    resilience: float = Field(default=0.5, ge=0.05, le=0.95)
    spiritual_clarity: float = Field(default=0.5, ge=0.05, le=0.95)


class PersonalityProfileRequest(BaseModel):
    """生成人格画像请求"""
    formation_vector: Optional[FormationStateVectorInput] = Field(default=None, description="8维状态向量")
    include_history: bool = Field(default=True, description="是否包含历史趋势")


class PersonalityProfileResponse(BaseModel):
    """人格画像响应"""
    user_id: str
    generated_at: str
    
    # 核心画像
    personality_archetype: Optional[str]
    dominant_loop: Optional[str]
    trajectory_direction: Optional[str]
    
    # 状态向量
    formation_vector: Dict[str, Any]
    
    # 标签聚合
    top_emotion_tags: List[Dict[str, Any]]
    top_behavior_tags: List[Dict[str, Any]]
    top_value_tags: List[Dict[str, Any]]
    top_relationship_tags: List[Dict[str, Any]]
    life_dominant_domains: List[Any]
    
    # 模式识别
    recurring_patterns: List[Dict[str, Any]]
    growth_indicators: List[str]
    risk_factors: List[Dict[str, Any]]
    
    # 时间维度
    profile_stability: float
    change_velocity: float
    trend_direction: str
    
    # 叙事描述
    profile_summary: str
    core_narrative: str
    growth_pathway: str


class TagCategoryInfo(BaseModel):
    """标签类别信息"""
    category: str
    display_name: str
    description: str
    example_tags: List[str]


class TagOperationResponse(BaseModel):
    """标签操作响应"""
    success: bool
    message: str
    tag_name: Optional[str] = None


# ==================== 依赖注入 ====================

def get_current_user_id() -> str:
    """
    获取当前用户ID
    实际实现应该从session/token中提取
    这里简化处理
    """
    # TODO: 从请求session中获取真实用户ID
    return "demo_user"


def require_initialized():
    """检查系统是否已初始化"""
    store = get_tag_store()
    if not store:
        raise HTTPException(status_code=503, detail="Profile system not initialized")
    return store


# ==================== API 路由 ====================

@router.get("/tags/categories", response_model=List[TagCategoryInfo])
async def get_tag_categories():
    """获取所有标签类别信息"""
    categories = [
        TagCategoryInfo(
            category=TagCategory.EMOTION_TYPE.value,
            display_name="情绪类型",
            description="用户常体验的情绪状态，如焦虑、喜悦、抑郁等",
            example_tags=["焦虑型", "喜悦型", "平静型", "疲惫型"]
        ),
        TagCategoryInfo(
            category=TagCategory.EMOTION_PATTERN.value,
            display_name="情绪模式",
            description="情绪的变化规律和应对模式",
            example_tags=["情绪波动型", "情绪压抑型", "情绪敏感型"]
        ),
        TagCategoryInfo(
            category=TagCategory.HABIT_TYPE.value,
            display_name="习惯类型",
            description="用户的日常习惯类型",
            example_tags=["灵修习惯", "健康习惯", "学习习惯", "社交习惯"]
        ),
        TagCategoryInfo(
            category=TagCategory.HABIT_CONSISTENCY.value,
            display_name="习惯坚持度",
            description="用户维持习惯的稳定性和持续性",
            example_tags=["高度自律", "间歇性努力", "启动困难", "容易放弃"]
        ),
        TagCategoryInfo(
            category=TagCategory.CHARACTER_TRAIT.value,
            display_name="性格特质",
            description="基于Formation State Vector的性格特征",
            example_tags=["谦逊型", "自信型", "坚韧型", "真诚型"]
        ),
        TagCategoryInfo(
            category=TagCategory.BEHAVIOR_PATTERN.value,
            display_name="行为模式",
            description="用户在面对情境时的典型行为反应",
            example_tags=["逃避型", "完美主义", "拖延型", "讨好型"]
        ),
        TagCategoryInfo(
            category=TagCategory.RESPONSE_STYLE.value,
            display_name="应对风格",
            description="面对压力和挑战时的应对方式",
            example_tags=["问题解决型", "情绪导向型", "寻求支持型", "独自承担型"]
        ),
        TagCategoryInfo(
            category=TagCategory.STRESS_REACTION.value,
            display_name="压力反应",
            description="在压力下的典型反应模式",
            example_tags=["压力下焦虑", "压力下愤怒", "压力下退缩", "压力下奋进"]
        ),
        TagCategoryInfo(
            category=TagCategory.LIFE_DOMAIN.value,
            display_name="生活领域",
            description="用户主要关注的生命领域",
            example_tags=["工作领域", "家庭领域", "关系领域", "健康领域", "信仰领域"]
        ),
        TagCategoryInfo(
            category=TagCategory.VALUE_PRIORITY.value,
            display_name="价值观",
            description="用户的核心价值优先级",
            example_tags=["安全感导向", "成就导向", "被爱导向", "成长导向"]
        ),
        TagCategoryInfo(
            category=TagCategory.MOTIVE_TYPE.value,
            display_name="动机类型",
            description="驱动用户行为的主要动机",
            example_tags=["恐惧驱动", "骄傲驱动", "爱驱动", "责任驱动"]
        ),
        TagCategoryInfo(
            category=TagCategory.RELATIONSHIP_TYPE.value,
            display_name="关系类型",
            description="用户在各关系中的表现模式",
            example_tags=["亲密关系", "亲子关系", "职场关系", "友谊关系"]
        ),
        TagCategoryInfo(
            category=TagCategory.ATTACHMENT_STYLE.value,
            display_name="依恋风格",
            description="人际关系中的依恋模式",
            example_tags=["安全依恋", "焦虑依恋", "回避依恋", "混乱依恋"]
        ),
        TagCategoryInfo(
            category=TagCategory.SOCIAL_PREFERENCE.value,
            display_name="社交偏好",
            description="社交互动中的偏好风格",
            example_tags=["外向型", "内向型", "小圈子型", "广泛社交型"]
        ),
        TagCategoryInfo(
            category=TagCategory.COGNITIVE_STYLE.value,
            display_name="认知风格",
            description="思考和信息处理方式",
            example_tags=["理性分析型", "直觉感受型", "细节关注型", "大局观型"]
        ),
        TagCategoryInfo(
            category=TagCategory.SPIRITUAL_STATE.value,
            display_name="灵性状态",
            description="当前的灵性生命状态",
            example_tags=["灵性干枯", "寻求引导", "感恩灵修", "亲密连接"]
        ),
        TagCategoryInfo(
            category=TagCategory.DECISION_STYLE.value,
            display_name="决策风格",
            description="做决定时的典型风格",
            example_tags=["快速决策", "拖延决策", "寻求共识", "分析型"]
        ),
    ]
    return categories


@router.get("/tags/sources", response_model=List[Dict[str, str]])
async def get_tag_sources():
    """获取所有标签来源类型"""
    return [
        {"value": TagSource.EMOTION_CHECKIN.value, "display": "情绪打卡", "description": "从情绪打卡数据提取"},
        {"value": TagSource.DECISION_EVENT.value, "display": "决策事件", "description": "从决策分析提取"},
        {"value": TagSource.HABIT_EXECUTION.value, "display": "习惯执行", "description": "从习惯追踪提取"},
        {"value": TagSource.JOURNAL_ENTRY.value, "display": "日记记录", "description": "从日记/灵修记录提取"},
        {"value": TagSource.CHAT_INTERACTION.value, "display": "对话交互", "description": "从AI对话提取"},
        {"value": TagSource.PRAYER_REQUEST.value, "display": "祷告请求", "description": "从祷告墙提取"},
        {"value": TagSource.FORMATION_ANALYSIS.value, "display": "性格分析", "description": "从Formation Engine分析提取"},
        {"value": TagSource.BEHAVIOR_REGULATION.value, "display": "行为调节", "description": "从行为调节记录提取"},
        {"value": TagSource.MANUAL.value, "display": "手动添加", "description": "用户手动添加的标签"},
        {"value": TagSource.TEST_ASSESSMENT.value, "display": "测评问卷", "description": "从人格测评提取"},
    ]


@router.post("/tags/extract", response_model=ExtractTagsResponse)
async def extract_tags_from_text(
    request: ExtractTagsRequest,
    user_id: str = Depends(get_current_user_id)
):
    """从文本中提取标签（不存储）"""
    try:
        source = TagSource(request.source_type) if request.source_type in [s.value for s in TagSource] else TagSource.SYSTEM_INFERRED
        tags = tag_extractor.extract_from_text(request.text, source, request.context)
        
        return ExtractTagsResponse(
            extracted_count=len(tags),
            tags=tags,
            stored_tag_ids=[],
            source_type=request.source_type,
            confidence=sum(t['confidence'] for t in tags) / len(tags) if tags else 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag extraction failed: {str(e)}")


@router.post("/tags/extract-and-store", response_model=ExtractTagsResponse)
async def extract_and_store_tags_from_event(
    request: ExtractTagsFromEventRequest,
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """从事件数据提取并存储标签"""
    try:
        tag_ids = extract_and_store_tags(
            user_id, 
            request.event_data, 
            request.event_type, 
            request.event_id
        )
        
        # 获取提取的标签详情
        result = None
        if request.event_type == "emotion_checkin":
            result = tag_extractor.extract_from_emotion_checkin(request.event_data)
        elif request.event_type == "decision_event":
            result = tag_extractor.extract_from_decision(request.event_data)
        elif request.event_type == "habit_execution":
            result = tag_extractor.extract_from_habit(request.event_data)
        elif request.event_type == "formation_analysis":
            result = tag_extractor.extract_from_formation(request.event_data)
        
        return ExtractTagsResponse(
            extracted_count=len(result.tags) if result else 0,
            tags=result.tags if result else [],
            stored_tag_ids=tag_ids,
            source_type=request.event_type,
            confidence=result.confidence if result else 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tag extraction and storage failed: {str(e)}")


@router.get("/tags", response_model=TagListResponse)
async def get_user_tags(
    category: Optional[str] = Query(None, description="按类别筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    min_weight: float = Query(0.5, ge=0.0, le=10.0, description="最小权重"),
    include_inactive: bool = Query(False, description="是否包含非活跃标签"),
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """获取用户的所有标签"""
    try:
        tags = store.get_user_tags(
            user_id, 
            category=category, 
            limit=limit, 
            active_only=not include_inactive,
            min_weight=min_weight
        )
        
        # 获取分类分布
        insights = store.get_tag_insights(user_id)
        
        return TagListResponse(
            user_id=user_id,
            total=len(tags),
            tags=[TagResponse(**tag) for tag in tags],
            category_distribution=insights.get('category_distribution', [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tags: {str(e)}")


@router.get("/tags/insights", response_model=TagInsightsResponse)
async def get_tag_insights(
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """获取用户标签洞察统计"""
    try:
        insights = store.get_tag_insights(user_id)
        return TagInsightsResponse(**insights)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.post("/tags/manual", response_model=TagOperationResponse)
async def add_manual_tag(
    request: TagCreateRequest,
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """手动添加标签"""
    try:
        tag_data = {
            'tag_name': request.tag_name,
            'tag_category': request.tag_category,
            'source': TagSource.MANUAL.value,
            'confidence': request.confidence,
            'context': request.context,
        }
        
        tag_ids = store.add_or_update_tags(user_id, [tag_data])
        
        return TagOperationResponse(
            success=len(tag_ids) > 0,
            message=f"Tag '{request.tag_name}' added successfully",
            tag_name=request.tag_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add tag: {str(e)}")


@router.post("/tags/batch", response_model=TagOperationResponse)
async def add_batch_tags(
    request: TagBatchCreateRequest,
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """批量添加标签"""
    try:
        tags_data = [
            {
                'tag_name': t.tag_name,
                'tag_category': t.tag_category,
                'source': TagSource.MANUAL.value,
                'confidence': t.confidence,
                'context': t.context,
            }
            for t in request.tags
        ]
        
        tag_ids = store.add_or_update_tags(user_id, tags_data, request.source_event)
        
        return TagOperationResponse(
            success=len(tag_ids) > 0,
            message=f"{len(tag_ids)} tags added successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add tags: {str(e)}")


@router.delete("/tags/{tag_name}", response_model=TagOperationResponse)
async def deactivate_tag(
    tag_name: str,
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """停用（软删除）标签"""
    try:
        success = store.deactivate_tag(user_id, tag_name)
        return TagOperationResponse(
            success=success,
            message=f"Tag '{tag_name}' deactivated" if success else f"Tag '{tag_name}' not found",
            tag_name=tag_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deactivate tag: {str(e)}")


@router.post("/tags/{tag_name}/reactivate", response_model=TagOperationResponse)
async def reactivate_tag(
    tag_name: str,
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """重新激活标签"""
    try:
        success = store.reactivate_tag(user_id, tag_name)
        return TagOperationResponse(
            success=success,
            message=f"Tag '{tag_name}' reactivated" if success else f"Tag '{tag_name}' not found",
            tag_name=tag_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reactivate tag: {str(e)}")


@router.post("/tags/apply-decay")
async def apply_time_decay(
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """手动触发时间衰减（通常由后台任务自动执行）"""
    try:
        store.apply_time_decay(user_id)
        return {"success": True, "message": "Time decay applied"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply decay: {str(e)}")


# ==================== 人格画像 API ====================

@router.get("/profile", response_model=PersonalityProfileResponse)
async def get_personality_profile(
    include_vector: bool = Query(True, description="是否包含8维状态向量"),
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """
    获取用户人格画像
    
    如果提供了formation_vector，会结合标签和状态向量生成画像；
    否则仅基于标签生成。
    """
    try:
        engine = get_profile_engine()
        if not engine:
            raise HTTPException(status_code=503, detail="Profile engine not initialized")
        
        profile = engine.generate_profile(user_id, formation_vector=None, include_history=True)
        
        return PersonalityProfileResponse(**profile.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate profile: {str(e)}")


@router.post("/profile", response_model=PersonalityProfileResponse)
async def generate_profile_with_vector(
    request: PersonalityProfileRequest,
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """
    使用8维状态向量生成人格画像
    
    这个端点允许提供Formation State Vector来生成更准确的画像
    """
    try:
        engine = get_profile_engine()
        if not engine:
            raise HTTPException(status_code=503, detail="Profile engine not initialized")
        
        vector = None
        if request.formation_vector:
            vector = FormationStateVector(
                humility=request.formation_vector.humility,
                fear_tendency=request.formation_vector.fear_tendency,
                pride_tendency=request.formation_vector.pride_tendency,
                emotional_stability=request.formation_vector.emotional_stability,
                truth_alignment=request.formation_vector.truth_alignment,
                relational_health=request.formation_vector.relational_health,
                resilience=request.formation_vector.resilience,
                spiritual_clarity=request.formation_vector.spiritual_clarity,
            )
        
        profile = engine.generate_profile(user_id, vector, request.include_history)
        
        return PersonalityProfileResponse(**profile.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate profile: {str(e)}")


@router.get("/profile/archetypes")
async def get_personality_archetypes():
    """获取所有人格原型定义"""
    from user_profile_tag_system import PersonalityArchetype, PersonalityProfileEngine
    
    archetypes = []
    for archetype in PersonalityArchetype:
        rule = PersonalityProfileEngine.ARCHETYPE_RULES.get(archetype, {})
        archetypes.append({
            "value": archetype.value,
            "display_name": {
                "seeker": "探索者",
                "steward": "管家",
                "warrior": "战士",
                "artist": "艺术家",
                "thinker": "思考者",
                "caregiver": "照顾者",
                "leader": "领袖",
                "contemplative": "默观者",
                "activist": "行动者",
                "diplomat": "外交家",
            }.get(archetype.value, archetype.value),
            "required_tags": rule.get("required", []),
            "preferred_tags": rule.get("preferred", []),
        })
    
    return archetypes


@router.get("/profile/dominant-loops")
async def get_dominant_loops():
    """获取所有主导循环模式定义"""
    from user_profile_tag_system import PersonalityProfileEngine
    
    loops = []
    for loop_key, info in PersonalityProfileEngine.GROWTH_PATHWAYS.items():
        loops.append({
            "loop_key": loop_key,
            "pattern": info["pattern"],
            "description": info["description"],
            "growth_focus": info["growth_focus"],
            "suggested_practices": info["suggested_practices"],
        })
    
    return loops


@router.get("/profile/trajectory-directions")
async def get_trajectory_directions():
    """获取轨迹方向定义"""
    return [
        {
            "value": "stabilizing",
            "display_name": "趋于稳定",
            "description": "人格特质正向整合，趋于稳定和成熟",
            "indicator": "健康维度提升，不健康维度下降",
        },
        {
            "value": "improving_clarity",
            "display_name": "清晰度提升",
            "description": "灵性视野和真理认知日益清晰",
            "indicator": "truth_alignment 和 spiritual_clarity 提升",
        },
        {
            "value": "fragmenting",
            "display_name": "趋于破碎",
            "description": "可能处于压力或危机中，需要支持和整合",
            "indicator": "fear_tendency 和 pride_tendency 升高",
        },
        {
            "value": "increasing_volatility",
            "display_name": "波动性增加",
            "description": "情绪和状态变化较大，处于转型期",
            "indicator": "emotional_stability 下降，变化速度加快",
        },
        {
            "value": "cyclical",
            "display_name": "循环反复",
            "description": "呈现周期性模式，在相似状态中循环",
            "indicator": "历史数据显示周期性重复",
        },
        {
            "value": "unknown",
            "display_name": "待确定",
            "description": "数据不足，无法确定轨迹方向",
            "indicator": "标签数量或质量不足",
        },
    ]


@router.get("/profile/summary")
async def get_profile_summary(
    user_id: str = Depends(get_current_user_id),
    store = Depends(require_initialized)
):
    """获取简化的画像摘要（用于快速展示）"""
    try:
        engine = get_profile_engine()
        if not engine:
            raise HTTPException(status_code=503, detail="Profile engine not initialized")
        
        profile = engine.generate_profile(user_id)
        
        # 只返回关键信息
        return {
            "user_id": user_id,
            "personality_archetype": profile.personality_archetype,
            "dominant_loop": profile.dominant_loop,
            "trajectory_direction": profile.trajectory_direction,
            "top_3_tags": [
                {"name": t["name"], "category": t.get("category", "unknown")}
                for t in (profile.top_emotion_tags[:1] + profile.top_behavior_tags[:1] + profile.top_value_tags[:1])
            ],
            "life_dominant_domain": profile.life_dominant_domains[0] if profile.life_dominant_domains else None,
            "profile_summary": profile.profile_summary,
            "trend_direction": profile.trend_direction,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


# ==================== 集成辅助函数 ====================

async def auto_extract_tags_from_checkin(user_id: str, checkin_data: Dict, checkin_id: str):
    """
    从情绪打卡自动提取标签
    供其他模块调用
    """
    try:
        store = get_tag_store()
        if not store:
            return None
        
        tag_ids = extract_and_store_tags(user_id, checkin_data, "emotion_checkin", checkin_id)
        return {
            "extracted": len(tag_ids),
            "tag_ids": tag_ids
        }
    except Exception as e:
        print(f"[auto_extract_tags] Error: {e}", flush=True)
        return None


async def auto_extract_tags_from_decision(user_id: str, decision_data: Dict, decision_id: str):
    """
    从决策事件自动提取标签
    供其他模块调用
    """
    try:
        store = get_tag_store()
        if not store:
            return None
        
        tag_ids = extract_and_store_tags(user_id, decision_data, "decision_event", decision_id)
        return {
            "extracted": len(tag_ids),
            "tag_ids": tag_ids
        }
    except Exception as e:
        print(f"[auto_extract_tags] Error: {e}", flush=True)
        return None


# ==================== 初始化函数 ====================

def setup_profile_system(app, db_pool=None, use_memory: bool = False):
    """
    在FastAPI应用中设置人格画像系统
    
    Args:
        app: FastAPI应用实例
        db_pool: 数据库连接池
        use_memory: 是否使用内存模式（测试用）
    """
    # 初始化系统
    init_profile_system(db_pool, use_memory)
    
    # 注册路由
    app.include_router(router)
    
    print('[profile_system] API routes registered', flush=True)
