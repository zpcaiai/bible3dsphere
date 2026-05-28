"""
用户人格画像系统与 main.py 的集成示例

此文件展示了如何在现有应用中集成人格画像标签系统
"""

# ============================================================================
# 集成步骤 1: 在 main.py 中导入并初始化
# ============================================================================

# 在 main.py 顶部添加导入
# from user_profile_tag_api import setup_profile_system, auto_extract_tags_from_checkin

# 在应用启动事件中初始化
async def init_profile_system_on_startup(app, db_pool):
    """
    在FastAPI应用启动时初始化人格画像系统
    
    将此函数添加到main.py的startup事件处理中
    """
    setup_profile_system(app, db_pool)
    print("[startup] User Personality Profile System initialized")


# ============================================================================
# 集成步骤 2: 在打卡接口中自动提取标签
# ============================================================================

# 修改现有的 /api/user/checkin 端点
async def enhanced_checkin_handler(request, payload, background_tasks):
    """
    增强版打卡处理 - 自动提取人格画像标签
    
    替换原有的 post_checkin 函数中的相关部分
    """
    from user_profile_tag_api import auto_extract_tags_from_checkin
    
    # 原有的打卡处理逻辑...
    user = _get_session_user(request)
    email = user.get('email', '') if user else ''
    
    # 保存打卡数据到数据库，获取checkin_id
    # ... 原有代码 ...
    checkin_id = "generated_checkin_id"  # 替换为实际ID
    
    # 自动提取标签（后台异步执行，不阻塞响应）
    if user and email:
        background_tasks.add_task(
            auto_extract_tags_from_checkin,
            email,  # 使用email作为user_id
            payload.model_dump(),
            str(checkin_id)
        )
    
    return {'ok': True, 'checkin_id': checkin_id}


# ============================================================================
# 集成步骤 3: 在决策接口中自动提取标签
# ============================================================================

# 修改现有的决策相关端点
async def enhanced_decision_handler(user_id, decision_data, decision_id):
    """
    决策事件标签提取
    
    在创建决策事件后调用
    """
    from user_profile_tag_api import auto_extract_tags_from_decision
    
    # 异步提取标签
    import asyncio
    asyncio.create_task(
        auto_extract_tags_from_decision(user_id, decision_data, str(decision_id))
    )


# ============================================================================
# 集成步骤 4: 添加人格画像查询接口
# ============================================================================

# 在主应用路由中添加以下端点
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

profile_router = APIRouter(prefix="/api/user", tags=["user_profile"])


@profile_router.get("/personality-profile")
async def get_my_personality_profile(request):
    """
    获取当前用户的人格画像
    
    需要用户已登录
    """
    from user_profile_tag_system import get_profile_engine
    
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = user.get('email', '')
    
    # 获取 Formation Vector（如果有）
    formation_vector = await _get_user_formation_vector(user_id)
    
    # 生成画像
    engine = get_profile_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Profile system not ready")
    
    from user_profile_tag_system import FormationStateVector
    vector = FormationStateVector.from_dict(formation_vector) if formation_vector else None
    
    profile = engine.generate_profile(user_id, vector)
    
    return {
        'ok': True,
        'profile': profile.to_dict()
    }


@profile_router.get("/personality-profile/summary")
async def get_my_profile_summary(request):
    """获取简化的画像摘要"""
    from user_profile_tag_system import get_profile_engine
    
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = user.get('email', '')
    engine = get_profile_engine()
    
    if not engine:
        raise HTTPException(status_code=503, detail="Profile system not ready")
    
    profile = engine.generate_profile(user_id)
    
    # 返回简化版本
    return {
        'ok': True,
        'summary': {
            'personality_archetype': profile.personality_archetype,
            'dominant_loop': profile.dominant_loop,
            'trajectory_direction': profile.trajectory_direction,
            'profile_summary': profile.profile_summary,
            'trend_direction': profile.trend_direction,
            'top_3_tags': profile.top_emotion_tags[:1] + profile.top_behavior_tags[:1] + profile.top_value_tags[:1],
        }
    }


@profile_router.get("/tags")
async def get_my_tags(
    request,
    category: Optional[str] = None,
    limit: int = 50
):
    """获取当前用户的标签"""
    from user_profile_tag_system import get_tag_store
    
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = user.get('email', '')
    store = get_tag_store()
    
    if not store:
        raise HTTPException(status_code=503, detail="Profile system not ready")
    
    tags = store.get_user_tags(user_id, category=category, limit=limit)
    
    return {
        'ok': True,
        'tags': tags,
        'total': len(tags)
    }


@profile_router.get("/tags/insights")
async def get_my_tag_insights(request):
    """获取用户标签洞察"""
    from user_profile_tag_system import get_tag_store
    
    user = _get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    
    user_id = user.get('email', '')
    store = get_tag_store()
    
    if not store:
        raise HTTPException(status_code=503, detail="Profile system not ready")
    
    insights = store.get_tag_insights(user_id)
    
    return {
        'ok': True,
        'insights': insights
    }


# ============================================================================
# 辅助函数
# ============================================================================

def _get_session_user(request):
    """
    从请求中获取当前用户
    这是main.py中已有函数的引用示例
    """
    # 实际实现请参考main.py中的 _get_session_user 函数
    pass


async def _get_user_formation_vector(user_id: str) -> Optional[dict]:
    """
    从Formation Engine获取用户的8维状态向量
    
    如果已有Formation Engine集成，调用其API获取
    """
    try:
        # 假设有 FormationEngine 可用
        # from formation_pipeline import get_pipeline
        # pipeline = get_pipeline()
        # profile = pipeline.formation_engine.get_profile(user_id)
        # return profile.state_vector.to_dict() if profile else None
        
        # 如果没有，返回None，画像将仅基于标签生成
        return None
    except Exception as e:
        print(f"[formation] Failed to get vector: {e}")
        return None


# ============================================================================
# 主应用集成入口
# ============================================================================

def integrate_with_main_app(app, db_pool):
    """
    将人格画像系统集成到主应用
    
    在main.py的startup事件中调用此函数
    
    Args:
        app: FastAPI应用实例
        db_pool: 数据库连接池
    """
    from user_profile_tag_api import setup_profile_system
    
    # 1. 初始化系统
    setup_profile_system(app, db_pool)
    
    # 2. 注册额外的路由（如果需要）
    # app.include_router(profile_router)
    
    print("[integration] User Personality Profile System fully integrated")


# ============================================================================
# 使用示例
# ============================================================================

"""
在 main.py 中的修改示例：

1. 添加导入:
    from user_profile_integration import integrate_with_main_app
    from user_profile_tag_api import auto_extract_tags_from_checkin

2. 修改startup事件:
    @app.on_event("startup")
    async def startup_event():
        # 原有初始化代码...
        
        # 初始化人格画像系统
        integrate_with_main_app(app, db_pool)

3. 修改打卡端点:
    @app.post('/api/user/checkin')
    async def post_checkin(
        payload: CheckinRequest, 
        request: Request,
        background_tasks: BackgroundTasks  # 添加这个参数
    ):
        user = _get_session_user(request)
        email = user.get('email', '') if user else ''
        
        # 保存打卡数据...
        data = payload.model_dump()
        # ... 保存到数据库，获取checkin_id ...
        
        # 异步提取标签
        if email:
            background_tasks.add_task(
                auto_extract_tags_from_checkin,
                email,
                data,
                str(checkin_id)
            )
        
        return {'ok': True, 'tags_extracted': True}

4. 添加画像查询端点（如果user_profile_tag_api的路由未自动注册）:
    # 这些端点已经在 user_profile_tag_api.py 中定义
    # 只需确保 setup_profile_system 被正确调用
"""
