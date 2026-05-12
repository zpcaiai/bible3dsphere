"""
Vector Router — pgvector semantic search API.
"""

from fastapi import APIRouter, Depends
from services.vector_service.service import VectorService, get_vector_service

router = APIRouter()


@router.post("/search")
async def semantic_search(body: dict, svc: VectorService = Depends(get_vector_service)):
    query = body.get("query", "")
    top_k = body.get("top_k", 5)
    return await svc.search(query, top_k=top_k)


@router.post("/principles")
async def get_principles(body: dict, svc: VectorService = Depends(get_vector_service)):
    return await svc.get_principles(body.get("context", ""), body.get("top_k", 5))
