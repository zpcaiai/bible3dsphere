"""
用户标签系统 API 路由
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from user_tag_system import get_tag_store, tag_extractor, TagSource

router = APIRouter(prefix="/user-tags", tags=["user-tags"])


class TagCreate(BaseModel):
    """手动创建标签请求"""
    tag_name: str
    tag_category: str = "manual"
    source: str = "manual"
    confidence: float = 0.8


class TagListResponse(BaseModel):
    """标签列表响应"""
    user_id: str
    tags: List[Dict[str, Any]]
    total: int
    insights: Optional[Dict[str, Any]] = None


class TagInsightsResponse(BaseModel):
    """标签洞察响应"""
    user_id: str
    insights: Dict[str, Any]


@router.get("/{user_id}", response_model=TagListResponse)
async def get_user_tags(
    user_id: str,
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    include_insights: bool = Query(False, description="是否包含洞察统计")
):
    """获取用户的所有个人标签"""
    store = get_tag_store()
    if not store:
        raise HTTPException(status_code=500, detail="Tag store not initialized")
    
    tags = store.get_user_tags(user_id, category=category, limit=limit)
    
    insights = None
    if include_insights:
        insights = store.get_tag_insights(user_id)
    
    return TagListResponse(
        user_id=user_id,
        tags=tags,
        total=len(tags),
        insights=insights
    )


@router.get("/{user_id}/insights", response_model=TagInsightsResponse)
async def get_tag_insights(user_id: str):
    """获取用户标签的洞察统计"""
    store = get_tag_store()
    if not store:
        raise HTTPException(status_code=500, detail="Tag store not initialized")
    
    insights = store.get_tag_insights(user_id)
    
    return TagInsightsResponse(
        user_id=user_id,
        insights=insights
    )


@router.post("/{user_id}/manual", response_model=Dict[str, str])
async def add_manual_tag(user_id: str, tag: TagCreate):
    """手动添加标签（用户自己添加）"""
    store = get_tag_store()
    if not store:
        raise HTTPException(status_code=500, detail="Tag store not initialized")
    
    tag_data = {
        'tag_name': tag.tag_name,
        'tag_category': tag.tag_category,
        'source': tag.source,
        'confidence': tag.confidence,
        'context': {'added_manually': True}
    }
    
    tag_ids = store.add_or_update_tags(user_id, [tag_data])
    
    return {
        "status": "success",
        "tag_id": tag_ids[0] if tag_ids else None,
        "message": f"标签 '{tag.tag_name}' 已添加"
    }


@router.delete("/{user_id}/{tag_name}")
async def deactivate_tag(user_id: str, tag_name: str):
    """停用标签（隐藏标签）"""
    store = get_tag_store()
    if not store:
        raise HTTPException(status_code=500, detail="Tag store not initialized")
    
    success = store.deactivate_tag(user_id, tag_name)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"标签 '{tag_name}' 不存在")
    
    return {
        "status": "success",
        "message": f"标签 '{tag_name}' 已停用"
    }


@router.post("/{user_id}/extract", response_model=Dict[str, Any])
async def extract_tags_from_text(
    user_id: str,
    text: str,
    source: str = "manual",
    auto_save: bool = Query(False, description="是否自动保存提取的标签")
):
    """从文本中提取标签（测试/预览用）"""
    try:
        source_enum = TagSource(source)
    except ValueError:
        source_enum = TagSource.SYSTEM
    
    extracted_tags = tag_extractor.extract_from_text(text, source_enum)
    
    saved_count = 0
    if auto_save:
        store = get_tag_store()
        if store:
            tag_ids = store.add_or_update_tags(user_id, extracted_tags)
            saved_count = len(tag_ids)
    
    return {
        "user_id": user_id,
        "extracted_tags": extracted_tags,
        "count": len(extracted_tags),
        "saved_count": saved_count if auto_save else None,
        "auto_saved": auto_save
    }


@router.get("/{user_id}/by-category/{category}")
async def get_tags_by_category(user_id: str, category: str, limit: int = 20):
    """按分类获取标签"""
    store = get_tag_store()
    if not store:
        raise HTTPException(status_code=500, detail="Tag store not initialized")
    
    tags = store.get_user_tags(user_id, category=category, limit=limit)
    
    return {
        "user_id": user_id,
        "category": category,
        "tags": tags,
        "count": len(tags)
    }


@router.get("/{user_id}/top")
async def get_top_tags(
    user_id: str,
    n: int = Query(10, ge=1, le=30),
    category: Optional[str] = None
):
    """获取用户最突出的标签（按权重排序）"""
    store = get_tag_store()
    if not store:
        raise HTTPException(status_code=500, detail="Tag store not initialized")
    
    tags = store.get_user_tags(user_id, category=category, limit=n)
    
    # 格式化输出
    formatted_tags = [
        {
            "rank": i + 1,
            "name": tag['tag_name'],
            "category": tag['tag_category'],
            "weight": tag['weight'],
            "confidence": tag['confidence'],
            "occurrences": tag['occurrence_count']
        }
        for i, tag in enumerate(tags)
    ]
    
    return {
        "user_id": user_id,
        "top_tags": formatted_tags,
        "count": len(formatted_tags)
    }
